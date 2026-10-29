import logging
from urllib.parse import urlencode

from odoo import _, fields, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager

from .portal_common import PortalHrMixin

_logger = logging.getLogger(__name__)


class PortalStudentViolationController(PortalHrMixin, http.Controller):
    def _require_misconduct_admin(self):
        if not self._is_portal_misconduct_admin():
            raise AccessError(_("You are not allowed to manage student misconduct."))

    def _failed_page(self, message):
        return request.render(
            "attendance_location_portal.portal_student_misconduct_failed_page",
            {
                "page_name": "portal_student_misconduct_failed",
                "error_message": message,
            },
        )

    def _allowed_companies(self):
        return request.env.user.company_ids.sorted("name")

    def _students_for_company(self, company):
        Partner = request.env["res.partner"].sudo()
        domain = [("is_student", "=", True)]
        if company:
            domain.append(("company_id", "in", [False, company.id]))
        return Partner.search(domain, order="name, id", limit=3000)

    def _classes(self):
        return request.env["student.class"].sudo().search([], order="name, id")

    def _divisions(self):
        return request.env["standard.division"].sudo().search([], order="name, id")

    def _selection_options(self, model, field_name):
        field = request.env[model]._fields[field_name]
        return [
            {"value": key, "label": request.env._(label)}
            for key, label in field.selection
        ]

    def _get_violation(self, violation_id):
        self._require_misconduct_admin()
        violation = request.env["student.violation"].sudo().browse(violation_id)
        company_ids = set(self._portal_user_company_ids())
        if (
            not violation.exists()
            or not violation.company_id
            or violation.company_id.id not in company_ids
        ):
            raise AccessError(_("This violation does not exist or is not accessible."))
        return violation

    def _form_values(self, **extra):
        return {
            "violation_types": self._selection_options("student.violation", "violation_type"),
            "action_options": self._selection_options("student.violation", "action_taken"),
            "classes": self._classes(),
            "divisions": self._divisions(),
            **extra,
        }

    @http.route(
        ["/my/student_violations", "/my/student_violations/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_student_violations(
        self,
        page=1,
        sortby=None,
        filterby=None,
        search=None,
        search_in="all",
        **kwargs,
    ):
        try:
            self._require_misconduct_admin()
        except AccessError as error:
            return self._failed_page(str(error))

        companies = self._allowed_companies()
        Violation = request.env["student.violation"].sudo()
        domain = self._portal_company_domain()
        searchbar_filters = self._portal_company_searchbar_filters(
            companies,
            base={"all": {"label": _("All"), "domain": [], "sequence": 10}},
        )
        search_inputs = self._portal_student_searchbar_inputs(
            name_fields=["student_id.name"],
            id_fields=["student_id.stud_id", "stud_id"],
            extra_all_domains=lambda value: [
                [("violation_type", "ilike", value)],
                [("action_taken", "ilike", value)],
                [("notes", "ilike", value)],
                [("description", "ilike", value)],
            ],
        )
        searchbar_sortings = {
            "date": {"label": _("Newest"), "order": "date desc, id desc"},
            "student": {"label": _("Student"), "order": "student_id, date desc"},
        }
        searchbar = self._portal_apply_searchbar(
            domain,
            searchbar_filters=searchbar_filters,
            searchbar_inputs=search_inputs,
            searchbar_sortings=searchbar_sortings,
            filterby=filterby,
            search=search,
            search_in=search_in,
            sortby=sortby,
            default_filterby="all",
            default_search_in="all",
            default_sortby="date",
        )
        domain = searchbar["domain"]
        total = Violation.search_count(domain)
        pager = portal_pager(
            url="/my/student_violations",
            url_args={
                "sortby": searchbar["sortby"],
                "filterby": searchbar["filterby"],
                "search": searchbar["search"],
                "search_in": searchbar["search_in"],
            },
            total=total,
            page=page,
            step=self._items_per_page,
        )
        records = Violation.search(
            domain,
            order=searchbar["order"],
            limit=self._items_per_page,
            offset=pager["offset"],
        )
        return request.render(
            "attendance_location_portal.portal_my_student_violations",
            {
                "page_name": "portal_student_violations",
                "violations": records,
                "pager": pager,
                "show_company": len(companies) > 1,
                "violation_labels": dict(Violation._fields["violation_type"].selection),
                "action_labels": dict(Violation._fields["action_taken"].selection),
                "default_url": "/my/student_violations",
                "searchbar_filters": searchbar["searchbar_filters"],
                "filterby": searchbar["filterby"],
                "searchbar_inputs": searchbar["searchbar_inputs"],
                "search_in": searchbar["search_in"],
                "search": searchbar["search"],
                "searchbar_sortings": searchbar["searchbar_sortings"],
                "sortby": searchbar["sortby"],
                "message": kwargs.get("message"),
                "error_message": kwargs.get("error"),
            },
        )

    @http.route("/my/student_violations/new", type="http", auth="user", website=True)
    def portal_student_violation_new(self, **kwargs):
        try:
            self._require_misconduct_admin()
        except AccessError as error:
            return self._failed_page(str(error))
        companies = self._allowed_companies()
        if not companies:
            return self._failed_page(_("No allowed companies are configured for your user."))
        try:
            company_id = int(kwargs.get("company_id") or companies[:1].id)
        except (TypeError, ValueError):
            company_id = companies[:1].id
        company = companies.filtered(lambda item: item.id == company_id)[:1]
        if not company:
            return self._failed_page(_("This company is not in your allowed companies."))
        try:
            student_id = int(kwargs.get("student_id") or 0) or False
        except (TypeError, ValueError):
            student_id = False
        students = self._students_for_company(company)
        student = students.filtered(lambda item: item.id == student_id)[:1]
        return request.render(
            "attendance_location_portal.portal_student_violation_form",
            self._form_values(
                page_name="portal_student_violation_new",
                companies=companies,
                company=company,
                students=students,
                student=student,
                violation=False,
                form_values={
                    "date": kwargs.get("date") or fields.Date.context_today(request.env.user),
                    "violation_type": kwargs.get("violation_type") or "",
                    "action_taken": kwargs.get("action_taken") or "",
                    "class_id": int(kwargs.get("class_id") or 0) or (student.class_id.id if student else False),
                    "div_id": int(kwargs.get("div_id") or 0) or (student.div.id if student and student.div else False),
                    "description": kwargs.get("description") or "",
                    "notes": kwargs.get("notes") or "",
                },
                error_message=kwargs.get("error"),
            ),
        )

    @http.route(
        "/my/student_violations/submit",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_student_violation_submit(self, **post):
        try:
            self._require_misconduct_admin()
        except AccessError as error:
            return self._failed_page(str(error))
        companies = self._allowed_companies()
        try:
            company_id = int(post.get("company_id") or 0)
            student_id = int(post.get("student_id") or 0)
            class_id = int(post.get("class_id") or 0) or False
            div_id = int(post.get("div_id") or 0) or False
        except (TypeError, ValueError):
            return request.redirect(
                "/my/student_violations/new?%s"
                % urlencode({"error": _("Invalid form values.")})
            )
        company = companies.filtered(lambda item: item.id == company_id)[:1]
        if not company:
            return self._failed_page(_("This company is not in your allowed companies."))
        if not student_id or not post.get("violation_type") or not post.get("date"):
            return request.redirect(
                "/my/student_violations/new?%s"
                % urlencode(
                    {
                        "error": _("Student, date and violation type are required."),
                        "company_id": company_id,
                        "student_id": student_id or "",
                    }
                )
            )
        try:
            violation = request.env["student.violation"].sudo().create(
                {
                    "company_id": company.id,
                    "student_id": student_id,
                    "class_id": class_id,
                    "div_id": div_id,
                    "date": post.get("date"),
                    "violation_type": post.get("violation_type"),
                    "action_taken": post.get("action_taken") or False,
                    "description": post.get("description") or False,
                    "notes": post.get("notes") or False,
                }
            )
            return request.redirect(
                "/my/student_violations/%s?%s"
                % (violation.id, urlencode({"message": _("Violation created.")}))
            )
        except (UserError, ValidationError, ValueError) as error:
            return request.redirect(
                "/my/student_violations/new?%s"
                % urlencode({"error": str(error), "company_id": company_id, "student_id": student_id})
            )
        except Exception as error:
            _logger.exception("Portal student violation create failed: %s", error)
            return request.redirect(
                "/my/student_violations/new?%s"
                % urlencode({"error": _("Could not create the violation."), "company_id": company_id})
            )

    @http.route(
        "/my/student_violations/<int:violation_id>",
        type="http",
        auth="user",
        website=True,
    )
    def portal_student_violation_detail(self, violation_id, **kwargs):
        try:
            violation = self._get_violation(violation_id)
        except AccessError as error:
            return self._failed_page(str(error))
        companies = self._allowed_companies()
        students = self._students_for_company(violation.company_id)
        return request.render(
            "attendance_location_portal.portal_student_violation_form",
            self._form_values(
                page_name="portal_student_violation_detail",
                companies=companies,
                company=violation.company_id,
                students=students,
                student=violation.student_id,
                violation=violation,
                form_values={
                    "date": violation.date,
                    "violation_type": violation.violation_type or "",
                    "action_taken": violation.action_taken or "",
                    "class_id": violation.class_id.id if violation.class_id else False,
                    "div_id": violation.div_id.id if violation.div_id else False,
                    "description": violation.description or "",
                    "notes": violation.notes or "",
                },
                message=kwargs.get("message"),
                error_message=kwargs.get("error"),
            ),
        )

    @http.route(
        "/my/student_violations/<int:violation_id>/save",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_student_violation_save(self, violation_id, **post):
        try:
            violation = self._get_violation(violation_id)
        except AccessError as error:
            return self._failed_page(str(error))
        try:
            class_id = int(post.get("class_id") or 0) or False
            div_id = int(post.get("div_id") or 0) or False
            student_id = int(post.get("student_id") or 0) or violation.student_id.id
            violation.write(
                {
                    "student_id": student_id,
                    "class_id": class_id,
                    "div_id": div_id,
                    "date": post.get("date") or violation.date,
                    "violation_type": post.get("violation_type") or violation.violation_type,
                    "action_taken": post.get("action_taken") or False,
                    "description": post.get("description") or False,
                    "notes": post.get("notes") or False,
                }
            )
            params = {"message": _("Violation saved.")}
        except (UserError, ValidationError, ValueError) as error:
            params = {"error": str(error)}
        except Exception as error:
            _logger.exception("Portal student violation save failed: %s", error)
            params = {"error": _("Could not save the violation.")}
        return request.redirect("/my/student_violations/%s?%s" % (violation.id, urlencode(params)))

    @http.route(
        "/my/student_violations/<int:violation_id>/delete",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_student_violation_delete(self, violation_id, **post):
        try:
            violation = self._get_violation(violation_id)
        except AccessError as error:
            return self._failed_page(str(error))
        try:
            violation.unlink()
            return request.redirect(
                "/my/student_violations?%s" % urlencode({"message": _("Violation deleted.")})
            )
        except Exception as error:
            _logger.exception("Portal student violation delete failed: %s", error)
            return request.redirect(
                "/my/student_violations/%s?%s"
                % (violation_id, urlencode({"error": _("Could not delete the violation.")}))
            )
