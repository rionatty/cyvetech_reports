# -*- coding: utf-8 -*-
# Copyright (c) 2026, Cyvetech and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from frappe.utils import (
    flt, getdate, fmt_money, formatdate,
    format_datetime, get_datetime
)


def execute(filters=None):
    filters = filters or {}
    validate_filters(filters)

    columns = get_columns(filters)
    data = get_data(filters)
    report_summary = get_report_summary(data)
    chart = get_chart_data(data, filters)

    return columns, data, None, chart, report_summary


def validate_filters(filters):
    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw(_("From Date and To Date are mandatory"))
    if getdate(filters.get("from_date")) > getdate(filters.get("to_date")):
        frappe.throw(_("From Date cannot be greater than To Date"))
    if not filters.get("company"):
        frappe.throw(_("Company is mandatory"))


# ============================================================
# COLUMNS
# ============================================================

def get_columns(filters):
    group_by = filters.get("group_by") or "Detailed"

    if group_by == "Route":
        return [
            {"label": _("Route"), "fieldname": "sales_person", "fieldtype": "Link",
             "options": "Sales Person", "width": 220},
            {"label": _("Receipts"), "fieldname": "receipt_count",
             "fieldtype": "Int", "width": 100},
            {"label": _("Customers"), "fieldname": "customer_count",
             "fieldtype": "Int", "width": 100},
            {"label": _("Total Collected"), "fieldname": "amount",
             "fieldtype": "Currency", "width": 160},
            {"label": _("Avg per Receipt"), "fieldname": "avg_amount",
             "fieldtype": "Currency", "width": 160},
        ]

    if group_by == "Customer":
        return [
            {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link",
             "options": "Customer", "width": 160},
            {"label": _("Customer Name"), "fieldname": "customer_name",
             "fieldtype": "Data", "width": 200},
            {"label": _("Group"), "fieldname": "customer_group", "fieldtype": "Link",
             "options": "Customer Group", "width": 130},
            {"label": _("Receipts"), "fieldname": "receipt_count",
             "fieldtype": "Int", "width": 90},
            {"label": _("Total Collected"), "fieldname": "amount",
             "fieldtype": "Currency", "width": 160},
            {"label": _("Last Collection"), "fieldname": "last_date",
             "fieldtype": "Date", "width": 120},
        ]

    if group_by == "Mode of Payment":
        return [
            {"label": _("Mode of Payment"), "fieldname": "mode_of_payment",
             "fieldtype": "Link", "options": "Mode of Payment", "width": 200},
            {"label": _("Receipts"), "fieldname": "receipt_count",
             "fieldtype": "Int", "width": 100},
            {"label": _("Customers"), "fieldname": "customer_count",
             "fieldtype": "Int", "width": 110},
            {"label": _("Total Collected"), "fieldname": "amount",
             "fieldtype": "Currency", "width": 170},
        ]

    if group_by == "Date":
        return [
            {"label": _("Date"), "fieldname": "posting_date",
             "fieldtype": "Date", "width": 120},
            {"label": _("Receipts"), "fieldname": "receipt_count",
             "fieldtype": "Int", "width": 100},
            {"label": _("Customers"), "fieldname": "customer_count",
             "fieldtype": "Int", "width": 110},
            {"label": _("Total Collected"), "fieldname": "amount",
             "fieldtype": "Currency", "width": 170},
        ]

    if group_by == "Collected By":
        return [
            {"label": _("Collected By"), "fieldname": "collected_by",
             "fieldtype": "Link", "options": "User", "width": 220},
            {"label": _("Employee Name"), "fieldname": "collector_name",
             "fieldtype": "Data", "width": 180},
            {"label": _("Receipts"), "fieldname": "receipt_count",
             "fieldtype": "Int", "width": 100},
            {"label": _("Total Collected"), "fieldname": "amount",
             "fieldtype": "Currency", "width": 170},
        ]

    # DETAILED
    return [
        {"label": _("Date"), "fieldname": "posting_date",
         "fieldtype": "Date", "width": 95},
        {"label": _("Payment Entry"), "fieldname": "payment_entry",
         "fieldtype": "Link", "options": "Payment Entry", "width": 150},
        {"label": _("Customer"), "fieldname": "customer",
         "fieldtype": "Link", "options": "Customer", "width": 140},
        {"label": _("Customer Name"), "fieldname": "customer_name",
         "fieldtype": "Data", "width": 170},
        {"label": _("Route"), "fieldname": "sales_person",
         "fieldtype": "Link", "options": "Sales Person", "width": 130},
        {"label": _("Mode"), "fieldname": "mode_of_payment",
         "fieldtype": "Link", "options": "Mode of Payment", "width": 110},
        {"label": _("Cash A/c"), "fieldname": "cash_account",
         "fieldtype": "Link", "options": "Account", "width": 200},
        {"label": _("Reference"), "fieldname": "reference_no",
         "fieldtype": "Data", "width": 130},
        {"label": _("Ref Date"), "fieldname": "reference_date",
         "fieldtype": "Date", "width": 95},
        {"label": _("Against Invoice"), "fieldname": "against_invoice",
         "fieldtype": "Link", "options": "Sales Invoice", "width": 140},
        {"label": _("Allocated"), "fieldname": "allocated_amount",
         "fieldtype": "Currency", "width": 120},
        {"label": _("Amount"), "fieldname": "amount",
         "fieldtype": "Currency", "width": 130},
        {"label": _("Collected By"), "fieldname": "collected_by",
         "fieldtype": "Link", "options": "User", "width": 150},
        {"label": _("Remarks"), "fieldname": "remarks",
         "fieldtype": "Data", "width": 200},
    ]


