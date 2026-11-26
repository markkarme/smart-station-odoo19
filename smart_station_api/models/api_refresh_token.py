import secrets
from datetime import datetime, timedelta
from odoo import api, fields, models


class ApiRefreshToken(models.Model):
    _name = 'api.refresh.token'
    _description = 'API Refresh Token'
    _order = 'create_date desc'

    name = fields.Char(string='Token Name', compute='_compute_name', store=True)
    token = fields.Char(string='Refresh Token', required=True, index=True, readonly=True)
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
    device_id = fields.Char(string='Device ID', help='Unique device identifier')
    device_name = fields.Char(string='Device Name', help='User-friendly device name')
    ip_address = fields.Char(string='IP Address')
    user_agent = fields.Char(string='User Agent')
    active = fields.Boolean(default=True, index=True)
    last_used_at = fields.Datetime(string='Last Used At')
    access_token_ids = fields.One2many(
        'api.access.token',
        'refresh_token_id',
        string='Access Tokens'
    )

    _token_unique = models.Constraint('unique(token)', 'Refresh token must be unique!')

    @api.depends('website_user_id', 'device_name', 'create_date')
    def _compute_name(self):
        for record in self:
            if record.website_user_id and record.device_name:
                record.name = f"{record.website_user_id.name} - {record.device_name}"
            elif record.website_user_id:
                date_str = fields.Datetime.to_string(record.create_date or fields.Datetime.now())
                record.name = f"{record.website_user_id.name} - {date_str}"
            else:
                record.name = 'Unknown User'

    @api.model
    def generate_token(self, website_user_id, device_id=None, device_name=None, ip_address=None, user_agent=None):
        """Generate a new refresh token for a website user."""
        token = secrets.token_urlsafe(64)
        expires_at = fields.Datetime.now() + timedelta(days=30)  # 30 days expiry

        # If device_id provided, check if token already exists for this device
        if device_id:
            existing = self.search([
                ('website_user_id', '=', website_user_id),
                ('device_id', '=', device_id),
                ('active', '=', True)
            ], limit=1)
            if existing:
                # Update existing token
                existing.write({
                    'token': token,
                    'expires_at': expires_at,
                    'last_used_at': fields.Datetime.now(),
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                })
                return existing

        return self.create({
            'token': token,
            'website_user_id': website_user_id,
            'expires_at': expires_at,
            'device_id': device_id,
            'device_name': device_name,
            'ip_address': ip_address,
            'user_agent': user_agent,
        })

    @api.model
    def verify_token(self, token):
        """Verify if refresh token is valid and not expired."""
        refresh_token = self.search([
            ('token', '=', token),
            ('active', '=', True),
            ('expires_at', '>', fields.Datetime.now())
        ], limit=1)

        if refresh_token:
            refresh_token.write({'last_used_at': fields.Datetime.now()})
            return refresh_token
        return self.env['api.refresh.token']

    def invalidate(self):
        """Invalidate this refresh token and all associated access tokens."""
        self.access_token_ids.invalidate()
        self.write({'active': False})

    @api.model
    def cleanup_expired_tokens(self):
        """Cron job to clean up expired refresh tokens."""
        expired_tokens = self.search([
            ('expires_at', '<', fields.Datetime.now())
        ])
        expired_tokens.unlink()
