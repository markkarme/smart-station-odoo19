# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PenaltyType(models.Model):
    _name = 'penalty.type'
    _description = 'PenaltyType'

    name = fields.Char('Name',required=True)
    currency_id = fields.Many2one('res.currency','currnecy',default=lambda self: self.env.company.currency_id)
    amount = fields.Monetary('Amount of deduction', currency_field='currency_id',required=True)

    _unique_name = models.Constraint('UNIQUE (name)', 'the name of penalty type must be unique')
    _validate_amount = models.Constraint('CHECK (amount > 0)', 'the amount of deduction must be greater than 0')