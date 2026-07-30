"""Enhancements for the standard Accounts Receivable / AR Summary reports.

Applied by wrapping the public ``frappe.desk.query_report.run`` (present in
all Frappe versions) via the ``before_request`` / ``before_job`` hooks, so the
desk view, prepared reports and XLSX/CSV exports are all covered — without
touching erpnext core.

Enhancements:
- Customer Name column: ERPNext only adds it when Selling Settings > Customer
  Naming By is "Naming Series", even though every row already carries
  ``customer_name`` via set_party_details. The missing column definition is
  inserted so the name shows regardless of the naming setting.
- Mode of Payment / Paid To columns: for Payment Entry rows, shows how the
  payment was made and the bank/cash account name (without the account code).
- Remove Customer Negative Balance: optional checkbox filter (added client
  side in ar_extensions.js) that hides rows with a negative outstanding.
- Summarize by Customer: optional checkbox filter (added client side) that
  collapses the report to one row per customer — numeric columns summed,
  per-voucher values blanked when they differ.
- Rows are sorted by customer name A-Z on load (unless grouped by customer).

To check the state on a server:
    bench --site <site> execute cyvetech_reports.overrides.accounts_receivable.verify
"""

import json

import frappe
from frappe import _
from frappe.utils import flt

TARGET_REPORTS = ("Accounts Receivable", "Accounts Receivable Summary")

_patched = False
_original_run = None


def apply_patch():
	global _patched, _original_run
	if _patched:
		return
	_patched = True

	try:
		import frappe.desk.query_report as query_report

		_original_run = query_report.run
		query_report.run = _patched_run
	except Exception:
		frappe.log_error(title="Cyvetech Reports: failed to patch query_report.run")


@frappe.whitelist()
def _patched_run(report_name=None, *args, **kwargs):
	result = _original_run(report_name, *args, **kwargs)

	if report_name in TARGET_REPORTS:
		try:
			filters = _parse_filters(kwargs.get("filters", args[0] if args else None))
			_add_payment_mode_columns(result)
			_insert_customer_name_column(result)
			_remove_negative_rows(result, filters)
			_sort_rows_by_customer(result, filters)
			_summarize_by_customer(result, filters)
		except Exception:
			frappe.log_error(title="Cyvetech Reports: AR report enhancements failed")

	return result


def _parse_filters(filters):
	if isinstance(filters, str):
		try:
			filters = json.loads(filters)
		except ValueError:
			filters = None
	return filters if isinstance(filters, dict) else {}


def _get_columns_and_rows(result):
	if not isinstance(result, dict):
		return [], []
	columns = result.get("columns") or []
	rows = [r for r in (result.get("result") or []) if isinstance(r, dict)]
	return columns, rows


def _fieldnames(columns):
	return [c.get("fieldname") for c in columns if isinstance(c, dict)]


def _insert_customer_name_column(result):
	columns, rows = _get_columns_and_rows(result)
	fieldnames = _fieldnames(columns)

	# nothing to do, or core already added it (Customer Naming By = Naming Series)
	if not fieldnames or "customer_name" in fieldnames or "party_name" in fieldnames:
		return

	# same position core uses: right after the Receivable Account column
	if "party_account" in fieldnames:
		idx = fieldnames.index("party_account") + 1
	elif "party" in fieldnames:
		idx = fieldnames.index("party") + 1
	else:
		return

	columns.insert(
		idx,
		{
			"label": _("Customer Name"),
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width": 180,
			"sticky": True,
		},
	)

	# AR detail rows already carry customer_name (set_party_details); the
	# Summary variant does not, so fill in whatever is missing
	missing = list(
		{
			r["party"]
			for r in rows
			if r.get("party") and not r.get("customer_name") and r.get("party_type") in (None, "Customer")
		}
	)
	if missing:
		names = dict(
			frappe.get_all(
				"Customer",
				filters={"name": ("in", missing)},
				fields=["name", "customer_name"],
				as_list=True,
			)
		)
		for r in rows:
			if not r.get("customer_name") and r.get("party") in names:
				r["customer_name"] = names[r["party"]]


def _add_payment_mode_columns(result):
	columns, rows = _get_columns_and_rows(result)
	fieldnames = _fieldnames(columns)

	if not fieldnames or "voucher_no" not in fieldnames or "mode_of_payment" in fieldnames:
		return

	idx = fieldnames.index("voucher_no") + 1
	columns[idx:idx] = [
		{
			"label": _("Mode of Payment"),
			"fieldname": "mode_of_payment",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Paid To"),
			"fieldname": "paid_to_account",
			"fieldtype": "Data",
			"width": 150,
		},
	]

	payment_entries = list(
		{r.get("voucher_no") for r in rows if r.get("voucher_type") == "Payment Entry" and r.get("voucher_no")}
	)
	if not payment_entries:
		return

	details = frappe.get_all(
		"Payment Entry",
		filters={"name": ("in", payment_entries)},
		fields=["name", "mode_of_payment", "paid_to"],
	)
	account_names = {
		a.name: a.account_name
		for a in frappe.get_all(
			"Account",
			filters={"name": ("in", list({d.paid_to for d in details if d.paid_to}))},
			fields=["name", "account_name"],
		)
	}
	details_map = {d.name: d for d in details}

	for row in rows:
		detail = row.get("voucher_type") == "Payment Entry" and details_map.get(row.get("voucher_no"))
		if detail:
			row["mode_of_payment"] = detail.mode_of_payment
			row["paid_to_account"] = account_names.get(detail.paid_to)


