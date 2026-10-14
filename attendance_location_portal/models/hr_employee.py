import pytz
from pytz import utc

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import email_normalize, format_date


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    hr_responsible_ids = fields.Many2many(
        "res.users",
        "hr_employee_hr_responsible_rel",
        "employee_id",
        "user_id",
        string="HR Responsibles",
        domain="[('share', '=', False)]",
        groups="hr.group_hr_user",
    )
    leave_manager_ids = fields.Many2many(
        "res.users",
        "hr_employee_leave_manager_rel",
        "employee_id",
        "user_id",
        string="Time Off Approvers",
        domain="['|', ('share', '=', False), ('portal_hr_admin', '=', True)]",
        groups="hr.group_hr_user",
    )
    attendance_manager_ids = fields.Many2many(
        "res.users",
        "hr_employee_attendance_manager_rel",
        "employee_id",
        "user_id",
        string="Attendance Approvers",
        domain="[('share', '=', False)]",
        groups="hr.group_hr_user",
    )
    expense_manager_ids = fields.Many2many(
        "res.users",
        "hr_employee_expense_manager_rel",
        "employee_id",
        "user_id",
        string="Expense Approvers",
        domain="[('share', '=', False)]",
        groups="hr.group_hr_user",
    )
    attendance_location_ids = fields.Many2many(
        "attendance.location",
        "attendance_location_employee_rel",
        "employee_id",
        "location_id",
        string="Allowed Attendance Locations",
        help="If set, the employee can check in/out only from these locations. "
        "If empty, company-wide attendance location rules apply.",
    )
    is_portal_hr_admin = fields.Boolean(
        string="Portal Admin",
        compute="_compute_is_portal_hr_admin",
        inverse="_inverse_is_portal_hr_admin",
        help="Portal admin users can view all attendance, general requests, "
        "time off, allocations, and attendance adjustments in the portal.",
    )

    def _sync_approver_fields(self, vals):
        if self.env.context.get("skip_approver_sync"):
            return
        mapping = (
            ("hr_responsible_id", "hr_responsible_ids"),
            ("leave_manager_id", "leave_manager_ids"),
            ("attendance_manager_id", "attendance_manager_ids"),
            ("expense_manager_id", "expense_manager_ids"),
        )
        for employee in self:
            update_vals = {}
            for single_field, multi_field in mapping:
                if single_field not in employee._fields or multi_field not in employee._fields:
                    continue
                single_updated = single_field in vals
                multi_updated = multi_field in vals
                if multi_updated and not single_updated:
                    update_vals[single_field] = employee[multi_field][:1].id or False
                elif single_updated and not multi_updated:
                    update_vals[multi_field] = [(6, 0, employee[single_field].ids)]
            if update_vals:
                super(
                    HrEmployee,
                    employee.with_context(skip_approver_sync=True),
                ).write(update_vals)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for employee, vals in zip(records, vals_list):
            employee._sync_approver_fields(vals)
        return records

    def write(self, vals):
        result = super().write(vals)
        self._sync_approver_fields(vals)
        return result

    def _compute_hours_last_month(self):
        """Tolerate checkout-first portal records with empty check_in."""
        now_utc = pytz.utc.localize(fields.Datetime.now())
        for timezone, employees in self.grouped("tz").items():
            now_tz = now_utc.astimezone(pytz.timezone(timezone or "UTC"))
            start_tz = now_tz.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            start_naive = start_tz.astimezone(pytz.utc).replace(tzinfo=None)
            end_naive = now_tz.astimezone(pytz.utc).replace(tzinfo=None)

            for employee in employees:
                current_month_attendances = employee.attendance_ids.filtered(
                    lambda att: att.check_in
                    and att.check_in >= start_naive
                    and att.check_out
                    and att.check_out <= end_naive
                )
                hours = sum(att.worked_hours or 0 for att in current_month_attendances)
                overtime_hours = sum(
                    att.validated_overtime_hours or 0 for att in current_month_attendances
                )
                employee.hours_last_month = round(hours, 2)
                employee.hours_last_month_display = "%g" % employee.hours_last_month
                employee.hours_last_month_overtime = round(overtime_hours, 2)

    def _get_portal_hr_admin_group(self):
        return self.env.ref(
            "attendance_location_portal.group_portal_hr_admin",
            raise_if_not_found=False,
        )

    def _compute_is_portal_hr_admin(self):
        admin_group = self._get_portal_hr_admin_group()
        for employee in self:
            employee.is_portal_hr_admin = bool(
                admin_group
                and employee.user_id
                and admin_group in employee.user_id.group_ids
            )

    def _inverse_is_portal_hr_admin(self):
        admin_group = self._get_portal_hr_admin_group()
        if not admin_group:
            return
        for employee in self:
            user = employee.user_id
            if not user:
                continue
            if employee.is_portal_hr_admin:
                user.sudo().write({"group_ids": [(4, admin_group.id)]})
            else:
                user.sudo().write({"group_ids": [(3, admin_group.id)]})

    def _attendance_action_change(self, geo_information=None):
        """On check-in, save attendance under the location's company."""
        location = self.env.context.get("portal_attendance_location")
        if not location or self.attendance_state == "checked_in":
            return super()._attendance_action_change(geo_information)

        self.ensure_one()
        vals = {
            "employee_id": self.id,
            "check_in": fields.Datetime.now(),
            "attendance_location_id": location.id,
            "company_id": location.company_id.id,
        }
        if geo_information:
            vals.update(
                {("in_%s" % key): geo_information[key] for key in geo_information}
            )
        return self.env["hr.attendance"].create(vals)

    def action_create_portal_user(self):
        return self._create_portal_user(as_admin=False)

    def action_create_portal_admin_user(self):
        return self._create_portal_user(as_admin=True)

    def _create_portal_user(self, as_admin=False):
        self.ensure_one()
        if self.user_id:
            raise UserError(_("This employee already has a linked user."))

        login = email_normalize(self.work_email)
        if not login:
            raise UserError(
                _(
                    "Please set a valid Work Email on the employee first. "
                    "It will be used as the portal user login."
                )
            )

        partner = self.work_contact_id
        if not partner:
            company_ids = self.company_ids or self.company_id
            partner = self.env["res.partner"].sudo().create(
                {
                    "name": self.name,
                    "email": login,
                    # Shared contact avoids portal multi-company 403s
                    "company_id": False if len(company_ids) > 1 else self.company_id.id,
                }
            )
            self.work_contact_id = partner.id
        elif email_normalize(partner.email) != login:
            partner.sudo().write({"email": login})

        users = self.env["res.users"].sudo()
        existing_user = users.with_context(active_test=False).search(
            ["|", ("login", "=", login), ("email_normalized", "=", login)],
            limit=1,
        )
        if existing_user and existing_user._is_internal():
            raise UserError(
                _(
                    "A user with login %(login)s already exists as an internal user. "
                    "Use another email for this employee."
                )
                % {"login": login}
            )

        portal_group = self.env.ref("base.group_portal")
        public_group = self.env.ref("base.group_public")
        admin_group = self._get_portal_hr_admin_group()
        allowed_companies = self.company_ids or self.company_id
        main_company = self.company_id if self.company_id in allowed_companies else allowed_companies[:1]

        if existing_user:
            user = existing_user
            user.write(
                {
                    "company_id": main_company.id,
                    "company_ids": [(6, 0, allowed_companies.ids)],
                }
            )
        else:
            user = users.with_context(no_reset_password=True)._create_user_from_template(
                {
                    "name": self.name,
                    "email": login,
                    "login": login,
                    "partner_id": partner.id,
                    "company_id": main_company.id,
                    "company_ids": [(6, 0, allowed_companies.ids)],
                }
            )

        group_commands = [(4, portal_group.id), (3, public_group.id)]
        if as_admin and admin_group:
            group_commands.append((4, admin_group.id))
        elif admin_group:
            group_commands.append((3, admin_group.id))

        user.write(
            {
                "active": True,
                "group_ids": group_commands,
            }
        )
        self.user_id = user.id
        return {
            "type": "ir.actions.act_window",
            "name": _("Portal Admin User") if as_admin else _("Portal User"),
            "res_model": "res.users",
            "view_mode": "form",
            "res_id": user.id,
            "target": "current",
        }

    def _validate_attendance_location(self, latitude, longitude):
        self.ensure_one()
        location_model = self.env["attendance.location"].sudo()
        allowed, nearest, nearest_distance = location_model.find_allowed_location(
            self, latitude, longitude
        )
        if allowed:
            return allowed
        if not nearest:
            raise UserError(
                _(
                    "No attendance location is configured for your employee. "
                    "Please contact your HR manager."
                )
            )
        raise UserError(
            _(
                "You are outside the allowed attendance range.\n"
                "Nearest location: %(name)s\n"
                "Your distance: %(distance).2f m\n"
                "Allowed range: %(allowed).2f m"
            )
            % {
                "name": nearest.name,
                "distance": nearest_distance or 0.0,
                "allowed": nearest.allowed_range_m,
            }
        )

    def _portal_attendance_local_date(self, dt=None):
        """Same calendar day as hr.attendance.date (employee/_get_tz), not user tz."""
        self.ensure_one()
        dt = fields.Datetime.to_datetime(dt or fields.Datetime.now())
        tz = pytz.timezone(self._get_tz() or "UTC")
        return utc.localize(dt).astimezone(tz).date()

    def _get_portal_day_attendance(self, action):
        """Find the attendance row that same-day check-in/out should update.

        Prefer an open check-in for checkout. Prefer rows that already have
        check_in when matching on date (NULL check_in sorts first in DESC).
        """
        self.ensure_one()
        attendance_model = self.env["hr.attendance"].sudo()
        today = self._portal_attendance_local_date()

        if action == "check_out":
            open_attendance = attendance_model.search(
                [
                    ("employee_id", "=", self.id),
                    ("check_in", "!=", False),
                    ("check_out", "=", False),
                ],
                order="check_in desc",
                limit=1,
            )
            if open_attendance:
                return open_attendance

        with_check_in = attendance_model.search(
            [
                ("employee_id", "=", self.id),
                ("date", "=", today),
                ("check_in", "!=", False),
            ],
            order="check_in desc",
            limit=1,
        )
        if with_check_in:
            return with_check_in

        return attendance_model.search(
            [
                ("employee_id", "=", self.id),
                ("date", "=", today),
            ],
            order="id desc",
            limit=1,
        )

    def action_portal_attendance_change(
        self,
        latitude,
        longitude,
        attendance_action=None,
        note=None,
    ):
        self.ensure_one()
        if latitude is None or longitude is None:
            raise UserError(_("Your location could not be detected. Please enable GPS."))
        try:
            lat = float(latitude)
            lon = float(longitude)
        except (TypeError, ValueError):
            raise UserError(_("Invalid GPS coordinates received from your device."))
        allowed_location = self._validate_attendance_location(lat, lon)
        action = (attendance_action or "").strip()
        if action not in ("check_in", "check_out"):
            raise UserError(_("Please choose whether this is check in or check out."))

        today_attendance = self._get_portal_day_attendance(action)

        if action == "check_out":
            open_attendance = today_attendance.filtered(
                lambda att: att.check_in and not att.check_out
            )
            if (
                open_attendance
                and open_attendance.attendance_location_id
                and open_attendance.attendance_location_id != allowed_location
            ):
                raise UserError(
                    _(
                        "You must check out from the same location where you checked in.\n"
                        "Check-in location: %(check_in)s\n"
                        "Your current location: %(current)s"
                    )
                    % {
                        "check_in": open_attendance.attendance_location_id.name,
                        "current": allowed_location.name,
                    }
                )

        if not self.company_id.attendance_device_tracking:
            self.company_id.sudo().write({"attendance_device_tracking": True})

        attendance_model = self.env["hr.attendance"].sudo().with_context(
            skip_attendance_validity_notification=True
        )
        portal_attendance = lambda recordset: recordset.with_context(
            skip_attendance_validity_notification=True
        )
        note_text = (note or "").strip()
        now = fields.Datetime.now()

        if action == "check_in":
            in_vals = {
                "employee_id": self.id,
                "check_in": now,
                "in_mode": "automatic",
                "in_latitude": lat,
                "in_longitude": lon,
                "in_location": allowed_location.name,
                "attendance_location_id": allowed_location.id,
                "company_id": allowed_location.company_id.id,
                "portal_action_type": "check_in",
                "portal_checkout_without_checkin": False,
            }
            if today_attendance:
                portal_attendance(today_attendance).write(in_vals)
                attendance = today_attendance
            else:
                attendance = attendance_model.create(in_vals)
        else:
            out_vals = {
                "employee_id": self.id,
                "check_out": now,
                "out_mode": "automatic",
                "out_latitude": lat,
                "out_longitude": lon,
                "out_location": allowed_location.name,
                "attendance_location_id": allowed_location.id,
                "company_id": allowed_location.company_id.id,
                "portal_action_type": "check_out",
            }
            if note_text:
                out_vals["portal_note"] = note_text
            if today_attendance:
                # Only keep checkout-without-checkin when the day row has no check-in.
                if not today_attendance.check_in:
                    out_vals["portal_checkout_without_checkin"] = True
                    out_vals["check_in"] = False
                else:
                    out_vals["portal_checkout_without_checkin"] = False
                portal_attendance(today_attendance).write(out_vals)
                attendance = today_attendance
            else:
                out_vals["portal_checkout_without_checkin"] = True
                out_vals["check_in"] = False
                attendance = attendance_model.create(out_vals)

        warnings = attendance.with_context(
            lang=self.env.lang
        )._collect_attendance_validity_warnings()
        # When portal shows "checked in without prior check-out", notify HR Responsible.
        if action == "check_in" and not attendance.check_out:
            attendance.with_context(
                lang=self.env.lang
            )._schedule_missing_checkout_hr_activity()
        if warnings:
            attendance.message_post(
                body="\n".join(warnings),
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )

        return {
            "location_name": allowed_location.name,
            "action": action,
            "warnings": warnings,
        }

    def _portal_ensure_current_user(self):
        self.ensure_one()
        if self.user_id != self.env.user:
            raise AccessError(_("You can only manage your own employee records."))

    def _get_portal_company_type_domain(self):
        self.ensure_one()
        company = self.company_id
        country_ids = company.country_id.ids if company.country_id else []
        if False not in country_ids:
            country_ids.append(False)
        return [
            ("active", "=", True),
            "|",
            ("company_id", "in", company.ids),
            "&",
            ("company_id", "=", False),
            ("country_id", "in", country_ids),
        ]

    def _get_portal_leave_context(self, date_from=None, date_to=None):
        self.ensure_one()
        today = fields.Date.context_today(self)
        date_from = date_from or today
        date_to = date_to or date_from
        return {
            "employee_id": self.id,
            "default_employee_id": self.id,
            "default_date_from": date_from,
            "default_date_to": date_to,
            "allowed_company_ids": self.company_id.ids,
        }

    def _get_portal_leave_type_domain(self):
        """Same domain as hr.leave form holiday_status_id field."""
        return [
            "|",
            ("requires_allocation", "=", False),
            "&",
            ("has_valid_allocation", "=", True),
            "|",
            ("allows_negative", "=", True),
            "&",
            ("virtual_remaining_leaves", ">", 0),
            ("allows_negative", "=", False),
        ]

    def _get_portal_leave_types(self, date_from=None, date_to=None):
        self.ensure_one()
        self._portal_ensure_current_user()
        domain = self._get_portal_leave_type_domain() + self._get_portal_company_type_domain()
        return (
            self.env["hr.leave.type"]
            .sudo()
            .with_context(**self._get_portal_leave_context(date_from=date_from, date_to=date_to))
            .search(domain, order="sequence, name")
        )

    @staticmethod
    def _portal_parse_float_time(value):
        if not value:
            return False
        if isinstance(value, (int, float)):
            return float(value)
        value = value.strip()
        if ":" in value:
            hours, minutes = value.split(":", 1)
            return int(hours) + int(minutes) / 60.0
        return float(value)

    def _portal_validate_leave_request(self, leave_type, leave_vals):
        self.ensure_one()
        if leave_type.allow_request_on_top:
            return

        leave_model = self.env["hr.leave"].sudo()
        preview = leave_model.new(
            dict(
                leave_vals,
                employee_id=self.id,
                holiday_status_id=leave_type.id,
            )
        )
        preview._compute_date_from_to()
        if not preview.date_from or not preview.date_to:
            return

        conflicting_leaves = leave_model.search(
            [
                ("employee_id", "=", self.id),
                ("state", "not in", ["cancel", "refuse"]),
                ("date_from", "<", preview.date_to),
                ("date_to", ">", preview.date_from),
                ("holiday_status_id.allow_request_on_top", "=", False),
            ]
        )
        if not conflicting_leaves:
            return

        state_labels = dict(leave_model._fields["state"].selection)
        lines = []
        for conflicting in conflicting_leaves:
            lines.append(
                _("\tfrom %(date_from)s to %(date_to)s - %(state)s")
                % {
                    "date_from": format_date(self.env, conflicting.date_from.date()),
                    "date_to": format_date(self.env, conflicting.date_to.date()),
                    "state": state_labels.get(conflicting.state, conflicting.state),
                }
            )
        raise UserError(
            _("You've already booked time off which overlaps with this period:\n%s")
            % "\n".join(lines)
        )

    def action_portal_create_leave(self, values):
        self.ensure_one()
        self._portal_ensure_current_user()

        leave_type_id = values.get("holiday_status_id")
        if not leave_type_id:
            raise UserError(_("Please select a time off type."))

        leave_type = (
            self.env["hr.leave.type"]
            .sudo()
            .with_context(
                **self._get_portal_leave_context(
                    date_from=values.get("request_date_from"),
                    date_to=values.get("request_date_to"),
                )
            )
            .browse(int(leave_type_id))
        )
        if not leave_type or not leave_type.active:
            raise UserError(_("The selected time off type is not available."))

        available_types = self._get_portal_leave_types(
            date_from=values.get("request_date_from"),
            date_to=values.get("request_date_to"),
        )
        if leave_type not in available_types:
            raise UserError(_("The selected time off type is not available for you."))

        request_date_from = values.get("request_date_from")
        request_date_to = values.get("request_date_to") or request_date_from
        if not request_date_from:
            raise UserError(_("Please select a start date."))

        try:
            request_date_from = fields.Date.to_date(request_date_from)
            request_date_to = fields.Date.to_date(request_date_to)
        except (TypeError, ValueError):
            raise UserError(_("Invalid date format.")) from None

        if request_date_to < request_date_from:
            raise UserError(_("The end date must be on or after the start date."))

        leave_vals = {
            "employee_id": self.id,
            "holiday_status_id": leave_type.id,
            "request_date_from": request_date_from,
            "request_date_to": request_date_to,
            "private_name": (values.get("name") or "").strip() or False,
            "notes": (values.get("notes") or "").strip() or False,
        }

        if leave_type.request_unit == "half_day":
            leave_vals.update(
                {
                    "request_date_from_period": values.get("request_date_from_period") or "am",
                    "request_date_to_period": values.get("request_date_to_period") or "pm",
                }
            )
            if request_date_from == request_date_to:
                leave_vals["request_date_to_period"] = leave_vals["request_date_from_period"]
        elif leave_type.request_unit == "hour":
            hour_from = self._portal_parse_float_time(values.get("request_hour_from"))
            hour_to = self._portal_parse_float_time(values.get("request_hour_to"))
            if hour_from is False or hour_to is False:
                raise UserError(_("Please provide both start and end hours."))
            leave_vals.update(
                {
                    "request_date_to": request_date_from,
                    "request_hour_from": hour_from,
                    "request_hour_to": hour_to,
                }
            )

        if leave_type.support_document and not values.get("attachments"):
            raise UserError(
                _("A supporting document is required for %(leave_type)s.")
                % {"leave_type": leave_type.name}
            )

        self._portal_validate_leave_request(leave_type, leave_vals)

        try:
            with self.env.cr.savepoint():
                leave = (
                    self.env["hr.leave"]
                    .with_user(SUPERUSER_ID)
                    .create(leave_vals)
                )
                attachments = values.get("attachments") or []
                attachment_model = self.env["ir.attachment"].sudo()
                for attachment in attachments:
                    if not attachment.get("datas"):
                        continue
                    attachment_model.create(
                        {
                            "name": attachment.get("name") or "attachment",
                            "datas": attachment["datas"],
                            "res_model": "hr.leave",
                            "res_id": leave.id,
                            "type": "binary",
                        }
                    )
        except ValidationError as error:
            raise UserError(str(error)) from error

        return leave

    def action_portal_cancel_leave(self, leave, reason=None):
        self.ensure_one()
        self._portal_ensure_current_user()
        leave = leave.sudo()
        if leave.employee_id != self:
            raise AccessError(_("You can only cancel your own time off requests."))
        if not leave.can_cancel:
            raise UserError(_("This time off request cannot be cancelled."))
        try:
            leave._action_user_cancel((reason or "").strip() or False)
        except ValidationError as error:
            raise UserError(str(error)) from error
        return leave

    def _get_portal_allocation_context(self, date_from=None):
        self.ensure_one()
        company = self.company_id
        return {
            "employee_id": self.id,
            "default_employee_id": self.id,
            "default_date_from": date_from or fields.Date.context_today(self),
            "request_type": "allocation",
            "allowed_company_ids": company.ids,
        }

    def _get_portal_allocation_type_domain(self):
        self.ensure_one()
        return [
            ("requires_allocation", "=", True),
        ] + self._get_portal_company_type_domain()

    def _get_portal_allocation_types(self, date_from=None):
        self.ensure_one()
        self._portal_ensure_current_user()
        return (
            self.env["hr.leave.type"]
            .sudo()
            .with_context(**self._get_portal_allocation_context(date_from=date_from))
            .search(self._get_portal_allocation_type_domain(), order="sequence, name")
        )

    def action_portal_create_allocation(self, values):
        self.ensure_one()
        self._portal_ensure_current_user()

        leave_type_id = values.get("holiday_status_id")
        if not leave_type_id:
            raise UserError(_("Please select a time off type."))

        leave_type = (
            self.env["hr.leave.type"]
            .sudo()
            .with_context(**self._get_portal_allocation_context(date_from=values.get("date_from")))
            .browse(int(leave_type_id))
        )
        if not leave_type or not leave_type.active:
            raise UserError(_("The selected time off type is not available."))

        available_types = self._get_portal_allocation_types(date_from=values.get("date_from"))
        if leave_type not in available_types:
            raise UserError(_("The selected time off type is not available for you."))

        date_from = values.get("date_from")
        if not date_from:
            raise UserError(_("Please select a validity start date."))

        try:
            date_from = fields.Date.to_date(date_from)
            date_to = values.get("date_to")
            date_to = fields.Date.to_date(date_to) if date_to else False
        except (TypeError, ValueError):
            raise UserError(_("Invalid date format.")) from None

        if date_to and date_to < date_from:
            raise UserError(_("The validity end date must be on or after the start date."))

        try:
            amount = float(values.get("allocation_amount") or 0)
        except (TypeError, ValueError):
            raise UserError(_("Please enter a valid allocation amount.")) from None

        if amount <= 0:
            raise UserError(_("The allocation must be greater than zero."))

        allocation_vals = {
            "employee_id": self.id,
            "holiday_status_id": leave_type.id,
            "date_from": date_from,
            "date_to": date_to,
            "notes": (values.get("notes") or "").strip() or False,
            "allocation_type": "regular",
        }
        if leave_type.request_unit == "hour":
            allocation_vals["number_of_hours_display"] = amount
        else:
            allocation_vals["number_of_days"] = amount

        try:
            with self.env.cr.savepoint():
                allocation = (
                    self.env["hr.leave.allocation"]
                    .with_user(SUPERUSER_ID)
                    .create(allocation_vals)
                )
        except ValidationError as error:
            raise UserError(str(error)) from error

        return allocation

    def action_portal_cancel_allocation(self, allocation):
        self.ensure_one()
        self._portal_ensure_current_user()
        allocation = allocation.sudo()
        if allocation.employee_id != self:
            raise AccessError(_("You can only cancel your own allocation requests."))
        if allocation.state not in ("confirm", "refuse"):
            raise UserError(_("This allocation request cannot be cancelled."))
        allocation.unlink()
        return True

    def action_portal_create_general_request(self, values):
        self.ensure_one()
        self._portal_ensure_current_user()

        description = (values.get("description") or "").strip()
        if not description:
            raise UserError(_("Please provide a description for your request."))

        request_vals = {
            "employee_id": self.id,
            "date": fields.Date.context_today(self),
            "description": description,
            "state": "confirm",
        }

        try:
            with self.env.cr.savepoint():
                general_request = (
                    self.env["hr.general.request"]
                    .with_user(SUPERUSER_ID)
                    .create(request_vals)
                )
        except ValidationError as error:
            raise UserError(str(error)) from error

        return general_request

    def action_portal_create_attendance_adjustment(self, values):
        self.ensure_one()
        self._portal_ensure_current_user()

        request_type = values.get("request_type")
        if request_type not in ("early_departure", "late_arrival"):
            raise UserError(_("Please select a valid request type."))

        request_date = values.get("date")
        if not request_date:
            raise UserError(_("Please select a date."))

        try:
            request_date = fields.Date.to_date(request_date)
        except (TypeError, ValueError):
            raise UserError(_("Invalid date format.")) from None

        try:
            time_minutes = int(values.get("time_minutes") or 0)
        except (TypeError, ValueError):
            raise UserError(_("Please enter a valid time in minutes.")) from None

        if time_minutes <= 0:
            raise UserError(_("Time in minutes must be greater than zero."))

        description = (values.get("description") or "").strip()
        if not description:
            raise UserError(_("Please provide a description for your request."))

        request_vals = {
            "employee_id": self.id,
            "request_type": request_type,
            "date": request_date,
            "time_minutes": time_minutes,
            "description": description,
            "state": "confirm",
        }

        try:
            with self.env.cr.savepoint():
                adjustment_request = (
                    self.env["hr.attendance.adjustment.request"]
                    .with_user(SUPERUSER_ID)
                    .create(request_vals)
                )
        except ValidationError as error:
            raise UserError(str(error)) from error

        return adjustment_request

    def _get_portal_appraisal_manager(self):
        self.ensure_one()
        manager = self.sudo().parent_id
        if manager and manager != self:
            return manager
        return self.env["hr.employee"]

    def _get_portal_appraisal_employees(self):
        self.ensure_one()
        company = self.sudo().company_id
        return (
            self.env["hr.employee"]
            .sudo()
            .search(
                [
                    ("active", "=", True),
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "=", company.id),
                ],
                order="name, id",
            )
        )

    def _portal_resolve_appraisal_people(self, values):
        self.ensure_one()
        employees = self._get_portal_appraisal_employees()
        subject = values.get("employee_id") or self
        if isinstance(subject, int):
            subject = employees.filtered(lambda emp: emp.id == subject)
        elif subject and subject.exists():
            subject = employees.filtered(lambda emp: emp.id == subject.id)
        if not subject:
            raise UserError(_("Please select an employee to review."))

        manager_ids = values.get("manager_ids") or []
        if hasattr(manager_ids, "ids"):
            manager_ids = manager_ids.ids
        managers = employees.filtered(
            lambda emp: emp.id in manager_ids and emp.id != subject.id
        )
        if not managers:
            managers = subject._get_portal_appraisal_manager()
        if self != subject and self in employees and self not in managers:
            managers |= self
        managers = managers.filtered(lambda emp: emp.id != subject.id)
        if not managers:
            raise UserError(_("Please select at least one appraiser."))
        return subject, managers

    def action_portal_create_appraisal(self, values):
        self.ensure_one()
        self._portal_ensure_current_user()

        date_close = values.get("date_close")
        if not date_close:
            raise UserError(_("Please select an appraisal date."))

        try:
            date_close = fields.Date.to_date(date_close)
        except (TypeError, ValueError):
            raise UserError(_("Invalid date format.")) from None

        subject, managers = self._portal_resolve_appraisal_people(values)

        template = values.get("appraisal_template_id")
        if template and not template.exists():
            template = False

        appraisal_vals = {
            "employee_id": subject.id,
            "date_close": date_close,
            "manager_ids": [(6, 0, managers.ids)],
            "state": "1_new",
        }
        if template:
            appraisal_vals["appraisal_template_id"] = template.id

        try:
            with self.env.cr.savepoint():
                appraisal = (
                    self.env["hr.appraisal"]
                    .with_user(SUPERUSER_ID)
                    .create(appraisal_vals)
                )
                write_vals = {}
                if values.get("employee_feedback"):
                    write_vals["employee_feedback"] = values["employee_feedback"]
                if values.get("manager_feedback"):
                    write_vals["manager_feedback"] = values["manager_feedback"]
                if write_vals:
                    appraisal.with_user(SUPERUSER_ID).write(write_vals)
        except ValidationError as error:
            raise UserError(str(error)) from error

        return appraisal

    def action_portal_update_appraisal_feedback(self, appraisal, feedback):
        self.ensure_one()
        return appraisal.action_portal_save(self, {"employee_feedback": feedback})
