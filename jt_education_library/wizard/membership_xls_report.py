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
from odoo import models, fields, api, _
import io
import base64
from xlwt import Workbook
import xlsxwriter

class MembershipXlsReport(models.TransientModel):
    _name = "membership.xls.report"
    _description = "Membership Xls Report"

    membership_ids = fields.Many2many("library.memberships", string="Memberships")
    excel_file = fields.Binary("Download Report")
    file_name = fields.Char("File Name", size=64)
    select_all_membership = fields.Boolean("Select All Memberships")

    @api.onchange('select_all_membership')
    def _onchange_select_all_membership(self):
        if self.select_all_membership:
            memberships = self.env['library.memberships'].search([])
            self.membership_ids = [(6, 0, memberships.ids)]

    def membership_xls_report_template(self):

        output = io.BytesIO()
        
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(_('Membership Details'))
        header_style = workbook.add_format({'bold': True, 'align': 'center'})
        header_table = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#CCCCCC'})
        value_style1 = workbook.add_format({'bg_color': '#DDDDDD', 'align': 'center'})
        value_style2 = workbook.add_format({'bg_color': '#EEEEEE', 'align': 'center'})
        style = workbook.add_format()

        filename_1 = "Membership Details Report.xls"
        row = 0
        col = 0
        
        sheet.merge_range(row, col, row, 7, 'Membership Details',header_style)

        row = row + 2
        col = 0
        sheet.merge_range(row, col, 7, 7, '')
        if self.env.user and self.env.user.company_id and self.env.user.company_id.logo:
            filename = 'logo.png'
            image_data = io.BytesIO(base64.standard_b64decode(self.env.user.company_id.logo))
            sheet.insert_image(row,col, filename, {'image_data': image_data,'x_offset':8,'y_offset':3,'x_scale':0.1,'y_scale':0.1})

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
        sheet.write(row,col,address,header_style)
        
        row += 8
        col = 0
        sheet.set_column(col, col,5)
        sheet.write(row,col,_('Sr'),header_table)

        col +=1
        sheet.set_column(col, col,17)
        sheet.write(row,col,_('Memberships'),header_table)
        
        col +=1 
        sheet.set_column(col, col,17)
        sheet.write(row,col,_('Student ID'),header_table)
        
        col += 1
        sheet.set_column(col, col,17)
        sheet.write(row,col,_('Student Name'),header_table)
        
        col += 1
        sheet.set_column(col, col,10)
        sheet.write(row,col,_('Book Limit'),header_table)
        
        col += 1
        sheet.set_column(col, col,12)
        sheet.write(row,col,_('Start Date'),header_table)
        
        col += 1
        sheet.set_column(col, col,12)
        sheet.write(row,col,_('End Date'),header_table)
        
        col += 1
        sheet.set_column(col, col,10)
        sheet.write(row,col,_('State'),header_table)        
        
        row += 1
        col = 0
        count = 1
        membership_data = self.env['library.memberships'].search(
            [('id', 'in', self.membership_ids.ids)])
        for membership in membership_data:

            if row%2 == 0:
                style= value_style1
            else:
                style = value_style2

            sheet.write(row, col, count, style)

            sheet.write(
                row, col + 1, membership.memberships_code  or '', style)

            sheet.write(
                row, col + 2, membership.student_id.stud_id or '', style)

            sheet.write(
                row, col + 3, membership.student_id.name or '', style)

            sheet.write(
                row, col + 4, membership.book_limit or '', style)

            sheet.write(
                row, col + 5, str(membership.start_date) or '', style)

            sheet.write(
                row, col + 6, str(membership.end_date) or '', style)

            sheet.write(
                row, col + 7, membership.state or '', style)
            
            count = count + 1
            row += 1
        
        workbook.close()
        xlsx_data = base64.encodebytes(output.getvalue())
        res_id = self.env['membership.xls.report'].create(
            {'excel_file': xlsx_data, 'file_name': filename_1})

        return {
            'name': 'Membership Details',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'res_model': 'membership.xls.report',
            'domain': [],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': res_id.id,
            'context': self._context,
        }