# ============================================================
# DATA FETCHING
# ============================================================

def build_conditions(filters):
    conditions = """
        pe.docstatus = 1
        AND pe.payment_type = 'Receive'
        AND pe.party_type = 'Customer'
        AND pe.posting_date BETWEEN %(from_date)s AND %(to_date)s
    """
    params = {
        "from_date": getdate(filters.get("from_date")),
        "to_date": getdate(filters.get("to_date")),
    }

    if filters.get("company"):
        conditions += " AND pe.company = %(company)s "
        params["company"] = filters.get("company")

    if filters.get("customer"):
        conditions += " AND pe.party = %(customer)s "
        params["customer"] = filters.get("customer")

    if filters.get("mode_of_payment"):
        conditions += " AND pe.mode_of_payment = %(mode_of_payment)s "
        params["mode_of_payment"] = filters.get("mode_of_payment")

    if filters.get("cash_account"):
        conditions += " AND pe.paid_to = %(cash_account)s "
        params["cash_account"] = filters.get("cash_account")

    if filters.get("collected_by"):
        conditions += " AND pe.owner = %(collected_by)s "
        params["collected_by"] = filters.get("collected_by")

    return conditions, params


def get_raw_data(filters):
    conditions, params = build_conditions(filters)
    include_unallocated = filters.get("include_unallocated")

    pe_query = """
        SELECT
            pe.name                  AS payment_entry,
            pe.posting_date          AS posting_date,
            pe.party                 AS customer,
            pe.party_name            AS customer_name,
            pe.mode_of_payment       AS mode_of_payment,
            pe.paid_to               AS cash_account,
            pe.paid_amount           AS amount,
            pe.received_amount       AS received_amount,
            pe.reference_no          AS reference_no,
            pe.reference_date        AS reference_date,
            pe.remarks               AS remarks,
            pe.owner                 AS collected_by,
            cust.customer_group      AS customer_group,
            cust.territory           AS territory
        FROM `tabPayment Entry` pe
        LEFT JOIN `tabCustomer` cust ON cust.name = pe.party
        WHERE {conditions}
        ORDER BY pe.posting_date, pe.name
    """.format(conditions=conditions)

    pe_rows = frappe.db.sql(pe_query, params, as_dict=1) or []
    if not pe_rows:
        return []

    pe_names = tuple(set([r.payment_entry for r in pe_rows]))

    # Get allocations
    allocations_map = {}
    if pe_names:
        alloc_rows = frappe.db.sql("""
            SELECT
                per.parent              AS payment_entry,
                per.reference_doctype   AS reference_doctype,
                per.reference_name      AS reference_name,
                per.allocated_amount    AS allocated_amount,
                per.outstanding_amount  AS outstanding_amount
            FROM `tabPayment Entry Reference` per
            WHERE per.parent IN %(names)s
              AND per.reference_doctype = 'Sales Invoice'
        """, {"names": pe_names}, as_dict=1) or []

        for ar in alloc_rows:
            allocations_map.setdefault(ar.payment_entry, []).append(ar)

    # Get sales person from invoices
    sales_person_map = {}
    all_invoices = []
    for allocs in allocations_map.values():
        for a in allocs:
            if a.reference_name:
                all_invoices.append(a.reference_name)

    if all_invoices:
        sp_rows = frappe.db.sql("""
            SELECT
                st.parent AS invoice,
                st.sales_person,
                st.allocated_percentage
            FROM `tabSales Team` st
            WHERE st.parent IN %(invoices)s
              AND st.parenttype = 'Sales Invoice'
        """, {"invoices": tuple(set(all_invoices))}, as_dict=1) or []

        for sp in sp_rows:
            sales_person_map.setdefault(sp.invoice, []).append({
                "sales_person": sp.sales_person,
                "allocated_percentage": flt(sp.allocated_percentage)
            })

    # Get collector name from Employee
    user_ids = list(set([r.collected_by for r in pe_rows if r.collected_by]))
    collector_map = {}
    if user_ids:
        emps = frappe.db.sql("""
            SELECT user_id, employee_name
            FROM `tabEmployee`
            WHERE user_id IN %(users)s
        """, {"users": tuple(user_ids)}, as_dict=1) or []
        for e in emps:
            collector_map[e.user_id] = e.employee_name

    # Build flat rows
    rows = []
    for pe in pe_rows:
        collector_name = collector_map.get(pe.collected_by, pe.collected_by or "")
        allocs = allocations_map.get(pe.payment_entry, [])

        if not allocs:
            if not include_unallocated:
                continue
            rows.append({
                "payment_entry": pe.payment_entry,
                "posting_date": pe.posting_date,
                "customer": pe.customer,
                "customer_name": pe.customer_name,
                "customer_group": pe.customer_group,
                "mode_of_payment": pe.mode_of_payment,
                "cash_account": pe.cash_account,
                "amount": flt(pe.amount),
                "allocated_amount": 0,
                "reference_no": pe.reference_no,
                "reference_date": pe.reference_date,
                "remarks": pe.remarks or "",
                "collected_by": pe.collected_by,
                "collector_name": collector_name,
                "against_invoice": "",
                "sales_person": "Unassigned",
            })
            continue

        for alloc in allocs:
            sps = sales_person_map.get(alloc.reference_name, [])
            if not sps:
                sps = [{"sales_person": "Unassigned", "allocated_percentage": 100}]

            for sp in sps:
                pct = flt(sp.get("allocated_percentage")) / 100.0
                rows.append({
                    "payment_entry": pe.payment_entry,
                    "posting_date": pe.posting_date,
                    "customer": pe.customer,
                    "customer_name": pe.customer_name,
                    "customer_group": pe.customer_group,
                    "mode_of_payment": pe.mode_of_payment,
                    "cash_account": pe.cash_account,
                    "amount": flt(alloc.allocated_amount) * pct,
                    "allocated_amount": flt(alloc.allocated_amount) * pct,
                    "reference_no": pe.reference_no,
                    "reference_date": pe.reference_date,
                    "remarks": pe.remarks or "",
                    "collected_by": pe.collected_by,
                    "collector_name": collector_name,
                    "against_invoice": alloc.reference_name,
                    "sales_person": sp.get("sales_person") or "Unassigned",
                })

    # Post-fetch filters
    if filters.get("sales_person"):
        rows = [r for r in rows if r.get("sales_person") == filters.get("sales_person")]

    if filters.get("customer_group"):
        rows = [r for r in rows if r.get("customer_group") == filters.get("customer_group")]

    return rows


