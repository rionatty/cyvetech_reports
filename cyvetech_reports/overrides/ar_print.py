"""Branded printout for the standard Accounts Receivable reports.

Renders the same letterhead / gradient header / summary-card / table styling
as the other Cyvetech reports (helpers reused from Sales Analysis Report),
fed by the live report output including all Cyvetech enhancements (customer
name, A-Z sort, negative-balance filter, summarize by customer).
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, escape_html, flt, fmt_money, format_datetime, formatdate, get_datetime

from cyvetech_reports.cyvetech_reports.report.sales_analysis_report.sales_analysis_report import (
	_company_header_html,
	get_pdf_css,
)

ALLOWED_REPORTS = ("Accounts Receivable", "Accounts Receivable Summary")
NUMERIC_TYPES = {"Currency", "Float", "Int"}

# Overrides on top of the shared branded CSS for both AR printouts: tighter
# rows so long customer lists fit on fewer pages
_AR_PRINT_CSS = """
	table.report-table td { padding: 2px 3px; line-height: 1.15; }
	table.report-table th { padding: 4px 3px; }
	tr.totals-row td { padding: 6px 3px; }
"""

# Accounts Receivable (detail) only: A4 portrait instead of landscape, with
# the header scaled to the narrower page so it never clips. AR Summary keeps
# the shared landscape layout.
_AR_PORTRAIT_CSS = """
	@page { size: A4 portrait; margin: 10mm; }
	html, body { width: 100%; max-width: 100%; overflow-x: hidden; }
	body { font-size: 8pt; }
	.letter-head img { max-height: 55px; }
	.report-title h1 { font-size: 13pt; }
	.report-title .subtitle { font-size: 8pt; }
	.report-header { padding: 10px 12px; }
	.report-meta { font-size: 7pt; }
	.filters-grid { grid-template-columns: repeat(2, 1fr); }
