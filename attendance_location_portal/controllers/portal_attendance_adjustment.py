import logging
from urllib.parse import urlencode

from odoo import _, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager

_logger = logging.getLogger(__name__)

ADJUSTMENT_REQUEST_STATE_BADGES = {
    "confirm": "text-bg-warning",
    "approve": "text-bg-success",
    "refuse": "text-bg-danger",
}


def _get_adjustment_request_state_labels(env):
    return {
        "confirm": env._("To Approve"),
        "approve": env._("Approved"),
        "refuse": env._("Refused"),
    }


def _get_adjustment_request_type_labels(env):
    return {
        "early_departure": env._("Request for early departure"),
        "late_arrival": env._("Late arrival request"),
    }


class PortalAttendanceAdjustmentController(http.Controller):
    def _get_user_employee(self):
        employee = request.env.user.employee_id
        if not employee:
            employee = request.env.user.employee_ids[:1]
        return employee

    def _get_employee_adjustment_request(self, employee, request_id):
        adjustment_request = request.env["hr.attendance.adjustment.request"].sudo().browse(request_id)
        if not adjustment_request.exists() or adjustment_request.employee_id != employee:
            raise AccessError(_("This attendance adjustment request does not exist or is not accessible."))
        return adjustment_request

    @http.route(
        ["/my/attendance_adjustments", "/my/attendance_adjustments/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_attendance_adjustments(self, page=1, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return request.render(
                "attendance_location_portal.portal_attendance_adjustment_failed_page",
                {
                    "page_name": "portal_attendance_adjustment_failed",
                    "error_message": _(
                        "Your account is not linked to an employee record. "
                        "Please contact your administrator."
                    ),
                },
            )

        request_model = request.env["hr.attendance.adjustment.request"].sudo()
        domain = [("employee_id", "=", employee.id)]
        request_count = request_model.search_count(domain)
        pager = portal_pager(
            url="/my/attendance_adjustments",
            total=request_count,
            page=page,
            step=20,
        )
        adjustment_requests = request_model.search(
            domain,
            order="create_date desc",
            limit=20,
            offset=pager["offset"],
        )
        values = {
            "page_name": "portal_attendance_adjustments",
            "employee": employee,
            "adjustment_requests": adjustment_requests,
            "pager": pager,
            "request_state_labels": _get_adjustment_request_state_labels(request.env),
            "request_state_badges": ADJUSTMENT_REQUEST_STATE_BADGES,
            "request_type_labels": _get_adjustment_request_type_labels(request.env),
        }
        return request.render("attendance_location_portal.portal_my_attendance_adjustments", values)

    @http.route("/my/attendance_adjustments/new", type="http", auth="user", website=True)
    def portal_attendance_adjustment_new(self, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return request.render(
                "attendance_location_portal.portal_attendance_adjustment_failed_page",
                {
                    "page_name": "portal_attendance_adjustment_failed",
                    "error_message": _(
                        "Your account is not linked to an employee record. "
                        "Please contact your administrator."
                    ),
                },
            )

        values = {
            "page_name": "portal_attendance_adjustment_new",
            "employee": employee,
            "error_message": kwargs.get("error"),
            "form_values": kwargs,
            "request_type_labels": _get_adjustment_request_type_labels(request.env),
        }
        return request.render("attendance_location_portal.portal_attendance_adjustment_form", values)

    def _prepare_form_values(self, post):
        return {
            key: post.get(key)
            for key in ("request_type", "date", "time_minutes", "description")
            if post.get(key)
        }

    @http.route(
        "/my/attendance_adjustments/submit",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_attendance_adjustment_submit(self, **post):
        employee = self._get_user_employee()
        if not employee:
            params = urlencode({"error": _("No employee is linked to your user.")})
            return request.redirect("/my/attendance_adjustments/new?%s" % params)

        try:
            adjustment_request = employee.action_portal_create_attendance_adjustment(
                {
                    "request_type": post.get("request_type"),
                    "date": post.get("date"),
                    "time_minutes": post.get("time_minutes"),
                    "description": post.get("description"),
                }
            )
            return request.redirect("/my/attendance_adjustments/%s" % adjustment_request.id)
        except (UserError, AccessError) as error:
            params = urlencode({"error": str(error), **self._prepare_form_values(post)})
            return request.redirect("/my/attendance_adjustments/new?%s" % params)
        except Exception as error:
            _logger.exception("Portal attendance adjustment submit failed: %s", error)
            params = urlencode(
                {
                    "error": _("Unexpected error while submitting your request. Please try again."),
                    **self._prepare_form_values(post),
                }
            )
            return request.redirect("/my/attendance_adjustments/new?%s" % params)

    @http.route("/my/attendance_adjustments/<int:request_id>", type="http", auth="user", website=True)
    def portal_attendance_adjustment_detail(self, request_id, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return request.render(
                "attendance_location_portal.portal_attendance_adjustment_failed_page",
                {
                    "page_name": "portal_attendance_adjustment_failed",
                    "error_message": _(
                        "Your account is not linked to an employee record. "
                        "Please contact your administrator."
                    ),
                },
            )

        try:
            adjustment_request = self._get_employee_adjustment_request(employee, request_id)
        except AccessError:
            return request.render(
                "attendance_location_portal.portal_attendance_adjustment_failed_page",
                {
                    "page_name": "portal_attendance_adjustment_failed",
                    "error_message": _("This attendance adjustment request is not accessible."),
                },
            )

        values = {
            "page_name": "portal_attendance_adjustment_detail",
            "employee": employee,
            "adjustment_request": adjustment_request,
            "request_state_labels": _get_adjustment_request_state_labels(request.env),
            "request_state_badges": ADJUSTMENT_REQUEST_STATE_BADGES,
            "request_type_labels": _get_adjustment_request_type_labels(request.env),
            "success_message": kwargs.get("success"),
            "error_message": kwargs.get("error"),
        }
        return request.render("attendance_location_portal.portal_attendance_adjustment_detail", values)