def get_data(filters):
    raw = get_raw_data(filters)
    if not raw:
        return []

    group_by = filters.get("group_by") or "Detailed"

    if group_by == "Detailed":
        return raw
    if group_by == "Route":
        return build_grouped(raw, key_field="sales_person")
    if group_by == "Customer":
        return build_grouped(raw, key_field="customer", label_field="customer_name",
                             extra_fields=["customer_group"], track_last_date=True)
    if group_by == "Mode of Payment":
        return build_grouped(raw, key_field="mode_of_payment")
    if group_by == "Date":
        return build_grouped(raw, key_field="posting_date")
    if group_by == "Collected By":
        return build_grouped(raw, key_field="collected_by", label_field="collector_name")

    return raw


def build_grouped(raw, key_field, label_field=None, extra_fields=None, track_last_date=False):
    extra_fields = extra_fields or []
    groups = {}

    for r in raw:
        key = r.get(key_field) or "Unassigned"

        if key not in groups:
            g = {
                key_field: key,
                "amount": 0,
                "receipt_count": 0,
                "customer_count": 0,
                "_receipts": set(),
                "_customers": set(),
                "_last_date": None,
            }
            if label_field:
                g[label_field] = r.get(label_field)
            for f in extra_fields:
                g[f] = r.get(f)
            groups[key] = g

        g = groups[key]
        g["amount"] += flt(r.get("amount"))
        g["_receipts"].add(r.get("payment_entry"))
        if r.get("customer"):
            g["_customers"].add(r.get("customer"))

        if track_last_date and r.get("posting_date"):
            if not g["_last_date"] or r.get("posting_date") > g["_last_date"]:
                g["_last_date"] = r.get("posting_date")

    data = []
    for key, g in groups.items():
        g["receipt_count"] = len(g["_receipts"])
        g["customer_count"] = len(g["_customers"])
        g["avg_amount"] = g["amount"] / g["receipt_count"] if g["receipt_count"] else 0
        if track_last_date:
            g["last_date"] = g["_last_date"]
        for k in ("_receipts", "_customers", "_last_date"):
            g.pop(k, None)
        data.append(g)

    if key_field == "posting_date":
        data.sort(key=lambda x: x.get("posting_date") or "")
    else:
        data.sort(key=lambda x: flt(x.get("amount")), reverse=True)

    return data


