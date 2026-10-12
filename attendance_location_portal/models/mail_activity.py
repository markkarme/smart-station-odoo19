from odoo import api, models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _get_hr_responsible_users_for_activity(self):
        self.ensure_one()
        employee = self.env["hr.employee"]
        if self.res_model == "hr.employee":
            employee = self.env["hr.employee"].browse(self.res_id).exists()
        elif self.res_model == "hr.version":
            version = self.env["hr.version"].browse(self.res_id).exists()
            employee = version.employee_id

        if not employee or "hr_responsible_ids" not in employee._fields:
            return self.env["res.users"]
        if not employee.hr_responsible_ids:
            return self.env["res.users"]
        if self.user_id not in employee.hr_responsible_ids:
            return self.env["res.users"]
        return employee.hr_responsible_ids

    @api.model_create_multi
    def create(self, vals_list):
        activities = super().create(vals_list)
        if self.env.context.get("skip_multi_hr_responsible_activity"):
            return activities

        extra_activity_vals = []
        for activity in activities:
            responsible_users = activity._get_hr_responsible_users_for_activity()
            if len(responsible_users) <= 1:
                continue

            existing_user_ids = set(
                self.search(
                    [
                        ("res_model_id", "=", activity.res_model_id.id),
                        ("res_id", "=", activity.res_id),
                        ("activity_type_id", "=", activity.activity_type_id.id),
                    ]
                ).mapped("user_id").ids
            )
            for user in responsible_users:
                if user.id in existing_user_ids:
                    continue
                extra_activity_vals.append(
                    {
                        "res_id": activity.res_id,
                        "res_model_id": activity.res_model_id.id,
                        "activity_type_id": activity.activity_type_id.id,
                        "summary": activity.summary,
                        "note": activity.note,
                        "date_deadline": activity.date_deadline,
                        "user_id": user.id,
                        "automated": activity.automated,
                    }
                )
                existing_user_ids.add(user.id)

        if extra_activity_vals:
            super(
                MailActivity,
                self.with_context(skip_multi_hr_responsible_activity=True),
            ).create(extra_activity_vals)
        return activities
