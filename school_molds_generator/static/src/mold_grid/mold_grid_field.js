import { Component, onWillUnmount, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class SchoolMoldGridField extends Component {
    static template = "school_molds_generator.MoldGridField";
    static props = { ...standardFieldProps };

    setup() {
        this.state = useState({
            columns: [],
            rows: [],
            expanded: false,
            zoom: 130,
        });
        this.zoomMin = 70;
        this.zoomMax = 230;
        this.zoomStep = 15;
        useRecordObserver((record) => {
            this.state.columns = this._readColumns(record);
            this.state.rows = this._readRows(record);
        });
        onWillUnmount(() => this._setExpanded(false));
    }

    get moldRecord() {
        return this.props.record;
    }

    get lineList() {
        return this.moldRecord.data[this.props.name];
    }

    get expandLabel() {
        return this.state.expanded ? _t("Exit Fullscreen") : _t("Expand Sheet");
    }

    _setExpanded(expanded) {
        this.state.expanded = expanded;
        document.body.classList.toggle("o_school_mold_fullscreen", expanded);
    }

    toggleExpanded() {
        this._setExpanded(!this.state.expanded);
    }

    get zoomLabel() {
        return `${this.state.zoom}%`;
    }

    get zoomWrapStyle() {
        return `width: ${this.state.zoom}%;`;
    }

    get canZoomOut() {
        return this.state.zoom > this.zoomMin;
    }

    get canZoomIn() {
        return this.state.zoom < this.zoomMax;
    }

    zoomIn() {
        this.state.zoom = Math.min(this.zoomMax, this.state.zoom + this.zoomStep);
    }

    zoomOut() {
        this.state.zoom = Math.max(this.zoomMin, this.state.zoom - this.zoomStep);
    }

    resetZoom() {
        this.state.zoom = 100;
    }

    _readColumns(record) {
        const payload = record.data.column_payload;
        if (Array.isArray(payload) && payload.length) {
            return payload.map((col) => ({
                key: col.key,
                name: col.name,
                groupName: col.group_name || "",
                colType: col.col_type,
                color: col.color || "#FFFFFF",
                maxValue: col.max_value,
            }));
        }
        const columns = record.data.column_ids;
        if (!columns) {
            return [];
        }
        return columns.records
            .slice()
            .sort((a, b) => (a.data.sequence || 0) - (b.data.sequence || 0))
            .map((col) => ({
                id: col.id,
                key: col.data.key,
                name: col.data.name,
                groupName: col.data.group_name || "",
                colType: col.data.col_type,
                color: col.data.color || "#FFFFFF",
                maxValue: col.data.max_value,
                record: col,
            }));
    }

    _readRows(record) {
        const lines = record.data[this.props.name];
        if (!lines) {
            return [];
        }
        const columns = this._readColumns(record);
        return lines.records.map((line) => {
            const values = line.data.values_json || {};
            const cells = {};
            for (const column of columns) {
                cells[column.key] = this._displayValue(line, column, values);
            }
            return {
                id: line.id,
                sequence: line.data.sequence,
                studentName: line.data.student_name || "",
                values,
                cells,
                record: line,
            };
        });
    }

    _toNumber(value) {
        if (value === "" || value === null || value === undefined || value === false) {
            return null;
        }
        const number = Number(value);
        return Number.isNaN(number) ? null : number;
    }

    _sumKeys(values, keys) {
        let total = 0;
        let hasValue = false;
        for (const key of keys) {
            const number = this._toNumber(values[key]);
            if (number === null) {
                continue;
            }
            total += number;
            hasValue = true;
        }
        if (!hasValue) {
            return "";
        }
        return Number.isInteger(total) ? total : Number(total.toFixed(2));
    }

    _computedValue(column, values, columns) {
        if (column.colType === "subtotal") {
            return this._sumKeys(
                values,
                columns
                    .filter((col) => col.colType === "score" && col.groupName === column.groupName)
                    .map((col) => col.key)
            );
        }
        if (column.colType === "total") {
            return this._sumKeys(
                values,
                columns
                    .filter((col) => col.colType === "score" && !col.groupName)
                    .map((col) => col.key)
            );
        }
        if (column.colType === "grand_total") {
            const subtotal = columns
                .filter((col) => col.colType === "subtotal")
                .reduce((sum, col) => sum + (this._toNumber(this._computedValue(col, values, columns)) || 0), 0);
            const summary = this._toNumber(
                this._computedValue({ colType: "total" }, values, columns)
            ) || 0;
            const total = subtotal + summary;
            if (!subtotal && !summary) {
                return 0;
            }
            return Number.isInteger(total) ? total : Number(total.toFixed(2));
        }
        return "";
    }

    _displayValue(line, column, values) {
        if (column.colType === "serial") {
            return line.data.sequence || 0;
        }
        if (column.colType === "name") {
            return line.data.student_name || "";
        }
        if (["subtotal", "total", "grand_total"].includes(column.colType)) {
            return this._computedValue(column, values, this.state.columns.length ? this.state.columns : this._readColumns(this.moldRecord));
        }
        const raw = values[column.key];
        return raw === undefined || raw === null || raw === false ? "" : raw;
    }

    headerLabel(column) {
        return column.name;
    }

    isIdentity(column) {
        return ["serial", "seat_number", "pin_number", "name", "class"].includes(column.colType);
    }

    isReadonly(column) {
        return ["serial", "subtotal", "total", "grand_total"].includes(column.colType);
    }

    async onNameChange(row, event) {
        await row.record.update({ student_name: event.target.value });
    }

    async onScoreChange(row, column, event) {
        const raw = event.target.value;
        const values = { ...(row.record.data.values_json || {}) };
        if (raw === "") {
            delete values[column.key];
        } else {
            const number = this._toNumber(raw);
            values[column.key] = number === null ? raw : number;
        }
        const columns = this.state.columns;
        for (const col of columns) {
            if (["subtotal", "total", "grand_total"].includes(col.colType)) {
                values[col.key] = this._computedValue(col, values, columns);
            }
        }
        await row.record.update({ values_json: values });
    }

    async addRow() {
        const nextSequence = this.state.rows.reduce(
            (max, row) => Math.max(max, row.sequence || 0),
            0
        ) + 1;
        const record = await this.lineList.addNewRecord({ position: "bottom" });
        await record.update({ sequence: nextSequence, values_json: {} });
    }

    async removeRow(row) {
        await this.lineList.delete(row.record);
    }
}

export const schoolMoldGridField = {
    component: SchoolMoldGridField,
    displayName: _t("School Mold Grid"),
    supportedTypes: ["one2many"],
};

registry.category("fields").add("school_mold_grid", schoolMoldGridField);
