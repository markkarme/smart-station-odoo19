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
from odoo.tools.translate import CodeTranslations



class Books(models.Model):

	_name = "books.books"
	_description = "Books Details"
	_inherit = [
				'mail.thread',
				'mail.activity.mixin',
			   ]
	_name_uniq = models.Constraint(
		'UNIQUE(name)',
		'Book Name Must Be Unique !',
	)

	@api.depends('name', 'author.name')
	def _compute_display_name(self):
		for rec in self:
			rec.display_name = '%s - %s' % (rec.name or '', rec.author.name or '')

	@api.model_create_multi
	def create(self, vals):
		res = super(Books, self).create(vals)
		for book_rec in res:
			book_rec.books_code = self.env['ir.sequence'].next_by_code('books.seq')
		return res

	# Details of Books
	books_image = fields.Binary(
		"Book Cover Picture", attachment=True, store=True)
	name = fields.Char("Name")
	no_of_books = fields.Integer('Total No. Of Books')
	lang_id = fields.Many2many('book.language', string='Language')
	edition = fields.Float(string="Edition")
	book_ids = fields.Many2many("book.xls.report", string="Book Ids")
	genres = fields.Selection([
		('romance', 'Romance'),
		('horror', 'Horror'),
		('mystery', 'Mystery'),
		('historic', 'Historic'),
		('biography', 'Biography'),
		('science', 'Science'),
		('cooking', 'Cooking'),
		('art', 'Art'),
		('motivational', 'Motivational'),
		('child', 'Child'),
		('comic', 'Comic')], default="motivational", string='Genres')
	author = fields.Many2one("res.partner", string="Author",domain=[(('is_author','=',True))])
	# , default=lambda self: self.env['ir.sequence'].next_by_code('books.seq')
	books_code = fields.Char(string="Book ID" ,copy=False)
	no_of_books_issued = fields.Integer('No. Of Books Issued', compute='_compute_no_of_books_issued')
	no_of_books_lost = fields.Integer('No. Of Books Lost', compute='_compute_no_of_books_lost')
	no_of_books_available = fields.Integer('No. Of Books Available', compute='_compute_no_of_books_available')

	def _compute_no_of_books_issued(self):
		for rec in self:
			issuebook_data = self.env['issue.books'].search([
				('issuebookslines_ids.name.id', '=', rec.id),
				'|',
				('state', '=', 'issued'),
				'&',
				('state', '!=', 'issued'),
				('issuebookslines_ids.is_reissued', '=', True)
			])
			rec.no_of_books_issued = len(issuebook_data)


	def _compute_no_of_books_lost(self):
		for rec in self:
			lostbook_data = self.env['issue.books'].search([('issuebookslines_ids.name.id','=',rec.id),('issuebookslines_ids.is_book_lost','=',True)])
			rec.no_of_books_lost = len(lostbook_data)

	def _compute_no_of_books_available(self):
		for rec in self:
			rec.no_of_books_available = rec.no_of_books - (rec.no_of_books_issued + rec.no_of_books_lost)
			print("no_of_books_available-------------------------",rec.no_of_books_available)
			
		# 	returned_books_count = self.env['issue.books'].search_count([
		# 	('issuebookslines_ids.name.id', '=', rec.id),
		# 	('issuebookslines_ids.is_book_returned', '=', True)
		# ])
		# 	rec.no_of_books_available += returned_books_count
		# 	print("no_of_books_available-------------------------",rec.no_of_books_available)
			
			if rec.no_of_books_available < 0:
				rec.no_of_books_available = 0
			

	

class BookLanguage(models.Model):

	_name = 'book.language'
	_description = 'Book Language'
	_rec_name='lang'
	_inherit = [
				'mail.thread',
				'mail.activity.mixin',
			
			   ]

	lang = fields.Char(string='Language')
	
	# lang = fields.Selection(selection='_get_languages', string='Language', validate=False)

	# def _get_languages(self):
	# 	return self.env['res.lang'].get_installed()

	

	