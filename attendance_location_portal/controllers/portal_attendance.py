from urllib.parse import urlencode
import logging

from odoo import _, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager

_logger = logging.getLogger(__name__)


class PortalAttendanceController(http.Controller):
    def _get_user_employee(self):
        employee = request.env.user.employee_id
        if not employee:
            employee = request.env.user.employee_ids[:1]
        return employee

    @http.route(
        "/my/attendance/check_location",
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_attendance_check_location(self, latitude=None, longitude=None, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return request.make_json_response(
                {
                    "allowed": False,
                    "message": _("No employee is linked to your user."),
                    "location_names": [],
                }
            )
        try:
            lat = float(latitude)
            lon = float(longitude)
        except (TypeError, ValueError):
            return request.make_json_response(
                {
                    "allowed": False,
                    "message": _("Invalid GPS coordinates received from your device."),
                    "location_names": [],
                }
            )

        # Keep website/frontend lang (e.g. /ar/) so _() matches the portal UI language,
        # not only res.users.lang (often en_US for portal users).
        Location = request.env["attendance.location"].sudo()
        result = Location.check_location_for_employee(employee, lat, lon)
        return request.make_json_response(result)

    @http.route("/my/attendance", type="http", auth="user", website=True)
    def portal_attendance_page(self, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            values = {
                "error_message": _(
                    "Your account is not linked to an employee record. "
                    "Please contact your administrator."
                )
            }
            return request.render(
                "attendance_location_portal.portal_attendance_failed_page", values
            )

        locations = request.env["attendance.location"].sudo().search(
            request.env["attendance.location"]._candidate_domain(employee)
        )
        values = {
            "page_name": "portal_attendance",
            "employee": employee,
            "attendance_state": employee.attendance_state,
            "locations": locations,
        }
        return request.render(
            "attendance_location_portal.portal_attendance_page",
            values,
        )

    @http.route(
        "/my/attendance/submit",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_attendance_submit(self, **post):
        employee = self._get_user_employee()
        if not employee:
            params = urlencode({"reason": _("No employee is linked to your user.")})
            return request.redirect("/my/attendance/failed?%s" % params)

        try:
            latitude = post.get("latitude")
            longitude = post.get("longitude")
            note = post.get("note")
            result = employee.sudo().action_portal_attendance_change(
                latitude, longitude, note=note
            )
            params = urlencode(
                {
                    "action": result["action"],
                    "location": result["location_name"],
                }
            )
            return request.redirect("/my/attendance/success?%s" % params)
        except UserError as error:
            params = urlencode({"reason": str(error)})
            return request.redirect("/my/attendance/failed?%s" % params)
        except Exception as error:
            _logger.exception("Portal attendance submit failed: %s", error)
            params = urlencode(
                {
                    "reason": _(
                        "Unexpected error while recording attendance. Please try again."
                    )
                }
            )
            return request.redirect("/my/attendance/failed?%s" % params)

    @http.route("/my/attendance/success", type="http", auth="user", website=True)
    def portal_attendance_success(self, **kwargs):
        values = {
            "page_name": "portal_attendance_success",
            "action": kwargs.get("action") or "check_in",
            "location": kwargs.get("location") or _("Unknown"),
        }
        return request.render(
            "attendance_location_portal.portal_attendance_success_page",
            values,
        )

    @http.route("/my/attendance/failed", type="http", auth="user", website=True)
    def portal_attendance_failed(self, **kwargs):
        values = {
            "page_name": "portal_attendance_failed",
            "error_message": kwargs.get("reason") or _("Attendance request failed."),
        }
        return request.render(
            "attendance_location_portal.portal_attendance_failed_page",
            values,
        )

    @http.route(
        ["/my/attendances", "/my/attendances/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_attendances(self, page=1, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            values = {
                "error_message": _(
                    "Your account is not linked to an employee record. "
                    "Please contact your administrator."
                )
            }
            return request.render(
                "attendance_location_portal.portal_attendance_failed_page", values
            )

        attendance_model = request.env["hr.attendance"].sudo()
        domain = [("employee_id", "=", employee.id)]
        attendance_count = attendance_model.search_count(domain)
        pager = portal_pager(
            url="/my/attendances",
            total=attendance_count,
            page=page,
            step=20,
        )
        attendances = attendance_model.search(
            domain,
            order="check_in desc",
            limit=20,
            offset=pager["offset"],
        )
        values = {
            "page_name": "portal_attendance_history",
            "employee": employee,
            "attendances": attendances,
            "pager": pager,
        }
        return request.render(
            "attendance_location_portal.portal_my_attendances",
            values,
        )
