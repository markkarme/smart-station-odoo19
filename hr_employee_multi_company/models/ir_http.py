# -*- coding: utf-8 -*-
from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _frontend_pre_dispatch(cls):
        super()._frontend_pre_dispatch()
        # Website normally activates only the website company. Portal employees
        # assigned to several companies need all of them active, otherwise
        # employee_ids / contacts from another company are empty or 403.
        user = request.env.user
        if not user or user._is_public() or not user._is_portal():
            return

        # Do not use user.employee_ids here: that field is company-filtered and
        # is empty before we expand allowed_company_ids (chicken-and-egg).
        employee = (
            request.env["hr.employee"]
            .sudo()
            .with_context(active_test=False)
            .search([("user_id", "=", user.id)], limit=1)
        )
        if not employee:
            return

        company_ids = list(
            dict.fromkeys(
                list(user._get_company_ids()) + employee.company_ids.ids + employee.company_id.ids
            )
        )
        if len(company_ids) <= 1:
            return
        request.update_context(allowed_company_ids=company_ids)
