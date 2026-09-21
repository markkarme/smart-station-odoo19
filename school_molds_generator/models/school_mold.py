# -*- coding: utf-8 -*-
import base64
import io

import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .default_columns import DEFAULT_COLUMNS, EMPTY_ROW_COUNT, IDENTITY_COL_TYPES, SUMMARY_SCORE_KEYS


class SchoolMold(models.Model):
    _name = 'school.mold'
    _description = 'School Mold'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(required=True, tracking=True, default=lambda self: _('New Mold'))
    year_id = fields.Many2one('year.year', string='Academic Year', tracking=True)
    standard_id = fields.Many2one('student.standard', string='Standard', tracking=True)
    division_id = fields.Many2one('standard.division', string='Division', tracking=True)
    term = fields.Selection([
        ('first', 'First Term'),
        ('second', 'Second Term'),
        ('third', 'Third Term'),
    ], string='Term', default='first')
    term_types = fields.Selection([
        ('industrial_electricity', 'كهرباء صناعية'),
        ('computer', 'حاسب الي'),
        ('industrial_electronics', 'الكترونيات صناعية'),
        ('office_equipment', 'اجهزه مكتبية'),
    ], string='First Term Types', default='industrial_electricity')
    date = fields.Date(default=fields.Date.context_today)
    note = fields.Char()
    column_ids = fields.One2many('school.mold.column', 'mold_id', string='Columns', copy=True)
    line_ids = fields.One2many('school.mold.line', 'mold_id', string='Rows', copy=True)
    line_count = fields.Integer(compute='_compute_line_count')
    column_payload = fields.Json(compute='_compute_column_payload')
    xlsx_file = fields.Binary(attachment=True)
    xlsx_filename = fields.Char()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], default='draft', tracking=True)

    @api.depends('line_ids')
    def _compute_line_count(self):
        for mold in self:
            mold.line_count = len(mold.line_ids)

    @api.depends(
        'column_ids',
        'column_ids.sequence',
        'column_ids.key',
        'column_ids.name',
        'column_ids.group_name',
        'column_ids.col_type',
        'column_ids.color',
        'column_ids.max_value',
    )
    def _compute_column_payload(self):
        for mold in self:
            mold.column_payload = [
                {
                    'key': column.key,
                    'name': column.name,
                    'group_name': column.group_name or '',
                    'col_type': column.col_type,
                    'color': column.color or '#FFFFFF',
                    'max_value': column.max_value or 0,
                    'sequence': column.sequence,
                }
                for column in mold.column_ids.sorted(lambda col: (col.sequence, col.id))
            ]

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        if 'column_ids' in fields_list and not vals.get('column_ids'):
            vals['column_ids'] = [
                (0, 0, {
                    'sequence': sequence,
                    'key': column['key'],
                    'name': column['name'],
                    'group_name': column['group_name'],
                    'col_type': column['col_type'],
                    'color': column['color'],
                    'max_value': column['max_value'],
                })
                for sequence, column in enumerate(DEFAULT_COLUMNS, start=1)
            ]
        if 'line_ids' in fields_list and not vals.get('line_ids'):
            vals['line_ids'] = [
                (0, 0, {
                    'sequence': index,
                    'student_name': '',
                    'values_json': {},
                })
                for index in range(1, EMPTY_ROW_COUNT + 1)
            ]
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        molds = super().create(vals_list)
        for mold in molds:
            if not mold.column_ids:
                mold._load_default_columns()
            if not mold.line_ids:
                mold._add_empty_rows(EMPTY_ROW_COUNT)
        return molds

    def _load_default_columns(self):
        self.ensure_one()
        commands = []
        for sequence, col in enumerate(DEFAULT_COLUMNS, start=1):
            commands.append((0, 0, {
                'sequence': sequence,
                'key': col['key'],
                'name': col['name'],
                'group_name': col['group_name'],
                'col_type': col['col_type'],
                'color': col['color'],
                'max_value': col['max_value'],
            }))
        self.column_ids = commands

    def _add_empty_rows(self, count):
        self.ensure_one()
        start = max(self.line_ids.mapped('sequence') or [0]) + 1
        self.line_ids = [
            (0, 0, {
                'sequence': start + index,
                'student_name': '',
                'values_json': {},
            })
            for index in range(count)
        ]

    def action_add_row(self):
        self._add_empty_rows(1)
        return True

    def action_add_empty_rows(self):
        self._add_empty_rows(10)
        return True

    def action_reset_columns(self):
        self._apply_first_term_layout()
        return {
            'type': 'ir.actions.act_window',
            'name': _('School Mold'),
            'res_model': 'school.mold',
            'res_id': self[:1].id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _apply_first_term_layout(self):
        for mold in self:
            mold.column_ids.unlink()
            mold._load_default_columns()
            if not mold.line_ids:
                mold._add_empty_rows(EMPTY_ROW_COUNT)

    def action_load_students(self):
        self.ensure_one()
        if not self.standard_id:
            raise UserError(_('Select a standard first.'))
        domain = [
            ('is_student', '=', True),
            ('standard', '=', self.standard_id.id),
        ]
        if self.division_id:
            domain.append(('div', '=', self.division_id.id))
        students = self.env['res.partner'].search(domain, order='roll_no, name')
        if not students:
            raise UserError(_('No students found for this standard.'))
        empty_lines = self.line_ids.filtered(lambda line: not line.student_id and not line.student_name)
        commands = []
        for index, student in enumerate(students):
            values = {
                'sequence': index + 1,
                'student_id': student.id,
                'student_name': student.name,
                'values_json': {
                    'seat_number': student.roll_no or '',
                    'class': student.div.name if student.div else (self.division_id.name or ''),
                },
            }
            if index < len(empty_lines):
                commands.append((1, empty_lines[index].id, values))
            else:
                commands.append((0, 0, values))
        leftover = empty_lines[len(students):]
        commands.extend((2, line.id) for line in leftover)
        self.line_ids = commands
        return True

    def action_recompute_totals(self):
        for mold in self:
            mold.line_ids._recompute_totals(mold.column_ids)
        return True

    def action_mark_done(self):
        self.write({'state': 'done'})
        return True

    def action_reset_draft(self):
        self.write({'state': 'draft'})
        return True

    def action_download_xlsx(self):
        self.ensure_one()
        content, filename = self._generate_xlsx()
        self.write({
            'xlsx_file': base64.b64encode(content),
            'xlsx_filename': filename,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=school.mold&id=%s&field=xlsx_file&filename=%s&download=true' % (
                self.id, filename,
            ),
            'target': 'self',
        }

    def _generate_xlsx(self):
        self.ensure_one()
        columns = self.column_ids.sorted('sequence')
        if not columns:
            raise UserError(_('Add columns before downloading the mold.'))
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(self.name[:31] or _('Mold'))
        sheet.right_to_left()
        sheet.freeze_panes(2, 2)
        sheet.set_row(0, 36)
        sheet.set_row(1, 18)

        formats = {}
        for column in columns:
            color = column.color or '#FFFFFF'
            formats[column.key] = {
                'header': workbook.add_format({
                    'bold': True,
                    'align': 'center',
                    'valign': 'vcenter',
                    'text_wrap': True,
                    'border': 1,
                    'bg_color': color,
                    'font_name': 'Arial',
                    'font_size': 10,
                }),
                'max': workbook.add_format({
                    'align': 'center',
                    'valign': 'vcenter',
                    'border': 1,
                    'bg_color': color,
                    'font_name': 'Arial',
                    'font_size': 10,
                }),
                'cell': workbook.add_format({
                    'align': 'center',
                    'valign': 'vcenter',
                    'border': 1,
                    'bg_color': color,
                    'font_name': 'Arial',
                    'font_size': 10,
                }),
            }

        for col_index, column in enumerate(columns):
            width = 18 if column.col_type == 'name' else (10 if column.col_type in IDENTITY_COL_TYPES else 12)
            sheet.set_column(col_index, col_index, width)
            sheet.write(0, col_index, column.name, formats[column.key]['header'])
            max_value = column.max_value or ''
            if column.col_type in IDENTITY_COL_TYPES:
                max_value = ''
            sheet.write(1, col_index, max_value, formats[column.key]['max'])

        for row_index, line in enumerate(self.line_ids.sorted('sequence'), start=2):
            values = line.values_json or {}
            for col_index, column in enumerate(columns):
                value = line._cell_value(column, values)
                sheet.write(row_index, col_index, value if value != '' else '', formats[column.key]['cell'])

        workbook.close()
        filename = '%s.xlsx' % (self.name or _('school_mold'))
        return output.getvalue(), filename


class SchoolMoldColumn(models.Model):
    _name = 'school.mold.column'
    _description = 'School Mold Column'
    _order = 'sequence, id'

    mold_id = fields.Many2one('school.mold', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    key = fields.Char(required=True)
    name = fields.Char(required=True)
    group_name = fields.Char()
    col_type = fields.Selection([
        ('serial', 'Serial'),
        ('seat_number', 'Seat Number'),
        ('pin_number', 'PIN Number'),
        ('name', 'Name'),
        ('class', 'Class'),
        ('score', 'Score'),
        ('subtotal', 'Subject Total'),
        ('total', 'Total'),
        ('grand_total', 'Grand Total'),
    ], default='score', required=True)
    color = fields.Char(default='#FFFFFF')
    max_value = fields.Float()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('key'):
                vals['key'] = 'col_%s' % fields.Datetime.now().strftime('%H%M%S%f')
        return super().create(vals_list)


class SchoolMoldLine(models.Model):
    _name = 'school.mold.line'
    _description = 'School Mold Row'
    _order = 'sequence, id'

    mold_id = fields.Many2one('school.mold', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    student_id = fields.Many2one(
        'res.partner',
        domain=[('is_student', '=', True)],
        string='Student',
    )
    student_name = fields.Char()
    values_json = fields.Json(default=dict)

    @api.onchange('student_id')
    def _onchange_student_id(self):
        if self.student_id:
            self.student_name = self.student_id.name

    def _cell_value(self, column, values=None):
        self.ensure_one()
        values = values if values is not None else (self.values_json or {})
        if column.col_type == 'serial':
            return self.sequence or 0
        if column.col_type == 'name':
            return self.student_name or ''
        if column.col_type in ('subtotal', 'total', 'grand_total'):
            return self._computed_value(column, values)
        raw = values.get(column.key, '')
        return raw if raw not in (None, False) else ''

    def _numeric_sum(self, values, keys):
        total = 0.0
        has_value = False
        for key in keys:
            raw = values.get(key)
            if raw in (None, False, ''):
                continue
            try:
                total += float(raw)
                has_value = True
            except (TypeError, ValueError):
                continue
        return total, has_value

    def _format_number(self, total):
        return int(total) if total == int(total) else total

    def _computed_value(self, column, values):
        columns = self.mold_id.column_ids
        if column.col_type == 'subtotal':
            keys = columns.filtered(
                lambda col: col.col_type == 'score' and col.group_name == column.group_name
            ).mapped('key')
            total, has_value = self._numeric_sum(values, keys)
            return self._format_number(total) if has_value else ''
        if column.col_type == 'total':
            keys = columns.filtered(
                lambda col: col.col_type == 'score' and not col.group_name
            ).mapped('key') or list(SUMMARY_SCORE_KEYS)
            total, has_value = self._numeric_sum(values, keys)
            return self._format_number(total) if has_value else ''
        if column.col_type == 'grand_total':
            subtotal = 0.0
            has_subtotal = False
            for subtotal_column in columns.filtered(lambda col: col.col_type == 'subtotal'):
                value = self._computed_value(subtotal_column, values)
                if value in (None, False, ''):
                    continue
                subtotal += float(value)
                has_subtotal = True
            total_column = columns.filtered(lambda col: col.col_type == 'total')[:1]
            summary = 0.0
            has_summary = False
            if total_column:
                value = self._computed_value(total_column, values)
                if value not in (None, False, ''):
                    summary = float(value)
                    has_summary = True
            if not has_subtotal and not has_summary:
                return 0
            return self._format_number(subtotal + summary)
        return ''

    def _recompute_totals(self, columns=None):
        compute_order = {'subtotal': 1, 'total': 2, 'grand_total': 3}
        for line in self:
            cols = columns or line.mold_id.column_ids
            values = dict(line.values_json or {})
            for column in cols.sorted(lambda col: compute_order.get(col.col_type, 0)):
                if column.col_type in ('subtotal', 'total', 'grand_total'):
                    values[column.key] = line._computed_value(column, values)
            line.values_json = values
