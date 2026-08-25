# -*- coding: utf-8 -*-
# Copyright (c) 2026, Cyvetech and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from frappe.utils import (
    date_diff, flt, fmt_money, format_datetime, formatdate, get_datetime, nowdate
)


# ============================================================
# HELPERS
# ============================================================

def get_extra(filters):
    raw = filters.get("extra_columns") or []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = []
    return raw


# ============================================================
# EXECUTE
# ============================================================

def execute(filters=None):
    filters = filters or {}
    columns = get_columns(filters)
    data    = get_data(filters)
    return columns, data


# ============================================================
# COLUMNS
# ============================================================

def get_columns(filters):
    extra = get_extra(filters)

    cols = [
        {
            "label"    : _("Item Group / Item Name"),
            "fieldname": "display_name",
            "fieldtype": "Data",
            "width"    : 320
        }
    ]

    if "selling_price" in extra:
        cols.append({
            "label"    : _("Selling Price"),
            "fieldname": "selling_price",
            "fieldtype": "Currency",
            "width"    : 140
        })

    if "qty_on_hand" in extra:
        cols.append({
            "label"    : _("Qty on Hand"),
            "fieldname": "qty_on_hand",
            "fieldtype": "Float",
            "width"    : 120
        })

    if "brand" in extra:
        cols.append({
            "label"    : _("Brand"),
            "fieldname": "brand",
            "fieldtype": "Link",
            "options"  : "Brand",
            "width"    : 140
        })

    if "batch" in extra:
        cols.append({
            "label"    : _("Batch No"),
            "fieldname": "batch_no",
            "fieldtype": "Link",
            "options"  : "Batch",
            "width"    : 150
        })
        cols.append({
            "label"    : _("Expiry"),
            "fieldname": "expiry_date",
            "fieldtype": "Date",
            "width"    : 110
        })
        cols.append({
            "label"    : _("Qty Available"),
            "fieldname": "batch_qty",
            "fieldtype": "Float",
            "width"    : 120
        })

    if "description" in extra:
        cols.append({
            "label"    : _("Description"),
            "fieldname": "description",
            "fieldtype": "Data",
            "width"    : 300
        })

    return cols


def get_batch_map(item_codes, company):
    """item_code -> [{batch_no, expiry_date, qty}] with stock still on hand.

    Batch quantities live in two places in ERPNext v15+: older stock ledger
    entries carry ``batch_no`` directly, newer ones point at a Serial and
    Batch Bundle whose child rows hold the per-batch quantity. Both are
    summed here (the legacy branch skips rows that have a bundle so nothing
    is counted twice), mirroring the standard Batch-Wise Balance History.
    """
    if not item_codes:
        return {}

    params = {"items": tuple(item_codes), "company": company}

    rows = frappe.db.sql("""
        SELECT sle.item_code, sle.batch_no, SUM(sle.actual_qty) AS qty
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabWarehouse` wh ON wh.name = sle.warehouse
        WHERE sle.is_cancelled = 0
          AND sle.docstatus < 2
          AND IFNULL(sle.batch_no, '') != ''
          AND IFNULL(sle.serial_and_batch_bundle, '') = ''
          AND sle.item_code IN %(items)s
          AND wh.company = %(company)s
        GROUP BY sle.item_code, sle.batch_no
    """, params, as_dict=1) or []

    if frappe.db.table_exists("Serial and Batch Entry"):
        rows += frappe.db.sql("""
            SELECT sle.item_code, sbe.batch_no, SUM(sbe.qty) AS qty
            FROM `tabStock Ledger Entry` sle
            INNER JOIN `tabSerial and Batch Entry` sbe
                    ON sbe.parent = sle.serial_and_batch_bundle
            INNER JOIN `tabWarehouse` wh ON wh.name = sle.warehouse
            WHERE sle.is_cancelled = 0
              AND sle.docstatus < 2
              AND IFNULL(sbe.batch_no, '') != ''
              AND sle.item_code IN %(items)s
              AND wh.company = %(company)s
            GROUP BY sle.item_code, sbe.batch_no
        """, params, as_dict=1) or []

    totals = {}
    for r in rows:
        key = (r["item_code"], r["batch_no"])
        totals[key] = totals.get(key, 0.0) + flt(r["qty"])

    batch_names = list({b for _code, b in totals})
    expiry = {}
    if batch_names:
        for b in frappe.get_all(
            "Batch",
            filters={"name": ("in", batch_names)},
            fields=["name", "expiry_date"],
        ):
            expiry[b["name"]] = b["expiry_date"]

    batch_map = {}
    for (code, batch_no), qty in totals.items():
        # only batches still holding stock are "available"
        if flt(qty) <= 0:
            continue
        batch_map.setdefault(code, []).append({
            "batch_no"   : batch_no,
            "expiry_date": expiry.get(batch_no),
            "qty"        : flt(qty),
        })

    # earliest expiry first (FEFO); undated batches last
    for code in batch_map:
        batch_map[code].sort(
            key=lambda b: (b["expiry_date"] is None, b["expiry_date"], b["batch_no"])
        )

    return batch_map


