// Copyright (c) 2024, Your Company and contributors
// For license information, please see license.txt

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

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname == "closing_qty" && data && data.closing_qty < 0) {
            value = `<span style="color:red">${value}</span>`;
        }
        if (column.fieldname == "in_qty" && data && data.in_qty > 0) {
            value = `<span style="color:green">${value}</span>`;
        }
        if (column.fieldname == "valuation_rate" && data && !data.valuation_rate) {
            value = `<span style="color:#718096">-</span>`;
        }
        return value;
    },

    onload: function(report) {
        report.page.add_inner_button(__("Print PDF"), function() {
            let filters = report.get_filter_values();
            let data = report.data || [];

            if (!data.length) {
                frappe.msgprint(__("Please run the report first"));
                return;
            }

            frappe.call({
                method: "cyvetech_reports.cyvetech_reports.report.stock_movement.stock_movement.get_pdf_html",
                args: {
                    filters: filters,
                    data: data
                },
                callback: function(r) {
                    if (r.message) {
                        let print_window = window.open("", "_blank");
                        print_window.document.write(r.message);
                        print_window.document.close();
                        print_window.focus();
                        setTimeout(() => {
                            print_window.print();
                        }, 500);
                    }
                }
            });
        });
    }
};