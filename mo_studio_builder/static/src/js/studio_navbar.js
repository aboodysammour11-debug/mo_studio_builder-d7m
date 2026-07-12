/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { NavBar } from "@web/webclient/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";
import { session } from "@web/session";

class StudioPageEditorDialog extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            title: "Studio Builder",
            model: this.props.model,
            modelLabel: this.props.model,
            fields: [],
            views: [],
            search: "",
            busy: false,
            dirty: false,
            selectedField: null,
            selectedTool: "char",
            panel: "properties",
            viewType: this.props.viewType || "form",
            formFieldOrder: [],
            draggingFieldName: null,
            accessRows: [],
            automationRows: [],
            reportRows: [],
            field: this.defaultField(),
        });
        onWillStart(async () => this.loadContext());
    }

    defaultField() {
        return {
            name: "",
            technical_name: "x_",
            ttype: "char",
            relation_model: "",
            selection_options: "",
            required: false,
            add_to_form: true,
            add_to_list: true,
        };
    }

    get fieldTypes() {
        return [
            ["char", "Text"], ["text", "Multiline"], ["html", "HTML"],
            ["integer", "Integer"], ["float", "Decimal"], ["monetary", "Monetary"],
            ["date", "Date"], ["datetime", "Datetime"], ["boolean", "Checkbox"],
            ["selection", "Selection"], ["many2one", "Many2one"], ["many2many", "Many2many"],
            ["binary", "File"], ["image", "Image"],
        ];
    }

    get filteredFields() {
        const needle = this.state.search.toLowerCase();
        return this.state.fields.filter((field) => {
            return !needle || field.name.toLowerCase().includes(needle) ||
                (field.field_description || "").toLowerCase().includes(needle);
        }).slice(0, 80);
    }

    get previewFields() {
        const hiddenNames = new Set([
            "id", "display_name", "__last_update", "create_uid", "create_date",
            "write_uid", "write_date",
        ]);
        const fieldByName = Object.fromEntries(this.state.fields.map((field) => [field.name, field]));
        const ordered = (this.state.formFieldOrder || [])
            .map((name) => fieldByName[name])
            .filter((field) => field && !hiddenNames.has(field.name));
        const remaining = this.state.fields.filter((field) =>
            !hiddenNames.has(field.name) && !ordered.some((item) => item.name === field.name)
        );
        return [...ordered, ...remaining].slice(0, 80);
    }

    async loadContext() {
        const data = await this.orm.call("mo.studio.builder.app", "get_page_editor_context", [this.state.model]);
        this.state.model = data.model;
        this.state.modelLabel = data.model_label;
        this.state.title = `Studio Builder - ${data.model_label}`;
        this.state.fields = data.fields;
        this.state.formFieldOrder = data.form_field_order || [];
        this.state.views = data.views;
        this.state.accessRows = data.access_rows || [];
        this.state.automationRows = data.automation_rows || [];
        this.state.reportRows = data.report_rows || [];
        if (!this.state.selectedField && data.fields.length) {
            this.state.selectedField = data.fields.find((field) => field.state === "manual") || data.fields[0];
        }
    }

    selectFieldType(type) {
        const defaults = this.defaultValuesForType(type);
        this.state.field.ttype = type;
        this.state.field.name = defaults.name;
        this.state.field.technical_name = defaults.technical_name;
        this.state.field.relation_model = defaults.relation_model;
        this.state.field.selection_options = defaults.selection_options;
        this.state.selectedTool = type;
        this.state.panel = "new";
    }

    selectExistingField(field) {
        this.state.selectedField = { ...field };
        this.state.panel = "properties";
    }

    markDirty() {
        this.state.dirty = true;
    }

    defaultValuesForType(type) {
        const labels = {
            char: "Text", text: "Notes", html: "Description", integer: "Number",
            float: "Decimal", monetary: "Amount", date: "Date", datetime: "Date Time",
            boolean: "Checkbox", selection: "Status", many2one: "Customer",
            many2many: "Tags", binary: "Attachment", image: "Image",
        };
        const label = labels[type] || "Custom Field";
        return {
            name: label,
            technical_name: `x_${label.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "")}`,
            relation_model: ["many2one", "many2many"].includes(type) ? "res.partner" : "",
            selection_options: type === "selection" ? "yes:Yes\nno:No" : "",
        };
    }

    fieldIcon(type) {
        const icons = {
            char: "fa fa-font", text: "fa fa-align-left", html: "fa fa-code",
            integer: "fa fa-hashtag", float: "fa fa-percent", monetary: "fa fa-money",
            date: "fa fa-calendar", datetime: "fa fa-clock-o", boolean: "fa fa-check-square-o",
            selection: "fa fa-caret-square-o-down", many2one: "fa fa-arrow-right",
            many2many: "fa fa-random", binary: "fa fa-paperclip", image: "fa fa-image",
        };
        return icons[type] || "fa fa-plus";
    }

    async addField() {
        if (!this.state.field.name.trim()) {
            this.notification.add("Field label is required.", { type: "warning" });
            return;
        }
        this.state.busy = true;
        try {
            const data = await this.orm.call("mo.studio.builder.app", "add_field_to_model", [
                this.state.model,
                { ...this.state.field },
            ]);
            this.state.fields = data.fields;
            this.state.views = data.views;
            this.state.field = this.defaultField();
            this.state.dirty = true;
            this.notification.add("Field added to the preview.", { type: "success" });
        } finally {
            this.state.busy = false;
        }
    }

    async createFieldAt(type = this.state.selectedTool, afterFieldName = null) {
        const defaults = this.defaultValuesForType(type);
        const createdName = defaults.technical_name;
        this.state.busy = true;
        try {
            const data = await this.orm.call("mo.studio.builder.app", "add_field_to_model", [
                this.state.model,
                {
                    ...this.defaultField(),
                    ...defaults,
                    ttype: type,
                    after_field_name: afterFieldName,
                    add_to_form: true,
                    add_to_list: true,
                },
            ]);
            this.state.fields = data.fields;
            this.state.formFieldOrder = this.insertNameAfter(
                data.form_field_order || this.state.formFieldOrder || [],
                createdName,
                afterFieldName
            );
            this.state.views = data.views;
            const created = data.fields.find((field) => field.name === createdName);
            this.state.selectedField = created || data.fields.find((field) => field.field_description === defaults.name) || null;
            this.state.panel = "properties";
            this.state.dirty = true;
            this.notification.add("Field added to the preview.", { type: "success" });
        } finally {
            this.state.busy = false;
        }
    }

    insertNameAfter(order, fieldName, afterFieldName) {
        const next = (order || []).filter((name) => name !== fieldName);
        if (!afterFieldName) {
            next.unshift(fieldName);
            return next;
        }
        const index = next.indexOf(afterFieldName);
        if (index < 0) {
            next.push(fieldName);
        } else {
            next.splice(index + 1, 0, fieldName);
        }
        return next;
    }

    startDrag(ev, type) {
        this.selectFieldType(type);
        ev.dataTransfer.effectAllowed = "copy";
        ev.dataTransfer.setData("application/x-mo-studio-field-type", type);
        ev.dataTransfer.setData("text/plain", `new:${type}`);
        this.state.draggingFieldName = null;
    }

    startFieldDrag(ev, field) {
        ev.stopPropagation();
        this.selectExistingField(field);
        ev.dataTransfer.effectAllowed = "move";
        ev.dataTransfer.setData("application/x-mo-studio-existing-field", field.name);
        ev.dataTransfer.setData("text/plain", `existing:${field.name}`);
        this.state.draggingFieldName = field.name;
    }

    async dropField(ev, afterFieldName = null) {
        ev.preventDefault();
        ev.stopPropagation();
        const existing = ev.dataTransfer.getData("application/x-mo-studio-existing-field");
        if (existing) {
            await this.moveField(existing, afterFieldName);
            return;
        }
        const type = ev.dataTransfer.getData("application/x-mo-studio-field-type") || this.state.selectedTool;
        await this.createFieldAt(type, afterFieldName);
    }

    async moveField(fieldName, afterFieldName = null) {
        if (!fieldName || fieldName === afterFieldName) {
            return;
        }
        this.state.formFieldOrder = this.insertNameAfter(this.state.formFieldOrder || [], fieldName, afterFieldName);
        this.state.dirty = true;
        this.state.busy = true;
        try {
            const data = await this.orm.call("mo.studio.builder.app", "move_field_in_view", [
                this.state.model,
                fieldName,
                afterFieldName,
                this.state.viewType || "form",
            ]);
            this.state.fields = data.fields;
            this.state.formFieldOrder = data.form_field_order || this.state.formFieldOrder;
            this.state.views = data.views;
            this.notification.add("Field moved in the preview.", { type: "success" });
        } finally {
            this.state.busy = false;
            this.state.draggingFieldName = null;
        }
    }

    async removeField(fieldName) {
        this.state.busy = true;
        try {
            const data = await this.orm.call("mo.studio.builder.app", "remove_field_from_model", [
                this.state.model,
                fieldName,
            ]);
            this.state.fields = data.fields;
            this.state.selectedField = null;
            this.state.dirty = true;
            this.notification.add("Field removed from the preview.", { type: "success" });
        } finally {
            this.state.busy = false;
        }
    }

    async updateSelectedField() {
        if (!this.state.selectedField) {
            return;
        }
        this.state.busy = true;
        try {
            const data = await this.orm.call("mo.studio.builder.app", "update_field_on_model", [
                this.state.model,
                this.state.selectedField.name,
                {
                    ...this.state.selectedField,
                    technical_name: this.state.selectedField.technical_name || this.state.selectedField.name,
                },
            ]);
            this.state.fields = data.fields;
            const refreshed = data.fields.find((field) => field.name === this.state.selectedField.name);
            this.state.selectedField = refreshed || null;
            this.state.dirty = true;
            this.notification.add("Field properties updated in the preview.", { type: "success" });
        } finally {
            this.state.busy = false;
        }
    }

    async addSelectedFieldToView(viewType = this.state.viewType, afterFieldName = null) {
        if (!this.state.selectedField) {
            return;
        }
        this.state.busy = true;
        try {
            const data = await this.orm.call("mo.studio.builder.app", "add_existing_field_to_view", [
                this.state.model,
                this.state.selectedField.name,
                viewType,
                afterFieldName,
            ]);
            this.state.views = data.views;
            this.state.formFieldOrder = data.form_field_order || this.state.formFieldOrder;
            this.state.dirty = true;
            this.notification.add(`Field added to ${viewType} preview.`, { type: "success" });
        } finally {
            this.state.busy = false;
        }
    }

    async doBackendAction(method) {
        const panels = {
            open_model_fields_action: "fields",
            open_model_views_action: "views",
            open_model_automations_action: "automations",
            open_model_access_action: "access",
            open_model_reports_action: "reports",
        };
        this.state.panel = panels[method] || "properties";
    }

    async openFields() {
        await this.doBackendAction("open_model_fields_action");
    }

    async openViews() {
        await this.doBackendAction("open_model_views_action");
    }

    async openAutomations() {
        await this.doBackendAction("open_model_automations_action");
    }

    async openAccess() {
        await this.doBackendAction("open_model_access_action");
    }

    async openReports() {
        await this.doBackendAction("open_model_reports_action");
    }

    async updatePage() {
        this.state.busy = true;
        try {
            await this.loadContext();
            this.state.dirty = false;
            this.notification.add("App updated.", { type: "success" });
            window.location.reload();
        } finally {
            this.state.busy = false;
        }
    }

    reloadPage() {
        window.location.reload();
    }

    previewValue(field) {
        const values = {
            boolean: "[ ]",
            date: "2026-07-12",
            datetime: "2026-07-12 14:30:00",
            integer: "0",
            float: "0.00",
            monetary: "0.00",
            many2one: "Record",
            many2many: "Tag",
            selection: "Yes",
            binary: "Upload file",
            html: "Text block",
            text: "Multiline text",
        };
        return values[field.ttype] || "";
    }
}
StudioPageEditorDialog.template = "mo_studio_builder.PageEditorDialog";
StudioPageEditorDialog.components = { Dialog };
StudioPageEditorDialog.props = {
    close: Function,
    model: String,
    viewType: { type: String, optional: true },
};

patch(NavBar.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    },

    canUseStudioBuilder() {
        return session.mo_studio_builder_access === true;
    },

    openStudioBuilder() {
        if (session.mo_studio_builder_access !== true) {
            this.notification.add("You do not have MO Studio Builder access.", { type: "warning" });
            return;
        }
        const controller = this.actionService.currentController;
        const props = controller && controller.props;
        const action = controller && controller.action;
        const model = props?.resModel || props?.res_model || action?.res_model || action?.resModel;
        const viewType = props?.type || props?.viewType || action?.view_mode?.split(",")?.[0] || "form";
        if (!model) {
            this.notification.add("Open any model page first, then start Studio.", { type: "warning" });
            return;
        }
        this.dialog.add(StudioPageEditorDialog, { model, viewType });
    },
});
