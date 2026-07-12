{
    "name": "MO Studio Builder",
    "summary": "Create custom Odoo apps, models, fields, menus, and generated views",
    "version": "17.0.1.0.0",
    "category": "Administration",
    "author": "Maqam / Codex",
    "license": "LGPL-3",
    "depends": ["base", "web", "base_automation"],
    "data": [
        "security/ir.model.access.csv",
        "views/studio_builder_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mo_studio_builder/static/src/js/studio_navbar.js",
            "mo_studio_builder/static/src/xml/studio_navbar.xml",
            "mo_studio_builder/static/src/scss/studio_builder.scss",
        ],
    },
    "application": True,
    "installable": True,
}
