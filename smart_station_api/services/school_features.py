from datetime import timedelta

from odoo import fields

from odoo.addons.attendance_location_portal.controllers.portal_school_mold import EDITABLE_COL_TYPES
from odoo.addons.attendance_location_portal.controllers.portal_student_case_study import (
    CASE_BOOL_FIELDS, CASE_CHAR_FIELDS, CASE_DATE_FIELDS, CASE_INT_FIELDS,
    CASE_SELECTION_FIELDS, CASE_TEXT_FIELDS,
)

from .base import (
    ApiError, Feature, action, clean_value, describe, field_label, float_to_hhmm,
    form_value, hhmm_to_float, record_options, selection_options, serialize,
    to_float, to_int, today,
)


class _SchoolFeature(Feature):
    """Company-scoped admin features (no own-employee records)."""
    section = 'school'
    employee_field = None

    def base_domain(self, ctx):
        return ctx.company_domain(self.company_field)

    def check_record(self, ctx, record_id):
        record = super().check_record(ctx, record_id)
        if not record.company_id:
            raise ApiError(ctx.t('This record does not exist or is not accessible.', 'هذا السجل غير موجود أو غير متاح.'), 404)
        return record

    def company_filters(self, ctx):
        if len(ctx.companies) < 2:
            return []
        return [('company_%s' % c.id, c.name, [('company_id', '=', c.id)]) for c in ctx.companies]

    # option helpers shared by the forms
    def _company_field(self, ctx, model, values):
        company = ctx.companies.filtered(lambda c: c.id == to_int(values.get('company_id'))) or ctx.companies[:1]
        return company, describe(model, 'company_id', options=record_options(ctx.companies), required=True, reload=True, value=company.id)

    @staticmethod
    def _standards(ctx, company):
        return ctx.env['student.standard'].search(['|', ('company_ids', '=', False), ('company_ids', 'in', company.ids)], order='name, id')

    @staticmethod
    def _divisions(ctx, standard=None):
        domain = [('standard_id', 'in', [False, standard.id])] if standard else []
        return ctx.env['standard.division'].search(domain, order='name, id')

    @staticmethod
    def _students(ctx, company, limit=3000):
        domain = [('is_student', '=', True)]
        if company:
            domain.append(('company_id', 'in', [False, company.id]))
        return ctx.env['res.partner'].search(domain, order='name, id', limit=limit)

    @staticmethod
    def _student_options(students):
        return [{'value': s.id, 'label': '%s%s' % (s.name, ' (%s)' % s.stud_id if s.stud_id else '')} for s in students]


def lines_block(ctx, key, label, records, columns, **options):
    """Table section: columns = [(field, editable, extra_descriptor_dict)]."""
    Model = records.browse()
    cols = []
    for name, editable, extra in columns:
        desc = describe(Model, name, editable=editable)
        desc['key'] = name
        desc.update(extra or {})
        cols.append(desc)
    rows = []
    for rec in records:
        values = {}
        for col in cols:
            if col.get('type') == 'time':
                values[col['key']] = float_to_hhmm(rec[col['key']])
            elif col.get('editable'):
                values[col['key']] = form_value(rec, col['key'])
            else:
                values[col['key']] = serialize(rec, col['key'])
        rows.append({'id': rec.id, 'values': values})
    block = {'type': 'lines', 'key': key, 'label': label, 'columns': cols, 'rows': rows}
    block.update(options)
    return block


