from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .approval_access import decision_user


class HrAttendanceAdjustmentRequest(models.Model):
    _name = "hr.attendance.adjustment.request"
    _description = "Attendance Adjustment Request"
    _order = "date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(compute="_compute_name", store=True)
    request_type = fields.Selection(
        [
            ("early_departure", "Request for early departure"),
            ("late_arrival", "Late arrival request"),
        ],
        string="Type",
        required=True,
        tracking=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        required=True,
        tracking=True,
        index=True,
    )
    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    time_minutes = fields.Integer(
        string="Time (minutes)",
        required=True,
        tracking=True,
    )
    description = fields.Text(
        string="Description",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("confirm", "To Approve"),
            ("validate1", "Second Approval"),
            ("approve", "Approved"),
            ("refuse", "Refused"),
        ],
        string="Status",
        default="confirm",
        required=True,
        tracking=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related="employee_id.company_id",
        store=True,
        readonly=True,
    )
    adjustment_applied = fields.Boolean(
        string="Adjustment Applied",
        default=False,
        readonly=True,
        copy=False,
        tracking=True,
    )
    applied_attendance_id = fields.Many2one(
        "hr.attendance",
        string="Applied Attendance",
        readonly=True,
        copy=False,
        tracking=True,
    )
    can_approve_refuse = fields.Boolean(compute="_compute_can_approve_refuse")
    portal_state_label = fields.Char(compute="_compute_portal_state_label")
    request_type_label = fields.Char(compute="_compute_request_type_label")
    actual_time = fields.Datetime(
        string="Actual Time",
        compute="_compute_actual_updated_time",
    )
    updated_time = fields.Datetime(
        string="Updated Time",
        compute="_compute_actual_updated_time",
    )
    attendance_check_in_time = fields.Datetime(
        string="Check In Time",
        compute="_compute_actual_updated_time",
    )
    workday_start_time = fields.Datetime(
        string="Workday Start Time",
        compute="_compute_actual_updated_time",
        help="Planned start time from the employee working schedule on request date.",
    )
    workday_end_time = fields.Datetime(
        string="Workday End Time",
        compute="_compute_actual_updated_time",
        help="Planned end time from the employee working schedule on request date.",
    )
    applied_actual_time = fields.Datetime(
        string="Applied Actual Time",
        readonly=True,
        copy=False,
        tracking=True,
    )
    applied_updated_time = fields.Datetime(
        string="Applied Updated Time",
        readonly=True,
        copy=False,
        tracking=True,
    )
    applied_effective_minutes = fields.Integer(
        string="Applied Effective Minutes",
        readonly=True,
        copy=False,
        tracking=True,
    )

    @api.depends("employee_id", "date", "request_type")
    def _compute_name(self):
        type_labels = dict(self._fields["request_type"].selection)
        for request in self:
            if request.employee_id and request.date and request.request_type:
                request.name = _("%(type)s - %(employee)s - %(date)s") % {
                    "type": type_labels.get(request.request_type, request.request_type),
                    "employee": request.employee_id.name,
                    "date": request.date,
                }
            else:
                request.name = _("Attendance Adjustment Request")

    @api.depends("request_type")
    def _compute_request_type_label(self):
        selection = dict(self._fields["request_type"].selection)
        for request in self:
            request.request_type_label = selection.get(request.request_type, request.request_type)

    @api.depends("state")
    def _compute_portal_state_label(self):
        selection = dict(self._fields["state"].selection)
        for request in self:
            request.portal_state_label = selection.get(request.state, request.state)

    @api.depends("state")
    def _compute_can_approve_refuse(self):
        for request in self:
            request.can_approve_refuse = request._user_can_decide()

    def _portal_state_badge_class(self):
        self.ensure_one()
        return {
            "confirm": "text-bg-warning",
            "validate1": "text-bg-info",
            "approve": "text-bg-success",
            "refuse": "text-bg-danger",
        }.get(self.state, "text-bg-secondary")

    def _is_portal_only_user(self, user):
        if not user:
            return False
        return user.has_group("base.group_portal") and not user.has_group("base.group_user")

    def _second_approver_users(self):
        self.ensure_one()
        employee = self.employee_id
        approvers = employee.leave_manager_ids
        if employee.leave_manager_id:
            approvers |= employee.leave_manager_id
        return approvers

    def _activity_users(self):
        self.ensure_one()
        employee = self.employee_id
        if not employee.hr_responsible_ids:
            return self.env["res.users"]
        if self.state == "confirm":
            return employee.hr_responsible_ids
        if self.state == "validate1":
            return self._second_approver_users()
        return self.env["res.users"]

    def _user_can_decide(self):
        self.ensure_one()
        user = decision_user(self)
        is_manager = user.has_group("hr_holidays.group_hr_holidays_manager")
        is_portal_admin = user.has_group("attendance_location_portal.group_portal_hr_admin")
        employee = self.employee_id
        if is_portal_admin and not is_manager:
            if employee.user_id == user:
                return False
            if self.company_id and self.company_id not in user.company_ids:
                return False
        if self.state == "confirm":
            if employee.hr_responsible_ids:
                return user in employee.hr_responsible_ids
            return is_manager or is_portal_admin
        if self.state == "validate1":
            return user in self._second_approver_users()
        return False

    def _get_to_clean_activities(self):
        return ["attendance_location_portal.mail_act_attendance_adjustment_approval"]

    def _activity_update_impl(self):
        to_clean = self.env["hr.attendance.adjustment.request"]
        to_do = self.env["hr.attendance.adjustment.request"]
        activity_vals = []
        today = fields.Date.today()
        model_id = self.env["ir.model"]._get_id("hr.attendance.adjustment.request")
        activity_type = self.env.ref(
            "attendance_location_portal.mail_act_attendance_adjustment_approval",
            raise_if_not_found=False,
        )
        if not activity_type:
            activity_type = self.env.ref("mail.mail_activity_data_todo")

        for request in self:
            if request.state in ("confirm", "validate1"):
                manager_users = request.sudo()._activity_users()
                if not manager_users:
                    existing = request.activity_ids.filtered(
                        lambda activity: activity.automated
                        and activity.activity_type_id == activity_type
                    )
                    if existing:
                        existing.unlink()
                    continue
                date_deadline = request.date or today
                if date_deadline < today:
                    date_deadline = today
                existing = request.activity_ids.filtered(
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
                    activity_vals.append(
                        {
                            "activity_type_id": activity_type.id,
                            "automated": True,
                            "date_deadline": date_deadline,
                            "note": _(
                                "Second approval request from %(employee)s",
                                employee=request.employee_id.name,
                            )
                            if request.state == "validate1"
                            else _(
                                "New Attendance Adjustment Request from %(employee)s",
                                employee=request.employee_id.name,
                            ),
                            "user_id": manager_user.id,
                            "res_id": request.id,
                            "res_model_id": model_id,
                        }
                    )
            elif request.state == "approve":
                to_do |= request
            elif request.state == "refuse":
                to_clean |= request

        if to_clean:
            to_clean.activity_unlink(self._get_to_clean_activities(), only_automated=False)
        if to_do:
            to_do.activity_feedback(self._get_to_clean_activities())
        if activity_vals:
            self.env["mail.activity"].with_context(short_name=False).create(activity_vals)

    def activity_update(self):
        if self.env.context.get("mail_activity_automation_skip"):
            return
        user = self.env.user
        if self._is_portal_only_user(user):
            return self.sudo()._activity_update_impl()
        portal_created = self.filtered(
            lambda request: self._is_portal_only_user(request.employee_id.user_id)
        )
        if portal_created:
            (self - portal_created)._activity_update_impl()
            return portal_created.sudo()._activity_update_impl()
        return self._activity_update_impl()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.activity_update()
        return records

    def write(self, vals):
        result = super().write(vals)
        if "state" in vals:
            self.activity_update()
        return result

    @api.depends("employee_id", "date", "request_type", "time_minutes", "state", "adjustment_applied")
    def _compute_actual_updated_time(self):
        for request in self:
            request.actual_time = False
            request.updated_time = False
            request.attendance_check_in_time = False
            workday_start, workday_end = request._get_workday_bounds()
            request.workday_start_time = workday_start
            request.workday_end_time = workday_end
            attendance = request.applied_attendance_id or request._get_attendance_for_adjustment()
            if not attendance:
                continue
            request.attendance_check_in_time = attendance.check_in
            if request.adjustment_applied and request.applied_actual_time and request.applied_updated_time:
                request.actual_time = request.applied_actual_time
                request.updated_time = request.applied_updated_time
                continue
            if request.request_type == "late_arrival":
                if not attendance.check_in:
                    continue
                if request.adjustment_applied:
                    request.updated_time = attendance.check_in
                    request.actual_time = attendance.check_in + timedelta(minutes=request.time_minutes)
                else:
                    request.actual_time = attendance.check_in
                    request.updated_time = request._get_updated_check_in(attendance)
            else:
                if not attendance.check_out:
                    continue
                if request.adjustment_applied:
                    request.updated_time = attendance.check_out
                    request.actual_time = attendance.check_out - timedelta(minutes=request.time_minutes)
                else:
                    request.actual_time = attendance.check_out
                    request.updated_time = request._get_updated_check_out(attendance)

    def _get_attendance_for_adjustment(self):
        self.ensure_one()
        day_start = datetime.combine(self.date, time.min)
        day_end = day_start + timedelta(days=1)
        attendances = self.env["hr.attendance"].sudo().search([
            ("employee_id", "=", self.employee_id.id),
            "|",
            "&",
            ("check_in", ">=", fields.Datetime.to_string(day_start)),
            ("check_in", "<", fields.Datetime.to_string(day_end)),
            "&",
            ("check_out", ">=", fields.Datetime.to_string(day_start)),
            ("check_out", "<", fields.Datetime.to_string(day_end)),
        ])
        if self.request_type == "late_arrival":
            return attendances.filtered("check_in").sorted("check_in")[:1]
        return attendances.filtered("check_out").sorted(
            key=lambda attendance: attendance.check_out,
            reverse=True,
        )[:1]

    def _get_workday_bounds(self):
        self.ensure_one()
        if not self.employee_id or not self.date:
            return False, False
        version = self.employee_id._get_version(self.date)
        calendar = (version and version.resource_calendar_id) or self.employee_id.resource_calendar_id
        if not calendar:
            return False, False
        employee_tz = self.employee_id.tz or self.env.user.tz or "UTC"
        tz = pytz.timezone(employee_tz)
        day_start = datetime.combine(self.date, time.min)
        day_end = day_start + timedelta(days=1)
        if hasattr(calendar, "att_get_work_intervals"):
            work_intervals = calendar.att_get_work_intervals(self, day_start, day_end, tz)
        else:
            start_localized = tz.localize(day_start)
            end_localized = tz.localize(day_end)
            attendance_intervals = calendar._attendance_intervals(start_localized, end_localized)
            work_intervals = [
                (
                    start.astimezone(pytz.UTC).replace(tzinfo=None),
                    end.astimezone(pytz.UTC).replace(tzinfo=None),
                )
                for start, end, _meta in attendance_intervals
            ]
        if not work_intervals:
            return False, False
        return (
            min(start for start, _end in work_intervals),
            max(end for _start, end in work_intervals),
        )

    def _get_updated_check_in(self, attendance):
        self.ensure_one()
        updated_check_in = attendance.check_in - timedelta(minutes=self.time_minutes)
        workday_start, _workday_end = self._get_workday_bounds()
        if workday_start and updated_check_in < workday_start:
            return workday_start
        return updated_check_in

    def _get_updated_check_out(self, attendance):
        self.ensure_one()
        updated_check_out = attendance.check_out + timedelta(minutes=self.time_minutes)
        _workday_start, workday_end = self._get_workday_bounds()
        if workday_end and updated_check_out > workday_end:
            return workday_end
        return updated_check_out

    def _apply_approved_adjustment_to_attendance(self, attendance=None):
        self.ensure_one()
        if self.adjustment_applied:
            return True
        attendance = attendance or self._get_attendance_for_adjustment()
        if not attendance:
            return False
        update_vals = {
            "has_approved_adjustment_request": True,
            "approved_adjustment_minutes": attendance.approved_adjustment_minutes + self.time_minutes,
        }
        if self.request_type == "late_arrival":
            if not attendance.check_in:
                return False
            actual_time = attendance.check_in
            updated_time = self._get_updated_check_in(attendance)
            update_vals["check_in"] = updated_time
            effective_minutes = int(round((actual_time - updated_time).total_seconds() / 60.0))
        else:
            if not attendance.check_out:
                return False
            actual_time = attendance.check_out
            updated_time = self._get_updated_check_out(attendance)
            update_vals["check_out"] = updated_time
            effective_minutes = int(round((updated_time - actual_time).total_seconds() / 60.0))
        attendance.sudo().with_context(
            skip_attendance_validity_notification=True,
            skip_pending_adjustment_apply=True,
        ).write(update_vals)
        self.sudo().write({
            "adjustment_applied": True,
            "applied_attendance_id": attendance.id,
            "applied_actual_time": actual_time,
            "applied_updated_time": updated_time,
            "applied_effective_minutes": effective_minutes,
        })
        return True

    def action_approve(self):
        if any(not request._user_can_decide() for request in self):
            raise UserError(_("Only HR Responsibles or Time Off Approvers can approve this attendance adjustment request."))
        first_step = self.filtered(
            lambda request: request.state == "confirm" and request.employee_id.hr_responsible_ids
        )
        final_step = self.filtered(
            lambda request: request.state == "validate1"
            or (request.state == "confirm" and not request.employee_id.hr_responsible_ids)
        )
        if len(first_step) + len(final_step) != len(self):
            raise UserError(_("Only requests pending approval can be approved."))
        if first_step:
            first_step.sudo().write({"state": "validate1"})
        if final_step:
            for request in final_step:
                request._apply_approved_adjustment_to_attendance()
            final_step.sudo().write({"state": "approve"})
            for request in final_step:
                partner = request.employee_id.user_id.partner_id
                if partner:
                    request.sudo().message_post(
                        body=_("Your attendance adjustment request has been approved."),
                        partner_ids=partner.ids,
                    )
        return True

    def action_refuse(self):
        if any(not request._user_can_decide() for request in self):
            raise UserError(_("Only HR Responsibles or Time Off Approvers can refuse this attendance adjustment request."))
        requests = self.filtered(lambda request: request.state in ("confirm", "validate1"))
        if len(requests) != len(self):
            raise UserError(_("Only requests pending approval can be refused."))
        requests.sudo().write({"state": "refuse"})
        for request in requests:
            partner = request.employee_id.user_id.partner_id
            if partner:
                request.sudo().message_post(
                    body=_("Your attendance adjustment request has been refused."),
                    partner_ids=partner.ids,
                )
        return True
