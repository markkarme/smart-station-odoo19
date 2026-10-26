import logging
from urllib.parse import urlencode

from odoo import _, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager

from .portal_common import PortalHrMixin

_logger = logging.getLogger(__name__)

FEE_STATE_LABELS = {
    "draft": "Draft",
    "open": "Open",
    "closed": "Closed",
}

FEE_STATE_BADGES = {
    "draft": "text-bg-secondary",
    "open": "text-bg-success",
    "closed": "text-bg-dark",
}


class PortalStudentFeePlanController(PortalHrMixin, http.Controller):
    def _require_fee_admin(self):
        if not self._is_portal_fee_admin():
            raise AccessError(_("You are not allowed to manage student fee plans."))

    def _failed_page(self, message):
        return request.render(
            "attendance_location_portal.portal_student_fee_plan_failed_page",
            {
                "page_name": "portal_student_fee_plan_failed",
                "error_message": message,
            },
        )

    def _allowed_companies(self):
        return request.env.user.company_ids.sorted("name")

    def _state_labels(self):
        return {key: request.env._(label) for key, label in FEE_STATE_LABELS.items()}

    def _get_fee_plan(self, plan_id):
        self._require_fee_admin()
        plan = request.env["student.fee.plan"].sudo().browse(plan_id)
        company_ids = set(self._portal_user_company_ids())
        if (
            not plan.exists()
            or not plan.company_id
            or plan.company_id.id not in company_ids
        ):
            raise AccessError(_("This fee plan does not exist or is not accessible."))
        return plan

    def _has_accounting(self, plan):
        return bool(hasattr(plan, "action_create_invoices_unpaid_basic"))

    def _has_exceptions(self, plan):
        return "exception_ids" in plan._fields

    def _format_money(self, plan, amount):
        currency = plan.currency_id
        try:
            return currency.format(amount or 0.0)
        except Exception:
            return "%.2f" % (amount or 0.0)

    def _years(self):
        return request.env["year.year"].sudo().search([], order="name desc, id desc")

    def _standards(self):
        return request.env["student.standard"].sudo().search([], order="name, id")

    def _students_for_company(self, company):
        Partner = request.env["res.partner"].sudo()
        domain = [("is_student", "=", True)]
        if company:
            domain.append(("company_id", "in", [False, company.id]))
        return Partner.search(domain, order="name, id", limit=2000)

    def _detail_values(self, plan, **extra):
        return {
            "page_name": "portal_student_fee_plan_detail",
            "plan": plan,
            "plan_editable": plan.state != "closed",
            "has_accounting": self._has_accounting(plan),
            "has_exceptions": self._has_exceptions(plan),
            "state_labels": self._state_labels(),
            "state_badges": FEE_STATE_BADGES,
            "format_money": lambda amount: self._format_money(plan, amount),
            "bus_categories": request.env["bus.category"].sudo().search([], order="name"),
            **extra,
        }

    @http.route(
        ["/my/fee_plans", "/my/fee_plans/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_fee_plans(self, page=1, **kwargs):
        try:
            self._require_fee_admin()
        except AccessError as error:
            return self._failed_page(str(error))

        Plan = request.env["student.fee.plan"].sudo()
        domain = self._portal_company_domain()
        plan_count = Plan.search_count(domain)
        pager = portal_pager(
            url="/my/fee_plans",
            total=plan_count,
            page=page,
            step=self._items_per_page,
        )
        plans = Plan.search(
            domain,
            order="year_id desc, student_id, id desc",
            limit=self._items_per_page,
            offset=pager["offset"],
        )
        return request.render(
            "attendance_location_portal.portal_my_fee_plans",
            {
                "page_name": "portal_student_fee_plans",
                "plans": plans,
                "pager": pager,
                "show_company": len(self._allowed_companies()) > 1,
                "state_labels": self._state_labels(),
                "state_badges": FEE_STATE_BADGES,
                "format_money": lambda plan, amount: self._format_money(plan, amount),
            },
        )

    @http.route("/my/fee_plans/new", type="http", auth="user", website=True)
    def portal_fee_plan_new(self, **kwargs):
        try:
            self._require_fee_admin()
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
            year_id = int(kwargs.get("year_id") or 0) or False
            standard_id = int(kwargs.get("standard_id") or 0) or False
            bus_category_id = int(kwargs.get("bus_category_id") or 0) or False
            basic_count = int(kwargs.get("basic_installment_count") or 3)
            bus_count = int(kwargs.get("bus_installment_count") or 2)
        except (TypeError, ValueError):
            student_id = year_id = standard_id = bus_category_id = False
            basic_count, bus_count = 3, 2

        students = self._students_for_company(company)
        student = students.filtered(lambda item: item.id == student_id)[:1]
        years = self._years()
        year = years.filtered(lambda item: item.id == year_id)[:1]
        if not year and student and student.curr_year:
            year = student.curr_year
        standards = self._standards()
        standard = standards.filtered(lambda item: item.id == standard_id)[:1]
        if not standard and student and student.standard:
            standard = student.standard
        bus_categories = request.env["bus.category"].sudo().search([], order="name")
        bus_category = bus_categories.filtered(lambda item: item.id == bus_category_id)[:1]
        if not bus_category and student and student.bus_category_id:
            bus_category = student.bus_category_id

        basic_total = kwargs.get("basic_total_due") or ""
        bus_total = kwargs.get("bus_total_due") or ""
        if not basic_total and standard:
            Plan = request.env["student.fee.plan"].sudo()
            basic_total = Plan._basic_total_from_standard(standard)
        if not bus_total and bus_category:
            bus_total = bus_category.price or 0.0

        return request.render(
            "attendance_location_portal.portal_student_fee_plan_new",
            {
                "page_name": "portal_student_fee_plan_new",
                "companies": companies,
                "company": company,
                "students": students,
                "student": student,
                "years": years,
                "year": year,
                "standards": standards,
                "standard": standard,
                "bus_categories": bus_categories,
                "bus_category": bus_category,
                "basic_installment_count": basic_count,
                "bus_installment_count": bus_count,
                "basic_total_due": basic_total,
                "bus_total_due": bus_total,
                "error_message": kwargs.get("error"),
            },
        )

    @http.route(
        "/my/fee_plans/submit",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_fee_plan_submit(self, **post):
        try:
            self._require_fee_admin()
        except AccessError as error:
            return self._failed_page(str(error))

        companies = self._allowed_companies()
        try:
            company_id = int(post.get("company_id") or 0)
            student_id = int(post.get("student_id") or 0)
            year_id = int(post.get("year_id") or 0)
            standard_id = int(post.get("standard_id") or 0) or False
            bus_category_id = int(post.get("bus_category_id") or 0) or False
            basic_count = int(post.get("basic_installment_count") or 3)
            bus_count = int(post.get("bus_installment_count") or 2)
            basic_total = float(post.get("basic_total_due") or 0)
            bus_total = float(post.get("bus_total_due") or 0)
        except (TypeError, ValueError):
            return request.redirect(
                "/my/fee_plans/new?%s" % urlencode({"error": _("Invalid fee plan values.")})
            )

        company = companies.filtered(lambda item: item.id == company_id)[:1]
        if not company:
            return self._failed_page(_("This company is not in your allowed companies."))

        students = self._students_for_company(company)
        student = students.filtered(lambda item: item.id == student_id)[:1]
        year = self._years().filtered(lambda item: item.id == year_id)[:1]
        if not student or not year:
            return request.redirect(
                "/my/fee_plans/new?%s"
                % urlencode(
                    {
                        "company_id": company.id,
                        "error": _("Student and academic year are required."),
                    }
                )
            )

        Plan = request.env["student.fee.plan"].sudo()
        existing = Plan.search(
            [
                ("student_id", "=", student.id),
                ("year_id", "=", year.id),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        if existing:
            return request.redirect(
                "/my/fee_plans/%s?%s"
                % (
                    existing.id,
                    urlencode({"error": _("A fee plan already exists for this student and year.")}),
                )
            )

        vals = {
            "company_id": company.id,
            "student_id": student.id,
            "year_id": year.id,
            "standard_id": standard_id or (student.standard.id if student.standard else False),
            "division_id": student.div.id if student.div else False,
            "class_id": student.class_id.id if student.class_id else False,
            "bus_category_id": bus_category_id
            or (student.bus_category_id.id if student.bus_category_id else False),
            "basic_installment_count": max(basic_count, 0),
            "bus_installment_count": max(bus_count, 0),
            "basic_total_due": basic_total,
            "bus_total_due": bus_total,
        }
        try:
            plan = Plan.create(vals)
        except (UserError, ValidationError) as error:
            return request.redirect(
                "/my/fee_plans/new?%s"
                % urlencode(
                    {
                        "company_id": company.id,
                        "student_id": student.id,
                        "year_id": year.id,
                        "error": str(error),
                    }
                )
            )
        except Exception as error:
            _logger.exception("Portal fee plan create failed: %s", error)
            return request.redirect(
                "/my/fee_plans/new?%s"
                % urlencode(
                    {
                        "company_id": company.id,
                        "error": _("Could not create the fee plan."),
                    }
                )
            )
        return request.redirect(
            "/my/fee_plans/%s?%s" % (plan.id, urlencode({"message": _("Fee plan created.")}))
        )

    @http.route(
        "/my/fee_plans/<int:plan_id>",
        type="http",
        auth="user",
        website=True,
    )
    def portal_fee_plan_detail(self, plan_id, **kwargs):
        try:
            plan = self._get_fee_plan(plan_id)
        except AccessError as error:
            return self._failed_page(str(error))
        return request.render(
            "attendance_location_portal.portal_student_fee_plan_detail",
            self._detail_values(
                plan,
                message=kwargs.get("message"),
                error_message=kwargs.get("error"),
                active_tab=kwargs.get("tab") or "basic",
            ),
        )

    @http.route(
        "/my/fee_plans/<int:plan_id>/action",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_fee_plan_action(self, plan_id, **post):
        try:
            plan = self._get_fee_plan(plan_id)
        except AccessError as error:
            return self._failed_page(str(error))

        action = (post.get("fee_action") or "").strip()
        params = {"tab": post.get("tab") or "basic"}
        try:
            if action == "open" and plan.state != "open":
                plan.action_open()
                params["message"] = _("Fee plan opened.")
            elif action == "close" and plan.state != "closed":
                plan.action_close()
                params["message"] = _("Fee plan closed.")
            elif action == "draft" and plan.state != "draft":
                plan.action_draft()
                params["message"] = _("Fee plan reset to draft.")
            elif action == "generate" and plan.state != "closed":
                plan.action_generate_installments()
                params["message"] = _("Installments refreshed.")
            elif action == "invoice_basic" and self._has_accounting(plan) and plan.state != "closed":
                result = plan.action_create_invoices_unpaid_basic()
                if isinstance(result, dict) and result.get("tag") == "display_notification":
                    params["error"] = result.get("params", {}).get("message") or _(
                        "No basic installments ready to invoice."
                    )
                else:
                    params["message"] = _("Basic installment invoices created.")
            elif action == "invoice_bus" and self._has_accounting(plan) and plan.state != "closed":
                result = plan.action_create_invoices_unpaid_bus()
                if isinstance(result, dict) and result.get("tag") == "display_notification":
                    params["error"] = result.get("params", {}).get("message") or _(
                        "No bus installments ready to invoice."
                    )
                else:
                    params["message"] = _("Bus installment invoices created.")
            elif action == "delete":
                plan.unlink()
                return request.redirect("/my/fee_plans")
            else:
                params["error"] = _("This action is not available.")
        except (UserError, ValidationError) as error:
            params["error"] = str(error)
        except Exception as error:
            _logger.exception("Portal fee plan action failed: %s", error)
            params["error"] = _("Could not update the fee plan.")
        return request.redirect("/my/fee_plans/%s?%s" % (plan.id, urlencode(params)))

    @http.route(
        "/my/fee_plans/<int:plan_id>/header",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_fee_plan_header(self, plan_id, **post):
        try:
            plan = self._get_fee_plan(plan_id)
        except AccessError as error:
            return self._failed_page(str(error))
        if plan.state == "closed":
            return request.redirect(
                "/my/fee_plans/%s?%s"
                % (plan.id, urlencode({"error": _("Closed plans cannot be modified."), "tab": "basic"}))
            )
        try:
            vals = {}
            if post.get("basic_total_due") not in (None, ""):
                vals["basic_total_due"] = float(post.get("basic_total_due") or 0)
            if post.get("bus_total_due") not in (None, ""):
                vals["bus_total_due"] = float(post.get("bus_total_due") or 0)
            if "bus_category_id" in post:
                try:
                    vals["bus_category_id"] = int(post.get("bus_category_id") or 0) or False
                except (TypeError, ValueError):
                    vals["bus_category_id"] = False
            if "note" in post:
                vals["note"] = post.get("note") or False
            if "penalty_price_per_week" in plan._fields and post.get("penalty_price_per_week") not in (None, ""):
                vals["penalty_price_per_week"] = float(post.get("penalty_price_per_week") or 0)
            if "installment_start_date" in plan._fields and "installment_start_date" in post:
                vals["installment_start_date"] = post.get("installment_start_date") or False
            if "installment_interval_months" in plan._fields and post.get("installment_interval_months") not in (None, ""):
                vals["installment_interval_months"] = int(post.get("installment_interval_months") or 0)
            if vals:
                plan.write(vals)
            params = {"message": _("Fee plan updated."), "tab": post.get("tab") or "basic"}
        except (UserError, ValidationError, ValueError) as error:
            params = {"error": str(error), "tab": post.get("tab") or "basic"}
        except Exception as error:
            _logger.exception("Portal fee plan header save failed: %s", error)
            params = {"error": _("Could not update the fee plan."), "tab": post.get("tab") or "basic"}
        return request.redirect("/my/fee_plans/%s?%s" % (plan.id, urlencode(params)))

    def _save_installments(self, plan, fee_type, post):
        lines = plan.basic_installment_ids if fee_type == "basic" else plan.bus_installment_ids
        for line in lines:
            prefix = "inst_%s_" % line.id
            vals = {}
            if prefix + "amount_due" in post:
                vals["amount_due"] = float(post.get(prefix + "amount_due") or 0)
            if prefix + "amount_paid" in post:
                vals["amount_paid"] = float(post.get(prefix + "amount_paid") or 0)
            if prefix + "receipt_number" in post:
                vals["receipt_number"] = post.get(prefix + "receipt_number") or False
            if prefix + "payment_date" in post:
                vals["payment_date"] = post.get(prefix + "payment_date") or False
            if prefix + "note" in post:
                vals["note"] = post.get(prefix + "note") or False
            if "due_date" in line._fields and prefix + "due_date" in post:
                vals["due_date"] = post.get(prefix + "due_date") or False
            if vals:
                line.write(vals)

    @http.route(
        "/my/fee_plans/<int:plan_id>/installments",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_fee_plan_installments(self, plan_id, **post):
        try:
            plan = self._get_fee_plan(plan_id)
        except AccessError as error:
            return self._failed_page(str(error))
        fee_type = (post.get("fee_type") or "basic").strip()
        tab = "bus" if fee_type == "bus" else "basic"
        if plan.state == "closed":
            return request.redirect(
                "/my/fee_plans/%s?%s"
                % (plan.id, urlencode({"error": _("Closed plans cannot be modified."), "tab": tab}))
            )
        try:
            self._save_installments(plan, fee_type, post)
            params = {"message": _("Installments saved."), "tab": tab}
        except (UserError, ValidationError, ValueError) as error:
            params = {"error": str(error), "tab": tab}
        except Exception as error:
            _logger.exception("Portal fee plan installments save failed: %s", error)
            params = {"error": _("Could not save installments."), "tab": tab}
        return request.redirect("/my/fee_plans/%s?%s" % (plan.id, urlencode(params)))

    @http.route(
        "/my/fee_plans/<int:plan_id>/other_fees",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_fee_plan_other_fees(self, plan_id, **post):
        try:
            plan = self._get_fee_plan(plan_id)
        except AccessError as error:
            return self._failed_page(str(error))
        fee_type = (post.get("fee_type") or "books").strip()
        tab = fee_type if fee_type in ("books", "uniform", "other") else "books"
        if plan.state == "closed":
            return request.redirect(
                "/my/fee_plans/%s?%s"
                % (plan.id, urlencode({"error": _("Closed plans cannot be modified."), "tab": tab}))
            )
        Other = request.env["student.fee.other"].sudo()
        try:
            delete_ids = set()
            for raw in post.getlist("delete_other_ids") if hasattr(post, "getlist") else request.httprequest.form.getlist("delete_other_ids"):
                try:
                    delete_ids.add(int(raw))
                except (TypeError, ValueError):
                    continue
            lines = {
                "books": plan.books_fee_ids,
                "uniform": plan.uniform_fee_ids,
                "other": plan.other_expense_ids,
            }.get(fee_type, plan.books_fee_ids)
            for line in lines:
                if line.id in delete_ids:
                    line.unlink()
                    continue
                prefix = "other_%s_" % line.id
                vals = {}
                if prefix + "amount" in post:
                    vals["amount"] = float(post.get(prefix + "amount") or 0)
                if prefix + "receipt_number" in post:
                    vals["receipt_number"] = post.get(prefix + "receipt_number") or False
                if prefix + "payment_date" in post:
                    vals["payment_date"] = post.get(prefix + "payment_date") or False
                if prefix + "note" in post:
                    vals["note"] = post.get(prefix + "note") or False
                if prefix + "description" in post:
                    vals["description"] = post.get(prefix + "description") or False
                if vals:
                    line.write(vals)

            if post.get("add_other") == "1":
                amount = float(post.get("new_amount") or 0)
                if amount:
                    Other.create(
                        {
                            "plan_id": plan.id,
                            "fee_type": fee_type,
                            "amount": amount,
                            "description": post.get("new_description") or False,
                            "receipt_number": post.get("new_receipt_number") or False,
                            "payment_date": post.get("new_payment_date") or False,
                            "note": post.get("new_note") or False,
                        }
                    )
            params = {"message": _("Other fees saved."), "tab": tab}
        except (UserError, ValidationError, ValueError) as error:
            params = {"error": str(error), "tab": tab}
        except Exception as error:
            _logger.exception("Portal fee plan other fees save failed: %s", error)
            params = {"error": _("Could not save other fees."), "tab": tab}
        return request.redirect("/my/fee_plans/%s?%s" % (plan.id, urlencode(params)))
