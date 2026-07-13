{
    "name": "MO Studio Builder",
    "summary": "Create apps and customize Odoo views with a Studio-like visual builder",
    "description": """
MO Studio Builder is a visual app builder for Odoo 17.

Create custom applications, add fields, customize generated forms and lists,
manage access, open automation shortcuts, and edit page layouts from a Studio-like
interface directly inside Odoo.
    """,
    "version": "17.0.1.0.14",
    "category": "Administration",
    "author": "abdulrahman sammour",
    "website": "https://digitalshopin.com/",
    "license": "OPL-1",
    "price": 5.00,
    "currency": "EUR",
    "depends": ["base", "web", "base_automation"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/module_icon_data.xml",
        "views/studio_builder_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mo_studio_builder/static/src/js/studio_navbar.js",
            "mo_studio_builder/static/src/js/studio_live_enhancements.js",
            "mo_studio_builder/static/src/xml/studio_navbar.xml",
            "mo_studio_builder/static/src/scss/studio_builder.scss",
            "mo_studio_builder/static/src/scss/studio_live_enhancements.scss",
        ],
    },
    "images": [
        "static/description/banner.png",
        "static/description/main_screenshot.png",
        "static/description/screenshot_builder.png",
        "static/description/screenshot_properties.png",
    ],
    "icon": "static/description/icon.png",
    "application": True,
    "installable": True,
    "auto_install": False,
}
