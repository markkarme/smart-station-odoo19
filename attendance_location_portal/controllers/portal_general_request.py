import logging
from urllib.parse import urlencode

from odoo import _, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager

_logger = logging.getLogger(__name__)

GENERAL_REQUEST_STATE_BADGES = {
    "confirm": "text-bg-warning",
    "approve": "text-bg-success",
    "refuse": "text-bg-danger",
}


def _get_general_request_state_labels(env):
    return {
        "confirm": env._("To Approve"),
        "approve": env._("Approved"),
        "refuse": env._("Refused"),
    }


class PortalGeneralRequestController(http.Controller):
    def _get_user_employee(self):
        employee = request.env.user.employee_id
        if not employee:
            employee = request.env.user.employee_ids[:1]
        return employee

    def _get_employee_general_request(self, employee, request_id):
        general_request = request.env["hr.general.request"].sudo().browse(request_id)
        if not general_request.exists() or general_request.employee_id != employee:
            raise AccessError(_("This general request does not exist or is not accessible."))
        return general_request

    @http.route(
        ["/my/general_requests", "/my/general_requests/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_general_requests(self, page=1, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return request.render(
                "attendance_location_portal.portal_general_request_failed_page",
                {
                    "page_name": "portal_general_request_failed",
                    "error_message": _(
                        "Your account is not linked to an employee record. "
                        "Please contact your administrator."
                    ),
                },
            )

        request_model = request.env["hr.general.request"].sudo()
        domain = [("employee_id", "=", employee.id)]
        request_count = request_model.search_count(domain)
        pager = portal_pager(
            url="/my/general_requests",
            total=request_count,
            page=page,
            step=20,
        )
        general_requests = request_model.search(
            domain,
            order="create_date desc",
            limit=20,
            offset=pager["offset"],
        )
        values = {
            "page_name": "portal_general_requests",
            "employee": employee,
            "general_requests": general_requests,
            "pager": pager,
            "request_state_labels": _get_general_request_state_labels(request.env),
            "request_state_badges": GENERAL_REQUEST_STATE_BADGES,
        }
        return request.render("attendance_location_portal.portal_my_general_requests", values)

    @http.route("/my/general_requests/new", type="http", auth="user", website=True)
    def portal_general_request_new(self, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return request.render(
                "attendance_location_portal.portal_general_request_failed_page",
                {
                    "page_name": "portal_general_request_failed",
                    "error_message": _(
                        "Your account is not linked to an employee record. "
                        "Please contact your administrator."
                    ),
                },
            )

        values = {
            "page_name": "portal_general_request_new",
            "employee": employee,
            "error_message": kwargs.get("error"),
            "form_values": kwargs,
        }
        return request.render("attendance_location_portal.portal_general_request_form", values)

    @http.route(
        "/my/general_requests/submit",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_general_request_submit(self, **post):
        employee = self._get_user_employee()
        if not employee:
            params = urlencode({"error": _("No employee is linked to your user.")})
            return request.redirect("/my/general_requests/new?%s" % params)

        try:
            general_request = employee.action_portal_create_general_request(
                {"description": post.get("description")}
            )
            return request.redirect("/my/general_requests/%s" % general_request.id)
        except (UserError, AccessError) as error:
            params = urlencode(
                {
                    "error": str(error),
                    "description": post.get("description") or "",
                }
            )
            return request.redirect("/my/general_requests/new?%s" % params)
        except Exception as error:
            _logger.exception("Portal general request submit failed: %s", error)
            params = urlencode(
                {
                    "error": _("Unexpected error while submitting your request. Please try again."),
                    "description": post.get("description") or "",
                }
            )
            return request.redirect("/my/general_requests/new?%s" % params)

    @http.route("/my/general_requests/<int:request_id>", type="http", auth="user", website=True)
    def portal_general_request_detail(self, request_id, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return request.render(
                "attendance_location_portal.portal_general_request_failed_page",
                {
                    "page_name": "portal_general_request_failed",
                    "error_message": _(
                        "Your account is not linked to an employee record. "
                        "Please contact your administrator."
                    ),
                },
            )

        try:
            general_request = self._get_employee_general_request(employee, request_id)
        except AccessError:
            return request.render(
                "attendance_location_portal.portal_general_request_failed_page",
                {
                    "page_name": "portal_general_request_failed",
                    "error_message": _("This general request is not accessible."),
                },
            )

        values = {
            "page_name": "portal_general_request_detail",
            "employee": employee,
            "general_request": general_request,
            "request_state_labels": _get_general_request_state_labels(request.env),
            "request_state_badges": GENERAL_REQUEST_STATE_BADGES,
            "success_message": kwargs.get("success"),
            "error_message": kwargs.get("error"),
        }
        return request.render("attendance_location_portal.portal_general_request_detail", values)
