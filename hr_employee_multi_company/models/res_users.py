# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _employee_ids_domain(self):
        """Include employees linked via company_ids, not only main company_id.

        Website/portal activates a single company. Without this, employee_ids is
        empty when the website company is not the employee's main company, so
        portal home cards (attendance, time off, ...) never appear.
        """
        companies = self.env.company.ids + list(
            self.env.context.get("allowed_company_ids") or []
        )
        return [
            "|",
            ("company_id", "in", companies),
            ("company_ids", "in", companies),
        ]

    # Re-bind domain: the core field points at the original function object.
    employee_ids = fields.One2many(
        "hr.employee",
        "user_id",
        string="Related employee",
        domain=_employee_ids_domain,
    )
