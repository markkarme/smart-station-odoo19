from datetime import datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrAttendanceAbsentReport(models.Model):
    _name = "hr.attendance.absent.report"
    _description = "Absent Employees"
    _order = "date, status, employee_id"
    _rec_name = "employee_id"

    date = fields.Date(string="Date", required=True, index=True)
    date_from = fields.Date(string="Date From", required=True, index=True)
    date_to = fields.Date(string="Date To", required=True, index=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True, index=True)
    status = fields.Selection(
        [
            ("absent", "Absent"),
            ("on_leave", "On Leave"),
            ("worked_time_off", "Worked Time Off"),
            ("weekend", "Weekend"),
            ("public_holiday", "Public Holiday"),
        ],
        string="Status",
        required=True,
    )


class HrAttendanceAbsentWizard(models.TransientModel):
    _name = "hr.attendance.absent.wizard"
    _description = "Select Date for Absent Employees"

    date_from = fields.Date(
        string="Date From",
        required=True,
        default=fields.Date.context_today,
    )
    date_to = fields.Date(
        string="Date To",
        required=True,
        default=fields.Date.context_today,
    )

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_from > wizard.date_to:
                raise ValidationError(_("Date From cannot be after Date To."))

    @api.model
    def _is_worked_time_leave(self, leave):
        """Detect validated leaves that should be counted as worked time."""
        leave_type = leave.holiday_status_id
        if not leave_type:
            return False

        # Newer Odoo versions expose this directly on leave type.
        if "time_type" in leave_type._fields:
            return leave_type.time_type not in ("leave", "absence")

        # Fallback for payroll/work-entry integrations.
        work_entry_type = False
        if "work_entry_type_id" in leave._fields:
            work_entry_type = leave.work_entry_type_id
        elif "work_entry_type_id" in leave_type._fields:
            work_entry_type = leave_type.work_entry_type_id
        if work_entry_type and "is_leave" in work_entry_type._fields:
            return not work_entry_type.is_leave

        return False

    @api.model
    def _is_weekend_for_employee(self, employee, current_date):
        calendar = employee.resource_calendar_id or employee.company_id.resource_calendar_id
        if not calendar:
            return False
        weekday = str(current_date.weekday())
        attendance_lines = calendar.attendance_ids.filtered(lambda att: att.dayofweek == weekday)
        return not bool(attendance_lines)

    @api.model
    def _is_public_holiday(self, public_holidays, employee, current_date):
        employee_calendar = employee.resource_calendar_id or employee.company_id.resource_calendar_id
        for holiday in public_holidays:
            if not holiday.date_from or not holiday.date_to:
                continue
            if not (fields.Date.to_date(holiday.date_from) <= current_date <= fields.Date.to_date(holiday.date_to)):
                continue
            applied_calendars = holiday.calendar_ids or holiday.calendar_id
            if not applied_calendars or (employee_calendar and employee_calendar in applied_calendars):
                return True
        return False

    def action_compute(self):
        self.ensure_one()
        report = self.env["hr.attendance.absent.report"]
        report.search(
            [
                ("date_from", "=", self.date_from),
                ("date_to", "=", self.date_to),
            ]
        ).unlink()

        all_employees = self.env["hr.employee"].search(
            [("active", "=", True), ("name", "not in", ["Administrator", "Admin"])]
        )
        period_start = datetime.combine(self.date_from, time.min)
        period_end = datetime.combine(self.date_to, time.max)

        attendances = self.env["hr.attendance"].search(
            [
                "|",
                "&",
                ("check_in", ">=", period_start),
                ("check_in", "<=", period_end),
                "&",
                ("check_out", ">=", period_start),
                ("check_out", "<=", period_end),
            ]
        )
        present_by_date = {}
        for attendance in attendances:
            if attendance.check_in:
                check_in_date = attendance.check_in.date()
                if self.date_from <= check_in_date <= self.date_to:
                    present_by_date.setdefault(check_in_date, set()).add(attendance.employee_id.id)
            if attendance.check_out:
                check_out_date = attendance.check_out.date()
                if self.date_from <= check_out_date <= self.date_to:
                    present_by_date.setdefault(check_out_date, set()).add(attendance.employee_id.id)

        leaves = self.env["hr.leave"].search(
            [
                ("state", "=", "validate"),
                ("date_from", "<=", period_end),
                ("date_to", ">=", period_start),
            ]
        )
        public_holidays = self.env["resource.calendar.leaves"].search(
            [
                ("resource_id", "=", False),
                ("date_from", "<=", period_end),
                ("date_to", ">=", period_start),
            ]
        )

        lines = []
        current_date = self.date_from
        while current_date <= self.date_to:
            present_ids = present_by_date.get(current_date, set())
            day_leaves = leaves.filtered(
                lambda leave: leave.date_from
                and leave.date_to
                and fields.Date.to_date(leave.date_from) <= current_date <= fields.Date.to_date(leave.date_to)
            )
            worked_time_off_ids = {
                leave.employee_id.id for leave in day_leaves if leave.employee_id and self._is_worked_time_leave(leave)
            }
            on_leave_ids = {
                leave.employee_id.id for leave in day_leaves if leave.employee_id and leave.employee_id.id not in worked_time_off_ids
            }
            for emp in all_employees:
                if emp.id in present_ids:
                    continue
                status = "absent"
                if emp.id in worked_time_off_ids:
                    status = "worked_time_off"
                elif emp.id in on_leave_ids:
                    status = "on_leave"
                elif self._is_public_holiday(public_holidays, emp, current_date):
                    status = "public_holiday"
                elif self._is_weekend_for_employee(emp, current_date):
                    status = "weekend"
                lines.append(
                    {
                        "date": current_date,
                        "date_from": self.date_from,
                        "date_to": self.date_to,
                        "employee_id": emp.id,
                        "status": status,
                    }
                )
            current_date += timedelta(days=1)

        if lines:
            report.create(lines)

        return {
            "type": "ir.actions.act_window",
            "name": _("Absent Employees – %s to %s") % (self.date_from, self.date_to),
            "res_model": "hr.attendance.absent.report",
            "view_mode": "list",
            "domain": [
                ("date_from", "=", self.date_from),
                ("date_to", "=", self.date_to),
            ],
            "context": {"create": False, "delete": False},
            "target": "current",
        }
