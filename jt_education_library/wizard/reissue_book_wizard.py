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
class ReissueBookWizard(models.TransientModel):

	_name = "reissue.book.wizard"
	_description = "Return Books Wizard"

	book_line_ids = fields.Many2many(
		'issue.books.lines',
		string='Books',
		domain=[('is_book_returned', '=', True)],
		help="Select the books to be reissues"
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
		res = super(ReissueBookWizard, self).default_get(fields_list)
		issue_books_id = self._context.get('default_issue_books')
		if issue_books_id:
			issue_lines = self.env['issue.books.lines'].search([('issue_books', '=', issue_books_id),('is_book_returned', '=', True)])
			res.update({
				'book_line_ids': [(6, 0, issue_lines.ids)]
			})
		return res
			
	def action_state_partially_returned(self):
		self.ensure_one()
		
		issue_books = self.env['issue.books'].browse(self._context.get('default_issue_books'))
		if issue_books:
			issue_books_lines = self.env['issue.books.lines'].search([('is_reissued', '=', True)])
			today = datetime.now().date()
			return_date = today + timedelta(days=7)
			# reissued_lines = issue_books_lines.filtered(lambda l: l.is_reissued)

			for line in issue_books_lines:
				line.is_book_returned = False
				line.date_return = return_date
				
		
		selected_lines = self.book_line_ids
		all_issued = all(line.is_reissued for line in selected_lines)
	
		if all_issued:
			issue_books.state = 'issued'
		else:
			issue_books.state = 'partially_returned'