class StudentAttendanceFeature(_SchoolFeature):
    key = 'student_attendances'
    model = 'attendance.attendance'
    title = ('Student Attendance', 'حضور الطلاب')
    subtitle = ('Record student attendance for your companies', 'تسجيل حضور الطلاب للشركات المسموح بها')
    icon = 'student_attendance'
    sequence = 110
    permissions = ('can_manage_student_attendance',)
    order = 'date desc, id desc'
    list_fields = ('name', 'company_id', 'standard_id', 'division_id', 'class_id', 'date')
    search_fields = ('name', 'standard_id.name', 'division_id.name', 'class_id.name',
                     'attendance_ids.student_id.name', 'attendance_ids.student_id.stud_id')
    STATUS_ACTIONS = {
        'present': ('present_student', 'Present', 'حاضر', 'success'),
        'absence_reason': ('absence_reason_student', 'Absent (excused)', 'غائب بعذر', 'warning'),
        'absence_noreason': ('absence_noreason_student', 'Absent (no excuse)', 'غائب بدون عذر', 'danger'),
        'late': ('late_student', 'Late', 'متأخر', 'secondary'),
        'withdraw': ('withdraw_student', 'Withdrawn', 'منسحب', 'secondary'),
    }

    def sortings(self, ctx):
        return [('date', ctx.t('Date', 'التاريخ'), 'date desc, id desc'), ('name', ctx.t('Name', 'الاسم'), 'name, id desc')]

    def can_create(self, ctx):
        return True

    def form(self, ctx, values):
        Model = ctx.env[self.model]
        company, company_desc = self._company_field(ctx, Model, values)
        standards = self._standards(ctx, company)
        standard = standards.filtered(lambda s: s.id == to_int(values.get('standard_id')))[:1]
        return [
            company_desc,
            describe(Model, 'standard_id', options=record_options(standards), required=True, reload=True),
            describe(Model, 'division_id', options=record_options(self._divisions(ctx, standard) if standard else []), required=True),
            describe(Model, 'class_id', options=record_options(ctx.env['student.class'].search([], order='name, id'))),
            describe(Model, 'date', required=True, value=values.get('date') or today(ctx)),
        ]

    def create(self, ctx, values):
        company = ctx.company(values.get('company_id'))
        standard = self._standards(ctx, company).filtered(lambda s: s.id == to_int(values.get('standard_id')))
        if not standard:
            raise ApiError(ctx.t('Please select a valid standard.', 'يرجى اختيار صف صحيح.'))
        division = self._divisions(ctx, standard).filtered(lambda d: d.id == to_int(values.get('division_id')))
        if not division:
            raise ApiError(ctx.t('Please select a valid division.', 'يرجى اختيار شعبة صحيحة.'))
        attendance = ctx.env[self.model].create({
            'company_id': company.id,
            'standard_id': standard.id,
            'division_id': division.id,
            'class_id': to_int(values.get('class_id')) or False,
            'date': values.get('date') or today(ctx),
        })
        students = ctx.env['res.partner'].search(attendance._get_student_domain())
        attendance.write({'attendance_ids': [(0, 0, {'student_id': s.id}) for s in students]})
        return attendance

    def sections(self, ctx, record):
        line_actions = [action(key, en, ar, ctx, style) for key, (_m, en, ar, style) in self.STATUS_ACTIONS.items()]
        return [lines_block(ctx, 'attendance_ids', ctx.t('Students', 'الطلاب'), record.attendance_ids,
                            [('roll_no', False, None), ('student_id', False, None), ('status', False, None)],
                            selectable=True, line_actions=line_actions)]

    def run_action(self, ctx, record, key, params):
        if key not in self.STATUS_ACTIONS:
            return super().run_action(ctx, record, key, params)
        line_ids = {to_int(i) for i in params.get('line_ids') or []}
        lines = record.attendance_ids.filtered(lambda line: line.id in line_ids)
        if not lines:
            raise ApiError(ctx.t('Please select at least one student.', 'يرجى اختيار طالب واحد على الأقل.'))
        record.attendance_ids.write({'selected': False})
        lines.write({'selected': True})
        getattr(record, self.STATUS_ACTIONS[key][0])()


