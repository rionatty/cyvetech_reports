"""Show the Customer Name column on the standard Accounts Receivable report.

ERPNext only adds this column when Selling Settings > Customer Naming By is
"Naming Series" (ReceivablePayableReport.get_columns), even though every data
row already carries ``customer_name`` via set_party_details. This patch
inserts the missing column definition into the report output, so the name is
visible regardless of the naming setting and without touching erpnext core.

The patch is applied lazily via the ``before_request`` / ``before_job`` hooks
(standard Frappe monkey-patch pattern) and wraps
``frappe.desk.query_report._run`` so the desk view, prepared reports and
XLSX/CSV exports are all covered.
"""

import frappe
from frappe import _

_patched = False
_original_run = None


def apply_patch():
	global _patched, _original_run
	if _patched:
		return
	_patched = True

	import frappe.desk.query_report as query_report

	# _run exists on Frappe v16+; on older versions do nothing
	if not hasattr(query_report, "_run"):
		return

	_original_run = query_report._run
	query_report._run = _run_with_customer_name


def _run_with_customer_name(*args, **kwargs):
	result = _original_run(*args, **kwargs)

	if kwargs.get("report_name") == "Accounts Receivable":
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
