/* Cyvetech Reports — Accounts Receivable desk extensions.
 *
 * - Print toolbar button: prints the report with a user-selected set of
 *   fields, optionally summarized to one row per customer (numeric columns
 *   summed + grand total). Selection and summarize choice are remembered
 *   (per user, in this browser), so the next print is a single click.
 *   Change them any time via the "Print Fields" button.
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

	function get_saved_config() {
		try {
			const saved = JSON.parse(localStorage.getItem(storage_key()));
			// legacy format: a plain array of fieldnames
			if (Array.isArray(saved)) {
				return saved.length ? { fields: saved, summarize: 0 } : null;
			}
			if (saved && Array.isArray(saved.fields) && saved.fields.length) {
				return saved;
			}
		} catch (e) {
			// fall through
		}
		return null;
	}

	function save_config(fields, summarize) {
		localStorage.setItem(storage_key(), JSON.stringify({ fields, summarize: summarize ? 1 : 0 }));
	}

	function print_with_saved_fields(report) {
		if (!report.datatable || !(report.columns || []).length) {
			frappe.msgprint(__("Please wait for the report to load."));
			return;
		}
		const saved = get_saved_config();
		if (saved) {
			do_print(report, saved.fields, saved.summarize);
		} else {
			select_fields_and_print(report);
		}
	}

	function select_fields_and_print(report) {
		if (!report.datatable || !(report.columns || []).length) {
			frappe.msgprint(__("Please wait for the report to load."));
			return;
		}
		const saved = get_saved_config();
		const options = report.get_visible_columns().map((col) => ({
			label: __(col.label),
			value: col.fieldname,
			checked: saved ? saved.fields.includes(col.fieldname) : true,
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
				{
					fieldname: "summarize_by_customer",
					fieldtype: "Check",
					label: __("Summarize by Customer"),
					default: saved && saved.summarize ? 1 : 0,
					description: __("One row per customer with summed amounts and a grand total"),
				},
			],
			primary_action_label: __("Save and Print"),
			primary_action() {
				const values = dialog.get_values();
				const selected = values.fields || [];
				if (!selected.length) {
					frappe.msgprint(__("Please select at least one field."));
					return;
				}
				save_config(selected, values.summarize_by_customer);
				dialog.hide();
				do_print(report, selected, values.summarize_by_customer);
			},
		});
		dialog.show();
	}

	function do_print(report, fields, summarize) {
		const print_settings = {
			orientation: "Landscape",
			include_filters: 1,
			columns: fields,
		};

		if (!summarize) {
			report.print_report(print_settings);
			return;
		}

		// Core print_report always reads this.get_data_for_print(); swap it out
		// for the duration of this (async) print to feed it summarized rows.
		const original = report.get_data_for_print;
		report.get_data_for_print = function () {
			const rows = original.call(this);
			const columns = this.get_visible_columns().filter((c) => fields.includes(c.fieldname));
			return summarize_rows(rows, columns);
		};
		const restore = () => (report.get_data_for_print = original);
		try {
			const result = report.print_report(print_settings);
			if (result && result.finally) {
				result.finally(restore);
			} else {
				restore();
			}
		} catch (e) {
			restore();
			throw e;
		}
	}

	function summarize_rows(rows, columns) {
		// Sum numeric columns per customer; keep non-numeric values only when
		// they are identical across the customer's rows. "age" is per-voucher,
		// summing it would be meaningless.
		const numeric = ["Currency", "Float", "Int"];
		const sum_cols = columns.filter(
			(c) => numeric.includes(c.fieldtype) && c.fieldname !== "age"
		);
		const other_cols = columns.filter((c) => !sum_cols.includes(c));

		const groups = new Map(); // keeps A-Z insertion order from the report
		(rows || []).forEach((row) => {
			if (!row || typeof row !== "object" || !row.party || row.is_total_row) return;
			if (!groups.has(row.party)) groups.set(row.party, []);
			groups.get(row.party).push(row);
		});

		const out = [];
		const totals = {};
		groups.forEach((group_rows) => {
			const agg = { currency: group_rows[0].currency };
			other_cols.forEach((c) => {
				const values = new Set(group_rows.map((r) => r[c.fieldname] ?? ""));
				agg[c.fieldname] = values.size === 1 ? values.values().next().value : "";
			});
			sum_cols.forEach((c) => {
				const sum = group_rows.reduce((s, r) => s + (parseFloat(r[c.fieldname]) || 0), 0);
				agg[c.fieldname] = sum;
				totals[c.fieldname] = (totals[c.fieldname] || 0) + sum;
			});
			out.push(agg);
		});

		if (out.length && sum_cols.length) {
			const total_row = Object.assign({ is_total_row: true, currency: out[0].currency }, totals);
			if (other_cols.length) total_row[other_cols[0].fieldname] = __("Total");
			out.push(total_row);
		}
		return out;
	}
})();
