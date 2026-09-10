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

class AuthorsDetails(models.Model):
	_inherit = 'res.partner'
	_description = "Authors"

	company_type = fields.Selection(selection_add=[('author', 'Author')])
	author_type = fields.Selection([('person', 'Individual'), ('company', 'Company'),('author','Author')],default="author",string="Company Type ")
	is_author = fields.Boolean(string='Is Author')
	authors_code = fields.Char(string="Author ID" ,copy=False)


	@api.onchange('author_type')
	def author_chng_type(self):
		self.company_type = self.author_type

	@api.onchange('company_type')
	def onchange_company_type(self):
		self.is_author = (self.company_type == 'author')
		
	# @api.model_create_multi
	# def create(self, vals):
	# 	for val in vals:
	# 		if 'author_type' not in val or not val.get('author_type'):
	# 			val['author_type'] = 'author'
			
	# 		if val.get('author_type') == 'author':
	# 			val['company_type'] = 'author'
	# 			val['is_author'] = True

	# 	res = super(AuthorsDetails, self).create(vals)
		
	# 	return res


class Authors(models.Model):
	_name = "authors.authors"
	_description = "Authors Details"
	_inherit = [
				'mail.thread',
				'mail.activity.mixin',
			
			   ]


	# image_1920 = fields.Binary(
	#     related='partner_id.image_1920', store=True, attachement=True)
	authors_code = fields.Char(string="Author ID" ,copy=False)
	partner_id = fields.Many2one('res.partner', string="Author Name")
	name = fields.Char(related='partner_id.name', string="Name", store=True)
	street = fields.Char(related="partner_id.street", readonly=False)
	street2 = fields.Char(related="partner_id.street2", readonly=False)
	city = fields.Char(related="partner_id.city", readonly=False)
	state_id = fields.Many2one(related="partner_id.state_id", readonly=False)
	country_id = fields.Many2one(related="partner_id.country_id", readonly=False)
	phone = fields.Char(related="partner_id.phone", readonly=False)
	mobile = fields.Char(related="partner_id.mobile", readonly=False)
	email = fields.Char(related="partner_id.email", readonly=False)
	website = fields.Char(related="partner_id.website", readonly=False)
	is_author = fields.Boolean("Is a Author")
	publisher = fields.Char('Publisher')

	@api.model_create_multi
	def create(self, vals):
		res = super(Authors, self).create(vals)
		for auth_rec in res:
			auth_rec.authors_code = self.env['ir.sequence'].next_by_code('authors.seq')
		return res
