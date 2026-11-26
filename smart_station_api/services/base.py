"""Declarative portal features served to the website.

Each ``Feature`` mirrors one tile of the Odoo portal (/my): it declares which
website.access.right permission opens it, which records the user may see, the
columns/filters of the list, the create form, the record actions and reports.
All reads/writes run as superuser, so every entry point must go through
``Feature.check_record`` / ``Feature.base_domain``.
"""
import base64
from datetime import datetime, time, timedelta

import pytz

from odoo import SUPERUSER_ID, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import date_utils

from ..models.portal_bridge import API_DECISION_KEY, API_EMPLOYEE_KEY


class ApiError(Exception):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.message = message
        self.code = code


class ApiContext:
    """Everything a feature needs to know about the acting website user."""

    def __init__(self, env, website_user, lang=None):
        employee = website_user.sudo().employee_id
        self.lang = lang if lang in ('ar_001', 'en_US') else (website_user.lang or 'en_US')
        companies = employee.company_ids | employee.company_id
        context = dict(
            env.context,
            lang=self.lang,
            tz=employee.tz or 'UTC',
            allowed_company_ids=[employee.company_id.id] + (companies - employee.company_id).ids,
            **{API_EMPLOYEE_KEY: employee.id},
        )
        self.env = env(user=SUPERUSER_ID, su=True, context=context)
        self.website_user = website_user.with_env(self.env)
        self.employee = employee.with_env(self.env)
        self.companies = companies.with_env(self.env).sorted('name')
        self.company_ids = self.companies.ids
        self.perms = self.website_user._permission_flags()
        self.is_ar = self.lang.startswith('ar')

    def t(self, en, ar):
        return ar if self.is_ar else en

    def can(self, *names):
        return any(self.perms.get(name) for name in names)

    def require(self, *names):
        if not self.can(*names):
            raise ApiError(self.t('You are not allowed to access this page.', 'غير مسموح لك بالوصول إلى هذه الصفحة.'), 403)

    def company_domain(self, field='company_id', allow_empty=False):
        domain = [(field, 'in', self.company_ids or [0])]
        if allow_empty:
            return ['|', (field, '=', False)] + domain
        return domain

    def decision_env(self):
        """Environment used once the API has authorised an approval."""
        return self.env(context=dict(self.env.context, **{API_DECISION_KEY: True}))

    def company(self, company_id):
        company = self.companies.filtered(lambda c: c.id == to_int(company_id))[:1]
        if not company:
            raise ApiError(self.t('This company is not in your allowed companies.', 'هذه الشركة ليست ضمن شركاتك المسموح بها.'), 403)
        return company

    def local_bounds(self, period):
        today = fields.Date.context_today(self.employee)
        if period == 'today':
            start, end = today, today
        elif period in ('week', 'month'):
            start, end = date_utils.start_of(today, period), date_utils.end_of(today, period)
        else:
            return False, False
        tz = pytz.timezone(self.employee.tz or 'UTC')
        to_utc = lambda d, t: tz.localize(datetime.combine(d, t)).astimezone(pytz.utc).replace(tzinfo=None)
        return to_utc(start, time.min), to_utc(end, time.max)


def to_int(value, default=0):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def to_float(value, default=0.0):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return default


def float_to_hhmm(value):
    if value in (False, None):
        return ''
    hours = int(value)
    minutes = int(round((value - hours) * 60))
    if minutes == 60:
        hours, minutes = hours + 1, 0
    return '%02d:%02d' % (hours, minutes)


def hhmm_to_float(value):
    if not value:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    hours, _sep, minutes = str(value).partition(':')
    return to_int(hours) + to_int(minutes) / 60.0


def selection_options(record_or_model, field_name):
    field = record_or_model._fields[field_name]
    return [{'value': key, 'label': label} for key, label in field._description_selection(record_or_model.env)]


def record_options(records):
    return [{'value': rec.id, 'label': rec.display_name} for rec in records]


