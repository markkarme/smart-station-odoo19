"""Let attendance_location_portal business methods run for website users.

The portal methods identify the actor through ``env.user`` / the HTTP session user.
The website API runs as superuser and performs its own permission checks first
(website.access.right + allowed companies + assigned approvers), then flags the
environment with these context keys so the portal checks accept the call.
"""
from odoo import models

API_EMPLOYEE_KEY = 'website_api_employee_id'
API_DECISION_KEY = 'website_api_decision'


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _portal_ensure_current_user(self):
        if self.env.context.get(API_EMPLOYEE_KEY) == self.id:
            return
        return super()._portal_ensure_current_user()


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def _check_double_validation_rules(self, employees, state):
        if self.env.context.get(API_DECISION_KEY):
            return
        return super()._check_double_validation_rules(employees, state)

    def _user_can_approve_current_step(self):
        if self.env.context.get(API_DECISION_KEY):
            return True
        return super()._user_can_approve_current_step()

    def _check_portal_admin_decision(self):
        if self.env.context.get(API_DECISION_KEY):
            return
        return super()._check_portal_admin_decision()


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    def _user_can_approve_current_step(self):
        if self.env.context.get(API_DECISION_KEY):
            return True
        return super()._user_can_approve_current_step()

    def _check_portal_admin_decision(self):
        if self.env.context.get(API_DECISION_KEY):
            return
        return super()._check_portal_admin_decision()


class HrGeneralRequest(models.Model):
    _inherit = 'hr.general.request'

    def _user_can_decide(self):
        if self.env.context.get(API_DECISION_KEY):
            return True
        return super()._user_can_decide()


class HrAttendanceAdjustmentRequest(models.Model):
    _inherit = 'hr.attendance.adjustment.request'

    def _user_can_decide(self):
        if self.env.context.get(API_DECISION_KEY):
            return True
        return super()._user_can_decide()
