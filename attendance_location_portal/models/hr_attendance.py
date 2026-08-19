from odoo import _, api, fields, models
from odoo.tools import email_normalize


class HrAttendance(models.Model):
    _inherit = ["hr.attendance", "mail.activity.mixin"]

    portal_note = fields.Text(string="Note", tracking=True)
    attendance_location_id = fields.Many2one(
        "attendance.location",
        string="Attendance Location",
        readonly=True,
        copy=False,
        tracking=True,
    )
    in_mode = fields.Selection(
        selection_add=[("automatic", "Automatic")],
        ondelete={"automatic": "set default"},
    )
    out_mode = fields.Selection(
        selection_add=[("automatic", "Automatic")],
        ondelete={"automatic": "set default"},
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.filtered(lambda record: record.portal_note and record.check_out)._schedule_manager_note_activity()
        return records

    def write(self, vals):
        note_updated = "portal_note" in vals and vals.get("portal_note")
        previous_notes = (
            {record.id: record.portal_note for record in self} if note_updated else {}
        )
        result = super().write(vals)
        if note_updated:
            self.filtered(
                lambda record: record.portal_note
                and record.portal_note != previous_notes.get(record.id)
                and record.check_out
            )._schedule_manager_note_activity()
        return result

    def _get_manager_user(self, employee):
        manager = employee.parent_id
        if not manager:
            return self.env["res.users"]
        if manager.user_id:
            return manager.user_id
        work_email = email_normalize(manager.work_email)
        if work_email:
            return self.env["res.users"].sudo().search(
                ["|", ("login", "=", work_email), ("email_normalized", "=", work_email)],
                limit=1,
            )
        return self.env["res.users"]

    def _schedule_manager_note_activity(self):
        activity_type_xmlid = "mail.mail_activity_data_todo"
        for attendance in self.sudo():
            if not attendance.portal_note or not attendance.check_out:
                continue
            employee = attendance.employee_id
            manager = employee.parent_id
            if not manager:
                continue
            manager_user = attendance._get_manager_user(employee)
            if not manager_user:
                continue
            existing_activity = self.env["mail.activity"].sudo().search(
                [
                    ("res_model", "=", "hr.attendance"),
                    ("res_id", "=", attendance.id),
                    ("user_id", "=", manager_user.id),
                    ("summary", "=", _("Attendance note from %s") % employee.name),
                ],
                limit=1,
            )
            if existing_activity:
                existing_activity.write({"note": attendance.portal_note})
                continue
            attendance.activity_schedule(
                activity_type_xmlid,
                user_id=manager_user.id,
                summary=_("Attendance note from %s") % employee.name,
                note=attendance.portal_note,
            )
