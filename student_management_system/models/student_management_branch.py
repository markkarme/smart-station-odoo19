from odoo import models, fields

class StudentManagementBranch(models.Model):
    _name = 'student.management.branch'
    _description = 'Branch'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Branch Name", required=True)
    location = fields.Char(string='Location')
    contact_info = fields.Char(string='Contact Info')
    icon = fields.Image(string="Photo")
    room_ids = fields.One2many(
        'student.management.room', 'branch_id', string='Rooms',
        help="List of rooms in this branch"
    )