# ============================================================
# DATA
# ============================================================

def get_data(filters):
    extra      = get_extra(filters)
    conditions = "i.docstatus < 2"
    params     = {}

    # Always exclude Fixed Asset items
    conditions += " AND COALESCE(i.is_fixed_asset, 0) = 0"

    if not filters.get("disabled"):
        conditions += " AND i.disabled = 0"

    if filters.get("item_group"):
        conditions += " AND i.item_group = %(item_group)s"
        params["item_group"] = filters["item_group"]

    if filters.get("item_name"):
        conditions += " AND i.item_name LIKE %(item_name)s"
        params["item_name"] = "%" + filters["item_name"] + "%"

    if filters.get("is_sales_item"):
        conditions += " AND i.is_sales_item = 1"

    if filters.get("is_purchase_item"):
        conditions += " AND i.is_purchase_item = 1"

    if filters.get("is_stock_item"):
        conditions += " AND i.is_stock_item = 1"

    # Show only items that have stock on hand (actual_qty > 0 in any warehouse of the company)
    if filters.get("stock_on_hand_only"):
        company = filters.get("company")
        if company:
            conditions += """ AND i.name IN (
                SELECT b.item_code
                FROM `tabBin` b
                INNER JOIN `tabWarehouse` wh ON wh.name = b.warehouse
                WHERE wh.company = %(stock_company)s
                  AND b.actual_qty > 0
            )"""
            params["stock_company"] = company
        else:
            conditions += """ AND i.name IN (
                SELECT item_code FROM `tabBin` WHERE actual_qty > 0
            )"""

    raw = frappe.db.sql("""
        SELECT
            i.name          AS item_code,
            i.item_name     AS item_name,
            i.item_group    AS item_group,
            i.brand         AS brand,
            i.description   AS description,
            i.is_stock_item AS is_stock_item,
            i.disabled      AS disabled
        FROM `tabItem` i
        WHERE {conditions}
        ORDER BY i.item_group, i.item_name
    """.format(conditions=conditions), params, as_dict=1) or []

    if not raw:
        return []

    item_codes = [r["item_code"] for r in raw]

    # Selling Price
    price_map = {}
    if "selling_price" in extra and item_codes:
        price_list = filters.get("price_list") or "Standard Selling"
        prices = frappe.db.sql("""
            SELECT item_code, price_list_rate
            FROM `tabItem Price`
            WHERE price_list  = %(price_list)s
              AND item_code  IN %(items)s
              AND (valid_upto IS NULL OR valid_upto >= CURDATE())
            ORDER BY valid_from DESC
        """, {
            "price_list": price_list,
            "items"     : tuple(item_codes)
        }, as_dict=1) or []

        for p in prices:
            if p["item_code"] not in price_map:
                price_map[p["item_code"]] = flt(p["price_list_rate"])

    # Stock
    stock_map = {}
    if "qty_on_hand" in extra and item_codes:
        company    = filters.get("company")
        stock_rows = frappe.db.sql("""
            SELECT
                b.item_code,
                SUM(b.actual_qty) AS qty_on_hand
            FROM `tabBin` b
            LEFT JOIN `tabWarehouse` wh ON wh.name = b.warehouse
            WHERE b.item_code IN %(items)s
              AND wh.company   = %(company)s
            GROUP BY b.item_code
        """, {
            "items"  : tuple(item_codes),
            "company": company
        }, as_dict=1) or []

        for s in stock_rows:
            stock_map[s["item_code"]] = flt(s["qty_on_hand"])

    # Batches (one sub-row per batch under its item)
    batch_map = {}
    if "batch" in extra and item_codes:
        batch_map = get_batch_map(item_codes, filters.get("company"))

    # Build grouped rows
    rows          = []
    current_group = None

    for item in raw:
        group = item.get("item_group") or "Uncategorized"

        if group != current_group:
            rows.append({
                "display_name" : group,
                "selling_price": None,
                "qty_on_hand"  : None,
                "brand"        : "",
                "description"  : "",
                "is_group_row" : 1,
                "item_code"    : "",
                "disabled"     : 0,
            })
            current_group = group

        code = item.get("item_code") or ""
        rows.append({
            "display_name" : "    " + (item.get("item_name") or code),
            "item_code"    : code,
            "selling_price": price_map.get(code),
            "qty_on_hand"  : stock_map.get(code, 0.0),
            "brand"        : item.get("brand") or "",
            "description"  : (item.get("description") or "")[:120],
            "is_group_row" : 0,
            "disabled"     : item.get("disabled") or 0,
        })

        for batch in batch_map.get(code, []):
            rows.append({
                "display_name" : "        " + (batch["batch_no"] or ""),
                "item_code"    : code,
                "selling_price": None,
                "qty_on_hand"  : None,
                "brand"        : "",
                "description"  : "",
                "batch_no"     : batch["batch_no"],
                "expiry_date"  : batch["expiry_date"],
                "batch_qty"    : batch["qty"],
                "is_group_row" : 0,
                "is_batch_row" : 1,
                "disabled"     : item.get("disabled") or 0,
            })

    return rows


