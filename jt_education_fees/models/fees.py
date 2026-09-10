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
from datetime import datetime
import xlwt
import io
import base64
from xlwt import easyxf
from PIL import Image
# from resizeimage import resizeimage
import tempfile
from odoo.exceptions import ValidationError

class FeesStructure(models.Model):
	_name = 'fees.structure'
	_description = 'Fees Structure'

	name = fields.Char('Reference')
	student = fields.Many2one('res.partner', 'Student', domain=[
							  ('is_student', '=', True)])
	year = fields.Many2one(related='student.curr_year', string='Year')
	amount = fields.Float('Amount')
	standard = fields.Many2one(related='student.standard', string='Standard')
	division = fields.Many2one(related='student.div', string='Division')
	product_id = fields.Many2one('product.product', string='Product')
	description = fields.Text(string="Description")
	fee_type = fields.Many2one('fees.type', 'Fees Type')
	# fees_id = fields.Many2one('fees.fees', 'Fees ID')


	@api.onchange('product_id')
	def onchange_product(self):
		if self.product_id:
			self.description = self.product_id.name
			self.amount = self.product_id.lst_price


class Fees(models.Model):
	_name = 'fees.fees'
	_description = 'Fees'
	_inherit = [
				'mail.thread',
				'mail.activity.mixin',
			
			   ]

	name = fields.Char('Receipt Number' ,copy=False)
	paid_on = fields.Datetime('Paid On')
	user_id = fields.Many2one('res.users', 'User Id')
	student = fields.Many2one('res.partner', 'Student', domain=[
							  ('is_student', '=', True)])
	standard = fields.Many2one(related='student.standard', string='Standard')
	division = fields.Many2one(related='student.div', string='Division')
	year = fields.Many2one(related='student.curr_year', string='Year')
	month = fields.Selection([
		('01', 'January'),
		('02', 'February'),
		('03', 'March'),
		('04', 'April'),
		('05', 'May'),
		('06', 'June'),
		('07', 'July'),
		('08', 'August'),
		('09', 'September'),
		('10', 'October'),
		('11', 'November'),
		('12', 'December'),
	], string='Month')
	amount = fields.Float('Total Fees Amount', store=True,
						  compute='_compute_total_fees')
	pre_school_fee = fields.Boolean('Pre School Fee')
	# user_id = fields.Many2one('res.users', 'User Id')
	fees_detail = fields.One2many('fees.detail', 'fees_id')
	state = fields.Selection([
		('draft', 'To be paid'),
		('sale', 'To Invoice'),
		('invoice', 'Invoiced'),
		('paid', 'Paid'),
		('cancel', 'Cancel'),
	], string='Status', copy=False, default='draft')

	payment_state = fields.Selection([
		('not_paid', 'Not Paid'),
		('paid', 'Paid')], string='Payment Status', default='not_paid')


	order_ref = fields.Char(string="Order Reference")
	inv_ref = fields.Char(string="Invoice Reference")

	# to get total Invoice Count
	invoice_count = fields.Float('Invoices Count', compute='_compute_invoice_count')

	# to get total Sale Order Count
	sale_order_count = fields.Float('Sale Orders Count', compute='_compute_sale_order_count')


	# smart button action for Total Sale Order Count
	def action_view_fees_sale_order(self):
		return {
			'name': 'Sale Orders',
			'type': 'ir.actions.act_window',
			'res_model': 'sale.order',
			'view_type': 'form',
			'view_mode': 'list,form',
			'domain': [('fees_id', '=', self.id),('state','!=','cancel')],
		}

	# calculate Total Sale Order
	def _compute_sale_order_count(self):
		for record in self:
			orders = self.env['sale.order'].search(
				[('fees_id', '=', self.id),('state','!=','cancel')])
			tmp = 0
			for order in orders:
				tmp += order.amount_total
			record.sale_order_count = tmp

	
	# smart button action for Total Invoices Count
	def action_view_fees_invoice(self):
		return {
			'name': 'Invoices',
			'type': 'ir.actions.act_window',
			'res_model': 'account.move',
			'view_type': 'form',
			'view_mode': 'list,form',
			'domain': [('fees_id', '=', self.id),('state','!=','cancel')],
		}

	# calculate Total Sale Order
	def _compute_invoice_count(self):
		for record in self:
			invoices = self.env['account.move'].search(
				[('fees_id', '=', self.id),('state','!=','cancel')])
			tmp = 0
			for invoice in invoices:
				tmp += invoice.amount_total
			record.invoice_count = tmp        

	@api.depends('fees_detail')
	def _compute_total_fees(self):
		for record in self:
			total = 0
			for fee in record.fees_detail:
				total += fee.amount
			record.amount = total

	# New/Draft state
	def action_draft(self):
		self.write({'state': 'draft'})

	# when fees validate (Current time/ state change)
	def action_paid(self):
		if not self.fees_detail:
			raise ValidationError(_('You need to add a line before validate.'))
		else:
			
			so = self.env['sale.order'].create({
				'partner_id': self.student.id,
				'partner_invoice_id': self.student.id,
				'fees_id': self.id,
			})
			if so:
				self.order_ref = so.name

			for record in self.fees_detail:
				self.env['sale.order.line'].create({
					'order_id': so.id,
					'name': record.product_desc, 
					'product_id': record.product_id.id, 
					'product_uom_qty': 1, 'price_unit': record.amount,
				})
			self.write({'state': 'sale'})

	# To cancel fees (refund/schlership) purpose
	def action_cancel(self):
		self.write({'state': 'cancel'})

	# To get fees is preschool fee or school fee
	@api.model
	def default_get(self, fields):
		res = super(Fees, self).default_get(fields)
		if self._context.get('pre_school_fee') == True:
			res.update({'pre_school_fee': True})
		else:
			res.update({'pre_school_fee': False})
		return res

	# For sequence and partner field entry purpose
	@api.model_create_multi
	def create(self, vals):
		for rec in vals:
			rec['user_id'] = self.env.user.id
			if rec.get('pre_school_fee'):
				rec['name'] = "PSF/" + \
					str(self.env['ir.sequence'].next_by_code('psf_seq'))
			else:
				rec['name'] = "SF/" + \
					str(self.env['ir.sequence'].next_by_code('sf_seq'))
		result = super(Fees, self).create(vals)
		for record in result:
				if record.pre_school_fee:
					record.student.fee_type = 'psf'
				else:
					record.student.fee_type = 'sf'
		return result

	# For sequence and partner field entry purpose
	def write(self, vals):
		for record in self:
			super(Fees, self).write(vals)

		if record.pre_school_fee:
			record.student.fee_type = 'psf'
		else:
			record.student.fee_type = 'sf'

	def get_fees_receipt_xls_report(self):
		fp = io.BytesIO()
		filename = 'Fees Receipt ' + str(self.name) + '.xls'
		workbook = xlwt.Workbook()
		sheet = workbook.add_sheet('FEES RECEIPT', cell_overwrite_ok=True)

		sub_header_style = xlwt.easyxf('pattern: pattern solid, fore_colour white;' 'font: name Helvetica size 16 px, '
										   'bold 1;' 'borders: top thin, right thin, bottom thin, left thin;' 'align: wrap on, horiz center, vert centre;')
		sheet.write_merge(0, 0, 0, 3, 'FEES RECEIPT', easyxf(
				'font:height 300;font:bold True;align: horiz center, vert centre;'))
		sheet.row(0).height = 70 * 8

		img = Image.open(io.BytesIO(
			base64.b64decode(self.env.user.company_id.logo)))
		img = img.resize((70,110),Image.ANTIALIAS)
		if img.mode == 'P':
			img = img.convert('RGB')
		image_parts = img.split()
		lst = [image_parts[index] for index in range(0, len(image_parts))][:3]
		img = Image.merge("RGB", tuple(lst))
		img.save(fp, format='bmp')
		fp.seek(0)

		with tempfile.TemporaryDirectory() as tempdir:
			path = tempdir + '/image.bmp'
			with open(path, 'wb') as f:
				f.write(fp.getvalue())
				f.close()
			sheet.insert_bitmap(path, 2, 0)

		row = 2
		col = 0
		address = ""
		partner = self.env.user.company_id.partner_id
		if partner:
			if partner.name:
				address += str(partner.name)
				address += '\n'
			if partner.street:
				address += '\n'
				address += str(partner.street)
			if partner.street2:
				address += '\n'
				address += str(partner.street2)
			if partner.city:
				address += '\n'
				address += str(partner.city)
				address += '-'
			if partner.zip:
				address += str(partner.zip)
			if partner.state_id:
				address += ','
				address += str(partner.state_id.name)
			if partner.phone:
				address += '\n'
				address += 'Phone No.:'
				address += str(partner.phone)
			if partner.email:
				address += '\n'
				address += 'Email:'
				address += partner.email
			if partner.vat:
				address += '\n'
				address += 'GSTIN NO.'
				address += partner.vat
		sheet.col(col).width = 3000
		sheet.write_merge(row, row + 6, col, col + 3,
						  address, sub_header_style)
		
		header_table = xlwt.easyxf(
			"font: name Helvetica size 13 px, height 170;font:bold True;align: horiz center, vert centre;pattern: pattern solid, pattern_fore_colour light_green, pattern_back_colour light_green;")
		header = xlwt.easyxf(
			"font: name Helvetica size 13 px, height 170;font:bold True;align: horiz center, vert centre;")
		sub_header = xlwt.easyxf(
			"font: name Helvetica size 12 px, height 170;align: horiz center,vert centre;")
		info = xlwt.easyxf(
			"font: name Helvetica size 13 px, height 170;align: horiz center, vert centre;")

		row = row + 8
		col = 0
		sheet.write(row, col, 'Date of Payment :', header)
		sheet.write(row, col + 1, str(self.paid_on) or '', info)
		sheet.write(row, col + 2, 'Receipt Number :', header)
		sheet.write(row, col + 3, self.name or '', info)
		
		row = row + 2
		col = 0
		sheet.write(row, col, 'Student :', header)
		sheet.write(row, col + 1, self.student.name or '', info)
		sheet.write(row, col + 2, 'Standard :', header)
		sheet.write(row, col + 3, self.standard.name + '/' + self.division.name or '', info)
		
		row = row + 2
		col = 0
		
		sheet.col(col).width = 256 * 17
		sheet.write(row, col, 'Sr', header_table)

		sheet.col(col + 1).width = 256 * 26
		sheet.write(row, col + 1,
					'Particulars', header_table)

		sheet.col(col + 2).width = 256 * 25
		sheet.write(row, col + 2, 'Amount', header_table)

		row = row + 1
		count = 1
		for fd in self.fees_detail:
			col = 0
			sheet.write(row, col, count, sub_header)

			sheet.write(
				row, col + 1, fd.fee_type.name or '', sub_header)

			sheet.write(
				row, col + 2, fd.amount or '', sub_header)
			
			count = count + 1
			row += 1

		col = 0
		sheet.write(row, col + 1, 'Total', header)
		sheet.write(
				row, col + 2, self.amount or '', header)

		note = """All above mentioned Amount once paid are non refundable in any case whatsoever. """
		row = row + 2
		col = 0
		sheet.write_merge(row, row + 1, col, col + 3, note, easyxf(
			"font: name Helvetica size; " "align: horiz center, vert centre;"))

		fp = io.BytesIO()
		workbook.save(fp)
		res_id = self.env['export.fees.receipt'].create(
			{'excel_file': base64.encodebytes(fp.getvalue()), 'file_name': filename})
		fp.close()

		return{
			'view_mode': 'form',
			'res_id': res_id.id,
			'res_model': 'export.fees.receipt',
			'type': 'ir.actions.act_window',
			'context': self._context,
			'target': 'new',
		}

