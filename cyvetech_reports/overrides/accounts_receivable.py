"""Show the Customer Name column on the standard Accounts Receivable report.

ERPNext only adds this column when Selling Settings > Customer Naming By is
"Naming Series" (ReceivablePayableReport.get_columns), even though every data
row already carries ``customer_name`` via set_party_details. This patch
inserts the missing column definition into the report output, so the name is
visible regardless of the naming setting and without touching erpnext core.

The patch wraps the public ``frappe.desk.query_report.run`` (present in all
Frappe versions) and is applied lazily via the ``before_request`` /
``before_job`` hooks, so the desk view, prepared reports and XLSX/CSV exports
are all covered.

To check the state on a server:
    bench --site <site> execute cyvetech_reports.overrides.accounts_receivable.verify
"""

import frappe
from frappe import _

TARGET_REPORTS = ("Accounts Receivable",)

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
			_insert_customer_name_column(result)
		except Exception:
			frappe.log_error(title="Cyvetech Reports: AR Customer Name column failed")

	return result


def _insert_customer_name_column(result):
	if not isinstance(result, dict):
		return

	columns = result.get("columns") or []
	fieldnames = [c.get("fieldname") for c in columns if isinstance(c, dict)]

	# nothing to do, or core already added it (Customer Naming By = Naming Series)
	if not fieldnames or "customer_name" in fieldnames:
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

	out = {
		"before_request_hook_registered": hooks_registered,
		"query_report_run_patched": getattr(query_report.run, "__module__", "") == __name__,
		"customer_name_in_columns": "customer_name" in columns,
		"columns": columns[:8],
	}
	print(out)
	return out
