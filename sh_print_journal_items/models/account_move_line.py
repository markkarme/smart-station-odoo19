# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models
import xlwt
import base64
from io import BytesIO


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def print_journal_item_xls_report(self):
        workbook = xlwt.Workbook()
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;borders:top thick;borders:bottom thick;')
        bold = xlwt.easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz left')
        border = xlwt.easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;borders:top thick;borders:bottom thick;')

        data = {}
        data = dict(data or {})

        worksheet = workbook.add_sheet(
            u'Journal Item Details', cell_overwrite_ok=True)
        worksheet.write_merge(
            0, 1, 0, 7, 'Journal Item Details', heading_format)
        worksheet.write_merge(0, 1, 8, 10, '', heading_format)

        active_ids = self.env.context.get('active_ids')

        move_lines = self.env['account.move.line'].search(
            [('id', 'in', active_ids)])

        worksheet.col(0).width = int(5 * 260)
        worksheet.col(1).width = int(13 * 260)
        worksheet.col(2).width = int(18 * 260)
        worksheet.col(3).width = int(18 * 260)
        worksheet.col(4).width = int(50 * 260)
        worksheet.col(5).width = int(20 * 260)
        worksheet.col(6).width = int(20 * 260)
        worksheet.col(7).width = int(20 * 260)
        worksheet.col(8).width = int(15 * 260)
        worksheet.col(9).width = int(15 * 260)
        worksheet.col(10).width = int(13 * 260)

        worksheet.write(5, 0, "Sr", bold)
        worksheet.write(5, 1, "Date", bold)
        worksheet.write(5, 2, "Journal Entry", bold)
        worksheet.write(5, 3, "Journal", bold)
        worksheet.write(5, 4, "Label", bold)
        worksheet.write(5, 5, "Reference", bold)
        worksheet.write(5, 6, "Partner", bold)
        worksheet.write(5, 7, "Account", bold)
        worksheet.write(5, 8, "Debit", bold)
        worksheet.write(5, 9, "Credit", bold)
        worksheet.write(5, 10, "Due Date", bold)
        count = 0

        journal_lines = []

        for lines in move_lines:

            count += 1
            product = {
                'count': count,
                'date': lines.date,
                'move_id': lines.move_id,
                'journal_id': lines.journal_id,
                'name': lines.name,
                'ref': lines.ref,
                'partner_id': lines.partner_id,
                'account_id': lines.account_id,
                'debit': lines.debit,
                'credit': lines.credit,
                'date_maturity': lines.date_maturity,
            }

            journal_lines.append(product)

        row = 6

        total_credit = 0.0
        total_debit = 0.0
        for rec in journal_lines:
            if rec.get('count'):
                worksheet.write(row, 0, rec.get('count'))
            if rec.get('date'):
                worksheet.write(row, 1, str(rec.get('date')))
            if rec.get('move_id'):
                worksheet.write(row, 2, str(rec.get('move_id').name))
            if rec.get('journal_id'):
                worksheet.write(row, 3, str(rec.get('journal_id').name))
            if rec.get('name'):
                worksheet.write(row, 4, rec.get('name'))
            if rec.get('ref'):
                worksheet.write(row, 5, rec.get('ref'))
            if rec.get('partner_id'):
                worksheet.write(row, 6, str(rec.get('partner_id').name))
            if rec.get('account_id'):
                worksheet.write(row, 7, str(rec.get('account_id').name))
            if rec.get('debit'):
                worksheet.write(row, 8, rec.get('debit'))
            if rec.get('credit'):
                worksheet.write(row, 9, rec.get('credit'))
            if rec.get('date_maturity'):
                worksheet.write(row, 10, str(rec.get('date_maturity')))

            total_debit += rec.get('debit')

            total_credit += rec.get('credit')

            row += 1

        row += 1
        worksheet.write(row, 0, '', border)
        worksheet.write(row, 1, "Total", border)
        worksheet.write_merge(row, row, 2, 7, '', border)
        worksheet.write(row, 8, total_debit, border)
        worksheet.write(row, 9, total_credit, border)
        worksheet.write(row, 10, '', border)

        filename = ('Journal Item Detail Xls Report' + '.xls')
        fp = BytesIO()
        workbook.save(fp)
        export_id = self.env['journal.detail.excel.extended'].sudo().create({
            'excel_file': base64.encodebytes(fp.getvalue()),
            'file_name': filename,
        })

        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=journal.detail.excel.extended&field=excel_file&download=true&id=%s&filename=%s' % (export_id.id, export_id.file_name),
            'target': 'new',
        }
