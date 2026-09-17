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
        # reading contacts from another company raises a multi-company 403.
        user = request.env.user
        if not user or user._is_public() or not user._is_portal():
            return
        if not user.sudo().employee_ids:
            return
        company_ids = list(user._get_company_ids())
        if len(company_ids) <= 1:
            return
        request.update_context(allowed_company_ids=company_ids)
