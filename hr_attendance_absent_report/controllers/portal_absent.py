from urllib.parse import urlencode

from odoo import fields, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager

from odoo.addons.attendance_location_portal.controllers.portal_common import PortalHrMixin


STATUS_BADGES = {
    "absent": "text-bg-danger",
    "on_leave": "text-bg-warning",
    "worked_time_off": "text-bg-success",
    "weekend": "text-bg-info",
    "public_holiday": "text-bg-info",
}


class PortalAbsentEmployeesController(PortalHrMixin, http.Controller):
    def _portal_lang_code(self):
        """Use website/frontend language so portal UI matches Arabic pages."""
        lang = getattr(request, "lang", None)
        if lang is None:
            return request.env.lang
        return lang.code if hasattr(lang, "code") else lang

    def _pt(self, source):
        """Translate with website lang (portal users often keep en_US on res.users)."""
        # Odoo 19: Environment has no with_context(); pass a new context via env(...).
        ctx = dict(request.env.context, lang=self._portal_lang_code())
        return request.env(context=ctx)._(source)

    def _ensure_portal_hr_admin(self):
        if not self._is_portal_hr_admin():
            raise AccessError(
                self._pt("Only portal administrators can access the absent employees report.")
            )

    def _status_labels(self):
        return {
            "absent": self._pt("Absent"),
            "on_leave": self._pt("On Leave"),
            "worked_time_off": self._pt("Worked Time Off"),
            "weekend": self._pt("Weekend"),
            "public_holiday": self._pt("Public Holiday"),
        }

    @http.route(
        ["/my/absent_employees", "/my/absent_employees/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_absent_employees(
        self,
        page=1,
        date_from=None,
        date_to=None,
        filterby=None,
        search=None,
        search_in="all",
        sortby=None,
        **kwargs,
    ):
        self._ensure_portal_hr_admin()
        employee = self._get_user_employee()
        if not employee:
            return request.render(
                "hr_attendance_absent_report.portal_absent_failed_page",
                {
                    "page_name": "portal_absent_failed",
                    "error_message": self._pt(
                        "Your account is not linked to an employee record. "
                        "Please contact your administrator."
                    ),
                },
            )

        today = fields.Date.context_today(request.env.user)
        date_from = fields.Date.to_date(date_from) if date_from else today
        date_to = fields.Date.to_date(date_to) if date_to else today
        if date_from > date_to:
            date_from, date_to = date_to, date_from

        company_ids = self._portal_user_company_ids()
        report_model = request.env["hr.attendance.absent.report"].sudo()
        domain = [
            ("date_from", "=", date_from),
            ("date_to", "=", date_to),
        ]
        if company_ids:
            domain.append(("company_id", "in", company_ids))
        else:
            domain.append(("employee_id", "=", employee.id))

        searchbar_filters = {
            "all": {"label": self._pt("All"), "domain": [], "sequence": 10},
            "absent": {
                "label": self._pt("Absent"),
                "domain": [("status", "=", "absent")],
                "sequence": 20,
            },
            "on_leave": {
                "label": self._pt("On Leave"),
                "domain": [("status", "=", "on_leave")],
                "sequence": 30,
            },
            "worked_time_off": {
                "label": self._pt("Worked Time Off"),
                "domain": [("status", "=", "worked_time_off")],
                "sequence": 40,
            },
            "weekend": {
                "label": self._pt("Weekend"),
                "domain": [("status", "=", "weekend")],
                "sequence": 50,
            },
            "public_holiday": {
                "label": self._pt("Public Holiday"),
                "domain": [("status", "=", "public_holiday")],
                "sequence": 60,
            },
        }
        search_inputs = {
            "all": {
                "input": "all",
                "label": self._pt("Search in All"),
                "sequence": 10,
                "domain": lambda value: self._portal_or_domain(
                    [
                        [("employee_id.name", "ilike", value)],
                        [("status", "ilike", value)],
                    ]
                ),
            },
            "employee": {
                "input": "employee",
                "label": self._pt("Search in Employee"),
                "sequence": 20,
                "domain": lambda value: [("employee_id.name", "ilike", value)],
            },
        }
        searchbar_sortings = {
            "date": {"label": self._pt("Date"), "order": "date desc, employee_id"},
            "employee": {"label": self._pt("Employee"), "order": "employee_id, date desc"},
            "status": {"label": self._pt("Status"), "order": "status, date desc"},
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
            default_search_in="employee",
            default_sortby="date",
        )
        domain = searchbar["domain"]
        report_count = report_model.search_count(domain)
        pager = portal_pager(
            url="/my/absent_employees",
            url_args={
                "date_from": date_from,
                "date_to": date_to,
                "sortby": searchbar["sortby"],
                "filterby": searchbar["filterby"],
                "search": searchbar["search"],
                "search_in": searchbar["search_in"],
            },
            total=report_count,
            page=page,
            step=self._items_per_page,
        )
        lines = report_model.search(
            domain,
            order=searchbar["order"],
            limit=self._items_per_page,
            offset=pager["offset"],
        )
        status_labels = self._status_labels()
        values = {
            "page_name": "portal_absent_employees",
            "employee": employee,
            "date_from": date_from,
            "date_to": date_to,
            "lines": lines,
            "pager": pager,
            "status_labels": status_labels,
            "status_badges": STATUS_BADGES,
            "default_url": "/my/absent_employees",
            "searchbar_filters": searchbar["searchbar_filters"],
            "filterby": searchbar["filterby"],
            "searchbar_inputs": searchbar["searchbar_inputs"],
            "search_in": searchbar["search_in"],
            "search": searchbar["search"],
            "searchbar_sortings": searchbar["searchbar_sortings"],
            "sortby": searchbar["sortby"],
        }
        return request.render(
            "hr_attendance_absent_report.portal_my_absent_employees",
            values,
        )

    @http.route(
        "/my/absent_employees/compute",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_absent_employees_compute(self, **post):
        self._ensure_portal_hr_admin()
        try:
            date_from = fields.Date.to_date(post.get("date_from"))
            date_to = fields.Date.to_date(post.get("date_to"))
            if not date_from or not date_to:
                raise UserError(self._pt("Please select Date From and Date To."))
            if date_from > date_to:
                raise UserError(self._pt("Date From cannot be after Date To."))

            company_ids = self._portal_user_company_ids()
            wizard = request.env["hr.attendance.absent.wizard"].sudo().create(
                {
                    "date_from": date_from,
                    "date_to": date_to,
                }
            )
            wizard.action_compute(company_ids=company_ids or False)
            params = urlencode({"date_from": date_from, "date_to": date_to})
            return request.redirect("/my/absent_employees?%s" % params)
        except (AccessError, UserError) as error:
            return request.render(
                "hr_attendance_absent_report.portal_absent_failed_page",
                {
                    "page_name": "portal_absent_failed",
                    "error_message": str(error),
                },
            )
