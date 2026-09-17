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
from odoo import models, fields, api
import xlwt
import io
import base64
from xlwt import easyxf
from PIL import Image
import tempfile


class Bookxlsreport(models.TransientModel):
    _name = "book.xls.report"
    _description = "Book Xls Report"

    book_ids = fields.Many2many("books.books", string="Book Name")
    excel_file = fields.Binary("Download Report")
    file_name = fields.Char("File Name", size=64)
    select_all_books = fields.Boolean("Select All Books")

    @api.onchange('select_all_books')
    def _onchange_select_all_books(self):
        if self.select_all_books:
            books = self.env['books.books'].search([])
            self.book_ids = [(6, 0, books.ids)]

    def book_xls_report_template(self):
        fp = io.BytesIO()
        filename = "Book Details Report.xls"
        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet('Books Details', cell_overwrite_ok=True)

        sub_header_style = xlwt.easyxf('pattern: pattern solid, fore_colour white;' 'font: name Helvetica size 16 px, '
                                           'bold 1;' 'borders: top thin, right thin, bottom thin, left thin;' 'align: wrap on, horiz center, vert centre;')
        sheet.write_merge(0, 0, 0, 5, 'Book Details', easyxf(
                'font:height 300;font:bold True;align: horiz center, vert centre;'))
        sheet.row(0).height = 70 * 8

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
            sheet.insert_bitmap(path, 2, 0)

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
        sheet.col(col).width = 3000
        sheet.write_merge(row, row + 6, col, col + 5,
                          address, sub_header_style)
        
        header_table = xlwt.easyxf(
            "font: name Helvetica size 13 px, height 170;font:bold True;align: horiz center, vert centre;pattern: pattern solid, pattern_fore_colour light_green, pattern_back_colour light_green;")
        header = xlwt.easyxf(
            "font: name Helvetica size 13 px, height 170;font:bold True;align: horiz center, vert centre;")
        sub_header = xlwt.easyxf(
            "font: name Helvetica size 12 px, height 170;align: horiz center,vert centre;")
        # sub_header_even = xlwt.easyxf(
            # "font: name Helvetica size 12 px, height 170;align: horiz center,vert centre;pattern: pattern solid, pattern_fore_colour light_blue, pattern_back_colour light_blue;")
        
        row = row + 8
        col = 0
        
        sheet.write(row, col, 'Sr', header_table)

        sheet.col(col + 1).width = 256 * 17
        sheet.write(row, col + 1,'Books', header_table)

        sheet.col(col + 2).width = 256 * 17
        sheet.write(row, col + 2, 'Name', header_table)

        sheet.col(col + 3).width = 256 * 17
        sheet.write(row, col + 3, 'Author', header_table)

        sheet.col(col + 4).width = 256 * 17
        sheet.write(row, col + 4, 'Genres', header_table)

        sheet.col(col + 5).width = 256 * 17
        sheet.write(row, col + 5, 'Number of Books', header_table)
        
        row = row + 1
        count = 1
        # data
        books_data = self.env['books.books'].search(
            [('id', 'in', self.book_ids.ids)])
        for book in books_data:
            col = 0
            sheet.write(row, col, count, sub_header)

            sheet.write(
                row, col + 1, book.books_code  or '', sub_header)

            sheet.write(
                row, col + 2, book.name or '', sub_header)

            sheet.write(
                row, col + 3, book.author.name or '', sub_header)

            sheet.write(
                row, col + 4, book.genres or '', sub_header)

            sheet.write(
                row, col + 5, book.no_of_books or '', sub_header)
            count = count + 1
            row += 1

        # for c in range(0,row,2):
        #     print("c::::::::::::::::::::::::::::",c)
            
        no_of_books = []
        for rec in books_data:
            no_of_books.append(rec.no_of_books)

        col = 0
        sheet.write(row, col + 5, 'Total : ' + str(sum(no_of_books)) , header)
        
        # file pointer lidhu, bytesio binary data sathe tackel kari tyare use
        # thai.
        fp = io.BytesIO()
        workbook.save(fp)   # work book save karaiwu.
        res_id = self.env['book.xls.report'].create(
            {'excel_file': base64.encodebytes(fp.getvalue()), 'file_name': filename})
        fp.close()
        return{
            'view_mode': 'form',
            'res_id': res_id.id,
            'res_model': 'book.xls.report',
            'type': 'ir.actions.act_window',
            'context': self._context,
            'target': 'new',
        }




# ......function to apply odd evn row colors
# for row in books:
#                 rowx += 1
#                 for colx, value in enumerate(row):
#                     if rowx % 2 == 0:
#                         # apply style for even-numbered rows
#                         ws0.write(rowx, colx, value, mystyle)
#                     else:
#                         # no style for odd-numbered rows
#                         ws0.write(rowx, colx, value)