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
from datetime import datetime, timedelta
import json


class HostelRegistration(models.Model):

	_name = 'hostel.registration'
	_description = "Hostel Registration"
	_rec_name = 'hostel_fee_seq'
	_inherit = [
				'mail.thread',
				'mail.activity.mixin',
			   ]

	hostel_fee_seq = fields.Char('Refrence',copy=False,readonly=True,index=True)
	student_id = fields.Many2one('res.partner', string="Student", domain=[('is_student', '=', True)]) 
	standard = fields.Many2one('student.standard',string="Standard",store=True)
	division = fields.Many2one('standard.division',string="Division",store=True)
	curr_year_id = fields.Many2one('year.year', string='Academic Year',store=True)
	building_id = fields.Many2one('hostel.building',"Building")
	room_id = fields.Many2one('hostel.room',string="Room",domain="[('building_id', '=', building_id),('is_capacity_full','=',False)]",)
	room_type = fields.Selection([('ac','Ac'),
						('non_ac','Non Ac')],related='room_id.room_type',string="Room Type")
	state = fields.Selection([('new', 'New'),('active', 'Active'),
		('cancelled','Cancelled'),('release','Released')], default="new", string="Status", readonly=True)
	registration_ids = fields.One2many('hostel.registration.line','registration_id',"House Keeping")
	invoice_state = fields.Selection([('no','Nothing to Invoice'),('to_invoice','To Invoice'),('invoiced','Invoiced')],default='to_invoice')
	payment_state = fields.Selection([('not_paid','Not Paid'),('paid','Paid'),('partial','Partially Paid')])
	invoice_count = fields.Float('Invoices Count', compute='_compute_invoice_count')
	image_1920 = fields.Image()

	@api.constrains('standard', 'division', 'student_id','state')
	def _check_duplicate_record(self):
		for rec in self:
			existing_record = self.search([
				('standard', '=', rec.standard.id),
				('division', '=', rec.division.id),
				('student_id', '=', rec.student_id.id),
				('state','=','active'),
				('id', '!=', rec.id)
			])
			if existing_record:
				raise ValidationError("Student Already registered")

	@api.model_create_multi
	def create(self,vals):
		for record in vals:
			if record.get('student_id'):
				record['hostel_fee_seq'] = self.env['ir.sequence'].next_by_code('hostel.sequence') 
		result = super(HostelRegistration,self).create(vals)
		return result


	@api.model
	def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
		result = super(HostelRegistration, self).fields_view_get(
			view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu
		)
		if view_type == 'form':
			# Calculate invoice_count based on your model logic
			invoice_count = ...  # Calculate or fetch invoice count

			# Pass invoice_count to the context
			result['fields']['invoice_count'] = invoice_count
			result['context']['invoice_count'] = invoice_count

		return result

	@api.onchange('student_id')
	def _onchange_student_id(self):
		if self.student_id:
			student = self.env['res.partner'].search([('id', '=', self.student_id.id)])

			if student:
				self.standard = student.standard
				self.division = student.div
				self.curr_year_id = student.curr_year
			else:
				self.standard = False
				self.division = False
				self.curr_year_id = False

	
	
	def _onchange_building_id(self):
		for rec in self:
			rooms = self.env['hostel.room'].search([('building_id', '=', rec.building_id.id)])
			for room in rooms:
				room_capacity = room.capacity
				current_students_count = len(room.student_ids)
				if current_students_count >= room_capacity:

					room.is_capacity_full = True
				else:
					room.is_capacity_full = False

	
	def _onchange_room_id(self):
		for rec in self:
			if rec.state == 'active':
				if rec.room_id and rec.student_id:
					room_capacity = rec.room_id.capacity
					current_students_count = len(rec.student_id)	
					# prev_room = self.env['hostel.room'].search([('student_ids', 'in', [rec.student_id.id])])
					# if prev_room:
					# 	prev_room.write({
					# 		'student_ids': [(3, rec.student_id.id)]
					# 	})
					rec.room_id.write({
						'student_ids': [(4, rec.student_id.id)]
					})
			else:
				print("Only Active students can select room")

	
	def student_new(self):
		self.ensure_one()
		self.state = 'new'

	def student_active(self):
		self.ensure_one()
		self.state = 'active'
		self._onchange_building_id()
		self._onchange_room_id()

	def student_release(self):
		self.ensure_one()
		self.state = 'release'
		for rec in self:
			prev_room = self.env['hostel.room'].search([('id', 'in',rec.room_id.ids),('student_ids', 'in', [rec.student_id.id])])
			if prev_room:
				prev_room.write({
					'student_ids': [(3, rec.student_id.id)]
				})


	def student_cancel(self):
		self.ensure_one()
		self.state = 'cancelled'


	def create_invoice(self):
		invoice_vals = {
			'partner_id': self.student_id.id,
			'move_type': 'out_invoice',
			'invoice_line_ids': [],
			'ref' : self.hostel_fee_seq,
		}
		for line in self.registration_ids:
			invoice_line_vals = {
				'name': line.housekeeping_id.name,
				'quantity': line.quantity,
				'price_unit': line.amount,
			}
			invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))

		self.invoice_state = 'invoiced'
		self.payment_state = 'not_paid'
		
		acc_move = self.env['account.move'].create(invoice_vals)
		acc_move.hostel_reg_id = self.id
		return True

	
	def _compute_invoice_count(self):
		for record in self:
			invoices = self.env['account.move'].search(
				[('hostel_reg_id', '=', self.id),('state','!=','cancel')])
			tmp = 0
			for invoice in invoices:
				tmp += 1
			record.invoice_count = tmp      
	

	def action_view_fees_invoice(self):
		return {
			'name': 'Invoices',
			'type': 'ir.actions.act_window',
			'res_model': 'account.move',
			'view_type': 'form',
			'view_mode': 'list,form',
			'domain': [('hostel_reg_id', '=', self.id),('state','!=','cancel')],
		}

	@api.model
	def default_get(self, fields_list):
		context = False
		params = self.env.context.get('params')
		if params:
			context = params.get('context')
			context = context.replace("'", '"')
			context = json.loads(context)
		building_id = False
		room_id = False
		if context:
			building_id = context.get('default_building_id')
			room_id = context.get('default_room_id')
		res = super(HostelRegistration, self).default_get(fields_list)
		
		if building_id:
			res.update({"building_id": int(building_id)})		
		if room_id:
			res.update({"room_id": int(room_id)})

		
		return res


