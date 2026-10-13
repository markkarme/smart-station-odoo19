from urllib.parse import urlencode
import logging

from odoo import _, fields, http
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

        attendance_action = (post.get("attendance_action") or "").strip()
        force_check_in = (post.get("force_check_in") or "").strip() in (
            "1",
            "true",
            "True",
        )
        if attendance_action == "check_in" and not force_check_in:
            today = employee._portal_attendance_local_date()
            has_check_in_today = request.env["hr.attendance"].sudo().search_count(
                [
                    ("employee_id", "=", employee.id),
                    ("date", "=", today),
                    ("check_in", "!=", False),
                ]
            )
            if has_check_in_today:
                values = {
                    "page_name": "portal_attendance_duplicate_checkin",
                    "employee": employee,
                    "warning_message": _(
                        "لقد قمت بتسجيل الحضور اليوم بالفعل. هل تريد متابعة تسجيل حضور جديد؟"
                    ),
                    "post_values": {
                        "latitude": post.get("latitude") or "",
                        "longitude": post.get("longitude") or "",
                        "attendance_action": attendance_action,
                        "note": post.get("note") or "",
                    },
                }
                return request.render(
                    "attendance_location_portal.portal_attendance_duplicate_checkin_page",
                    values,
                )

        try:
            latitude = post.get("latitude")
            longitude = post.get("longitude")
            note = post.get("note")
            result = employee.sudo().with_context(
                lang=request.env.lang
            ).action_portal_attendance_change(
                latitude,
                longitude,
                attendance_action=attendance_action,
                note=note,
            )
            params = {
                "action": result["action"],
                "location": result["location_name"],
            }
            if result.get("warnings"):
                params["warning"] = "\n".join(result["warnings"])
            return request.redirect("/my/attendance/success?%s" % urlencode(params))
        except UserError as error:
            params = urlencode({"reason": str(error)})
            return request.redirect("/my/attendance/failed?%s" % params)
        except Exception as error:
            _logger.exception("Portal attendance submit failed: %s", error)
            action = (post.get("attendance_action") or "").strip()
            if action not in ("check_in", "check_out"):
                action = "check_in"
            today = employee._portal_attendance_local_date()
            today_attendance = request.env["hr.attendance"].sudo().search(
                [
                    ("employee_id", "=", employee.id),
                    ("date", "=", today),
                ],
                order="write_date desc, id desc",
                limit=1,
            )
            if today_attendance:
                params = urlencode(
                    {
                        "action": action,
                        "location": today_attendance.attendance_location_id.name
                        or _("Unknown"),
                    }
                )
                return request.redirect("/my/attendance/success?%s" % params)
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
            "warning_message": kwargs.get("warning"),
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

    def _format_worked_hours(self, hours):
        total_minutes = int(round(float(hours or 0.0) * 60))
        sign = "-" if total_minutes < 0 else ""
        total_minutes = abs(total_minutes)
        return "%s%d:%02d" % (sign, total_minutes // 60, total_minutes % 60)

    def _portal_attendance_url(self, **params):
        cleaned = {
            key: value
            for key, value in params.items()
            if value not in (None, "", False)
        }
        query = urlencode(cleaned)
        return "/my/attendances%s" % (("?%s" % query) if query else "")

    def _portal_attendance_groupby(self, is_portal_hr_admin, groupby):
        if not is_portal_hr_admin:
            return "none", None
        options = {
            "company": {"label": _("Company"), "sequence": 10},
            "employee": {"label": _("Employee"), "sequence": 20},
            "none": {"label": _("None"), "sequence": 30},
        }
        if groupby not in options:
            groupby = "company"
        return groupby, self._portal_sorted_searchbar(options)

    def _portal_attendance_groups(self, attendance_model, domain, groupby, url_params):
        field_name = "company_id" if groupby == "company" else "employee_id"
        rows = attendance_model._read_group(
            domain,
            groupby=[field_name],
            aggregates=["__count", "worked_hours:sum"],
            order=field_name,
        )
        groups = []
        for record, count, hours in rows:
            if record:
                name = record.display_name
                record_id = record.id
            else:
                name = _("No Company") if groupby == "company" else _("No Employee")
                record_id = "false"
            filter_key = "company_id" if groupby == "company" else "employee_id"
            groups.append(
                {
                    "name": name,
                    "count": count,
                    "hours": self._format_worked_hours(hours),
                    "url": self._portal_attendance_url(
                        groupby="none",
                        **url_params,
                        **{filter_key: record_id},
                    ),
                }
            )
        return groups

    def _portal_attendance_group_context(self, groupby, company_id, employee_id, url_params):
        """Flat list opened from a company or employee group."""
        if groupby != "none":
            return [], None
        if company_id:
            if str(company_id) == "false":
                return [("company_id", "=", False)], {
                    "label": _("Company"),
                    "name": _("No Company"),
                    "back_url": self._portal_attendance_url(groupby="company", **url_params),
                }
            if str(company_id).isdigit():
                company = request.env["res.company"].sudo().browse(int(company_id)).exists()
                allowed_company_ids = set(self._portal_user_company_ids())
                if not company or company.id not in allowed_company_ids:
                    return [("company_id", "=", 0)], None
                return [("company_id", "=", company.id)], {
                    "label": _("Company"),
                    "name": company.display_name,
                    "back_url": self._portal_attendance_url(groupby="company", **url_params),
                }
        if employee_id:
            if str(employee_id) == "false":
                return [("employee_id", "=", False)], {
                    "label": _("Employee"),
                    "name": _("No Employee"),
                    "back_url": self._portal_attendance_url(groupby="employee", **url_params),
                }
            if str(employee_id).isdigit():
                employee = request.env["hr.employee"].sudo().browse(int(employee_id)).exists()
                if not employee:
                    return [("employee_id", "=", 0)], None
                context = None
                if self._portal_can_access_employee_record(
                    self._get_user_employee(),
                    employee,
                ):
                    context = {
                        "label": _("Employee"),
                        "name": employee.display_name,
                        "back_url": self._portal_attendance_url(
                            groupby="employee", **url_params
                        ),
                    }
                return [("employee_id", "=", employee.id)], context
        return [], None

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
        groupby=None,
        company_id=None,
        employee_id=None,
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
                        [("company_id.name", "ilike", value)] if is_portal_hr_admin else [],
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
            "attendance_location_id": {
                "input": "attendance_location_id",
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
        groupby, searchbar_groupby = self._portal_attendance_groupby(
            is_portal_hr_admin, groupby
        )
        url_params = {
            "sortby": searchbar["sortby"],
            "filterby": searchbar["filterby"] if searchbar["filterby"] != "all" else None,
            "search": searchbar["search"] or None,
            "search_in": searchbar["search_in"] if searchbar["search"] else None,
        }
        pager_args = {
            "sortby": searchbar["sortby"],
            "filterby": searchbar["filterby"],
            "search": searchbar["search"],
            "search_in": searchbar["search_in"],
            "groupby": groupby,
        }
        attendance_groups = False
        attendance_group_context = None
        if groupby != "none":
            all_groups = self._portal_attendance_groups(
                attendance_model, domain, groupby, url_params
            )
            pager = portal_pager(
                url="/my/attendances",
                url_args=pager_args,
                total=len(all_groups),
                page=page,
                step=self._items_per_page,
            )
            attendance_groups = all_groups[
                pager["offset"] : pager["offset"] + self._items_per_page
            ]
            attendances = attendance_model.browse()
        else:
            extra_domain, attendance_group_context = (
                self._portal_attendance_group_context(
                    groupby, company_id, employee_id, url_params
                )
                if is_portal_hr_admin
                else ([], None)
            )
            domain = list(domain) + list(extra_domain)
            if company_id:
                pager_args["company_id"] = company_id
            if employee_id:
                pager_args["employee_id"] = employee_id
            attendance_count = attendance_model.search_count(domain)
            pager = portal_pager(
                url="/my/attendances",
                url_args=pager_args,
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
            "attendance_groups": attendance_groups,
            "attendance_group_context": attendance_group_context,
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
            "searchbar_groupby": searchbar_groupby,
            "groupby": groupby,
        }
        return request.render(
            "attendance_location_portal.portal_my_attendances",
            values,
        )
