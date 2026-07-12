import re
from lxml import etree
from xml.sax.saxutils import escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


FIELD_TYPES = [
    ("char", "Text"),
    ("text", "Multiline Text"),
    ("html", "HTML"),
    ("integer", "Integer"),
    ("float", "Decimal"),
    ("monetary", "Monetary"),
    ("date", "Date"),
    ("datetime", "Datetime"),
    ("boolean", "Checkbox"),
    ("selection", "Selection"),
    ("many2one", "Many2one"),
    ("many2many", "Many2many"),
    ("binary", "File"),
    ("image", "Image"),
]

VALID_FIELD_TYPES = {key for key, _label in FIELD_TYPES}
FIELD_TYPE_ALIASES = {
    "": "char",
    "text short": "char",
    "multiline": "text",
    "multiline text": "text",
    "decimal": "float",
    "checkbox": "boolean",
    "file": "binary",
}


def slugify(value, prefix="x_"):
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    if not value:
        value = "custom"
    if not value.startswith(prefix):
        value = f"{prefix}{value}"
    return value[:63]


def normalize_field_type(value):
    value = (value or "").strip().lower()
    value = FIELD_TYPE_ALIASES.get(value, value)
    return value if value in VALID_FIELD_TYPES else "char"


class StudioBuilderApp(models.Model):
    _name = "mo.studio.builder.app"
    _description = "MO Studio Builder App"
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, translate=True)
    technical_name = fields.Char(
        string="Technical Model",
        help="Must start with x_. Example: x_customer_visit",
    )
    menu_name = fields.Char(string="Menu Name")
    state = fields.Selection(
        [("draft", "Draft"), ("created", "Created")],
        default="draft",
        required=True,
    )
    model_id = fields.Many2one("ir.model", readonly=True, ondelete="set null")
    model_name = fields.Char(string="Technical Model Name", related="model_id.model", readonly=True)
    action_id = fields.Many2one("ir.actions.act_window", readonly=True, ondelete="set null")
    menu_id = fields.Many2one("ir.ui.menu", readonly=True, ondelete="set null")
    menu_icon = fields.Char(default="mo_studio_builder,static/description/icon.svg")
    menu_icon_upload = fields.Binary(string="App Icon")
    menu_icon_filename = fields.Char(string="App Icon Filename")
    field_line_ids = fields.One2many(
        "mo.studio.builder.field",
        "app_id",
        string="Fields",
        copy=True,
    )

    feature_contact = fields.Boolean(default=True)
    feature_user = fields.Boolean(string="User Assignment", default=True)
    feature_date = fields.Boolean(string="Date & Calendar", default=True)
    feature_date_range = fields.Boolean(string="Date Range & Gantt")
    feature_stage = fields.Boolean(string="Pipeline Stages")
    feature_tags = fields.Boolean(default=True)
    feature_picture = fields.Boolean(default=True)
    feature_notes = fields.Boolean(default=True)
    feature_company = fields.Boolean(default=False)
    feature_monetary = fields.Boolean(string="Monetary Value")
    feature_sorting = fields.Boolean(string="Custom Sorting", default=True)
    feature_archiving = fields.Boolean(default=True)

    view_count = fields.Integer(compute="_compute_counts")
    custom_field_count = fields.Integer(compute="_compute_counts")

    @api.onchange("name")
    def _onchange_name(self):
        if self.name and not self.technical_name:
            self.technical_name = slugify(self.name)
        if self.name and not self.menu_name:
            self.menu_name = self.name

    @api.constrains("technical_name")
    def _check_technical_name(self):
        for rec in self:
            if rec.technical_name and not rec.technical_name.startswith("x_"):
                raise ValidationError(_("The technical model name must start with x_."))

    def _compute_counts(self):
        View = self.env["ir.ui.view"].sudo()
        Field = self.env["ir.model.fields"].sudo()
        for rec in self:
            if rec.model_id:
                rec.view_count = View.search_count([("model", "=", rec.model_id.model)])
                rec.custom_field_count = Field.search_count([
                    ("model_id", "=", rec.model_id.id),
                    ("state", "=", "manual"),
                ])
            else:
                rec.view_count = 0
                rec.custom_field_count = len(rec.field_line_ids)

    def action_add_suggested_fields(self):
        for rec in self:
            existing = set(rec.field_line_ids.mapped("technical_name"))
            commands = []
            for values in rec._suggested_field_values():
                if values["technical_name"] not in existing:
                    commands.append((0, 0, values))
            if commands:
                rec.write({"field_line_ids": commands})
        return True

    def action_create_app(self):
        self.ensure_one()
        if self.state == "created":
            return self.action_open_generated_app()

        model_name = slugify(self.technical_name or self.name)
        if self.env["ir.model"].sudo().search([("model", "=", model_name)], limit=1):
            raise UserError(_("A model with technical name %s already exists.") % model_name)

        model = self.env["ir.model"].sudo().create({
            "name": self.name,
            "model": model_name,
            "state": "manual",
            "order": "id desc",
        })
        self.model_id = model
        self.technical_name = model_name

        self._ensure_field(model, "x_name", "Name", "char")
        for values in self._suggested_field_values():
            self._create_field_from_values(model, values)
        for line in self.field_line_ids:
            line.create_or_update_field()
        if self.feature_sorting:
            model.write({"order": "x_sequence, id"})

        self._ensure_access(model)
        self._generate_views_and_menu()
        self.state = "created"
        return self.action_open_generated_app()

    def action_regenerate_views(self):
        for rec in self:
            if not rec.model_id:
                raise UserError(_("Create the app first."))
            rec._generate_views_and_menu()
        return True

    def action_update_app(self):
        for rec in self:
            if not rec.model_id:
                raise UserError(_("Create the app first."))
            for line in rec.field_line_ids:
                line.create_or_update_field()
            rec._relax_generated_name_field()
            if rec.feature_sorting:
                rec.model_id.write({"order": "x_sequence, id"})
            rec._ensure_access(rec.model_id)
            rec._generate_views_and_menu()
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_open_generated_app(self):
        self.ensure_one()
        if not self.action_id:
            raise UserError(_("The app action has not been generated yet."))
        return self.action_id.read()[0]

    def _list_form_action(self, name, res_model, domain=None, context=None):
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": res_model,
            "view_mode": "list,form",
            "views": [(False, "list"), (False, "form")],
            "domain": domain or [],
            "context": context or {},
        }

    def action_open_fields(self):
        self.ensure_one()
        return self._list_form_action(
            _("Fields"),
            "ir.model.fields",
            [("model_id", "=", self.model_id.id)],
            {"default_model_id": self.model_id.id, "default_model": self.model_id.model},
        )

    def action_open_views(self):
        self.ensure_one()
        return self._list_form_action(
            _("Views"),
            "ir.ui.view",
            [("model", "=", self.model_id.model)],
            {"default_model": self.model_id.model},
        )

    def action_open_access(self):
        self.ensure_one()
        return self._list_form_action(
            _("Access Rights"),
            "ir.model.access",
            [("model_id", "=", self.model_id.id)],
            {"default_model_id": self.model_id.id},
        )

    def action_open_automations(self):
        self.ensure_one()
        return self._list_form_action(
            _("Automations"),
            "base.automation",
            [("model_id", "=", self.model_id.id)],
            {"default_model_id": self.model_id.id},
        )

    @api.model
    def get_page_editor_context(self, model_name):
        if not model_name:
            raise UserError(_("Open a model page first, then start Studio."))
        model = self.env["ir.model"].sudo().search([("model", "=", model_name)], limit=1)
        if not model:
            raise UserError(_("Model %s was not found.") % model_name)
        field_records = self.env["ir.model.fields"].sudo().search(
            [("model_id", "=", model.id)],
            order="state desc, name",
        )
        ordered_names = self._ordered_field_names(model.model, "form")
        fields_data = []
        for field in field_records:
            fields_data.append({
                "id": field.id,
                "name": field.name,
                "field_description": field.field_description,
                "ttype": field.ttype,
                "state": field.state,
                "required": field.required,
                "readonly": field.readonly,
                "help": field.help,
                "relation": field.relation,
                "selection_options": "\n".join(
                    f"{selection.value}:{selection.name}"
                    for selection in field.selection_ids.sorted("sequence")
                ),
                "can_make_required": self._can_make_required(model, field.name),
                "in_form": field.name in ordered_names,
            })
        views = self.env["ir.ui.view"].sudo().search_read(
            [("model", "=", model.model), ("type", "in", ["form", "tree", "kanban", "search", "calendar", "pivot", "graph"])],
            ["name", "type", "inherit_id"],
            order="type, priority, id",
        )
        return {
            "model_id": model.id,
            "model": model.model,
            "model_label": model.name,
            "is_custom_model": model.state == "manual",
            "fields": fields_data,
            "form_field_order": ordered_names,
            "views": views,
            "field_types": FIELD_TYPES,
            "access_rows": self._access_rows(model),
            "automation_rows": self._automation_rows(model),
            "report_rows": self._report_rows(model),
        }

    @api.model
    def add_field_to_model(self, model_name, values):
        model = self.env["ir.model"].sudo().search([("model", "=", model_name)], limit=1)
        if not model:
            raise UserError(_("Model %s was not found.") % model_name)
        values = values or {}
        field_type = normalize_field_type(values.get("ttype"))
        label = values.get("name") or dict(FIELD_TYPES).get(field_type) or _("Custom Field")
        technical_name = slugify(values.get("technical_name") or label)
        relation = values.get("relation_model")
        selection_options = values.get("selection_options")
        currency_field = values.get("currency_field")
        if field_type in ("many2one", "many2many") and not relation:
            relation = "res.partner"
        if field_type == "selection" and not selection_options:
            selection_options = "yes:Yes\nno:No"
        if field_type == "monetary" and not currency_field:
            currency = self._ensure_currency_field(model)
            currency_field = currency.name
        field = self._ensure_field(
            model,
            technical_name,
            label,
            field_type,
            relation=relation,
            required=bool(values.get("required")) and self._can_make_required(model, technical_name),
            selection_options=selection_options,
            currency_field=currency_field,
        )
        if values.get("add_to_form", True):
            self._ensure_inherited_view_field(model, field, "form", after_field_name=values.get("after_field_name"))
            if field_type == "monetary":
                self._ensure_inherited_view_field(model, currency, "form")
        if values.get("add_to_list", True):
            self._ensure_inherited_view_field(model, field, "tree")
            if field_type == "monetary":
                self._ensure_inherited_view_field(model, currency, "tree")
        return self.get_page_editor_context(model.model)

    @api.model
    def update_field_on_model(self, model_name, field_name, values):
        model = self.env["ir.model"].sudo().search([("model", "=", model_name)], limit=1)
        if not model:
            raise UserError(_("Model %s was not found.") % model_name)
        field = self.env["ir.model.fields"].sudo().search([
            ("model_id", "=", model.id),
            ("name", "=", field_name),
        ], limit=1)
        if not field:
            raise UserError(_("Field %s was not found.") % field_name)
        values = values or {}
        writable = {
            "field_description": values.get("field_description") or field.field_description,
            "help": values.get("help") or False,
            "required": bool(values.get("required")),
            "readonly": bool(values.get("readonly")),
        }
        if writable["required"] and not self._can_make_required(model, field.name):
            raise UserError(_("This field has empty values on existing records. Fill them first, then make it required."))
        if field.state == "manual":
            technical_name = values.get("technical_name") or values.get("name")
            if technical_name and technical_name != field.name:
                writable["name"] = slugify(technical_name)
            if values.get("ttype"):
                writable["ttype"] = "binary" if normalize_field_type(values.get("ttype")) == "image" else normalize_field_type(values.get("ttype"))
            if values.get("relation"):
                writable["relation"] = values.get("relation")
            field.write(writable)
        else:
            field.write({
                "field_description": writable["field_description"],
                "help": writable["help"],
            })
            self._ensure_field_view_attributes(model, field, values)
        if field.ttype == "selection" and values.get("selection_options"):
            self.env["ir.model.fields"].sudo().invalidate_model(["selection_ids"])
            self.env["ir.model.fields.selection"].sudo()._update_selection(
                field.model,
                field.name,
                [(cmd[2]["value"], cmd[2]["name"]) for cmd in self._selection_commands(values.get("selection_options"))],
            )
        return self.get_page_editor_context(model.model)

    @api.model
    def add_existing_field_to_view(self, model_name, field_name, view_type="form", after_field_name=None):
        model = self.env["ir.model"].sudo().search([("model", "=", model_name)], limit=1)
        if not model:
            raise UserError(_("Model %s was not found.") % model_name)
        field = self.env["ir.model.fields"].sudo().search([
            ("model_id", "=", model.id),
            ("name", "=", field_name),
        ], limit=1)
        if not field:
            raise UserError(_("Field %s was not found.") % field_name)
        if view_type not in ("form", "tree"):
            view_type = "form"
        self._ensure_inherited_view_field(model, field, view_type, after_field_name=after_field_name)
        return self.get_page_editor_context(model.model)

    @api.model
    def move_field_in_view(self, model_name, field_name, after_field_name=None, view_type="form"):
        model = self.env["ir.model"].sudo().search([("model", "=", model_name)], limit=1)
        if not model:
            raise UserError(_("Model %s was not found.") % model_name)
        field = self.env["ir.model.fields"].sudo().search([
            ("model_id", "=", model.id),
            ("name", "=", field_name),
        ], limit=1)
        if not field:
            raise UserError(_("Field %s was not found.") % field_name)
        self._ensure_field_moved_in_view(model, field, view_type, after_field_name=after_field_name)
        return self.get_page_editor_context(model.model)

    @api.model
    def remove_field_from_model(self, model_name, field_name):
        model = self.env["ir.model"].sudo().search([("model", "=", model_name)], limit=1)
        if not model:
            raise UserError(_("Model %s was not found.") % model_name)
        field = self.env["ir.model.fields"].sudo().search([
            ("model_id", "=", model.id),
            ("name", "=", field_name),
        ], limit=1)
        if not field:
            raise UserError(_("Field %s was not found.") % field_name)
        if field.state != "manual":
            raise UserError(_("Only custom fields can be deleted from Studio Builder."))
        self._remove_field_from_studio_views(model, field.name)
        self.env["mo.studio.builder.field"].sudo().search([("ir_field_id", "=", field.id)]).unlink()
        field.unlink()
        return self.get_page_editor_context(model.model)

    @api.model
    def open_model_fields_action(self, model_name):
        model = self.env["ir.model"].sudo().search([("model", "=", model_name)], limit=1)
        if not model:
            raise UserError(_("Model %s was not found.") % model_name)
        return self._list_form_action(
            _("Fields"),
            "ir.model.fields",
            [("model_id", "=", model.id)],
            {"default_model_id": model.id, "default_model": model.model},
        )

    @api.model
    def open_model_views_action(self, model_name):
        return self._list_form_action(
            _("Views"),
            "ir.ui.view",
            [("model", "=", model_name)],
            {"default_model": model_name},
        )

    @api.model
    def open_model_automations_action(self, model_name):
        model = self.env["ir.model"].sudo().search([("model", "=", model_name)], limit=1)
        if not model:
            raise UserError(_("Model %s was not found.") % model_name)
        return self._list_form_action(
            _("Automations"),
            "base.automation",
            [("model_id", "=", model.id)],
            {"default_model_id": model.id},
        )

    @api.model
    def open_model_access_action(self, model_name):
        model = self.env["ir.model"].sudo().search([("model", "=", model_name)], limit=1)
        if not model:
            raise UserError(_("Model %s was not found.") % model_name)
        return self._list_form_action(
            _("Access Rights"),
            "ir.model.access",
            [("model_id", "=", model.id)],
            {"default_model_id": model.id},
        )

    @api.model
    def open_model_reports_action(self, model_name):
        return self._list_form_action(
            _("Reports"),
            "ir.actions.report",
            [("model", "=", model_name)],
            {"default_model": model_name},
        )

    def _suggested_field_values(self):
        self.ensure_one()
        fields_to_create = []
        if self.feature_contact:
            fields_to_create += [
                {"name": "Customer", "technical_name": "x_partner_id", "ttype": "many2one", "relation_model": "res.partner"},
                {"name": "Phone", "technical_name": "x_phone", "ttype": "char"},
                {"name": "Email", "technical_name": "x_email", "ttype": "char"},
            ]
        if self.feature_user:
            fields_to_create.append({"name": "Responsible", "technical_name": "x_user_id", "ttype": "many2one", "relation_model": "res.users"})
        if self.feature_date:
            fields_to_create.append({"name": "Date", "technical_name": "x_date", "ttype": "date"})
        if self.feature_date_range:
            fields_to_create += [
                {"name": "Start Date", "technical_name": "x_date_start", "ttype": "date"},
                {"name": "End Date", "technical_name": "x_date_end", "ttype": "date"},
            ]
        if self.feature_stage:
            fields_to_create.append({
                "name": "Stage",
                "technical_name": "x_stage",
                "ttype": "selection",
                "selection_options": "new:New\nin_progress:In Progress\ndone:Done\ncancelled:Cancelled",
            })
        if self.feature_tags:
            fields_to_create.append({"name": "Tags", "technical_name": "x_tag_ids", "ttype": "many2many", "relation_model": "res.partner.category"})
        if self.feature_picture:
            fields_to_create.append({"name": "Picture", "technical_name": "x_image", "ttype": "image"})
        if self.feature_notes:
            fields_to_create.append({"name": "Notes", "technical_name": "x_notes", "ttype": "html"})
        if self.feature_company:
            fields_to_create.append({"name": "Company", "technical_name": "x_company_id", "ttype": "many2one", "relation_model": "res.company"})
        if self.feature_monetary:
            fields_to_create += [
                {"name": "Currency", "technical_name": "x_currency_id", "ttype": "many2one", "relation_model": "res.currency"},
                {"name": "Amount", "technical_name": "x_amount", "ttype": "monetary", "currency_field": "x_currency_id"},
            ]
        if self.feature_sorting:
            fields_to_create.append({"name": "Sequence", "technical_name": "x_sequence", "ttype": "integer"})
        if self.feature_archiving:
            fields_to_create.append({"name": "Active", "technical_name": "x_active", "ttype": "boolean"})
        return fields_to_create

    def _create_field_from_values(self, model, values):
        return self._ensure_field(
            model,
            values["technical_name"],
            values["name"],
            values["ttype"],
            relation=values.get("relation_model"),
            required=values.get("required", False),
            selection_options=values.get("selection_options"),
            currency_field=values.get("currency_field"),
        )

    def _ensure_currency_field(self, model):
        Field = self.env["ir.model.fields"].sudo()
        existing = Field.search([
            ("model_id", "=", model.id),
            ("ttype", "=", "many2one"),
            ("relation", "=", "res.currency"),
        ], limit=1)
        if existing:
            return existing
        return self._ensure_field(model, "x_currency_id", _("Currency"), "many2one", relation="res.currency")

    def _can_make_required(self, model, field_name):
        Model = self.env.get(model.model)
        if not Model:
            return False
        if not Model.sudo().search([], limit=1):
            return True
        if field_name not in Model._fields:
            return False
        try:
            return not Model.sudo().search([(field_name, "=", False)], limit=1)
        except Exception:
            return False

    def _ensure_field(self, model, name, label, ttype, relation=None, required=False, selection_options=None, currency_field=None):
        Field = self.env["ir.model.fields"].sudo()
        name = slugify(name)
        ttype = normalize_field_type(ttype)
        existing = Field.search([("model_id", "=", model.id), ("name", "=", name)], limit=1)
        if existing:
            return existing
        values = {
            "name": name,
            "field_description": label,
            "model_id": model.id,
            "ttype": "binary" if ttype == "image" else ttype,
            "required": required,
        }
        if ttype == "image":
            values["help"] = _("Image field generated by MO Studio Builder.")
        if relation:
            values["relation"] = relation
        if currency_field:
            values["currency_field"] = currency_field
        if selection_options:
            values["selection_ids"] = self._selection_commands(selection_options)
        return Field.create(values)

    def _selection_commands(self, options):
        commands = []
        raw_options = (options or "").replace(",", "\n").replace("\u061b", "\n").replace("\u060c", "\n")
        for sequence, raw in enumerate(raw_options.splitlines(), start=1):
            raw = raw.strip()
            if not raw:
                continue
            if ":" in raw:
                value, label = raw.split(":", 1)
            else:
                value = slugify(raw, prefix="").lower()
                label = raw
            commands.append((0, 0, {
                "sequence": sequence,
                "value": value.strip(),
                "name": label.strip(),
            }))
        return commands

    def _ensure_inherited_view_field(self, model, field, view_type, after_field_name=None):
        View = self.env["ir.ui.view"].sudo()
        base_view = View.search([
            ("model", "=", model.model),
            ("type", "=", view_type),
            ("inherit_id", "=", False),
        ], order="priority, id", limit=1)
        if not base_view:
            return False

        name = f"{model.model}.{view_type}.mo_studio_builder_extension"
        view = View.search([
            ("name", "=", name),
            ("model", "=", model.model),
            ("inherit_id", "=", base_view.id),
        ], limit=1)
        field_xml = self._field_xml_for_arch(field)
        base_arch = base_view.arch_base or base_view.arch_db or ""
        if view:
            arch = view.arch_base or view.arch_db or "<data/>"
            root = etree.fromstring(arch.encode())
            if root.xpath(f".//field[@name='{field.name}']"):
                if after_field_name:
                    self._ensure_field_moved_in_view(model, field, view_type, after_field_name=after_field_name)
                return view
            if after_field_name and not root.xpath(f".//field[@name='{after_field_name}']") and f'name="{after_field_name}"' not in base_arch:
                after_field_name = None
            target_xpath, position, content = self._view_insert_spec(view_type, field_xml, after_field_name)
            root.append(etree.fromstring(f'<xpath expr="{target_xpath}" position="inside">{content}</xpath>'.encode()))
            if position != "inside":
                root[-1].set("position", position)
            view.write({"arch_base": etree.tostring(root, encoding="unicode")})
            return view

        if after_field_name and f'name="{after_field_name}"' not in base_arch:
            after_field_name = None
        target_xpath, position, content = self._view_insert_spec(view_type, field_xml, after_field_name)
        if view_type == "form":
            arch = f'<data><xpath expr="{target_xpath}" position="{position}">{content}</xpath></data>'
        else:
            arch = f'<data><xpath expr="{target_xpath}" position="{position}">{content}</xpath></data>'
        return View.create({
            "name": name,
            "model": model.model,
            "type": view_type,
            "inherit_id": base_view.id,
            "mode": "extension",
            "priority": 99,
            "arch_base": arch,
        })

    def _ensure_field_moved_in_view(self, model, field, view_type, after_field_name=None):
        if not after_field_name or after_field_name == field.name:
            return False
        View = self.env["ir.ui.view"].sudo()
        base_view = View.search([
            ("model", "=", model.model),
            ("type", "=", view_type),
            ("inherit_id", "=", False),
        ], order="priority, id", limit=1)
        if not base_view:
            return False
        name = f"{model.model}.{view_type}.mo_studio_builder_layout"
        view = View.search([
            ("name", "=", name),
            ("model", "=", model.model),
            ("inherit_id", "=", base_view.id),
        ], limit=1)
        move_xml = (
            f'<xpath expr="//field[@name=\'{after_field_name}\']" position="after">'
            f'<xpath expr="//field[@name=\'{field.name}\']" position="move"/>'
            '</xpath>'
        )
        if view:
            arch = view.arch_base or view.arch_db or "<data/>"
            root = etree.fromstring(arch.encode())
            for node in root.xpath(f".//xpath[contains(@expr, \"@name='{field.name}'\")]"):
                parent = node.getparent()
                if parent is not None:
                    parent.remove(node)
            root.append(etree.fromstring(move_xml.encode()))
            view.write({"arch_base": etree.tostring(root, encoding="unicode")})
            return view
        return View.create({
            "name": name,
            "model": model.model,
            "type": view_type,
            "inherit_id": base_view.id,
            "mode": "extension",
            "priority": 100,
            "arch_base": f"<data>{move_xml}</data>",
        })

    def _ensure_field_view_attributes(self, model, field, values):
        View = self.env["ir.ui.view"].sudo()
        base_view = View.search([
            ("model", "=", model.model),
            ("type", "=", "form"),
            ("inherit_id", "=", False),
        ], order="priority, id", limit=1)
        if not base_view:
            return False
        attrs = {
            "string": values.get("field_description") or field.field_description,
            "help": values.get("help") or "",
            "required": "1" if values.get("required") else "0",
            "readonly": "1" if values.get("readonly") else "0",
        }
        attr_nodes = "".join(f'<attribute name="{key}">{escape(val)}</attribute>' for key, val in attrs.items())
        item_xml = f'<xpath expr="//field[@name=\'{field.name}\']" position="attributes">{attr_nodes}</xpath>'
        name = f"{model.model}.form.mo_studio_builder_attrs.{field.name}"
        view = View.search([
            ("name", "=", name),
            ("model", "=", model.model),
            ("inherit_id", "=", base_view.id),
        ], limit=1)
        values_to_write = {
            "name": name,
            "model": model.model,
            "type": "form",
            "inherit_id": base_view.id,
            "mode": "extension",
            "priority": 101,
            "arch_base": f"<data>{item_xml}</data>",
        }
        if view:
            view.write(values_to_write)
            return view
        return View.create(values_to_write)

    def _ordered_field_names(self, model_name, view_type):
        View = self.env["ir.ui.view"].sudo()
        view = View.search([
            ("model", "=", model_name),
            ("type", "=", view_type),
        ], order="priority desc, id desc", limit=1)
        if not view:
            return []
        try:
            arch = view.get_combined_arch()
        except Exception:
            arch = view.arch_base or view.arch_db or ""
        try:
            root = etree.fromstring(arch.encode())
        except Exception:
            return []
        names = []
        for node in root.xpath(".//field[@name]"):
            name = node.get("name")
            if name and name not in names:
                names.append(name)
        return names

    def _access_rows(self, model):
        return self.env["ir.model.access"].sudo().search_read(
            [("model_id", "=", model.id)],
            ["name", "group_id", "perm_read", "perm_write", "perm_create", "perm_unlink"],
            limit=30,
        )

    def _automation_rows(self, model):
        return self.env["base.automation"].sudo().search_read(
            [("model_id", "=", model.id)],
            ["name", "active", "trigger"],
            limit=30,
        )

    def _report_rows(self, model):
        return self.env["ir.actions.report"].sudo().search_read(
            [("model", "=", model.model)],
            ["name", "report_type", "report_name"],
            limit=30,
        )

    def _view_insert_spec(self, view_type, field_xml, after_field_name=None):
        if after_field_name:
            return f"//field[@name='{after_field_name}']", "after", field_xml
        if view_type == "form":
            return "//sheet", "inside", f'<group string="Studio">{field_xml}</group>'
        return "//tree", "inside", field_xml

    def _remove_field_from_studio_views(self, model, field_name):
        views = self.env["ir.ui.view"].sudo().search([
            ("model", "=", model.model),
            ("name", "like", "mo_studio_builder"),
        ])
        for view in views:
            arch = view.arch_base or view.arch_db or "<data/>"
            root = etree.fromstring(arch.encode())
            changed = False
            for node in root.xpath(f".//field[@name='{field_name}']"):
                parent = node.getparent()
                if parent is not None:
                    parent.remove(node)
                    if parent.tag == "group" and not len(parent) and parent.getparent() is not None:
                        parent.getparent().remove(parent)
                changed = True
            if changed:
                view.write({"arch_base": etree.tostring(root, encoding="unicode")})

    def _field_xml_for_arch(self, field):
        if field.ttype == "many2many":
            return f'<field name="{field.name}" widget="many2many_tags"/>'
        if field.ttype == "binary" and (field.name.endswith("image") or "image" in field.name or "picture" in field.name or field.help == _("Image field generated by MO Studio Builder.")):
            return f'<field name="{field.name}" widget="image"/>'
        return f'<field name="{field.name}"/>'

    def _ensure_access(self, model):
        Access = self.env["ir.model.access"].sudo()
        name = f"{model.model} user access"
        access = Access.search([("name", "=", name), ("model_id", "=", model.id)], limit=1)
        if not access:
            Access.create({
                "name": name,
                "model_id": model.id,
                "group_id": self.env.ref("base.group_user").id,
                "perm_read": True,
                "perm_write": True,
                "perm_create": True,
                "perm_unlink": True,
            })

    def _generate_views_and_menu(self):
        self.ensure_one()
        self._relax_generated_name_field()
        model = self.model_id.model
        fields_data = self.env["ir.model.fields"].sudo().search([
            ("model_id", "=", self.model_id.id),
            ("name", "like", "x_%"),
        ], order="id")
        field_names = [field.name for field in fields_data]
        view_modes = ["list", "form", "kanban"]
        views = [
            self._upsert_view("tree", self._tree_arch(field_names)),
            self._upsert_view("form", self._form_arch(fields_data)),
            self._upsert_view("kanban", self._kanban_arch(field_names)),
            self._upsert_view("search", self._search_arch(fields_data)),
        ]
        date_field = self._first_existing(field_names, ["x_date_start", "x_date"])
        if date_field:
            views.append(self._upsert_view("calendar", self._calendar_arch(date_field, field_names)))
            view_modes.append("calendar")
        if "x_amount" in field_names:
            views.append(self._upsert_view("pivot", self._pivot_arch()))
            views.append(self._upsert_view("graph", self._graph_arch()))
            view_modes += ["pivot", "graph"]

        action = self._upsert_action(",".join(view_modes))
        self.action_id = action
        self._upsert_menu(action)
        return views

    def _upsert_view(self, view_type, arch):
        View = self.env["ir.ui.view"].sudo()
        name = f"{self.model_id.model}.{view_type}.mo_studio_builder"
        view = View.search([("name", "=", name), ("model", "=", self.model_id.model), ("type", "=", view_type)], limit=1)
        values = {
            "name": name,
            "model": self.model_id.model,
            "type": view_type,
            "arch_base": arch,
        }
        if view:
            view.write(values)
        else:
            view = View.create(values)
        return view

    def _upsert_action(self, view_mode):
        Action = self.env["ir.actions.act_window"].sudo()
        name = self.name
        action = self.action_id or Action.search([("res_model", "=", self.model_id.model), ("name", "=", name)], limit=1)
        values = {
            "name": name,
            "res_model": self.model_id.model,
            "view_mode": view_mode,
            "context": "{}",
        }
        if action:
            action.write(values)
        else:
            action = Action.create(values)
        return action

    def _relax_generated_name_field(self):
        if not self.model_id:
            return
        field = self.env["ir.model.fields"].sudo().search([
            ("model_id", "=", self.model_id.id),
            ("name", "=", "x_name"),
            ("state", "=", "manual"),
        ], limit=1)
        if field and field.required:
            field.write({"required": False})

    def _upsert_menu(self, action):
        Menu = self.env["ir.ui.menu"].sudo()
        menu = self.menu_id or Menu.search([("name", "=", self.menu_name or self.name), ("action", "=", f"ir.actions.act_window,{action.id}")], limit=1)
        values = {
            "name": self.menu_name or self.name,
            "parent_id": False,
            "action": f"ir.actions.act_window,{action.id}",
            "sequence": 100,
        }
        if self.menu_icon_upload:
            values.update({
                "web_icon_data": self.menu_icon_upload,
            })
        else:
            values["web_icon"] = self.menu_icon or "mo_studio_builder,static/description/icon.svg"
        if menu:
            menu.write(values)
        else:
            menu = Menu.create(values)
        self.menu_id = menu
        return menu

    def _tree_arch(self, field_names):
        fields_xml = []
        for name in field_names[:10]:
            if name == "x_image":
                fields_xml.append(f'<field name="{name}" widget="image" optional="show"/>')
            elif name != "x_notes":
                fields_xml.append(f'<field name="{name}" optional="show"/>')
        return "<tree string=\"%s\">%s</tree>" % (escape(self.name), "".join(fields_xml))

    def _form_arch(self, fields_data):
        title = '<h1><field name="x_name" placeholder="Name"/></h1>'
        image = ""
        regular_fields = []
        notebook_pages = []
        for field in fields_data:
            if field.name == "x_name":
                continue
            if field.name == "x_image":
                image = '<field name="x_image" widget="image" class="oe_avatar"/>'
                continue
            if field.ttype == "html":
                notebook_pages.append(f'<page string="{escape(field.field_description)}"><field name="{field.name}"/></page>')
            elif field.ttype == "many2many":
                regular_fields.append(f'<field name="{field.name}" widget="many2many_tags"/>')
            elif field.ttype == "binary":
                regular_fields.append(f'<field name="{field.name}" widget="image"/>')
            else:
                regular_fields.append(f'<field name="{field.name}"/>')
        groups = "".join(f"<group>{''.join(regular_fields[i:i + 8])}</group>" for i in range(0, len(regular_fields), 8))
        notebook = f"<notebook>{''.join(notebook_pages)}</notebook>" if notebook_pages else ""
        return (
            f'<form string="{escape(self.name)}">'
            "<sheet>"
            f"{image}<div class=\"oe_title\">{title}</div>"
            f"<group>{groups}</group>"
            f"{notebook}"
            "</sheet>"
            "</form>"
        )

    def _kanban_arch(self, field_names):
        image = '<img t-if="record.x_image.raw_value" t-att-src="kanban_image(record._name, \'x_image\', record.id.raw_value)" class="oe_kanban_avatar" alt="Image"/>' if "x_image" in field_names else ""
        amount = '<div t-if="record.x_amount.raw_value"><field name="x_amount"/></div>' if "x_amount" in field_names else ""
        partner = '<div t-if="record.x_partner_id.raw_value"><field name="x_partner_id"/></div>' if "x_partner_id" in field_names else ""
        return (
            f'<kanban class="o_kanban_mobile" string="{escape(self.name)}">'
            '<field name="x_name"/>'
            '<templates><t t-name="kanban-box">'
            '<div class="oe_kanban_global_click o_kanban_record">'
            f'{image}<strong><field name="x_name"/></strong>{partner}{amount}'
            '</div></t></templates>'
            '</kanban>'
        )

    def _search_arch(self, fields_data):
        pieces = ['<field name="x_name"/>']
        for field in fields_data:
            if field.name in ("x_partner_id", "x_user_id", "x_stage", "x_company_id"):
                pieces.append(f'<field name="{field.name}"/>')
                pieces.append(f'<filter string="Group by {escape(field.field_description)}" name="group_{field.name}" context="{{\'group_by\': \'{field.name}\'}}"/>')
        if any(field.name == "x_active" for field in fields_data):
            pieces.append('<filter string="Archived" name="archived" domain="[(\'x_active\', \'=\', False)]"/>')
        return f'<search string="{escape(self.name)}">{"".join(pieces)}</search>'

    def _calendar_arch(self, date_field, field_names):
        color = ' color="x_user_id"' if "x_user_id" in field_names else ""
        return f'<calendar string="{escape(self.name)}" date_start="{date_field}"{color}><field name="x_name"/></calendar>'

    def _pivot_arch(self):
        return f'<pivot string="{escape(self.name)}"><field name="x_amount" type="measure"/></pivot>'

    def _graph_arch(self):
        return f'<graph string="{escape(self.name)}" type="bar"><field name="x_amount" type="measure"/></graph>'

    def _first_existing(self, field_names, candidates):
        for candidate in candidates:
            if candidate in field_names:
                return candidate
        return False


