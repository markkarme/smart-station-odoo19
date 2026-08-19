import base64
import logging
from urllib.parse import urlencode

from odoo import _, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager

_logger = logging.getLogger(__name__)

LEAVE_STATE_BADGES = {
    "confirm": "text-bg-warning",
    "validate1": "text-bg-info",
    "validate": "text-bg-success",
    "refuse": "text-bg-danger",
    "cancel": "text-bg-secondary",
}


def _get_leave_state_labels():
    return {
        "confirm": _("To Approve"),
        "validate1": _("Second Approval"),
        "validate": _("Approved"),
        "refuse": _("Refused"),
        "cancel": _("Cancelled"),
    }


class PortalTimeOffController(http.Controller):
    def _get_user_employee(self):
        employee = request.env.user.employee_id
        if not employee:
            employee = request.env.user.employee_ids[:1]
        return employee

    def _get_employee_leave(self, employee, leave_id):
        leave = request.env["hr.leave"].sudo().browse(leave_id)
        if not leave.exists() or leave.employee_id != employee:
            raise AccessError(_("This time off request does not exist or is not accessible."))
        return leave

    def _prepare_leave_type_data(self, employee, date_from=None, date_to=None):
        leave_types = employee._get_portal_leave_types(date_from=date_from, date_to=date_to)
        result = []
        for leave_type in leave_types:
            result.append(
                {
                    "id": leave_type.id,
                    "name": leave_type.name,
                    "label": leave_type.display_name,
                    "request_unit": leave_type.request_unit,
                    "support_document": leave_type.support_document,
                    "requires_allocation": leave_type.requires_allocation,
                    "virtual_remaining_leaves": leave_type.virtual_remaining_leaves,
                }
            )
        return result

    def _prepare_attachments(self):
        attachments = []
        files = request.httprequest.files.getlist("attachments")
        for uploaded_file in files:
            if not uploaded_file or not uploaded_file.filename:
                continue
            attachments.append(
                {
                    "name": uploaded_file.filename,
                    "datas": base64.b64encode(uploaded_file.read()),
                }
            )
        return attachments

    @http.route(
        ["/my/time_off", "/my/time_off/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_time_off(self, page=1, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return request.render(
                "attendance_location_portal.portal_time_off_failed_page",
                {
                    "page_name": "portal_time_off_failed",
                    "error_message": _(
                        "Your account is not linked to an employee record. "
                        "Please contact your administrator."
                    ),
                },
            )

        leave_model = request.env["hr.leave"].sudo()
        domain = [("employee_id", "=", employee.id)]
        leave_count = leave_model.search_count(domain)
        pager = portal_pager(
            url="/my/time_off",
            total=leave_count,
            page=page,
            step=20,
        )
        leaves = leave_model.search(
            domain,
            order="create_date desc",
            limit=20,
            offset=pager["offset"],
        )
        values = {
            "page_name": "portal_time_off",
            "employee": employee,
            "leaves": leaves,
            "pager": pager,
            "leave_state_labels": _get_leave_state_labels(),
            "leave_state_badges": LEAVE_STATE_BADGES,
        }
        return request.render("attendance_location_portal.portal_my_time_off", values)

    @http.route("/my/time_off/new", type="http", auth="user", website=True)
    def portal_time_off_new(self, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return request.render(
                "attendance_location_portal.portal_time_off_failed_page",
                {
                    "page_name": "portal_time_off_failed",
                    "error_message": _(
                        "Your account is not linked to an employee record. "
                        "Please contact your administrator."
                    ),
                },
            )

        leave_types = self._prepare_leave_type_data(
            employee,
            date_from=kwargs.get("request_date_from"),
            date_to=kwargs.get("request_date_to"),
        )
        values = {
            "page_name": "portal_time_off_new",
            "employee": employee,
            "leave_types": leave_types,
            "error_message": kwargs.get("error"),
            "form_values": kwargs,
        }
        return request.render("attendance_location_portal.portal_time_off_form", values)

    def _prepare_form_values(self, post):
        return {
            key: post.get(key)
            for key in (
                "holiday_status_id",
                "request_date_from",
                "request_date_to",
                "request_date_from_period",
                "request_date_to_period",
                "request_hour_from",
                "request_hour_to",
                "name",
                "notes",
            )
            if post.get(key)
        }

    @http.route(
        "/my/time_off/submit",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_time_off_submit(self, **post):
        employee = self._get_user_employee()
        if not employee:
            params = urlencode({"error": _("No employee is linked to your user.")})
            return request.redirect("/my/time_off/new?%s" % params)

        try:
            leave = employee.action_portal_create_leave(
                {
                    "holiday_status_id": post.get("holiday_status_id"),
                    "request_date_from": post.get("request_date_from"),
                    "request_date_to": post.get("request_date_to"),
                    "request_date_from_period": post.get("request_date_from_period"),
                    "request_date_to_period": post.get("request_date_to_period"),
                    "request_hour_from": post.get("request_hour_from"),
                    "request_hour_to": post.get("request_hour_to"),
                    "name": post.get("name"),
                    "notes": post.get("notes"),
                    "attachments": self._prepare_attachments(),
                }
            )
            return request.redirect("/my/time_off/%s" % leave.id)
        except (UserError, AccessError) as error:
            params = urlencode({"error": str(error), **self._prepare_form_values(post)})
            return request.redirect("/my/time_off/new?%s" % params)
        except Exception as error:
            _logger.exception("Portal time off submit failed: %s", error)
            params = urlencode(
                {
                    "error": _("Unexpected error while submitting time off. Please try again."),
                    **self._prepare_form_values(post),
                }
            )
            return request.redirect("/my/time_off/new?%s" % params)

    @http.route("/my/time_off/<int:leave_id>", type="http", auth="user", website=True)
    def portal_time_off_detail(self, leave_id, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return request.render(
                "attendance_location_portal.portal_time_off_failed_page",
                {
                    "page_name": "portal_time_off_failed",
                    "error_message": _(
                        "Your account is not linked to an employee record. "
                        "Please contact your administrator."
                    ),
                },
            )

        try:
            leave = self._get_employee_leave(employee, leave_id)
        except AccessError:
            return request.render(
                "attendance_location_portal.portal_time_off_failed_page",
                {
                    "page_name": "portal_time_off_failed",
                    "error_message": _("This time off request is not accessible."),
                },
            )

        values = {
            "page_name": "portal_time_off_detail",
            "employee": employee,
            "leave": leave,
            "leave_state_labels": _get_leave_state_labels(),
            "leave_state_badges": LEAVE_STATE_BADGES,
            "success_message": kwargs.get("success"),
            "error_message": kwargs.get("error"),
        }
        return request.render("attendance_location_portal.portal_time_off_detail", values)

    @http.route(
        "/my/time_off/<int:leave_id>/cancel",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_time_off_cancel(self, leave_id, **post):
        employee = self._get_user_employee()
        if not employee:
            params = urlencode({"error": _("No employee is linked to your user.")})
            return request.redirect("/my/time_off?%s" % params)

        try:
            leave = self._get_employee_leave(employee, leave_id)
            employee.action_portal_cancel_leave(leave, reason=post.get("cancel_reason"))
            params = urlencode({"success": _("Time off request cancelled successfully.")})
            return request.redirect("/my/time_off/%s?%s" % (leave.id, params))
        except (UserError, AccessError) as error:
            params = urlencode({"error": str(error)})
            return request.redirect("/my/time_off/%s?%s" % (leave_id, params))
        except Exception as error:
            _logger.exception("Portal time off cancel failed: %s", error)
            params = urlencode(
                {"error": _("Unexpected error while cancelling time off. Please try again.")}
            )
            return request.redirect("/my/time_off/%s?%s" % (leave_id, params))
