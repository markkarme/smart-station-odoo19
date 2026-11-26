import base64
import mimetypes

from odoo import fields

from .base import (
    ApiError, Feature, action, describe, record_options, selection_options,
    serialize, to_int, today,
)


def _decision_allowed(ctx, record, admin_permission, states, step_approvers):
    """Who may approve/refuse, mirroring the portal (_portal_can_decide + admin checks)."""
    if record.state not in states or record.employee_id == ctx.employee:
        return False
    company = record.company_id if 'company_id' in record._fields else record.employee_id.company_id
    if company and company.id not in ctx.company_ids:
        return False
    if record.employee_id.hr_responsible_ids:
        actor = ctx.employee.user_id
        return bool(actor) and actor in step_approvers(record)
    return ctx.can(admin_permission)


def _leave_managers(employee):
    return employee.leave_manager_ids | employee.leave_manager_id


class AttendanceFeature(Feature):
    key = 'attendances'
    model = 'hr.attendance'
    icon = 'attendance'
    sequence = 20
    permissions = ('can_view_attendance',)
    admin_permissions = ('can_view_all_attendance',)
    order = 'check_in desc'
    admin_list_fields = ('employee_id',)
    list_fields = ('date', 'check_in', 'check_out', 'worked_hours', 'attendance_location_id', 'portal_note')
    detail_fields = ('date', 'check_in', 'check_out', 'worked_hours', 'attendance_location_id', 'company_id', 'portal_note', 'portal_action_type')
    search_fields = ('portal_note', 'attendance_location_id.name')
    admin_search_fields = ('employee_id.name', 'company_id.name')

    def tile(self, ctx):
        tile = super().tile(ctx)
        if self.is_admin(ctx):
            tile.update(title=ctx.t('All Attendances', 'كل سجلات الحضور'),
                        subtitle=ctx.t('View all employees attendance', 'عرض سجل الحضور والانصراف لجميع الموظفين'))
        else:
            tile.update(title=ctx.t('My Attendances', 'سجل حضوري'),
                        subtitle=ctx.t('View your check-ins and check-outs', 'عرض سجل حضورك وانصرافك'))
        return tile

    def filters(self, ctx):
        result = [('all', ctx.t('All', 'الكل'), []),
                  ('checked_in', ctx.t('Checked In', 'حاضر حالياً'), [('check_out', '=', False)]),
                  ('completed', ctx.t('Completed', 'مكتمل'), [('check_out', '!=', False)])]
        for period, en, ar in (('today', 'Today', 'اليوم'), ('week', 'This Week', 'هذا الأسبوع'), ('month', 'This Month', 'هذا الشهر')):
            start, end = ctx.local_bounds(period)
            result.append((period, ctx.t(en, ar), [('check_in', '>=', start), ('check_in', '<=', end)]))
        return result + self.company_filters(ctx)

    def sortings(self, ctx):
        result = [('date', ctx.t('Newest', 'الأحدث'), 'check_in desc'),
                  ('date_asc', ctx.t('Oldest', 'الأقدم'), 'check_in asc'),
                  ('hours', ctx.t('Worked Hours', 'ساعات العمل'), 'worked_hours desc, check_in desc')]
        if self.is_admin(ctx):
            result.append(('employee', ctx.t('Employee', 'الموظف'), 'employee_id, check_in desc'))
        return result


