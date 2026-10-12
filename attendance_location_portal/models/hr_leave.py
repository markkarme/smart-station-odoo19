import pytz

from odoo import _, api, fields, models


class HrLeave(models.Model):
    _inherit = "hr.leave"

    portal_state_label = fields.Char(compute="_compute_portal_state_label")

    @api.depends("state")
    def _compute_portal_state_label(self):
        selection = dict(self._fields["state"].selection)
        for leave in self:
            leave.portal_state_label = selection.get(leave.state, leave.state)

    def _portal_state_badge_class(self):
        self.ensure_one()
        return {
            "confirm": "text-bg-warning",
            "validate1": "text-bg-info",
            "validate": "text-bg-success",
            "refuse": "text-bg-danger",
            "cancel": "text-bg-secondary",
        }.get(self.state, "text-bg-secondary")

    def _is_portal_only_user(self, user):
        if not user:
            return False
        return user.has_group("base.group_portal") and not user.has_group("base.group_user")

    def _create_calendar_meetings_for_leaves(self, meeting_holidays):
        """Create calendar meetings without switching to portal-only users."""
        meetings = self.env["calendar.event"]
        if not meeting_holidays:
            return meetings
        meeting_values_for_user_id = meeting_holidays._prepare_holidays_meeting_values()
        Meeting = self.env["calendar.event"]
        ctx = {
            "allowed_company_ids": [],
            "no_mail_to_attendees": True,
            "calendar_no_videocall": True,
            "active_model": self._name,
        }
        for user_id, meeting_values in meeting_values_for_user_id.items():
            user = self.env["res.users"].browse(user_id) if user_id else self.env.user
            if self._is_portal_only_user(user):
                meetings += Meeting.sudo().with_context(**ctx).create(meeting_values)
            else:
                meetings += Meeting.with_user(user_id or self.env.uid).with_context(**ctx).create(
                    meeting_values
                )
        return meetings

    def _validate_leave_request(self):
        """Validate time off requests by creating calendar events and resource leaves."""
        holidays = self.filtered("employee_id")
        holidays._create_resource_leave()
        meeting_holidays = holidays.filtered(lambda leave: leave.holiday_status_id.create_calendar_meeting)
        meetings = self._create_calendar_meetings_for_leaves(meeting_holidays)
        for meeting in meetings:
            self.browse(meeting.res_id).meeting_id = meeting
        for holiday in holidays:
            user_tz = pytz.timezone(holiday.tz)
            utc_tz = pytz.utc.localize(holiday.date_from).astimezone(user_tz)
            notify_partner_ids = holiday.employee_id.user_id.partner_id.ids
            holiday.message_post(
                body=_(
                    "Your %(leave_type)s planned on %(date)s has been accepted",
                    leave_type=holiday.holiday_status_id.display_name,
                    date=utc_tz.replace(tzinfo=None),
                ),
                partner_ids=notify_partner_ids,
            )

    def _get_manager_users_for_activity(self):
        self.ensure_one()
        employee = self.employee_id
        if employee.leave_manager_ids:
            return employee.leave_manager_ids
        if employee.leave_manager_id:
            return employee.leave_manager_id
        return self.env["res.users"]

    def _sync_multi_approver_activities(self):
        activity_type = self.env.ref(
            "hr_holidays.mail_act_leave_approval",
            raise_if_not_found=False,
        )
        if not activity_type:
            return

        model_id = self.env["ir.model"]._get_id("hr.leave")
        today = fields.Date.today()
        for leave in self.filtered(lambda leave: leave.state == "confirm"):
            manager_users = leave._get_manager_users_for_activity()
            if not manager_users:
                continue

            date_deadline = leave.request_date_from or leave.date_from or today
            if date_deadline < today:
                date_deadline = today

            existing = leave.activity_ids.filtered(
                lambda activity: activity.automated
                and activity.activity_type_id == activity_type
            )
            stale_activities = existing.filtered(
                lambda activity: activity.user_id not in manager_users
            )
            if stale_activities:
                stale_activities.unlink()
            current_activities = existing - stale_activities
            if current_activities:
                current_activities.write({"date_deadline": date_deadline})

            users_with_activity = current_activities.mapped("user_id")
            for manager_user in manager_users - users_with_activity:
                self.env["mail.activity"].with_context(short_name=False).create(
                    {
                        "activity_type_id": activity_type.id,
                        "automated": True,
                        "date_deadline": date_deadline,
                        "note": _(
                            "New Time Off request from %(employee)s",
                            employee=leave.employee_id.name,
                        ),
                        "user_id": manager_user.id,
                        "res_id": leave.id,
                        "res_model_id": model_id,
                    }
                )

    def activity_update(self):
        user = self.env.user
        if self._is_portal_only_user(user):
            result = super(HrLeave, self.sudo()).activity_update()
            self.sudo()._sync_multi_approver_activities()
            return result
        portal_created = self.filtered(
            lambda leave: self._is_portal_only_user(leave.user_id)
        )
        if portal_created:
            super(HrLeave, self - portal_created).activity_update()
            result = super(HrLeave, portal_created.sudo()).activity_update()
            portal_created.sudo()._sync_multi_approver_activities()
            return result
        result = super().activity_update()
        self._sync_multi_approver_activities()
        return result
