app_name = "cyvetech_reports"
app_title = "Cyvetech Reports"
app_publisher = "Cyvetech"
app_description = "Custom Frappe/ERPNext reports by Cyvetech"
app_email = "support@cyvetech.com"
app_license = "MIT"

# Accounts Receivable report enhancements — server side
# (see cyvetech_reports/overrides/accounts_receivable.py)
before_request = ["cyvetech_reports.overrides.accounts_receivable.apply_patch"]
before_job = ["cyvetech_reports.overrides.accounts_receivable.apply_patch"]

# Accounts Receivable report enhancements — desk UI (Print button, filters)
app_include_js = "/assets/cyvetech_reports/js/ar_extensions.js"

fixtures = [
    {
        "doctype": "Report",
        "filters": [
            ["name", "in", [
                "Sales Analysis Report",
                "Cash Collection Report",
                "Stock Movement",
                "Item List Report",
                "General Ledger Print",
            ]]
        ]
    }
]