class TimeOffFeature(Feature):
    key = 'time_off'
    model = 'hr.leave'
    title = ('Time Off', 'الإجازات')
    subtitle = ('Request time off and follow approvals', 'طلب الإجازات ومتابعة الموافقة')
    icon = 'time_off'
    sequence = 30
    permissions = ('can_view_leave', 'can_create_leave')
    admin_permissions = ('can_approve_leave',)
    order = 'create_date desc'
    admin_list_fields = ('employee_id',)
    list_fields = ('holiday_status_id', 'request_date_from', 'request_date_to', 'duration_display', 'private_name', 'state')
    detail_fields = ('holiday_status_id', 'request_date_from', 'request_date_to', 'duration_display', 'private_name', 'notes', 'validation_type', 'state')
    search_fields = ('holiday_status_id.name', 'private_name')
    admin_search_fields = ('employee_id.name',)

    def tile(self, ctx):
        tile = super().tile(ctx)
        if self.is_admin(ctx):
            tile.update(title=ctx.t('All Time Off', 'كل الإجازات'),
                        subtitle=ctx.t('Time off requests of all employees and approvals', 'عرض طلبات الإجازة لجميع الموظفين وحالة الموافقة'))
        return tile

    def filters(self, ctx):
        return [('all', ctx.t('All', 'الكل'), [])] + self.state_filters(ctx) + self.company_filters(ctx)

    def sortings(self, ctx):
        result = [('date', ctx.t('Newest', 'الأحدث'), 'create_date desc'),
                  ('date_from', ctx.t('Start Date', 'تاريخ البداية'), 'request_date_from desc, id desc'),
                  ('duration', ctx.t('Duration', 'المدة'), 'number_of_days desc, create_date desc')]
        if self.is_admin(ctx):
            result.append(('employee', ctx.t('Employee', 'الموظف'), 'employee_id, create_date desc'))
        return result

    def can_create(self, ctx):
        return ctx.can('can_create_leave')

    def _types(self, ctx, values):
        return ctx.employee._get_portal_leave_types(
            date_from=values.get('request_date_from') or None,
            date_to=values.get('request_date_to') or values.get('request_date_from') or None,
        )

    def form(self, ctx, values):
        Leave = ctx.env['hr.leave']
        types = self._types(ctx, values)
        options = []
        for leave_type in types:
            label = leave_type.display_name
            if leave_type.requires_allocation:
                label = '%s (%s %s)' % (label, round(leave_type.virtual_remaining_leaves, 2), ctx.t('remaining', 'متبقي'))
            options.append({'value': leave_type.id, 'label': label})
        selected = types.filtered(lambda t: t.id == to_int(values.get('holiday_status_id')))[:1]
        result = [
            describe(Leave, 'request_date_from', required=True, reload=True, value=values.get('request_date_from') or today(ctx)),
            describe(Leave, 'request_date_to', reload=True, value=values.get('request_date_to') or values.get('request_date_from') or today(ctx)),
            describe(Leave, 'holiday_status_id', type='many2one', options=options, required=True, reload=True),
        ]
        if selected.request_unit == 'half_day':
            result += [describe(Leave, 'request_date_from_period', value='am'), describe(Leave, 'request_date_to_period', value='pm')]
        elif selected.request_unit == 'hour':
            result += [describe(Leave, 'request_hour_from', type='time', required=True), describe(Leave, 'request_hour_to', type='time', required=True)]
        result += [
            describe(Leave, 'private_name', name='name', label=ctx.t('Description', 'الوصف')),
            describe(Leave, 'notes', type='text'),
            {'name': 'attachments', 'type': 'files', 'label': ctx.t('Supporting Document', 'المستند الداعم'), 'required': bool(selected.support_document)},
        ]
        return result

    def create(self, ctx, values):
        if not self.can_create(ctx):
            raise ApiError(ctx.t('You cannot request time off.', 'لا يمكنك طلب إجازة.'), 403)
        values = dict(values, attachments=self.attachments(values.get('attachments')))
        return ctx.employee.action_portal_create_leave(values)

    def _can_decide(self, ctx, leave, states):
        def approvers(record):
            if record.state == 'confirm':
                return record.employee_id.hr_responsible_ids
            return record._time_off_approver_users()
        return _decision_allowed(ctx, leave, 'can_approve_leave', states, approvers)

    def actions(self, ctx, record):
        result = []
        if self._can_decide(ctx, record, ('confirm', 'validate1')):
            result.append(action('approve', 'Approve', 'موافقة', ctx, 'success'))
        if self._can_decide(ctx, record, ('confirm', 'validate', 'validate1')):
            result.append(action('refuse', 'Refuse', 'رفض', ctx, 'danger', ctx.t('Refuse this request?', 'هل تريد رفض هذا الطلب؟')))
        if record.employee_id == ctx.employee and ctx.can('can_cancel_leave') and record.can_cancel:
            result.append(action('cancel', 'Cancel', 'إلغاء', ctx, 'danger', ctx.t('Cancel this time off?', 'هل تريد إلغاء هذه الإجازة؟')))
        return result

    def run_action(self, ctx, record, key, params):
        if key == 'approve' and self._can_decide(ctx, record, ('confirm', 'validate1')):
            leave = record.with_env(ctx.decision_env())
            leave.action_portal_admin_approve()
            leave.write({'second_approver_id' if leave.state == 'validate' and leave.validation_type == 'both' else 'first_approver_id': ctx.employee.id})
        elif key == 'refuse' and self._can_decide(ctx, record, ('confirm', 'validate', 'validate1')):
            record.with_env(ctx.decision_env()).action_portal_admin_refuse()
        elif key == 'cancel' and record.employee_id == ctx.employee and ctx.can('can_cancel_leave'):
            ctx.employee.action_portal_cancel_leave(record, reason=params.get('reason'))
        else:
            super().run_action(ctx, record, key, params)

    def sections(self, ctx, record):
        files = ctx.env['ir.attachment'].search([('res_model', '=', 'hr.leave'), ('res_id', '=', record.id)])
        if not files:
            return []
        return [{'type': 'files', 'label': ctx.t('Attachments', 'المرفقات'),
                 'files': [{'key': 'attachment_%s' % f.id, 'name': f.name} for f in files]}]

    def reports(self, ctx, record):
        return []

    def report(self, ctx, record, key):
        if key.startswith('attachment_'):
            attachment = ctx.env['ir.attachment'].search([('id', '=', to_int(key[11:])), ('res_model', '=', 'hr.leave'), ('res_id', '=', record.id)])
            if attachment:
                return base64.b64decode(attachment.datas or b''), attachment.name, attachment.mimetype or 'application/octet-stream'
        return super().report(ctx, record, key)