class StudentExamFeature(_SchoolFeature):
    key = 'student_exams'
    model = 'student.exam'
    title = ('Student Exams', 'امتحانات الطلاب')
    subtitle = ('Manage student exams for your companies', 'إدارة امتحانات الطلاب للشركات المسموح بها')
    icon = 'exam'
    sequence = 120
    permissions = ('can_manage_student_exams',)
    order = 'start_date desc, id desc'
    list_fields = ('name', 'company_id', 'standard', 'division', 'class_id', 'start_date', 'end_date', 'state')
    detail_fields = ('company_id', 'standard', 'division', 'class_id', 'curr_year', 'start_date', 'end_date', 'state', 'mold_id')
    search_fields = ('name', 'standard.name', 'division.name', 'class_id.name', 'student_ids.name', 'student_ids.stud_id')

    def filters(self, ctx):
        return [('all', ctx.t('All', 'الكل'), [])] + self.state_filters(ctx) + self.company_filters(ctx)

    def sortings(self, ctx):
        return [('date', ctx.t('Date', 'التاريخ'), 'start_date desc, id desc'), ('name', ctx.t('Name', 'الاسم'), 'name, id'),
                ('state', ctx.t('Status', 'الحالة'), 'state, start_date desc')]

    def can_create(self, ctx):
        return True

    def form(self, ctx, values):
        Exam = ctx.env[self.model]
        company, company_desc = self._company_field(ctx, Exam, values)
        standards = self._standards(ctx, company)
        standard = standards.filtered(lambda s: s.id == to_int(values.get('standard')))[:1]
        return [
            describe(Exam, 'name', required=True),
            company_desc,
            describe(Exam, 'standard', options=record_options(standards), reload=True),
            describe(Exam, 'division', options=record_options(self._divisions(ctx, standard) if standard else [])),
            describe(Exam, 'class_id', options=record_options(ctx.env['student.class'].search([], order='name, id'))),
            describe(Exam, 'curr_year', options=record_options(ctx.env['year.year'].search([], order='name desc, id desc'))),
            describe(Exam, 'start_date', required=True, value=values.get('start_date') or today(ctx)),
            describe(Exam, 'end_date', required=True, value=values.get('end_date') or today(ctx)),
            describe(Exam, 'time_from', type='time', value=values.get('time_from') or '09:00'),
            describe(Exam, 'time_to', type='time', value=values.get('time_to') or '11:00'),
        ]

    def _load_students(self, ctx, exam):
        students = ctx.env['res.partner'].search(exam._get_student_domain(), order='roll_no, name')
        exam.write({'student_ids': [(6, 0, students.ids)]})

    def create(self, ctx, values):
        company = ctx.company(values.get('company_id'))
        if not (values.get('name') and values.get('start_date') and values.get('end_date')):
            raise ApiError(ctx.t('Name, start date and end date are required.', 'الاسم وتاريخ البداية والنهاية مطلوبة.'))
        start = fields.Date.to_date(values['start_date'])
        end = fields.Date.to_date(values['end_date'])
        time_from, time_to = hhmm_to_float(values.get('time_from')), hhmm_to_float(values.get('time_to'))
        lines, day, index = [], start, 0
        while day <= end:
            lines.append((0, 0, {'sequence': (index + 1) * 10, 'date': day, 'day': day.strftime('%A').lower(),
                                 'time_from': time_from, 'time_to': time_to}))
            day += timedelta(days=1)
            index += 1
        exam = ctx.env[self.model].create({
            'name': values['name'],
            'company_id': company.id,
            'standard': to_int(values.get('standard')) or False,
            'division': to_int(values.get('division')) or False,
            'class_id': to_int(values.get('class_id')) or False,
            'curr_year': to_int(values.get('curr_year')) or False,
            'start_date': start,
            'end_date': end,
            'time_from': time_from,
            'time_to': time_to,
            'subject_line': lines,
        })
        self._load_students(ctx, exam)
        return exam

    def _subjects(self, ctx, exam):
        return exam.allowed_subject_ids or ctx.env['student.subject'].search([])

    def sections(self, ctx, record):
        editable = record.state == 'draft'
        result = [
            lines_block(ctx, 'subject_line', ctx.t('Subjects', 'المواد'), record.subject_line.sorted(lambda l: (l.sequence, l.id)),
                        [('subject_id', editable, {'options': record_options(self._subjects(ctx, record))}),
                         ('date', editable, None), ('day', False, None),
                         ('time_from', editable, {'type': 'time'}), ('time_to', editable, {'type': 'time'})],
                        editable=editable, can_add=editable, can_delete=editable),
            lines_block(ctx, 'student_ids', ctx.t('Students', 'الطلاب'), record.student_ids,
                        [('name', False, None), ('stud_id', False, None), ('standard', False, None), ('div', False, None), ('class_id', False, None)]),
        ]
        if record.mold_id:
            result.insert(0, {'type': 'link', 'label': ctx.t('Exam Results', 'نتائج الامتحان'),
                              'text': record.mold_id.display_name, 'route': '/f/school_molds/%s' % record.mold_id.id})
        return result

    def save_lines(self, ctx, record, block, rows, new_rows, deleted):
        if block != 'subject_line' or record.state != 'draft':
            return super().save_lines(ctx, record, block, rows, new_rows, deleted)
        allowed = self._subjects(ctx, record)
        commands = [(2, to_int(i)) for i in deleted or [] if to_int(i) in record.subject_line.ids]

        def vals_of(values):
            vals = {}
            if 'subject_id' in values:
                subject = to_int(values['subject_id'])
                if subject and subject not in allowed.ids:
                    raise ApiError(ctx.t('Subject is not allowed for this exam standard/division.', 'المادة غير مسموح بها لصف/شعبة هذا الامتحان.'))
                vals['subject_id'] = subject or False
            if values.get('date'):
                day = fields.Date.to_date(values['date'])
                vals.update(date=day, day=day.strftime('%A').lower())
            for name in ('time_from', 'time_to'):
                if name in values:
                    vals[name] = hhmm_to_float(values[name])
            return vals

        for row in rows or []:
            if to_int(row.get('id')) in record.subject_line.ids:
                commands.append((1, to_int(row['id']), vals_of(row.get('values') or {})))
        for values in new_rows or []:
            vals = vals_of(values)
            vals.setdefault('date', record.start_date)
            vals.setdefault('day', vals['date'].strftime('%A').lower() if vals['date'] else False)
            vals.setdefault('time_from', record.time_from)
            vals.setdefault('time_to', record.time_to)
            commands.append((0, 0, vals))
        record.write({'subject_line': commands})

    def actions(self, ctx, record):
        result = []
        if record.state == 'draft':
            result += [action('confirm', 'Start Exam', 'بدء الامتحان', ctx, 'primary'),
                       action('reload_students', 'Reload Students', 'تحديث الطلاب', ctx),
                       action('cancel', 'Cancel', 'إلغاء', ctx, 'danger', ctx.t('Cancel this exam?', 'هل تريد إلغاء الامتحان؟'))]
        if record.state == 'ongoing':
            result.append(action('complete', 'Complete', 'إنهاء', ctx, 'success',
                                 ctx.t('Completing the exam creates its results sheet. Continue?', 'إنهاء الامتحان سيُنشئ كشف النتائج. هل تريد المتابعة؟')))
        result.append(action('delete', 'Delete', 'حذف', ctx, 'danger', ctx.t('Delete this exam?', 'هل تريد حذف الامتحان؟')))
        return result

    def run_action(self, ctx, record, key, params):
        if key == 'confirm' and record.state == 'draft':
            record.ongoing_exam()
        elif key == 'cancel' and record.state == 'draft':
            record.cancel_exam()
        elif key == 'complete' and record.state == 'ongoing':
            record.close_exam()
        elif key == 'reload_students' and record.state == 'draft':
            self._load_students(ctx, record)
        elif key == 'delete':
            record.unlink()
            return {'deleted': True}
        else:
            super().run_action(ctx, record, key, params)

    def reports(self, ctx, record):
        return [{'key': 'schedule', 'label': ctx.t('Exam Schedule (PDF)', 'جدول الامتحان (PDF)'), 'preview': True}]

    def report(self, ctx, record, key):
        if key != 'schedule':
            return super().report(ctx, record, key)
        report = ctx.env.ref('jt_education_exam.action_report_exam_schedule')
        content, _t = ctx.env['ir.actions.report'].with_context(lang='ar_001')._render_qweb_pdf(report, record.ids)
        return content, 'Exam_Schedule_%s.pdf' % record.id, 'application/pdf'


