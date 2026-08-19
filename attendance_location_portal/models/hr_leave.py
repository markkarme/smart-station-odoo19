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

    def activity_update(self):
        user = self.env.user
        if self._is_portal_only_user(user):
            return super(HrLeave, self.sudo()).activity_update()
        portal_created = self.filtered(
            lambda leave: self._is_portal_only_user(leave.user_id)
        )
        if portal_created:
            super(HrLeave, self - portal_created).activity_update()
            return super(HrLeave, portal_created.sudo()).activity_update()
        return super().activity_update()