class AllocationFeature(Feature):
    key = 'allocations'
    model = 'hr.leave.allocation'
    title = ('Allocations', 'المخصصات')
    subtitle = ('Request additional time off days', 'طلب تخصيص أيام إجازة')
    icon = 'time_off'
    sequence = 35
    permissions = ('can_view_allocation', 'can_create_allocation')
    admin_permissions = ('can_approve_leave',)
    company_field = 'employee_company_id'
    order = 'create_date desc'
    admin_list_fields = ('employee_id',)
    list_fields = ('holiday_status_id', 'date_from', 'date_to', 'duration_display', 'notes', 'state')
    detail_fields = ('holiday_status_id', 'date_from', 'date_to', 'duration_display', 'notes', 'validation_type', 'state')
    search_fields = ('holiday_status_id.name', 'notes')
    admin_search_fields = ('employee_id.name',)

    def tile(self, ctx):
        tile = super().tile(ctx)
        if self.is_admin(ctx):
            tile.update(title=ctx.t('All Allocations', 'كل المخصصات'),
                        subtitle=ctx.t('Allocation requests of all employees', 'عرض طلبات المخصصات لجميع الموظفين وحالة الموافقة'))
        return tile

    def filters(self, ctx):
        return [('all', ctx.t('All', 'الكل'), [])] + self.state_filters(ctx) + self.company_filters(ctx)

    def can_create(self, ctx):
        return ctx.can('can_create_allocation')

    def form(self, ctx, values):
        Allocation = ctx.env['hr.leave.allocation']
        types = ctx.employee._get_portal_allocation_types(date_from=values.get('date_from') or None)
        selected = types.filtered(lambda t: t.id == to_int(values.get('holiday_status_id')))[:1]
        unit = ctx.t('Hours', 'ساعات') if selected.request_unit == 'hour' else ctx.t('Days', 'أيام')
        return [
            describe(Allocation, 'holiday_status_id', type='many2one', options=record_options(types), required=True, reload=True),
            describe(Allocation, 'date_from', required=True, value=values.get('date_from') or today(ctx)),
            describe(Allocation, 'date_to', required=False),
            {'name': 'allocation_amount', 'type': 'float', 'required': True, 'label': '%s (%s)' % (ctx.t('Allocation', 'التخصيص'), unit)},
            describe(Allocation, 'notes', type='text'),
        ]

    def create(self, ctx, values):
        if not self.can_create(ctx):
            raise ApiError(ctx.t('You cannot request allocations.', 'لا يمكنك طلب مخصصات.'), 403)
        return ctx.employee.action_portal_create_allocation(values)

    def _can_decide(self, ctx, record, states):
        def approvers(rec):
            return rec.employee_id.hr_responsible_ids if rec.state == 'confirm' else _leave_managers(rec.employee_id)
        return _decision_allowed(ctx, record, 'can_approve_leave', states, approvers)

    def actions(self, ctx, record):
        result = []
        if self._can_decide(ctx, record, ('confirm', 'validate1')):
            result.append(action('approve', 'Approve', 'موافقة', ctx, 'success'))
        if self._can_decide(ctx, record, ('confirm', 'validate', 'validate1')):
            result.append(action('refuse', 'Refuse', 'رفض', ctx, 'danger', ctx.t('Refuse this request?', 'هل تريد رفض هذا الطلب؟')))
        if record.employee_id == ctx.employee and record.state in ('confirm', 'refuse'):
            result.append(action('cancel', 'Delete Request', 'حذف الطلب', ctx, 'danger', ctx.t('Delete this request?', 'هل تريد حذف هذا الطلب؟')))
        return result

    def run_action(self, ctx, record, key, params):
        if key == 'approve' and self._can_decide(ctx, record, ('confirm', 'validate1')):
            allocation = record.with_env(ctx.decision_env())
            allocation.action_portal_admin_approve()
            allocation.write({'second_approver_id' if allocation.state == 'validate' else 'approver_id': ctx.employee.id})
        elif key == 'refuse' and self._can_decide(ctx, record, ('confirm', 'validate', 'validate1')):
            record.with_env(ctx.decision_env()).action_portal_admin_refuse()
        elif key == 'cancel' and record.employee_id == ctx.employee:
            ctx.employee.action_portal_cancel_allocation(record)
            return {'deleted': True}
        else:
            super().run_action(ctx, record, key, params)


