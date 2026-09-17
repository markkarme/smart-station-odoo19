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
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
	_inherit = "account.move"


	hostel_reg_id = fields.Many2one('hostel.registration',copy=False)
	hostel_payment_state = fields.Char(compute="_update_payment_state", store=True)

	
	@api.depends('payment_state','state')
	def _update_payment_state(self):
		for rec in self:
			rec.hostel_payment_state = False
			if rec.hostel_reg_id:
				rec.hostel_reg_id.payment_state = rec.payment_state
				if rec.state == 'cancel':
					rec.hostel_reg_id.invoice_state = 'to_invoice'
				elif rec.state == 'posted':
					rec.hostel_reg_id.invoice_state = 'invoiced'

