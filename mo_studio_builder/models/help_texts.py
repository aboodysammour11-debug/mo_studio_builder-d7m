from odoo import api, fields, models


class MoStudioBuilderAppHelp(models.Model):
    _inherit = "mo.studio.builder.app"

    technical_name = fields.Char(
        help="Technical model name used internally by Odoo. Example: x_support_request. Use lowercase letters, numbers, and underscores only."
    )
    menu_name = fields.Char(
        help="The app name that will appear in the normal Odoo menu after creating the app."
    )
    menu_icon = fields.Char(
        help="Path of the menu icon file. Example: mo_studio_builder/static/description/icon.png."
    )
    feature_contact = fields.Boolean(
        help="Adds customer/contact fields such as Customer, Phone, and Email to the generated app."
    )
    feature_user = fields.Boolean(
        help="Adds a Responsible user field so each record can be assigned to an employee or Odoo user."
    )
    feature_date = fields.Boolean(
        help="Adds a Date field for appointments, deadlines, or calendar-style tracking."
    )
    feature_date_range = fields.Boolean(
        help="Adds Start Date and End Date fields for requests, bookings, projects, or planned work periods."
    )
    feature_stage = fields.Boolean(
        help="Adds a Status field so records can move through steps such as Draft, In Progress, and Done."
    )
    feature_tags = fields.Boolean(
        help="Adds Tags to classify records and make filtering/searching easier."
    )
    feature_picture = fields.Boolean(
        help="Adds an Image field to attach a main picture to every record."
    )
    feature_notes = fields.Boolean(
        help="Adds a rich Notes field for descriptions, comments, and internal instructions."
    )
    feature_company = fields.Boolean(
        help="Adds a Company field for multi-company databases and company-based filtering."
    )
    feature_monetary = fields.Boolean(
        help="Adds Amount and Currency fields for prices, costs, budgets, or financial values."
    )
    feature_sorting = fields.Boolean(
        help="Adds a Sequence field so records can be manually ordered in list views."
    )
    feature_archiving = fields.Boolean(
        help="Adds an Active checkbox so old records can be archived instead of deleted."
    )


class MoStudioBuilderFieldHelp(models.Model):
    _inherit = "mo.studio.builder.field"

    selection_options = fields.Text(
        help=(
            "Only for Selection fields. Write one option per line using key:Label. "
            "Examples:\nyes:Yes\nno:No\npending:Pending\napproved:Approved"
        )
    )


class IrModelFieldsStudioGuard(models.Model):
    _inherit = "ir.model.fields"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "ttype" in vals:
                vals["ttype"] = (vals.get("ttype") or "").strip()
                if not vals["ttype"]:
                    vals["ttype"] = "char"
        return super().create(vals_list)