class _RequestFeature(Feature):
    """General requests and attendance adjustments share the same approval flow."""
    admin_permissions = ('can_approve_request',)
    order = 'create_date desc'
    admin_list_fields = ('employee_id',)
    admin_search_fields = ('employee_id.name',)

    def filters(self, ctx):
        return [('all', ctx.t('All', 'الكل'), [])] + self.state_filters(ctx) + self.company_filters(ctx)

    def _can_decide(self, ctx, record):
        def approvers(rec):
            return rec.employee_id.hr_responsible_ids if rec.state == 'confirm' else _leave_managers(rec.employee_id)
        return _decision_allowed(ctx, record, 'can_approve_request', ('confirm', 'validate1'), approvers)

    def actions(self, ctx, record):
        if not self._can_decide(ctx, record):
            return []
        return [action('approve', 'Approve', 'موافقة', ctx, 'success'),
                action('refuse', 'Refuse', 'رفض', ctx, 'danger', ctx.t('Refuse this request?', 'هل تريد رفض هذا الطلب؟'))]

    def run_action(self, ctx, record, key, params):
        if key not in ('approve', 'refuse') or not self._can_decide(ctx, record):
            return super().run_action(ctx, record, key, params)
        target = record.with_env(ctx.decision_env())
        target.action_approve() if key == 'approve' else target.action_refuse()


class GeneralRequestFeature(_RequestFeature):
    key = 'general_requests'
    model = 'hr.general.request'
    title = ('General Requests', 'الطلبات العامة')
    subtitle = ('Submit general requests to HR', 'تقديم الطلبات العامة ومتابعة حالتها')
    icon = 'request'
    sequence = 40
    permissions = ('can_create_request',)
    list_fields = ('name', 'date', 'description', 'state')
    search_fields = ('name', 'description')

    def tile(self, ctx):
        tile = super().tile(ctx)
        if self.is_admin(ctx):
            tile.update(title=ctx.t('All General Requests', 'كل الطلبات العامة'),
                        subtitle=ctx.t('General requests of all employees', 'عرض الطلبات العامة لجميع الموظفين وحالة الموافقة'))
        return tile

    def can_create(self, ctx):
        return ctx.can('can_create_request')

    def form(self, ctx, values):
        return [describe(ctx.env[self.model], 'description', type='text', required=True)]

    def create(self, ctx, values):
        return ctx.employee.action_portal_create_general_request(values)


