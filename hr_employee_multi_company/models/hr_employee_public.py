# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    company_ids = fields.Many2many(
        related="employee_id.company_ids",
        string="Companies",
        readonly=True,
    )
