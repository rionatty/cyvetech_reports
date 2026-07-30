/* Cyvetech Reports — Accounts Receivable desk extensions.
 *
 * - Print toolbar button: prints the report with a user-selected set of
 *   fields. The selection is remembered (per user, in this browser), so the
 *   next print is a single click. Change it any time via the report menu >
 *   "Select Print Fields".
 * - "Remove Customer Negative Balance" checkbox filter (rows are filtered
 *   server side, see overrides/accounts_receivable.py).
 *
 * The report settings object is registered lazily by core when the report
 * page loads, so we intercept the registration with a property setter
 * instead of assuming load order.
 */
(function () {
	const REPORT_NAME = "Accounts Receivable";
	const storage_key = () => `cyvetech:ar_print_fields:${frappe.session.user}`;

	frappe.provide("frappe.query_reports");

	let current_settings = frappe.query_reports[REPORT_NAME];
	Object.defineProperty(frappe.query_reports, REPORT_NAME, {
		configurable: true,
		enumerable: true,
		get() {
			return current_settings;
		},
		set(settings) {
			current_settings = extend_settings(settings);
		},
	});
	if (current_settings) {
		current_settings = extend_settings(current_settings);
	}

	function extend_settings(settings) {
		if (!settings || settings.__cyvetech_extended) return settings;
		settings.__cyvetech_extended = true;

		(settings.filters = settings.filters || []).push({
			fieldname: "remove_negative_balance",
			label: __("Remove Customer Negative Balance"),
			fieldtype: "Check",
		});

		const original_onload = settings.onload;
		settings.onload = function (report) {
			if (original_onload) original_onload.call(this, report);
			const $print = report.page.add_inner_button(__("Print"), () =>
				print_with_saved_fields(report)
			);
			if ($print && $print.css) {
				$print.css({
					"background-color": "#16a34a",
					"border-color": "#16a34a",
					color: "#fff",
					"font-weight": "600",
				});
			}
			report.page.add_inner_button(__("Print Fields"), () => select_fields_and_print(report));
		};
		return settings;
	}

	function get_saved_fields() {
		try {
			const saved = JSON.parse(localStorage.getItem(storage_key()));
			return Array.isArray(saved) && saved.length ? saved : null;
		} catch (e) {
			return null;
		}
	}

	function print_with_saved_fields(report) {
		if (!report.datatable || !(report.columns || []).length) {
			frappe.msgprint(__("Please wait for the report to load."));
			return;
		}
		const saved = get_saved_fields();
		if (saved) {
			do_print(report, saved);
		} else {
			select_fields_and_print(report);
		}
	}

	function select_fields_and_print(report) {
		if (!report.datatable || !(report.columns || []).length) {
			frappe.msgprint(__("Please wait for the report to load."));
			return;
		}
		const saved = get_saved_fields();
		const options = report.get_visible_columns().map((col) => ({
			label: __(col.label),
			value: col.fieldname,
			checked: saved ? saved.includes(col.fieldname) : true,
		}));

		const dialog = new frappe.ui.Dialog({
			title: __("Select Fields to Print"),
			fields: [
				{
					fieldname: "fields",
					fieldtype: "MultiCheck",
					label: __("Fields"),
					columns: 2,
					select_all: true,
					options: options,
				},
			],
			primary_action_label: __("Save and Print"),
			primary_action() {
				const selected = dialog.get_values().fields || [];
				if (!selected.length) {
					frappe.msgprint(__("Please select at least one field."));
					return;
				}
				localStorage.setItem(storage_key(), JSON.stringify(selected));
				dialog.hide();
				do_print(report, selected);
			},
		});
		dialog.show();
	}

	function do_print(report, fields) {
		report.print_report({
			orientation: "Landscape",
			include_filters: 1,
			columns: fields,
		});
	}
})();
