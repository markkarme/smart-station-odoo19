import logging
from urllib.parse import urlencode

from odoo import _, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager

_logger = logging.getLogger(__name__)

ALLOCATION_STATE_BADGES = {
    "confirm": "text-bg-warning",
    "validate1": "text-bg-info",
    "validate": "text-bg-success",
    "refuse": "text-bg-danger",
}


def _get_allocation_state_labels():
    return {
        "confirm": _("To Approve"),
        "validate1": _("Second Approval"),
        "validate": _("Approved"),
        "refuse": _("Refused"),
    }


class PortalAllocationController(http.Controller):
    def _get_user_employee(self):
        employee = request.env.user.employee_id
        if not employee:
            employee = request.env.user.employee_ids[:1]
        return employee

    def _get_employee_allocation(self, employee, allocation_id):
        allocation = request.env["hr.leave.allocation"].sudo().browse(allocation_id)
        if not allocation.exists() or allocation.employee_id != employee:
            raise AccessError(_("This allocation request does not exist or is not accessible."))
        return allocation

    def _prepare_allocation_type_data(self, employee, date_from=None):
        leave_types = employee._get_portal_allocation_types(date_from=date_from)
        return [
            {
                "id": leave_type.id,
                "name": leave_type.display_name,
                "request_unit": leave_type.request_unit,
                "allocation_validation_type": leave_type.allocation_validation_type,
            }
            for leave_type in leave_types
        ]

    def _prepare_form_values(self, post):
        return {
            key: post.get(key)
            for key in (
                "holiday_status_id",
                "date_from",
                "date_to",
                "allocation_amount",
                "notes",
            )
            if post.get(key)
        }

    @http.route(
        ["/my/allocations", "/my/allocations/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_allocations(self, page=1, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return request.render(
                "attendance_location_portal.portal_allocation_failed_page",
                {
                    "page_name": "portal_allocation_failed",
                    "error_message": _(
                        "Your account is not linked to an employee record. "
                        "Please contact your administrator."
                    ),
                },
            )

        allocation_model = request.env["hr.leave.allocation"].sudo()
        domain = [("employee_id", "=", employee.id)]
        allocation_count = allocation_model.search_count(domain)
        pager = portal_pager(
            url="/my/allocations",
            total=allocation_count,
            page=page,
            step=20,
        )
        allocations = allocation_model.search(
            domain,
            order="create_date desc",
            limit=20,
            offset=pager["offset"],
        )
        values = {
            "page_name": "portal_allocations",
            "employee": employee,
            "allocations": allocations,
            "pager": pager,
            "allocation_state_labels": _get_allocation_state_labels(),
            "allocation_state_badges": ALLOCATION_STATE_BADGES,
            "success_message": kwargs.get("success"),
            "error_message": kwargs.get("error"),
        }
        return request.render("attendance_location_portal.portal_my_allocations", values)

    @http.route("/my/allocations/new", type="http", auth="user", website=True)
    def portal_allocation_new(self, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return request.render(
                "attendance_location_portal.portal_allocation_failed_page",
                {
                    "page_name": "portal_allocation_failed",
                    "error_message": _(
                        "Your account is not linked to an employee record. "
                        "Please contact your administrator."
                    ),
                },
            )

        allocation_types = self._prepare_allocation_type_data(
            employee,
            date_from=kwargs.get("date_from"),
        )
        values = {
            "page_name": "portal_allocation_new",
            "employee": employee,
            "allocation_types": allocation_types,
            "error_message": kwargs.get("error"),
            "form_values": kwargs,
        }
        return request.render("attendance_location_portal.portal_allocation_form", values)

    @http.route(
        "/my/allocations/submit",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_allocation_submit(self, **post):
        employee = self._get_user_employee()
        if not employee:
            params = urlencode({"error": _("No employee is linked to your user.")})
            return request.redirect("/my/allocations/new?%s" % params)

        form_values = self._prepare_form_values(post)

        try:
            allocation = employee.action_portal_create_allocation(
                {
                    "holiday_status_id": post.get("holiday_status_id"),
                    "date_from": post.get("date_from"),
                    "date_to": post.get("date_to"),
                    "allocation_amount": post.get("allocation_amount"),
                    "notes": post.get("notes"),
                }
            )
            return request.redirect("/my/allocations/%s" % allocation.id)
        except (UserError, AccessError) as error:
            params = urlencode({"error": str(error), **form_values})
            return request.redirect("/my/allocations/new?%s" % params)
        except Exception as error:
            _logger.exception("Portal allocation submit failed: %s", error)
            params = urlencode(
                {
                    "error": _("Unexpected error while submitting allocation. Please try again."),
                    **form_values,
                }
            )
            return request.redirect("/my/allocations/new?%s" % params)

    @http.route("/my/allocations/<int:allocation_id>", type="http", auth="user", website=True)
    def portal_allocation_detail(self, allocation_id, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return request.render(
                "attendance_location_portal.portal_allocation_failed_page",
                {
                    "page_name": "portal_allocation_failed",
                    "error_message": _(
                        "Your account is not linked to an employee record. "
                        "Please contact your administrator."
                    ),
                },
            )

        try:
            allocation = self._get_employee_allocation(employee, allocation_id)
        except AccessError:
            return request.render(
                "attendance_location_portal.portal_allocation_failed_page",
                {
                    "page_name": "portal_allocation_failed",
                    "error_message": _("This allocation request is not accessible."),
                },
            )

        values = {
            "page_name": "portal_allocation_detail",
            "employee": employee,
            "allocation": allocation,
            "allocation_state_labels": _get_allocation_state_labels(),
            "allocation_state_badges": ALLOCATION_STATE_BADGES,
            "success_message": kwargs.get("success"),
            "error_message": kwargs.get("error"),
        }
        return request.render("attendance_location_portal.portal_allocation_detail", values)

    @http.route(
        "/my/allocations/<int:allocation_id>/cancel",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_allocation_cancel(self, allocation_id, **post):
        employee = self._get_user_employee()
        if not employee:
            params = urlencode({"error": _("No employee is linked to your user.")})
            return request.redirect("/my/allocations?%s" % params)

        try:
            allocation = self._get_employee_allocation(employee, allocation_id)
            employee.action_portal_cancel_allocation(allocation)
            params = urlencode({"success": _("Allocation request cancelled successfully.")})
            return request.redirect("/my/allocations?%s" % params)
        except (UserError, AccessError) as error:
            params = urlencode({"error": str(error)})
            return request.redirect("/my/allocations/%s?%s" % (allocation_id, params))
        except Exception as error:
            _logger.exception("Portal allocation cancel failed: %s", error)
            params = urlencode(
                {"error": _("Unexpected error while cancelling allocation. Please try again.")}
            )
            return request.redirect("/my/allocations/%s?%s" % (allocation_id, params))
