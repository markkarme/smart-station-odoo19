from odoo import http

from ..services.base import ApiError, serialize, to_float
from .main import BaseAPIController, require_token
from .portal_api import JSON_ROUTE, PortalApiMixin


class AttendanceAPIController(PortalApiMixin, BaseAPIController):
    """Take Attendance page (portal /my/attendance) with GPS range validation."""

    def _attendance_ctx(self, kwargs):
        ctx = self._ctx(kwargs)
        ctx.require('can_submit_attendance')
        if not ctx.employee:
            raise ApiError(ctx.t('Your account is not linked to an employee.', 'حسابك غير مرتبط بموظف.'), 403)
        return ctx

    def _today_rows(self, ctx):
        day = ctx.employee._portal_attendance_local_date()
        rows = ctx.env['hr.attendance'].search([('employee_id', '=', ctx.employee.id), ('date', '=', day)], order='id desc')
        return [{name: serialize(row, name) for name in ('id', 'check_in', 'check_out', 'worked_hours', 'attendance_location_id', 'portal_note')}
                for row in rows]

    @http.route('/api/v1/attendance/status', **JSON_ROUTE)
    @require_token
    def status(self, **kwargs):
        def run():
            ctx = self._attendance_ctx(kwargs)
            Location = ctx.env['attendance.location']
            locations = Location.search(Location._candidate_domain(ctx.employee))
            return {
                'employee': ctx.employee.name,
                'attendance_state': ctx.employee.attendance_state,
                'locations': [{'id': loc.id, 'name': loc.name, 'allowed_range_m': loc.allowed_range_m,
                               'google_maps_url': loc.google_maps_url or ''} for loc in locations],
                'today': self._today_rows(ctx),
            }
        return self._run(run)

    @http.route('/api/v1/attendance/check-location', **JSON_ROUTE)
    @require_token
    def check_location(self, **kwargs):
        def run():
            ctx = self._attendance_ctx(kwargs)
            if kwargs.get('latitude') is None or kwargs.get('longitude') is None:
                raise ApiError(ctx.t('Invalid GPS coordinates.', 'إحداثيات GPS غير صالحة.'))
            return ctx.env['attendance.location'].check_location_for_employee(
                ctx.employee, to_float(kwargs['latitude']), to_float(kwargs['longitude']))
        return self._run(run)

    @http.route('/api/v1/attendance/submit', **JSON_ROUTE)
    @require_token
    def submit(self, **kwargs):
        def run():
            ctx = self._attendance_ctx(kwargs)
            action = kwargs.get('action')
            if action not in ('check_in', 'check_out'):
                raise ApiError(ctx.t('Please choose check in or check out.', 'يرجى اختيار تسجيل حضور أو انصراف.'))
            if action == 'check_in' and not kwargs.get('force_check_in'):
                already = ctx.env['hr.attendance'].search_count([
                    ('employee_id', '=', ctx.employee.id),
                    ('date', '=', ctx.employee._portal_attendance_local_date()),
                    ('check_in', '!=', False),
                ])
                if already:
                    return {'needs_confirmation': True, 'message': ctx.t(
                        'You already checked in today. Do you want to check in again?',
                        'لقد قمت بتسجيل الحضور اليوم بالفعل. هل تريد تسجيل الحضور مرة أخرى؟')}
            result = ctx.employee.action_portal_attendance_change(
                kwargs.get('latitude'), kwargs.get('longitude'), attendance_action=action, note=kwargs.get('note'))
            location = result.get('location_name') or ''
            result['message'] = (ctx.t('Check in recorded at %s.', 'تم تسجيل الحضور في %s.') if action == 'check_in'
                                 else ctx.t('Check out recorded at %s.', 'تم تسجيل الانصراف في %s.')) % location
            result['today'] = self._today_rows(ctx)
            result['attendance_state'] = ctx.employee.attendance_state
            return result
        return self._run(run)
