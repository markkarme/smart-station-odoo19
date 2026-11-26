from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class WebsiteUserPasswordWizard(models.TransientModel):
    _name = 'website.user.password.wizard'
    _description = 'Reset Website User Password Wizard'

    user_id = fields.Many2one('website.user', string='User', required=True)
    new_password = fields.Char(string='New Password', required=True)
    confirm_password = fields.Char(string='Confirm Password', required=True)
    
    @api.constrains('new_password', 'confirm_password')
    def _check_passwords_match(self):
        for wizard in self:
            if wizard.new_password != wizard.confirm_password:
                raise ValidationError(_('Passwords do not match!'))
    
    @api.constrains('new_password')
    def _check_password_strength(self):
        for wizard in self:
            if len(wizard.new_password) < 6:
                raise ValidationError(_('Password must be at least 6 characters long!'))

    def action_reset_password(self):
        """Reset user password."""
        self.ensure_one()
        
        # Update password
        self.user_id.write({'password': self.new_password})
        
        # Invalidate all existing tokens
        self.user_id.invalidate_all_tokens()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Password has been reset successfully. All existing tokens have been invalidated.'),
                'type': 'success',
                'sticky': False,
            }
        }
