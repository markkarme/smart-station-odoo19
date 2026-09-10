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
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from io import BytesIO
import base64
import xlwt
import io
from PIL import Image
import tempfile

class ExportFeesHistory(models.TransientModel):
    _name = 'export.fees.history.wizard'
    _description = 'Export Fees History'

    res_id = fields.Many2one('res.partner')

    name = fields.Char('File Name', size=32)
    year = fields.Many2one('year.year', 'Year')

    state = fields.Selection(
        [('choose', 'choose'), ('get', 'get')], default='choose')
    report = fields.Binary('Download Report', readonly=True)

    formats = fields.Selection([
        ('curr_year', 'Current Year'),
        ('spec_year', 'Specific Year'),
        ('all_year', 'All Year Fees')
    ], default='all_year')
   
    def generate_report(self):
        self.ensure_one()
        fp = BytesIO()

        active_ids = self._context.get('active_ids')

        wb1 = xlwt.Workbook(encoding='utf-8')
        ws1 = wb1.add_sheet('Fees Summary Report')

        first_header_content_style = xlwt.easyxf("font: name Helvetica size 100 px, bold 1, height 270; "
                                                 "align: horiz center")
        header_content_style = xlwt.easyxf(
            "font: name Helvetica size 50 px, bold 1, height 225; align: horiz center")
        sub_header_style = xlwt.easyxf('pattern: pattern solid, fore_colour white;' 'font: name Helvetica size 16 px, '
                                           'bold 1;' 'borders: top thin, right thin, bottom thin, left thin;' 'align: wrap on, horiz center, vert centre;')
        sub_header_content_style = xlwt.easyxf(
            "font: name Helvetica size 10 px, height 170;" "alignment: wrap 0;")

        row = 1
        col = 0
        ws1.row(row).height = 500

        ws1.write_merge(row, row, 0, 7, "Fees Summary",
                        first_header_content_style)
        
        img = Image.open(io.BytesIO(
            base64.b64decode(self.env.user.company_id.logo)))
        img = img.resize((90,110),Image.ANTIALIAS)
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
        ws1.write_merge(row, row + 6, col, col + 7,
                          address, sub_header_style)

        row += 8

        labels = ['Reference', 'Student', 'Standard',
                  'Year', 'Month', 'Fee Type', 'Amount', 'Status']

        for rec in range(0, len(labels)):
            ws1.write(row, col + rec, labels[rec], sub_header_style)

        row += 1
        col = 0

        for idd in active_ids:
            student = self.env['res.partner'].browse(idd)
            if student:
                for fee in student.fees_detail:
                    month = None
                    if fee.month == '01':
                        month = 'January'
                    if fee.month == '02':
                        month = 'Fabruary'
                    if fee.month == '03':
                        month = 'March'
                    if fee.month == '04':
                        month = 'April'
                    if fee.month == '05':
                        month = 'May'
                    if fee.month == '06':
                        month = 'June'
                    if fee.month == '07':
                        month = 'July'
                    if fee.month == '08':
                        month = 'August'
                    if fee.month == '09':
                        month = 'September'
                    if fee.month == '10':
                        month = 'October'
                    if fee.month == '11':
                        month = 'November'
                    if fee.month == '12':
                        month = 'December'

                    status = None
                    if fee.state == 'draft':
                        status = 'To be paid'
                    if fee.state == 'paid':
                        status = 'Paid'
                    if fee.state == 'cancel':
                        status = 'Cancel'
                    data = [fee.name, student.name, fee.standard.name,
                            fee.year.name, month, fee.fee_type.name, fee.amount, status]

                    if self.formats == 'curr_year':
                        if fee.year.id == student.curr_year.id:
                            for rec in range(0, len(labels)):
                                ws1.write(row, col + rec,
                                          data[rec], sub_header_content_style)
                            row += 1
                    elif self.formats == 'spec_year':
                        if fee.year.id == self.year.id:
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
        context['name'] = 'Fees Summary report.xls'
        context['file'] = out
        self.write({'state': 'get', 'report': out, 'name': context['name']})

        # Return to wizard
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'export.fees.history.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
