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

# student information


class StudentInformation(models.Model):
    _inherit = 'res.partner'
    # _description = 'Student Information'

    fee_structure = fields.One2many(
        'fees.structure', 'student', 'Fee Structure')
    fee_ids = fields.One2many('fees.fees', 'student', 'Fee IDs')
    fees_detail = fields.One2many('fees.detail', 'student', domain=[
                                  ('pre_school_fee', '=', False)])  # yearr.name

    # to get total paid/due fees
    paid_fees = fields.Float('Total Fees Paid', compute='_compute_paid_fees')
    due_fees = fields.Float('Total Due Fees', compute='_compute_due_fees')

    # Total Current Year Fees
    total_fees = fields.Float('Total Fees', compute='_compute_total_fees')

    # to get total yearly paid/due fees
    yearly_due_fees = fields.Float(
        'Yearly Total Due Fees', compute='_compute_yearly_due_fees')
    yearly_paid_fees = fields.Float(
        'Yearly Total Paid Fees', compute='_compute_yearly_paid_fees')

    # For fees internal fees type (School fees or Preschool fees)
    fee_type = fields.Selection([
        ('psf', 'Pre School Fee'),
        ('sf', 'School Fee'),
    ], string='Fees Type')

    # to get total Invoice Count
    total_invoice_count = fields.Float('Total Invoices Count', compute='_compute_total_invoices_count')

    # to get total Sale Order Count
    total_sale_order_count = fields.Float('Total Sale Orders Count', compute='_compute_total_sale_order_count')


    # Calculate Total fees of year

    def _compute_total_fees(self):
        for record in self:
            year_fee = self.env['fees.structure'].search([('student', '=', record.id), (
                'standard', '=', record.standard.id), ('year', '=', record.curr_year.id)], limit=1)
            if year_fee:
                record.total_fees = year_fee.amount

    # Function to count yearly due fees for current year(For smart button)

    # @api.depends('curr_year', 'fee_ids.state')
    def _compute_yearly_due_fees(self):
        for record in self:
            due = 0
            if record.curr_year:
                fees = self.env['fees.detail'].search([('student', '=', record.id), (
                    'state', '=', 'draft'), ('year', '=', record.curr_year.id), ('pre_school_fee', '=', False)])
                for fee in fees:
                    due += fee.amount
            record.yearly_due_fees = due

    # Function to count yearly paid fes for current year (For smart button)
    # @api.depends('curr_year', 'fee_ids.state')
    def _compute_yearly_paid_fees(self):
        for record in self:
            paid = 0
            if record.curr_year:
                fees = self.env['fees.detail'].search([('student', '=', record.id), (
                    'state', '=', 'paid'), ('year', '=', record.curr_year.id), ('pre_school_fee', '=', False)])
                for fee in fees:
                    paid += fee.amount
            record.yearly_paid_fees = paid

    # smart button action for yearly paid fees
    def action_view_yearly_paid_fees(self):
        return {
            'name': 'Yearly Paid Fees',
            'type': 'ir.actions.act_window',
            'res_model': 'fees.detail',
            'view_type': 'form',
            'view_mode': 'list,form',
            'domain': [('student', '=', self.id), ('state', '=', 'paid'), ('year', '=', self.curr_year.id), ('pre_school_fee', '=', False)],
        }
    
    def action_count_student_certi(self):
        print("hello")
        return {
                'name': 'Student Rewards',
                'type': 'ir.actions.act_window',
                'res_model': 'student.yearly.result',
                'view_type': 'form',
                'view_mode': 'list,form',
                'domain': [('student_id', '=', self.id)],  # Filters records based on the current student
                'context': {'default_student_id': self.id},  # Optional: sets default student_id in new records
            }

    # smart button action for yearly due fees
    def action_view_yearly_due_fees(self):
        return {
            'name': 'Yearly Due Fees',
            'type': 'ir.actions.act_window',
            'res_model': 'fees.detail',
            'view_type': 'form',
            'view_mode': 'list,form',
            'domain': [('student', '=', self.id), ('state', '=', 'draft'), ('year', '=', self.curr_year.id), ('pre_school_fee', '=', False)],
        }

    # calculate total paid fees

    def _compute_paid_fees(self):
        for record in self:
            fees = self.env['fees.detail'].search(
                [('student', '=', record.id), ('state', '=', 'paid'), ('pre_school_fee', '=', False)])
            tmp = 0
            for fee in fees:
                tmp += fee.amount
            record.paid_fees = tmp

    # smart button action for total paid fees
    def action_view_fees(self):
        return {
            'name': 'Total Paid Fees',
            'type': 'ir.actions.act_window',
            'res_model': 'fees.detail',
            'view_type': 'form',
            'view_mode': 'list,form',
            'domain': [('student', '=', self.id), ('state', '=', 'paid'), ('pre_school_fee', '=', False)],
        }

    # smart button action for Total Invoice Count
    def action_view_invoice(self):
        return {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_type': 'form',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id),('move_type', '=', 'out_invoice'),('state','!=','cancel')],
        }

    # calculate total Invoice Amount
    def _compute_total_invoices_count(self):
        for record in self:
            invoices = self.env['account.move'].search(
                [('partner_id', '=', record.id),('move_type', '=', 'out_invoice'),('state','!=','cancel')])
            tmp = 0
            for invoice in invoices:
                tmp += invoice.amount_total
            record.total_invoice_count = tmp    

    # smart button action for Total Sale Order Count
    def action_view_sale_order(self):
        return {
            'name': 'Sale Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_type': 'form',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id),('state','!=','cancel')],
        }

    # calculate Total Sale Order
    def _compute_total_sale_order_count(self):
        for record in self:
            orders = self.env['sale.order'].search(
                [('partner_id', '=', record.id),('state','!=','cancel')])
            tmp = 0
            for order in orders:
                tmp += order.amount_total
            record.total_sale_order_count = tmp            

    # calculate total due fees

    def _compute_due_fees(self):
        for due in self:
            fees = self.env['fees.fees'].search(
                [('student', '=', due.id), ('payment_state','=','not_paid')])
                # [('student', '=', due.id), ('state', '=', 'draft'), ('pre_school_fee', '=', False)])
            tmp = 0
            for fee in fees:
                tmp += fee.amount
            due.due_fees = tmp

    # smart button action for total due fees
    def action_view_due_fees(self):
        return {
            'name': 'Total Due Fees',
            'type': 'ir.actions.act_window',
            'res_model': 'fees.fees',
            'view_type': 'form',
            'view_mode': 'list,form',
            # 'domain': [('student', '=', self.id), ('state', '=', 'draft'), ('pre_school_fee', '=', False)],
            'domain': [('student', '=', self.id), ('payment_state','=','not_paid')],
        }

    def action_create_student_so(self):
        for line in self:
            if line.fee_structure:
                fees_rec = self.env['fees.fees'].create({
                    'student': line.id,
                })

                for record in line.fee_structure:
                    self.env['fees.detail'].create({
                        'fees_id': fees_rec.id,
                        'product_id': record.product_id.id,
                        'product_desc': record.description,
                        'fee_type': record.fee_type.id,
                        'amount': record.amount,
                    })
                fees_rec.action_paid()



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