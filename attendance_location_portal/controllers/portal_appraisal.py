import logging
from datetime import date, timedelta
from urllib.parse import urlencode

from odoo import _, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager

_logger = logging.getLogger(__name__)

APPRAISAL_STATE_BADGES = {
    "1_new": "text-bg-secondary",
    "2_pending": "text-bg-warning",
    "3_done": "text-bg-success",
}


def _get_appraisal_state_labels(env):
    return {
        "1_new": env._("Draft"),
        "2_pending": env._("Ongoing"),
        "3_done": env._("Done"),
    }


class PortalAppraisalController(http.Controller):
    def _get_user_employee(self):
        employee = request.env.user.employee_id
        if not employee:
            employee = request.env.user.employee_ids[:1]
        return employee

    def _get_employee_appraisal(self, employee, appraisal_id):
        appraisal = request.env["hr.appraisal"].sudo().browse(appraisal_id)
        if not appraisal.exists() or appraisal.employee_id != employee:
            raise AccessError(_("This appraisal does not exist or is not accessible."))
        return appraisal

    @http.route(
        ["/my/appraisals", "/my/appraisals/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_appraisals(self, page=1, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return request.render(
                "attendance_location_portal.portal_appraisal_failed_page",
                {
                    "page_name": "portal_appraisal_failed",
                    "error_message": _(
                        "Your account is not linked to an employee record. "
                        "Please contact your administrator."
                    ),
                },
            )

        appraisal_model = request.env["hr.appraisal"].sudo()
        domain = [("employee_id", "=", employee.id)]
        appraisal_count = appraisal_model.search_count(domain)
        pager = portal_pager(
            url="/my/appraisals",
            total=appraisal_count,
            page=page,
            step=20,
        )
        appraisals = appraisal_model.search(
            domain,
            order="date_close desc, id desc",
            limit=20,
            offset=pager["offset"],
        )
        values = {
            "page_name": "portal_appraisals",
            "employee": employee,
            "appraisals": appraisals,
            "pager": pager,
            "appraisal_state_labels": _get_appraisal_state_labels(request.env),
            "appraisal_state_badges": APPRAISAL_STATE_BADGES,
        }
        return request.render("attendance_location_portal.portal_my_appraisals", values)

    @http.route("/my/appraisals/new", type="http", auth="user", website=True)
    def portal_appraisal_new(self, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return request.render(
                "attendance_location_portal.portal_appraisal_failed_page",
                {
                    "page_name": "portal_appraisal_failed",
                    "error_message": _(
                        "Your account is not linked to an employee record. "
                        "Please contact your administrator."
                    ),
                },
            )

        manager = employee.sudo()._get_portal_appraisal_manager()
        default_date_close = (date.today() + timedelta(days=30)).isoformat()
        values = {
            "page_name": "portal_appraisal_new",
            "employee": employee,
            "manager": manager,
            "default_date_close": default_date_close,
            "error_message": kwargs.get("error"),
            "form_values": kwargs,
        }
        return request.render("attendance_location_portal.portal_appraisal_form", values)

    @http.route(
        "/my/appraisals/submit",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_appraisal_submit(self, **post):
        employee = self._get_user_employee()
        if not employee:
            params = urlencode({"error": _("No employee is linked to your user.")})
            return request.redirect("/my/appraisals/new?%s" % params)

        try:
            appraisal = employee.action_portal_create_appraisal(
                {"date_close": post.get("date_close")}
            )
            return request.redirect("/my/appraisals/%s" % appraisal.id)
        except (UserError, AccessError) as error:
            params = urlencode(
                {
                    "error": str(error),
                    "date_close": post.get("date_close") or "",
                }
            )
            return request.redirect("/my/appraisals/new?%s" % params)
        except Exception as error:
            _logger.exception("Portal appraisal submit failed: %s", error)
            params = urlencode(
                {
                    "error": _("Unexpected error while submitting your appraisal. Please try again."),
                    "date_close": post.get("date_close") or "",
                }
            )
            return request.redirect("/my/appraisals/new?%s" % params)

    @http.route(
        "/my/appraisals/<int:appraisal_id>",
        type="http",
        auth="user",
        website=True,
    )
    def portal_appraisal_detail(self, appraisal_id, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return request.render(
                "attendance_location_portal.portal_appraisal_failed_page",
                {
                    "page_name": "portal_appraisal_failed",
                    "error_message": _(
                        "Your account is not linked to an employee record. "
                        "Please contact your administrator."
                    ),
                },
            )

        try:
            appraisal = self._get_employee_appraisal(employee, appraisal_id)
        except AccessError:
            return request.render(
                "attendance_location_portal.portal_appraisal_failed_page",
                {
                    "page_name": "portal_appraisal_failed",
                    "error_message": _("This appraisal is not accessible."),
                },
            )

        values = {
            "page_name": "portal_appraisal_detail",
            "employee": employee,
            "appraisal": appraisal,
            "appraisal_state_labels": _get_appraisal_state_labels(request.env),
            "appraisal_state_badges": APPRAISAL_STATE_BADGES,
            "success_message": kwargs.get("success"),
            "error_message": kwargs.get("error"),
            "can_edit_feedback": appraisal.state in ("1_new", "2_pending"),
        }
        return request.render("attendance_location_portal.portal_appraisal_detail", values)

    @http.route(
        "/my/appraisals/<int:appraisal_id>/feedback",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_appraisal_feedback_submit(self, appraisal_id, **post):
        employee = self._get_user_employee()
        if not employee:
            params = urlencode({"error": _("No employee is linked to your user.")})
            return request.redirect("/my/appraisals/%s?%s" % (appraisal_id, params))

        try:
            appraisal = self._get_employee_appraisal(employee, appraisal_id)
            employee.action_portal_update_appraisal_feedback(
                appraisal,
                post.get("employee_feedback"),
            )
            params = urlencode({"success": _("Your feedback has been saved.")})
            return request.redirect("/my/appraisals/%s?%s" % (appraisal_id, params))
        except (UserError, AccessError) as error:
            params = urlencode({"error": str(error)})
            return request.redirect("/my/appraisals/%s?%s" % (appraisal_id, params))
        except Exception as error:
            _logger.exception("Portal appraisal feedback submit failed: %s", error)
            params = urlencode(
                {"error": _("Unexpected error while saving your feedback. Please try again.")}
            )
            return request.redirect("/my/appraisals/%s?%s" % (appraisal_id, params))