class RegistrationLine(models.Model):

	_name = 'hostel.registration.line'
	_description = "Hostel Registration Line"

	housekeeping_id = fields.Many2one('hostel.housekeeping',"Name")
	quantity = fields.Integer("Quantity",default='1')
	amount = fields.Float("Amount")
	total_fees = fields.Float("Total Fees",compute="_compute_total_fees")
	registration_id = fields.Many2one('hostel.registration',"Hostel Fee")


	@api.depends('amount','quantity')
	def _compute_total_fees(self):
		for rec in self:
			rec.total_fees = rec.quantity * rec.amount



class HouseKeeping(models.Model):

	_name = 'hostel.housekeeping'
	_description = "Hostel House Keeping Service"
	_inherit = [
				'mail.thread',
				'mail.activity.mixin',
			   ]


	name = fields.Char("Name")


class ResUsers(models.Model):
	_inherit = 'res.users'

	is_student = fields.Boolean(string='Is Student', compute='_compute_is_student_and_is_parent')
	is_parent = fields.Boolean(string='Is Parent', compute='_compute_is_student_and_is_parent')

	@api.depends('partner_id')
	def _compute_is_student_and_is_parent(self):
		for user in self:
			if user.partner_id:
				user.is_student = user.partner_id.is_student
				user.is_parent = user.partner_id.is_parent
			else:
				user.is_student = False
				user.is_parent = False 