# ============================================================
# PDF EXPORT
# ============================================================

@frappe.whitelist()
def get_pdf_html(filters, data):
    if isinstance(filters, str):
        filters = json.loads(filters)
    if isinstance(data, str):
        data = json.loads(data)

    extra       = get_extra(filters)
    company     = filters.get("company")
    company_doc = frappe.get_doc("Company", company) if company else None
    currency    = company_doc.default_currency if company_doc else "UGX"

    # Company header
    letter_head_html = build_company_header(company_doc)

    # Table
    table_html = build_pdf_table(data, extra, currency)
    now        = format_datetime(get_datetime(), "dd MMM yyyy HH:mm")
    css        = get_pdf_css()

    # Filter summary
    price_list   = filters.get("price_list") or "Standard Selling"
    filter_pairs = [
        ("Item Group",       filters.get("item_group") or "All"),
        ("Item Name",        filters.get("item_name")  or "All"),
        ("Price List",       price_list if "selling_price" in extra else ""),
        ("Show Disabled",    "Yes" if filters.get("disabled")         else "No"),
        ("Sales Items Only", "Yes" if filters.get("is_sales_item")    else "No"),
        ("Purchase Only",    "Yes" if filters.get("is_purchase_item") else "No"),
        ("Stock Items Only", "Yes" if filters.get("is_stock_item")    else "No"),
    ]
    filter_html = "".join(
        '<div class="filter-item">'
        '<span class="filter-label">' + lbl + ':</span> '
        '<span class="filter-value">' + val + '</span>'
        '</div>'
        for lbl, val in filter_pairs if val
    )

    # Active column badges
    badge_map = {
        "selling_price": "Selling Price",
        "qty_on_hand"  : "Current Stock",
        "batch"        : "Batch / Expiry / Qty",
        "brand"        : "Brand",
        "description"  : "Description",
    }
    active_cols = [badge_map[k] for k in badge_map if k in extra]
    cols_badge  = " | ".join(active_cols) or "Item Name only"

    html = (
        "<!DOCTYPE html><html>"
        "<head><meta charset='UTF-8'>"
        "<title>Item List Report</title>"
        "<style>" + css + "</style>"
        "</head><body>"
        + letter_head_html
        + "<div class='report-header'>"
            "<div class='report-title'>"
                "<h1>Item List Report</h1>"
                "<div class='subtitle'>Company: " + str(company or "")
                + " &nbsp;|&nbsp; Generated: " + str(now) + "</div>"
                "<div class='col-badges'>Columns: " + cols_badge + "</div>"
            "</div>"
            "<div class='report-meta'>"
                "<div><span class='label'>Generated By:</span> "
                "<strong>" + str(frappe.session.user) + "</strong></div>"
                "<div><span class='label'>Date:</span> " + str(now) + "</div>"
            "</div>"
        "</div>"
        "<div class='filters-section'>"
            "<div class='filters-title'>Applied Filters</div>"
            "<div class='filters-grid'>" + filter_html + "</div>"
        "</div>"
        + table_html
        + "<div class='footer'>"
            "<div>Item List Report - " + str(company or "") + "</div>"
            "<div>Generated by " + str(frappe.session.user)
            + " on " + str(now) + "</div>"
        "</div>"
        "</body></html>"
    )

    return html


