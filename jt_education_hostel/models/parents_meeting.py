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


class ParentsMeeting(models.Model):

	_name = 'parent.meeting'
	_description = "Meeting with Parents"
	_inherit = [
				'mail.thread',
				'mail.activity.mixin',
			   ]
	
	name = fields.Char("Name")
	start_date = fields.Date(string="Start Date", default=fields.Date.today())
	end_date = fields.Date(string="End Date")
	agenda = fields.Text(string="Agenda")
	standard = fields.Many2one('student.standard',string="Standard",store=True)
	division = fields.Many2one('standard.division',string="Division",store=True)