class AdjustmentFeature(_RequestFeature):
    key = 'attendance_adjustments'
    model = 'hr.attendance.adjustment.request'
    title = ('Attendance Adjustments', 'تعديلات الحضور')
    subtitle = ('Request late arrival or early departure', 'طلب تأخير أو انصراف مبكر')
    icon = 'attendance'
    sequence = 45
    permissions = ('can_create_adjustment',)
    list_fields = ('name', 'request_type', 'date', 'time_minutes', 'description', 'state')
    search_fields = ('name', 'description')

    def tile(self, ctx):
        tile = super().tile(ctx)
        if self.is_admin(ctx):
            tile.update(title=ctx.t('All Attendance Adjustments', 'كل تعديلات الحضور'),
                        subtitle=ctx.t('Adjustment requests of all employees', 'عرض طلبات تعديل الحضور لجميع الموظفين'))
        return tile

    def can_create(self, ctx):
        return ctx.can('can_create_adjustment')

    def form(self, ctx, values):
        Model = ctx.env[self.model]
        return [describe(Model, 'request_type', required=True), describe(Model, 'date', required=True, value=today(ctx)),
                describe(Model, 'time_minutes', required=True), describe(Model, 'description', type='text', required=True)]

    def create(self, ctx, values):
        return ctx.employee.action_portal_create_attendance_adjustment(values)


class PayslipFeature(Feature):
    key = 'payslips'
    model = 'hr.payslip'
    title = ('Payslips', 'كشوف الرواتب')
    subtitle = ('View your approved payslips', 'عرض كشوف الرواتب المعتمدة لشركاتك')
    icon = 'payslip'
    sequence = 50
    permissions = ('can_view_payslips',)
    admin_permissions = ('can_view_all_payslips',)
    order = 'date_from desc, id desc'
    admin_list_fields = ('employee_id',)
    list_fields = ('name', 'date_from', 'date_to', 'net_wage', 'state')
    search_fields = ('name',)
    admin_search_fields = ('employee_id.name',)

    def base_domain(self, ctx):
        return super().base_domain(ctx) + [('state', 'in', ('validated', 'paid'))]

    def reports(self, ctx, record):
        return [{'key': 'pdf', 'label': ctx.t('Download PDF', 'تحميل PDF'), 'preview': True}]

    def report(self, ctx, record, key):
        reports = record._get_pdf_reports()
        if key != 'pdf' or not reports:
            return super().report(ctx, record, key)
        return self.pdf_from_report(ctx, next(iter(reports)), record, '%s.pdf' % (record.name or 'payslip'))


