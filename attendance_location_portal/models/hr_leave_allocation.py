from odoo import _, api, fields, models


class HrLeaveAllocation(models.Model):
    _inherit = "hr.leave.allocation"

    portal_state_label = fields.Char(compute="_compute_portal_state_label")

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

    def activity_update(self):
        user = self.env.user
        if self._is_portal_only_user(user):
            return super(HrLeaveAllocation, self.sudo()).activity_update()
        portal_owned = self.filtered(
            lambda allocation: self._is_portal_only_user(allocation.employee_id.user_id)
        )
        if portal_owned:
            super(HrLeaveAllocation, self - portal_owned).activity_update()
            return super(HrLeaveAllocation, portal_owned.sudo()).activity_update()
        return super().activity_update()
