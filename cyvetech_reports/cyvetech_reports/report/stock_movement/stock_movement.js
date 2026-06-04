// Copyright (c) 2024, Your Company and contributors
// For license information, please see license.txt

// Module-level state for Monthly expand/collapse.
// Lives outside the report config so it survives re-renders.
const _sm_state = {
    all_data: null,   // full server data (group + item rows)
    expanded: new Set()  // which month labels are currently expanded
};

frappe.query_reports["Stock Movement"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "group_by",
            "label": __("Group By"),
            "fieldtype": "Select",
            "options": "Summary\nMonthly",
            "default": "Summary"
        },
        {
            "fieldname": "warehouse",
            "label": __("Warehouse"),
            "fieldtype": "Link",
            "options": "Warehouse",
            "get_query": function() {
                let company = frappe.query_report.get_filter_value('company');
                return {
                    filters: { 'company': company, 'is_group': 0 }
                };
            }
        },
        {
            "fieldname": "item_group",
            "label": __("Item Group"),
            "fieldtype": "Link",
            "options": "Item Group"
        },
        {
            "fieldname": "item_code",
            "label": __("Item"),
            "fieldtype": "Link",
            "options": "Item",
            "get_query": function() {
                return {
                    query: "erpnext.controllers.queries.item_query"
                };
            }
        },
        {
            "fieldname": "brand",
            "label": __("Brand"),
            "fieldtype": "Link",
            "options": "Brand"
        },
        {
            "fieldname": "show_zero_balance",
            "label": __("Show Items With Zero Movement"),
            "fieldtype": "Check",
            "default": 0
        }
    ],

    // ----------------------------------------------------------------
    // FORMATTER
    // ----------------------------------------------------------------
    "formatter": function(value, row, column, data, default_formatter) {
        // ── Monthly group (header) row ───────────────────────────────
        if (data && data.is_group) {
            if (column.fieldname === "month") {
                const expanded = _sm_state.expanded && _sm_state.expanded.has(data.month);
                const icon = expanded ? "▼" : "▶";
                const safe = frappe.utils.escape_html(data.month || "");
                const key  = (data.month || "").replace(/"/g, "&quot;");
                return (
                    '<span class="sm-month-toggle" data-month="' + key + '" '
                    + 'style="cursor:pointer;font-weight:700;color:#2b6cb0;'
                    + 'font-size:9.5pt;letter-spacing:0.2px;">'
                    + icon + "&nbsp;&nbsp;" + safe
                    + "</span>"
                );
            }
            // All other cells on a group row: bold totals, empty for null
            value = default_formatter(value, row, column, data);
            return (value !== null && value !== undefined && String(value).trim() !== "")
                ? "<strong>" + value + "</strong>"
                : "";
        }

        // ── Monthly item row — suppress the month column (group shows it) ─
        if (data && data.is_group === 0 && column.fieldname === "month") {
            return "";
        }

        // ── Regular formatting ────────────────────────────────────────
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "closing_qty" && data && data.closing_qty < 0) {
            return "<span style='color:red'>" + value + "</span>";
        }
        if (column.fieldname === "in_qty" && data && data.in_qty > 0) {
            return "<span style='color:green'>" + value + "</span>";
        }
        if (column.fieldname === "valuation_rate" && data && !data.valuation_rate) {
            return "<span style='color:#718096'>-</span>";
        }
        return value;
    },

    // ----------------------------------------------------------------
    // AFTER DATATABLE RENDER
    // Fires once per fresh server response (not on datatable.refresh() calls).
    // We use it to store the full data and collapse to group rows only.
    // ----------------------------------------------------------------
    "after_datatable_render": function(datatable) {
        const report = frappe.query_report;
        const is_monthly = (report.get_filter_value("group_by") || "Summary") === "Monthly";

        if (!is_monthly) {
            // Reset state when switching away from Monthly
            _sm_state.all_data = null;
            _sm_state.expanded = new Set();
            return;
        }

        // Fresh server data contains both group rows (is_group=1) and item rows
        // (is_group=0).  Detect that so we don't re-process our own refreshes.
        const data = report.data || [];
        const hasItems = data.some(r => r.is_group === 0);
        if (!hasItems) return;   // already collapsed — skip

        // Store the full set and reset expansion
        _sm_state.all_data = data.slice();
        _sm_state.expanded = new Set();

        // Show only month group rows (collapsed view)
        const collapsed = data.filter(r => r.is_group);
        report.data = collapsed;
        datatable.refresh(collapsed, report.columns);
    },

    // ----------------------------------------------------------------
    // ON LOAD
    // ----------------------------------------------------------------
    onload: function(report) {

        // ── Expand / collapse click handler ──────────────────────────
        // Delegated on the report wrapper so it survives datatable re-renders.
        $(report.wrapper).on("click", ".sm-month-toggle", function(e) {
            e.stopPropagation();

            if (!_sm_state.all_data) return;

            const month = $(this).data("month");
            if (_sm_state.expanded.has(month)) {
                _sm_state.expanded.delete(month);
            } else {
                _sm_state.expanded.add(month);
            }

            // Rebuild visible rows: all group headers + items of expanded months
            const visible = _sm_state.all_data.filter(
                r => r.is_group || _sm_state.expanded.has(r.month)
            );

            report.data = visible;
            report.datatable.refresh(visible, report.columns);
        });

        // ── Print PDF button ─────────────────────────────────────────
        // Sends exactly what the user currently sees:
        //   • collapsed → only month summary rows
        //   • partially expanded → summary rows + item rows for expanded months
        //   • fully expanded → all rows
        report.page.add_inner_button(__("Print PDF"), function() {
            const filters = report.get_filter_values();
            const data    = report.data || [];

            if (!data.length) {
                frappe.msgprint(__("Please run the report first"));
                return;
            }

            frappe.call({
                method: "cyvetech_reports.cyvetech_reports.report.stock_movement.stock_movement.get_pdf_html",
                args: { filters: filters, data: data },
                freeze: true,
                freeze_message: __("Generating PDF…"),
                callback: function(r) {
                    if (r.message) {
                        const w = window.open("", "_blank");
                        w.document.write(r.message);
                        w.document.close();
                        setTimeout(() => w.print(), 500);
                    }
                }
            });
        });
    }
};
