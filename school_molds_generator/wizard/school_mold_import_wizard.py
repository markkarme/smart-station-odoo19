# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class SchoolMoldImportWizard(models.TransientModel):
    _name = 'school.mold.import.wizard'
    _description = 'Upload Excel into School Mold'

    mold_id = fields.Many2one('school.mold', string='Mold', required=True, ondelete='cascade')
    data_file = fields.Binary(string='Excel File', required=True)
    filename = fields.Char(string='Filename')

    def action_import(self):
        self.ensure_one()
        if not self.data_file:
            raise UserError(_('Please select an Excel file (.xlsx).'))
        if self.filename and not self.filename.lower().endswith(('.xlsx', '.xlsm')):
            raise UserError(_('Only .xlsx Excel files are supported.'))
        mold = self.mold_id
        if mold.state == 'done':
            raise UserError(_('This result is done and cannot be modified. Reset to draft first.'))
        count = mold.action_import_xlsx(self.data_file, self.filename)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Excel imported'),
                'message': _('%s row(s) loaded into the sheet.') % count,
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'school.mold',
                    'res_id': mold.id,
                    'view_mode': 'form',
                    'views': [(False, 'form')],
                    'target': 'current',
                },
            },
        }
