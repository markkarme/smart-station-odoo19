# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrDepartment(models.Model):
    _inherit = "hr.department"

    company_ids = fields.Many2many(
        "res.company",
        "hr_department_res_company_rel",
        "department_id",
        "company_id",
        string="Companies",
        tracking=True,
        default=lambda self: self.env.company,
        domain="[('id', 'in', allowed_company_ids)]",
    )

    @api.model
    def _apply_m2m_commands(self, current_ids, commands):
        """Apply Many2many commands on top of current ids and return the result."""
        if isinstance(commands, models.BaseModel):
            return set(commands.ids)
        if not commands:
            return set(current_ids)

        result = set(current_ids)
        for command in commands:
            if not command and command != 0:
                continue
            if isinstance(command, int):
                result.add(command)
                continue
            code = command[0]
            if code == 6:
                result = set(command[2] or [])
            elif code == 5:
                result = set()
            elif code in (4, 1) and command[1]:
                result.add(command[1])
            elif code == 3 and command[1]:
                result.discard(command[1])
            elif code == 2 and command[1]:
                result.discard(command[1])
            elif code == 0 and len(command) > 2:
                pass
        return result

    def _sync_company_fields(self, vals, current_company_ids=None):
        """Keep company_id and company_ids aligned."""
        vals = dict(vals)
        has_company_ids = "company_ids" in vals
        has_company_id = "company_id" in vals

        if has_company_ids:
            current_ids = current_company_ids if current_company_ids is not None else set()
            company_ids = self._apply_m2m_commands(current_ids, vals["company_ids"])

            company_id = vals.get("company_id")
            if company_id is None and self and len(self) == 1:
                company_id = self.company_id.id
            if company_ids and (not company_id or company_id not in company_ids):
                vals["company_id"] = next(iter(company_ids))
            elif not company_ids and has_company_id and not vals.get("company_id"):
                # Explicitly clearing companies keeps department shared (company_id=False)
                vals["company_id"] = False
            return vals

        if has_company_id:
            company_id = vals.get("company_id")
            if company_id:
                vals.setdefault("company_ids", [(4, company_id)])
            else:
                vals.setdefault("company_ids", [(5, 0, 0)])
        return vals

    def _ensure_company_id_in_company_ids(self):
        """After parent-driven company_id compute, keep company_ids in sync."""
        for department in self:
            if department.company_id and department.company_id not in department.company_ids:
                department.company_ids = [(4, department.company_id.id)]

    @api.model_create_multi
    def create(self, vals_list):
        synced_vals_list = [
            self._sync_company_fields(vals, current_company_ids=set())
            for vals in vals_list
        ]
        departments = super().create(synced_vals_list)
        departments._ensure_company_id_in_company_ids()
        return departments

    def write(self, vals):
        if "company_ids" not in vals and "company_id" not in vals and "parent_id" not in vals:
            return super().write(vals)

        if "company_ids" in vals or "company_id" in vals:
            if len(self) == 1:
                res = super().write(
                    self._sync_company_fields(
                        vals, current_company_ids=set(self.company_ids.ids)
                    )
                )
                self._ensure_company_id_in_company_ids()
                return res

            if "company_ids" in vals:
                for department in self:
                    department.write(
                        department._sync_company_fields(
                            vals, current_company_ids=set(department.company_ids.ids)
                        )
                    )
                return True

            res = super().write(self._sync_company_fields(vals))
            self._ensure_company_id_in_company_ids()
            return res

        res = super().write(vals)
        if "parent_id" in vals:
            self._ensure_company_id_in_company_ids()
        return res

    @api.onchange("company_ids")
    def _onchange_company_ids(self):
        if not self.company_ids:
            self.company_id = False
            return
        if self.company_id not in self.company_ids:
            self.company_id = self.company_ids[0]

    @api.onchange("company_id")
    def _onchange_company_id(self):
        if self.company_id and self.company_id not in self.company_ids:
            self.company_ids = [(4, self.company_id.id)]
        elif not self.company_id:
            self.company_ids = [(5, 0, 0)]

    @api.onchange("parent_id")
    def _onchange_parent_id_companies(self):
        if not self.parent_id:
            return
        if self.parent_id.company_ids:
            self.company_ids = self.parent_id.company_ids
        if self.parent_id.company_id:
            self.company_id = self.parent_id.company_id

    @api.constrains("company_id", "company_ids")
    def _check_company_ids(self):
        for department in self:
            if (
                department.company_id
                and department.company_ids
                and department.company_id not in department.company_ids
            ):
                raise ValidationError(
                    _("The main company must be one of the department's companies.")
                )
