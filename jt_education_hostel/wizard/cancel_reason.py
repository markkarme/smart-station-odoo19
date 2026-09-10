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

class CancelReason(models.Model):

	_name = 'cancel.reason'
	_description = "Reason for Cancellation"


	name = fields.Text("Reason for Cancellation")
	closing_date = fields.Date(string="Closing Date",default=fields.Date.today())

	def save_reason(self):
		active_id = self._context.get('active_id')
		complaint_obj = self.env['student.complaints'].browse(active_id)
		values = {
			'cancel_reason': self.name,
			'closing_date': self.closing_date
		}
		complaint_obj.write(values)
		return True



	# def action_reject_reason(self):
	#     active_id = self._context.get('active_id')
	#     result = self.env['request.fund'].browse(active_id)
	#     values = {
	#         'reject_fund': self.reject_fund,
	#         'reject_description': self.description
	#     }
	#     result.write(values)
	#     self.action_grant_reject_reason()
	#     return True