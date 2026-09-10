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
from odoo import models, fields, api, _
from datetime import datetime, timedelta

class ReturnBookWizard(models.TransientModel):

	_name = "return.book.wizard"
	_description = "Return Books Wizard"
	

	book_id = fields.Many2one("issue.books.lines", string="Book Name")
	author = fields.Many2one(related='book_id.author', string="Author")
	genres = fields.Selection(related='book_id.genres', string="Genres")
	lang_id = fields.Many2many(related='book_id.lang_id', string='Language')
	book_line_ids = fields.Many2many(
		'issue.books.lines',
		string='Books',
		domain=[('is_book_returned', '=', False)],
		help="Select the books to be returned"
	)
	issue_books = fields.Many2one("issue.books", string="Issue Books")
	state = fields.Selection([
		('issued', 'Issued'),
		('partially_returned','Partially Returned'),
		('returned', 'Returned'),
		('lost', 'Lost'),
		('cancel', 'Cancel')], default="issued", string="Issue Status", readonly=True)




	@api.model
	def default_get(self, fields_list):
		res = super(ReturnBookWizard, self).default_get(fields_list)
		issue_books_id = self._context.get('default_issue_books')
		if issue_books_id:
			issue_lines = self.env['issue.books.lines'].search([('issue_books', '=', issue_books_id),('is_book_returned', '=', False)])
			res.update({
				'book_line_ids': [(6, 0, issue_lines.ids)]
			})
		return res
			
	def action_change_state(self):
		self.ensure_one()
		
		issue_books = self.env['issue.books'].browse(self._context.get('default_issue_books'))
		if issue_books:
			issue_books_lines = self.env['issue.books.lines'].search([('is_book_returned', '=',True)])
			for line in issue_books_lines:
				line.is_reissued = False
				line.date_return = fields.Datetime.now()

		selected_lines = self.book_line_ids

		all_returned = all(line.is_book_returned for line in selected_lines)
	
		if all_returned:
			issue_books.state = 'returned'
		else:
			issue_books.state = 'partially_returned'