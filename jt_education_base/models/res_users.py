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
from odoo import api, models, _
from odoo.exceptions import ValidationError


class Users(models.Model):
    _inherit = "res.users"

    @api.constrains('group_ids')
    def _check_school_college_groups(self):
        school = self.env.ref('jt_education_base.group_school', raise_if_not_found=False)
        college = self.env.ref('jt_education_base.group_college', raise_if_not_found=False)
        if not school or not college:
            return
        for user in self:
            groups = user.all_group_ids
            if school in groups and college in groups:
                raise ValidationError(_("A user cannot have both School and College."))
