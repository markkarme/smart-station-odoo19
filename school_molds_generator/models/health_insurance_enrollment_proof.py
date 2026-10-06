# -*- coding: utf-8 -*-
import base64
import os

from markupsafe import Markup
from odoo import fields, models
from odoo.modules.module import get_module_path


class HealthInsuranceEnrollmentProof(models.TransientModel):
    _name = 'health.insurance.enrollment.proof'
    _description = 'Health Insurance Enrollment Proof 2'

    student_count = fields.Integer(string='عدد الطلاب')
    academic_year = fields.Char(string='العام الدراسي')
    region = fields.Char(string='المنطقة', default='منطقة شمال الصعيد')
    station = fields.Char(string='المحطة', default='محطة سمارت')

    def get_asset_data_uri(self, filename):
        """Return a data URI for a logo so wkhtmltopdf does not need HTTP."""
        module_path = get_module_path('school_molds_generator')
        path = os.path.join(module_path, 'static', 'assets', filename)
        if not os.path.isfile(path):
            return ''
        with open(path, 'rb') as handle:
            encoded = base64.b64encode(handle.read()).decode('ascii')
        return 'data:image/png;base64,%s' % encoded

    def get_arabic_font_face_css(self):
        """Embed DejaVu Sans so Arabic glyphs render in wkhtmltopdf."""
        fonts = (
            ('normal', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
            ('bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
        )
        rules = []
        for weight, path in fonts:
            if not os.path.isfile(path):
                continue
            with open(path, 'rb') as handle:
                encoded = base64.b64encode(handle.read()).decode('ascii')
            rules.append(
                "@font-face{"
                "font-family:'ReportArabic';"
                "src:url(data:font/truetype;charset=utf-8;base64,%s) format('truetype');"
                "font-weight:%s;font-style:normal;}"
                % (encoded, weight)
            )
        return Markup(''.join(rules))

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref(
            'school_molds_generator.action_report_health_insurance_enrollment_proof'
        ).report_action(self, config=False)
