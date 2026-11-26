import base64

from odoo import http
from odoo.tools.image import image_process

from ..services.base import ApiError, serialize
from .main import BaseAPIController, require_token
from .portal_api import JSON_ROUTE, PortalApiMixin

AVATAR_MIMETYPES = ('image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'image/gif')
AVATAR_MAX_BYTES = 5 * 1024 * 1024


class ProfileAPIController(PortalApiMixin, BaseAPIController):
    """My profile, photo, password and language (portal /my/account + /my/security)."""

    def _data_uri(self, image):
        if not image:
            return None
        image = image.decode() if isinstance(image, bytes) else image
        mimetype = 'image/svg+xml' if image.startswith('PD94') or image.startswith('PHN2') else 'image/png'
        return 'data:%s;base64,%s' % (mimetype, image)

    def _profile(self, ctx):
        employee = ctx.employee
        fields_ = ('name', 'job_id', 'department_id', 'parent_id', 'company_id', 'work_email', 'work_phone',
                   'mobile_phone', 'work_location_id', 'resource_calendar_id')
        return {
            'login': ctx.website_user.login,
            'lang': ctx.website_user.lang,
            'languages': [{'value': code, 'label': name} for code, name in ctx.env['res.lang'].get_installed()],
            'avatar': self._data_uri(employee.image_256),
            'can_update': ctx.can('can_update_profile'),
            'fields': [{'key': name, 'label': employee._fields[name].get_description(ctx.env)['string'],
                        'value': serialize(employee, name)} for name in fields_ if name in employee._fields],
        }

    @http.route('/api/v1/profile', **JSON_ROUTE)
    @require_token
    def profile(self, **kwargs):
        def run():
            ctx = self._ctx(kwargs)
            ctx.require('can_view_profile', 'can_update_profile')
            return self._profile(ctx)
        return self._run(run)

    @http.route('/api/v1/profile/avatar', **JSON_ROUTE)
    @require_token
    def avatar(self, **kwargs):
        def run():
            ctx = self._ctx(kwargs)
            ctx.require('can_update_profile')
            data = kwargs.get('image') or ''
            mimetype = kwargs.get('mimetype') or ''
            if ',' in data[:100]:
                header, data = data.split(',', 1)
                mimetype = mimetype or header[5:].split(';')[0]
            if mimetype not in AVATAR_MIMETYPES:
                raise ApiError(ctx.t('Please choose a PNG, JPG, WEBP or GIF image.', 'يرجى اختيار صورة PNG أو JPG أو WEBP أو GIF.'))
            raw = base64.b64decode(data or b'')
            if not raw:
                raise ApiError(ctx.t('Please choose an image file.', 'يرجى اختيار ملف صورة.'))
            if len(raw) > AVATAR_MAX_BYTES:
                raise ApiError(ctx.t('Maximum size is 5 MB.', 'الحد الأقصى للحجم 5 ميجابايت.'))
            image = base64.b64encode(image_process(raw, size=(1920, 1920)))
            ctx.employee.write({'image_1920': image})
            return self._profile(ctx)
        return self._run(run)

    @http.route('/api/v1/profile/password', **JSON_ROUTE)
    @require_token
    def password(self, **kwargs):
        def run():
            ctx = self._ctx(kwargs)
            user = ctx.website_user
            new = kwargs.get('new_password') or ''
            if not user.verify_password(kwargs.get('current_password') or ''):
                raise ApiError(ctx.t('Your current password is incorrect.', 'كلمة المرور الحالية غير صحيحة.'))
            if len(new) < 6:
                raise ApiError(ctx.t('The new password must have at least 6 characters.', 'يجب أن تتكون كلمة المرور الجديدة من 6 أحرف على الأقل.'))
            if new != kwargs.get('confirm_password'):
                raise ApiError(ctx.t('The passwords do not match.', 'كلمتا المرور غير متطابقتين.'))
            user.write({'password': new})
            return {}
        return self._run(run)

    @http.route('/api/v1/profile/lang', **JSON_ROUTE)
    @require_token
    def lang(self, **kwargs):
        def run():
            ctx = self._ctx(kwargs)
            lang = kwargs.get('value')
            if lang not in dict(ctx.env['res.lang'].get_installed()):
                raise ApiError('Unknown language.')
            ctx.website_user.write({'lang': lang})
            return {'lang': lang}
        return self._run(run)
