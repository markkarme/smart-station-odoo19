# -*- coding: utf-8 -*-
import base64
import io
import os

import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.modules.module import get_module_path

from .default_columns import (
    EMPTY_ROW_COUNT,
    FORM_27_ROW_COUNT,
    HEALTH_INSURANCE_ROW_COUNT,
    IDENTITY_COL_TYPES,
    SUMMARY_SCORE_KEYS,
    get_template_columns,
)

REPORT_KINDS = ('health_insurance', 'form_27')
ROW_COUNT_BY_KIND = {
    'health_insurance': HEALTH_INSURANCE_ROW_COUNT,
    'form_27': FORM_27_ROW_COUNT,
}


class SchoolMold(models.Model):
    _name = 'school.mold'
    _description = 'School Mold'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(required=True, tracking=True, default=lambda self: _('New Mold'))
    mold_kind = fields.Selection([
        ('grades', 'School Mold'),
        ('health_insurance', 'Health Insurance report'),
        ('form_27', 'Form 27 report'),
    ], string='Template', default='grades', required=True, tracking=True)
    year_id = fields.Many2one('year.year', string='Academic Year', tracking=True)
    standard_id = fields.Many2one('student.standard', string='Standard', tracking=True)
    division_id = fields.Many2one('standard.division', string='Division', tracking=True)
    craft = fields.Char(string='الحرفة', help='Used on Form 27 header')
    region = fields.Char(string='المنطقة', default='شمال الصعيد')
    center = fields.Char(string='المركز', default='محطه سمارت المنيا الجديده')
    batch_label = fields.Char(
        string='الدفعة',
        default='2025 / 2026',
        help='Batch years shown on Form 27 subtitle',
    )
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
    ], string='Specialization', default='industrial_electricity')
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
        'column_ids.include_in_grand_total',
    )
    def _compute_column_payload(self):
        for mold in self:
            mold.column_payload = [
                {
                    'id': column.id,
                    'key': column.key,
                    'name': column.name,
                    'group_name': column.group_name or '',
                    'col_type': column.col_type,
                    'color': column.color or '#FFFFFF',
                    'max_value': column.max_value or 0,
                    'sequence': column.sequence,
                    'include_in_grand_total': column.include_in_grand_total,
                }
                for column in mold.column_ids.sorted(lambda col: (col.sequence, col.id))
            ]

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        mold_kind = (
            vals.get('mold_kind')
            or self.env.context.get('default_mold_kind')
            or 'grades'
        )
        term = (
            vals.get('term')
            or self.env.context.get('default_term')
            or 'first'
        )
        term_types = (
            vals.get('term_types')
            or self.env.context.get('default_term_types')
            or 'industrial_electricity'
        )
        layout = get_template_columns(term, term_types, mold_kind)
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
                    'include_in_grand_total': column.get('include_in_grand_total', True),
                })
                for sequence, column in enumerate(layout, start=1)
            ]
        row_count = ROW_COUNT_BY_KIND.get(mold_kind, EMPTY_ROW_COUNT)
        if 'line_ids' in fields_list and not vals.get('line_ids'):
            vals['line_ids'] = [
                (0, 0, {
                    'sequence': index,
                    'student_name': '',
                    'values_json': {},
                })
                for index in range(1, row_count + 1)
            ]
        if mold_kind == 'health_insurance' and not vals.get('name'):
            vals['name'] = _('Health Insurance report')
        if mold_kind == 'form_27' and not vals.get('name'):
            vals['name'] = _('Form 27 report')
        return vals

    def _target_row_count(self):
        self.ensure_one()
        return ROW_COUNT_BY_KIND.get(self.mold_kind, EMPTY_ROW_COUNT)

    def _is_report_kind(self):
        self.ensure_one()
        return self.mold_kind in REPORT_KINDS

    @api.model_create_multi
    def create(self, vals_list):
        molds = super().create(vals_list)
        for mold in molds:
            # default_get may have injected columns before term/type were known
            mold._ensure_layout_columns()
            target_rows = mold._target_row_count()
            if not mold.line_ids:
                mold._add_empty_rows(target_rows)
            elif mold._is_report_kind() and len(mold.line_ids) < target_rows:
                mold._add_empty_rows(target_rows - len(mold.line_ids))
        return molds

    def _ensure_layout_columns(self):
        """Load or replace columns so they match term + specialization."""
        self.ensure_one()
        expected = [col['key'] for col in self._get_layout_columns()]
        actual = self.column_ids.sorted(lambda c: (c.sequence, c.id)).mapped('key')
        if list(actual) == expected:
            return
        self.column_ids.unlink()
        self._load_default_columns()

    def _get_layout_columns(self):
        self.ensure_one()
        return get_template_columns(
            self.term or 'first',
            self.term_types,
            self.mold_kind or 'grades',
        )

    def _load_default_columns(self):
        self.ensure_one()
        commands = []
        for sequence, col in enumerate(self._get_layout_columns(), start=1):
            commands.append((0, 0, {
                'sequence': sequence,
                'key': col['key'],
                'name': col['name'],
                'group_name': col['group_name'],
                'col_type': col['col_type'],
                'color': col['color'],
                'max_value': col['max_value'],
                'include_in_grand_total': col.get('include_in_grand_total', True),
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
        self._apply_layout()
        title = _('School Mold')
        if self[:1].mold_kind == 'health_insurance':
            title = _('Health Insurance report')
        elif self[:1].mold_kind == 'form_27':
            title = _('Form 27 report')
        return {
            'type': 'ir.actions.act_window',
            'name': title,
            'res_model': 'school.mold',
            'res_id': self[:1].id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _apply_layout(self):
        """Reload columns for the current term + specialization."""
        for mold in self:
            mold.column_ids.unlink()
            mold._load_default_columns()
            if not mold.line_ids:
                mold._add_empty_rows(mold._target_row_count())

    def _apply_first_term_layout(self):
        # Kept for older migrations/callers.
        return self._apply_layout()

    @api.onchange('term', 'term_types', 'mold_kind')
    def _onchange_term_or_type(self):
        """Swap the sheet layout when term/specialization changes (new records)."""
        if self._origin.id:
            return {
                'warning': {
                    'title': _('Layout'),
                    'message': _(
                        'Template changed. Click "Reset Columns" '
                        'to load the matching sheet template.'
                    ),
                },
            }
        layout = get_template_columns(
            self.term or 'first',
            self.term_types,
            self.mold_kind or 'grades',
        )
        self.column_ids = [(5, 0, 0)] + [
            (0, 0, {
                'sequence': sequence,
                'key': column['key'],
                'name': column['name'],
                'group_name': column['group_name'],
                'col_type': column['col_type'],
                'color': column['color'],
                'max_value': column['max_value'],
                'include_in_grand_total': column.get('include_in_grand_total', True),
            })
            for sequence, column in enumerate(layout, start=1)
        ]

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
            if self.mold_kind == 'health_insurance':
                values_json = {
                    'national_id': student.national_iD_number or '',
                    'mobile': student.mobile or '',
                    'insurance_number': '',
                }
            elif self.mold_kind == 'form_27':
                values_json = self._form_27_values_from_student(student)
            else:
                values_json = {
                    'seat_number': student.roll_no or '',
                    'class': student.div.name if student.div else (self.division_id.name or ''),
                }
            values = {
                'sequence': index + 1,
                'student_id': student.id,
                'student_name': student.name,
                'values_json': values_json,
            }
            if index < len(empty_lines):
                commands.append((1, empty_lines[index].id, values))
            else:
                commands.append((0, 0, values))
        leftover = empty_lines[len(students):]
        commands.extend((2, line.id) for line in leftover)
        self.line_ids = commands
        return True

    def _form_27_values_from_student(self, student):
        gender_map = {'male': 'ذكر', 'female': 'أنثى'}
        birth = student.birthdate
        residence = (
            student.street
            or student.birthPlace
            or (student.village.name if student.village else '')
            or ''
        )
        governorate = (
            (student.state1.name if student.state1 else '')
            or (student.province.name if student.province else '')
            or ''
        )
        return {
            'registration_number': (
                student.stud_id
                or student.file_registration_number
                or student.gr_no
                or student.roll_no
                or ''
            ),
            'national_id': student.national_iD_number or '',
            'gender': gender_map.get(student.gender, student.gender or ''),
            'nationality': student.nationality or '',
            'religion': student.religion or '',
            'birth_day': birth.day if birth else '',
            'birth_month': birth.month if birth else '',
            'birth_year': birth.year if birth else '',
            'residence': residence,
            'governorate': governorate,
            'phone': student.mobile or '',
            'notes': '',
        }

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

    def _asset_path(self, filename):
        module_path = get_module_path('school_molds_generator')
        return os.path.join(module_path, 'static', 'assets', filename)

    def _generate_xlsx(self):
        self.ensure_one()
        if self.mold_kind == 'health_insurance':
            return self._generate_health_insurance_xlsx()
        if self.mold_kind == 'form_27':
            return self._generate_form_27_xlsx()
        return self._generate_grades_xlsx()

    def _generate_grades_xlsx(self):
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

    def _generate_health_insurance_xlsx(self):
        """Excel matching the Health Insurance report screenshot (logos + yellow header)."""
        self.ensure_one()
        columns = self.column_ids.sorted('sequence')
        if not columns:
            raise UserError(_('Add columns before downloading the mold.'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet((self.name or _('Health Insurance'))[:31])
        sheet.right_to_left()

        header_fmt = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#FFFF00',
            'font_name': 'Arial',
            'font_size': 12,
        })
        cell_fmt = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_name': 'Arial',
            'font_size': 11,
        })
        serial_fmt = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_name': 'Arial',
            'font_size': 11,
        })

        # Column widths (RTL: col 0 = م on the right)
        widths = {
            'serial': 6,
            'name': 28,
            'insurance_number': 18,
            'national_id': 20,
            'mobile': 16,
        }
        for col_index, column in enumerate(columns):
            sheet.set_column(col_index, col_index, widths.get(column.key, 16))

        # Logo header rows (rows 0–3), table starts at row 4
        logo_row_height = 22
        for row in range(4):
            sheet.set_row(row, logo_row_height)
        sheet.set_row(4, 24)

        last_col = len(columns) - 1
        # RTL visual: right=Ministry, center=PVTD, left=SMART
        logo_specs = [
            ('ministry_of_industry.png', 0, {'x_scale': 0.08, 'y_scale': 0.08, 'x_offset': 8, 'y_offset': 4}),
            ('pvtd_image.png', max(last_col // 2, 1), {'x_scale': 0.55, 'y_scale': 0.55, 'x_offset': 10, 'y_offset': 4}),
            ('smart-logo.png', last_col, {'x_scale': 0.7, 'y_scale': 0.7, 'x_offset': 4, 'y_offset': 8}),
        ]
        for filename, col, options in logo_specs:
            path = self._asset_path(filename)
            if os.path.isfile(path):
                sheet.insert_image(0, col, path, options)

        header_row = 4
        data_start = 5
        for col_index, column in enumerate(columns):
            sheet.write(header_row, col_index, column.name, header_fmt)

        sheet.freeze_panes(data_start, 1)

        for row_index, line in enumerate(self.line_ids.sorted('sequence'), start=data_start):
            values = line.values_json or {}
            for col_index, column in enumerate(columns):
                value = line._cell_value(column, values)
                fmt = serial_fmt if column.col_type == 'serial' else cell_fmt
                sheet.write(row_index, col_index, value if value != '' else '', fmt)

        workbook.close()
        filename = '%s.xlsx' % (self.name or _('health_insurance'))
        return output.getvalue(), filename

    def _generate_form_27_xlsx(self):
        """Excel matching Form 27 (نموذج 27) screenshot."""
        self.ensure_one()
        columns = self.column_ids.sorted('sequence')
        if not columns:
            raise UserError(_('Add columns before downloading the mold.'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet((self.name or _('Form 27'))[:31])
        sheet.right_to_left()

        org_fmt = workbook.add_format({
            'align': 'right',
            'valign': 'vcenter',
            'font_name': 'Arial',
            'font_size': 11,
        })
        title_fmt = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Arial',
            'font_size': 16,
        })
        subtitle_fmt = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Arial',
            'font_size': 12,
        })
        craft_fmt = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Arial',
            'font_size': 12,
        })
        header_top_fmt = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#D9D9D9',
            'font_name': 'Arial',
            'font_size': 10,
            'text_wrap': True,
        })
        header_sub_fmt = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#D9D9D9',
            'font_name': 'Arial',
            'font_size': 10,
        })
        cell_fmt = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_name': 'Arial',
            'font_size': 10,
        })

        widths = {
            'serial': 5,
            'name': 28,
            'registration_number': 14,
            'national_id': 18,
            'gender': 8,
            'nationality': 10,
            'religion': 10,
            'birth_day': 6,
            'birth_month': 6,
            'birth_year': 8,
            'residence': 18,
            'governorate': 14,
            'phone': 14,
            'notes': 14,
        }
        for col_index, column in enumerate(columns):
            sheet.set_column(col_index, col_index, widths.get(column.key, 12))

        last_col = len(columns) - 1
        # Institutional block (right side in RTL = low column indices)
        org_lines = [
            'مصلحة الكفاية الإنتاجية و التدريب المهني',
            'الإدارة العامة للإختبارات النمطية',
            'إدارة الامتحانات',
            'المنطقة | %s' % (self.region or 'شمال الصعيد'),
            'المركز | %s' % (self.center or 'محطه سمارت المنيا الجديده'),
        ]
        for row_index, text in enumerate(org_lines):
            sheet.set_row(row_index, 18)
            sheet.merge_range(row_index, 0, row_index, min(3, last_col), text, org_fmt)

        # Center title block
        batch = self.batch_label or (self.year_id.name if self.year_id else '2025 / 2026')
        sheet.merge_range(1, max(4, last_col // 3), 1, last_col, 'نموذج 27', title_fmt)
        sheet.merge_range(
            3, max(4, last_col // 3), 3, last_col,
            'كشف أسماء الطلاب المقيدون بالصف الأول دفعة %s' % batch,
            subtitle_fmt,
        )
        sheet.merge_range(
            5, max(4, last_col // 3), 5, last_col,
            'الحرفه : %s' % (self.craft or ''),
            craft_fmt,
        )

        header_row = 8
        sub_header_row = 9
        data_start = 10
        sheet.set_row(header_row, 22)
        sheet.set_row(sub_header_row, 18)

        birth_keys = {'birth_day', 'birth_month', 'birth_year'}
        birth_indexes = [i for i, col in enumerate(columns) if col.key in birth_keys]
        birth_start = birth_indexes[0] if birth_indexes else None
        birth_end = birth_indexes[-1] if birth_indexes else None

        for col_index, column in enumerate(columns):
            if column.key in birth_keys:
                continue
            sheet.merge_range(
                header_row, col_index, sub_header_row, col_index,
                column.name, header_top_fmt,
            )

        if birth_start is not None:
            sheet.merge_range(
                header_row, birth_start, header_row, birth_end,
                'تاريخ الميلاد', header_top_fmt,
            )
            for col_index, column in enumerate(columns):
                if column.key in birth_keys:
                    sheet.write(sub_header_row, col_index, column.name, header_sub_fmt)

        sheet.freeze_panes(data_start, 2)

        for row_index, line in enumerate(self.line_ids.sorted('sequence'), start=data_start):
            values = line.values_json or {}
            for col_index, column in enumerate(columns):
                value = line._cell_value(column, values)
                sheet.write(row_index, col_index, value if value != '' else '', cell_fmt)

        workbook.close()
        filename = '%s.xlsx' % (self.name or _('form_27'))
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
        ('text', 'Text'),
        ('score', 'Score'),
        ('subtotal', 'Subject Total'),
        ('total', 'Total'),
        ('grand_total', 'Grand Total'),
    ], default='score', required=True)
    color = fields.Char(default='#FFFFFF')
    max_value = fields.Float()
    include_in_grand_total = fields.Boolean(
        string='In Grand Total',
        default=True,
        help="Uncheck for subjects that appear on the sheet but are not counted "
             "in المجموع الكلي (e.g. تربية دينية).",
    )

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
            for subtotal_column in columns.filtered(
                lambda col: col.col_type == 'subtotal' and col.include_in_grand_total
            ):
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
            else:
                # No separate total column — sum ungrouped scores (matches JS / third-term sheets).
                keys = columns.filtered(
                    lambda col: col.col_type == 'score' and not col.group_name
                ).mapped('key')
                summary, has_summary = self._numeric_sum(values, keys)
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
