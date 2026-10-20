# -*- coding: utf-8 -*-
import hashlib
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .default_columns import (
    COLOR_GRAND,
    EMPTY_ROW_COUNT,
    IDENTITY_COL_TYPES,
    get_exam_subject_names,
    get_template_columns,
    resolve_term_from_standard_name,
    resolve_term_type_from_division_name,
)

EXAM_SUBJECT_COLORS = (
    '#A8D08D',
    '#A8C8E8',
    '#FFF3A0',
    '#F6E8B8',
    '#F5E04A',
    '#E8A8A8',
    '#B8A0D8',
    '#F0A040',
)


class StudentExam(models.Model):
    _inherit = 'student.exam'

    allowed_subject_ids = fields.Many2many(
        'student.subject',
        'student_exam_allowed_subject_rel',
        'exam_id',
        'subject_id',
        compute='_compute_allowed_subject_ids',
        store=True,
        string='Allowed Subjects',
        help='Subjects available for the selected standard and division '
             '(from school mold column layouts).',
    )
    mold_id = fields.Many2one(
        'school.mold',
        string='School Mold',
        copy=False,
        readonly=True,
        help='Grade mold created automatically when this exam is completed.',
    )

    @api.depends('standard', 'division')
    def _compute_allowed_subject_ids(self):
        for exam in self:
            names = exam._get_mold_subject_names()
            if not names:
                exam.allowed_subject_ids = False
                continue
            exam.allowed_subject_ids = exam._find_or_create_subjects(names)

    def _get_mold_subject_names(self):
        """Resolve mold subject labels from exam standard + division."""
        self.ensure_one()
        term = resolve_term_from_standard_name(self.standard.name if self.standard else '')
        term_type = resolve_term_type_from_division_name(
            self.division.name if self.division else ''
        )
        if not term:
            return []
        return get_exam_subject_names(term, term_type)

    def _find_or_create_subjects(self, names):
        """Match student.subject by name; create missing ones for the dropdown."""
        Subject = self.env['student.subject'].sudo()
        subjects = Subject
        for name in names:
            subject = Subject.search([('name', '=', name)], limit=1)
            if not subject:
                subject = Subject.search([('name', 'ilike', name)], limit=1)
            if not subject:
                code = self._subject_code_from_name(name)
                base_code = code
                suffix = 1
                while Subject.search([('code', '=', code)], limit=1):
                    code = '%s-%s' % (base_code, suffix)
                    suffix += 1
                subject = Subject.create({
                    'name': name,
                    'code': code,
                })
            subjects |= subject
        return subjects

    @staticmethod
    def _subject_code_from_name(name):
        digest = hashlib.md5((name or '').encode('utf-8')).hexdigest()[:8].upper()
        return 'SUB-%s' % digest

    def close_exam(self):
        for exam in self:
            if not exam.mold_id:
                mold = exam._create_school_mold_from_exam()
                exam.mold_id = mold.id
            exam.state = 'close'
        return True

    def action_open_school_mold(self):
        self.ensure_one()
        if not self.mold_id:
            raise UserError(_('No school mold is linked to this exam yet. Complete the exam first.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('School Mold'),
            'res_model': 'school.mold',
            'res_id': self.mold_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_school_mold_from_exam(self):
        """Create a grades mold from this exam's header, subjects, and students."""
        self.ensure_one()
        if not self.company_id or not self.standard:
            raise UserError(_('Company and Standard are required to create a school mold.'))
        if not self.subject_line.filtered('subject_id'):
            raise UserError(_('Add at least one subject before completing the exam.'))

        term = resolve_term_from_standard_name(self.standard.name or '') or 'first'
        term_type = resolve_term_type_from_division_name(
            self.division.name if self.division else ''
        ) or 'industrial_electricity'
        exam_type = 'final' if self.is_annual else 'monthly'

        line_commands = self._mold_line_commands_from_exam()
        mold_name = self._prepare_mold_name(term, term_type)
        mold = self.env['school.mold'].with_context(skip_mold_layout=True).create({
            'name': mold_name,
            'company_id': self.company_id.id,
            'mold_kind': 'grades',
            'year_id': self.curr_year.id if self.curr_year else False,
            'class_id': self.class_id.id if self.class_id else False,
            'standard_id': self.standard.id,
            'division_id': self.division.id if self.division else False,
            'term': term,
            'term_types': term_type,
            'exam_type': exam_type,
            'date': self.end_date or self.start_date or fields.Date.context_today(self),
            'note': self.name or '',
            'exam_id': self.id,
            'line_ids': line_commands or [
                (0, 0, {
                    'sequence': index,
                    'student_name': '',
                    'values_json': {},
                })
                for index in range(1, EMPTY_ROW_COUNT + 1)
            ],
        })
        # Only the subjects scheduled on this exam (e.g. 3 subjects → 3 groups).
        mold._load_columns_from_exam(self)
        mold.message_post(body=_(
            'Created automatically from exam <a href="#" data-oe-model="student.exam" data-oe-id="%(exam_id)s">%(exam_name)s</a> '
            'with %(count)s subject(s).'
        ) % {
            'exam_id': self.id,
            'exam_name': self.display_name or self.name or self.id,
            'count': len(self.subject_line.filtered('subject_id')),
        })
        return mold

    def _prepare_mold_name(self, term, term_type):
        """Build a non-empty mold name before create (name is required/stored)."""
        self.ensure_one()
        Mold = self.env['school.mold']
        term_label = dict(Mold._fields['term'].selection).get(term) or ''
        type_label = dict(Mold._fields['term_types'].selection).get(term_type) or ''
        class_label = self.class_id.display_name or ''
        company_label = self.company_id.display_name or ''
        parts = [part for part in (term_label, type_label) if part]
        if class_label and company_label:
            parts.append('%s (%s)' % (class_label, company_label))
        elif class_label:
            parts.append(class_label)
        elif company_label:
            parts.append('(%s)' % company_label)
        if self.name:
            parts.insert(0, self.name)
        return ' - '.join(parts) or _('Exam Mold')

    def _mold_line_commands_from_exam(self):
        """Build mold row commands from exam students."""
        self.ensure_one()
        commands = []
        students = self.student_ids.sorted(
            key=lambda student: (student.roll_no or 0, student.name or '')
        )
        for index, student in enumerate(students, start=1):
            class_name = (
                student.class_id.name
                if student.class_id
                else (self.class_id.name if self.class_id else '')
            )
            commands.append((0, 0, {
                'sequence': index,
                'student_id': student.id,
                'student_name': student.name,
                'values_json': {
                    'seat_number': student.roll_no or '',
                    'class': class_name or '',
                },
            }))
        return commands


class SchoolMold(models.Model):
    _inherit = 'school.mold'

    def _load_columns_from_exam(self, exam):
        """Replace mold columns with identity + only the exam's subjects + grand total."""
        self.ensure_one()
        column_defs = self._build_exam_column_defs(exam)
        self.column_ids.unlink()
        self.column_ids = [
            (0, 0, {
                'sequence': sequence,
                'key': column['key'],
                'name': column['name'],
                'group_name': column.get('group_name') or '',
                'col_type': column['col_type'],
                'color': column.get('color') or '#FFFFFF',
                'max_value': column.get('max_value') or 0,
                'include_in_grand_total': column.get('include_in_grand_total', True),
            })
            for sequence, column in enumerate(column_defs, start=1)
        ]

    def _build_exam_column_defs(self, exam):
        """Build column layout from exam subject lines only."""
        self.ensure_one()
        layout = get_template_columns(
            self.term or 'first',
            self.term_types,
            'grades',
        )
        identity_cols = [
            col for col in layout
            if col.get('col_type') in IDENTITY_COL_TYPES
        ]

        # Map template subject groups: normalized label → list of columns
        groups = {}
        for col in layout:
            if col.get('col_type') in IDENTITY_COL_TYPES:
                continue
            if col.get('col_type') in ('total', 'grand_total'):
                continue
            if col.get('key') in ('practical_total', 'theory', 'year_work'):
                continue
            label = (col.get('group_name') or col.get('name') or '').strip()
            if not label:
                continue
            key = self._normalize_subject_label(label)
            groups.setdefault(key, {'label': label, 'columns': []})
            groups[key]['columns'].append(dict(col))

        subject_cols = []
        grand_max = 0.0
        used_keys = set()
        exam_lines = exam.subject_line.sorted(
            key=lambda line: (line.sequence, line.date or fields.Date.today(), line.id)
        ).filtered('subject_id')

        for index, subject_line in enumerate(exam_lines):
            subject_name = (subject_line.subject_id.name or '').strip()
            if not subject_name:
                continue
            matched = self._match_template_subject_group(subject_name, groups)
            if matched:
                group_columns = []
                for col in matched['columns']:
                    col_copy = dict(col)
                    # Avoid duplicate keys if the same subject appears twice
                    if col_copy['key'] in used_keys:
                        col_copy['key'] = '%s_%s' % (col_copy['key'], index + 1)
                    used_keys.add(col_copy['key'])
                    group_columns.append(col_copy)
                if subject_line.mark:
                    self._apply_mark_to_group(group_columns, subject_line.mark)
                subject_cols.extend(group_columns)
                subtotal = next(
                    (c for c in group_columns if c.get('col_type') == 'subtotal'),
                    None,
                )
                if subtotal and subtotal.get('include_in_grand_total', True):
                    grand_max += float(subtotal.get('max_value') or 0)
                continue

            # Subject not in the grade template — synthesize a simple group
            synthesized = self._synthesize_subject_columns(
                subject_name, index, subject_line.mark
            )
            for col in synthesized:
                used_keys.add(col['key'])
            subject_cols.extend(synthesized)
            subtotal = next(
                (c for c in synthesized if c.get('col_type') == 'subtotal'),
                None,
            )
            if subtotal:
                grand_max += float(subtotal.get('max_value') or 0)

        columns = list(identity_cols) + subject_cols
        columns.append({
            'key': 'grand_total',
            'name': 'المجموع الكلي',
            'group_name': '',
            'col_type': 'grand_total',
            'color': COLOR_GRAND,
            'max_value': grand_max or 0,
            'include_in_grand_total': True,
        })
        return columns

    @staticmethod
    def _normalize_subject_label(name):
        text = (name or '').strip()
        for src, dst in (
            ('أ', 'ا'),
            ('إ', 'ا'),
            ('آ', 'ا'),
            ('ى', 'ي'),
            ('ة', 'ه'),
        ):
            text = text.replace(src, dst)
        text = re.sub(r'\s+', '', text)
        return text

    def _match_template_subject_group(self, subject_name, groups):
        """Find a template subject group for an exam subject name."""
        needle = self._normalize_subject_label(subject_name)
        if not needle:
            return None
        if needle in groups:
            return groups[needle]
        # Containment match (e.g. مبادئ حاسب آلي ↔ مبادئ حاسوب)
        for key, group in groups.items():
            if needle in key or key in needle:
                return group
        return None

    @staticmethod
    def _apply_mark_to_group(group_columns, mark):
        """Scale/set max values when the exam line has an explicit mark."""
        mark = float(mark or 0)
        if mark <= 0:
            return
        main = next(
            (c for c in group_columns if c.get('key', '').endswith('_subject')),
            None,
        )
        if not main:
            main = next(
                (c for c in group_columns if c.get('col_type') == 'score'),
                None,
            )
        subtotal = next(
            (c for c in group_columns if c.get('col_type') == 'subtotal'),
            None,
        )
        if main and subtotal:
            # Keep work columns; put exam mark on the main subject score.
            main['max_value'] = mark
            work_total = sum(
                float(c.get('max_value') or 0)
                for c in group_columns
                if c.get('col_type') == 'score' and c is not main
            )
            subtotal['max_value'] = mark + work_total
        elif main:
            main['max_value'] = mark
        elif subtotal:
            subtotal['max_value'] = mark

    def _synthesize_subject_columns(self, subject_name, index, mark):
        """Create subject / year-work / subtotal columns for unknown subjects."""
        color = EXAM_SUBJECT_COLORS[index % len(EXAM_SUBJECT_COLORS)]
        total = float(mark) if mark else 50.0
        subject_max = round(total * 0.7, 2) if total else 35.0
        work_max = max(total - subject_max, 0.0)
        prefix = 'ex%s' % (index + 1)
        return [
            {
                'key': '%s_subject' % prefix,
                'name': subject_name,
                'group_name': subject_name,
                'col_type': 'score',
                'color': color,
                'max_value': subject_max,
                'include_in_grand_total': True,
            },
            {
                'key': '%s_work' % prefix,
                'name': 'أعمال السنة',
                'group_name': subject_name,
                'col_type': 'score',
                'color': color,
                'max_value': work_max,
                'include_in_grand_total': True,
            },
            {
                'key': '%s_total' % prefix,
                'name': 'المجموع',
                'group_name': subject_name,
                'col_type': 'subtotal',
                'color': color,
                'max_value': total,
                'include_in_grand_total': True,
            },
        ]

    def action_open_exam(self):
        self.ensure_one()
        if not self.exam_id:
            raise UserError(_('This mold is not linked to an exam.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Exam'),
            'res_model': 'student.exam',
            'res_id': self.exam_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class SubjectLine(models.Model):
    _inherit = 'subject.line'

    @api.onchange('subject_id')
    def _onchange_subject_mark(self):
        for line in self:
            if line.subject_id and line.subject_id.mark:
                line.mark = int(line.subject_id.mark)

    @api.constrains('subject_id', 'exam_id')
    def _check_subject_allowed_for_exam(self):
        for line in self:
            if not line.subject_id or not line.exam_id:
                continue
            allowed = line.exam_id.allowed_subject_ids
            if allowed and line.subject_id not in allowed:
                raise ValidationError(_(
                    "Subject '%(subject)s' is not valid for standard %(standard)s / division %(division)s."
                ) % {
                    'subject': line.subject_id.name,
                    'standard': line.exam_id.standard.name or '',
                    'division': line.exam_id.division.name or '',
                })
