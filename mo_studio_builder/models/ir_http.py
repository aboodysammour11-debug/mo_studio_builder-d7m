from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        result = super().session_info()
        user = self.env.user
        result["mo_studio_builder_access"] = (
            user.has_group("base.group_system")
            or user.has_group("mo_studio_builder.group_mo_studio_builder_user")
        )
        return result
