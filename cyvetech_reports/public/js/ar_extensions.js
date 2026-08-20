/* Cyvetech Reports — Accounts Receivable desk extensions.
 *
 * Applies to both "Accounts Receivable" and "Accounts Receivable Summary":
 * - Green Print toolbar button producing the branded Cyvetech printout
 *   (rendered server side, see overrides/ar_print.py) with a user-selected
 *   set of fields, remembered per user and per report. The "Print Fields"
 *   button changes the selection any time.
 * - "Remove Customer Negative Balance" checkbox filter (server side).
 * - "Summarize by Customer" checkbox filter (detail report only — the
 *   Summary report is already one row per customer).
 *
 * Report settings are registered lazily by core when the report page loads,
 * so registration is intercepted with a property setter instead of assuming
 * load order.
 *
 * cyvetech-ar-ext v7
 */
(function () {
	const REPORTS = {
		"Accounts Receivable": { summarize_option: true, group_summary_option: false },
		"Accounts Receivable Summary": { summarize_option: false, group_summary_option: true },
	};
	const legacy_key = () => `cyvetech:ar_print_fields:${frappe.session.user}`;
	const storage_key = (report_name) =>
		`cyvetech:print_fields:${report_name}:${frappe.session.user}`;

	frappe.provide("frappe.query_reports");
	Object.keys(REPORTS).forEach(setup);

	function setup(report_name) {
		let current_settings = frappe.query_reports[report_name];
		Object.defineProperty(frappe.query_reports, report_name, {
			configurable: true,
			enumerable: true,
			get() {
				return current_settings;
			},
			set(settings) {
				current_settings = extend_settings(settings, report_name);
			},
		});
		if (current_settings) {
			current_settings = extend_settings(current_settings, report_name);
		}
	}

	function extend_settings(settings, report_name) {
		if (!settings || settings.__cyvetech_extended) return settings;
		settings.__cyvetech_extended = true;

		const filters = (settings.filters = settings.filters || []);
		filters.push({
			fieldname: "remove_negative_balance",
			label: __("Remove Customer Negative Balance"),
			fieldtype: "Check",
		});
		if (REPORTS[report_name].summarize_option) {
			filters.push({
				fieldname: "summarize_by_customer",
				label: __("Summarize by Customer"),
				fieldtype: "Check",
			});
		}

		const original_onload = settings.onload;
		settings.onload = function (report) {
			if (original_onload) original_onload.call(this, report);
			const $print = report.page.add_inner_button(__("Print"), () =>
				print_with_saved_fields(report, report_name)
			);
			if ($print && $print.css) {
				$print.css({
					"background-color": "#16a34a",
					"border-color": "#16a34a",
					color: "#fff",
					"font-weight": "600",
				});
			}
			report.page.add_inner_button(__("Print Fields"), () =>
				select_fields_and_print(report, report_name)
			);
		};
		return settings;
	}

	function get_saved_config(report_name) {
		const read = (key) => {
			try {
				return JSON.parse(localStorage.getItem(key));
			} catch (e) {
				return null;
			}
		};
		let saved = read(storage_key(report_name));
		if (!saved && report_name === "Accounts Receivable") saved = read(legacy_key());
		if (Array.isArray(saved)) saved = saved.length ? { fields: saved, summarize: 0 } : null;
		if (!saved || !Array.isArray(saved.fields) || !saved.fields.length) return null;

		// configs saved before an option existed have no key for it - fall back
		// to the report default instead of reading undefined as "off"
		if (saved.group_summary === undefined) {
			saved.group_summary = REPORTS[report_name].group_summary_option ? 1 : 0;
		}
		return saved;
	}

	function save_config(report_name, fields, summarize, group_summary) {
		localStorage.setItem(
			storage_key(report_name),
			JSON.stringify({
				fields,
				summarize: summarize ? 1 : 0,
				group_summary: group_summary ? 1 : 0,
			})
		);
	}

	function report_ready(report) {
		if (!report.datatable || !(report.columns || []).length) {
			frappe.msgprint(__("Please wait for the report to load."));
			return false;
		}
		return true;
	}

	function print_with_saved_fields(report, report_name) {
		if (!report_ready(report)) return;
		const saved = get_saved_config(report_name);
		if (saved) {
			do_print(report, report_name, saved.fields, saved.summarize, saved.group_summary);
		} else {
			select_fields_and_print(report, report_name);
		}
	}

	function select_fields_and_print(report, report_name) {
		if (!report_ready(report)) return;
		const saved = get_saved_config(report_name);
		const options = report.get_visible_columns().map((col) => ({
			label: __(col.label),
			value: col.fieldname,
			checked: saved ? saved.fields.includes(col.fieldname) : true,
		}));

		const dialog_fields = [
			{
				fieldname: "fields",
				fieldtype: "MultiCheck",
				label: __("Fields"),
				columns: 2,
				select_all: true,
				options: options,
			},
		];
		if (REPORTS[report_name].summarize_option) {
			dialog_fields.push({
				fieldname: "summarize_by_customer",
				fieldtype: "Check",
				label: __("Summarize by Customer"),
				default: saved && saved.summarize ? 1 : 0,
				description: __("One row per customer with summed amounts"),
			});
		}
		if (REPORTS[report_name].group_summary_option) {
			dialog_fields.push({
				fieldname: "group_summary",
				fieldtype: "Check",
				// defaults on - this is the format the client asked for
				default: saved && !saved.group_summary ? 0 : 1,
				label: __("Group Summary (Debit / Credit)"),
				description: __(
					"Closing balance split into Debit and Credit, with Carried Over / Brought Forward per page"
				),
			});
		}

		const dialog = new frappe.ui.Dialog({
			title: __("Select Fields to Print"),
			fields: dialog_fields,
			primary_action_label: __("Save and Print"),
			primary_action() {
				const values = dialog.get_values();
				const selected = values.fields || [];
				if (!selected.length) {
					frappe.msgprint(__("Please select at least one field."));
					return;
				}
				save_config(
					report_name,
					selected,
					values.summarize_by_customer,
					values.group_summary
				);
				dialog.hide();
				do_print(
					report,
					report_name,
					selected,
					values.summarize_by_customer,
					values.group_summary
				);
			},
		});
		dialog.show();
	}

	function do_print(report, report_name, fields, summarize, group_summary) {
		const filters =
			(report.get_filter_values && report.get_filter_values()) ||
			(report.get_values && report.get_values()) ||
			{};

		frappe.call({
			method: "cyvetech_reports.overrides.ar_print.get_pdf_html",
			args: {
				report_name: report_name,
				filters: JSON.stringify(filters),
				visible_columns: JSON.stringify(fields),
				summarize: summarize ? 1 : 0,
				group_summary: group_summary ? 1 : 0,
			},
			freeze: true,
			freeze_message: __("Generating PDF..."),
			callback(r) {
				if (r.message) {
					const w = window.open();
					w.document.write(r.message);
					w.document.close();
					setTimeout(() => w.print(), 600);
				}
			},
		});
	}
})();
