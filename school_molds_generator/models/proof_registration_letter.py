# -*- coding: utf-8 -*-
import base64
import os

from markupsafe import Markup
from odoo import api, fields, models
from odoo.modules.module import get_module_path


class ProofRegistrationLetter(models.TransientModel):
    _name = 'proof.registration.letter'
    _description = 'Proof of Registration'

    student_id = fields.Many2one(
        'res.partner',
        string='الطالب',
        domain=[('is_student', '=', True)],
    )
    student_name = fields.Char(string='اسم الطالب')
    addressee = fields.Char(string='إلي')
    class_name = fields.Char(string='الصف')
    specialization = fields.Char(string='التخصص')
    national_id = fields.Char(string='رقم القومي')
    academic_year = fields.Char(string='العام الدراسي')
    region = fields.Char(string='المنطقة', default='منطقة شمال الصعيد')
    station = fields.Char(string='المحطة', default='محطة سمارت')

    @api.onchange('student_id')
    def _onchange_student_id(self):
        student = self.student_id
        if not student:
            return
        self.student_name = student.name or ''
        self.national_id = student.national_iD_number or ''
        self.class_name = student.standard.name or ''
        year = student.curr_year.name or ''
        self.academic_year = year.replace('-', '/').replace('–', '/')

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
            'school_molds_generator.action_report_proof_registration_letter'
        ).report_action(self, config=False)