# ============================================================
# COMPANY HEADER
# ============================================================

def build_company_header(company_doc):
    if not company_doc:
        return ""

    letter_head_content = ""
    if company_doc.default_letter_head:
        try:
            lh  = frappe.get_doc("Letter Head", company_doc.default_letter_head)
            raw = lh.content or ""
            if raw:
                letter_head_content = frappe.render_template(
                    raw,
                    {"doc": frappe._dict({"company": company_doc.name})}
                )
        except Exception as e:
            frappe.log_error(str(e), "Letter Head Render Error")

    if letter_head_content:
        return '<div class="letter-head">' + letter_head_content + '</div>'

    # Fallback
    logo_html = ""
    if company_doc.company_logo:
        logo_html = (
            '<img src="' + company_doc.company_logo + '" '
            'style="height:65px; max-width:220px; object-fit:contain;" />'
        )

    def field(f):
        return str(company_doc.get(f) or "")

    contact_lines = ""
    if field("address_line1"):
        contact_lines += "<div>" + field("address_line1") + "</div>"
    if field("address_line2"):
        contact_lines += "<div>" + field("address_line2") + "</div>"
    if field("city"):
        contact_lines += "<div>" + field("city") + "</div>"
    if field("phone_no"):
        contact_lines += "<div>Tel: "   + field("phone_no") + "</div>"
    if field("email"):
        contact_lines += "<div>Email: " + field("email")    + "</div>"
    if field("website"):
        contact_lines += "<div>Web: "   + field("website")  + "</div>"

    return (
        '<div class="letter-head">'
            '<div class="lh-inner">'
                '<div class="lh-logo">' + logo_html + '</div>'
                '<div class="lh-info">'
                    '<div class="lh-company-name">'
                    + company_doc.company_name
                    + '</div>'
                    '<div class="lh-contact">'
                    + contact_lines
                    + '</div>'
                '</div>'
            '</div>'
        '</div>'
    )


# ============================================================
# TABLE BUILDER
# ============================================================

