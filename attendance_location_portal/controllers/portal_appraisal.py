import json
import logging
from datetime import date, timedelta
from urllib.parse import urlencode

from markupsafe import Markup
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


def _as_markup(html):
    return Markup(html or "")


class PortalAppraisalController(http.Controller):
    def _get_user_employee(self):
        employee = request.env.user.employee_id
        if not employee:
            employee = request.env.user.employee_ids[:1]
        return employee

    def _appraisal_failed(self, message):
        return request.render(
            "attendance_location_portal.portal_appraisal_failed_page",
            {
                "page_name": "portal_appraisal_failed",
                "error_message": message,
            },
        )

    def _no_employee_page(self):
        return self._appraisal_failed(
            _(
                "Your account is not linked to an employee record. "
                "Please contact your administrator."
            )
        )

    def _get_accessible_appraisal(self, employee, appraisal_id):
        appraisal = request.env["hr.appraisal"].sudo().browse(appraisal_id)
        if not appraisal.exists():
            raise AccessError(_("This appraisal does not exist or is not accessible."))
        appraisal._portal_ensure_access(employee)
        return appraisal

    def _get_portal_templates(self, employee):
        employee = employee.sudo()
        templates = (
            request.env["hr.appraisal.template"]
            .sudo()
            .search(
                [
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "=", employee.company_id.id),
                ],
                order="sequence, description, id",
            )
        )
        department = employee.department_id
        if department:
            matching = templates.filtered(
                lambda template: not template.department_ids or department in template.department_ids
            )
            if matching:
                return matching
        return templates

    def _get_default_template(self, employee, templates=None):
        employee = employee.sudo()
        if templates is None:
            templates = self._get_portal_templates(employee)
        department_template = employee.department_id.appraisal_template_ids[:1]
        if department_template:
            return department_template
        generic = templates.filtered(lambda template: not template.department_ids)
        return generic[:1] or templates[:1]

    def _employee_avatar_src(self, employee):
        if not employee:
            return "/web/static/img/placeholder.png"
        avatar = employee.sudo().avatar_128
        if not avatar:
            return "/web/static/img/placeholder.png"
        if isinstance(avatar, bytes):
            avatar = avatar.decode()
        return "data:image/png;base64,%s" % avatar

    def _coerce_ids(self, value):
        if value is None:
            return []
        values = value if isinstance(value, list) else [value]
        return [int(item) for item in values if item and str(item).isdigit()]

    def _parse_post_ids(self, post, key):
        raw = request.httprequest.form.getlist(key)
        if not raw:
            value = post.get(key)
            if isinstance(value, list):
                raw = value
            elif value:
                raw = [value]
        return [int(item) for item in raw if item and str(item).isdigit()]

    def _serialize_employee(self, employee):
        employee = employee.sudo()
        manager = employee.parent_id if employee.parent_id and employee.parent_id != employee else employee.browse()
        return {
            "id": employee.id,
            "name": employee.name,
            "manager_id": manager.id or False,
            "manager_name": manager.name or "",
        }

    def _selection_values(self, current_employee, subject_employee, managers):
        selectable = current_employee._get_portal_appraisal_employees()
        return {
            "selectable_employees": selectable,
            "employees_json": Markup(json.dumps([self._serialize_employee(emp) for emp in selectable]).replace("<", "\\u003c")),
            "subject_employee": subject_employee,
            "subject_avatar_src": self._employee_avatar_src(subject_employee),
            "managers": managers,
            "manager_avatar_src": {mgr.id: self._employee_avatar_src(mgr) for mgr in managers},
            "manager": managers[:1],
        }

    def _common_values(self):
        return {
            "appraisal_state_labels": _get_appraisal_state_labels(request.env),
            "appraisal_state_badges": APPRAISAL_STATE_BADGES,
        }

    def _prepare_new_form_values(self, employee, kwargs=None):
        kwargs = kwargs or {}
        selectable = employee._get_portal_appraisal_employees()
        subject_id = kwargs.get("employee_id")
        subject = selectable.browse()
        if subject_id and str(subject_id).isdigit():
            subject = selectable.filtered(lambda emp: emp.id == int(subject_id))[:1]
        if not subject:
            subject = employee.sudo()

        templates = self._get_portal_templates(subject)
        selected_id = kwargs.get("appraisal_template_id")
        selected = templates.browse()
        if selected_id and str(selected_id).isdigit():
            selected = templates.filtered(lambda rec: rec.id == int(selected_id))[:1]
        if not selected:
            selected = self._get_default_template(subject, templates)

        requested_manager_ids = self._coerce_ids(kwargs.get("manager_ids"))
        if not requested_manager_ids:
            requested_manager_ids = request.httprequest.args.getlist("manager_ids")
            requested_manager_ids = self._coerce_ids(requested_manager_ids)
        managers = selectable.filtered(lambda emp: emp.id in requested_manager_ids and emp.id != subject.id)
        if not managers:
            managers = subject._get_portal_appraisal_manager()
        if employee != subject and employee in selectable and employee not in managers:
            managers |= employee

        default_date_close = kwargs.get("date_close") or (date.today() + timedelta(days=30)).isoformat()
        values = self._common_values()
        values.update(self._selection_values(employee, subject, managers))
        values.update(
            {
                "page_name": "portal_appraisal_new",
                "is_new": True,
                "employee": employee,
                "appraisal": False,
                "templates": templates,
                "selected_template": selected,
                "state": "1_new",
                "date_close_value": default_date_close,
                "employee_feedback_html": _as_markup(
                    selected.appraisal_employee_feedback_template if selected else ""
                ),
                "manager_feedback_html": _as_markup(
                    selected.appraisal_manager_feedback_template if selected else ""
                ),
                "manager_feedback_template_html": _as_markup(
                    selected.appraisal_manager_feedback_template if selected else ""
                ),
                "employee_feedback_template_html": _as_markup(
                    selected.appraisal_employee_feedback_template if selected else ""
                ),
                "can_edit_employee": True,
                "can_edit_appraisers": True,
                "can_edit_employee_feedback": True,
                "can_see_employee_feedback": True,
                "can_edit_manager_feedback": True,
                "can_see_manager_feedback": True,
                "can_confirm": False,
                "can_edit_date": True,
                "can_edit_template": True,
                "can_publish_employee": False,
                "can_publish_manager": False,
                "show_private_note": False,
                "employee_feedback_published": True,
                "manager_feedback_published": True,
                "form_action": "/my/appraisals/submit",
                "error_message": kwargs.get("error"),
                "success_message": False,
            }
        )
        return values

    def _prepare_detail_values(self, employee, appraisal, kwargs=None):
        kwargs = kwargs or {}
        is_employee, is_appraiser = appraisal._portal_role(employee)
        state = appraisal.state
        can_see_employee = (
            is_employee
            or appraisal.employee_feedback_published
            or (is_appraiser and state == "1_new")
        )
        can_edit_employee = (is_employee and state in ("1_new", "2_pending")) or (
            is_appraiser and state == "1_new"
        )
        can_see_manager = is_appraiser or appraisal.manager_feedback_published
        can_edit_manager = is_appraiser and state in ("1_new", "2_pending")
        sudo_appraisal = appraisal.sudo()
        employee_html = sudo_appraisal.employee_feedback if can_see_employee else ""
        manager_html = sudo_appraisal.manager_feedback if can_see_manager else ""
        values = self._common_values()
        values.update(self._selection_values(employee, sudo_appraisal.employee_id, sudo_appraisal.manager_ids))
        values.update(
            {
                "page_name": "portal_appraisal_detail",
                "is_new": False,
                "employee": employee,
                "appraisal": sudo_appraisal,
                "templates": self._get_portal_templates(sudo_appraisal.employee_id),
                "selected_template": sudo_appraisal.appraisal_template_id,
                "state": state,
                "date_close_value": sudo_appraisal.date_close.isoformat() if sudo_appraisal.date_close else "",
                "employee_feedback_html": _as_markup(employee_html),
                "manager_feedback_html": _as_markup(manager_html),
                "employee_feedback_template_html": _as_markup(sudo_appraisal.employee_feedback_template),
                "manager_feedback_template_html": _as_markup(sudo_appraisal.manager_feedback_template),
                "can_edit_employee": state == "1_new",
                "can_edit_appraisers": state != "3_done" and (is_appraiser or (is_employee and state == "1_new")),
                "can_edit_employee_feedback": can_edit_employee,
                "can_see_employee_feedback": can_see_employee,
                "can_edit_manager_feedback": can_edit_manager,
                "can_see_manager_feedback": can_see_manager,
                "can_confirm": is_appraiser and not is_employee and state == "1_new",
                "can_edit_date": state != "3_done" and (is_employee or is_appraiser),
                "can_edit_template": False,
                "can_publish_employee": is_employee and state == "2_pending",
                "can_publish_manager": is_appraiser and state == "2_pending",
                "show_private_note": is_appraiser,
                "private_note_html": _as_markup(sudo_appraisal.note if is_appraiser else ""),
                "employee_feedback_published": sudo_appraisal.employee_feedback_published,
                "manager_feedback_published": sudo_appraisal.manager_feedback_published,
                "form_action": "/my/appraisals/%s/save" % appraisal.id,
                "error_message": kwargs.get("error"),
                "success_message": kwargs.get("success"),
            }
        )
        return values

    @http.route(
        ["/my/appraisals", "/my/appraisals/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_appraisals(self, page=1, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return self._no_employee_page()

        appraisal_model = request.env["hr.appraisal"].sudo()
        domain = [
            "|",
            ("employee_id", "=", employee.id),
            ("manager_ids", "in", employee.ids),
        ]
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
        values = self._common_values()
        values.update(
            {
                "page_name": "portal_appraisals",
                "employee": employee,
                "appraisals": appraisals,
                "pager": pager,
            }
        )
        return request.render("attendance_location_portal.portal_my_appraisals", values)

    @http.route("/my/appraisals/new", type="http", auth="user", website=True)
    def portal_appraisal_new(self, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return self._no_employee_page()
        values = self._prepare_new_form_values(employee, kwargs)
        return request.render("attendance_location_portal.portal_appraisal_form", values)

    @http.route(
        "/my/appraisals/template/<int:template_id>",
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_appraisal_template(self, template_id, employee_id=None, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return request.make_json_response({"error": _("No employee is linked to your user.")}, status=400)
        selectable = employee._get_portal_appraisal_employees()
        subject = employee
        if employee_id and str(employee_id).isdigit():
            subject = selectable.filtered(lambda emp: emp.id == int(employee_id))[:1] or employee
        templates = self._get_portal_templates(subject)
        template = templates.filtered(lambda rec: rec.id == template_id)[:1]
        if not template:
            return request.make_json_response({"error": _("Template not found.")}, status=404)
        return request.make_json_response(
            {
                "id": template.id,
                "name": template.description,
                "employee_feedback": template.appraisal_employee_feedback_template or "",
                "manager_feedback": template.appraisal_manager_feedback_template or "",
            }
        )

    @http.route(
        "/my/appraisals/employee/<int:employee_id>/defaults",
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_appraisal_employee_defaults(self, employee_id, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return request.make_json_response({"error": _("No employee is linked to your user.")}, status=400)
        selectable = employee._get_portal_appraisal_employees()
        subject = selectable.filtered(lambda emp: emp.id == employee_id)[:1]
        if not subject:
            return request.make_json_response({"error": _("Employee not found.")}, status=404)
        managers = subject._get_portal_appraisal_manager()
        if employee != subject and employee in selectable and employee not in managers:
            managers |= employee
        templates = self._get_portal_templates(subject)
        default_template = self._get_default_template(subject, templates)
        return request.make_json_response(
            {
                "id": subject.id,
                "name": subject.name,
                "manager_ids": [
                    {"id": mgr.id, "name": mgr.name} for mgr in managers
                ],
                "templates": [
                    {"id": template.id, "name": template.description} for template in templates
                ],
                "default_template_id": default_template.id if default_template else False,
                "employee_feedback": (
                    default_template.appraisal_employee_feedback_template if default_template else ""
                ),
                "manager_feedback": (
                    default_template.appraisal_manager_feedback_template if default_template else ""
                ),
            }
        )

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

        templates = self._get_portal_templates(employee)
        template = templates.browse()
        template_id = post.get("appraisal_template_id")
        if template_id and str(template_id).isdigit():
            subject_id = self._parse_post_ids(post, "employee_id")
            subject = employee
            if subject_id:
                selectable = employee._get_portal_appraisal_employees()
                subject = selectable.filtered(lambda emp: emp.id == subject_id[0])[:1] or employee
            templates = self._get_portal_templates(subject)
            template = templates.filtered(lambda rec: rec.id == int(template_id))[:1]

        try:
            appraisal = employee.action_portal_create_appraisal(
                {
                    "date_close": post.get("date_close"),
                    "appraisal_template_id": template,
                    "employee_feedback": post.get("employee_feedback"),
                    "manager_feedback": post.get("manager_feedback"),
                    "employee_id": (self._parse_post_ids(post, "employee_id") or [employee.id])[0],
                    "manager_ids": self._parse_post_ids(post, "manager_ids"),
                }
            )
            return request.redirect("/my/appraisals/%s" % appraisal.id)
        except (UserError, AccessError) as error:
            params = urlencode(
                [
                    ("error", str(error)),
                    ("date_close", post.get("date_close") or ""),
                    ("appraisal_template_id", template_id or ""),
                    ("employee_id", post.get("employee_id") or ""),
                ]
                + [("manager_ids", manager_id) for manager_id in self._parse_post_ids(post, "manager_ids")],
                doseq=True,
            )
            return request.redirect("/my/appraisals/new?%s" % params)
        except Exception as error:
            _logger.exception("Portal appraisal submit failed: %s", error)
            params = urlencode(
                [
                    ("error", _("Unexpected error while submitting your appraisal. Please try again.")),
                    ("date_close", post.get("date_close") or ""),
                    ("appraisal_template_id", template_id or ""),
                    ("employee_id", post.get("employee_id") or ""),
                ]
                + [("manager_ids", manager_id) for manager_id in self._parse_post_ids(post, "manager_ids")],
                doseq=True,
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
            return self._no_employee_page()

        try:
            appraisal = self._get_accessible_appraisal(employee, appraisal_id)
        except AccessError:
            return self._appraisal_failed(_("This appraisal is not accessible."))

        values = self._prepare_detail_values(employee, appraisal, kwargs)
        return request.render("attendance_location_portal.portal_appraisal_detail", values)

    def _save_post_values(self, employee, appraisal, post):
        values = {
            "date_close": post.get("date_close"),
        }
        employee_ids = self._parse_post_ids(post, "employee_id")
        manager_ids = self._parse_post_ids(post, "manager_ids")
        if employee_ids:
            values["employee_id"] = employee_ids[0]
        if manager_ids or request.httprequest.form.getlist("manager_ids"):
            values["manager_ids"] = manager_ids
        if "employee_feedback" in post:
            values["employee_feedback"] = post.get("employee_feedback")
        if "manager_feedback" in post:
            values["manager_feedback"] = post.get("manager_feedback")
        if "note" in post:
            values["note"] = post.get("note")
        if employee == appraisal.employee_id and appraisal.state == "2_pending":
            values["employee_feedback_published"] = post.get("employee_feedback_published") == "1"
        if employee in appraisal.manager_ids and appraisal.state == "2_pending":
            values["manager_feedback_published"] = post.get("manager_feedback_published") == "1"
        return appraisal.action_portal_save(employee, values)

    @http.route(
        "/my/appraisals/<int:appraisal_id>/save",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_appraisal_save(self, appraisal_id, **post):
        employee = self._get_user_employee()
        if not employee:
            params = urlencode({"error": _("No employee is linked to your user.")})
            return request.redirect("/my/appraisals/%s?%s" % (appraisal_id, params))

        try:
            appraisal = self._get_accessible_appraisal(employee, appraisal_id)
            action = post.get("portal_action") or "save"
            if action == "confirm":
                self._save_post_values(employee, appraisal, post)
                appraisal.action_portal_confirm(employee)
                params = urlencode({"success": _("The appraisal has been confirmed.")})
            else:
                self._save_post_values(employee, appraisal, post)
                params = urlencode({"success": _("Your appraisal has been saved.")})
            return request.redirect("/my/appraisals/%s?%s" % (appraisal_id, params))
        except (UserError, AccessError) as error:
            params = urlencode({"error": str(error)})
            return request.redirect("/my/appraisals/%s?%s" % (appraisal_id, params))
        except Exception as error:
            _logger.exception("Portal appraisal save failed: %s", error)
            params = urlencode(
                {"error": _("Unexpected error while saving your appraisal. Please try again.")}
            )
            return request.redirect("/my/appraisals/%s?%s" % (appraisal_id, params))

    @http.route(
        "/my/appraisals/<int:appraisal_id>/feedback",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_appraisal_feedback_submit(self, appraisal_id, **post):
        return self.portal_appraisal_save(appraisal_id, **post)
