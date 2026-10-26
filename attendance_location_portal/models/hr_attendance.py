import logging
from datetime import timedelta

from pytz import timezone, utc

from odoo import _, api, fields, models
from odoo.tools import email_normalize, format_datetime

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = ["hr.attendance", "mail.activity.mixin"]

    check_in = fields.Datetime(
        string="Check In",
        required=False,
        default=False,
        tracking=True,
        index=True,
    )
    portal_checkout_without_checkin = fields.Boolean(
        string="Portal Checkout Without Checkin",
        readonly=True,
        copy=False,
    )
    portal_action_type = fields.Selection(
        [
            ("check_in", "Check In"),
            ("check_out", "Check Out"),
        ],
        string="Portal Attendance Action",
        readonly=True,
        copy=False,
        tracking=True,
    )
    portal_note = fields.Text(string="Note", tracking=True)
    attendance_location_id = fields.Many2one(
        "attendance.location",
        string="Attendance Location",
        readonly=True,
        copy=False,
        tracking=True,
    )
    has_approved_adjustment_request = fields.Boolean(
        string="Has Approved Adjustment Request",
        readonly=True,
        copy=False,
        tracking=True,
    )
    approved_adjustment_minutes = fields.Integer(
        string="Approved Adjustment Minutes",
        readonly=True,
        copy=False,
        tracking=True,
        help="Total approved attendance adjustment minutes applied on this attendance.",
    )
    adjustment_check_in_time = fields.Datetime(
        string="Check In Time",
        compute="_compute_adjustment_preview_times",
    )
    adjustment_actual_time = fields.Datetime(
        string="Actual Time",
        compute="_compute_adjustment_preview_times",
    )
    adjustment_updated_time = fields.Datetime(
        string="Updated Time",
        compute="_compute_adjustment_preview_times",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
        tracking=True,
        help="Company of the attendance location used for check-in.",
    )
    in_mode = fields.Selection(
        selection_add=[("automatic", "Automatic")],
        ondelete={"automatic": "set default"},
    )
    out_mode = fields.Selection(
        selection_add=[("automatic", "Automatic")],
        ondelete={"automatic": "set default"},
    )

    @api.model
    def _company_from_vals(self, vals):
        """Always prefer the location company when a location is set."""
        location_id = vals.get("attendance_location_id")
        if location_id:
            location = self.env["attendance.location"].sudo().browse(location_id)
            if location.company_id:
                return location.company_id.id
        if vals.get("company_id"):
            return vals["company_id"]
        employee_id = vals.get("employee_id")
        if employee_id:
            employee = self.env["hr.employee"].sudo().browse(employee_id)
            if employee.company_id:
                return employee.company_id.id
        return self.env.company.id

    @api.depends("check_in", "check_out", "employee_id")
    def _compute_date(self):
        """Use check_out when check_in is empty (portal checkout-first rows)."""
        for attendance in self:
            dt = attendance.check_in or attendance.check_out
            if not attendance.employee_id or not dt:
                attendance.date = fields.Date.context_today(attendance)
                continue
            tz = timezone(attendance.employee_id._get_tz())
            attendance.date = utc.localize(fields.Datetime.to_datetime(dt)).astimezone(tz).date()

    @api.constrains("check_in", "check_out")
    def _check_validity_check_in_check_out(self):
        # Soft validation: warnings are handled after create/write.
        return

    @api.constrains("check_in", "check_out", "employee_id")
    def _check_validity(self):
        # Soft validation: warnings are handled after create/write.
        return

    def _collect_attendance_validity_warnings(self):
        self.ensure_one()
        attendance = self
        warnings = []

        if (
            attendance.check_in
            and attendance.check_out
            and attendance.check_out < attendance.check_in
        ):
            warnings.append(
                _(
                    'تحذير: وقت "تسجيل الخروج" قبل وقت "تسجيل الحضور". '
                    "يرجى مراجعة سجل الحضور."
                )
            )

        if not attendance.check_in or not attendance.employee_id:
            return warnings

        last_attendance_before_check_in = self.env["hr.attendance"].search(
            [
                ("employee_id", "=", attendance.employee_id.id),
                ("check_in", "<=", attendance.check_in),
                ("id", "!=", attendance.id),
            ],
            order="check_in desc",
            limit=1,
        )
        if (
            last_attendance_before_check_in
            and last_attendance_before_check_in.check_out
            and last_attendance_before_check_in.check_out > attendance.check_in
        ):
            warnings.append(
                _(
                    "تحذير: %(empl_name)s مسجّل حضوره مسبقاً في %(datetime)s. "
                    "يرجى التحقق من سجلات الحضور المتداخلة.",
                    empl_name=attendance.employee_id.name,
                    datetime=format_datetime(
                        self.env, attendance.check_in, dt_format=False
                    ),
                )
            )

        if not attendance.check_out:
            open_attendance = attendance._get_prior_open_attendance()
            if open_attendance:
                warnings.append(
                    _(
                        "تحذير: لم يسجّل %(empl_name)s انصرافه منذ %(datetime)s. "
                        "يرجى التحقق من سجلات الحضور المفتوحة.",
                        empl_name=attendance.employee_id.name,
                        datetime=format_datetime(
                            self.env, open_attendance.check_in, dt_format=False
                        ),
                    )
                )
        else:
            last_attendance_before_check_out = self.env["hr.attendance"].search(
                [
                    ("employee_id", "=", attendance.employee_id.id),
                    ("check_in", "<", attendance.check_out),
                    ("id", "!=", attendance.id),
                ],
                order="check_in desc",
                limit=1,
            )
            if (
                last_attendance_before_check_out
                and last_attendance_before_check_in != last_attendance_before_check_out
            ):
                warnings.append(
                    _(
                        "تحذير: %(empl_name)s مسجّل حضوره مسبقاً في %(datetime)s. "
                        "يرجى التحقق من سجلات الحضور المتداخلة.",
                        empl_name=attendance.employee_id.name,
                        datetime=format_datetime(
                            self.env,
                            last_attendance_before_check_out.check_in,
                            dt_format=False,
                        ),
                    )
                )

        return warnings

    def _get_prior_open_attendance(self):
        """Previous open check-in (no check-out) for the same employee."""
        self.ensure_one()
        if not self.employee_id:
            return self.env["hr.attendance"]
        return self.env["hr.attendance"].search(
            [
                ("employee_id", "=", self.employee_id.id),
                ("check_out", "=", False),
                ("check_in", "!=", False),
                ("id", "!=", self.id),
            ],
            order="check_in desc",
            limit=1,
        )

    def _schedule_missing_checkout_hr_activity(self):
        """Notify HR Responsible about an open attendance without check-out.

        Activity is created on the open (empty check-out) record so opening it
        takes HR directly to that attendance line.
        """
        self.ensure_one()
        open_attendance = self._get_prior_open_attendance()
        if not open_attendance:
            return open_attendance

        employee = open_attendance.employee_id.sudo()
        responsible_users = employee.hr_responsible_ids or employee.hr_responsible_id
        if not responsible_users:
            return open_attendance

        check_in_display = format_datetime(
            self.env, open_attendance.check_in, dt_format=False
        )
        summary = _("حضور بدون انصراف: %s") % employee.name
        note = _(
            "الموظف %(employee)s سجّل حضوراً جديداً دون إغلاق سجل الحضور السابق "
            "(بدون انصراف) منذ %(datetime)s.\n"
            "يرجى فتح سجل الحضور وإكمال وقت الانصراف."
        ) % {
            "employee": employee.name,
            "datetime": check_in_display,
        }

        for responsible in responsible_users:
            existing_activity = self.env["mail.activity"].sudo().search(
                [
                    ("res_model", "=", "hr.attendance"),
                    ("res_id", "=", open_attendance.id),
                    ("user_id", "=", responsible.id),
                    ("summary", "=", summary),
                ],
                limit=1,
            )
            if existing_activity:
                existing_activity.write({"note": note})
                continue

            open_attendance.sudo().activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=responsible.id,
                summary=summary,
                note=note,
            )
        return open_attendance

    def _notify_attendance_validity_warnings(self):
        if self.env.context.get("skip_attendance_validity_notification"):
            return []
        all_warnings = []
        for attendance in self:
            warnings = attendance._collect_attendance_validity_warnings()
            if not warnings:
                continue
            message = "\n".join(warnings)
            all_warnings.extend(warnings)
            attendance.message_post(
                body=message,
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )
            if self.env.user.has_group("base.group_user"):
                self.env.user._bus_send(
                    "simple_notification",
                    {
                        "type": "warning",
                        "title": _("تحذير الحضور"),
                        "message": message,
                    },
                )
        return all_warnings

    @api.depends("check_in", "check_out", "worked_hours", "out_mode")
    def _compute_color(self):
        stale_checkin_limit = fields.Datetime.now() - timedelta(days=1)
        for attendance in self:
            if attendance.check_out:
                attendance.color = (
                    1
                    if attendance.worked_hours > 16
                    or attendance.out_mode == "technical"
                    else 0
                )
            elif not attendance.check_in:
                attendance.color = 0
            else:
                attendance.color = 1 if attendance.check_in < stale_checkin_limit else 10

    def _get_overtimes_to_update_domain(self):
        attendances_with_check_in = self.filtered("check_in")
        if not attendances_with_check_in:
            return [("id", "=", 0)]
        return super(
            HrAttendance, attendances_with_check_in
        )._get_overtimes_to_update_domain()

    def _update_overtime(self, attendance_domain=None):
        attendances = self.filtered("check_in")
        if not self.env.context.get("ignore_overtime_singleton_error"):
            return super(HrAttendance, attendances)._update_overtime(
                attendance_domain=attendance_domain
            )
        # Public-holiday creation recalculates overtime for every attendance
        # on that day. Overlapping attendances are merged into one recordset,
        # and core then reads check_in on that recordset. Roll back only the
        # overtime change and let the holiday save continue.
        try:
            with self.env.cr.savepoint():
                return super(HrAttendance, attendances)._update_overtime(
                    attendance_domain=attendance_domain
                )
        except ValueError as error:
            if "Expected singleton" not in str(error):
                raise
            _logger.warning(
                "Skipped attendance overtime update while saving public holidays: %s",
                error,
            )

    def _create_work_entries(self):
        # Enterprise hr_work_entry_attendance crashes on min(check_in) when
        # portal checkout-first rows leave check_in empty (False).
        valid = self.filtered(lambda attendance: attendance.check_in and attendance.check_out)
        if not valid:
            return
        return super(HrAttendance, valid)._create_work_entries()

    @api.depends("check_in", "has_approved_adjustment_request", "approved_adjustment_minutes")
    def _compute_adjustment_preview_times(self):
        request_model = self.env["hr.attendance.adjustment.request"]
        for attendance in self:
            attendance.adjustment_check_in_time = attendance.check_in or False
            attendance.adjustment_actual_time = False
            attendance.adjustment_updated_time = False
            if not attendance.check_in and not attendance.check_out:
                continue
            requests = request_model.sudo().search([
                ("applied_attendance_id", "=", attendance.id),
                ("state", "=", "approve"),
                ("adjustment_applied", "=", True),
            ])
            if not requests:
                continue
            latest_request = requests.sorted("id", reverse=True)[:1]
            if latest_request.applied_actual_time and latest_request.applied_updated_time:
                attendance.adjustment_actual_time = latest_request.applied_actual_time
                attendance.adjustment_updated_time = latest_request.applied_updated_time
            elif latest_request.request_type == "late_arrival" and attendance.check_in:
                attendance.adjustment_updated_time = attendance.check_in
                attendance.adjustment_actual_time = attendance.check_in + timedelta(
                    minutes=latest_request.time_minutes or 0
                )
            elif latest_request.request_type == "early_departure" and attendance.check_out:
                attendance.adjustment_updated_time = attendance.check_out
                attendance.adjustment_actual_time = attendance.check_out - timedelta(
                    minutes=latest_request.time_minutes or 0
                )

    def _apply_pending_approved_adjustments(self):
        if self.env.context.get("skip_pending_adjustment_apply"):
            return
        adjustment_request_model = self.env["hr.attendance.adjustment.request"].sudo()
        for attendance in self:
            if not attendance.employee_id:
                continue
            if attendance.check_in:
                attendance_date = fields.Datetime.to_datetime(attendance.check_in).date()
            elif attendance.check_out:
                attendance_date = fields.Datetime.to_datetime(attendance.check_out).date()
            else:
                continue
            pending_requests = adjustment_request_model.search(
                [
                    ("employee_id", "=", attendance.employee_id.id),
                    ("date", "=", attendance_date),
                    ("state", "=", "approve"),
                    ("adjustment_applied", "=", False),
                ],
                order="id asc",
            )
            for request in pending_requests:
                request._apply_approved_adjustment_to_attendance(attendance=attendance)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["company_id"] = self._company_from_vals(vals)
        records = super().create(vals_list)
        records._apply_pending_approved_adjustments()
        records._notify_attendance_validity_warnings()
        records.filtered(
            lambda record: record.portal_note and record.check_out
        )._schedule_manager_note_activity()
        return records

    def write(self, vals):
        if vals.get("attendance_location_id"):
            location = (
                self.env["attendance.location"]
                .sudo()
                .browse(vals["attendance_location_id"])
            )
            if location.company_id:
                vals = dict(vals, company_id=location.company_id.id)

        if "check_in" in vals and "portal_checkout_without_checkin" not in vals:
            vals = dict(vals, portal_checkout_without_checkin=False)

        note_updated = "portal_note" in vals and vals.get("portal_note")
        previous_notes = (
            {record.id: record.portal_note for record in self} if note_updated else {}
        )

        # Enterprise write builds min(check_in) for open attendances being closed.
        # Split checkout-only rows so that path never sees False check_in values.
        checkout_only = self.env["hr.attendance"]
        if vals.get("check_out") and not vals.get("check_in"):
            checkout_only = self.filtered(
                lambda attendance: not attendance.check_out and not attendance.check_in
            )
        others = self - checkout_only
        result = True
        if others:
            result = super(HrAttendance, others).write(vals)
        if checkout_only:
            work_entry_cls = next(
                (
                    cls
                    for cls in type(checkout_only).__mro__
                    if cls.__module__.endswith(
                        "hr_work_entry_attendance.models.hr_attendance"
                    )
                ),
                None,
            )
            if work_entry_cls:
                # Skip enterprise write (needs real check_in timestamps).
                result = super(work_entry_cls, checkout_only).write(vals)
            else:
                result = super(HrAttendance, checkout_only).write(vals)

        if {"check_in", "check_out", "employee_id"} & set(vals.keys()):
            self._apply_pending_approved_adjustments()
            self._notify_attendance_validity_warnings()
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
