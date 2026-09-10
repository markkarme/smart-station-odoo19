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


class HostelRoom(models.Model):

	_name = 'hostel.room'
	_description = "Hostel Room Management"
	_inherit = [
				'mail.thread',
				'mail.activity.mixin',
			   ]
	

	name = fields.Char("Room No.")
	room_type = fields.Selection([('ac','Ac'),
						('non_ac','Non Ac')])
	capacity = fields.Integer("Room Capacity")
	room_bed = fields.Integer("Beds")
	student_ids = fields.Many2many('res.partner',string="Students", domain=[('is_student', '=', True)])
	building_id = fields.Many2one('hostel.building',string="Building")
	is_capacity_full = fields.Boolean("Is Capacity full?")


	@api.depends('building_id')
	def _compute_display_name(self):
		for room in self:
			if room.building_id:
				building_name = room.building_id.name
				room_name = room.name
				room.display_name = f'[{building_name}]{room_name}'
			else:
				room.display_name = room.name