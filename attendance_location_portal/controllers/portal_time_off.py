import base64
import logging
from urllib.parse import urlencode

from odoo import _, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager

from .portal_common import PortalHrMixin

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


class PortalTimeOffController(PortalHrMixin, http.Controller):
    def _get_employee_leave(self, employee, leave_id):
        leave = request.env["hr.leave"].sudo().browse(leave_id)
        if not leave.exists() or not self._portal_can_access_employee_record(
            employee, leave.employee_id
        ):
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
    def portal_my_time_off(
        self,
        page=1,
        sortby=None,
        filterby=None,
        search=None,
        search_in="all",
        **kwargs,
    ):
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

        is_portal_hr_admin = self._is_portal_hr_admin()
        leave_model = request.env["hr.leave"].sudo()
        domain = self._portal_employee_domain(employee)

        searchbar_filters = {
            "all": {"label": _("All"), "domain": [], "sequence": 10},
            "confirm": {
                "label": _("To Approve"),
                "domain": [("state", "=", "confirm")],
                "sequence": 20,
            },
            "validate1": {
                "label": _("Second Approval"),
                "domain": [("state", "=", "validate1")],
                "sequence": 30,
            },
            "validate": {
                "label": _("Approved"),
                "domain": [("state", "=", "validate")],
                "sequence": 40,
            },
            "refuse": {
                "label": _("Refused"),
                "domain": [("state", "=", "refuse")],
                "sequence": 50,
            },
            "cancel": {
                "label": _("Cancelled"),
                "domain": [("state", "=", "cancel")],
                "sequence": 60,
            },
        }

        search_inputs = {
            "all": {
                "input": "all",
                "label": _("Search in All"),
                "sequence": 10,
                "domain": lambda value: self._portal_or_domain(
                    [
                        [("employee_id.name", "ilike", value)] if is_portal_hr_admin else [],
                        [("holiday_status_id.name", "ilike", value)],
                        [("private_name", "ilike", value)],
                    ]
                ),
            },
            "type": {
                "input": "type",
                "label": _("Search in Time Off Type"),
                "sequence": 20,
                "domain": lambda value: [("holiday_status_id.name", "ilike", value)],
            },
            "description": {
                "input": "description",
                "label": _("Search in Description"),
                "sequence": 30,
                "domain": lambda value: [("private_name", "ilike", value)],
            },
        }
        if is_portal_hr_admin:
            search_inputs["employee"] = {
                "input": "employee",
                "label": _("Search in Employee"),
                "sequence": 15,
                "domain": lambda value: [("employee_id.name", "ilike", value)],
            }

        searchbar_sortings = {
            "date": {"label": _("Newest"), "order": "create_date desc"},
            "date_from": {"label": _("Start Date"), "order": "request_date_from desc, id desc"},
            "duration": {"label": _("Duration"), "order": "number_of_days desc, create_date desc"},
        }
        if is_portal_hr_admin:
            searchbar_sortings["employee"] = {
                "label": _("Employee"),
                "order": "employee_id, create_date desc",
            }

        searchbar = self._portal_apply_searchbar(
            domain,
            searchbar_filters=searchbar_filters,
            searchbar_inputs=search_inputs,
            searchbar_sortings=searchbar_sortings,
            filterby=filterby,
            search=search,
            search_in=search_in,
            sortby=sortby,
            default_filterby="all",
            default_search_in="all",
            default_sortby="date",
        )
        domain = searchbar["domain"]
        leave_count = leave_model.search_count(domain)
        pager = portal_pager(
            url="/my/time_off",
            url_args={
                "sortby": searchbar["sortby"],
                "filterby": searchbar["filterby"],
                "search": searchbar["search"],
                "search_in": searchbar["search_in"],
            },
            total=leave_count,
            page=page,
            step=self._items_per_page,
        )
        leaves = leave_model.search(
            domain,
            order=searchbar["order"],
            limit=self._items_per_page,
            offset=pager["offset"],
        )
        values = {
            "page_name": "portal_time_off",
            "employee": employee,
            "leaves": leaves,
            "pager": pager,
            "leave_state_labels": _get_leave_state_labels(),
            "leave_state_badges": LEAVE_STATE_BADGES,
            "is_portal_hr_admin": is_portal_hr_admin,
            "default_url": "/my/time_off",
            "searchbar_filters": searchbar["searchbar_filters"],
            "filterby": searchbar["filterby"],
            "searchbar_inputs": searchbar["searchbar_inputs"],
            "search_in": searchbar["search_in"],
            "search": searchbar["search"],
            "searchbar_sortings": searchbar["searchbar_sortings"],
            "sortby": searchbar["sortby"],
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
            "is_portal_hr_admin": self._is_portal_hr_admin(),
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
            "is_portal_hr_admin": self._is_portal_hr_admin(),
            "can_cancel_leave": leave.employee_id == employee and leave.can_cancel,
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
            if leave.employee_id != employee:
                raise AccessError(_("You can only cancel your own time off requests."))
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
