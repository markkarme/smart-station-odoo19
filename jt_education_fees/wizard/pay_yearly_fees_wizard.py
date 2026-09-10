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
from datetime import datetime
from odoo.exceptions import ValidationError


class PayBulkFeesYearly(models.TransientModel):
    _name = 'pay.yearly.fees.wizard'
    _description = 'Pay BulkFees Yearly'

    amount = fields.Float('Amount')
    year = fields.Many2one('year.year', 'Year')
    standard = fields.Many2one('student.standard', 'Standard')

    # Generate fee structure entry
    def create_entry(self):
        if self.amount <= 0:
            raise ValidationError("Amount should be greater than 0")

        stud_ids = self._context.get('active_ids')

        for stud_id in stud_ids:
            student = self.env['res.partner'].browse(stud_id)
            fee_struct_id = self.env['fees.structure'].search([
                ('student', '=', student.id),
                ('standard', '=', self.standard.id),
                ('year', '=', self.year.id),
            ], limit=1)
            if fee_struct_id:
                fee_struct_id.amount = self.amount
            else:
                vals = {
                    'student': student.id,
                    'standard': self.standard.id,
                    'year': self.year.id,
                    'amount': self.amount,
                }
                self.env['fees.structure'].create(vals)

    @api.onchange('standard')
    def _onchange_standard(self):
        if self.standard:
            self.amount = self.standard.fee