def build_pdf_table(data, extra, currency):
    show_price = "selling_price" in extra
    show_stock = "qty_on_hand"   in extra
    show_batch = "batch"         in extra
    show_brand = "brand"         in extra
    show_desc  = "description"   in extra

    def fmt(v):
        return fmt_money(flt(v), currency=currency) if flt(v) else "-"

    # Column widths as relative weights, normalised to 100% so the table
    # always spans exactly the usable A4 width (with table-layout:fixed) no
    # matter which optional columns are shown — nothing overflows the page.
    weights = [("idx", 0.5), ("name", 4.0)]
    if show_price: weights.append(("price", 1.6))
    if show_stock: weights.append(("qty",   1.4))
    if show_batch:
        weights.append(("batch",  1.8))
        weights.append(("expiry", 1.2))
        weights.append(("bqty",   1.3))
    if show_brand: weights.append(("brand", 1.6))
    if show_desc:  weights.append(("desc",  3.5))

    total_w   = sum(w for _, w in weights)
    pct       = {k: round(w / total_w * 100, 2) for k, w in weights}
    col_count = len(weights)  # for the group-row colspan

    # Header
    headers = (
        '<tr>'
        '<th class="text-center" style="width:' + str(pct["idx"]) + '%;">#</th>'
        '<th style="width:' + str(pct["name"]) + '%;">Item Group / Item Name</th>'
    )
    if show_price:
        headers += '<th class="text-right" style="width:' + str(pct["price"]) + '%;">Selling Price</th>'
    if show_stock:
        headers += '<th class="text-right" style="width:' + str(pct["qty"]) + '%;">Qty on Hand</th>'
    if show_batch:
        headers += '<th style="width:' + str(pct["batch"]) + '%;">Batch No</th>'
        headers += '<th class="text-center" style="width:' + str(pct["expiry"]) + '%;">Expiry</th>'
        headers += '<th class="text-right" style="width:' + str(pct["bqty"]) + '%;">Qty Available</th>'
    if show_brand:
        headers += '<th style="width:' + str(pct["brand"]) + '%;">Brand</th>'
    if show_desc:
        headers += '<th style="width:' + str(pct["desc"]) + '%;">Description</th>'
    headers += '</tr>'

    rows_html  = ""
    item_index = 0

    for row in data:
        if row.get("is_group_row"):
            group_name = row.get("display_name") or ""
            rows_html += (
                '<tr class="group-header-row">'
                '<td colspan="' + str(col_count) + '" class="group-name">'
                '&#9658; &nbsp;<strong>' + group_name + '</strong>'
                '</td></tr>'
            )
        elif row.get("is_batch_row"):
            # stale batch rows (batch columns since switched off) would push
            # every following cell out of alignment - drop them
            if not show_batch:
                continue

            # batch detail line: only the batch columns carry values
            expiry = row.get("expiry_date")
            expiry_str, expiry_style = "-", ""
            if expiry:
                expiry_str = formatdate(expiry)
                days = date_diff(expiry, nowdate())
                if days < 0:
                    expiry_str += " (expired)"
                    expiry_style = "color:#c53030; font-weight:700;"
                elif days <= 90:
                    expiry_style = "color:#b7791f; font-weight:600;"

            rows_html += '<tr class="batch-row">'
            rows_html += '<td></td>'
            rows_html += (
                '<td class="item-name-cell" style="padding-left:26px; color:#4a5568;">'
                '&#8226; ' + (row.get("batch_no") or "") + '</td>'
            )
            if show_price:
                rows_html += '<td></td>'
            if show_stock:
                rows_html += '<td></td>'
            rows_html += '<td style="color:#4a5568;">' + (row.get("batch_no") or "-") + '</td>'
            rows_html += '<td class="text-center" style="' + expiry_style + '">' + expiry_str + '</td>'
            rows_html += (
                '<td class="text-right" style="color:#2b6cb0; font-weight:600;">'
                + "{:,.2f}".format(flt(row.get("batch_qty"))) + '</td>'
            )
            if show_brand:
                rows_html += '<td></td>'
            if show_desc:
                rows_html += '<td></td>'
            rows_html += '</tr>'

        else:
            item_index += 1
            cls  = "even" if item_index % 2 == 0 else "odd"
            name = (row.get("display_name") or "").strip()

            qty       = flt(row.get("qty_on_hand"))
            qty_str   = "{:,.2f}".format(qty)
            qty_style = (
                "color:#e53e3e; font-weight:700;"
                if qty <= 0
                else "color:#276749; font-weight:600;"
            )

            rows_html += '<tr class="' + cls + '">'
            rows_html += (
                '<td class="text-center" style="color:#718096;">'
                + str(item_index) + '</td>'
            )
            rows_html += '<td class="item-name-cell">' + name + '</td>'

            if show_price:
                rows_html += (
                    '<td class="text-right selling-rate">'
                    + fmt(row.get("selling_price")) + '</td>'
                )
            if show_stock:
                rows_html += (
                    '<td class="text-right" style="' + qty_style + '">'
                    + qty_str + '</td>'
                )
            if show_batch:
                rows_html += '<td></td><td></td><td></td>'
            if show_brand:
                rows_html += (
                    '<td>' + (row.get("brand") or "-") + '</td>'
                )
            if show_desc:
                rows_html += (
                    '<td class="desc-cell">'
                    + (row.get("description") or "-") + '</td>'
                )

            rows_html += '</tr>'

    return (
        '<table class="report-table">'
        '<thead>' + headers + '</thead>'
        '<tbody>' + rows_html + '</tbody>'
        '</table>'
    )


# ============================================================
# CSS
# ============================================================

