from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class WebsiteUserCreateWizard(models.TransientModel):
    _name = 'website.user.create.wizard'
    _description = 'Create Website User Wizard'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    name = fields.Char(string='Name', required=True)
    login = fields.Char(string='Login (Email)', required=True)
    password = fields.Char(string='Password', required=True)
    password_confirm = fields.Char(string='Confirm Password', required=True)
    access_right_ids = fields.Many2many(
        'website.access.right',
        string='Access Rights',
        required=True,
        help='Select access rights for this user'
    )
    
    @api.constrains('password', 'password_confirm')
    def _check_passwords_match(self):
        for wizard in self:
            if wizard.password != wizard.password_confirm:
                raise ValidationError(_('Passwords do not match!'))
    
    @api.constrains('password')
    def _check_password_strength(self):
        for wizard in self:
            if len(wizard.password) < 6:
                raise ValidationError(_('Password must be at least 6 characters long!'))

    def action_create_user(self):
        """Create website user."""
        self.ensure_one()
        
        # Check if employee already has a user
        if self.employee_id.website_user_id:
            raise UserError(_('This employee already has a website user.'))
        
        # Create website user
        website_user = self.env['website.user'].create({
            'name': self.name,
            'login': self.login,
            'password': self.password,
            'employee_id': self.employee_id.id,
            'access_right_ids': [(6, 0, self.access_right_ids.ids)],
        })
        
        # Link to employee
        self.employee_id.write({'website_user_id': website_user.id})
        
        # Return action to view created user
        return {
            'type': 'ir.actions.act_window',
            'name': _('Website User'),
            'res_model': 'website.user',
            'view_mode': 'form',
            'res_id': website_user.id,
            'target': 'current',
        }