def _remove_negative_rows(result, filters):
	if not filters.get("remove_negative_balance") or not isinstance(result, dict):
		return

	rows = result.get("result") or []
	if not rows:
		return

	# the server-appended grand total (a plain list as the last row) must be
	# recomputed after filtering, or it would still include the removed rows
	has_total_row = bool(result.get("add_total_row")) and isinstance(rows[-1], (list, tuple))
	if has_total_row:
		rows = rows[:-1]

	rows = [
		r
		for r in rows
		if not (isinstance(r, dict) and r.get("outstanding") is not None and flt(r.get("outstanding")) < 0)
	]

	if has_total_row and rows:
		import frappe.desk.query_report as query_report

		rows = query_report.add_total_row(rows, result.get("columns") or [])

	result["result"] = rows


def _sort_rows_by_customer(result, filters):
	# grouped output has subtotal structure that must not be reordered
	if filters.get("group_by_party") or not isinstance(result, dict):
		return

	rows = result.get("result") or []
	# sort only the data rows; keep everything else (e.g. the grand total,
	# which frappe appends as a plain list) after them in original order
	sortable = [r for r in rows if isinstance(r, dict) and r.get("party")]
	others = [r for r in rows if not (isinstance(r, dict) and r.get("party"))]
	if len(sortable) < 2:
		return

	sortable.sort(key=lambda r: (r.get("customer_name") or r.get("party") or "").lower())
	result["result"] = sortable + others


def _summarize_by_customer(result, filters):
	# one row per customer: numeric columns summed, non-numeric kept only when
	# identical across the customer's rows. Grouped output is left alone.
	if not filters.get("summarize_by_customer") or filters.get("group_by_party"):
		return
	if not isinstance(result, dict):
		return

	columns = result.get("columns") or []
	rows = result.get("result") or []
	if not columns or not rows:
		return

	has_total_row = bool(result.get("add_total_row")) and isinstance(rows[-1], (list, tuple))
	if has_total_row:
		rows = rows[:-1]

	numeric = {"Currency", "Float", "Int"}
	col_defs = [c for c in columns if isinstance(c, dict) and c.get("fieldname")]
	# age is per-voucher; summing it would be meaningless
	sum_fields = [
		c["fieldname"] for c in col_defs if c.get("fieldtype") in numeric and c["fieldname"] != "age"
	]
	other_fields = [c["fieldname"] for c in col_defs if c["fieldname"] not in sum_fields]

	groups = {}
	order = []
	for r in rows:
		if isinstance(r, dict) and r.get("party"):
			if r["party"] not in groups:
				groups[r["party"]] = []
				order.append(r["party"])
			groups[r["party"]].append(r)

	if not groups:
		return

	out = []
	for party in order:
		group = groups[party]
		agg = {"currency": group[0].get("currency")}
		for f in other_fields:
			values = {g.get(f) if g.get(f) is not None else "" for g in group}
			agg[f] = values.pop() if len(values) == 1 else None
		for f in sum_fields:
			agg[f] = sum(flt(g.get(f)) for g in group)
		out.append(agg)

	if has_total_row:
		import frappe.desk.query_report as query_report

		out = query_report.add_total_row(out, columns)

	result["result"] = out


def verify():
	"""End-to-end server-side check. Run:
	bench --site <site> execute cyvetech_reports.overrides.accounts_receivable.verify
	"""
	import frappe.desk.query_report as query_report

	hook_path = "cyvetech_reports.overrides.accounts_receivable.apply_patch"
	hooks_registered = hook_path in (frappe.get_hooks("before_request") or [])

	apply_patch()

	result = query_report.run(
		"Accounts Receivable",
		filters={"report_date": frappe.utils.nowdate(), "range": "30, 60, 90, 120"},
		ignore_prepared_report=True,
	)
	columns = [c.get("fieldname") for c in (result.get("columns") or [])]

	rows = [r for r in (result.get("result") or []) if isinstance(r, dict) and r.get("party")]
	names = [(r.get("customer_name") or r.get("party") or "").lower() for r in rows]

	def js_is_current(path):
		# version tag comment bumped on every ar_extensions.js change
		try:
			with open(path, encoding="utf-8") as f:
				return "cyvetech-ar-ext v5" in f.read()
		except OSError:
			return None  # file missing / unreadable

	import os

	app_js = frappe.get_app_path("cyvetech_reports", "public", "js", "ar_extensions.js")
	served_js = os.path.join(
		frappe.utils.get_bench_path(), "sites", "assets", "cyvetech_reports", "js", "ar_extensions.js"
	)

	out = {
		"before_request_hook_registered": hooks_registered,
		"app_include_js_registered": any(
			"/assets/cyvetech_reports/js/ar_extensions.js" in hook
			for hook in (frappe.get_hooks("app_include_js") or [])
		),
		"app_source_js_current": js_is_current(app_js),
		"served_assets_js_current": js_is_current(served_js),
		"query_report_run_patched": getattr(query_report.run, "__module__", "") == __name__,
		"customer_name_in_columns": "customer_name" in columns,
		"mode_of_payment_in_columns": "mode_of_payment" in columns,
		"rows_sorted_a_to_z": names == sorted(names),
		"columns": columns[:12],
	}

	summary = query_report.run(
		"Accounts Receivable Summary",
		filters={"report_date": frappe.utils.nowdate(), "range": "30, 60, 90, 120"},
		ignore_prepared_report=True,
	)
	summary_columns = [c.get("fieldname") for c in (summary.get("columns") or []) if isinstance(c, dict)]
	summary_rows = [r for r in (summary.get("result") or []) if isinstance(r, dict) and r.get("party")]
	out["summary_customer_name_in_columns"] = (
		"customer_name" in summary_columns or "party_name" in summary_columns
	)
	out["summary_names_populated"] = any(
		r.get("customer_name") or r.get("party_name") for r in summary_rows
	) or not summary_rows
	print(out)
	return out