# ============================================================
# SUMMARY & CHART
# ============================================================

def get_report_summary(data):
    if not data:
        return []

    total = sum(flt(d.get("amount")) for d in data)
    receipts = len(set(d.get("payment_entry") for d in data if d.get("payment_entry"))) or len(data)
    customers = len(set(d.get("customer") for d in data if d.get("customer")))
    avg = total / receipts if receipts else 0

    return [
        {"value": total, "label": _("Total Collected"),
         "datatype": "Currency", "indicator": "green"},
        {"value": receipts, "label": _("Total Receipts"),
         "datatype": "Int", "indicator": "blue"},
        {"value": customers, "label": _("Customers"),
         "datatype": "Int", "indicator": "purple"},
        {"value": avg, "label": _("Avg per Receipt"),
         "datatype": "Currency", "indicator": "orange"},
    ]


def get_chart_data(data, filters):
    if not data:
        return None

    group_by = filters.get("group_by") or "Detailed"

    if group_by == "Date":
        sorted_d = sorted(data, key=lambda x: x.get("posting_date") or "")
        return {
            "data": {
                "labels": [formatdate(d.get("posting_date")) for d in sorted_d],
                "datasets": [
                    {"name": "Collected",
                     "values": [flt(d.get("amount")) for d in sorted_d]},
                ]
            },
            "type": "line",
            "colors": ["#5cb37e"],
            "lineOptions": {"regionFill": 1, "hideDots": 0}
        }

    if group_by == "Detailed":
        totals = {}
        for r in data:
            sp = r.get("sales_person") or "Unassigned"
            totals[sp] = totals.get(sp, 0) + flt(r.get("amount"))
        sorted_x = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:10]
        return {
            "data": {
                "labels": [x[0] for x in sorted_x],
                "datasets": [{"name": "Collected",
                              "values": [x[1] for x in sorted_x]}]
            },
            "type": "bar",
            "colors": ["#7cc99a"],
        }

    label_key = (
        "sales_person" if group_by == "Route" else
        "customer" if group_by == "Customer" else
        "mode_of_payment" if group_by == "Mode of Payment" else
        "collected_by"
    )

    sorted_d = sorted(data, key=lambda x: flt(x.get("amount")), reverse=True)[:10]
    return {
        "data": {
            "labels": [str(d.get(label_key) or "") for d in sorted_d],
            "datasets": [
                {"name": "Collected",
                 "values": [flt(d.get("amount")) for d in sorted_d]},
            ]
        },
        "type": "bar",
        "colors": ["#7cc99a"],
        "barOptions": {"spaceRatio": 0.3}
    }


# ============================================================
# PDF EXPORT
# ============================================================

