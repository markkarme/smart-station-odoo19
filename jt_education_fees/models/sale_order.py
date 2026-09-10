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
from odoo import api, fields, models,_

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    _description = "Sale Order"

    fees_id = fields.Many2one('fees.fees',string="Fees Ref")

    def _create_invoices(self, grouped=False, final=False, date=None):
        res = super()._create_invoices(grouped=grouped, final=final, date=date)
        for sale in self:
            res.update({'fees_id':sale.fees_id and sale.fees_id.id or False})
            
            fees = self.env['fees.fees'].search([('id','=',sale.fees_id.id)],limit=1)
            fees.update({'state':'invoice','payment_state':'not_paid'})
        return res


    @api.model
    def action_validate(self):
        for sale_order in self:
            if sale_order.state in ['draft','sent']:
                sale_order.action_confirm()