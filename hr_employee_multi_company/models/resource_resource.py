# -*- coding: utf-8 -*-
from odoo import fields, models


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    # Used by multi-company record rule so a resource of a multi-company
    # employee can be read while working in any of that employee's companies.
    employee_company_ids = fields.Many2many(
        "res.company",
        string="Employee Companies",
        compute="_compute_employee_company_ids",
        search="_search_employee_company_ids",
    )

    def _compute_employee_company_ids(self):
        for resource in self:
            resource.employee_company_ids = resource.employee_id.company_ids

    def _search_employee_company_ids(self, operator, value):
        employees = self.env["hr.employee"].sudo().search(
            [("company_ids", operator, value)]
        )
        return [("id", "in", employees.resource_id.ids)]
