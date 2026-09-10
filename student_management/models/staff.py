from odoo import models, fields


class Staff(models.Model):
    _name = 'staff.staff'
    _description = 'Staff'
    _inherit = ['base.person', 'mail.thread', 'mail.activity.mixin']
    _order = 'name'

    position = fields.Char(string='Position')
    salary = fields.Monetary(string='Salary', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
