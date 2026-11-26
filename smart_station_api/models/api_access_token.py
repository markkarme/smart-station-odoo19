import secrets
from datetime import datetime, timedelta
from odoo import api, fields, models


class ApiAccessToken(models.Model):
    _name = 'api.access.token'
    _description = 'API Access Token'
    _order = 'create_date desc'

    name = fields.Char(string='Token Name', compute='_compute_name', store=True)
    token = fields.Char(string='Access Token', required=True, index=True, readonly=True)
    website_user_id = fields.Many2one(
        'website.user',
        string='Website User',
        required=True,
        ondelete='cascade',
        index=True
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        related='website_user_id.employee_id',
        store=True
    )
    expires_at = fields.Datetime(string='Expires At', required=True, index=True)
    ip_address = fields.Char(string='IP Address')
    user_agent = fields.Char(string='User Agent')
    active = fields.Boolean(default=True, index=True)
    refresh_token_id = fields.Many2one(
        'api.refresh.token',
        string='Refresh Token',
        ondelete='cascade'
    )

    _token_unique = models.Constraint('unique(token)', 'Token must be unique!')

    @api.depends('website_user_id', 'create_date')
    def _compute_name(self):
        for record in self:
            if record.website_user_id:
                date_str = fields.Datetime.to_string(record.create_date or fields.Datetime.now())
                record.name = f"{record.website_user_id.name} - {date_str}"
            else:
                record.name = 'Unknown User'

    @api.model
    def generate_token(self, website_user_id, ip_address=None, user_agent=None, refresh_token_id=None):
        """Generate a new access token for a website user."""
        token = secrets.token_urlsafe(64)
        expires_at = fields.Datetime.now() + timedelta(hours=1)  # 1 hour expiry

        return self.create({
            'token': token,
            'website_user_id': website_user_id,
            'expires_at': expires_at,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'refresh_token_id': refresh_token_id,
        })

    @api.model
    def verify_token(self, token):
        """Verify if token is valid and not expired."""
        access_token = self.search([
            ('token', '=', token),
            ('active', '=', True),
            ('expires_at', '>', fields.Datetime.now())
        ], limit=1)

        if access_token:
            return access_token.website_user_id
        return self.env['website.user']

    def invalidate(self):
        """Invalidate this access token."""
        self.write({'active': False})

    @api.model
    def cleanup_expired_tokens(self):
        """Cron job to clean up expired tokens."""
        expired_tokens = self.search([
            ('expires_at', '<', fields.Datetime.now())
        ])
        expired_tokens.unlink()
