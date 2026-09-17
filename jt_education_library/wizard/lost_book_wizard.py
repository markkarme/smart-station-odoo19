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

class LostBookWizard(models.TransientModel):

	_name = "lost.book.wizard"
	_description = "Lost Books Wizard"
	
	book_line_ids = fields.Many2many(
		'issue.books.lines',
		string='Books',
		domain=[('is_book_lost', '=', False)],
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
		res = super(LostBookWizard, self).default_get(fields_list)
		issue_books_id = self._context.get('default_issue_books')
		if issue_books_id:
			issue_lines = self.env['issue.books.lines'].search([('issue_books', '=', issue_books_id),('is_book_returned', '=', False)])
			res.update({
				'book_line_ids': [(6, 0, issue_lines.ids)]
			})
		return res
			
	def action_state_lost(self):
		self.ensure_one()
		
		issue_books = self.env['issue.books'].browse(self._context.get('default_issue_books'))
		if issue_books:
			issue_books_lines = self.env['issue.books.lines'].search([('is_book_lost', '=',True)])
			for line in issue_books_lines:
				line.is_reissued = False
				line.is_book_returned = False

		selected_lines = self.book_line_ids

		all_lost = all(line.is_book_lost for line in selected_lines)
	
		if all_lost:
			issue_books.state = 'lost'