import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from .approval_access import decision_user


class HrLeave(models.Model):
    _inherit = "hr.leave"

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

    @api.depends("holiday_status_id.leave_validation_type", "employee_id.hr_responsible_ids")
    def _compute_validation_type(self):
        for leave in self:
            base = leave.holiday_status_id.leave_validation_type
            if leave.employee_id.hr_responsible_ids and base and base != "no_validation":
                leave.validation_type = "both"
            else:
                leave.validation_type = base

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
            return employee.leave_manager_ids or employee.leave_manager_id
        return self.env["res.users"]

    def _time_off_approver_users(self):
        self.ensure_one()
        approvers = self.employee_id.leave_manager_ids
        if self.employee_id.leave_manager_id:
            approvers |= self.employee_id.leave_manager_id
        return approvers

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

    def _check_double_validation_rules(self, employees, state):
        # create() passes employee_id as int; write() passes an hr.employee recordset.
        if not isinstance(employees, models.BaseModel):
            employees = (
                self.env["hr.employee"].browse(employees)
                if employees
                else self.env["hr.employee"]
            )

        user = decision_user(self)
        assigned = self.filtered(lambda leave: leave._uses_assigned_approvers())
        for leave in assigned:
            if state == "validate1" and user not in leave.employee_id.hr_responsible_ids:
                raise AccessError(
                    _(
                        "Only HR Responsibles can give the first approval for %(employee)s.",
                        employee=leave.employee_id.name,
                    )
                )
            if state == "validate" and user not in leave._time_off_approver_users():
                raise AccessError(_("Only Time Off Approvers can give the second approval."))
            if state == "refuse" and leave.state in ("confirm", "validate1") and not leave._user_can_approve_current_step():
                if leave.state == "confirm":
                    raise AccessError(
                        _(
                            "Only HR Responsibles can give the first approval for %(employee)s.",
                            employee=leave.employee_id.name,
                        )
                    )
                raise AccessError(_("Only Time Off Approvers can give the second approval."))
        others = employees - assigned.employee_id
        if others:
            super(HrLeave, self - assigned)._check_double_validation_rules(others, state)

    def _sync_multi_approver_activities(self):
        first_type = self.env.ref(
            "hr_holidays.mail_act_leave_approval",
            raise_if_not_found=False,
        )
        second_type = self.env.ref(
            "hr_holidays.mail_act_leave_second_approval",
            raise_if_not_found=False,
        )
        approval_types = (first_type | second_type) if first_type and second_type else first_type or second_type
        if not approval_types:
            return

        model_id = self.env["ir.model"]._get_id("hr.leave")
        today = fields.Date.today()
        for leave in self.filtered(lambda item: item.validation_type == "both"):
            if leave.state == "confirm":
                users = leave.employee_id.hr_responsible_ids
                activity_type = first_type
                note = _(
                    "New Time Off request from %(employee)s",
                    employee=leave.employee_id.name,
                )
            elif leave.state == "validate1":
                users = leave._time_off_approver_users() if leave.employee_id.hr_responsible_ids else self.env["res.users"]
                activity_type = second_type
                note = _(
                    "Second approval request for %(leave_type)s",
                    leave_type=leave.holiday_status_id.display_name,
                )
            else:
                users = self.env["res.users"]
                activity_type = False

            existing = leave.activity_ids.filtered(
                lambda activity: activity.automated and activity.activity_type_id in approval_types
            )
            if not activity_type or not users:
                if existing:
                    existing.unlink()
                continue

            date_deadline = leave.request_date_from or (
                leave.date_from.date() if leave.date_from else False
            ) or today
            if date_deadline < today:
                date_deadline = today

            stale_activities = existing.filtered(
                lambda activity: activity.activity_type_id != activity_type
                or activity.user_id not in users
            )
            if stale_activities:
                stale_activities.unlink()
            current_activities = existing - stale_activities
            if current_activities:
                current_activities.write({"date_deadline": date_deadline})
            for user in users - current_activities.mapped("user_id"):
                self.env["mail.activity"].with_context(short_name=False).create(
                    {
                        "activity_type_id": activity_type.id,
                        "automated": True,
                        "date_deadline": date_deadline,
                        "note": note,
                        "user_id": user.id,
                        "res_id": leave.id,
                        "res_model_id": model_id,
                    }
                )

    def action_approve(self, check_state=True):
        for leave in self.filtered(lambda item: item._uses_assigned_approvers()):
            if not leave._user_can_approve_current_step():
                if leave.state == "confirm":
                    raise UserError(
                        _(
                            "Only HR Responsibles can give the first approval for %(employee)s.",
                            employee=leave.employee_id.name,
                        )
                    )
                raise UserError(_("Only Time Off Approvers can give the second approval."))
        first_step = self.filtered(
            lambda leave: leave._uses_assigned_approvers() and leave.state == "confirm"
        )
        if first_step:
            first_step.write(
                {
                    "state": "validate1",
                    "first_approver_id": self.env.user.employee_id.id,
                }
            )
            if not self.env.context.get("leave_fast_create"):
                first_step.activity_update()
        remaining = self - first_step
        if remaining:
            super(HrLeave, remaining).action_approve(check_state=check_state)
        return True

    def _check_portal_admin_decision(self):
        self.ensure_one()
        user = decision_user(self)
        if not user.has_group("attendance_location_portal.group_portal_hr_admin"):
            raise UserError(_("Only portal administrators can approve or refuse requests."))
        if self.employee_id.user_id == user:
            raise UserError(_("You cannot approve or refuse your own request."))
        if self.company_id and self.company_id not in user.company_ids:
            raise UserError(_("This time off request is not accessible."))

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
        leave = self.sudo()
        if leave.state not in ("confirm", "validate1"):
            raise UserError(_("Only requests pending approval can be approved."))
        approver = self.env.user.employee_id
        if leave.validation_type == "both" and leave.state == "confirm":
            leave.write({
                "state": "validate1",
                "first_approver_id": approver.id,
            })
            leave.activity_update()
            return True
        leave._action_validate(check_state=False)
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
        leave = self.sudo()
        if leave.state not in ("confirm", "validate", "validate1"):
            raise UserError(_("Only pending or approved time off can be refused."))
        leave.action_refuse()
        return True

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
