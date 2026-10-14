from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    portal_hr_admin = fields.Boolean(
        string="Portal Admin",
        compute="_compute_portal_hr_admin",
        store=True,
        compute_sudo=True,
    )

    def _portal_hr_admin_group(self):
        return self.env.ref(
            "attendance_location_portal.group_portal_hr_admin",
            raise_if_not_found=False,
        )

    @api.depends("group_ids")
    def _compute_portal_hr_admin(self):
        group = self._portal_hr_admin_group()
        for user in self:
            user.portal_hr_admin = bool(group and group in user.all_group_ids)
