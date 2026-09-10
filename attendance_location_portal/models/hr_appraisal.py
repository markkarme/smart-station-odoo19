from odoo import _, api, fields, models


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
