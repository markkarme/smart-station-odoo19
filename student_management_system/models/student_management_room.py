from odoo import models, fields


class Room(models.Model):
    _name = 'student.management.room'
    _description = 'Room Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Room Name', required=True)
    icon = fields.Image(string="Photo")
    capacity = fields.Integer(string='Capacity')
    branch_id = fields.Many2one(
        'student.management.branch', string='Branch',
        required=True, help="Branch to which this room belongs"
    )