@frappe.whitelist()
def get_pdf_html(filters, data, columns=None):
    if isinstance(filters, str):
        filters = json.loads(filters)
    if isinstance(data, str):
        data = json.loads(data)

    company = filters.get("company")
    company_doc = frappe.get_doc("Company", company) if company else None
    currency = company_doc.default_currency if company_doc else "USD"

    letter_head = ""
    if company_doc and company_doc.default_letter_head:
        try:
            lh = frappe.get_doc("Letter Head", company_doc.default_letter_head)
            letter_head = frappe.render_template(lh.content or "", {"company": company_doc})
        except Exception:
            letter_head = ""

    group_by = filters.get("group_by") or "Detailed"

    total_amount = sum(flt(d.get("amount")) for d in data)
    receipts = len(set(d.get("payment_entry") for d in data
                       if d.get("payment_entry"))) or len(data)
    customers = len(set(d.get("customer") for d in data if d.get("customer")))
    avg = total_amount / receipts if receipts else 0

    # Filter summary
    filter_html = ""
    filter_map = [
        ("From Date", formatdate(filters.get("from_date"))
         if filters.get("from_date") else ""),
        ("To Date", formatdate(filters.get("to_date"))
         if filters.get("to_date") else ""),
        ("Company", filters.get("company") or ""),
        ("Group By", group_by),
        ("Route", filters.get("sales_person") or "All"),
        ("Customer", filters.get("customer") or "All"),
        ("Customer Group", filters.get("customer_group") or "All"),
        ("Mode of Payment", filters.get("mode_of_payment") or "All"),
        ("Cash Account", filters.get("cash_account") or "All"),
        ("Collected By", filters.get("collected_by") or "All"),
    ]
    for label, value in filter_map:
        if value:
            filter_html += (
                '<div class="filter-item">'
                '<span class="filter-label">' + str(label) + ':</span> '
                '<span class="filter-value">' + str(value) + '</span>'
                '</div>'
            )

    headers_html, rows_html, totals_html = build_pdf_table(
        data, group_by, currency, total_amount
    )

    now = format_datetime(get_datetime(), "dd MMM yyyy HH:mm")
    css = get_pdf_css()
    letter_head_html = (
        '<div class="letter-head">' + letter_head + '</div>'
    ) if letter_head else ''

    html = (
        '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        '<title>Cash Collection Report</title>'
        '<style>' + css + '</style></head><body>'
        + letter_head_html +
        '<div class="report-header">'
            '<div class="report-title">'
                '<h1>Cash Collection Report</h1>'
                '<div class="subtitle">Period: '
                + formatdate(filters.get('from_date'))
                + ' to '
                + formatdate(filters.get('to_date'))
                + ' &nbsp;|&nbsp; Grouped by: ' + group_by + '</div>'
            '</div>'
            '<div class="report-meta">'
                '<div><span class="label">Company:</span> <strong>'
                + str(filters.get('company') or '') + '</strong></div>'
                '<div><span class="label">Generated:</span> ' + str(now) + '</div>'
                '<div><span class="label">By:</span> '
                + str(frappe.session.user) + '</div>'
            '</div>'
        '</div>'
        '<div class="filters-section">'
            '<div class="filters-title">Applied Filters</div>'
            '<div class="filters-grid">' + filter_html + '</div>'
        '</div>'
        '<div class="summary-cards">'
            '<div class="summary-card card-green">'
                '<div class="label">Total Collected</div>'
                '<div class="value">'
                + fmt_money(total_amount, currency=currency) + '</div>'
            '</div>'
            '<div class="summary-card card-blue">'
                '<div class="label">Receipts</div>'
                '<div class="value">' + str(receipts) + '</div>'
            '</div>'
            '<div class="summary-card card-purple">'
                '<div class="label">Customers</div>'
                '<div class="value">' + str(customers) + '</div>'
            '</div>'
            '<div class="summary-card card-orange">'
                '<div class="label">Avg per Receipt</div>'
                '<div class="value">'
                + fmt_money(avg, currency=currency) + '</div>'
            '</div>'
        '</div>'
        '<table class="report-table"><thead>' + headers_html + '</thead>'
        '<tbody>' + rows_html + totals_html + '</tbody></table>'
        '<div class="signature-section">'
            '<div class="signature-box">'
                '<div class="signature-line"></div>'
                '<div><strong>Prepared By</strong></div>'
            '</div>'
            '<div class="signature-box">'
                '<div class="signature-line"></div>'
                '<div><strong>Verified By</strong></div>'
            '</div>'
            '<div class="signature-box">'
                '<div class="signature-line"></div>'
                '<div><strong>Approved By</strong></div>'
            '</div>'
        '</div>'
        '<div class="footer">'
            '<div>Cash Collection Report - '
            + str(filters.get('company') or '') + '</div>'
            '<div>Generated by ' + str(frappe.session.user)
            + ' on ' + str(now) + '</div>'
        '</div>'
        '</body></html>'
    )

    return html


