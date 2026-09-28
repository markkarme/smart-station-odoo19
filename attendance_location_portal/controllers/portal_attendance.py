from urllib.parse import urlencode
import logging

from odoo import _, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager

from .portal_common import PortalHrMixin

_logger = logging.getLogger(__name__)


class PortalAttendanceController(PortalHrMixin, http.Controller):
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
            "is_portal_hr_admin": self._is_portal_hr_admin(),
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
    def portal_my_attendances(
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
            values = {
                "error_message": _(
                    "Your account is not linked to an employee record. "
                    "Please contact your administrator."
                )
            }
            return request.render(
                "attendance_location_portal.portal_attendance_failed_page", values
            )

        is_portal_hr_admin = self._is_portal_hr_admin()
        attendance_model = request.env["hr.attendance"].sudo()
        domain = self._portal_employee_domain(employee)

        today_start, today_end = self._portal_local_day_bounds("today")
        week_start, week_end = self._portal_local_day_bounds("week")
        month_start, month_end = self._portal_local_day_bounds("month")

        searchbar_filters = {
            "all": {"label": _("All"), "domain": [], "sequence": 10},
            "checked_in": {
                "label": _("Checked In"),
                "domain": [("check_out", "=", False)],
                "sequence": 20,
            },
            "completed": {
                "label": _("Completed"),
                "domain": [("check_out", "!=", False)],
                "sequence": 30,
            },
            "today": {
                "label": _("Today"),
                "domain": [
                    ("check_in", ">=", today_start),
                    ("check_in", "<=", today_end),
                ],
                "sequence": 40,
            },
            "week": {
                "label": _("This Week"),
                "domain": [
                    ("check_in", ">=", week_start),
                    ("check_in", "<=", week_end),
                ],
                "sequence": 50,
            },
            "month": {
                "label": _("This Month"),
                "domain": [
                    ("check_in", ">=", month_start),
                    ("check_in", "<=", month_end),
                ],
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
                        [("portal_note", "ilike", value)],
                        [("attendance_location_id.name", "ilike", value)],
                    ]
                ),
            },
            "note": {
                "input": "note",
                "label": _("Search in Note"),
                "sequence": 20,
                "domain": lambda value: [("portal_note", "ilike", value)],
            },
            "location": {
                "input": "location",
                "label": _("Search in Location"),
                "sequence": 30,
                "domain": lambda value: [("attendance_location_id.name", "ilike", value)],
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
            "date": {"label": _("Newest"), "order": "check_in desc"},
            "date_asc": {"label": _("Oldest"), "order": "check_in asc"},
            "hours": {"label": _("Worked Hours"), "order": "worked_hours desc, check_in desc"},
        }
        if is_portal_hr_admin:
            searchbar_sortings["employee"] = {
                "label": _("Employee"),
                "order": "employee_id, check_in desc",
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
        attendance_count = attendance_model.search_count(domain)
        pager = portal_pager(
            url="/my/attendances",
            url_args={
                "sortby": searchbar["sortby"],
                "filterby": searchbar["filterby"],
                "search": searchbar["search"],
                "search_in": searchbar["search_in"],
            },
            total=attendance_count,
            page=page,
            step=self._items_per_page,
        )
        attendances = attendance_model.search(
            domain,
            order=searchbar["order"],
            limit=self._items_per_page,
            offset=pager["offset"],
        )
        values = {
            "page_name": "portal_attendance_history",
            "employee": employee,
            "attendances": attendances,
            "pager": pager,
            "is_portal_hr_admin": is_portal_hr_admin,
            "default_url": "/my/attendances",
            "searchbar_filters": searchbar["searchbar_filters"],
            "filterby": searchbar["filterby"],
            "searchbar_inputs": searchbar["searchbar_inputs"],
            "search_in": searchbar["search_in"],
            "search": searchbar["search"],
            "searchbar_sortings": searchbar["searchbar_sortings"],
            "sortby": searchbar["sortby"],
        }
        return request.render(
            "attendance_location_portal.portal_my_attendances",
            values,
        )
