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
from odoo import fields,models,api
class BookHistory(models.Model):
	_name = "books.history"
	_description = "Books History"

	book_id = fields.Many2one("books.books", string="Book Name", required=True)
	issue_books_id = fields.Many2one("issue.books", string="Issue Books", required=True)
	author = fields.Many2one(related='book_id.author', string="Author")
	genres = fields.Selection(related='book_id.genres', string="Genres")
	lang_id = fields.Many2many(related='book_id.lang_id', string='Language')
	date_return = fields.Date(string="Date",default=lambda self: fields.Date.today())
	action = fields.Selection([('reissued','Reissued'),('issue','issue'),('returned','Returned'),('lost','Lost')],string="State")
	state = fields.Selection(related='issue_books_id.state', string="State")
