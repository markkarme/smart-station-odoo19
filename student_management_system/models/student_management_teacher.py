from odoo import models, fields

class Teacher(models.Model):
    _name = 'student.management.teacher'
    _description = 'Teacher Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Teacher Name', required=True)
    icon = fields.Image(string="Photo")
    contact_info = fields.Char(string='Contact Info')
    specialization = fields.Char(string='Specialization')
   # course_ids = fields.One2many('student.management.course', 'teacher_id', string='Courses')
    course_ids = fields.Many2many('student.management.course', 'teacher_course_rel', 'teacher_id', 'course_id', string='Courses')
