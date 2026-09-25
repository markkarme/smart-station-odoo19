# -*- coding: utf-8 -*-
import base64
import os

from markupsafe import Markup
from odoo import api, fields, models, _
from odoo.modules.module import get_module_path


class HealthInsuranceLetter(models.TransientModel):
    _name = 'health.insurance.letter'
    _description = 'Health Insurance Letter'

    student_id = fields.Many2one(
        'res.partner',
        string='Student',
        domain=[('is_student', '=', True)],
    )
    student_name = fields.Char(string='اسم الطالب', required=True)
    insurance_number = fields.Char(string='رقم بطاقة التأمين الصحي', required=True)
    region = fields.Char(string='المنطقة', default='منطقة شمال الصعيد')
    station = fields.Char(string='المحطة', default='محطة سمارت')

    @api.onchange('student_id')
    def _onchange_student_id(self):
        if self.student_id:
            self.student_name = self.student_id.name or ''

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
            'school_molds_generator.action_report_health_insurance_letter'
        ).report_action(self, config=False)
