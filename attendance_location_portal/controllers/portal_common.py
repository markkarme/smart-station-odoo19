from collections import OrderedDict
from datetime import datetime, time

from odoo import _
from odoo.http import request
from odoo.tools import date_utils


class PortalHrMixin:
    """Shared helpers for HR portal controllers."""

    _items_per_page = 20

    def _get_user_employee(self):
        employee = request.env.user.employee_id
        if not employee:
            employee = request.env.user.employee_ids[:1]
        return employee

    def _is_portal_hr_admin(self):
        return request.env.user.has_group(
            "attendance_location_portal.group_portal_hr_admin"
        )

    def _portal_employee_domain(self, employee, field="employee_id"):
        """Own records for normal portal users; all records for portal admins."""
        if self._is_portal_hr_admin():
            return []
        return [(field, "=", employee.id)]

    def _portal_can_access_employee_record(self, employee, record_employee):
        return self._is_portal_hr_admin() or record_employee == employee

    def _portal_sorted_searchbar(self, values):
        return OrderedDict(
            sorted(values.items(), key=lambda item: item[1].get("sequence", 50))
        )

    def _portal_or_domain(self, domains):
        domains = [domain for domain in domains if domain]
        if not domains:
            return []
        if len(domains) == 1:
            return list(domains[0])
        domain = ["|"] * (len(domains) - 1)
        for part in domains:
            domain.extend(part)
        return domain

    def _portal_local_day_bounds(self, period):
        """Return UTC-naive datetimes covering today/week/month in the user timezone."""
        from odoo import fields

        today = fields.Date.context_today(request.env.user)
        if period == "today":
            start_date = end_date = today
        elif period == "week":
            start_date = date_utils.start_of(today, "week")
            end_date = date_utils.end_of(today, "week")
        elif period == "month":
            start_date = date_utils.start_of(today, "month")
            end_date = date_utils.end_of(today, "month")
        else:
            return False, False

        try:
            import pytz

            user_tz = pytz.timezone(request.env.user.tz or "UTC")
            start_utc = (
                user_tz.localize(datetime.combine(start_date, time.min))
                .astimezone(pytz.utc)
                .replace(tzinfo=None)
            )
            end_utc = (
                user_tz.localize(datetime.combine(end_date, time.max))
                .astimezone(pytz.utc)
                .replace(tzinfo=None)
            )
            return start_utc, end_utc
        except Exception:
            return (
                datetime.combine(start_date, time.min),
                datetime.combine(end_date, time.max),
            )

    def _portal_apply_searchbar(
        self,
        domain,
        *,
        searchbar_filters=None,
        searchbar_inputs=None,
        searchbar_sortings=None,
        filterby=None,
        search=None,
        search_in=None,
        sortby=None,
        default_filterby="all",
        default_search_in="all",
        default_sortby=None,
    ):
        searchbar_filters = searchbar_filters or {
            "all": {"label": _("All"), "domain": [], "sequence": 10}
        }
        searchbar_inputs = searchbar_inputs or {}
        searchbar_sortings = searchbar_sortings or {}

        if not filterby or filterby not in searchbar_filters:
            filterby = (
                default_filterby
                if default_filterby in searchbar_filters
                else next(iter(searchbar_filters))
            )
        domain = list(domain) + list(searchbar_filters[filterby].get("domain") or [])

        if not search_in or (searchbar_inputs and search_in not in searchbar_inputs):
            search_in = (
                default_search_in
                if default_search_in in searchbar_inputs
                else (next(iter(searchbar_inputs), None) if searchbar_inputs else None)
            )
        if search and search_in and searchbar_inputs:
            search_domain = searchbar_inputs[search_in].get("domain")
            if callable(search_domain):
                search_domain = search_domain(search)
            domain = list(domain) + list(search_domain or [])

        if not sortby or sortby not in searchbar_sortings:
            sortby = (
                default_sortby
                if default_sortby in searchbar_sortings
                else (next(iter(searchbar_sortings), None) if searchbar_sortings else None)
            )
        order = (
            searchbar_sortings[sortby]["order"]
            if sortby and searchbar_sortings
            else None
        )

        return {
            "domain": domain,
            "filterby": filterby,
            "search": search or "",
            "search_in": search_in,
            "sortby": sortby,
            "order": order,
            "searchbar_filters": self._portal_sorted_searchbar(searchbar_filters),
            "searchbar_inputs": (
                self._portal_sorted_searchbar(searchbar_inputs) if searchbar_inputs else None
            ),
            "searchbar_sortings": searchbar_sortings or None,
        }
