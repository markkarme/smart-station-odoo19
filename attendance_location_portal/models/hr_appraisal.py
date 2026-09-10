from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class HrAppraisal(models.Model):
    _inherit = "hr.appraisal"

    portal_state_label = fields.Char(compute="_compute_portal_state_label")

    @api.depends("state")
    def _compute_portal_state_label(self):
        selection = dict(self._fields["state"].selection)
        for appraisal in self:
            appraisal.portal_state_label = selection.get(appraisal.state, appraisal.state)

    def _portal_state_badge_class(self):
        self.ensure_one()
        return {
            "1_new": "text-bg-secondary",
            "2_pending": "text-bg-warning",
            "3_done": "text-bg-success",
        }.get(self.state, "text-bg-secondary")

    def _portal_role(self, employee):
        self.ensure_one()
        is_employee = self.employee_id == employee
        is_appraiser = employee in self.manager_ids
        return is_employee, is_appraiser

    def _portal_ensure_access(self, employee):
        self.ensure_one()
        is_employee, is_appraiser = self._portal_role(employee)
        if not is_employee and not is_appraiser:
            raise AccessError(_("This appraisal does not exist or is not accessible."))
        return is_employee, is_appraiser

    def action_portal_save(self, employee, values):
        self.ensure_one()
        employee._portal_ensure_current_user()
        is_employee, is_appraiser = self._portal_ensure_access(employee)

        if self.state == "3_done":
            raise UserError(_("This appraisal is done and can no longer be edited."))

        vals = {}
        date_close = values.get("date_close")
        if date_close:
            try:
                vals["date_close"] = fields.Date.to_date(date_close)
            except (TypeError, ValueError):
                raise UserError(_("Invalid date format.")) from None

        if self.state == "1_new" and values.get("employee_id"):
            people_vals = {
                "employee_id": values.get("employee_id"),
                "manager_ids": values.get("manager_ids", self.manager_ids.ids),
            }
            subject, managers = employee._portal_resolve_appraisal_people(people_vals)
            vals["employee_id"] = subject.id
            vals["manager_ids"] = [(6, 0, managers.ids)]
        elif self.state != "3_done" and "manager_ids" in values:
            if not (is_appraiser or (is_employee and self.state == "1_new")):
                raise UserError(_("You cannot change the appraisers of this appraisal."))
            _subject, managers = employee._portal_resolve_appraisal_people(
                {
                    "employee_id": self.employee_id,
                    "manager_ids": values.get("manager_ids"),
                }
            )
            vals["manager_ids"] = [(6, 0, managers.ids)]

        if is_employee or (is_appraiser and self.state == "1_new"):
            if "employee_feedback" in values and self.state in ("1_new", "2_pending"):
                vals["employee_feedback"] = values.get("employee_feedback") or False
            if self.state == "2_pending" and is_employee and "employee_feedback_published" in values:
                vals["employee_feedback_published"] = bool(values.get("employee_feedback_published"))

        if is_appraiser and self.state in ("1_new", "2_pending"):
            if "manager_feedback" in values:
                vals["manager_feedback"] = values.get("manager_feedback") or False
            if self.state == "2_pending" and "manager_feedback_published" in values:
                vals["manager_feedback_published"] = bool(values.get("manager_feedback_published"))
            if "note" in values:
                vals["note"] = values.get("note") or False

        if not vals:
            return self

        try:
            with self.env.cr.savepoint():
                self.with_user(SUPERUSER_ID).write(vals)
        except ValidationError as error:
            raise UserError(str(error)) from error

        return self

    def action_portal_confirm(self, employee):
        self.ensure_one()
        employee._portal_ensure_current_user()
        _is_employee, is_appraiser = self._portal_ensure_access(employee)
        if not is_appraiser:
            raise UserError(_("Only an appraiser can confirm this appraisal."))
        if self.state != "1_new":
            raise UserError(_("Only draft appraisals can be confirmed."))
        try:
            with self.env.cr.savepoint():
                self.with_user(SUPERUSER_ID).action_confirm()
        except ValidationError as error:
            raise UserError(str(error)) from error
        return self