def serialize(record, field_name):
    """JSON-friendly value of one field, keeping labels for relations/selections."""
    field = record._fields[field_name]
    value = record[field_name]
    ftype = field.type
    if ftype == 'many2one':
        return {'id': value.id, 'name': value.display_name} if value else None
    if ftype in ('one2many', 'many2many'):
        return [{'id': rec.id, 'name': rec.display_name} for rec in value]
    if ftype == 'selection':
        if not value:
            return None
        return {'value': value, 'label': dict(field._description_selection(record.env)).get(value, value)}
    if ftype == 'date':
        return fields.Date.to_string(value) if value else None
    if ftype == 'datetime':
        return value.isoformat() + 'Z' if value else None
    if ftype == 'binary':
        return bool(value)
    if ftype == 'boolean':
        return bool(value)
    if ftype in ('float', 'monetary', 'integer'):
        return value or 0
    return value or None


def field_label(model, field_name):
    return model._fields[field_name].get_description(model.env)['string']


def describe(model, field_name, **overrides):
    """Form-field descriptor built from the Odoo field definition."""
    field = model._fields[field_name]
    ftype = field.type
    desc = {
        'name': field_name,
        'label': field_label(model, field_name),
        'type': {'monetary': 'float', 'html': 'html', 'one2many': 'many2many'}.get(ftype, ftype),
        'required': bool(field.required),
        'help': field.help or '',
    }
    if ftype == 'selection':
        desc['options'] = selection_options(model, field_name)
    desc.update(overrides)
    return desc


def form_value(record, field_name):
    """Raw value used to pre-fill an editable form field."""
    field = record._fields[field_name]
    value = record[field_name]
    if field.type == 'many2one':
        return value.id or False
    if field.type in ('one2many', 'many2many'):
        return value.ids
    if field.type == 'date':
        return fields.Date.to_string(value) if value else ''
    if field.type == 'datetime':
        return fields.Datetime.to_string(value) if value else ''
    if field.type == 'boolean':
        return bool(value)
    if field.type in ('float', 'monetary', 'integer'):
        return value or 0
    return value or ''


def clean_value(model, field_name, raw):
    """Convert a value posted by the website to an ORM write value."""
    field = model._fields[field_name]
    ftype = field.type
    if ftype == 'many2one':
        return to_int(raw) or False
    if ftype in ('many2many', 'one2many'):
        return [(6, 0, [to_int(item) for item in (raw or []) if to_int(item)])]
    if ftype == 'boolean':
        return bool(raw) and raw not in ('0', 'false', 'False')
    if ftype == 'integer':
        return to_int(raw)
    if ftype in ('float', 'monetary'):
        return to_float(raw)
    if ftype in ('date', 'datetime'):
        return raw or False
    if ftype == 'selection':
        allowed = {key for key, _label in field._description_selection(model.env)}
        return raw if raw in allowed else False
    if isinstance(raw, str):
        return raw.strip() or False
    return raw or False


def user_message(error):
    if isinstance(error, (UserError, ValidationError, AccessError)):
        return error.args[0] if error.args else str(error)
    return str(error)


