import logging

from odoo import http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import content_disposition, request

from ..services.base import ApiContext, ApiError, to_int, user_message
from ..services.registry import FEATURES, TILES
from .main import BaseAPIController, require_token

_logger = logging.getLogger(__name__)

ROUTE = '/api/v1/portal/<string:key>/%s'
JSON_ROUTE = dict(type='jsonrpc', auth='public', methods=['POST'], csrf=False, cors='*')


class PortalApiMixin:
    """Helpers shared by the website API controllers (no routes)."""

    def _ctx(self, kwargs, website_user=None):
        website_user = website_user or request.env.context.get('website_user')
        return ApiContext(request.env, website_user, kwargs.get('lang'))

    def _feature(self, key):
        feature = FEATURES.get(key)
        if not feature:
            raise ApiError('Unknown page.', 404)
        return feature

    def _run(self, func):
        try:
            with request.env.cr.savepoint():
                return self._success_response(data=func())
        except ApiError as error:
            return self._error_response(error.message, error.code)
        except (UserError, ValidationError, AccessError) as error:
            return self._error_response(user_message(error), 400)
        except Exception as error:
            _logger.exception('Portal API error')
            return self._error_response(str(error) or 'Server error', 500)


class PortalAPIController(PortalApiMixin, BaseAPIController):
    """Generic endpoints serving every feature in services/registry.py."""

    @http.route('/api/v1/portal/home', **JSON_ROUTE)
    @require_token
    def home(self, **kwargs):
        def run():
            ctx = self._ctx(kwargs)
            return {
                'user': ctx.website_user.get_permissions(),
                'tiles': [tile.tile(ctx) for tile in TILES if tile.visible(ctx)],
            }
        return self._run(run)

    @http.route(ROUTE % 'list', **JSON_ROUTE)
    @require_token
    def list_records(self, key, **kwargs):
        return self._run(lambda: self._feature(key).list(
            self._ctx(kwargs), page=kwargs.get('page'), filterby=kwargs.get('filterby'),
            search=kwargs.get('search'), sortby=kwargs.get('sortby'), params=kwargs.get('params')))

    @http.route(ROUTE % 'list_action', **JSON_ROUTE)
    @require_token
    def list_action(self, key, **kwargs):
        def run():
            ctx, feature = self._ctx(kwargs), self._feature(key)
            feature.ensure_visible(ctx)
            feature.run_list_action(ctx, kwargs.get('action'), kwargs.get('params') or {})
            return {}
        return self._run(run)

    @http.route(ROUTE % 'record', **JSON_ROUTE)
    @require_token
    def record(self, key, **kwargs):
        def run():
            ctx, feature = self._ctx(kwargs), self._feature(key)
            return feature.detail(ctx, feature.check_record(ctx, kwargs.get('id')))
        return self._run(run)

    @http.route(ROUTE % 'form', **JSON_ROUTE)
    @require_token
    def form(self, key, **kwargs):
        def run():
            ctx, feature = self._ctx(kwargs), self._feature(key)
            feature.ensure_visible(ctx)
            if not feature.can_create(ctx):
                raise ApiError(ctx.t('You cannot create records here.', 'لا يمكنك إنشاء سجلات هنا.'), 403)
            return {'title': feature.tile(ctx)['title'], 'fields': feature.form(ctx, kwargs.get('values') or {})}
        return self._run(run)

    @http.route(ROUTE % 'create', **JSON_ROUTE)
    @require_token
    def create(self, key, **kwargs):
        def run():
            ctx, feature = self._ctx(kwargs), self._feature(key)
            feature.ensure_visible(ctx)
            if not feature.can_create(ctx):
                raise ApiError(ctx.t('You cannot create records here.', 'لا يمكنك إنشاء سجلات هنا.'), 403)
            return {'id': feature.create(ctx, kwargs.get('values') or {}).id}
        return self._run(run)

    @http.route(ROUTE % 'save', **JSON_ROUTE)
    @require_token
    def save(self, key, **kwargs):
        def run():
            ctx, feature = self._ctx(kwargs), self._feature(key)
            record = feature.check_record(ctx, kwargs.get('id'))
            feature.save(ctx, record, kwargs.get('values') or {})
            return feature.detail(ctx, record)
        return self._run(run)

    @http.route(ROUTE % 'lines', **JSON_ROUTE)
    @require_token
    def save_lines(self, key, **kwargs):
        def run():
            ctx, feature = self._ctx(kwargs), self._feature(key)
            record = feature.check_record(ctx, kwargs.get('id'))
            feature.save_lines(ctx, record, kwargs.get('block'), kwargs.get('rows') or [],
                               kwargs.get('new_rows') or [], kwargs.get('deleted') or [])
            return feature.detail(ctx, record)
        return self._run(run)

    @http.route(ROUTE % 'action', **JSON_ROUTE)
    @require_token
    def action(self, key, **kwargs):
        def run():
            ctx, feature = self._ctx(kwargs), self._feature(key)
            record = feature.check_record(ctx, kwargs.get('id'))
            allowed = {a['key'] for a in feature.actions(ctx, record)}
            for section in feature.sections(ctx, record):
                allowed |= {a['key'] for a in section.get('line_actions') or []}
            name = kwargs.get('action')
            if name not in allowed:
                raise ApiError(ctx.t('This action is not available.', 'هذا الإجراء غير متاح.'))
            result = feature.run_action(ctx, record, name, kwargs.get('params') or {}) or {}
            if isinstance(result, dict) and result.get('deleted'):
                return {'deleted': True}
            return feature.detail(ctx, record)
        return self._run(run)

    @http.route('/api/v1/portal/<string:key>/<int:record_id>/report/<string:report_key>',
                type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def report(self, key, record_id, report_key, token=None, lang=None, download=None, **kwargs):
        website_user = self._verify_token() or (token and request.env['api.access.token'].sudo().verify_token(token))
        if not website_user:
            return request.make_json_response(self._error_response('Unauthorized: Invalid or expired token', 401), status=401)
        try:
            ctx, feature = self._ctx({'lang': lang}, website_user), self._feature(key)
            record = feature.check_record(ctx, record_id)
            allowed = {r['key'] for r in feature.reports(ctx, record)}
            for section in feature.sections(ctx, record):
                allowed |= {f['key'] for f in section.get('files') or []}
            if report_key not in allowed:
                raise ApiError('Report not available.', 404)
            content, filename, mimetype = feature.report(ctx, record, report_key)
        except ApiError as error:
            return request.make_json_response(self._error_response(error.message, error.code), status=error.code)
        except Exception as error:
            _logger.exception('Portal report error')
            return request.make_json_response(self._error_response(user_message(error), 500), status=500)
        disposition = content_disposition(filename)
        if not download:
            disposition = disposition.replace('attachment', 'inline', 1)
        return request.make_response(content, headers=[('Content-Type', mimetype), ('Content-Disposition', disposition)])