"""


@frappe.whitelist()
def get_pdf_html(report_name, filters, visible_columns=None, summarize=0, group_summary=0):
	if report_name not in ALLOWED_REPORTS:
		frappe.throw(_("Unsupported report: {0}").format(report_name))

	if isinstance(filters, str):
		filters = json.loads(filters or "{}")
	filters = filters or {}
	if isinstance(visible_columns, str):
		visible_columns = json.loads(visible_columns or "[]")
	visible_columns = visible_columns or []

	if cint(summarize):
		filters["summarize_by_customer"] = 1

	# make sure the report enhancements are active, then run the report the
	# same way the desk does (permission checks included)
	from cyvetech_reports.overrides.accounts_receivable import apply_patch

	apply_patch()

	import frappe.desk.query_report as query_report

	result = query_report.run(report_name, filters=filters, ignore_prepared_report=True)

	all_columns = [
		c for c in (result.get("columns") or []) if isinstance(c, dict) and c.get("fieldname")
	]
	rows = [r for r in (result.get("result") or []) if isinstance(r, dict) and r.get("party")]

	if visible_columns:
		columns = [c for c in all_columns if c["fieldname"] in visible_columns]
	else:
		columns = [c for c in all_columns if not c.get("hidden")]
	if not columns:
		frappe.throw(_("No fields selected to print"))

	company = filters.get("company") or frappe.db.get_single_value(
		"Global Defaults", "default_company"
	)
	company_doc = frappe.get_doc("Company", company) if company else None
	currency = (company_doc and company_doc.default_currency) or "USD"

	if cint(group_summary):
		return _build_group_summary_html(report_name, filters, rows, company, company_doc, currency)

	letter_head_html = _company_header_html(company_doc)
	filter_html = _build_filter_html(filters, company)
	headers_html, rows_html, totals_html = _build_table(columns, rows, currency)

	# with only a few fields selected, a full-width table strands the amounts
	# at the far page edge - let it shrink so values sit next to the names
	compact_css = (
		"table.report-table { width: auto; min-width: 55%; }"
		" table.report-table td, table.report-table th { padding-left: 8px; padding-right: 8px; }"
		if len(columns) <= 3
		else ""
	)

	css = get_pdf_css() + _AR_PRINT_CSS
	if report_name == "Accounts Receivable":
		css += _AR_PORTRAIT_CSS
	css += compact_css

	report_date = filters.get("report_date")
	subtitle = _("As at {0}").format(formatdate(report_date)) if report_date else ""
	if cint(filters.get("summarize_by_customer")):
		subtitle += (" &nbsp;|&nbsp; " if subtitle else "") + _("Summarized by Customer")

	now = format_datetime(get_datetime(), "dd MMM yyyy HH:mm")
	user = escape_html(str(frappe.session.user))
	title = escape_html(_(report_name))
	company_label = escape_html(str(company or ""))

	return (
		'<!DOCTYPE html><html><head><meta charset="UTF-8">'
		"<title>" + title + "</title>"
		"<style>" + css + "</style></head><body>"
		+ letter_head_html
		+ '<div class="report-header">'
		'<div class="report-title">'
		"<h1>" + title + "</h1>"
		'<div class="subtitle">' + subtitle + "</div>"
		"</div>"
		'<div class="report-meta">'
		'<div><span class="label">' + _("Company") + ":</span> <strong>" + company_label + "</strong></div>"
		'<div><span class="label">' + _("Generated") + ":</span> " + str(now) + "</div>"
		'<div><span class="label">' + _("By") + ":</span> " + user + "</div>"
		"</div>"
		"</div>"
		'<div class="filters-section">'
		'<div class="filters-title">' + _("Applied Filters") + "</div>"
		'<div class="filters-grid">' + filter_html + "</div>"
		"</div>"
		+ '<table class="report-table"><thead>' + headers_html + "</thead>"
		"<tbody>" + rows_html + totals_html + "</tbody></table>"
		'<div class="signature-section">'
		'<div class="signature-box"><div class="signature-line"></div><div><strong>' + _("Prepared By") + "</strong></div></div>"
		'<div class="signature-box"><div class="signature-line"></div><div><strong>' + _("Verified By") + "</strong></div></div>"
		'<div class="signature-box"><div class="signature-line"></div><div><strong>' + _("Approved By") + "</strong></div></div>"
		"</div>"
		'<div class="footer">'
		"<div>" + title + " - " + company_label + "</div>"
		"<div>" + _("Generated by {0} on {1}").format(user, now) + "</div>"
		"</div>"
		"</body></html>"
	)


# Tally-style "Group Summary": one line per customer with the closing balance
# split into Debit / Credit, a running Carried Over at each page foot and the
# matching Brought Forward at the next page head - under the standard Cyvetech
# branded header.
#
# Pagination is computed server side (CSS cannot produce running per-page
# subtotals), so these are the row counts that fit an A4 portrait page. Page 1
# carries the letterhead, gradient band and Applied Filters, so it holds fewer
# lines than the continuation pages, which carry the band only. Lower these if
# a page ever spills a single row onto the next one.
_GROUP_SUMMARY_ROWS_FIRST = 34
_GROUP_SUMMARY_ROWS_REST = 44

_GROUP_SUMMARY_CSS = """
	.gs-page { page-break-after: always; }
	.gs-page:last-child { page-break-after: auto; }
	.gs-page + .gs-page .report-header { margin-top: 0; }
	table.gs { width: 100%; border-collapse: collapse; font-size: 8pt;
	           margin-top: 6px; }
	table.gs th, table.gs td { padding: 1.5px 6px; }
	table.gs td.amt, table.gs th.amt { text-align: right; width: 19%;
	                                   font-variant-numeric: tabular-nums; }
	table.gs th.gs-cb { text-align: center; font-weight: 600; font-size: 8pt;
	                    text-transform: uppercase; letter-spacing: 0.3px;
	                    color: #5e72e4; border-bottom: 1px solid #cbd5e0; }
	table.gs tr.gs-dc th { text-align: right; font-weight: 700; font-size: 7.5pt;
	                       text-transform: uppercase; letter-spacing: 0.3px;
	                       border-bottom: 1.5px solid #4a5568; }
	table.gs tr.gs-dc th.nm { text-align: left; }
	table.gs tbody tr.odd { background: #ffffff; }
	table.gs tbody tr.even { background: #f7fafc; }
	tr.gs-carry td { border-top: 1px solid #4a5568; font-weight: 600;
	                 padding-top: 3px; background: #fff; }
	tr.gs-total td { border-top: 1.5px solid #4a5568; border-bottom: 3px double #4a5568;
	                 font-weight: 700; padding: 5px 6px; background: #f0f4ff; }
	.gs-cont { text-align: right; font-size: 7.5pt; font-style: italic;
	           margin-top: 3px; color: #718096; }
"""


def _build_group_summary_html(report_name, filters, rows, company, company_doc, currency):
	def money(value):
		return fmt_money(flt(value), currency=currency) if flt(value) else ""

	entries = []
	for r in rows:
		balance = r.get("outstanding")
		if balance is None:
			balance = r.get("total_due")
		balance = flt(balance)
		if not balance:
			continue
		entries.append(
			{
				"name": r.get("customer_name") or r.get("party_name") or r.get("party") or "",
				"debit": balance if balance > 0 else 0.0,
				"credit": -balance if balance < 0 else 0.0,
			}
		)
	entries.sort(key=lambda e: e["name"].lower())

	# split into pages - the first page carries the full letterhead so it fits
	# fewer lines than the continuation pages
	pages = []
	if entries:
		pages.append(entries[:_GROUP_SUMMARY_ROWS_FIRST])
		rest = entries[_GROUP_SUMMARY_ROWS_FIRST:]
		for i in range(0, len(rest), _GROUP_SUMMARY_ROWS_REST):
			pages.append(rest[i : i + _GROUP_SUMMARY_ROWS_REST])
	else:
		pages.append([])

	company_label = escape_html(str(company or ""))
	title = escape_html(_(report_name))
	report_date = filters.get("report_date")
	period = _("As at {0}").format(formatdate(report_date)) if report_date else ""

	now = format_datetime(get_datetime(), "dd MMM yyyy HH:mm")
	user = escape_html(str(frappe.session.user))
	letter_head_html = _company_header_html(company_doc)
	filter_html = _build_filter_html(filters, company)
	total_pages = len(pages)

	def branded_head(page_no):
		"""Standard Cyvetech header: full letterhead + filters on page 1, the
		gradient band alone on continuation pages so they stay branded without
		spending a third of the page on it."""
		subtitle = escape_html(period)
		if total_pages > 1:
			subtitle += (" &nbsp;|&nbsp; " if subtitle else "") + _("Page {0} of {1}").format(
				page_no, total_pages
			)

		band = (
			'<div class="report-header">'
			'<div class="report-title">'
			"<h1>" + title + "</h1>"
			'<div class="subtitle">' + subtitle + "</div>"
			"</div>"
			'<div class="report-meta">'
			'<div><span class="label">' + _("Company") + ":</span> <strong>" + company_label + "</strong></div>"
			'<div><span class="label">' + _("Generated") + ":</span> " + str(now) + "</div>"
			'<div><span class="label">' + _("By") + ":</span> " + user + "</div>"
			"</div>"
			"</div>"
		)

		if page_no > 1:
			return band

		return (
			letter_head_html
			+ band
			+ '<div class="filters-section">'
			'<div class="filters-title">' + _("Applied Filters") + "</div>"
			'<div class="filters-grid">' + filter_html + "</div>"
			"</div>"
		)

	def column_head():
		return (
			"<thead>"
			'<tr><th></th><th class="amt gs-cb" colspan="2">' + _("Closing Balance") + "</th></tr>"
			'<tr class="gs-dc"><th class="nm">' + _("Customer Name") + "</th>"
			'<th class="amt">' + _("Debit") + "</th>"
			'<th class="amt">' + _("Credit") + "</th></tr>"
			"</thead>"
		)

	html_pages = []
	run_debit = run_credit = 0.0

	for page_no, page_rows in enumerate(pages, 1):
		open_debit, open_credit = run_debit, run_credit

		body = ""
		if page_no > 1:
			body += (
				'<tr class="gs-carry"><td>' + _("Brought Forward") + "</td>"
				'<td class="amt">' + money(open_debit) + "</td>"
				'<td class="amt">' + money(open_credit) + "</td></tr>"
			)

		for idx, e in enumerate(page_rows):
			run_debit += e["debit"]
			run_credit += e["credit"]
			body += (
				'<tr class="' + ("odd" if idx % 2 == 0 else "even") + '"><td>'
				+ escape_html(e["name"])
				+ "</td>"
				'<td class="amt">' + money(e["debit"]) + "</td>"
				'<td class="amt">' + money(e["credit"]) + "</td></tr>"
			)

		is_last = page_no == total_pages
		if is_last:
			body += (
				'<tr class="gs-total"><td>' + _("Grand Total") + "</td>"
				'<td class="amt">' + money(run_debit) + "</td>"
				'<td class="amt">' + money(run_credit) + "</td></tr>"
			)
		else:
			body += (
				'<tr class="gs-carry"><td>' + _("Carried Over") + "</td>"
				'<td class="amt">' + money(run_debit) + "</td>"
				'<td class="amt">' + money(run_credit) + "</td></tr>"
			)

		footer = "" if is_last else '<div class="gs-cont">' + _("continued ...") + "</div>"

		html_pages.append(
			'<div class="gs-page">'
			+ branded_head(page_no)
			+ '<table class="gs">'
			+ column_head()
			+ "<tbody>"
			+ body
			+ "</tbody></table>"
			+ footer
			+ "</div>"
		)

	css = get_pdf_css() + _AR_PORTRAIT_CSS + _GROUP_SUMMARY_CSS
	return (
		'<!DOCTYPE html><html><head><meta charset="UTF-8">'
		"<title>" + title + "</title>"
		"<style>" + css + "</style></head><body>"
		+ "".join(html_pages)
		+ "</body></html>"
	)


def _as_text(value):
	if isinstance(value, (list, tuple)):
		return ", ".join(str(v) for v in value if v)
	return str(value or "")


def _build_filter_html(filters, company):
	filter_map = [
		(_("Company"), _as_text(company)),
		(
			_("Report Date"),
			formatdate(filters.get("report_date")) if filters.get("report_date") else "",
		),
		(_("Ageing Based On"), _as_text(filters.get("ageing_based_on"))),
		(_("Ageing Range"), _as_text(filters.get("range"))),
		(_("Customer"), _as_text(filters.get("party"))),
		(_("Customer Group"), _as_text(filters.get("customer_group"))),
		(_("Territory"), _as_text(filters.get("territory"))),
		(_("Sales Person"), _as_text(filters.get("sales_person"))),
		(_("Sales Partner"), _as_text(filters.get("sales_partner"))),
		(_("Payment Terms Template"), _as_text(filters.get("payment_terms_template"))),
		(_("Negative Balances Removed"), _("Yes") if cint(filters.get("remove_negative_balance")) else ""),
		(_("Summarized by Customer"), _("Yes") if cint(filters.get("summarize_by_customer")) else ""),
	]

	html = ""
	for label, value in filter_map:
		if value:
			html += (
				'<div class="filter-item">'
				'<span class="filter-label">' + escape_html(str(label)) + ":</span> "
				'<span class="filter-value">' + escape_html(str(value)) + "</span>"
				"</div>"
			)
	return html


def _build_table(columns, rows, currency):
	def is_numeric(col):
		return col.get("fieldtype") in NUMERIC_TYPES

	header_cells = ""
	for col in columns:
		css = ' class="text-right"' if is_numeric(col) else ""
		header_cells += "<th" + css + ">" + escape_html(str(_(col.get("label") or col["fieldname"]))) + "</th>"
	headers_html = "<tr>" + header_cells + "</tr>"

	def render_cell(col, row):
		value = row.get(col["fieldname"])
		if value is None or value == "":
			return ""
		fieldtype = col.get("fieldtype")
		if fieldtype == "Currency":
			return fmt_money(flt(value), currency=row.get("currency") or currency)
		if fieldtype == "Float":
			return f"{flt(value):,.2f}"
		if fieldtype == "Int":
			return str(cint(value))
		if fieldtype == "Date":
			return formatdate(value)
		return escape_html(str(value))

	rows_html = ""
	for i, row in enumerate(rows):
		css = "odd" if i % 2 == 0 else "even"
		cells = ""
		for col in columns:
			cell_css = ' class="text-right"' if is_numeric(col) else ""
			cells += "<td" + cell_css + ">" + render_cell(col, row) + "</td>"
		rows_html += '<tr class="' + css + '">' + cells + "</tr>"

	totals_cells = ""
	label_done = False
	for col in columns:
		# age is per-voucher; a summed age would be meaningless
		if is_numeric(col) and col["fieldname"] != "age":
			total = sum(flt(r.get(col["fieldname"])) for r in rows)
			if col.get("fieldtype") == "Currency":
				formatted = fmt_money(total, currency=currency)
			else:
				formatted = f"{total:,.2f}"
			totals_cells += '<td class="text-right">' + formatted + "</td>"
		elif not label_done:
			totals_cells += "<td><b>" + _("TOTAL") + "</b></td>"
			label_done = True
		else:
			totals_cells += "<td></td>"
	totals_html = '<tr class="totals-row">' + totals_cells + "</tr>"

	return headers_html, rows_html, totals_html