class AppraisalFeature(Feature):
    key = 'appraisals'
    model = 'hr.appraisal'
    title = ('Appraisals', 'التقييمات')
    subtitle = ('Your appraisals and the ones you review', 'أكمل التقييمات وتابع حالتها')
    icon = 'appraisal'
    sequence = 55
    permissions = ('can_view_appraisals', 'can_manage_appraisals')
    order = 'date_close desc, id desc'
    list_fields = ('employee_id', 'date_close', 'manager_ids', 'state')
    detail_fields = ('employee_id', 'manager_ids', 'date_close', 'appraisal_template_id', 'state')
    search_fields = ('employee_id.name',)

    def base_domain(self, ctx):
        return ['|', ('employee_id', '=', ctx.employee.id), ('manager_ids', 'in', ctx.employee.ids)]

    def filters(self, ctx):
        return [('all', ctx.t('All', 'الكل'), [])] + self.state_filters(ctx)

    def can_create(self, ctx):
        return ctx.can('can_manage_appraisals')

    def _templates(self, ctx, subject):
        Template = ctx.env['hr.appraisal.template']
        templates = Template.search(['|', ('company_id', '=', False), ('company_id', '=', subject.company_id.id)], order='sequence, description, id')
        if subject.department_id and 'appraisal_template_ids' in subject.department_id._fields:
            dept = templates & subject.department_id.appraisal_template_ids
            templates = dept or templates
        return templates

    def form(self, ctx, values):
        Appraisal = ctx.env['hr.appraisal']
        employees = ctx.employee._get_portal_appraisal_employees()
        subject = employees.filtered(lambda e: e.id == to_int(values.get('employee_id'))) or ctx.employee
        templates = self._templates(ctx, subject)
        return [
            describe(Appraisal, 'employee_id', options=record_options(employees), required=True, reload=True, value=subject.id),
            describe(Appraisal, 'manager_ids', type='many2many', options=record_options(employees - subject),
                     value=subject._get_portal_appraisal_manager().ids),
            describe(Appraisal, 'date_close', required=True, value=today(ctx)),
            describe(Appraisal, 'appraisal_template_id', type='many2one', options=[{'value': t.id, 'label': t.description or t.display_name} for t in templates]),
        ]

    def create(self, ctx, values):
        if not self.can_create(ctx):
            raise ApiError(ctx.t('You cannot create appraisals.', 'لا يمكنك إنشاء تقييمات.'), 403)
        template = ctx.env['hr.appraisal.template'].browse(to_int(values.get('appraisal_template_id')))
        return ctx.employee.action_portal_create_appraisal({
            'employee_id': to_int(values.get('employee_id')) or ctx.employee.id,
            'manager_ids': [to_int(i) for i in values.get('manager_ids') or []],
            'date_close': values.get('date_close'),
            'appraisal_template_id': template if template.exists() else False,
        })

    def _roles(self, ctx, record):
        return record.employee_id == ctx.employee, ctx.employee in record.manager_ids

    def sections(self, ctx, record):
        is_employee, is_appraiser = self._roles(ctx, record)
        result = []
        if is_employee or record.employee_feedback_published or (is_appraiser and record.state == '1_new'):
            result.append({'type': 'html', 'label': ctx.t('Employee Feedback', 'تقييم الموظف'), 'html': record.employee_feedback or ''})
        if is_appraiser or record.manager_feedback_published:
            result.append({'type': 'html', 'label': ctx.t('Manager Feedback', 'تقييم المدير'), 'html': record.manager_feedback or ''})
        if is_appraiser and record.note:
            result.append({'type': 'html', 'label': ctx.t('Private Note', 'ملاحظة خاصة'), 'html': record.note})
        return result

    def edit_fields(self, ctx, record):
        if not ctx.can('can_manage_appraisals') or record.state == '3_done':
            return []
        is_employee, is_appraiser = self._roles(ctx, record)
        Appraisal = ctx.env['hr.appraisal']
        result = [describe(Appraisal, 'date_close')]
        if is_employee or (is_appraiser and record.state == '1_new'):
            result.append(describe(Appraisal, 'employee_feedback', type='html'))
            if is_employee and record.state == '2_pending':
                result.append(describe(Appraisal, 'employee_feedback_published'))
        if is_appraiser:
            result.append(describe(Appraisal, 'manager_feedback', type='html'))
            if record.state == '2_pending':
                result.append(describe(Appraisal, 'manager_feedback_published'))
            result.append(describe(Appraisal, 'note', type='html'))
        return result

    def save(self, ctx, record, values):
        allowed = {desc['name'] for desc in self.edit_fields(ctx, record)}
        record.action_portal_save(ctx.employee, {k: v for k, v in values.items() if k in allowed})

    def actions(self, ctx, record):
        _is_employee, is_appraiser = self._roles(ctx, record)
        if ctx.can('can_manage_appraisals') and is_appraiser and record.state == '1_new':
            return [action('confirm', 'Confirm', 'تأكيد', ctx, 'primary')]
        return []

    def run_action(self, ctx, record, key, params):
        if key == 'confirm' and ctx.can('can_manage_appraisals'):
            return record.action_portal_confirm(ctx.employee)
        return super().run_action(ctx, record, key, params)


