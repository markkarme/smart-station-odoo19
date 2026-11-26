from odoo import api, fields, models, _

# Every boolean permission exposed to the website, grouped like the portal groups.
SELF_SERVICE_PERMISSIONS = [
    'can_submit_attendance',
    'can_view_attendance',
    'can_view_leave',
    'can_create_leave',
    'can_cancel_leave',
    'can_view_allocation',
    'can_create_allocation',
    'can_create_request',
    'can_create_adjustment',
    'can_view_payslips',
    'can_view_appraisals',
    'can_manage_appraisals',
    'can_view_profile',
    'can_update_profile',
]
PORTAL_ADMIN_PERMISSIONS = [
    'can_view_all_attendance',
    'can_approve_leave',
    'can_approve_request',
    'can_view_all_payslips',
    'can_view_absent_employees',
]
EDUCATION_PERMISSIONS = [
    'can_manage_student_attendance',
    'can_manage_student_exams',
    'can_manage_school_molds',
    'can_manage_violations',
    'can_view_job_descriptions',
]
ALL_PERMISSIONS = SELF_SERVICE_PERMISSIONS + PORTAL_ADMIN_PERMISSIONS + EDUCATION_PERMISSIONS + ['is_admin']


class WebsiteAccessRight(models.Model):
    _name = 'website.access.right'
    _description = 'Website Access Right'
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Char(string='Technical Code', required=True, index=True)
    description = fields.Text(string='Description', translate=True)
    active = fields.Boolean(string='Active', default=True)
    sequence = fields.Integer(string='Sequence', default=10)

    category = fields.Selection([
        ('attendance', 'Attendance'),
        ('leave', 'Time Off'),
        ('request', 'Requests'),
        ('employee', 'Employee Management'),
        ('admin', 'Administration'),
        ('student', 'Student Management'),
    ], string='Category', required=True, default='attendance')

    # Employee self-service (portal user)
    can_submit_attendance = fields.Boolean(string='Take Attendance', help='تسجيل الحضور')
    can_view_attendance = fields.Boolean(string='My Attendances', help='سجل حضوري')
    can_view_leave = fields.Boolean(string='My Time Off', help='إجازاتي')
    can_create_leave = fields.Boolean(string='Request Time Off')
    can_cancel_leave = fields.Boolean(string='Cancel Own Time Off')
    can_view_allocation = fields.Boolean(string='My Allocations', help='المخصصات')
    can_create_allocation = fields.Boolean(string='Request Allocation')
    can_create_request = fields.Boolean(string='General Requests', help='الطلبات العامة')
    can_create_adjustment = fields.Boolean(string='Attendance Adjustments', help='تعديلات الحضور')
    can_view_payslips = fields.Boolean(string='My Payslips', help='كشوف الرواتب')
    can_view_appraisals = fields.Boolean(string='Appraisals', help='التقييمات')
    can_manage_appraisals = fields.Boolean(string='Create / Edit Appraisals')
    can_view_profile = fields.Boolean(string='View Own Profile')
    can_update_profile = fields.Boolean(string='Update Own Profile / Photo')

    # Portal admin (group_portal_hr_admin), always limited to the user's allowed companies
    is_admin = fields.Boolean(
        string='Portal Admin',
        help='مسؤول البوابة: grants every permission in this tab for the allowed companies.',
    )
    can_view_all_attendance = fields.Boolean(string='All Attendances', help='كل سجلات الحضور')
    can_approve_leave = fields.Boolean(string='All Time Off & Allocations + Approve', help='كل الإجازات / كل المخصصات')
    can_approve_request = fields.Boolean(string='All Requests & Adjustments + Approve', help='كل الطلبات العامة / كل تعديلات الحضور')
    can_view_all_payslips = fields.Boolean(string='All Payslips')
    can_view_absent_employees = fields.Boolean(string='Absent Employees', help='الموظفون الغائبون')

    # Education admins (one per portal admin group)
    can_manage_student_attendance = fields.Boolean(string='Student Attendance Admin', help='مسؤول حضور البوابة')
    can_manage_student_exams = fields.Boolean(string='Student Exams Admin', help='مسؤول امتحانات البوابة')
    can_manage_school_molds = fields.Boolean(string='Exam Results Admin', help='مسؤول نتائج البوابة')
    can_manage_violations = fields.Boolean(string='Student Misconduct Admin', help='مسؤول مخالفات الطلاب ودراسات الحالة')
    can_view_job_descriptions = fields.Boolean(string='Job Descriptions Admin', help='مسؤول بوابة الوصف الوظيفي')

    user_ids = fields.Many2many(
        'website.user',
        'website_user_access_right_rel',
        'right_id',
        'user_id',
        string='Users'
    )
    user_count = fields.Integer(string='User Count', compute='_compute_user_count')

    _code_unique = models.Constraint('unique(code)', 'Code must be unique!')

    @api.depends('user_ids')
    def _compute_user_count(self):
        for right in self:
            right.user_count = len(right.user_ids)

    @api.onchange('is_admin')
    def _onchange_is_admin(self):
        if self.is_admin:
            for name in PORTAL_ADMIN_PERMISSIONS:
                self[name] = True

    @api.model
    def _create_default_access_rights(self):
        """Create one access right per portal group if it doesn't exist yet."""
        self_service = {name: True for name in SELF_SERVICE_PERMISSIONS}
        default_rights = [
            dict(self_service, name='Portal User', code='portal_user', category='attendance', sequence=10,
                 description='مستخدم البوابة: own attendance, time off, requests, payslips and appraisals.'),
            dict(self_service, name='Portal Admin', code='portal_admin', category='admin', sequence=20,
                 description='مسؤول البوابة: company-wide records and approvals.',
                 is_admin=True, **{name: True for name in PORTAL_ADMIN_PERMISSIONS}),
            dict(name='Student Attendance Admin', code='attendance_admin', category='student', sequence=30,
                 can_manage_student_attendance=True),
            dict(name='Student Exams Admin', code='exam_admin', category='student', sequence=40,
                 can_manage_student_exams=True),
            dict(name='Exam Results Admin', code='mold_admin', category='student', sequence=50,
                 can_manage_school_molds=True),
            dict(name='Student Misconduct Admin', code='misconduct_admin', category='student', sequence=70,
                 can_manage_violations=True),
            dict(name='Job Descriptions Admin', code='job_description_admin', category='employee', sequence=80,
                 can_view_job_descriptions=True),
        ]
        for right_data in default_rights:
            if not self.with_context(active_test=False).search_count([('code', '=', right_data['code'])]):
                self.create(right_data)

    def action_view_users(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Users with %s') % self.name,
            'res_model': 'website.user',
            'view_mode': 'list,form',
            'domain': [('access_right_ids', 'in', self.id)],
        }
