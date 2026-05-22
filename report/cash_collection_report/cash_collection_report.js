// Copyright (c) 2026, Cyvetech and contributors
// For license information, please see license.txt

frappe.query_reports["Cash Collection Report"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_start(),
            reqd: 1
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.now_date(),
            reqd: 1
        },
        {
            fieldname: "group_by",
            label: __("Group By"),
            fieldtype: "Select",
            options: "Detailed\nRoute\nCustomer\nMode of Payment\nDate\nCollected By",
            default: "Detailed"
        },
        {
            fieldname: "sales_person",
            label: __("Route / Sales Person"),
            fieldtype: "Link",
            options: "Sales Person"
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer"
        },
        {
            fieldname: "customer_group",
            label: __("Customer Group"),
            fieldtype: "Link",
            options: "Customer Group"
        },
        {
            fieldname: "mode_of_payment",
            label: __("Mode of Payment"),
            fieldtype: "Link",
            options: "Mode of Payment"
        },
        {
            fieldname: "cash_account",
            label: __("Cash / Bank Account"),
            fieldtype: "Link",
            options: "Account",
            get_query: function () {
                const company = frappe.query_report.get_filter_value("company");
                return {
                    filters: {
                        account_type: ["in", ["Cash", "Bank"]],
                        company: company,
                        is_group: 0
                    }
                };
            }
        },
        {
            fieldname: "collected_by",
            label: __("Collected By (User)"),
            fieldtype: "Link",
            options: "User"
        },
        {
            fieldname: "include_unallocated",
            label: __("Include Unallocated Payments"),
            fieldtype: "Check",
            default: 1
        }
    ],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "amount" && flt(data?.amount) > 0) {
            value = `<span style="color:#2f855a;font-weight:600">${value}</span>`;
        }
        return value;
    },

    onload: function (report) {
        report.page.add_inner_button(__("Print PDF"), function () {
            const filters = report.get_values();
            const data = report.data || [];

            if (!data.length) {
                frappe.msgprint(__("Run the report first."));
                return;
            }

            frappe.call({
                method: "cyvetech_reports.cyvetech_reports.report.cash_collection_report.cash_collection_report.get_pdf_html",
                args: {
                    filters: JSON.stringify(filters),
                    data: JSON.stringify(data)
                },
                freeze: true,
                freeze_message: __("Generating PDF..."),
                callback: function (r) {
                    if (r.message) {
                        const w = window.open();
                        w.document.write(r.message);
                        w.document.close();
                        setTimeout(() => w.print(), 600);
                    }
                }
            });
        }).addClass("btn-primary");
    }
};