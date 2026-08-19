from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import email_normalize


class HrGeneralRequest(models.Model):
    _name = "hr.general.request"
    _description = "General Request"
    _order = "date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(compute="_compute_name", store=True)
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
    description = fields.Text(
        string="Description",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("confirm", "To Approve"),
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
    can_approve_refuse = fields.Boolean(compute="_compute_can_approve_refuse")
    portal_state_label = fields.Char(compute="_compute_portal_state_label")

    @api.depends("employee_id", "date")
    def _compute_name(self):
        for request in self:
            if request.employee_id and request.date:
                request.name = _("%(employee)s - %(date)s") % {
                    "employee": request.employee_id.name,
                    "date": request.date,
                }
            else:
                request.name = _("General Request")

    @api.depends("state")
    def _compute_portal_state_label(self):
        selection = dict(self._fields["state"].selection)
        for request in self:
            request.portal_state_label = selection.get(request.state, request.state)

    @api.depends("state")
    def _compute_can_approve_refuse(self):
        is_admin = self.env.user.has_group("hr_holidays.group_hr_holidays_manager")
        for request in self:
            request.can_approve_refuse = is_admin and request.state == "confirm"

    def _portal_state_badge_class(self):
        self.ensure_one()
        return {
            "confirm": "text-bg-warning",
            "approve": "text-bg-success",
            "refuse": "text-bg-danger",
        }.get(self.state, "text-bg-secondary")

    def _is_portal_only_user(self, user):
        if not user:
            return False
        return user.has_group("base.group_portal") and not user.has_group("base.group_user")

    def _get_manager_user(self):
        self.ensure_one()
        employee = self.employee_id
        if employee.leave_manager_id:
            return employee.leave_manager_id
        manager = employee.parent_id
        if manager and manager.user_id:
            return manager.user_id
        if manager:
            work_email = email_normalize(manager.work_email)
            if work_email:
                return self.env["res.users"].sudo().search(
                    ["|", ("login", "=", work_email), ("email_normalized", "=", work_email)],
                    limit=1,
                )
        return self.env["res.users"]

    def _get_to_clean_activities(self):
        return ["attendance_location_portal.mail_act_general_request_approval"]

    def _activity_update_impl(self):
        to_clean = self.env["hr.general.request"]
        to_do = self.env["hr.general.request"]
        activity_vals = []
        today = fields.Date.today()
        model_id = self.env["ir.model"]._get_id("hr.general.request")
        activity_type = self.env.ref(
            "attendance_location_portal.mail_act_general_request_approval",
            raise_if_not_found=False,
        )
        if not activity_type:
            activity_type = self.env.ref("mail.mail_activity_data_todo")

        for request in self:
            if request.state == "confirm":
                manager_user = request.sudo()._get_manager_user()
                if not manager_user:
                    continue
                date_deadline = request.date or today
                if date_deadline < today:
                    date_deadline = today
                existing = request.activity_ids.filtered(
                    lambda activity: activity.automated
                    and activity.activity_type_id == activity_type
                )
                if existing:
                    existing.write({"date_deadline": date_deadline})
                    continue
                activity_vals.append(
                    {
                        "activity_type_id": activity_type.id,
                        "automated": True,
                        "date_deadline": date_deadline,
                        "note": _(
                            "New General Request from %(employee)s",
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

    def action_approve(self):
        if not self.env.user.has_group("hr_holidays.group_hr_holidays_manager"):
            raise UserError(_("Only Time Off Administrators can approve general requests."))
        requests = self.filtered(lambda request: request.state == "confirm")
        if len(requests) != len(self):
            raise UserError(_("Only requests pending approval can be approved."))
        requests.write({"state": "approve"})
        for request in requests:
            partner = request.employee_id.user_id.partner_id
            if partner:
                request.message_post(
                    body=_("Your general request has been approved."),
                    partner_ids=partner.ids,
                )
        return True

    def action_refuse(self):
        if not self.env.user.has_group("hr_holidays.group_hr_holidays_manager"):
            raise UserError(_("Only Time Off Administrators can refuse general requests."))
        requests = self.filtered(lambda request: request.state == "confirm")
        if len(requests) != len(self):
            raise UserError(_("Only requests pending approval can be refused."))
        requests.write({"state": "refuse"})
        for request in requests:
            partner = request.employee_id.user_id.partner_id
            if partner:
                request.message_post(
                    body=_("Your general request has been refused."),
                    partner_ids=partner.ids,
                )
        return True

