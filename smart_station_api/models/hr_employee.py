from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    website_user_id = fields.Many2one(
        'website.user',
        string='Website User',
        help='Linked website user account'
    )
    has_website_user = fields.Boolean(
        string='Has Website User',
        compute='_compute_has_website_user',
        store=True
    )

    @api.depends('website_user_id')
    def _compute_has_website_user(self):
        for employee in self:
            employee.has_website_user = bool(employee.website_user_id)

    def action_create_website_user(self):
        """Create website user for this employee."""
        self.ensure_one()
        
        if self.website_user_id:
            raise UserError(_('This employee already has a website user.'))
        
        if not self.work_email:
            raise UserError(_('Employee must have a work email to create a website user.'))
        
        # Open wizard to create user with password
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Website User'),
            'res_model': 'website.user.create.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_employee_id': self.id,
                'default_name': self.name,
                'default_login': self.work_email,
            },
        }

    def action_view_website_user(self):
        """View website user form."""
        self.ensure_one()
        
        if not self.website_user_id:
            raise UserError(_('This employee does not have a website user.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Website User'),
            'res_model': 'website.user',
            'view_mode': 'form',
            'res_id': self.website_user_id.id,
            'target': 'current',
        }
