app_name = "cyvetech_reports"
app_title = "Cyvetech Reports"
app_publisher = "Cyvetech"
app_description = "Custom Frappe/ERPNext reports by Cyvetech"
app_email = "support@cyvetech.com"
app_license = "MIT"

# Adds the Customer Name column to the standard Accounts Receivable report
# (see cyvetech_reports/overrides/accounts_receivable.py)
before_request = ["cyvetech_reports.overrides.accounts_receivable.apply_patch"]
before_job = ["cyvetech_reports.overrides.accounts_receivable.apply_patch"]

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