class Feature:
    key = ''
    model = ''
    title = ('', '')
    subtitle = ('', '')
    icon = ''
    section = 'hr'
    sequence = 100
    permissions = ()
    admin_permissions = ()
    employee_field = 'employee_id'
    company_field = 'company_id'
    order = 'id desc'
    list_fields = ()
    admin_list_fields = ()
    detail_fields = ()
    search_fields = ('display_name',)
    admin_search_fields = ()
    state_field = 'state'
    page_size = 20

    # ---- visibility & scope -------------------------------------------------
    def visible(self, ctx):
        return ctx.can(*self.permissions, *self.admin_permissions)

    def is_admin(self, ctx):
        return bool(self.admin_permissions) and ctx.can(*self.admin_permissions)

    def tile(self, ctx):
        return {
            'key': self.key,
            'title': ctx.t(*self.title),
            'subtitle': ctx.t(*self.subtitle),
            'icon': self.icon,
            'section': self.section,
            'route': '/f/%s' % self.key,
        }

    def Model(self, ctx):
        return ctx.env[self.model]

    def base_domain(self, ctx):
        if self.is_admin(ctx) and self.company_field:
            return ctx.company_domain(self.company_field, allow_empty=True)
        return [(self.employee_field, '=', ctx.employee.id)]

    def ensure_visible(self, ctx):
        if not self.visible(ctx):
            raise ApiError(ctx.t('You are not allowed to access this page.', 'غير مسموح لك بالوصول إلى هذه الصفحة.'), 403)
        if not ctx.employee:
            raise ApiError(ctx.t('Your account is not linked to an employee.', 'حسابك غير مرتبط بموظف.'), 403)

    def check_record(self, ctx, record_id):
        self.ensure_visible(ctx)
        record = self.Model(ctx).browse(to_int(record_id))
        if not record.exists() or not self.Model(ctx).search_count([('id', '=', record.id)] + self.base_domain(ctx)):
            raise ApiError(ctx.t('This record does not exist or is not accessible.', 'هذا السجل غير موجود أو غير متاح.'), 404)
        return record

    # ---- list -----------------------------------------------------------------
    def filters(self, ctx):
        """[(key, label, domain)]"""
        return [('all', ctx.t('All', 'الكل'), [])] + self.company_filters(ctx)

    def company_filters(self, ctx):
        if not self.company_field or len(ctx.companies) < 2 or not (self.is_admin(ctx) or not self.employee_field):
            return []
        return [('company_%s' % c.id, c.name, [(self.company_field, '=', c.id)]) for c in ctx.companies]

    def state_filters(self, ctx):
        Model = self.Model(ctx)
        return [(key, label, [(self.state_field, '=', key)]) for key, label in Model._fields[self.state_field]._description_selection(ctx.env)]

    def sortings(self, ctx):
        """[(key, label, order)]"""
        return [('default', ctx.t('Newest', 'الأحدث'), self.order)]

    def columns(self, ctx):
        return list(self.admin_list_fields if self.is_admin(ctx) else ()) + list(self.list_fields)

    def search_domain(self, ctx, search):
        names = list(self.search_fields) + (list(self.admin_search_fields) if self.is_admin(ctx) else [])
        if not search or not names:
            return []
        return ['|'] * (len(names) - 1) + [(name, 'ilike', search) for name in names]

    def list_params(self, ctx):
        """Extra list inputs (e.g. a date range) shown above the table."""
        return []

    def list_actions(self, ctx):
        return []

    def run_list_action(self, ctx, action, params):
        raise ApiError(ctx.t('This action is not available.', 'هذا الإجراء غير متاح.'))

    def extra_list_domain(self, ctx, params):
        return []

    def serialize_row(self, ctx, record, columns):
        row = {'id': record.id, 'display_name': record.display_name}
        for name in columns:
            row[name] = serialize(record, name)
        return row

    def list(self, ctx, page=1, filterby=None, search=None, sortby=None, params=None):
        self.ensure_visible(ctx)
        params = params or {}
        Model = self.Model(ctx)
        filters = self.filters(ctx)
        filter_map = {key: domain for key, _label, domain in filters}
        filterby = filterby if filterby in filter_map else filters[0][0]
        sortings = self.sortings(ctx)
        sort_map = {key: order for key, _label, order in sortings}
        sortby = sortby if sortby in sort_map else sortings[0][0]
        domain = (
            self.base_domain(ctx)
            + filter_map[filterby]
            + self.search_domain(ctx, (search or '').strip())
            + self.extra_list_domain(ctx, params)
        )
        page = max(1, to_int(page, 1))
        total = Model.search_count(domain)
        records = Model.search(domain, order=sort_map[sortby], limit=self.page_size, offset=(page - 1) * self.page_size)
        columns = self.columns(ctx)
        return {
            'title': self.tile(ctx)['title'],
            'columns': [{'key': name, 'label': field_label(Model, name), 'type': Model._fields[name].type} for name in columns],
            'rows': [self.serialize_row(ctx, record, columns) for record in records],
            'filters': [{'key': key, 'label': label} for key, label, _d in filters],
            'sortings': [{'key': key, 'label': label} for key, label, _o in sortings],
            'filterby': filterby,
            'sortby': sortby,
            'params': self.list_params(ctx),
            'list_actions': self.list_actions(ctx),
            'can_create': self.can_create(ctx),
            'meta': {'page': page, 'per_page': self.page_size, 'total': total, 'pages': max(1, -(-total // self.page_size))},
        }

    # ---- detail ---------------------------------------------------------------
    def detail_field_names(self, ctx, record):
        return list(self.admin_list_fields if self.is_admin(ctx) else ()) + list(self.detail_fields or self.list_fields)

    def sections(self, ctx, record):
        """Extra blocks (line tables, html, files) rendered under the fields."""
        return []

    def actions(self, ctx, record):
        """[{key, label, style, confirm}] available on this record."""
        return []

    def run_action(self, ctx, record, action, params):
        raise ApiError(ctx.t('This action is not available.', 'هذا الإجراء غير متاح.'))

    def edit_fields(self, ctx, record):
        return []

    def save(self, ctx, record, values):
        allowed = {desc['name']: desc for desc in self.edit_fields(ctx, record)}
        if not allowed:
            raise ApiError(ctx.t('This record cannot be edited.', 'لا يمكن تعديل هذا السجل.'))
        vals = {name: clean_value(record, name, values[name]) for name in allowed if name in values and not allowed[name].get('readonly')}
        if vals:
            record.write(vals)

    def save_lines(self, ctx, record, block, rows, new_rows, deleted):
        raise ApiError(ctx.t('These lines cannot be edited.', 'لا يمكن تعديل هذه السطور.'))

    def reports(self, ctx, record):
        """[{key, label}] downloadable files for this record."""
        return []

    def report(self, ctx, record, key):
        """Return (content bytes, filename, mimetype)."""
        raise ApiError(ctx.t('Report not available.', 'التقرير غير متاح.'), 404)

    def detail(self, ctx, record):
        names = self.detail_field_names(ctx, record)
        edit = self.edit_fields(ctx, record)
        for desc in edit:
            desc.setdefault('value', form_value(record, desc['name']) if desc['name'] in record._fields else '')
        state = record._fields.get(self.state_field) and serialize(record, self.state_field)
        return {
            'id': record.id,
            'title': record.display_name,
            'state': state,
            'fields': [{'key': name, 'label': field_label(record, name), 'type': record._fields[name].type, 'value': serialize(record, name)} for name in names],
            'sections': self.sections(ctx, record),
            'actions': self.actions(ctx, record),
            'edit_fields': edit,
            'reports': self.reports(ctx, record),
        }

    # ---- create ---------------------------------------------------------------
    def can_create(self, ctx):
        return False

    def form(self, ctx, values):
        """Create-form descriptors; ``values`` holds the user's current input."""
        return []

    def create(self, ctx, values):
        raise ApiError(ctx.t('You cannot create records here.', 'لا يمكنك إنشاء سجلات هنا.'), 403)

    # ---- helpers ------------------------------------------------------------------
    @staticmethod
    def pdf_from_report(ctx, report_ref, record, filename):
        report = ctx.env['ir.actions.report']._get_report(report_ref) if isinstance(report_ref, str) else report_ref
        content, _type = ctx.env['ir.actions.report'].with_context(lang=ctx.lang)._render_qweb_pdf(report, record.ids)
        return content, filename, 'application/pdf'

    @staticmethod
    def attachments(files):
        """[{name, datas(base64)}] posted by the website -> portal attachment dicts."""
        result = []
        for item in files or []:
            data = (item or {}).get('datas') or ''
            if ',' in data[:100]:
                data = data.split(',', 1)[1]
            if data:
                base64.b64decode(data, validate=True)
                result.append({'name': item.get('name') or 'attachment', 'datas': data})
        return result


def action(key, en, ar, ctx, style='secondary', confirm=None):
    return {'key': key, 'label': ctx.t(en, ar), 'style': style, 'confirm': confirm}


def today(ctx):
    return fields.Date.to_string(fields.Date.context_today(ctx.employee))


def days_ago(ctx, days):
    return fields.Date.to_string(fields.Date.context_today(ctx.employee) - timedelta(days=days))
