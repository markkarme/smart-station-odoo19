# -*- coding: utf-8 -*-
##############################################################################
#
#    Jupical Technologies Pvt. Ltd.
#    Copyright (C) 2018-TODAY Jupical Technologies Pvt. Ltd.(<https://www.jupical.io>).
#    Author: Jupical Technologies Pvt. Ltd.(<https://www.jupical.io>)
#    you can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import fields, models
from io import BytesIO
import base64
import xlwt
from PIL import Image
import tempfile
import io

class ExportFeesHistory(models.TransientModel):
    _name = 'export.due.fees.history.wizard'
    _description = 'Export Fees History'

    res_id = fields.Many2one('res.partner')
    name = fields.Char('File Name', size=32)
    standard = fields.Many2one('student.standard', 'Standard')
    state = fields.Selection(
        [('choose', 'choose'), ('get', 'get')], default='choose')
    report = fields.Binary('Download Report', readonly=True)

    formats = fields.Selection([
        ('all_std', 'All Standard'),
        ('spec_std', 'Specific Standard'),
    ], default='all_std')

    def generate_due_fees_report(self):
        self.ensure_one()
        fp = BytesIO()

        active_ids = self._context.get('active_ids')

        wb1 = xlwt.Workbook(encoding='utf-8')
        ws1 = wb1.add_sheet('Due/Paid Fees Summary Report', cell_overwrite_ok=True)

        first_header_content_style = xlwt.easyxf("font: name Helvetica size 18 px, bold 1; "
                                                 "align: horiz center, vert center")
        # header_content_style = xlwt.easyxf(
        #     "font: name Helvetica size 50 px, bold 1, height 225; align: horiz center")
        sub_header_style = xlwt.easyxf('pattern: pattern solid, fore_colour white;' 'font: name Helvetica size 16 px, '
                                           'bold 1;' 'borders: top thin, right thin, bottom thin, left thin;' 'align: wrap on, horiz center, vert centre;')
        sub_header_content_style = xlwt.easyxf(
            "font: name Helvetica size 10 px, height 170;" "alignment: wrap 0;")

        row = 0
        col = 0
        ws1.row(row).height = 500

        ws1.write_merge(row, row, 0, 4, "Due/Paid Fees Summary Report",
                        first_header_content_style)

        img = Image.open(io.BytesIO(
            base64.b64decode(self.env.user.company_id.logo)))
        img = img.resize((70,110),Image.ANTIALIAS)
        if img.mode == 'P':
            img = img.convert('RGB')
        image_parts = img.split()
        lst = [image_parts[index] for index in range(0, len(image_parts))][:3]
        img = Image.merge("RGB", tuple(lst))
        img.save(fp, format='bmp')
        fp.seek(0)

        with tempfile.TemporaryDirectory() as tempdir:
            path = tempdir + '/image.bmp'
            with open(path, 'wb') as f:
                f.write(fp.getvalue())
                f.close()
            ws1.insert_bitmap(path, 2, 0)

        row = 2
        col = 0
        address = ""
        partner = self.env.user.company_id.partner_id
        if partner:
            if partner.name:
                address += str(partner.name)
                address += '\n'
            if partner.street:
                address += '\n'
                address += str(partner.street)
            if partner.street2:
                address += '\n'
                address += str(partner.street2)
            if partner.city:
                address += '\n'
                address += str(partner.city)
                address += '-'
            if partner.zip:
                address += str(partner.zip)
            if partner.state_id:
                address += ','
                address += str(partner.state_id.name)
            if partner.phone:
                address += '\n'
                address += 'Phone No.:'
                address += str(partner.phone)
            if partner.email:
                address += '\n'
                address += 'Email:'
                address += partner.email
            if partner.vat:
                address += '\n'
                address += 'GSTIN NO.'
                address += partner.vat
        ws1.col(col).width = 3000
        ws1.write_merge(row, row + 6, col, col + 4,
                          address, sub_header_style)

        row += 8
        col = 0
        ws1.col(col).width = 256 * 17
        ws1.write(row, col, 'Student', sub_header_style)

        ws1.col(col + 1).width = 256 * 17
        ws1.write(row, col + 1,'Standard', sub_header_style)

        ws1.col(col + 2).width = 256 * 17
        ws1.write(row, col + 2, 'Total Fees', sub_header_style)

        ws1.col(col + 3).width = 256 * 17
        ws1.write(row, col + 3, 'Paid Fees', sub_header_style)

        ws1.col(col + 4).width = 256 * 17
        ws1.write(row, col + 4, 'Due Fees', sub_header_style)

        labels = ['Student', 'Standard', 'Total Fees', 'Paid Fees', 'Due Fees']
        for rec in range(0, len(labels)):
            ws1.write(row, col + rec, labels[rec], sub_header_style)

        row += 1
        col = 0

        for idd in active_ids:
            student = self.env['res.partner'].browse(idd)
            if student:
                for fee in student.fee_structure:
                    paid = None
                    paid = self.env['fees.detail'].search([
                        ('student', '=', student.id),
                        ('standard', '=', fee.standard.id),
                        ('pre_school_fee', '=', False),
                        ('state', '=', 'paid')
                    ])
                    paid_fees = 0
                    due_fees = 0
                    if paid:
                        for rec in paid:
                            paid_fees += rec.amount
                    due_fees = fee.amount - paid_fees
                    data = [student.name, fee.standard.name,
                            fee.amount, paid_fees, due_fees]

                    if self.formats == 'spec_std':
                        if self.standard.id == fee.standard.id:
                            for rec in range(0, len(labels)):
                                ws1.write(row, col + rec,
                                          data[rec], sub_header_content_style)
                            row += 1
                    else:
                        for rec in range(0, len(labels)):
                            ws1.write(row, col + rec,
                                      data[rec], sub_header_content_style)
                        row += 1

        # Save XLS file into bytesIO
        wb1.save(fp)

        context = {}
        out = None

        out = base64.encodebytes(fp.getvalue())
        context['name'] = 'Paid/Due Fees Summary Report.xls'
        context['file'] = out
        self.write({'state': 'get', 'report': out, 'name': context['name']})

        # Return to wizard
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'export.due.fees.history.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