class AbsentEmployeesFeature(Feature):
    key = 'absent_employees'
    model = 'hr.attendance.absent.report'
    title = ('Absent Employees', 'الموظفون الغائبون')
    subtitle = ('Absent, on leave or weekend employees for your companies', 'عرض الموظفين الغائبين أو في إجازة أو في عطلة نهاية الأسبوع أو العطل الرسمية لشركاتك')
    icon = 'absent'
    sequence = 60
    permissions = ('can_view_absent_employees',)
    order = 'date desc, employee_id'
    list_fields = ('date', 'employee_id', 'company_id', 'status')
    search_fields = ('employee_id.name',)
    state_field = 'status'

    def base_domain(self, ctx):
        return ctx.company_domain()

    def filters(self, ctx):
        return [('all', ctx.t('All', 'الكل'), [])] + self.state_filters(ctx)

    def sortings(self, ctx):
        return [('date', ctx.t('Date', 'التاريخ'), 'date desc, employee_id'),
                ('employee', ctx.t('Employee', 'الموظف'), 'employee_id, date desc'),
                ('status', ctx.t('Status', 'الحالة'), 'status, date desc')]

    def _range(self, ctx, params):
        date_from = params.get('date_from') or today(ctx)
        date_to = params.get('date_to') or today(ctx)
        return (date_to, date_from) if date_from > date_to else (date_from, date_to)

    def list_params(self, ctx):
        return [{'name': 'date_from', 'type': 'date', 'label': ctx.t('Date From', 'من تاريخ'), 'value': today(ctx)},
                {'name': 'date_to', 'type': 'date', 'label': ctx.t('Date To', 'إلى تاريخ'), 'value': today(ctx)}]

    def extra_list_domain(self, ctx, params):
        date_from, date_to = self._range(ctx, params)
        return [('date_from', '=', date_from), ('date_to', '=', date_to)]

    def list_actions(self, ctx):
        return [action('compute', 'Compute', 'احتساب', ctx, 'primary')]

    def run_list_action(self, ctx, key, params):
        if key != 'compute':
            return super().run_list_action(ctx, key, params)
        date_from, date_to = self._range(ctx, params)
        wizard = ctx.env['hr.attendance.absent.wizard'].create({'date_from': date_from, 'date_to': date_to})
        wizard.action_compute(company_ids=ctx.company_ids or False)


class JobDescriptionFeature(Feature):
    key = 'job_descriptions'
    model = 'hr.appraisal.job.description'
    title = ('Job Descriptions & KPIs', 'الوصف الوظيفي ومؤشرات الأداء')
    subtitle = ('Job description and KPI files for your companies', 'عرض ملفات الوصف الوظيفي ومؤشرات الأداء للشركات المسموح بها')
    icon = 'job'
    sequence = 70
    permissions = ('can_view_job_descriptions',)
    order = 'name, id'
    list_fields = ('name', 'file_name', 'company_id')
    search_fields = ('name', 'file_name')

    def base_domain(self, ctx):
        return ctx.company_domain(allow_empty=True)

    def sortings(self, ctx):
        return [('name', ctx.t('Name', 'الاسم'), 'name, id'), ('newest', ctx.t('Newest', 'الأحدث'), 'id desc')]

    def reports(self, ctx, record):
        if not record.file:
            return []
        previewable = (record.file_mimetype or '').startswith(('application/pdf', 'image/'))
        return [{'key': 'file', 'label': ctx.t('Download', 'تحميل'), 'preview': previewable}]

    def report(self, ctx, record, key):
        if key != 'file' or not record.file:
            return super().report(ctx, record, key)
        name = record.file_name or record.name or 'file'
        mimetype = record.file_mimetype or mimetypes.guess_type(name)[0] or 'application/octet-stream'
        return base64.b64decode(record.file), name, mimetype


class TakeAttendanceTile:
    """Tile only: the page uses the dedicated /attendance endpoints (GPS)."""
    key = 'take_attendance'
    sequence = 10

    def visible(self, ctx):
        return ctx.can('can_submit_attendance') and bool(ctx.employee)

    def tile(self, ctx):
        return {'key': self.key, 'title': ctx.t('Take Attendance', 'تسجيل الحضور'),
                'subtitle': ctx.t('Check in and check out from your allowed location', 'سجّل حضورك وانصرافك من موقعك المسموح به'),
                'icon': 'location', 'section': 'hr', 'route': '/attendance'}


class ProfileTile:
    key = 'profile'
    sequence = 5

    def visible(self, ctx):
        return ctx.can('can_view_profile', 'can_update_profile')

    def tile(self, ctx):
        return {'key': self.key, 'title': ctx.t('My Profile & Security', 'الملف الشخصي والأمان'),
                'subtitle': ctx.t('Your details, photo and password', 'بياناتك وصورتك وكلمة المرور'),
                'icon': 'profile', 'section': 'hr', 'route': '/profile'}
