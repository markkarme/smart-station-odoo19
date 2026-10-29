import base64
import logging
from urllib.parse import urlencode

from odoo import SUPERUSER_ID, _, fields, http
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
        return (
            "exception_ids" in plan._fields
            and "student.fee.exception.wizard" in request.env
        )

    def _exception_form_values(self, plan, form_values=None, error_message=None):
        unpaid = plan.installment_ids.filtered(lambda line: not line.is_paid).sorted(
            lambda line: (line.fee_type or "", line.number or 0, line.id)
        )
        form_values = dict(form_values or {})
        exception_type = form_values.get("exception_type") or "increase_installments"
        fee_type = form_values.get("fee_type") or "basic"
        if fee_type == "bus":
            current_count = plan.bus_installment_count or 0
        else:
            current_count = plan.basic_installment_count or 0
        selected_ids = set()
        raw_selected = form_values.get("installment_ids") or []
        if isinstance(raw_selected, str):
            raw_selected = [raw_selected]
        for raw in raw_selected:
            try:
                selected_ids.add(int(raw))
            except (TypeError, ValueError):
                continue
        return {
            "page_name": "portal_student_fee_plan_exception",
            "plan": plan,
            "unpaid_installments": unpaid,
            "selected_installment_ids": selected_ids,
            "current_installment_count": current_count,
            "default_new_count": current_count + 1,
            "form_values": form_values,
            "exception_type": exception_type,
            "error_message": error_message,
            "format_money": lambda amount: self._format_money(plan, amount),
        }

    def _read_exception_document(self):
        uploaded = request.httprequest.files.get("document")
        if not uploaded or not uploaded.filename:
            return False, False
        content = uploaded.read()
        if not content:
            return False, False
        return base64.b64encode(content), uploaded.filename

    def _fee_line_from_plan(self, plan, line_model, line_id):
        line_id = int(line_id or 0)
        if line_model == "other":
            line = request.env["student.fee.other"].sudo().browse(line_id)
            if not line.exists() or line.plan_id.id != plan.id:
                return False
            return line
        line = request.env["student.fee.installment"].sudo().browse(line_id)
        if not line.exists() or line.plan_id.id != plan.id:
            return False
        return line

    def _accounting_env(self):
        """Portal users cannot access accounting models; run fee payments as superuser."""
        return request.env(user=SUPERUSER_ID)

    def _portal_create_fee_invoice(self, line):
        """Create (+ leave draft handling to pay) without opening backend payment wizard."""
        line = line.with_user(SUPERUSER_ID)
        line.with_context(open_payment_after_invoice=False).action_create_invoice()
        invoice = line.invoice_id
        if invoice and invoice.state == "draft":
            invoice.action_post()
        return invoice

    def _fee_invoice_ready_for_payment(self, line):
        env = self._accounting_env()
        line = env[line._name].browse(line.id)
        invoice = line.invoice_id
        if not invoice:
            raise UserError(_("Create an invoice first."))
        if invoice.state == "draft":
            invoice.action_post()
        if invoice.state != "posted":
            raise UserError(_("Post the invoice before registering a payment."))
        if invoice.payment_state in ("paid", "in_payment"):
            raise UserError(_("This installment is already paid."))
        return line, invoice

    def _fee_payment_journals(self, company):
        return (
            self._accounting_env()["account.journal"]
            .search(
                [
                    ("type", "in", ["bank", "cash"]),
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "=", company.id),
                ],
                order="sequence, id",
            )
        )

    def _fee_payment_methods(self, journal):
        if not journal:
            return self._accounting_env()["account.payment.method.line"]
        methods = journal.inbound_payment_method_line_ids
        return methods or self._accounting_env()["account.payment.method.line"]

    def _portal_register_fee_payment(
        self,
        line,
        *,
        journal_id=None,
        amount=None,
        payment_date=None,
        communication=None,
        payment_method_line_id=None,
    ):
        """Register payment with the same fields as the backend Pay wizard."""
        env = self._accounting_env()
        line, invoice = self._fee_invoice_ready_for_payment(line)
        company = line.plan_id.company_id
        journals = self._fee_payment_journals(company)
        if not journal_id or journal_id not in journals.ids:
            raise UserError(_("Please select a valid payment journal."))
        journal = journals.browse(journal_id)
        methods = self._fee_payment_methods(journal)
        vals = {
            "journal_id": journal.id,
            "amount": amount if amount is not None else invoice.amount_residual,
            "payment_date": payment_date or fields.Date.context_today(invoice),
            "communication": communication or invoice.name or False,
        }
        if payment_method_line_id and payment_method_line_id in methods.ids:
            vals["payment_method_line_id"] = payment_method_line_id
        elif methods:
            vals["payment_method_line_id"] = methods[:1].id
        wizard = env["account.payment.register"].with_context(
            active_model="account.move",
            active_ids=invoice.ids,
            active_id=invoice.id,
            dont_redirect_to_payments=True,
        ).create(vals)
        wizard.action_create_payments()
        return invoice

    def _fee_pay_page_values(self, plan, line, line_model, tab, **extra):
        # Never touch account.* with the portal uid — QWeb/ORM would raise AccessError.
        env = self._accounting_env()
        plan = env["student.fee.plan"].browse(plan.id)
        line = env[line._name].browse(line.id)
        _line, invoice = self._fee_invoice_ready_for_payment(line)
        journals = self._fee_payment_journals(plan.company_id)
        if not journals:
            raise UserError(_("No bank/cash journal is configured for this company."))
        journal = journals[:1]
        payment_methods = self._fee_payment_methods(journal)
        payment_method = payment_methods[:1]
        currency = invoice.currency_id or plan.currency_id or plan.company_id.currency_id
        return {
            "page_name": "portal_student_fee_plan_pay",
            "plan": plan,
            "line": line,
            "line_model": line_model,
            "tab": tab,
            "invoice_name": invoice.display_name or "",
            "invoice_residual": invoice.amount_residual or 0.0,
            "student_name": plan.student_id.name,
            "line_name": line.display_name or line.name,
            "journal_options": [
                {"id": jour.id, "name": jour.display_name} for jour in journals
            ],
            "journal_id": journal.id,
            "payment_method_options": [
                {"id": method.id, "name": method.display_name} for method in payment_methods
            ],
            "payment_method_id": payment_method.id if payment_method else False,
            "amount": invoice.amount_residual or 0.0,
            "payment_date": fields.Date.context_today(invoice),
            "communication": invoice.name or "",
            "currency_label": (currency.symbol or currency.name) if currency else "",
            "format_money": lambda amount: self._format_money(plan, amount),
            **extra,
        }
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
    def portal_my_fee_plans(
        self,
        page=1,
        sortby=None,
        filterby=None,
        search=None,
        search_in="all",
        **kwargs,
    ):
        try:
            self._require_fee_admin()
        except AccessError as error:
            return self._failed_page(str(error))

        companies = self._allowed_companies()
        Plan = request.env["student.fee.plan"].sudo()
        domain = self._portal_company_domain()

        searchbar_filters = self._portal_company_searchbar_filters(
            companies,
            base={
                "all": {"label": _("All"), "domain": [], "sequence": 10},
                "draft": {
                    "label": _("Draft"),
                    "domain": [("state", "=", "draft")],
                    "sequence": 20,
                },
                "open": {
                    "label": _("Open"),
                    "domain": [("state", "=", "open")],
                    "sequence": 30,
                },
                "closed": {
                    "label": _("Closed"),
                    "domain": [("state", "=", "closed")],
                    "sequence": 40,
                },
            },
        )
        search_inputs = self._portal_student_searchbar_inputs(
            name_fields=["student_id.name"],
            id_fields=["student_id.stud_id"],
            extra_all_domains=lambda value: [
                [("name", "ilike", value)],
                [("year_id.name", "ilike", value)],
                [("standard_id.name", "ilike", value)],
            ],
            extra_inputs={
                "year": {
                    "input": "year",
                    "label": _("Search in Academic Year"),
                    "sequence": 40,
                    "domain": lambda value: [("year_id.name", "ilike", value)],
                },
            },
        )
        searchbar_sortings = {
            "year": {"label": _("Academic Year"), "order": "year_id desc, student_id, id desc"},
            "student": {"label": _("Student"), "order": "student_id, year_id desc, id desc"},
            "state": {"label": _("Status"), "order": "state, year_id desc"},
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
            default_sortby="year",
        )
        domain = searchbar["domain"]
        plan_count = Plan.search_count(domain)
        pager = portal_pager(
            url="/my/fee_plans",
            url_args={
                "sortby": searchbar["sortby"],
                "filterby": searchbar["filterby"],
                "search": searchbar["search"],
                "search_in": searchbar["search_in"],
            },
            total=plan_count,
            page=page,
            step=self._items_per_page,
        )
        plans = Plan.search(
            domain,
            order=searchbar["order"],
            limit=self._items_per_page,
            offset=pager["offset"],
        )
        return request.render(
            "attendance_location_portal.portal_my_fee_plans",
            {
                "page_name": "portal_student_fee_plans",
                "plans": plans,
                "pager": pager,
                "show_company": len(companies) > 1,
                "state_labels": self._state_labels(),
                "state_badges": FEE_STATE_BADGES,
                "format_money": lambda plan, amount: self._format_money(plan, amount),
                "default_url": "/my/fee_plans",
                "searchbar_filters": searchbar["searchbar_filters"],
                "filterby": searchbar["filterby"],
                "searchbar_inputs": searchbar["searchbar_inputs"],
                "search_in": searchbar["search_in"],
                "search": searchbar["search"],
                "searchbar_sortings": searchbar["searchbar_sortings"],
                "sortby": searchbar["sortby"],
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
                # Ensure counts exist when totals were filled (portal used to leave bus_count=0).
                count_vals = {}
                if (plan.basic_total_due or 0.0) > 0 and (plan.basic_installment_count or 0) <= 0:
                    count_vals["basic_installment_count"] = 3
                if (plan.bus_total_due or 0.0) > 0 and (plan.bus_installment_count or 0) <= 0:
                    count_vals["bus_installment_count"] = 2
                if count_vals:
                    plan.with_context(skip_installment_sync=True).write(count_vals)
                plan.action_generate_installments()
                params["message"] = _("Installments refreshed.")
                if (plan.bus_total_due or 0.0) > 0:
                    params["tab"] = "bus"
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
            if post.get("basic_installment_count") not in (None, ""):
                vals["basic_installment_count"] = max(int(post.get("basic_installment_count") or 0), 0)
            if post.get("bus_installment_count") not in (None, ""):
                vals["bus_installment_count"] = max(int(post.get("bus_installment_count") or 0), 0)
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
            # If totals are set but counts are still 0, default them so Refresh/Save creates lines.
            basic_total = vals.get("basic_total_due", plan.basic_total_due or 0.0)
            bus_total = vals.get("bus_total_due", plan.bus_total_due or 0.0)
            basic_count = vals.get("basic_installment_count", plan.basic_installment_count or 0)
            bus_count = vals.get("bus_installment_count", plan.bus_installment_count or 0)
            if basic_total > 0 and basic_count <= 0:
                vals["basic_installment_count"] = 3
            if bus_total > 0 and bus_count <= 0:
                vals["bus_installment_count"] = 2
            if vals:
                plan.write(vals)
            params = {
                "message": _("Fee plan updated."),
                "tab": post.get("tab") or ("bus" if vals.get("bus_total_due") or vals.get("bus_installment_count") else "basic"),
            }
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
        "/my/fee_plans/<int:plan_id>/line_action",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_fee_plan_line_action(self, plan_id, **post):
        try:
            plan = self._get_fee_plan(plan_id)
        except AccessError as error:
            return self._failed_page(str(error))

        tab = (post.get("tab") or post.get("fee_type") or "basic").strip()
        if tab not in ("basic", "bus", "books", "uniform", "other"):
            tab = "basic"
        params = {"tab": tab}

        if not self._has_accounting(plan):
            params["error"] = _("Accounting is not available for fee plans.")
            return request.redirect("/my/fee_plans/%s?%s" % (plan.id, urlencode(params)))
        if plan.state == "closed":
            params["error"] = _("Closed plans cannot be modified.")
            return request.redirect("/my/fee_plans/%s?%s" % (plan.id, urlencode(params)))

        raw_action = (post.get("line_action") or "").strip()
        action = ""
        line_id = 0
        if ":" in raw_action:
            action, raw_id = raw_action.split(":", 1)
            try:
                line_id = int(raw_id)
            except (TypeError, ValueError):
                line_id = 0
        else:
            action = raw_action
            try:
                line_id = int(post.get("line_id") or 0)
            except (TypeError, ValueError):
                line_id = 0

        line_model = (post.get("line_model") or "installment").strip()
        if tab in ("books", "uniform", "other"):
            line_model = "other"
        try:
            line = self._fee_line_from_plan(plan, line_model, line_id)
            if not line:
                raise UserError(_("Installment line not found."))
            if action == "invoice":
                self._portal_create_fee_invoice(line)
                # Same as backend: after invoicing, open the Pay form.
                return request.redirect(
                    "/my/fee_plans/%s/pay/%s/%s?%s"
                    % (
                        plan.id,
                        line_model,
                        line.id,
                        urlencode({"tab": tab, "message": _("Invoice created and posted.")}),
                    )
                )
            if action == "pay":
                return request.redirect(
                    "/my/fee_plans/%s/pay/%s/%s?%s"
                    % (plan.id, line_model, line.id, urlencode({"tab": tab}))
                )
            params["error"] = _("This action is not available.")
        except (UserError, ValidationError) as error:
            params["error"] = str(error)
        except Exception as error:
            _logger.exception("Portal fee plan line action failed: %s", error)
            params["error"] = _("Could not process the installment payment.")
        return request.redirect("/my/fee_plans/%s?%s" % (plan.id, urlencode(params)))

    @http.route(
        "/my/fee_plans/<int:plan_id>/pay/<string:line_model>/<int:line_id>",
        type="http",
        auth="user",
        website=True,
    )
    def portal_fee_plan_pay(self, plan_id, line_model, line_id, **kwargs):
        try:
            plan = self._get_fee_plan(plan_id)
        except AccessError as error:
            return self._failed_page(str(error))
        if not self._has_accounting(plan):
            return self._failed_page(_("Accounting is not available for fee plans."))

        tab = (kwargs.get("tab") or "basic").strip()
        if line_model not in ("installment", "other"):
            line_model = "other" if tab in ("books", "uniform", "other") else "installment"
        line = self._fee_line_from_plan(plan, line_model, line_id)
        if not line:
            return self._failed_page(_("Installment line not found."))
        try:
            values = self._fee_pay_page_values(
                plan,
                line,
                line_model,
                tab,
                message=kwargs.get("message"),
                error_message=kwargs.get("error"),
            )
        except (AccessError, UserError, ValidationError) as error:
            _logger.exception("Portal fee pay page failed for plan %s line %s", plan_id, line_id)
            return request.redirect(
                "/my/fee_plans/%s?%s"
                % (plan.id, urlencode({"error": str(error), "tab": tab}))
            )
        except Exception as error:
            _logger.exception("Portal fee pay page crashed for plan %s line %s: %s", plan_id, line_id, error)
            return request.redirect(
                "/my/fee_plans/%s?%s"
                % (
                    plan.id,
                    urlencode(
                        {
                            "error": _("Could not open the payment form."),
                            "tab": tab,
                        }
                    ),
                )
            )
        return request.render(
            "attendance_location_portal.portal_student_fee_plan_pay",
            values,
        )

    @http.route(
        "/my/fee_plans/<int:plan_id>/pay/<string:line_model>/<int:line_id>/submit",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_fee_plan_pay_submit(self, plan_id, line_model, line_id, **post):
        try:
            plan = self._get_fee_plan(plan_id)
        except AccessError as error:
            return self._failed_page(str(error))

        tab = (post.get("tab") or "basic").strip()
        if line_model not in ("installment", "other"):
            line_model = "other" if tab in ("books", "uniform", "other") else "installment"
        line = self._fee_line_from_plan(plan, line_model, line_id)
        if not line:
            return self._failed_page(_("Installment line not found."))

        pay_url = "/my/fee_plans/%s/pay/%s/%s" % (plan.id, line_model, line.id)
        try:
            journal_id = int(post.get("journal_id") or 0) or False
            payment_method_line_id = int(post.get("payment_method_line_id") or 0) or False
            amount = float(post.get("amount") or 0)
            payment_date = (post.get("payment_date") or "").strip() or False
            communication = (post.get("communication") or "").strip() or False
            if amount <= 0:
                raise UserError(_("Payment amount must be greater than zero."))
            self._portal_register_fee_payment(
                line,
                journal_id=journal_id,
                amount=amount,
                payment_date=payment_date,
                communication=communication,
                payment_method_line_id=payment_method_line_id,
            )
            return request.redirect(
                "/my/fee_plans/%s?%s"
                % (plan.id, urlencode({"message": _("Payment registered."), "tab": tab}))
            )
        except (UserError, ValidationError, ValueError) as error:
            return request.redirect(
                "%s?%s" % (pay_url, urlencode({"tab": tab, "error": str(error)}))
            )
        except Exception as error:
            _logger.exception("Portal fee plan payment failed: %s", error)
            return request.redirect(
                "%s?%s"
                % (
                    pay_url,
                    urlencode(
                        {
                            "tab": tab,
                            "error": _("Could not process the installment payment."),
                        }
                    ),
                )
            )

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

            # Create from the draft row on "Add Line" OR when Save is clicked with new values.
            add_requested = post.get("add_other") == "1"
            new_amount_raw = post.get("new_amount")
            new_description = (post.get("new_description") or "").strip() or False
            new_receipt = (post.get("new_receipt_number") or "").strip() or False
            new_date = (post.get("new_payment_date") or "").strip() or False
            new_note = (post.get("new_note") or "").strip() or False
            has_new_row = any(
                [
                    (new_amount_raw not in (None, "")),
                    new_description,
                    new_receipt,
                    new_date,
                    new_note,
                    add_requested,
                ]
            )
            created = False
            if has_new_row:
                try:
                    amount = float(new_amount_raw or 0)
                except (TypeError, ValueError):
                    amount = 0.0
                if add_requested or amount or new_description or new_receipt or new_date or new_note:
                    Other.create(
                        {
                            "plan_id": plan.id,
                            "fee_type": fee_type,
                            "amount": amount,
                            "description": new_description,
                            "receipt_number": new_receipt,
                            "payment_date": new_date,
                            "note": new_note,
                        }
                    )
                    created = True
            if created:
                params = {"message": _("New line added."), "tab": tab}
            elif delete_ids:
                params = {"message": _("Other fees saved."), "tab": tab}
            else:
                params = {"message": _("Other fees saved."), "tab": tab}
        except (UserError, ValidationError, ValueError) as error:
            params = {"error": str(error), "tab": tab}
        except Exception as error:
            _logger.exception("Portal fee plan other fees save failed: %s", error)
            params = {"error": _("Could not save other fees."), "tab": tab}
        return request.redirect("/my/fee_plans/%s?%s" % (plan.id, urlencode(params)))

    @http.route(
        "/my/fee_plans/<int:plan_id>/exception",
        type="http",
        auth="user",
        website=True,
        methods=["GET", "POST"],
        csrf=True,
    )
    def portal_fee_plan_exception(self, plan_id, **post):
        try:
            plan = self._get_fee_plan(plan_id)
        except AccessError as error:
            return self._failed_page(str(error))
        if not self._has_exceptions(plan):
            return self._failed_page(_("Fee exceptions are not available on this database."))
        if plan.state == "closed":
            return request.redirect(
                "/my/fee_plans/%s?%s"
                % (
                    plan.id,
                    urlencode(
                        {
                            "error": _("You cannot create an exception on a closed fee plan."),
                            "tab": "exceptions",
                        }
                    ),
                )
            )

        if request.httprequest.method == "GET":
            return request.render(
                "attendance_location_portal.portal_student_fee_plan_exception",
                self._exception_form_values(plan),
            )

        form_values = {
            "exception_type": (post.get("exception_type") or "increase_installments").strip(),
            "fee_type": (post.get("fee_type") or "basic").strip(),
            "new_installment_count": post.get("new_installment_count") or "",
            "discount_type": (post.get("discount_type") or "fixed").strip(),
            "discount_value": post.get("discount_value") or "",
            "new_due_date": post.get("new_due_date") or "",
            "reason": post.get("reason") or "",
            "installment_ids": request.httprequest.form.getlist("installment_ids"),
        }
        try:
            document, document_filename = self._read_exception_document()
            if not document:
                raise UserError(_("Please upload a supporting document."))

            exception_type = form_values["exception_type"]
            Wizard = request.env["student.fee.exception.wizard"].sudo()
            vals = {
                "plan_id": plan.id,
                "exception_type": exception_type,
                "document": document,
                "document_filename": document_filename,
                "reason": form_values["reason"] or False,
            }
            if exception_type == "increase_installments":
                vals.update(
                    {
                        "fee_type": form_values["fee_type"]
                        if form_values["fee_type"] in ("basic", "bus")
                        else "basic",
                        "new_installment_count": int(form_values["new_installment_count"] or 0),
                    }
                )
            elif exception_type == "discount":
                installment_ids = []
                for raw in form_values["installment_ids"]:
                    try:
                        installment_ids.append(int(raw))
                    except (TypeError, ValueError):
                        continue
                vals.update(
                    {
                        "discount_type": form_values["discount_type"],
                        "discount_value": float(form_values["discount_value"] or 0),
                        "installment_ids": [(6, 0, installment_ids)],
                    }
                )
            elif exception_type == "change_due_date":
                installment_ids = []
                for raw in form_values["installment_ids"]:
                    try:
                        installment_ids.append(int(raw))
                    except (TypeError, ValueError):
                        continue
                vals.update(
                    {
                        "new_due_date": form_values["new_due_date"] or False,
                        "installment_ids": [(6, 0, installment_ids)],
                    }
                )
            else:
                raise UserError(_("Invalid exception type."))

            wizard = Wizard.create(vals)
            wizard.action_confirm()
            return request.redirect(
                "/my/fee_plans/%s?%s"
                % (
                    plan.id,
                    urlencode(
                        {
                            "message": _("Exception applied."),
                            "tab": "exceptions",
                        }
                    ),
                )
            )
        except (UserError, ValidationError, ValueError) as error:
            return request.render(
                "attendance_location_portal.portal_student_fee_plan_exception",
                self._exception_form_values(
                    plan,
                    form_values=form_values,
                    error_message=str(error),
                ),
            )
        except Exception as error:
            _logger.exception("Portal fee plan exception failed: %s", error)
            return request.render(
                "attendance_location_portal.portal_student_fee_plan_exception",
                self._exception_form_values(
                    plan,
                    form_values=form_values,
                    error_message=_("Could not apply the exception."),
                ),
            )