class SchoolMoldFeature(_SchoolFeature):
    key = 'school_molds'
    model = 'school.mold'
    title = ('Exam Results', 'نتائج الامتحانات')
    subtitle = ('Manage grade sheets / exam results for your companies', 'إدارة قوالب الدرجات / نتائج الامتحانات للشركات المسموح بها')
    icon = 'results'
    sequence = 130
    permissions = ('can_manage_school_molds',)
    order = 'date desc, id desc'
    list_fields = ('name', 'company_id', 'term', 'term_types', 'exam_type', 'date', 'exam_id', 'line_count', 'state')
    detail_fields = ('term', 'term_types', 'exam_type', 'company_id', 'year_id', 'class_id', 'standard_id', 'division_id', 'date', 'exam_id', 'note', 'line_count', 'state')
    search_fields = ('name', 'exam_id.name', 'class_id.name', 'year_id.name', 'line_ids.student_name', 'line_ids.student_id.stud_id')

    def base_domain(self, ctx):
        return super().base_domain(ctx) + [('mold_kind', '=', 'grades')]

    def check_record(self, ctx, record_id):
        """Exam admins may open (read only) the results generated from their exams."""
        if ctx.can('can_manage_school_molds'):
            return super().check_record(ctx, record_id)
        mold = ctx.env[self.model].browse(to_int(record_id))
        if ctx.can('can_manage_student_exams') and mold.exists() and mold.exam_id \
                and mold.company_id.id in ctx.company_ids and mold.exam_id.company_id.id in ctx.company_ids:
            return mold
        raise ApiError(ctx.t('This result does not exist or is not accessible.', 'هذه النتيجة غير موجودة أو غير متاحة.'), 404)

    def filters(self, ctx):
        return [('all', ctx.t('All', 'الكل'), [])] + self.state_filters(ctx) + self.company_filters(ctx)

    def sortings(self, ctx):
        return [('date', ctx.t('Date', 'التاريخ'), 'date desc, id desc'), ('name', ctx.t('Name', 'الاسم'), 'name, id'),
                ('state', ctx.t('Status', 'الحالة'), 'state, date desc')]

    def can_create(self, ctx):
        return True

    def _term_types(self, ctx, term):
        options = selection_options(ctx.env[self.model], 'term_types')
        try:
            from odoo.addons.school_molds_generator.models.school_mold import BASE_TERM_TYPE_KEYS, FIRST_TERM_ONLY_TYPE_KEYS
        except ImportError:
            return options
        allowed = set(BASE_TERM_TYPE_KEYS) | (set(FIRST_TERM_ONLY_TYPE_KEYS) if (term or 'first') == 'first' else set())
        return [opt for opt in options if opt['value'] in allowed]

    def form(self, ctx, values):
        Mold = ctx.env[self.model]
        _company, company_desc = self._company_field(ctx, Mold, values)
        term = values.get('term') or 'first'
        term_types = self._term_types(ctx, term)
        return [
            company_desc,
            describe(Mold, 'term', required=True, reload=True, value=term),
            describe(Mold, 'term_types', required=True, options=term_types),
            describe(Mold, 'exam_type', value=values.get('exam_type') or 'monthly'),
            describe(Mold, 'year_id', options=record_options(ctx.env['year.year'].search([], order='name desc, id desc'))),
            describe(Mold, 'class_id', options=record_options(ctx.env['student.class'].search([], order='name, id'))),
            describe(Mold, 'date', value=values.get('date') or today(ctx)),
            {'name': 'load_students', 'type': 'boolean', 'label': ctx.t('Load students', 'تحميل الطلاب'), 'value': True},
        ]

    def create(self, ctx, values):
        company = ctx.company(values.get('company_id'))
        term = values.get('term') or 'first'
        if values.get('term_types') not in {opt['value'] for opt in self._term_types(ctx, term)}:
            raise ApiError(ctx.t('Please select a valid term and specialization.', 'يرجى اختيار فصل وتخصص صحيحين.'))
        Mold = ctx.env[self.model]
        mold = Mold.create({
            'mold_kind': 'grades',
            'company_id': company.id,
            'term': term,
            'term_types': values['term_types'],
            'exam_type': clean_value(Mold, 'exam_type', values.get('exam_type')) or 'monthly',
            'year_id': to_int(values.get('year_id')) or False,
            'class_id': to_int(values.get('class_id')) or False,
            'date': values.get('date') or today(ctx),
        })
        if values.get('load_students'):
            mold.action_load_students()
        return mold

    def _editable(self, ctx, mold):
        return mold.state == 'draft' and ctx.can('can_manage_school_molds')

    def sections(self, ctx, record):
        editable = self._editable(ctx, record)
        columns = record.column_ids.sorted(lambda c: (c.sequence, c.id))
        cols = []
        for column in columns:
            is_name = column.col_type == 'name'
            cols.append({
                'key': '__student_name' if is_name else column.key,
                'label': column.name,
                'group': column.group_name or '',
                'color': column.color or '',
                'type': 'float' if column.col_type == 'score' else 'char',
                'editable': editable and (is_name or column.col_type in EDITABLE_COL_TYPES),
                'max': column.max_value or None,
            })
        rows = []
        for line in record.line_ids.sorted(lambda l: (l.sequence, l.id)):
            values = {}
            for column, col in zip(columns, cols):
                values[col['key']] = line.student_name or '' if column.col_type == 'name' else line._cell_value(column)
            rows.append({'id': line.id, 'values': values})
        return [{'type': 'lines', 'key': 'line_ids', 'label': ctx.t('Results Sheet', 'كشف النتائج'), 'columns': cols,
                 'rows': rows, 'editable': editable, 'can_delete': editable, 'grid': True}]

    def save_lines(self, ctx, record, block, rows, new_rows, deleted):
        if block != 'line_ids' or not self._editable(ctx, record):
            raise ApiError(ctx.t('This result is done and cannot be modified.', 'هذه النتيجة منتهية ولا يمكن تعديلها.'))
        editable_keys = {c.key for c in record.column_ids if c.col_type in EDITABLE_COL_TYPES}
        lines = {line.id: line for line in record.line_ids}
        for line_id in deleted or []:
            if to_int(line_id) in lines:
                lines.pop(to_int(line_id)).unlink()
        for row in rows or []:
            line = lines.get(to_int(row.get('id')))
            if not line:
                continue
            posted = row.get('values') or {}
            values = dict(line.values_json or {})
            vals = {}
            for key in editable_keys & set(posted):
                values[key] = str(posted[key] if posted[key] is not None else '').strip()
            if values != (line.values_json or {}):
                vals['values_json'] = values
            if '__student_name' in posted and (posted['__student_name'] or '') != (line.student_name or ''):
                vals['student_name'] = (posted['__student_name'] or '').strip()
            if vals:
                line.write(vals)
        record.line_ids._recompute_totals(record.column_ids)

    def actions(self, ctx, record):
        if not ctx.can('can_manage_school_molds'):
            return []
        if record.state == 'draft':
            return [action('load_students', 'Load Students', 'تحميل الطلاب', ctx),
                    action('add_rows', 'Add Rows', 'إضافة صفوف', ctx),
                    action('recompute', 'Recompute Totals', 'إعادة حساب المجاميع', ctx),
                    action('mark_done', 'Mark Done', 'اعتماد', ctx, 'success'),
                    action('delete', 'Delete', 'حذف', ctx, 'danger', ctx.t('Delete this result?', 'هل تريد حذف هذه النتيجة؟'))]
        return [action('reset_draft', 'Reset to Draft', 'إعادة إلى مسودة', ctx),
                action('delete', 'Delete', 'حذف', ctx, 'danger', ctx.t('Delete this result?', 'هل تريد حذف هذه النتيجة؟'))]

    def run_action(self, ctx, record, key, params):
        if not ctx.can('can_manage_school_molds'):
            raise ApiError(ctx.t('You are not allowed to edit school molds.', 'غير مسموح لك بتعديل النتائج.'), 403)
        methods = {'load_students': 'action_load_students', 'add_rows': 'action_add_empty_rows',
                   'recompute': 'action_recompute_totals', 'mark_done': 'action_mark_done'}
        if key in methods and record.state == 'draft':
            getattr(record, methods[key])()
        elif key == 'reset_draft' and record.state == 'done':
            record.action_reset_draft()
        elif key == 'delete':
            record.unlink()
            return {'deleted': True}
        else:
            super().run_action(ctx, record, key, params)

    def reports(self, ctx, record):
        return [{'key': 'xlsx', 'label': ctx.t('Download Excel', 'تحميل Excel')}]

    def report(self, ctx, record, key):
        if key != 'xlsx':
            return super().report(ctx, record, key)
        content, filename = record._generate_xlsx()
        return content, filename, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class ViolationFeature(_SchoolFeature):
    key = 'student_violations'
    model = 'student.violation'
    title = ('Student Violations', 'مخالفات الطلاب')
    subtitle = ('Manage student violations for your companies', 'إدارة مخالفات الطلاب للشركات المسموح بها')
    icon = 'violation'
    sequence = 150
    permissions = ('can_manage_violations',)
    order = 'date desc, id desc'
    list_fields = ('date', 'student_id', 'stud_id', 'company_id', 'violation_type', 'action_taken')
    detail_fields = ('company_id', 'student_id', 'stud_id', 'class_id', 'div_id', 'date', 'violation_type', 'action_taken', 'description', 'notes')
    search_fields = ('student_id.name', 'student_id.stud_id', 'notes', 'description')
    FORM_FIELDS = ('date', 'student_id', 'class_id', 'div_id', 'violation_type', 'action_taken', 'description', 'notes')

    def sortings(self, ctx):
        return [('date', ctx.t('Date', 'التاريخ'), 'date desc, id desc'), ('student', ctx.t('Student', 'الطالب'), 'student_id, date desc')]

    def can_create(self, ctx):
        return True

    def _options(self, ctx, company):
        Violation = ctx.env[self.model]
        to_opts = lambda sel: [{'value': k, 'label': v} for k, v in sel]
        return (to_opts(Violation._get_violation_type_selection_for_company(company)),
                to_opts(Violation._get_action_taken_selection_for_company(company)))

    def _fields(self, ctx, company, values, record=None):
        Violation = ctx.env[self.model]
        types, actions_ = self._options(ctx, company)
        student = ctx.env['res.partner'].browse(to_int(values.get('student_id'))) if values.get('_changed') == 'student_id' else None
        return [
            describe(Violation, 'date', required=True, value=values.get('date') or (form_value(record, 'date') if record else today(ctx))),
            describe(Violation, 'student_id', options=self._student_options(self._students(ctx, company)), required=True, reload=not record),
            describe(Violation, 'class_id', options=record_options(ctx.env['student.class'].search([], order='name, id')),
                     **({'value': student.class_id.id} if student else {})),
            describe(Violation, 'div_id', options=record_options(ctx.env['standard.division'].search([], order='name, id')),
                     **({'value': student.div.id} if student else {})),
            describe(Violation, 'violation_type', options=types, required=True),
            describe(Violation, 'action_taken', options=actions_),
            describe(Violation, 'description', type='text'),
            describe(Violation, 'notes', type='text'),
        ]

    def form(self, ctx, values):
        company, company_desc = self._company_field(ctx, ctx.env[self.model], values)
        return [company_desc] + self._fields(ctx, company, values)

    def _vals(self, ctx, company, values):
        types, actions_ = self._options(ctx, company)
        if values.get('violation_type') not in {o['value'] for o in types} or \
                (values.get('action_taken') and values['action_taken'] not in {o['value'] for o in actions_}):
            raise ApiError(ctx.t('Selected violation or action is not valid for this company.', 'المخالفة أو الإجراء المختار غير صالح لهذه الشركة.'))
        Violation = ctx.env[self.model]
        vals = {name: values[name] if name in ('violation_type', 'action_taken') else clean_value(Violation, name, values.get(name))
                for name in self.FORM_FIELDS if name in values}
        if not (vals.get('student_id') and vals.get('date') and vals.get('violation_type')):
            raise ApiError(ctx.t('Student, date and violation type are required.', 'الطالب والتاريخ ونوع المخالفة مطلوبة.'))
        return vals

    def create(self, ctx, values):
        company = ctx.company(values.get('company_id'))
        return ctx.env[self.model].create(dict(self._vals(ctx, company, values), company_id=company.id))

    def edit_fields(self, ctx, record):
        return self._fields(ctx, record.company_id, {}, record)

    def save(self, ctx, record, values):
        merged = {name: form_value(record, name) for name in self.FORM_FIELDS}
        merged.update(values)
        record.write(self._vals(ctx, record.company_id, merged))

    def actions(self, ctx, record):
        return [action('delete', 'Delete', 'حذف', ctx, 'danger', ctx.t('Delete this violation?', 'هل تريد حذف المخالفة؟'))]

    def run_action(self, ctx, record, key, params):
        if key == 'delete':
            record.unlink()
            return {'deleted': True}
        return super().run_action(ctx, record, key, params)