class StudioBuilderField(models.Model):
    _name = "mo.studio.builder.field"
    _description = "MO Studio Builder Field"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    app_id = fields.Many2one("mo.studio.builder.app", required=True, ondelete="cascade")
    name = fields.Char(string="Label", required=True, translate=True)
    technical_name = fields.Char(required=True, default="x_")
    ttype = fields.Selection(FIELD_TYPES, string="Type", required=True, default="char")
    required = fields.Boolean()
    readonly = fields.Boolean()
    relation_model_id = fields.Many2one("ir.model", string="Related Model")
    relation_model = fields.Char(related="relation_model_id.model", readonly=True)
    selection_options = fields.Text(
        help="One option per line. Use key:Label, for example draft:Draft.",
    )
    help = fields.Text()
    ir_field_id = fields.Many2one("ir.model.fields", readonly=True, ondelete="set null")

    @api.onchange("name")
    def _onchange_name(self):
        if self.name and (not self.technical_name or self.technical_name == "x_"):
            self.technical_name = slugify(self.name)

    @api.constrains("technical_name")
    def _check_technical_name(self):
        for rec in self:
            if rec.technical_name and not rec.technical_name.startswith("x_"):
                raise ValidationError(_("Custom field names must start with x_."))

    def create_or_update_field(self):
        for rec in self:
            if not rec.app_id.model_id:
                continue
            if rec.ttype in ("many2one", "many2many") and not rec.relation_model:
                raise UserError(_("Field %s needs a related model.") % rec.name)
            field = rec.app_id._ensure_field(
                rec.app_id.model_id,
                rec.technical_name,
                rec.name,
                rec.ttype,
                relation=rec.relation_model,
                required=rec.required,
                selection_options=rec.selection_options,
            )
            values = {
                "field_description": rec.name,
                "help": rec.help,
                "required": rec.required,
                "readonly": rec.readonly,
            }
            if field.state == "manual":
                field.sudo().write(values)
            rec.ir_field_id = field
        return True