def get_pdf_css():
    return (
        "@page { size: A4 landscape; margin: 8mm; }"
        "* { box-sizing: border-box; margin: 0; padding: 0; }"
        "body { font-family: 'Helvetica Neue', Arial, sans-serif;"
        "       font-size: 7.5pt; color: #2d3748; background:#fff; line-height:1.35; }"

        ".letter-head { margin-bottom:10px; padding-bottom:8px;"
        "               border-bottom:3px solid #4299e1; }"
        ".lh-inner { display:flex; justify-content:space-between;"
        "            align-items:center; padding:6px 0; }"
        ".lh-company-name { font-size:14pt; font-weight:700;"
        "                   color:#2d3748; margin-bottom:4px; }"
        ".lh-contact { font-size:7.5pt; color:#4a5568; line-height:1.7; }"

        ".report-header { display:flex; justify-content:space-between;"
        "    align-items:flex-start; margin-bottom:10px; padding:12px 16px;"
        "    color:white; border-radius:8px;"
        "    background:linear-gradient(135deg,#4299e1 0%,#667eea 50%,#764ba2 100%); }"
        ".report-title h1 { font-size:16pt; font-weight:700; margin-bottom:3px; }"
        ".report-title .subtitle { font-size:8pt; opacity:0.9; }"
        ".col-badges { margin-top:5px; font-size:7pt; opacity:0.85;"
        "    background:rgba(255,255,255,0.15);"
        "    display:inline-block; padding:2px 8px; border-radius:10px; }"
        ".report-meta { text-align:right; font-size:7.5pt; }"
        ".report-meta .label { opacity:0.82; }"

        ".filters-section { background:#f0f4ff; border-left:4px solid #667eea;"
        "    padding:8px 12px; margin-bottom:10px; border-radius:4px; }"
        ".filters-title { font-size:8pt; font-weight:700; color:#5e72e4;"
        "    margin-bottom:4px; text-transform:uppercase; letter-spacing:0.5px; }"
        ".filters-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:4px 12px; }"
        ".filter-item { font-size:7.5pt; }"
        ".filter-label { font-weight:600; color:#4a5568; }"

        "table.report-table { width:100%; max-width:100%; border-collapse:collapse;"
        "    font-size:7pt; margin-bottom:10px; table-layout:fixed; }"
        "table.report-table thead {"
        "    background:linear-gradient(135deg,#4299e1 0%,#667eea 100%); color:white; }"
        "table.report-table th { padding:6px 5px; font-weight:600; font-size:6.8pt;"
        "    text-transform:uppercase; letter-spacing:0.2px; border:1px solid #5a92d4;"
        "    word-wrap:break-word; overflow-wrap:break-word; }"
        "table.report-table td { padding:4px 5px; border:1px solid #e2e8f0;"
        "    vertical-align:top; word-wrap:break-word; overflow-wrap:break-word;"
        "    word-break:break-word; }"
        "table.report-table tr.odd  { background:#ffffff; }"
        "table.report-table tr.even { background:#f7fafc; }"
        "table.report-table tr.batch-row { background:#fbfdff; }"
        "table.report-table tr.batch-row td { font-size:6.8pt; border-top:none;"
        " padding-top:2px; padding-bottom:2px; }"
        ".text-right  { text-align:right  !important; }"
        ".text-center { text-align:center !important; }"

        "tr.group-header-row { background:#ebf4ff !important; }"
        "td.group-name { font-size:8.5pt; font-weight:700; color:#2b6cb0;"
        "    padding:7px 8px !important;"
        "    border-left:5px solid #4299e1 !important; }"

        ".item-name-cell { padding-left:18px !important; color:#2d3748; }"
        ".selling-rate   { color:#276749; font-weight:600; }"
        ".desc-cell      { font-size:6.8pt; color:#718096; }"

        ".footer { margin-top:12px; padding-top:6px;"
        "    border-top:1px solid #e2e8f0; display:flex;"
        "    justify-content:space-between; font-size:6.5pt; color:#718096; }"

        "@media print {"
        "    body { -webkit-print-color-adjust:exact; print-color-adjust:exact; }"
        "    tr { page-break-inside:avoid; }"
        "    thead { display:table-header-group; }"
        "    tr.group-header-row { page-break-after:avoid; }"
        "}"
    )