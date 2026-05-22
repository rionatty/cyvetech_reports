// Copyright (c) 2026, Cyvetech and contributors
// For license information, please see license.txt

frappe.query_reports["General Ledger Print"] = {
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
            fieldname: "account",
            label: __("Account"),
            fieldtype: "Link",
            options: "Account",
            get_query: function() {
                return {
                    filters: {
                        company: frappe.query_report.get_filter_value("company")
                    }
                };
            }
        },
        {
            fieldname: "party_type",
            label: __("Party Type"),
            fieldtype: "Link",
            options: "Party Type"
        },
        {
            fieldname: "party",
            label: __("Party"),
            fieldtype: "Dynamic Link",
            options: "party_type"
        },
        {
            fieldname: "cost_center",
            label: __("Cost Center"),
            fieldtype: "Link",
            options: "Cost Center"
        },
        {
            fieldname: "project",
            label: __("Project"),
            fieldtype: "Link",
            options: "Project"
        },
        {
            fieldname: "voucher_no",
            label: __("Voucher No"),
            fieldtype: "Data"
        }
    ],

    onload: function(report) {
        report.page.add_inner_button(__("Print PDF"), function() {
            const filters = report.get_values();
            const data    = report.data || [];

            if (!data.length) {
                frappe.msgprint(__("Please run the report first."));
                return;
            }

            frappe.call({
                method: "cyvetech_reports.cyvetech_reports.report.general_ledger_print.general_ledger_print.get_pdf_html",
                args: {
                    filters: JSON.stringify(filters),
                    data   : JSON.stringify(data)
                },
                freeze        : true,
                freeze_message: __("Generating PDF..."),
                callback: function(r) {
                    if (r && r.message) {
                        const w = window.open("", "_blank");
                        if (w) {
                            w.document.write(r.message);
                            w.document.close();
                            setTimeout(() => w.print(), 800);
                        } else {
                            frappe.msgprint(__("Popup blocked! Please allow popups."));
                        }
                    }
                }
            });
        }).addClass("btn-primary");
    }
};