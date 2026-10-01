import logging
from urllib.parse import urlencode

from odoo import _, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager

from .portal_common import PortalHrMixin

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


class PortalGeneralRequestController(PortalHrMixin, http.Controller):
    def _get_employee_general_request(self, employee, request_id):
        general_request = request.env["hr.general.request"].sudo().browse(request_id)
        if not general_request.exists() or not self._portal_can_access_employee_record(
            employee, general_request.employee_id, general_request.company_id
        ):
            raise AccessError(_("This general request does not exist or is not accessible."))
        return general_request

    @http.route(
        ["/my/general_requests", "/my/general_requests/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_general_requests(
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
                "attendance_location_portal.portal_general_request_failed_page",
                {
                    "page_name": "portal_general_request_failed",
                    "error_message": _(
                        "Your account is not linked to an employee record. "
                        "Please contact your administrator."
                    ),
                },
            )

        is_portal_hr_admin = self._is_portal_hr_admin()
        request_model = request.env["hr.general.request"].sudo()
        domain = self._portal_employee_domain(employee)

        searchbar_filters = {
            "all": {"label": _("All"), "domain": [], "sequence": 10},
            "confirm": {
                "label": _("To Approve"),
                "domain": [("state", "=", "confirm")],
                "sequence": 20,
            },
            "approve": {
                "label": _("Approved"),
                "domain": [("state", "=", "approve")],
                "sequence": 30,
            },
            "refuse": {
                "label": _("Refused"),
                "domain": [("state", "=", "refuse")],
                "sequence": 40,
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
                        [("description", "ilike", value)],
                        [("name", "ilike", value)],
                    ]
                ),
            },
            "description": {
                "input": "description",
                "label": _("Search in Description"),
                "sequence": 20,
                "domain": lambda value: [("description", "ilike", value)],
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
            "request_date": {"label": _("Request Date"), "order": "date desc, id desc"},
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
        request_count = request_model.search_count(domain)
        pager = portal_pager(
            url="/my/general_requests",
            url_args={
                "sortby": searchbar["sortby"],
                "filterby": searchbar["filterby"],
                "search": searchbar["search"],
                "search_in": searchbar["search_in"],
            },
            total=request_count,
            page=page,
            step=self._items_per_page,
        )
        general_requests = request_model.search(
            domain,
            order=searchbar["order"],
            limit=self._items_per_page,
            offset=pager["offset"],
        )
        values = {
            "page_name": "portal_general_requests",
            "employee": employee,
            "general_requests": general_requests,
            "pager": pager,
            "request_state_labels": _get_general_request_state_labels(request.env),
            "request_state_badges": GENERAL_REQUEST_STATE_BADGES,
            "is_portal_hr_admin": is_portal_hr_admin,
            "default_url": "/my/general_requests",
            "searchbar_filters": searchbar["searchbar_filters"],
            "filterby": searchbar["filterby"],
            "searchbar_inputs": searchbar["searchbar_inputs"],
            "search_in": searchbar["search_in"],
            "search": searchbar["search"],
            "searchbar_sortings": searchbar["searchbar_sortings"],
            "sortby": searchbar["sortby"],
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
            "is_portal_hr_admin": self._is_portal_hr_admin(),
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
            "is_portal_hr_admin": self._is_portal_hr_admin(),
        }
        return request.render("attendance_location_portal.portal_general_request_detail", values)