class FeesDetail(models.Model):
	_name = 'fees.detail'
	_description = 'Fees Detail'
	_inherit = [
				'mail.thread',
				'mail.activity.mixin',
			
			   ]

	# Different fees for students
	fees_id = fields.Many2one('fees.fees', 'Fees ID')
	standard = fields.Many2one(
		'student.standard', 'Standard', related='fees_id.standard', store=True)
	division = fields.Many2one(
		'standard.division', 'Division', related='fees_id.division', store=True)
	year = fields.Many2one('year.year', 'Year',
						   related="fees_id.year", store=True)
	month = fields.Selection([
		('01', 'January'),
		('02', 'Fabruary'),
		('03', 'March'),
		('04', 'April'),
		('05', 'May'),
		('06', 'June'),
		('07', 'July'),
		('08', 'August'),
		('09', 'September'),
		('10', 'October'),
		('11', 'November'),
		('12', 'December'),
	], string='Month', related='fees_id.month', store=True)
	fee_type = fields.Many2one('fees.type', 'Fees Type')
	amount = fields.Float('Amount')
	pre_school_fee = fields.Boolean(
		'Pre School Fee', related='fees_id.pre_school_fee', store=True)
	student = fields.Many2one('res.partner', string='Student', related='fees_id.student', domain=[
							  ('is_student', '=', True)])
	state = fields.Selection(
		related='fees_id.state', string='Status', copy=False,store=True)
	name = fields.Char('Reference', related='fees_id.name', store=True)
	paid_on = fields.Datetime('Paid On', related='fees_id.paid_on', store=True)
	user_id = fields.Many2one(
		'res.users', related="fees_id.user_id", store=True, string='User Id')
	product_id = fields.Many2one('product.product', string='Product')
	product_desc = fields.Text(string="Description")


	@api.onchange('product_id')
	def onchange_product_description(self):
		if self.product_id:
			self.product_desc = self.product_id.name
			self.amount = self.product_id.lst_price

# fee type
class FeesType(models.Model):
	_name = 'fees.type'
	_description = 'Fees Type'
	_inherit = [
				'mail.thread',
				'mail.activity.mixin',
			
			   ]

	name = fields.Char('Fee Type')
	fees_amount = fields.Float("Amount")
	fees_id = fields.Many2one('student.standard')

	


class StudentStandard(models.Model):
	_inherit = 'student.standard'
	_description = 'Student Standard'

	fee = fields.Float("Fees",compute="_compute_total_fee", store=True)

	total_fee_type = fields.Float('Total Fee')
	fees_ids = fields.Many2many('fees.type', string="Fees Types") 
	total_fees = fields.Float("Total Fees") 
	fees_type = fields.Many2many('fees.type', 'fees_id', string='Fees Types')

	 
	@api.depends('fees_type')
	def _compute_total_fee(self):
		for record in self:
			record.fee = sum(fee.fees_amount for fee in record.fees_type)