def build_pdf_table(data, group_by, currency, total_amount):
    fmt = lambda v: fmt_money(v, currency=currency) if flt(v) else "-"

    # ====== ROUTE ======
    if group_by == "Route":
        headers_html = (
            '<tr>'
            '<th class="text-center">#</th>'
            '<th>Route</th>'
            '<th class="text-center">Receipts</th>'
            '<th class="text-center">Customers</th>'
            '<th class="text-right">Total Collected</th>'
            '<th class="text-right">Avg per Receipt</th>'
            '</tr>'
        )
        rows_html = ""
        for idx, r in enumerate(data, 1):
            cls = "even" if idx % 2 == 0 else "odd"
            rows_html += (
                f'<tr class="{cls}">'
                f'<td class="text-center">{idx}</td>'
                f'<td><strong>{r.get("sales_person") or "-"}</strong></td>'
                f'<td class="text-center">{r.get("receipt_count") or 0}</td>'
                f'<td class="text-center">{r.get("customer_count") or 0}</td>'
                f'<td class="text-right collected-col">'
                f'{fmt(r.get("amount"))}</td>'
                f'<td class="text-right">{fmt(r.get("avg_amount"))}</td>'
                f'</tr>'
            )
        totals_html = (
            '<tr class="totals-row">'
            '<td colspan="4" class="text-right"><strong>GRAND TOTAL</strong></td>'
            f'<td class="text-right"><strong>{fmt(total_amount)}</strong></td>'
            '<td></td>'
            '</tr>'
        )
        return headers_html, rows_html, totals_html

    # ====== CUSTOMER ======
    if group_by == "Customer":
        headers_html = (
            '<tr>'
            '<th class="text-center">#</th>'
            '<th>Customer</th>'
            '<th>Customer Name</th>'
            '<th>Group</th>'
            '<th class="text-center">Receipts</th>'
            '<th class="text-right">Total Collected</th>'
            '<th class="text-center">Last Collection</th>'
            '</tr>'
        )
        rows_html = ""
        for idx, r in enumerate(data, 1):
            cls = "even" if idx % 2 == 0 else "odd"
            last_dt = formatdate(r.get("last_date")) if r.get("last_date") else "-"
            rows_html += (
                f'<tr class="{cls}">'
                f'<td class="text-center">{idx}</td>'
                f'<td>{r.get("customer") or "-"}</td>'
                f'<td>{r.get("customer_name") or "-"}</td>'
                f'<td>{r.get("customer_group") or "-"}</td>'
                f'<td class="text-center">{r.get("receipt_count") or 0}</td>'
                f'<td class="text-right collected-col">'
                f'{fmt(r.get("amount"))}</td>'
                f'<td class="text-center">{last_dt}</td>'
                f'</tr>'
            )
        totals_html = (
            '<tr class="totals-row">'
            '<td colspan="5" class="text-right"><strong>GRAND TOTAL</strong></td>'
            f'<td class="text-right"><strong>{fmt(total_amount)}</strong></td>'
            '<td></td>'
            '</tr>'
        )
        return headers_html, rows_html, totals_html

    # ====== MODE OF PAYMENT ======
    if group_by == "Mode of Payment":
        headers_html = (
            '<tr>'
            '<th class="text-center">#</th>'
            '<th>Mode of Payment</th>'
            '<th class="text-center">Receipts</th>'
            '<th class="text-center">Customers</th>'
            '<th class="text-right">Total Collected</th>'
            '</tr>'
        )
        rows_html = ""
        for idx, r in enumerate(data, 1):
            cls = "even" if idx % 2 == 0 else "odd"
            rows_html += (
                f'<tr class="{cls}">'
                f'<td class="text-center">{idx}</td>'
                f'<td><strong>{r.get("mode_of_payment") or "-"}</strong></td>'
                f'<td class="text-center">{r.get("receipt_count") or 0}</td>'
                f'<td class="text-center">{r.get("customer_count") or 0}</td>'
                f'<td class="text-right collected-col">'
                f'{fmt(r.get("amount"))}</td>'
                f'</tr>'
            )
        totals_html = (
            '<tr class="totals-row">'
            '<td colspan="4" class="text-right"><strong>GRAND TOTAL</strong></td>'
            f'<td class="text-right"><strong>{fmt(total_amount)}</strong></td>'
            '</tr>'
        )
        return headers_html, rows_html, totals_html

    # ====== DATE ======
    if group_by == "Date":
        headers_html = (
            '<tr>'
            '<th class="text-center">#</th>'
            '<th class="text-center">Date</th>'
            '<th class="text-center">Receipts</th>'
            '<th class="text-center">Customers</th>'
            '<th class="text-right">Total Collected</th>'
            '</tr>'
        )
        rows_html = ""
        for idx, r in enumerate(data, 1):
            cls = "even" if idx % 2 == 0 else "odd"
            rows_html += (
                f'<tr class="{cls}">'
                f'<td class="text-center">{idx}</td>'
                f'<td class="text-center">'
                f'{formatdate(r.get("posting_date")) if r.get("posting_date") else "-"}'
                f'</td>'
                f'<td class="text-center">{r.get("receipt_count") or 0}</td>'
                f'<td class="text-center">{r.get("customer_count") or 0}</td>'
                f'<td class="text-right collected-col">'
                f'{fmt(r.get("amount"))}</td>'
                f'</tr>'
            )
        totals_html = (
            '<tr class="totals-row">'
            '<td colspan="4" class="text-right"><strong>GRAND TOTAL</strong></td>'
            f'<td class="text-right"><strong>{fmt(total_amount)}</strong></td>'
            '</tr>'
        )
        return headers_html, rows_html, totals_html

    # ====== COLLECTED BY ======
    if group_by == "Collected By":
        headers_html = (
            '<tr>'
            '<th class="text-center">#</th>'
            '<th>User</th>'
            '<th>Employee Name</th>'
            '<th class="text-center">Receipts</th>'
            '<th class="text-right">Total Collected</th>'
            '</tr>'
        )
        rows_html = ""
        for idx, r in enumerate(data, 1):
            cls = "even" if idx % 2 == 0 else "odd"
            rows_html += (
                f'<tr class="{cls}">'
                f'<td class="text-center">{idx}</td>'
                f'<td>{r.get("collected_by") or "-"}</td>'
                f'<td>{r.get("collector_name") or "-"}</td>'
                f'<td class="text-center">{r.get("receipt_count") or 0}</td>'
                f'<td class="text-right collected-col">'
                f'{fmt(r.get("amount"))}</td>'
                f'</tr>'
            )
        totals_html = (
            '<tr class="totals-row">'
            '<td colspan="4" class="text-right"><strong>GRAND TOTAL</strong></td>'
            f'<td class="text-right"><strong>{fmt(total_amount)}</strong></td>'
            '</tr>'
        )
        return headers_html, rows_html, totals_html

    # ====== DETAILED (default) ======
    headers_html = (
        '<tr>'
        '<th class="text-center">#</th>'
        '<th class="text-center">Date</th>'
        '<th>Payment Entry</th>'
        '<th>Customer</th>'
        '<th>Customer Name</th>'
        '<th>Route</th>'
        '<th>Mode</th>'
        '<th>Reference</th>'
        '<th>Against Invoice</th>'
        '<th class="text-right">Amount</th>'
        '<th>Collected By</th>'
        '</tr>'
    )
    rows_html = ""
    for idx, r in enumerate(data, 1):
        cls = "even" if idx % 2 == 0 else "odd"
        rows_html += (
            f'<tr class="{cls}">'
            f'<td class="text-center">{idx}</td>'
            f'<td class="text-center">'
            f'{formatdate(r.get("posting_date")) if r.get("posting_date") else "-"}'
            f'</td>'
            f'<td>{r.get("payment_entry") or "-"}</td>'
            f'<td>{r.get("customer") or "-"}</td>'
            f'<td>{r.get("customer_name") or "-"}</td>'
            f'<td>{r.get("sales_person") or "-"}</td>'
            f'<td>{r.get("mode_of_payment") or "-"}</td>'
            f'<td>{r.get("reference_no") or "-"}</td>'
            f'<td>{r.get("against_invoice") or "-"}</td>'
            f'<td class="text-right collected-col">'
            f'{fmt(r.get("amount"))}</td>'
            f'<td>{r.get("collector_name") or r.get("collected_by") or "-"}</td>'
            f'</tr>'
        )
    totals_html = (
        '<tr class="totals-row">'
        '<td colspan="9" class="text-right"><strong>GRAND TOTAL</strong></td>'
        f'<td class="text-right"><strong>{fmt(total_amount)}</strong></td>'
        '<td></td>'
        '</tr>'
    )
    return headers_html, rows_html, totals_html


def get_pdf_css():
    return """
        @page { size: A4 landscape; margin: 8mm; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 7.5pt;
               color: #2d3748; background: #fff; line-height: 1.3; }
        .letter-head { margin-bottom: 10px; padding-bottom: 6px;
                      border-bottom: 2px solid #5e72e4; }
        .report-header { display: flex; justify-content: space-between;
                         align-items: flex-start; margin-bottom: 10px;
                         padding: 12px 16px;
                         background: linear-gradient(135deg, #4299e1 0%,
                             #667eea 50%, #764ba2 100%);
                         color: white; border-radius: 8px;
                         box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .report-title h1 { font-size: 16pt; font-weight: 700;
                          margin-bottom: 3px; letter-spacing: 0.3px; }
        .report-title .subtitle { font-size: 8.5pt; opacity: 0.92; font-weight: 400; }
        .report-meta { text-align: right; font-size: 7.5pt; }
        .report-meta .label { opacity: 0.85; }
        .filters-section { background: #f0f4ff; border-left: 4px solid #667eea;
                          padding: 8px 12px; margin-bottom: 10px; border-radius: 4px; }
        .filters-title { font-size: 8pt; font-weight: 700; color: #5e72e4;
                        margin-bottom: 4px; text-transform: uppercase;
                        letter-spacing: 0.5px; }
        .filters-grid { display: grid; grid-template-columns: repeat(4, 1fr);
                       gap: 4px 12px; }
        .filter-item { font-size: 7.5pt; }
        .filter-label { font-weight: 600; color: #4a5568; }
        .filter-value { color: #2d3748; }
        .summary-cards { display: grid; grid-template-columns: repeat(4, 1fr);
                        gap: 8px; margin-bottom: 10px; }
        .summary-card { padding: 10px; border-radius: 6px; color: white;
                        text-align: center;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
        .card-blue { background: linear-gradient(135deg, #7ab8e8, #5a92d4); }
        .card-green { background: linear-gradient(135deg, #7cc99a, #5cb37e); }
        .card-orange { background: linear-gradient(135deg, #f5a96b, #e8884a); }
        .card-purple { background: linear-gradient(135deg, #b08ee0, #9374c8); }
        .summary-card .label { font-size: 7pt; opacity: 0.95; margin-bottom: 3px;
                              text-transform: uppercase; letter-spacing: 0.4px;
                              font-weight: 500; }
        .summary-card .value { font-size: 12pt; font-weight: 700; }
        table.report-table { width: 100%; border-collapse: collapse;
                            font-size: 7pt; margin-bottom: 10px; }
        table.report-table thead { background: linear-gradient(135deg,
                                   #4299e1 0%, #667eea 100%); color: white; }
        table.report-table th { padding: 6px 4px; text-align: left;
                                font-weight: 600; font-size: 7pt;
                                text-transform: uppercase; letter-spacing: 0.2px;
                                border: 1px solid #5a92d4; }
        table.report-table th.text-right { text-align: right; }
        table.report-table th.text-center { text-align: center; }
        table.report-table td { padding: 4px; border: 1px solid #e2e8f0; }
        table.report-table tr.odd { background: #ffffff; }
        table.report-table tr.even { background: #f7fafc; }
        table.report-table .text-right { text-align: right; }
        table.report-table .text-center { text-align: center; }
        .collected-col { color: #2f855a; font-weight: 600; }
        tr.totals-row { background: linear-gradient(135deg,
                        #4299e1, #667eea) !important;
                       color: white; font-weight: 700; }
        tr.totals-row td { padding: 9px 4px; border-color: #5a92d4; font-size: 8pt; }
        .footer { margin-top: 14px; padding-top: 6px;
                 border-top: 1px solid #e2e8f0; display: flex;
                 justify-content: space-between; font-size: 6.5pt; color: #718096; }
        .signature-section { display: grid; grid-template-columns: repeat(3, 1fr);
                            gap: 25px; margin-top: 30px; padding-top: 6px; }
        .signature-box { text-align: center; font-size: 7.5pt; color: #4a5568; }
        .signature-line { border-top: 1px solid #2d3748;
                         margin: 22px 15px 4px 15px; }
        @media print {
            body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
            tr { page-break-inside: avoid; }
            thead { display: table-header-group; }
            .summary-cards { page-break-inside: avoid; }
        }
    """