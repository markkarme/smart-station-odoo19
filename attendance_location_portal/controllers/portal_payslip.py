import logging
from urllib.parse import quote

from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager

from .portal_common import PortalHrMixin

_logger = logging.getLogger(__name__)

VALIDATED_PAYSLIP_STATES = ("validated", "paid")

PAYSLIP_STATE_BADGES = {
    "validated": "text-bg-success",
    "paid": "text-bg-primary",
}


def _get_payslip_state_labels(env):
    return {
        "validated": env._("Validated"),
        "paid": env._("Paid"),
    }


class PortalPayslipController(PortalHrMixin, http.Controller):
    def _payslip_domain(self, employee):
        return self._portal_employee_domain(employee) + [
            ("state", "in", list(VALIDATED_PAYSLIP_STATES)),
        ]

    def _get_employee_payslip(self, employee, payslip_id):
        payslip = request.env["hr.payslip"].sudo().browse(payslip_id)
        if (
            not payslip.exists()
            or payslip.state not in VALIDATED_PAYSLIP_STATES
            or not self._portal_can_access_employee_record(
                employee, payslip.employee_id, payslip.company_id
            )
        ):
            raise AccessError(_("This payslip does not exist or is not accessible."))
        return payslip

    def _no_employee_page(self):
        return request.render(
            "attendance_location_portal.portal_payslip_failed_page",
            {
                "page_name": "portal_payslip_failed",
                "error_message": _(
                    "Your account is not linked to an employee record. "
                    "Please contact your administrator."
                ),
            },
        )

    @http.route(
        ["/my/payslips", "/my/payslips/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_payslips(self, page=1, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return self._no_employee_page()

        payslip_model = request.env["hr.payslip"].sudo()
        domain = self._payslip_domain(employee)
        payslip_count = payslip_model.search_count(domain)
        pager = portal_pager(
            url="/my/payslips",
            total=payslip_count,
            page=page,
            step=self._items_per_page,
        )
        payslips = payslip_model.search(
            domain,
            order="date_from desc, id desc",
            limit=self._items_per_page,
            offset=pager["offset"],
        )
        return request.render(
            "attendance_location_portal.portal_my_payslips",
            {
                "page_name": "portal_payslips",
                "employee": employee,
                "payslips": payslips,
                "pager": pager,
                "payslip_state_labels": _get_payslip_state_labels(request.env),
                "payslip_state_badges": PAYSLIP_STATE_BADGES,
                "is_portal_hr_admin": self._is_portal_hr_admin(),
            },
        )

    @http.route("/my/payslips/<int:payslip_id>", type="http", auth="user", website=True)
    def portal_payslip_detail(self, payslip_id, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return self._no_employee_page()
        try:
            payslip = self._get_employee_payslip(employee, payslip_id)
        except AccessError:
            return request.render(
                "attendance_location_portal.portal_payslip_failed_page",
                {
                    "page_name": "portal_payslip_failed",
                    "error_message": _("This payslip is not accessible."),
                },
            )
        return request.render(
            "attendance_location_portal.portal_payslip_detail",
            {
                "page_name": "portal_payslip_detail",
                "employee": employee,
                "payslip": payslip,
                "payslip_state_labels": _get_payslip_state_labels(request.env),
                "payslip_state_badges": PAYSLIP_STATE_BADGES,
                "is_portal_hr_admin": self._is_portal_hr_admin(),
            },
        )

    @http.route("/my/payslips/<int:payslip_id>/pdf", type="http", auth="user", website=True)
    def portal_payslip_pdf(self, payslip_id, **kwargs):
        employee = self._get_user_employee()
        if not employee:
            return request.not_found()
        try:
            payslip = self._get_employee_payslip(employee, payslip_id)
        except AccessError:
            return request.not_found()

        report = next(iter(payslip._get_pdf_reports()))
        pdf_content, _report_type = (
            request.env["ir.actions.report"]
            .sudo()
            .with_context(lang=payslip.employee_id.lang or request.env.lang)
            ._render_qweb_pdf(report, payslip.id)
        )
        filename = (payslip.name or _("Payslip")).replace('"', "")
        return request.make_response(
            pdf_content,
            headers=[
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf_content)),
                (
                    "Content-Disposition",
                    "inline; filename*=UTF-8''%s.pdf" % quote(filename),
                ),
            ],
        )
