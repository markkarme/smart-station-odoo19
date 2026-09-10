from odoo import models, fields


class Course(models.Model):
    _name = 'student.management.course'
    _description = 'Course Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc' 

    name = fields.Char(string='Course Name', required=True)
    fee = fields.Monetary(string='Course Fee', required=True, currency_field='currency_id')
    duration = fields.Char(string='Duration')
    icon = fields.Image(string="Photo")
    teacher_id = fields.Many2one('student.management.teacher', string='Teacher')
    branch_id = fields.Many2one('student.management.branch', string='Branch', required=True)
    schedule_ids = fields.One2many('student.management.schedule', 'course_id', string='Schedules')
    teacher_id2 = fields.Many2many('student.management.teacher', 'teacher_course_rel', 'course_id', 'teacher_id', string='Related Teachers')
    currency_id = fields.Many2one(
        'res.currency', 
        string='Currency', 
        default=lambda self: self.env.company.currency_id.id,
        readonly=True
    )
