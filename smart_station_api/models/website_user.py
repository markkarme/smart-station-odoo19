import hashlib
import secrets
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from .website_access_right import ALL_PERMISSIONS, PORTAL_ADMIN_PERMISSIONS


class WebsiteUser(models.Model):
    _name = 'website.user'
    _description = 'Website User'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Name', required=True, tracking=True)
    login = fields.Char(string='Login (Email)', required=True, index=True, tracking=True)
    password = fields.Char(string='Password', required=True)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Linked Employee',
        required=True,
        ondelete='cascade',
        tracking=True,
        help='Employee record linked to this website user'
    )
    active = fields.Boolean(string='Active', default=True, tracking=True)
    
    # Access Rights
    access_right_ids = fields.Many2many(
        'website.access.right',
        'website_user_access_right_rel',
        'user_id',
        'right_id',
        string='Access Rights',
        tracking=True,
        help='Access rights granted to this user'
    )
    
    # Company access
    company_id = fields.Many2one(
        related='employee_id.company_id',
        string='Main Company',
        store=True,
        readonly=True
    )
    company_ids = fields.Many2many(
        related='employee_id.company_ids',
        string='Allowed Companies',
        readonly=True
    )
    
    # Profile
    avatar = fields.Image(
        string='Avatar',
        related='employee_id.image_1920',
        readonly=False
    )
    email = fields.Char(related='employee_id.work_email', string='Work Email', readonly=True)
    phone = fields.Char(related='employee_id.work_phone', string='Work Phone', readonly=True)
    department_id = fields.Many2one(related='employee_id.department_id', string='Department', readonly=True)
    job_id = fields.Many2one(related='employee_id.job_id', string='Job Position', readonly=True)
    
    # Token tracking
    api_access_token_ids = fields.One2many(
        'api.access.token',
        'website_user_id',
        string='API Access Tokens'
    )
    api_refresh_token_ids = fields.One2many(
        'api.refresh.token',
        'website_user_id',
        string='API Refresh Tokens'
    )
    active_token_count = fields.Integer(
        string='Active Tokens',
        compute='_compute_active_token_count'
    )
    last_login = fields.Datetime(string='Last Login', readonly=True)
    lang = fields.Selection(
        selection='_get_lang_selection',
        string='Website Language',
        default=lambda self: 'ar_001' if self.env['res.lang']._lang_get('ar_001') else 'en_US',
    )

    _login_unique = models.Constraint('unique(login)', 'Login (Email) must be unique!')
    _employee_unique = models.Constraint('unique(employee_id)', 'Employee can have only one website user!')

    @api.model
    def _get_lang_selection(self):
        return self.env['res.lang'].get_installed()

    @api.depends('api_access_token_ids.active', 'api_refresh_token_ids.active')
    def _compute_active_token_count(self):
        for user in self:
            user.active_token_count = len(user.api_access_token_ids.filtered('active')) + \
                                     len(user.api_refresh_token_ids.filtered('active'))

    @api.constrains('login')
    def _check_login_email(self):
        """Ensure login is a valid email."""
        import re
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        for user in self:
            if not re.match(email_regex, user.login):
                raise ValidationError(_('Login must be a valid email address.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Hash password before saving
            if 'password' in vals:
                vals['password'] = self._hash_password(vals['password'])
            
            # Set name from employee if not provided
            if 'employee_id' in vals and 'name' not in vals:
                employee = self.env['hr.employee'].browse(vals['employee_id'])
                vals['name'] = employee.name
            
            # Set login from employee email if not provided
            if 'employee_id' in vals and 'login' not in vals:
                employee = self.env['hr.employee'].browse(vals['employee_id'])
                if employee.work_email:
                    vals['login'] = employee.work_email
        
        users = super().create(vals_list)
        users._generate_initial_tokens()
        return users

    def _generate_initial_tokens(self, device_name='Initial Token'):
        """Create a refresh + access token pair for each user."""
        RefreshToken = self.env['api.refresh.token'].sudo()
        AccessToken = self.env['api.access.token'].sudo()
        for user in self:
            refresh_token = RefreshToken.generate_token(
                website_user_id=user.id,
                device_id=f'initial-{user.id}',
                device_name=device_name,
            )
            AccessToken.generate_token(
                website_user_id=user.id,
                refresh_token_id=refresh_token.id,
                user_agent=device_name,
            )
        return True

    def action_generate_tokens(self):
        """Manually generate a new access + refresh token pair."""
        self.ensure_one()
        self._generate_initial_tokens(device_name='Manual Token')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Tokens Generated'),
                'message': _('A new access token and refresh token were created. Open the Access Tokens tab to copy them.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def write(self, vals):
        # Hash password if being updated
        if 'password' in vals:
            vals['password'] = self._hash_password(vals['password'])
        return super().write(vals)

    @api.model
    def _hash_password(self, password):
        """Hash password using SHA-256."""
        if not password:
            return False
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def verify_password(self, password):
        """Verify password against stored hash."""
        self.ensure_one()
        if not password or not self.password:
            return False
        hashed = self._hash_password(password)
        return hashed == self.password

    @api.model
    def authenticate(self, login, password):
        """Authenticate user with login and password."""
        user = self.search([
            ('login', '=', login),
            ('active', '=', True)
        ], limit=1)
        
        if not user:
            return self.env['website.user']
        
        if user.verify_password(password):
            # Update last login
            user.sudo().write({'last_login': fields.Datetime.now()})
            return user
        
        return self.env['website.user']

    def invalidate_all_tokens(self):
        """Invalidate all API tokens for this user."""
        self.ensure_one()
        self.api_access_token_ids.write({'active': False})
        self.api_refresh_token_ids.write({'active': False})

    def _permission_flags(self):
        """Union of every boolean permission over the user's active access rights."""
        self.ensure_one()
        rights = self.access_right_ids.filtered('active')
        flags = {name: any(rights.mapped(name)) for name in ALL_PERMISSIONS}
        if flags['is_admin']:
            flags.update(dict.fromkeys(PORTAL_ADMIN_PERMISSIONS, True))
        return flags

    def get_permissions(self):
        """Profile + permissions payload returned to the website after login."""
        self.ensure_one()
        return {
            'user_id': self.id,
            'employee_id': self.employee_id.id,
            'name': self.name,
            'login': self.login,
            'email': self.email,
            'lang': self.lang or 'en_US',
            'job': self.job_id.name or '',
            'department': self.department_id.name or '',
            'company_id': self.company_id.id,
            'company_name': self.company_id.name or '',
            'company_ids': self.company_ids.ids,
            'access_rights': [
                {'code': right.code, 'name': right.name, 'category': right.category}
                for right in self.access_right_ids.filtered('active')
            ],
            'permissions': self._permission_flags(),
        }

    def action_reset_password(self):
        """Open wizard to reset password."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reset Password'),
            'res_model': 'website.user.password.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_user_id': self.id},
        }

    def action_view_tokens(self):
        """View all tokens for this user."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('API Tokens'),
            'res_model': 'api.access.token',
            'view_mode': 'list,form',
            'domain': [('website_user_id', '=', self.id)],
            'context': {
                'default_website_user_id': self.id,
                'search_default_active': 1,
            },
        }