class CaseStudyFeature(_SchoolFeature):
    key = 'case_studies'
    model = 'student.case.study'
    title = ('Case Studies', 'دراسات الحالة')
    subtitle = ('Manage electronic student case studies', 'إدارة دراسات الحالة الإلكترونية للشركات المسموح بها')
    icon = 'case'
    sequence = 160
    permissions = ('can_manage_violations',)
    order = 'date desc, id desc'
    list_fields = ('date', 'name', 'student_id', 'stud_id', 'company_id', 'psychologist_id')
    detail_fields = ('company_id', 'student_id', 'stud_id', 'date', 'psychologist_id')
    search_fields = ('name', 'student_id.name', 'student_id.stud_id', 'referral_reason', 'psychologist_id.name')
    FORM_FIELDS = ['student_id', 'class_id', 'div_id'] + CASE_DATE_FIELDS + CASE_CHAR_FIELDS + CASE_INT_FIELDS + \
        CASE_SELECTION_FIELDS + CASE_BOOL_FIELDS + CASE_TEXT_FIELDS
    FAMILY_FIELDS = ('relation_type', 'name', 'age', 'education', 'job', 'economic_level')

    def sortings(self, ctx):
        return [('date', ctx.t('Date', 'التاريخ'), 'date desc, id desc'), ('student', ctx.t('Student', 'الطالب'), 'student_id, date desc')]

    def can_create(self, ctx):
        return True

    def _group(self, name):
        if name in ('student_id', 'class_id', 'div_id', 'date', 'name', 'birthdate', 'gender', 'nationality', 'marital_status', 'residence', 'live_with', 'referral_reason'):
            return 'demographic'
        if name in CASE_BOOL_FIELDS:
            return 'symptoms'
        if name in ('general_appearance', 'smile_type', 'sitting_posture', 'eye_contact', 'movement_activity_level', 'thought_coherence',
                    'voice_tone', 'mood_emotional_state', 'involuntary_movements', 'physical_injuries', 'behavioral_notes',
                    'depression_anxiety_indicators', 'initial_diagnosis', 'therapeutic_goals', 'treatment_plan', 'recommendations'):
            return 'psychologist'
        return 'history'

    GROUP_LABELS = {'demographic': ('Demographic Data', 'البيانات الديموغرافية'), 'history': ('Childhood & History', 'الطفولة والتاريخ'),
                    'symptoms': ('Violence & Symptoms', 'العنف والأعراض'), 'psychologist': ('Psychologist Assessment', 'تقييم الأخصائي')}

    def _fields(self, ctx, company, values, record=None):
        Case = ctx.env[self.model]
        student = None
        if values.get('_changed') == 'student_id' and to_int(values.get('student_id')):
            student = ctx.env['res.partner'].browse(to_int(values['student_id']))
        prefill = {}
        if student:
            prefill = {'name': student.name, 'birthdate': form_value(student, 'birthdate'), 'nationality': student.nationality or '',
                       'class_id': student.class_id.id or False, 'div_id': student.div.id or False}
            if student.gender in {o['value'] for o in selection_options(Case, 'gender')}:
                prefill['gender'] = student.gender
        options = {'student_id': self._student_options(self._students(ctx, company)),
                   'class_id': record_options(ctx.env['student.class'].search([], order='name, id')),
                   'div_id': record_options(ctx.env['standard.division'].search([], order='name, id'))}
        result = []
        for name in self.FORM_FIELDS:
            extra = {'group': self._group(name)}
            if name in options:
                extra['options'] = options[name]
            if name == 'student_id':
                extra.update(required=True, reload=not record)
            if name in prefill:
                extra['value'] = prefill[name]
            if name == 'date' and not record:
                extra['value'] = values.get('date') or today(ctx)
            result.append(describe(Case, name, **extra))
        for desc in result:
            desc['group_label'] = ctx.t(*self.GROUP_LABELS[desc['group']])
        return result

    def form(self, ctx, values):
        company, company_desc = self._company_field(ctx, ctx.env[self.model], values)
        company_desc.update(group='demographic', group_label=ctx.t(*self.GROUP_LABELS['demographic']))
        return [company_desc] + self._fields(ctx, company, values)

    def _vals(self, ctx, values):
        Case = ctx.env[self.model]
        return {name: clean_value(Case, name, values.get(name)) for name in self.FORM_FIELDS if name in values}

    def create(self, ctx, values):
        company = ctx.company(values.get('company_id'))
        vals = self._vals(ctx, values)
        if not vals.get('student_id'):
            raise ApiError(ctx.t('Please select a student.', 'يرجى اختيار طالب.'))
        vals.update(company_id=company.id, date=vals.get('date') or today(ctx))
        if ctx.employee.user_id:
            vals['psychologist_id'] = ctx.employee.user_id.id
        relations = ('father', 'mother', 'other')
        allowed = {o['value'] for o in selection_options(ctx.env['student.case.study.family'], 'relation_type')}
        vals['family_member_ids'] = [(0, 0, {'relation_type': rel, 'sequence': (i + 1) * 10}) for i, rel in enumerate(relations) if rel in allowed]
        return ctx.env[self.model].create(vals)

    def edit_fields(self, ctx, record):
        return self._fields(ctx, record.company_id, {}, record)

    def save(self, ctx, record, values):
        record.write(self._vals(ctx, values))

    def sections(self, ctx, record):
        columns = [(name, True, None) for name in self.FAMILY_FIELDS]
        return [lines_block(ctx, 'family_member_ids', ctx.t('Family Members', 'أفراد الأسرة'),
                            record.family_member_ids.sorted(lambda l: (l.sequence, l.id)), columns,
                            editable=True, can_add=True, can_delete=True)]

    def save_lines(self, ctx, record, block, rows, new_rows, deleted):
        if block != 'family_member_ids':
            return super().save_lines(ctx, record, block, rows, new_rows, deleted)
        Family = ctx.env['student.case.study.family']
        vals_of = lambda values: {n: clean_value(Family, n, values[n]) for n in self.FAMILY_FIELDS if n in values}
        ids = set(record.family_member_ids.ids)
        commands = [(2, to_int(i)) for i in deleted or [] if to_int(i) in ids]
        commands += [(1, to_int(r['id']), vals_of(r.get('values') or {})) for r in rows or [] if to_int(r.get('id')) in ids]
        start = len(record.family_member_ids)
        commands += [(0, 0, dict(vals_of(v), relation_type=v.get('relation_type') or 'other', sequence=(start + i + 1) * 10))
                     for i, v in enumerate(new_rows or [])]
        record.write({'family_member_ids': commands})

    def actions(self, ctx, record):
        return [action('delete', 'Delete', 'حذف', ctx, 'danger', ctx.t('Delete this case study?', 'هل تريد حذف دراسة الحالة؟'))]

    def run_action(self, ctx, record, key, params):
        if key == 'delete':
            record.unlink()
            return {'deleted': True}
        return super().run_action(ctx, record, key, params)

    def reports(self, ctx, record):
        return [{'key': 'pdf', 'label': ctx.t('Print Case Study', 'طباعة دراسة الحالة'), 'preview': True}]

    def report(self, ctx, record, key):
        report = ctx.env['ir.actions.report'].search([('report_name', '=', 'jt_student_violations.report_student_case_study')], limit=1)
        if key != 'pdf' or not report:
            return super().report(ctx, record, key)
        content, _t = report.with_context(lang='ar_001')._render_qweb_pdf(report.report_name, res_ids=record.ids)
        name = record.name or record.student_id.name or record.id
        return content, 'Case_Study_%s.pdf' % name, 'application/pdf'
