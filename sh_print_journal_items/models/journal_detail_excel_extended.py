# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models


class JournalDetailExcelExtended(models.Model):
    _name = "journal.detail.excel.extended"
    _description = 'Excel Extended'

    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64)

    def download_report(self):

        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=journal.detail.excel.extended&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }
