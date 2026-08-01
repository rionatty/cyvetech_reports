# -*- coding: utf-8 -*-
# Copyright (c) 2026, Your Company and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from frappe.utils import (
    flt, getdate, fmt_money, formatdate,
    format_datetime, get_datetime
)


def _company_header_html(company_doc):
    if not company_doc:
        return ""

    logo_html = ""
    if company_doc.company_logo:
        logo_html = (
            f'<img src="{company_doc.company_logo}" '
            f'style="max-height:65px;max-width:160px;object-fit:contain;" />'
        )

    address_lines = []
    try:
        addr_name = frappe.db.get_value(
            "Dynamic Link",
            {"link_doctype": "Company", "link_name": company_doc.name, "parenttype": "Address"},
            "parent"
        )
        if addr_name:
            addr = frappe.get_doc("Address", addr_name)
            for f in ["address_line1", "address_line2", "city", "state"]:
                v = getattr(addr, f, None)
                if v:
                    address_lines.append(v)
    except Exception:
        pass

    info = f'<div style="font-size:12pt;font-weight:700;">{company_doc.company_name}</div>'
    for line in address_lines:
        info += f'<div>{line}</div>'
    if company_doc.phone_no:
        info += f'<div><b>Tel:</b> {company_doc.phone_no}</div>'
    if company_doc.email:
        info += f'<div><b>Email:</b> {company_doc.email}</div>'
    if company_doc.website:
        info += f'<div><b>Web:</b> {company_doc.website}</div>'

    return (
        '<div style="display:flex;justify-content:space-between;align-items:center;'
        'margin-bottom:10px;padding-bottom:8px;border-bottom:2px solid #5e72e4;">'
        f'<div>{logo_html}</div>'
        f'<div style="text-align:right;font-size:8.5pt;color:#2d3748;line-height:1.7;">{info}</div>'
        '</div>'
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
             "options": "Sales Person", "width": 200},
            {"label": _("Invoices"), "fieldname": "invoice_count", "fieldtype": "Int", "width": 90},
            {"label": _("Customers"), "fieldname": "customer_count", "fieldtype": "Int", "width": 90},
            {"label": _("Qty Sold"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
            {"label": _("Gross Total"), "fieldname": "gross_total", "fieldtype": "Currency", "width": 130},
            {"label": _("Discount"), "fieldname": "discount", "fieldtype": "Currency", "width": 110},
            {"label": _("Net Total"), "fieldname": "net_total", "fieldtype": "Currency", "width": 130},
            {"label": _("Tax"), "fieldname": "tax", "fieldtype": "Currency", "width": 110},
            {"label": _("Grand Total"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 140},
            {"label": _("Paid"), "fieldname": "paid_amount", "fieldtype": "Currency", "width": 130},
            {"label": _("Outstanding"), "fieldname": "outstanding", "fieldtype": "Currency", "width": 130},
        ]

    if group_by == "Customer":
        return [
            {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link",
             "options": "Customer", "width": 160},
            {"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 180},
            {"label": _("Group"), "fieldname": "customer_group", "fieldtype": "Link",
             "options": "Customer Group", "width": 130},
            {"label": _("Invoices"), "fieldname": "invoice_count", "fieldtype": "Int", "width": 80},
            {"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 90},
            {"label": _("Net Total"), "fieldname": "net_total", "fieldtype": "Currency", "width": 130},
            {"label": _("Grand Total"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 140},
            {"label": _("Paid"), "fieldname": "paid_amount", "fieldtype": "Currency", "width": 130},
            {"label": _("Advance (Unallocated)"), "fieldname": "advance_amount", "fieldtype": "Currency", "width": 130},
            {"label": _("Outstanding"), "fieldname": "outstanding", "fieldtype": "Currency", "width": 130},
        ]

    if group_by == "Item":
        return [
            {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link",
             "options": "Item", "width": 160},
            {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
            {"label": _("Group"), "fieldname": "item_group", "fieldtype": "Link",
             "options": "Item Group", "width": 130},
            {"label": _("Brand"), "fieldname": "brand", "fieldtype": "Link",
             "options": "Brand", "width": 100},
            {"label": _("UOM"), "fieldname": "uom", "fieldtype": "Link",
             "options": "UOM", "width": 80},
            {"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
            {"label": _("Avg Rate"), "fieldname": "avg_rate", "fieldtype": "Currency", "width": 110},
            {"label": _("Net Total"), "fieldname": "net_total", "fieldtype": "Currency", "width": 130},
            {"label": _("# Invoices"), "fieldname": "invoice_count", "fieldtype": "Int", "width": 90},
        ]

    if group_by == "Item Group":
        return [
            {"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link",
             "options": "Item Group", "width": 200},
            {"label": _("Items"), "fieldname": "item_count", "fieldtype": "Int", "width": 80},
            {"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
            {"label": _("Net Total"), "fieldname": "net_total", "fieldtype": "Currency", "width": 130},
            {"label": _("Grand Total"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 140},
        ]

    if group_by == "Date":
        return [
            {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
            {"label": _("Invoices"), "fieldname": "invoice_count", "fieldtype": "Int", "width": 90},
            {"label": _("Customers"), "fieldname": "customer_count", "fieldtype": "Int", "width": 90},
            {"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
            {"label": _("Net Total"), "fieldname": "net_total", "fieldtype": "Currency", "width": 130},
            {"label": _("Grand Total"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 140},
            {"label": _("Paid"), "fieldname": "paid_amount", "fieldtype": "Currency", "width": 130},
            {"label": _("Outstanding"), "fieldname": "outstanding", "fieldtype": "Currency", "width": 130},
        ]

    if group_by == "Invoice":
        return [
            {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
            {"label": _("Invoice"), "fieldname": "invoice", "fieldtype": "Link",
             "options": "Sales Invoice", "width": 150},
            {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link",
             "options": "Customer", "width": 150},
            {"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 180},
            {"label": _("Items"), "fieldname": "item_count", "fieldtype": "Int", "width": 70},
            {"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 90},
            {"label": _("Net Total"), "fieldname": "net_total", "fieldtype": "Currency", "width": 130},
            {"label": _("Grand Total"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 140},
            {"label": _("Paid"), "fieldname": "paid_amount", "fieldtype": "Currency", "width": 130},
            {"label": _("Outstanding"), "fieldname": "outstanding", "fieldtype": "Currency", "width": 130},
        ]

    # DETAILED
    return [
        {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 90},
        {"label": _("Invoice"), "fieldname": "invoice", "fieldtype": "Link",
         "options": "Sales Invoice", "width": 130},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link",
         "options": "Customer", "width": 140},
        {"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 160},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 80},
        {"label": _("UOM"), "fieldname": "uom", "fieldtype": "Link",
         "options": "UOM", "width": 70},
        {"label": _("Rate"), "fieldname": "rate", "fieldtype": "Currency", "width": 110},
        {"label": _("Net Amount"), "fieldname": "net_total", "fieldtype": "Currency", "width": 130},
        {"label": _("Grand Total"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 130},
    ]


# ============================================================
# DATA FETCHING
# ============================================================

def build_conditions(filters):
    conditions = " si.docstatus = 1 AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s "
    params = {
        "from_date": getdate(filters.get("from_date")),
        "to_date": getdate(filters.get("to_date")),
    }

    if filters.get("company"):
        conditions += " AND si.company = %(company)s "
        params["company"] = filters.get("company")

    if filters.get("customer"):
        conditions += " AND si.customer = %(customer)s "
        params["customer"] = filters.get("customer")

    if filters.get("customer_group"):
        conditions += " AND si.customer_group = %(customer_group)s "
        params["customer_group"] = filters.get("customer_group")

    if filters.get("territory"):
        conditions += " AND si.territory = %(territory)s "
        params["territory"] = filters.get("territory")

    # Online vs Offline sales — custom_online_sale is a Yes/No select on the
    # Sales Invoice (Yes = online). Offline = anything not explicitly 'Yes',
    # so Online + Offline together always cover every invoice.
    sale_type = filters.get("sale_type")
    if sale_type == "Online":
        conditions += " AND si.custom_online_sale = 'Yes' "
    elif sale_type == "Offline":
        conditions += " AND COALESCE(si.custom_online_sale, '') <> 'Yes' "

    if filters.get("item_code"):
        conditions += " AND sii.item_code = %(item_code)s "
        params["item_code"] = filters.get("item_code")

    if filters.get("item_group"):
        conditions += " AND sii.item_group = %(item_group)s "
        params["item_group"] = filters.get("item_group")

    if filters.get("brand"):
        conditions += " AND sii.brand = %(brand)s "
        params["brand"] = filters.get("brand")

    if filters.get("warehouse"):
        conditions += " AND sii.warehouse = %(warehouse)s "
        params["warehouse"] = filters.get("warehouse")

    if filters.get("sales_person"):
        conditions += " AND st.sales_person = %(sales_person)s "
        params["sales_person"] = filters.get("sales_person")

    # ===== PAYMENT TERMS FILTERS =====
    if filters.get("payment_terms_template"):
        conditions += " AND si.payment_terms_template = %(payment_terms_template)s "
        params["payment_terms_template"] = filters.get("payment_terms_template")

    if filters.get("payment_term"):
        conditions += """ AND EXISTS (
            SELECT 1 FROM `tabPayment Schedule` ps
            WHERE ps.parent = si.name
              AND ps.payment_term = %(payment_term)s
        ) """
        params["payment_term"] = filters.get("payment_term")

    if not filters.get("include_returns"):
        conditions += " AND COALESCE(si.is_return, 0) = 0 "

    payment_status = filters.get("payment_status") or []
    if payment_status and isinstance(payment_status[0], dict):
        payment_status = [s.get("value") for s in payment_status]

    if payment_status:
        placeholders = ", ".join([f"%(status_{i})s" for i in range(len(payment_status))])
        conditions += f" AND si.status IN ({placeholders}) "
        for i, s in enumerate(payment_status):
            params[f"status_{i}"] = s

    return conditions, params


def build_conditions_no_st(filters):
    """Same conditions as build_conditions but uses EXISTS for sales_person (no Sales Team join)."""
    conditions = " si.docstatus = 1 AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s "
    params = {
        "from_date": getdate(filters.get("from_date")),
        "to_date": getdate(filters.get("to_date")),
    }

    if filters.get("company"):
        conditions += " AND si.company = %(company)s "
        params["company"] = filters.get("company")

    if filters.get("customer"):
        conditions += " AND si.customer = %(customer)s "
        params["customer"] = filters.get("customer")

    if filters.get("customer_group"):
        conditions += " AND si.customer_group = %(customer_group)s "
        params["customer_group"] = filters.get("customer_group")

    if filters.get("territory"):
        conditions += " AND si.territory = %(territory)s "
        params["territory"] = filters.get("territory")

    # Online vs Offline sales — custom_online_sale is a Yes/No select on the
    # Sales Invoice (Yes = online). Offline = anything not explicitly 'Yes',
    # so Online + Offline together always cover every invoice.
    sale_type = filters.get("sale_type")
    if sale_type == "Online":
        conditions += " AND si.custom_online_sale = 'Yes' "
    elif sale_type == "Offline":
        conditions += " AND COALESCE(si.custom_online_sale, '') <> 'Yes' "

    if filters.get("item_code"):
        conditions += " AND sii.item_code = %(item_code)s "
        params["item_code"] = filters.get("item_code")

    if filters.get("item_group"):
        conditions += " AND sii.item_group = %(item_group)s "
        params["item_group"] = filters.get("item_group")

    if filters.get("brand"):
        conditions += " AND sii.brand = %(brand)s "
        params["brand"] = filters.get("brand")

    if filters.get("warehouse"):
        conditions += " AND sii.warehouse = %(warehouse)s "
        params["warehouse"] = filters.get("warehouse")

    if filters.get("sales_person"):
        # Use EXISTS to avoid row multiplication
        conditions += """ AND EXISTS (
            SELECT 1 FROM `tabSales Team` _st
            WHERE _st.parent = si.name
              AND _st.sales_person = %(sales_person)s
        ) """
        params["sales_person"] = filters.get("sales_person")

    if filters.get("payment_terms_template"):
        conditions += " AND si.payment_terms_template = %(payment_terms_template)s "
        params["payment_terms_template"] = filters.get("payment_terms_template")

    if filters.get("payment_term"):
        conditions += """ AND EXISTS (
            SELECT 1 FROM `tabPayment Schedule` ps
            WHERE ps.parent = si.name
              AND ps.payment_term = %(payment_term)s
        ) """
        params["payment_term"] = filters.get("payment_term")

    if not filters.get("include_returns"):
        conditions += " AND COALESCE(si.is_return, 0) = 0 "

    payment_status = filters.get("payment_status") or []
    if payment_status and isinstance(payment_status[0], dict):
        payment_status = [s.get("value") for s in payment_status]

    if payment_status:
        placeholders = ", ".join([f"%(status_{i})s" for i in range(len(payment_status))])
        conditions += f" AND si.status IN ({placeholders}) "
        for i, s in enumerate(payment_status):
            params[f"status_{i}"] = s

    return conditions, params


def get_raw_data(filters):
    """Pull invoice line items joined with sales team."""
    conditions, params = build_conditions(filters)

    query = f"""
        SELECT
            si.name                                    AS invoice,
            si.posting_date                            AS posting_date,
            si.status                                  AS status,
            si.payment_terms_template                  AS payment_terms_template,
            si.customer                                AS customer,
            si.customer_name                           AS customer_name,
            si.customer_group                          AS customer_group,
            si.territory                               AS territory,
            si.grand_total                             AS si_grand_total,
            si.rounded_total                           AS si_rounded_total,
            si.outstanding_amount                      AS si_outstanding,
            si.is_return                               AS is_return,
            COALESCE(st.sales_person, 'Unassigned')    AS sales_person,
            COALESCE(st.allocated_percentage, 100)     AS allocated_percentage,
            sii.name                                   AS line_id,
            sii.item_code                              AS item_code,
            sii.item_name                              AS item_name,
            sii.item_group                             AS item_group,
            sii.brand                                  AS brand,
            sii.uom                                    AS uom,
            sii.qty                                    AS qty,
            sii.rate                                   AS rate,
            sii.discount_amount                        AS discount_amount,
            sii.amount                                 AS net_total,
            sii.base_amount                            AS base_amount,
            sii.warehouse                              AS warehouse
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        LEFT JOIN `tabSales Team` st ON st.parent = si.name
        WHERE {conditions}
        ORDER BY si.posting_date, si.name, sii.idx
    """

    rows = frappe.db.sql(query, params, as_dict=1) or []

    # Apply allocation percentage to amount fields
    for r in rows:
        alloc = flt(r.allocated_percentage) / 100.0
        # unscaled copies for groupings that must not depend on sales-team allocation
        r.full_qty = flt(r.qty)
        r.full_net_total = flt(r.net_total)
        r.full_discount = flt(r.discount_amount)
        # outstanding_amount is based on rounded_total when rounding is enabled,
        # so paid must be derived from the same base or unpaid invoices show a
        # phantom negative paid amount
        r.si_effective_total = flt(r.si_rounded_total) or flt(r.si_grand_total)
        r.qty = flt(r.qty) * alloc
        r.net_total = flt(r.net_total) * alloc
        r.discount_amount = flt(r.discount_amount) * alloc
        r.allocated_grand_total = flt(r.si_grand_total) * alloc
        r.allocated_outstanding = flt(r.si_outstanding) * alloc
        r.allocated_paid = (r.si_effective_total - flt(r.si_outstanding)) * alloc

    return rows


def get_data(filters):
    group_by = filters.get("group_by") or "Detailed"

    # Detailed uses a clean query without Sales Team join to avoid row multiplication
    if group_by == "Detailed":
        return build_detailed_clean(filters)

    if group_by == "Invoice":
        return build_invoice_grouped(filters)

    raw = get_raw_data(filters)
    if not raw:
        return []

    if group_by == "Route":
        return build_grouped(raw, key_field="sales_person")
    if group_by == "Customer":
        data = build_grouped(raw, key_field="customer", label_field="customer_name",
                             extra_fields=["customer_group"])
        # Outstanding must reflect what the customer actually owes as at To
        # Date (per the receivables ledger: older invoices, advances, credit
        # notes and unallocated payments included) - not just the unpaid
        # portion of the invoices in the period, which overstates debt for
        # customers with unreconciled payments.
        receivables = get_customer_receivables(filters)
        if receivables is not None:
            for d in data:
                entry = receivables.get(d.get("customer")) or {}
                d["outstanding"] = flt(entry.get("due"))
                d["advance_amount"] = flt(entry.get("advance"))
            data.extend(build_balance_only_rows(data, receivables))
        return data
    if group_by == "Item":
        return build_grouped(raw, key_field="item_code", label_field="item_name",
                             extra_fields=["item_group", "brand", "uom"], compute_avg_rate=True)
    if group_by == "Item Group":
        return build_grouped(raw, key_field="item_group")
    if group_by == "Date":
        return build_grouped(raw, key_field="posting_date")

    return build_detailed_clean(filters)


def get_customer_receivables(filters):
    """party -> {"due", "advance"} as at To Date, from the same engine the
    Accounts Receivable Summary report uses, so both reports always agree.

    "due" is the Total Amount Due (aged buckets: invoices net of allocated
    payments, JEs and credit notes). "advance" is payments/credits received
    but not allocated to any invoice - AR shows these separately, not as a
    reduction of the amount due.
    """
    try:
        from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary import (
            AccountsReceivableSummary,
        )

        args = {
            "account_type": "Receivable",
            "naming_by": ["Selling Settings", "cust_master_name"],
        }
        ar_filters = frappe._dict(
            {
                "company": filters.get("company"),
                "report_date": filters.get("to_date") or frappe.utils.nowdate(),
                "range": "30, 60, 90, 120",
            }
        )
        _, rows = AccountsReceivableSummary(ar_filters).run(args)

        receivables = {}
        for r in rows:
            due = r.get("total_due")
            if due is None:
                due = r.get("outstanding")
            receivables[r.get("party")] = {
                "due": flt(due),
                "advance": flt(r.get("advance")),
            }
        return receivables
    except Exception:
        frappe.log_error(title="Sales Analysis: customer receivables lookup failed")
        return None


def build_balance_only_rows(data, receivables):
    """Rows for customers with a ledger balance (debt or overpayment/credit)
    but no sales in the period - they would otherwise be invisible in the
    Customer view even though they owe money or have money with us."""
    seen = {d.get("customer") for d in data}
    extras = {
        party: entry
        for party, entry in receivables.items()
        if party and party not in seen and (flt(entry.get("due")) or flt(entry.get("advance")))
    }
    if not extras:
        return []

    details = {
        c.name: c
        for c in frappe.get_all(
            "Customer",
            filters={"name": ("in", list(extras))},
            fields=["name", "customer_name", "customer_group"],
        )
    }

    rows = []
    for party, entry in extras.items():
        customer = details.get(party)
        rows.append({
            "customer": party,
            "customer_name": (customer and customer.customer_name) or party,
            "customer_group": (customer and customer.customer_group) or "",
            "invoice_count": 0,
            "customer_count": 0,
            "item_count": 0,
            "qty": 0.0,
            "gross_total": 0.0,
            "discount": 0.0,
            "net_total": 0.0,
            "tax": 0.0,
            "grand_total": 0.0,
            "paid_amount": 0.0,
            "advance_amount": flt(entry.get("advance")),
            "outstanding": flt(entry.get("due")),
        })

    # biggest debts first, overpayments (negative) at the end where they
    # stand out against the zero-sales rows
    rows.sort(key=lambda r: flt(r.get("outstanding")), reverse=True)
    return rows


def build_detailed(raw):
    """One row per invoice line."""
    data = []
    seen_invoice = {}

    for r in raw:
        # Invoice-level paid/outstanding only on first line of each invoice
        if r.invoice in seen_invoice:
            paid_amt = 0
            outstanding = 0
            grand_total = 0
        else:
            seen_invoice[r.invoice] = True
            paid_amt = flt(r.allocated_paid)
            outstanding = flt(r.allocated_outstanding)
            grand_total = flt(r.allocated_grand_total)

        data.append({
            "posting_date": r.posting_date,
            "invoice": r.invoice,
            "status": r.status or "",
            "payment_terms_template": r.payment_terms_template or "",
            "sales_person": r.sales_person,
            "customer": r.customer,
            "customer_name": r.customer_name,
            "item_code": r.item_code,
            "item_name": r.item_name,
            "item_group": r.item_group,
            "qty": flt(r.qty),
            "uom": r.uom,
            "rate": flt(r.rate),
            "discount_amount": flt(r.discount_amount),
            "net_total": flt(r.net_total),
            "grand_total": grand_total,
            "paid_amount": paid_amt,
            "outstanding": outstanding,
        })
    return data


def build_detailed_clean(filters):
    """Detailed view without Sales Team join — eliminates row multiplication from multi-salesperson invoices."""
    conditions, params = build_conditions_no_st(filters)

    query = f"""
        SELECT
            si.name                   AS invoice,
            si.posting_date           AS posting_date,
            si.status                 AS status,
            si.payment_terms_template AS payment_terms_template,
            si.customer               AS customer,
            si.customer_name          AS customer_name,
            si.customer_group         AS customer_group,
            si.territory              AS territory,
            si.grand_total            AS grand_total,
            si.rounded_total          AS rounded_total,
            si.outstanding_amount     AS outstanding_amount,
            si.is_return              AS is_return,
            sii.item_code             AS item_code,
            sii.item_name             AS item_name,
            sii.item_group            AS item_group,
            sii.brand                 AS brand,
            sii.uom                   AS uom,
            sii.qty                   AS qty,
            sii.rate                  AS rate,
            sii.discount_amount       AS discount_amount,
            sii.amount                AS net_total,
            sii.warehouse             AS warehouse
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE {conditions}
        ORDER BY si.posting_date, si.name, sii.idx
    """

    rows = frappe.db.sql(query, params, as_dict=1) or []
    data = []
    seen_invoices = set()

    for r in rows:
        first_of_invoice = r.invoice not in seen_invoices
        seen_invoices.add(r.invoice)

        data.append({
            "posting_date": r.posting_date,
            "invoice": r.invoice,
            "status": r.status or "",
            "payment_terms_template": r.payment_terms_template or "",
            "sales_person": "",
            "customer": r.customer,
            "customer_name": r.customer_name,
            "item_code": r.item_code,
            "item_name": r.item_name,
            "item_group": r.item_group,
            "qty": flt(r.qty),
            "uom": r.uom,
            "rate": flt(r.rate),
            "discount_amount": flt(r.discount_amount),
            "net_total": flt(r.net_total),
            # Invoice-level totals only on the first item row of each invoice.
            # Paid is derived from rounded_total when set - outstanding_amount
            # is based on it, deriving from grand_total shows phantom negatives.
            "grand_total": flt(r.grand_total) if first_of_invoice else 0.0,
            "paid_amount": flt((flt(r.rounded_total) or flt(r.grand_total)) - flt(r.outstanding_amount))
            if first_of_invoice
            else 0.0,
            "outstanding": flt(r.outstanding_amount) if first_of_invoice else 0.0,
        })

    return data


def build_invoice_grouped(filters):
    """One row per Sales Invoice. Uses a clean query (no Sales Team join) so
    invoice-level totals stay exact and there's no row multiplication."""
    conditions, params = build_conditions_no_st(filters)

    query = f"""
        SELECT
            si.name               AS invoice,
            si.posting_date       AS posting_date,
            si.status             AS status,
            si.customer           AS customer,
            si.customer_name      AS customer_name,
            si.customer_group     AS customer_group,
            si.grand_total        AS grand_total,
            si.rounded_total      AS rounded_total,
            si.outstanding_amount AS outstanding_amount,
            COUNT(DISTINCT sii.item_code) AS item_count,
            SUM(sii.qty)          AS qty,
            SUM(sii.amount)       AS net_total
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE {conditions}
        GROUP BY si.name
        ORDER BY si.posting_date, si.name
    """

    rows = frappe.db.sql(query, params, as_dict=1) or []
    data = []
    for r in rows:
        grand = flt(r.grand_total)
        outstanding = flt(r.outstanding_amount)
        effective_total = flt(r.rounded_total) or grand
        data.append({
            "posting_date": r.posting_date,
            "invoice": r.invoice,
            "status": r.status or "",
            "customer": r.customer,
            "customer_name": r.customer_name,
            "customer_group": r.customer_group,
            "item_count": int(r.item_count or 0),
            "qty": flt(r.qty),
            "net_total": flt(r.net_total),
            "grand_total": grand,
            "paid_amount": effective_total - outstanding,
            "outstanding": outstanding,
        })
    return data


def build_grouped(raw, key_field, label_field=None, extra_fields=None, compute_avg_rate=False):
    """Aggregate rows by a single key."""
    extra_fields = extra_fields or []
    groups = {}
    invoice_seen_by_group = {}
    line_seen_by_group = {}

    # Only the Route grouping splits amounts by sales-team allocation. Every
    # other grouping must use full invoice/line values: the Sales Team join
    # duplicates each item line once per salesperson, and adding only the
    # first-seen allocated fraction undercounts multi-salesperson invoices.
    route_mode = key_field == "sales_person"

    for r in raw:
        key = r.get(key_field)
        if key is None or key == "":
            key = "Unassigned"

        if key not in groups:
            g = {
                key_field: key,
                "qty": 0,
                "gross_total": 0,
                "discount": 0,
                "net_total": 0,
                "tax": 0,
                "grand_total": 0,
                "paid_amount": 0,
                "outstanding": 0,
                "invoice_count": 0,
                "customer_count": 0,
                "item_count": 0,
                "_invoices": set(),
                "_customers": set(),
                "_items": set(),
                "_rate_sum": 0,
                "_rate_qty": 0,
            }
            if label_field:
                g[label_field] = r.get(label_field)
            for f in extra_fields:
                g[f] = r.get(f)
            groups[key] = g
            invoice_seen_by_group[key] = set()
            line_seen_by_group[key] = set()

        g = groups[key]

        if route_mode:
            line_qty = flt(r.qty)
            add_line = True
        else:
            line_qty = flt(r.full_qty)
            add_line = r.line_id not in line_seen_by_group[key]

        if add_line:
            line_seen_by_group[key].add(r.line_id)
            if route_mode:
                g["qty"] += flt(r.qty)
                g["discount"] += flt(r.discount_amount)
                g["net_total"] += flt(r.net_total)
            else:
                g["qty"] += flt(r.full_qty)
                g["discount"] += flt(r.full_discount)
                g["net_total"] += flt(r.full_net_total)
            if compute_avg_rate:
                g["_rate_sum"] += flt(r.rate) * line_qty
                g["_rate_qty"] += line_qty

        g["_invoices"].add(r.invoice)
        if r.customer:
            g["_customers"].add(r.customer)
        if r.item_code:
            g["_items"].add(r.item_code)

        # Invoice-level totals only once per (group, invoice)
        if r.invoice not in invoice_seen_by_group[key]:
            invoice_seen_by_group[key].add(r.invoice)
            if route_mode:
                g["grand_total"] += flt(r.allocated_grand_total)
                g["paid_amount"] += flt(r.allocated_paid)
                g["outstanding"] += flt(r.allocated_outstanding)
            else:
                g["grand_total"] += flt(r.si_grand_total)
                g["paid_amount"] += flt(r.si_effective_total) - flt(r.si_outstanding)
                g["outstanding"] += flt(r.si_outstanding)

    # Finalize
    data = []
    for key, g in groups.items():
        g["invoice_count"] = len(g["_invoices"])
        g["customer_count"] = len(g["_customers"])
        g["item_count"] = len(g["_items"])
        g["gross_total"] = g["net_total"] + g["discount"]
        g["tax"] = g["grand_total"] - g["net_total"]
        if compute_avg_rate and g["_rate_qty"]:
            g["avg_rate"] = g["_rate_sum"] / g["_rate_qty"]
        else:
            g["avg_rate"] = 0

        for k in ("_invoices", "_customers", "_items", "_rate_sum", "_rate_qty"):
            g.pop(k, None)

        data.append(g)

    if key_field == "posting_date":
        data.sort(key=lambda x: x.get("posting_date") or "")
    else:
        data.sort(key=lambda x: flt(x.get("net_total")), reverse=True)

    return data


# ============================================================
# SUMMARY & CHART
# ============================================================

def get_report_summary(data):
    if not data:
        return []

    total_net = sum(flt(d.get("net_total")) for d in data)
    total_grand = sum(flt(d.get("grand_total")) for d in data)
    total_paid = sum(flt(d.get("paid_amount")) for d in data)
    total_outstanding = sum(flt(d.get("outstanding")) for d in data)
    total_qty = sum(flt(d.get("qty")) for d in data)

    return [
        {"value": total_net, "label": _("Net Sales"),
         "datatype": "Currency", "indicator": "blue"},
        {"value": total_grand, "label": _("Grand Total"),
         "datatype": "Currency", "indicator": "purple"},
        {"value": total_paid, "label": _("Total Paid"),
         "datatype": "Currency", "indicator": "green"},
        {"value": total_outstanding, "label": _("Outstanding"),
         "datatype": "Currency",
         "indicator": "red" if total_outstanding > 0 else "green"},
        {"value": total_qty, "label": _("Total Qty"),
         "datatype": "Float", "indicator": "grey"},
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
                    {"name": "Net Sales", "values": [flt(d.get("net_total")) for d in sorted_d]},
                ]
            },
            "type": "line",
            "colors": ["#5e72e4"],
            "lineOptions": {"regionFill": 1, "hideDots": 0}
        }

    if group_by == "Detailed":
        totals = {}
        for r in data:
            sp = r.get("sales_person") or "Unassigned"
            totals[sp] = totals.get(sp, 0) + flt(r.get("net_total"))
        sorted_x = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:10]
        return {
            "data": {
                "labels": [x[0] for x in sorted_x],
                "datasets": [{"name": "Net Sales", "values": [x[1] for x in sorted_x]}]
            },
            "type": "bar",
            "colors": ["#7ab8e8"],
        }

    label_key = (
        "sales_person" if group_by == "Route" else
        "customer" if group_by == "Customer" else
        "item_code" if group_by == "Item" else
        "invoice" if group_by == "Invoice" else
        "item_group"
    )

    sorted_d = sorted(data, key=lambda x: flt(x.get("net_total")), reverse=True)[:10]

    return {
        "data": {
            "labels": [str(d.get(label_key) or "") for d in sorted_d],
            "datasets": [
                {"name": "Net Sales", "values": [flt(d.get("net_total")) for d in sorted_d]},
            ]
        },
        "type": "bar",
        "colors": ["#7ab8e8"],
        "barOptions": {"spaceRatio": 0.3}
    }


# ============================================================
# PDF EXPORT
# ============================================================

@frappe.whitelist()
def get_pdf_html(filters, data=None, columns=None, visible_columns=None):
    if isinstance(filters, str):
        filters = json.loads(filters)

    if isinstance(visible_columns, str):
        visible_columns = json.loads(visible_columns or "[]")
    visible_columns = visible_columns or []

    # Always regenerate data server-side so Frappe's auto-totals row
    # (add_total_row feature) never contaminates the PDF totals.
    data = get_data(filters)

    company = filters.get("company")
    company_doc = frappe.get_doc("Company", company) if company else None
    currency = company_doc.default_currency if company_doc else "USD"

    letter_head_html = _company_header_html(company_doc)

    group_by = filters.get("group_by") or "Detailed"

    total_net   = sum(flt(d.get("net_total"))    for d in data)
    total_grand = sum(flt(d.get("grand_total"))  for d in data)
    total_paid  = sum(flt(d.get("paid_amount"))  for d in data)
    total_outstanding = sum(flt(d.get("outstanding")) for d in data)
    total_qty   = sum(flt(d.get("qty"))          for d in data)

    # Filter summary
    filter_html = ""
    payment_status_list = filters.get("payment_status") or []
    if payment_status_list and isinstance(payment_status_list[0], dict):
        payment_status_list = [s.get("value") for s in payment_status_list]

    filter_map = [
        ("From Date", formatdate(filters.get("from_date")) if filters.get("from_date") else ""),
        ("To Date", formatdate(filters.get("to_date")) if filters.get("to_date") else ""),
        ("Company", filters.get("company") or ""),
        ("Group By", group_by),
        ("Route", filters.get("sales_person") or "All"),
        ("Customer", filters.get("customer") or "All"),
        ("Item", filters.get("item_code") or "All"),
        ("Item Group", filters.get("item_group") or "All"),
        ("Brand", filters.get("brand") or "All"),
        ("Sale Type", filters.get("sale_type") or "All"),
        ("Payment Status", ", ".join(payment_status_list) or "All"),
        ("Payment Terms Template", filters.get("payment_terms_template") or "All"),
        ("Payment Term", filters.get("payment_term") or "All"),
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
        data, group_by, currency, total_qty, total_net,
        total_grand, total_paid, total_outstanding,
        visible_columns
    )

    now = format_datetime(get_datetime(), "dd MMM yyyy HH:mm")
    css = get_pdf_css()

    html = (
        '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        '<title>Sales Report</title>'
        '<style>' + css + '</style></head><body>'
        + letter_head_html +
        '<div class="report-header">'
            '<div class="report-title">'
                '<h1>Sales Report</h1>'
                '<div class="subtitle">Period: ' + formatdate(filters.get('from_date')) + ' to ' + formatdate(filters.get('to_date')) +
                ' &nbsp;|&nbsp; Grouped by: ' + group_by + '</div>'
            '</div>'
            '<div class="report-meta">'
                '<div><span class="label">Company:</span> <strong>' + str(filters.get('company') or '') + '</strong></div>'
                '<div><span class="label">Generated:</span> ' + str(now) + '</div>'
                '<div><span class="label">By:</span> ' + str(frappe.session.user) + '</div>'
            '</div>'
        '</div>'

        '<div class="filters-section">'
            '<div class="filters-title">Applied Filters</div>'
            '<div class="filters-grid">' + filter_html + '</div>'
        '</div>'

        '<div class="summary-cards">'
            '<div class="summary-card card-blue">'
                '<div class="label">Net Sales</div>'
                '<div class="value">' + fmt_money(total_net, currency=currency) + '</div>'
            '</div>'
            '<div class="summary-card card-purple">'
                '<div class="label">Grand Total</div>'
                '<div class="value">' + fmt_money(total_grand, currency=currency) + '</div>'
            '</div>'
            '<div class="summary-card card-green">'
                '<div class="label">Total Paid</div>'
                '<div class="value">' + fmt_money(total_paid, currency=currency) + '</div>'
            '</div>'
            '<div class="summary-card card-red">'
                '<div class="label">Outstanding</div>'
                '<div class="value">' + fmt_money(total_outstanding, currency=currency) + '</div>'
            '</div>'
            '<div class="summary-card card-grey">'
                '<div class="label">Total Qty</div>'
                '<div class="value">' + "{:,.2f}".format(total_qty) + '</div>'
            '</div>'
        '</div>'

        '<table class="report-table"><thead>' + headers_html + '</thead>'
        '<tbody>' + rows_html + totals_html + '</tbody></table>'

        '<div class="signature-section">'
            '<div class="signature-box"><div class="signature-line"></div><div><strong>Prepared By</strong></div></div>'
            '<div class="signature-box"><div class="signature-line"></div><div><strong>Verified By</strong></div></div>'
            '<div class="signature-box"><div class="signature-line"></div><div><strong>Approved By</strong></div></div>'
        '</div>'

        '<div class="footer">'
            '<div>Sales Report - ' + str(filters.get('company') or '') + '</div>'
            '<div>Generated by ' + str(frappe.session.user) + ' on ' + str(now) + '</div>'
        '</div>'

        '</body></html>'
    )

    return html


def build_pdf_table(data, group_by, currency, total_qty, total_net,
                    total_grand, total_paid, total_outstanding,
                    visible_cols=None):
    """Build headers, rows and totals based on group_by.

    visible_cols: list of fieldnames currently visible in the UI.
    Empty/None means show all columns (backward-compatible default).
    """
    fmt     = lambda v: fmt_money(v, currency=currency) if flt(v) else "-"
    qty_fmt = lambda v: "{:,.2f}".format(flt(v)) if flt(v) else "-"

    def vis(f):
        return not visible_cols or f in visible_cols

    # ====== ROUTE ======
    if group_by == "Route":
        ths = ['<th class="text-center">#</th>']
        if vis("sales_person"):   ths.append("<th>Route</th>")
        if vis("invoice_count"):  ths.append('<th class="text-center">Invoices</th>')
        if vis("customer_count"): ths.append('<th class="text-center">Customers</th>')
        if vis("qty"):            ths.append('<th class="text-right">Qty</th>')
        if vis("net_total"):      ths.append('<th class="text-right">Net Total</th>')
        if vis("grand_total"):    ths.append('<th class="text-right">Grand Total</th>')
        if vis("paid_amount"):    ths.append('<th class="text-right">Paid</th>')
        if vis("outstanding"):    ths.append('<th class="text-right">Outstanding</th>')
        headers_html = "<tr>" + "".join(ths) + "</tr>"
        n = 1 + sum([vis("sales_person"), vis("invoice_count"), vis("customer_count")])
        rows_html = ""
        for idx, r in enumerate(data, 1):
            cls = "even" if idx % 2 == 0 else "odd"
            sp  = r.get("sales_person") or "-"
            tds = [f'<td class="text-center">{idx}</td>']
            if vis("sales_person"):   tds.append(f"<td><strong>{sp}</strong></td>")
            if vis("invoice_count"):  tds.append(f'<td class="text-center">{r.get("invoice_count") or 0}</td>')
            if vis("customer_count"): tds.append(f'<td class="text-center">{r.get("customer_count") or 0}</td>')
            if vis("qty"):            tds.append(f'<td class="text-right">{qty_fmt(r.get("qty"))}</td>')
            if vis("net_total"):      tds.append(f'<td class="text-right">{fmt(r.get("net_total"))}</td>')
            if vis("grand_total"):    tds.append(f'<td class="text-right">{fmt(r.get("grand_total"))}</td>')
            if vis("paid_amount"):    tds.append(f'<td class="text-right">{fmt(r.get("paid_amount"))}</td>')
            if vis("outstanding"):    tds.append(f'<td class="text-right">{fmt(r.get("outstanding"))}</td>')
            rows_html += f'<tr class="{cls}">{"".join(tds)}</tr>'
        tot = [f'<td colspan="{n}" class="text-right"><strong>GRAND TOTAL</strong></td>']
        if vis("qty"):         tot.append(f'<td class="text-right"><strong>{qty_fmt(total_qty)}</strong></td>')
        if vis("net_total"):   tot.append(f'<td class="text-right"><strong>{fmt(total_net)}</strong></td>')
        if vis("grand_total"): tot.append(f'<td class="text-right"><strong>{fmt(total_grand)}</strong></td>')
        if vis("paid_amount"): tot.append(f'<td class="text-right"><strong>{fmt(total_paid)}</strong></td>')
        if vis("outstanding"): tot.append(f'<td class="text-right"><strong>{fmt(total_outstanding)}</strong></td>')
        return headers_html, rows_html, '<tr class="totals-row">' + "".join(tot) + "</tr>"

    # ====== CUSTOMER ======
    if group_by == "Customer":
        ths = ['<th class="text-center">#</th>']
        if vis("customer"):       ths.append("<th>Customer</th>")
        if vis("customer_name"):  ths.append("<th>Customer Name</th>")
        if vis("customer_group"): ths.append("<th>Group</th>")
        if vis("invoice_count"):  ths.append('<th class="text-center">Inv</th>')
        if vis("qty"):            ths.append('<th class="text-right">Qty</th>')
        if vis("net_total"):      ths.append('<th class="text-right">Net Total</th>')
        if vis("grand_total"):    ths.append('<th class="text-right">Grand Total</th>')
        if vis("paid_amount"):    ths.append('<th class="text-right">Paid</th>')
        if vis("advance_amount"): ths.append('<th class="text-right">Advance</th>')
        if vis("outstanding"):    ths.append('<th class="text-right">Outstanding</th>')
        headers_html = "<tr>" + "".join(ths) + "</tr>"
        n = 1 + sum([vis("customer"), vis("customer_name"), vis("customer_group"), vis("invoice_count")])
        total_advance = sum(flt(d.get("advance_amount")) for d in data)
        rows_html = ""
        for idx, r in enumerate(data, 1):
            cls = "even" if idx % 2 == 0 else "odd"
            tds = [f'<td class="text-center">{idx}</td>']
            if vis("customer"):       tds.append(f'<td>{r.get("customer") or "-"}</td>')
            if vis("customer_name"):  tds.append(f'<td>{r.get("customer_name") or "-"}</td>')
            if vis("customer_group"): tds.append(f'<td>{r.get("customer_group") or "-"}</td>')
            if vis("invoice_count"):  tds.append(f'<td class="text-center">{r.get("invoice_count") or 0}</td>')
            if vis("qty"):            tds.append(f'<td class="text-right">{qty_fmt(r.get("qty"))}</td>')
            if vis("net_total"):      tds.append(f'<td class="text-right">{fmt(r.get("net_total"))}</td>')
            if vis("grand_total"):    tds.append(f'<td class="text-right">{fmt(r.get("grand_total"))}</td>')
            if vis("paid_amount"):    tds.append(f'<td class="text-right">{fmt(r.get("paid_amount"))}</td>')
            if vis("advance_amount"): tds.append(f'<td class="text-right">{fmt(r.get("advance_amount"))}</td>')
            if vis("outstanding"):    tds.append(f'<td class="text-right">{fmt(r.get("outstanding"))}</td>')
            rows_html += f'<tr class="{cls}">{"".join(tds)}</tr>'
        tot = [f'<td colspan="{n}" class="text-right"><strong>GRAND TOTAL</strong></td>']
        if vis("qty"):         tot.append(f'<td class="text-right"><strong>{qty_fmt(total_qty)}</strong></td>')
        if vis("net_total"):   tot.append(f'<td class="text-right"><strong>{fmt(total_net)}</strong></td>')
        if vis("grand_total"): tot.append(f'<td class="text-right"><strong>{fmt(total_grand)}</strong></td>')
        if vis("paid_amount"): tot.append(f'<td class="text-right"><strong>{fmt(total_paid)}</strong></td>')
        if vis("advance_amount"): tot.append(f'<td class="text-right"><strong>{fmt(total_advance)}</strong></td>')
        if vis("outstanding"): tot.append(f'<td class="text-right"><strong>{fmt(total_outstanding)}</strong></td>')
        return headers_html, rows_html, '<tr class="totals-row">' + "".join(tot) + "</tr>"

    # ====== ITEM ======
    if group_by == "Item":
        ths = ['<th class="text-center">#</th>']
        if vis("item_code"):     ths.append("<th>Item Code</th>")
        if vis("item_name"):     ths.append("<th>Item Name</th>")
        if vis("item_group"):    ths.append("<th>Group</th>")
        if vis("brand"):         ths.append("<th>Brand</th>")
        if vis("uom"):           ths.append("<th>UOM</th>")
        if vis("qty"):           ths.append('<th class="text-right">Qty</th>')
        if vis("avg_rate"):      ths.append('<th class="text-right">Avg Rate</th>')
        if vis("net_total"):     ths.append('<th class="text-right">Net Total</th>')
        if vis("invoice_count"): ths.append('<th class="text-center">Inv</th>')
        headers_html = "<tr>" + "".join(ths) + "</tr>"
        n = 1 + sum([vis("item_code"), vis("item_name"), vis("item_group"), vis("brand"), vis("uom")])
        rows_html = ""
        for idx, r in enumerate(data, 1):
            cls = "even" if idx % 2 == 0 else "odd"
            tds = [f'<td class="text-center">{idx}</td>']
            if vis("item_code"):     tds.append(f'<td>{r.get("item_code") or "-"}</td>')
            if vis("item_name"):     tds.append(f'<td>{r.get("item_name") or "-"}</td>')
            if vis("item_group"):    tds.append(f'<td>{r.get("item_group") or "-"}</td>')
            if vis("brand"):         tds.append(f'<td>{r.get("brand") or "-"}</td>')
            if vis("uom"):           tds.append(f'<td>{r.get("uom") or "-"}</td>')
            if vis("qty"):           tds.append(f'<td class="text-right">{qty_fmt(r.get("qty"))}</td>')
            if vis("avg_rate"):      tds.append(f'<td class="text-right">{fmt(r.get("avg_rate"))}</td>')
            if vis("net_total"):     tds.append(f'<td class="text-right">{fmt(r.get("net_total"))}</td>')
            if vis("invoice_count"): tds.append(f'<td class="text-center">{r.get("invoice_count") or 0}</td>')
            rows_html += f'<tr class="{cls}">{"".join(tds)}</tr>'
        tot = [f'<td colspan="{n}" class="text-right"><strong>GRAND TOTAL</strong></td>']
        if vis("qty"):           tot.append(f'<td class="text-right"><strong>{qty_fmt(total_qty)}</strong></td>')
        if vis("avg_rate"):      tot.append("<td></td>")
        if vis("net_total"):     tot.append(f'<td class="text-right"><strong>{fmt(total_net)}</strong></td>')
        if vis("invoice_count"): tot.append("<td></td>")
        return headers_html, rows_html, '<tr class="totals-row">' + "".join(tot) + "</tr>"

    # ====== ITEM GROUP ======
    if group_by == "Item Group":
        ths = ['<th class="text-center">#</th>']
        if vis("item_group"):  ths.append("<th>Item Group</th>")
        if vis("item_count"):  ths.append('<th class="text-center">Items</th>')
        if vis("qty"):         ths.append('<th class="text-right">Qty</th>')
        if vis("net_total"):   ths.append('<th class="text-right">Net Total</th>')
        if vis("grand_total"): ths.append('<th class="text-right">Grand Total</th>')
        headers_html = "<tr>" + "".join(ths) + "</tr>"
        n = 1 + sum([vis("item_group"), vis("item_count")])
        rows_html = ""
        for idx, r in enumerate(data, 1):
            cls = "even" if idx % 2 == 0 else "odd"
            ig  = r.get("item_group") or "-"
            tds = [f'<td class="text-center">{idx}</td>']
            if vis("item_group"):  tds.append(f"<td><strong>{ig}</strong></td>")
            if vis("item_count"):  tds.append(f'<td class="text-center">{r.get("item_count") or 0}</td>')
            if vis("qty"):         tds.append(f'<td class="text-right">{qty_fmt(r.get("qty"))}</td>')
            if vis("net_total"):   tds.append(f'<td class="text-right">{fmt(r.get("net_total"))}</td>')
            if vis("grand_total"): tds.append(f'<td class="text-right">{fmt(r.get("grand_total"))}</td>')
            rows_html += f'<tr class="{cls}">{"".join(tds)}</tr>'
        tot = [f'<td colspan="{n}" class="text-right"><strong>GRAND TOTAL</strong></td>']
        if vis("qty"):         tot.append(f'<td class="text-right"><strong>{qty_fmt(total_qty)}</strong></td>')
        if vis("net_total"):   tot.append(f'<td class="text-right"><strong>{fmt(total_net)}</strong></td>')
        if vis("grand_total"): tot.append(f'<td class="text-right"><strong>{fmt(total_grand)}</strong></td>')
        return headers_html, rows_html, '<tr class="totals-row">' + "".join(tot) + "</tr>"

    # ====== DATE ======
    if group_by == "Date":
        ths = ['<th class="text-center">#</th>']
        if vis("posting_date"):   ths.append('<th class="text-center">Date</th>')
        if vis("invoice_count"):  ths.append('<th class="text-center">Invoices</th>')
        if vis("customer_count"): ths.append('<th class="text-center">Customers</th>')
        if vis("qty"):            ths.append('<th class="text-right">Qty</th>')
        if vis("net_total"):      ths.append('<th class="text-right">Net Total</th>')
        if vis("grand_total"):    ths.append('<th class="text-right">Grand Total</th>')
        if vis("paid_amount"):    ths.append('<th class="text-right">Paid</th>')
        if vis("outstanding"):    ths.append('<th class="text-right">Outstanding</th>')
        headers_html = "<tr>" + "".join(ths) + "</tr>"
        n = 1 + sum([vis("posting_date"), vis("invoice_count"), vis("customer_count")])
        rows_html = ""
        for idx, r in enumerate(data, 1):
            cls = "even" if idx % 2 == 0 else "odd"
            pd  = formatdate(r.get("posting_date")) if r.get("posting_date") else "-"
            tds = [f'<td class="text-center">{idx}</td>']
            if vis("posting_date"):   tds.append(f'<td class="text-center">{pd}</td>')
            if vis("invoice_count"):  tds.append(f'<td class="text-center">{r.get("invoice_count") or 0}</td>')
            if vis("customer_count"): tds.append(f'<td class="text-center">{r.get("customer_count") or 0}</td>')
            if vis("qty"):            tds.append(f'<td class="text-right">{qty_fmt(r.get("qty"))}</td>')
            if vis("net_total"):      tds.append(f'<td class="text-right">{fmt(r.get("net_total"))}</td>')
            if vis("grand_total"):    tds.append(f'<td class="text-right">{fmt(r.get("grand_total"))}</td>')
            if vis("paid_amount"):    tds.append(f'<td class="text-right">{fmt(r.get("paid_amount"))}</td>')
            if vis("outstanding"):    tds.append(f'<td class="text-right">{fmt(r.get("outstanding"))}</td>')
            rows_html += f'<tr class="{cls}">{"".join(tds)}</tr>'
        tot = [f'<td colspan="{n}" class="text-right"><strong>GRAND TOTAL</strong></td>']
        if vis("qty"):         tot.append(f'<td class="text-right"><strong>{qty_fmt(total_qty)}</strong></td>')
        if vis("net_total"):   tot.append(f'<td class="text-right"><strong>{fmt(total_net)}</strong></td>')
        if vis("grand_total"): tot.append(f'<td class="text-right"><strong>{fmt(total_grand)}</strong></td>')
        if vis("paid_amount"): tot.append(f'<td class="text-right"><strong>{fmt(total_paid)}</strong></td>')
        if vis("outstanding"): tot.append(f'<td class="text-right"><strong>{fmt(total_outstanding)}</strong></td>')
        return headers_html, rows_html, '<tr class="totals-row">' + "".join(tot) + "</tr>"

    # ====== INVOICE ======
    if group_by == "Invoice":
        ths = ['<th class="text-center">#</th>']
        if vis("posting_date"):  ths.append('<th class="text-center">Date</th>')
        if vis("invoice"):       ths.append("<th>Invoice</th>")
        if vis("customer"):      ths.append("<th>Customer</th>")
        if vis("customer_name"): ths.append("<th>Customer Name</th>")
        if vis("item_count"):    ths.append('<th class="text-center">Items</th>')
        if vis("qty"):           ths.append('<th class="text-right">Qty</th>')
        if vis("net_total"):     ths.append('<th class="text-right">Net Total</th>')
        if vis("grand_total"):   ths.append('<th class="text-right">Grand Total</th>')
        if vis("paid_amount"):   ths.append('<th class="text-right">Paid</th>')
        if vis("outstanding"):   ths.append('<th class="text-right">Outstanding</th>')
        headers_html = "<tr>" + "".join(ths) + "</tr>"
        n = 1 + sum([vis("posting_date"), vis("invoice"), vis("customer"), vis("customer_name"), vis("item_count")])
        rows_html = ""
        for idx, r in enumerate(data, 1):
            cls = "even" if idx % 2 == 0 else "odd"
            pd  = formatdate(r.get("posting_date")) if r.get("posting_date") else "-"
            tds = [f'<td class="text-center">{idx}</td>']
            if vis("posting_date"):  tds.append(f'<td class="text-center">{pd}</td>')
            if vis("invoice"):       tds.append(f'<td>{r.get("invoice") or "-"}</td>')
            if vis("customer"):      tds.append(f'<td>{r.get("customer") or "-"}</td>')
            if vis("customer_name"): tds.append(f'<td>{r.get("customer_name") or "-"}</td>')
            if vis("item_count"):    tds.append(f'<td class="text-center">{r.get("item_count") or 0}</td>')
            if vis("qty"):           tds.append(f'<td class="text-right">{qty_fmt(r.get("qty"))}</td>')
            if vis("net_total"):     tds.append(f'<td class="text-right">{fmt(r.get("net_total"))}</td>')
            if vis("grand_total"):   tds.append(f'<td class="text-right">{fmt(r.get("grand_total"))}</td>')
            if vis("paid_amount"):   tds.append(f'<td class="text-right">{fmt(r.get("paid_amount"))}</td>')
            if vis("outstanding"):   tds.append(f'<td class="text-right">{fmt(r.get("outstanding"))}</td>')
            rows_html += f'<tr class="{cls}">{"".join(tds)}</tr>'
        tot = [f'<td colspan="{n}" class="text-right"><strong>GRAND TOTAL</strong></td>']
        if vis("qty"):         tot.append(f'<td class="text-right"><strong>{qty_fmt(total_qty)}</strong></td>')
        if vis("net_total"):   tot.append(f'<td class="text-right"><strong>{fmt(total_net)}</strong></td>')
        if vis("grand_total"): tot.append(f'<td class="text-right"><strong>{fmt(total_grand)}</strong></td>')
        if vis("paid_amount"): tot.append(f'<td class="text-right"><strong>{fmt(total_paid)}</strong></td>')
        if vis("outstanding"): tot.append(f'<td class="text-right"><strong>{fmt(total_outstanding)}</strong></td>')
        return headers_html, rows_html, '<tr class="totals-row">' + "".join(tot) + "</tr>"

    # ====== DETAILED (default) ======
    ths = ['<th class="text-center">#</th>']
    if vis("posting_date"):  ths.append('<th class="text-center">Date</th>')
    if vis("invoice"):       ths.append("<th>Invoice</th>")
    if vis("customer"):      ths.append("<th>Customer</th>")
    if vis("customer_name"): ths.append("<th>Customer Name</th>")
    if vis("item_name"):     ths.append("<th>Item Name</th>")
    if vis("qty"):           ths.append('<th class="text-right">Qty</th>')
    if vis("uom"):           ths.append("<th>UOM</th>")
    if vis("rate"):          ths.append('<th class="text-right">Rate</th>')
    if vis("net_total"):     ths.append('<th class="text-right">Net Amt</th>')
    if vis("grand_total"):   ths.append('<th class="text-right">Grand Total</th>')
    headers_html = "<tr>" + "".join(ths) + "</tr>"
    n = 1 + sum([vis("posting_date"), vis("invoice"), vis("customer"), vis("customer_name"), vis("item_name")])
    rows_html = ""
    seen_inv_pdf = set()
    for item_idx, r in enumerate(data, 1):
        cls = "even" if item_idx % 2 == 0 else "odd"
        inv = r.get("invoice") or ""
        is_first = inv not in seen_inv_pdf
        if inv:
            seen_inv_pdf.add(inv)
        pd   = formatdate(r.get("posting_date")) if (is_first and r.get("posting_date")) else ""
        invs = inv if is_first else ""
        cust = (r.get("customer") or "") if is_first else ""
        cnam = (r.get("customer_name") or "") if is_first else ""
        gt   = flt(r.get("grand_total"))
        tds  = [f'<td class="text-center">{item_idx}</td>']
        if vis("posting_date"):  tds.append(f'<td class="text-center">{pd}</td>')
        if vis("invoice"):       tds.append(f"<td>{invs}</td>")
        if vis("customer"):      tds.append(f"<td>{cust}</td>")
        if vis("customer_name"): tds.append(f"<td>{cnam}</td>")
        if vis("item_name"):     tds.append(f'<td>{r.get("item_name") or "-"}</td>')
        if vis("qty"):           tds.append(f'<td class="text-right">{qty_fmt(r.get("qty"))}</td>')
        if vis("uom"):           tds.append(f'<td>{r.get("uom") or "-"}</td>')
        if vis("rate"):          tds.append(f'<td class="text-right">{fmt(r.get("rate"))}</td>')
        if vis("net_total"):     tds.append(f'<td class="text-right">{fmt(r.get("net_total"))}</td>')
        if vis("grand_total"):   tds.append(f'<td class="text-right">{fmt(gt) if gt else "-"}</td>')
        rows_html += f'<tr class="{cls}">{"".join(tds)}</tr>'
    tot = [f'<td colspan="{n}" class="text-right"><strong>GRAND TOTAL</strong></td>']
    if vis("qty"):         tot.append(f'<td class="text-right"><strong>{qty_fmt(total_qty)}</strong></td>')
    if vis("uom"):         tot.append("<td></td>")
    if vis("rate"):        tot.append("<td></td>")
    if vis("net_total"):   tot.append(f'<td class="text-right"><strong>{fmt(total_net)}</strong></td>')
    if vis("grand_total"): tot.append(f'<td class="text-right"><strong>{fmt(total_grand)}</strong></td>')
    totals_html = '<tr class="totals-row">' + "".join(tot) + "</tr>"
    return headers_html, rows_html, totals_html

def get_pdf_css():
    return """
        @page { size: A4 landscape; margin: 8mm; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 7.5pt;
               color: #2d3748; background: #fff; line-height: 1.3; }
        .letter-head { margin-bottom: 10px; padding-bottom: 6px; border-bottom: 2px solid #5e72e4; }
        .report-header { display: flex; justify-content: space-between; align-items: flex-start;
                         margin-bottom: 10px; padding: 12px 16px;
                         background: linear-gradient(135deg, #4299e1 0%, #667eea 50%, #764ba2 100%);
                         color: white; border-radius: 8px;
                         box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .report-title h1 { font-size: 16pt; font-weight: 700; margin-bottom: 3px; letter-spacing: 0.3px; }
        .report-title .subtitle { font-size: 8.5pt; opacity: 0.92; font-weight: 400; }
        .report-meta { text-align: right; font-size: 7.5pt; }
        .report-meta .label { opacity: 0.85; }
        .filters-section { background: #f0f4ff; border-left: 4px solid #667eea;
                          padding: 8px 12px; margin-bottom: 10px; border-radius: 4px; }
        .filters-title { font-size: 8pt; font-weight: 700; color: #5e72e4;
                        margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
        .filters-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px 12px; }
        .filter-item { font-size: 7.5pt; }
        .filter-label { font-weight: 600; color: #4a5568; }
        .filter-value { color: #2d3748; }
        .summary-cards { display: grid; grid-template-columns: repeat(5, 1fr);
                        gap: 8px; margin-bottom: 10px; }
        .summary-card { padding: 10px; border-radius: 6px; color: white; text-align: center;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
        .card-blue { background: linear-gradient(135deg, #7ab8e8, #5a92d4); }
        .card-green { background: linear-gradient(135deg, #7cc99a, #5cb37e); }
        .card-orange { background: linear-gradient(135deg, #f5a96b, #e8884a); }
        .card-red { background: linear-gradient(135deg, #f08585, #e06868); }
        .card-purple { background: linear-gradient(135deg, #b08ee0, #9374c8); }
        .card-grey { background: linear-gradient(135deg, #95a3b8, #7a8aa3); }
        .summary-card .label { font-size: 7pt; opacity: 0.95; margin-bottom: 3px;
                              text-transform: uppercase; letter-spacing: 0.4px; font-weight: 500; }
        .summary-card .value { font-size: 12pt; font-weight: 700; }
        table.report-table { width: 100%; border-collapse: collapse; font-size: 6.8pt; margin-bottom: 10px; }
        table.report-table thead { background: linear-gradient(135deg, #4299e1 0%, #667eea 100%); color: white; }
        table.report-table th { padding: 6px 3px; text-align: left; font-weight: 600;
                                font-size: 6.8pt; text-transform: uppercase; letter-spacing: 0.2px;
                                border: 1px solid #5a92d4; }
        table.report-table th.text-right { text-align: right; }
        table.report-table th.text-center { text-align: center; }
        table.report-table td { padding: 4px 3px; border: 1px solid #e2e8f0; }
        table.report-table tr.odd { background: #ffffff; }
        table.report-table tr.even { background: #f7fafc; }
        table.report-table .text-right { text-align: right; }
        table.report-table .text-center { text-align: center; }
        tr.totals-row { background: linear-gradient(135deg, #4299e1, #667eea) !important; color: white; font-weight: 700; }
        tr.totals-row td { padding: 9px 3px; border-color: #5a92d4; font-size: 8pt; }
        .footer { margin-top: 14px; padding-top: 6px; border-top: 1px solid #e2e8f0;
                 display: flex; justify-content: space-between; font-size: 6.5pt; color: #718096; }
        .signature-section { display: grid; grid-template-columns: repeat(3, 1fr);
                            gap: 25px; margin-top: 30px; padding-top: 6px; }
        .signature-box { text-align: center; font-size: 7.5pt; color: #4a5568; }
        .signature-line { border-top: 1px solid #2d3748; margin: 22px 15px 4px 15px; }
        @media print {
            body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
            tr { page-break-inside: avoid; }
            thead { display: table-header-group; }
            .summary-cards { page-break-inside: avoid; }
        }
    """