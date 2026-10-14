from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .approval_access import decision_user


class HrLeaveAllocation(models.Model):
    _inherit = "hr.leave.allocation"

    portal_state_label = fields.Char(compute="_compute_portal_state_label")
    validation_type = fields.Selection(
        selection=[
            ("no_validation", "None needed"),
            ("hr", "By Time Off Officer"),
            ("manager", "By Employee's Approver"),
            ("both", "By Employee's Approver and Time Off Officer"),
        ],
        string="Validation Type",
        compute="_compute_validation_type",
        store=True,
        readonly=True,
        related=False,
    )

    @api.depends("holiday_status_id.allocation_validation_type", "employee_id.hr_responsible_ids")
    def _compute_validation_type(self):
        for allocation in self:
            base = allocation.holiday_status_id.allocation_validation_type
            if allocation.employee_id.hr_responsible_ids and base and base != "no_validation":
                allocation.validation_type = "both"
            else:
                allocation.validation_type = base

    @api.depends("state")
    def _compute_portal_state_label(self):
        selection = dict(self._fields["state"].selection)
        for allocation in self:
            allocation.portal_state_label = selection.get(allocation.state, allocation.state)

    def _portal_state_badge_class(self):
        self.ensure_one()
        return {
            "confirm": "text-bg-warning",
            "validate1": "text-bg-info",
            "validate": "text-bg-success",
            "refuse": "text-bg-danger",
        }.get(self.state, "text-bg-secondary")

    def _is_portal_only_user(self, user):
        if not user:
            return False
        return user.has_group("base.group_portal") and not user.has_group("base.group_user")

    def _check_portal_admin_decision(self):
        self.ensure_one()
        user = decision_user(self)
        if not user.has_group("attendance_location_portal.group_portal_hr_admin"):
            raise UserError(_("Only portal administrators can approve or refuse requests."))
        if self.employee_id.user_id == user:
            raise UserError(_("You cannot approve or refuse your own request."))
        company = self.employee_company_id or self.employee_id.company_id
        if company and company not in user.company_ids:
            raise UserError(_("This allocation request is not accessible."))

    def _time_off_approver_users(self):
        self.ensure_one()
        approvers = self.employee_id.leave_manager_ids
        if self.employee_id.leave_manager_id:
            approvers |= self.employee_id.leave_manager_id
        return approvers

    def _get_responsible_for_approval(self):
        self.ensure_one()
        if self.validation_type != "both":
            return super()._get_responsible_for_approval()
        employee = self.employee_id
        if not employee.hr_responsible_ids:
            return self.env["res.users"]
        if self.state == "confirm":
            return employee.hr_responsible_ids
        if self.state == "validate1":
            return self._time_off_approver_users()
        return self.env["res.users"]

    def _uses_assigned_approvers(self):
        self.ensure_one()
        return self.validation_type == "both" and bool(self.employee_id.hr_responsible_ids)

    def _user_can_approve_current_step(self):
        self.ensure_one()
        if not self._uses_assigned_approvers():
            return True
        user = decision_user(self)
        if self.state == "confirm":
            return user in self.employee_id.hr_responsible_ids
        if self.state in ("validate1", "validate"):
            return user in self._time_off_approver_users()
        return False

    def _get_next_states_by_state(self):
        result = super()._get_next_states_by_state()
        if not self._uses_assigned_approvers():
            return result
        user = decision_user(self)
        result["confirm"].difference_update({"validate", "validate1", "refuse"})
        result["validate1"].difference_update({"validate", "refuse"})
        if user in self.employee_id.hr_responsible_ids:
            result["confirm"].update({"validate1", "refuse"})
        if user in self._time_off_approver_users():
            result["validate1"].update({"validate", "refuse"})
        return result

    def _sync_multi_approver_activities(self):
        first_type = self.env.ref(
            "hr_holidays.mail_act_leave_allocation_approval",
            raise_if_not_found=False,
        )
        second_type = self.env.ref(
            "hr_holidays.mail_act_leave_allocation_second_approval",
            raise_if_not_found=False,
        )
        approval_types = (first_type | second_type) if first_type and second_type else first_type or second_type
        if not approval_types:
            return
        model_id = self.env["ir.model"]._get_id("hr.leave.allocation")
        today = fields.Date.today()
        for allocation in self.filtered(lambda item: item.validation_type == "both"):
            if allocation.state == "confirm":
                users = allocation.employee_id.hr_responsible_ids
                activity_type = first_type
                note = _(
                    "New Allocation request from %(employee)s",
                    employee=allocation.employee_id.name,
                )
            elif allocation.state == "validate1" and allocation.employee_id.hr_responsible_ids:
                users = allocation._time_off_approver_users()
                activity_type = second_type
                note = _(
                    "Second approval request for %(allocation_type)s",
                    allocation_type=allocation.holiday_status_id.display_name,
                )
            else:
                users = self.env["res.users"]
                activity_type = False
            existing = allocation.activity_ids.filtered(
                lambda activity: activity.automated and activity.activity_type_id in approval_types
            )
            if not activity_type or not users:
                if existing:
                    existing.unlink()
                continue
            date_deadline = allocation.date_from or today
            if date_deadline < today:
                date_deadline = today
            stale_activities = existing.filtered(
                lambda activity: activity.activity_type_id != activity_type or activity.user_id not in users
            )
            if stale_activities:
                stale_activities.unlink()
            current_activities = existing - stale_activities
            for user in users - current_activities.mapped("user_id"):
                self.env["mail.activity"].with_context(short_name=False).create(
                    {
                        "activity_type_id": activity_type.id,
                        "automated": True,
                        "date_deadline": date_deadline,
                        "note": note,
                        "user_id": user.id,
                        "res_id": allocation.id,
                        "res_model_id": model_id,
                    }
                )

    def action_approve(self):
        for allocation in self.filtered(lambda item: item._uses_assigned_approvers()):
            if not allocation._user_can_approve_current_step():
                if allocation.state == "confirm":
                    raise UserError(
                        _(
                            "Only HR Responsibles can give the first approval for %(employee)s.",
                            employee=allocation.employee_id.name,
                        )
                    )
                raise UserError(_("Only Time Off Approvers can give the second approval."))
        first_step = self.filtered(
            lambda allocation: allocation._uses_assigned_approvers() and allocation.state == "confirm"
        )
        if first_step:
            first_step.write(
                {
                    "state": "validate1",
                    "approver_id": self.env.user.employee_id.id,
                }
            )
            first_step.activity_update()
        remaining = self - first_step
        if remaining:
            super(HrLeaveAllocation, remaining).action_approve()
        return True

    def action_portal_admin_approve(self):
        self._check_portal_admin_decision()
        if self._uses_assigned_approvers() and not self._user_can_approve_current_step():
            if self.state == "confirm":
                raise UserError(
                    _(
                        "Only HR Responsibles can give the first approval for %(employee)s.",
                        employee=self.employee_id.name,
                    )
                )
            raise UserError(_("Only Time Off Approvers can give the second approval."))
        allocation = self.sudo()
        if allocation.state not in ("confirm", "validate1"):
            raise UserError(_("Only requests pending approval can be approved."))
        approver = self.env.user.employee_id
        if allocation.validation_type == "both" and allocation.state == "confirm":
            allocation.write({
                "state": "validate1",
                "approver_id": approver.id,
            })
            allocation.activity_update()
            return True
        allocation._action_validate()
        allocation.activity_update()
        return True

    def action_portal_admin_refuse(self):
        self._check_portal_admin_decision()
        if self._uses_assigned_approvers() and self.state in ("confirm", "validate1") and not self._user_can_approve_current_step():
            if self.state == "confirm":
                raise UserError(
                    _(
                        "Only HR Responsibles can give the first approval for %(employee)s.",
                        employee=self.employee_id.name,
                    )
                )
            raise UserError(_("Only Time Off Approvers can give the second approval."))
        allocation = self.sudo()
        if allocation.state not in ("confirm", "validate", "validate1"):
            raise UserError(_("Only pending or approved allocations can be refused."))
        allocation.action_refuse()
        return True

    def activity_update(self):
        user = self.env.user
        if self._is_portal_only_user(user):
            result = super(HrLeaveAllocation, self.sudo()).activity_update()
            self.sudo()._sync_multi_approver_activities()
            return result
        portal_owned = self.filtered(
            lambda allocation: self._is_portal_only_user(allocation.employee_id.user_id)
        )
        if portal_owned:
            super(HrLeaveAllocation, self - portal_owned).activity_update()
            result = super(HrLeaveAllocation, portal_owned.sudo()).activity_update()
            portal_owned.sudo()._sync_multi_approver_activities()
            (self - portal_owned)._sync_multi_approver_activities()
            return result
        result = super().activity_update()
        self._sync_multi_approver_activities()
        return result
