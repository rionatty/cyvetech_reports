// Copyright (c) 2026, Cyvetech and contributors
// For license information, please see license.txt

frappe.query_reports["Item List Report"] = {

    filters: [
        // -- Core Filters --------------------------------------
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1
        },
        {
            fieldname: "item_group",
            label: __("Item Group"),
            fieldtype: "Link",
            options: "Item Group"
        },
        {
            fieldname: "item_name",
            label: __("Item Name"),
            fieldtype: "Data"
        },
        {
            fieldname: "disabled",
            label: __("Show Disabled Items"),
            fieldtype: "Check",
            default: 0
        },
        {
            fieldname: "is_sales_item",
            label: __("Sales Items Only"),
            fieldtype: "Check",
            default: 0
        },
        {
            fieldname: "is_purchase_item",
            label: __("Purchase Items Only"),
            fieldtype: "Check",
            default: 0
        },
        {
            fieldname: "is_stock_item",
            label: __("Stock Items Only"),
            fieldtype: "Check",
            default: 0
        },

        // -- Extra Columns Selector ----------------------------
        {
            fieldname: "extra_columns",
            label: __("Extra Columns"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                const options = [
                    { value: "selling_price", description: "Selling Price" },
                    { value: "qty_on_hand",   description: "Current Stock (Qty on Hand)" },
                    { value: "brand",         description: "Brand" },
                    { value: "description",   description: "Description" }
                ];
                return options.filter(o =>
                    !txt || o.description.toLowerCase().includes(txt.toLowerCase())
                );
            }
        },

        // -- Price List (only relevant if selling_price selected) --
        {
            fieldname: "price_list",
            label: __("Price List"),
            fieldtype: "Link",
            options: "Price List",
            default: "Standard Selling",
            depends_on: "eval:frappe.query_report.get_filter_value('extra_columns') && frappe.query_report.get_filter_value('extra_columns').includes('selling_price')"
        }
    ],

    // -- Formatter ---------------------------------------------
    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (data && data.is_group_row) {
            return `<strong style="color:#2b6cb0; font-size:10pt;">
                        &#9658; ${data.display_name || ""}
                    </strong>`;
        }

        if (column.fieldname === "selling_price" && data && !data.is_group_row) {
            value = `<span style="color:#276749; font-weight:600;">${value}</span>`;
        }

        if (column.fieldname === "qty_on_hand" && data && !data.is_group_row) {
            const qty = parseFloat(data.qty_on_hand) || 0;
            const color = qty <= 0 ? "#e53e3e" : "#276749";
            value = `<span style="color:${color}; font-weight:600;">${value}</span>`;
        }

        return value;
    },

    // -- On Load -----------------------------------------------
    onload: function(report) {

        // -- Print PDF Button ----------------------------------
        report.page.add_inner_button(__("Print PDF"), function() {
            const filters = report.get_values();
            const data    = report.data || [];

            if (!data.length) {
                frappe.msgprint(__("Please run the report first."));
                return;
            }

            frappe.call({
                method: "cyvetech_reports.cyvetech_reports.report.item_list_report.item_list_report.get_pdf_html",
                args: {
                    filters: JSON.stringify(filters),
                    data   : JSON.stringify(data)
                },
                freeze        : true,
                freeze_message: __("Generating PDF..."),
                callback: function(r) {
                    if (r.message) {
                        const w = window.open();
                        w.document.write(r.message);
                        w.document.close();
                        setTimeout(() => w.print(), 700);
                    }
                }
            });
        }).addClass("btn-primary");
    }
};