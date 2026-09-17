from odoo import models, fields



class Schedule(models.Model):
    _name = 'student.management.schedule'
    _description = 'Schedule Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    room_id = fields.Many2one('student.management.room', string='Room', required=True)
    course_id = fields.Many2one('student.management.course', string='Course', required=True)
    day = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday')
    ], string='Day', required=True)
    start_time = fields.Float(string='Start Time', required=True, help='Start time in 24-hour format, e.g., 9.0 for 9:00 AM')
    end_time = fields.Float(string='End Time', required=True, help='End time in 24-hour format, e.g., 11.0 for 11:00 AM')
