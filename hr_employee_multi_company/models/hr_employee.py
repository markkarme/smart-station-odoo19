# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    company_ids = fields.Many2many(
        "res.company",
        "hr_employee_res_company_rel",
        "employee_id",
        "company_id",
        string="Companies",
        required=True,
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
            if not company_ids:
                company_ids = {self.env.company.id}
                vals["company_ids"] = [(6, 0, list(company_ids))]

            company_id = vals.get("company_id")
            if company_id is None and self and len(self) == 1:
                company_id = self.company_id.id
            if not company_id or company_id not in company_ids:
                vals["company_id"] = next(iter(company_ids))
            return vals

        if has_company_id and vals.get("company_id"):
            vals.setdefault("company_ids", [(4, vals["company_id"])])
        return vals

    def _sync_linked_user_companies(self):
        """Mirror employee companies on the linked user and share the contact."""
        for employee in self:
            user = employee.user_id
            if not user:
                continue
            companies = employee.company_ids
            if not companies:
                continue

            user_vals = {}
            if set(user.company_ids.ids) != set(companies.ids):
                user_vals["company_ids"] = [(6, 0, companies.ids)]
            main_company = employee.company_id if employee.company_id in companies else companies[0]
            if user.company_id != main_company:
                user_vals["company_id"] = main_company.id
            if user_vals:
                user.sudo().with_context(no_reset_password=True).write(user_vals)

            # Portal/website activate one company; a shared contact avoids 403s
            # when the partner was created under another company.
            partner = user.partner_id
            if partner and len(companies) > 1 and partner.company_id:
                partner.sudo().write({"company_id": False})
            work_contact = employee.work_contact_id
            if work_contact and len(companies) > 1 and work_contact.company_id:
                work_contact.sudo().write({"company_id": False})

    @api.model_create_multi
    def create(self, vals_list):
        synced_vals_list = [
            self._sync_company_fields(vals, current_company_ids=set())
            for vals in vals_list
        ]
        employees = super().create(synced_vals_list)
        to_fix = employees.filtered(
            lambda e: e.company_id and e.company_id not in e.company_ids
        )
        for employee in to_fix:
            employee.company_ids = [(4, employee.company_id.id)]
        employees._sync_linked_user_companies()
        return employees

    def write(self, vals):
        if "company_ids" not in vals and "company_id" not in vals and "user_id" not in vals:
            return super().write(vals)

        if "company_ids" in vals or "company_id" in vals:
            if len(self) == 1:
                res = super().write(
                    self._sync_company_fields(
                        vals, current_company_ids=set(self.company_ids.ids)
                    )
                )
                self._sync_linked_user_companies()
                return res

            if "company_ids" in vals:
                for employee in self:
                    employee.write(
                        employee._sync_company_fields(
                            vals, current_company_ids=set(employee.company_ids.ids)
                        )
                    )
                return True
            res = super().write(self._sync_company_fields(vals))
            self._sync_linked_user_companies()
            return res

        res = super().write(vals)
        if "user_id" in vals:
            self._sync_linked_user_companies()
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
        # Suppress standard "create another employee" warning: multi-company
        # assignment is handled through company_ids.
        if self.company_id and self.company_id not in self.company_ids:
            self.company_ids = [(4, self.company_id.id)]

    @api.constrains("company_id", "company_ids")
    def _check_company_ids(self):
        for employee in self:
            if not employee.company_ids:
                raise ValidationError(
                    _("An employee must belong to at least one company.")
                )
            if employee.company_id and employee.company_id not in employee.company_ids:
                raise ValidationError(
                    _("The main company must be one of the employee's companies.")
                )
