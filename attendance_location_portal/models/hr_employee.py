from odoo import SUPERUSER_ID, _, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import email_normalize, format_date


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    attendance_location_ids = fields.Many2many(
        "attendance.location",
        "attendance_location_employee_rel",
        "employee_id",
        "location_id",
        string="Allowed Attendance Locations",
        help="If set, the employee can check in/out only from these locations. "
        "If empty, company-wide attendance location rules apply.",
    )

    def action_create_portal_user(self):
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
            partner = self.env["res.partner"].sudo().create(
                {
                    "name": self.name,
                    "email": login,
                    "company_id": self.company_id.id,
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

        if existing_user:
            user = existing_user
        else:
            user = users.with_context(no_reset_password=True)._create_user_from_template(
                {
                    "name": self.name,
                    "email": login,
                    "login": login,
                    "partner_id": partner.id,
                    "company_id": self.company_id.id,
                    "company_ids": [(6, 0, [self.company_id.id])],
                }
            )

        user.write(
            {
                "active": True,
                "group_ids": [(4, portal_group.id), (3, public_group.id)],
            }
        )
        self.user_id = user.id
        return {
            "type": "ir.actions.act_window",
            "name": _("Portal User"),
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

    def action_portal_attendance_change(self, latitude, longitude, note=None):
        self.ensure_one()
        if latitude is None or longitude is None:
            raise UserError(_("Your location could not be detected. Please enable GPS."))
        try:
            lat = float(latitude)
            lon = float(longitude)
        except (TypeError, ValueError):
            raise UserError(_("Invalid GPS coordinates received from your device."))
        allowed_location = self._validate_attendance_location(lat, lon)
        checking_in = self.attendance_state != "checked_in"
        if not checking_in:
            open_attendance = (
                self.env["hr.attendance"]
                .sudo()
                .search(
                    [("employee_id", "=", self.id), ("check_out", "=", False)],
                    limit=1,
                )
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

        attendance = self.sudo()._attendance_action_change(
            {
                "latitude": lat,
                "longitude": lon,
                "location": allowed_location.name,
                "mode": "automatic",
            }
        )
        if checking_in and attendance:
            attendance.write({"attendance_location_id": allowed_location.id})
        note_text = (note or "").strip()
        if note_text and not checking_in:
            attendance = (
                self.env["hr.attendance"]
                .sudo()
                .search(
                    [
                        ("employee_id", "=", self.id),
                        ("check_out", "!=", False),
                    ],
                    order="check_out desc",
                    limit=1,
                )
            )
            if attendance:
                attendance.write({"portal_note": note_text})

        return {
            "location_name": allowed_location.name,
            "action": "check_in" if checking_in else "check_out",
            "state": self.attendance_state,
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
        manager = self.parent_id
        if manager and manager != self:
            return manager
        return self.env["hr.employee"]

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

        manager = self._get_portal_appraisal_manager()
        if not manager:
            raise UserError(
                _(
                    "No manager is configured on your employee record. "
                    "Please contact your HR department."
                )
            )

        appraisal_vals = {
            "employee_id": self.id,
            "date_close": date_close,
            "manager_ids": [(6, 0, manager.ids)],
            "state": "1_new",
        }

        try:
            with self.env.cr.savepoint():
                appraisal = (
                    self.env["hr.appraisal"]
                    .with_user(SUPERUSER_ID)
                    .create(appraisal_vals)
                )
        except ValidationError as error:
            raise UserError(str(error)) from error

        return appraisal

    def action_portal_update_appraisal_feedback(self, appraisal, feedback):
        self.ensure_one()
        self._portal_ensure_current_user()
        appraisal = appraisal.sudo()
        if appraisal.employee_id != self:
            raise AccessError(_("You can only update your own appraisals."))
        if appraisal.state not in ("1_new", "2_pending"):
            raise UserError(_("You can only edit feedback for draft or ongoing appraisals."))

        try:
            with self.env.cr.savepoint():
                appraisal.sudo().write({"employee_feedback": feedback or False})
        except ValidationError as error:
            raise UserError(str(error)) from error

        return appraisal
