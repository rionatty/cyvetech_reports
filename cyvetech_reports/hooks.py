app_name = "cyvetech_reports"
app_title = "Cyvetech Reports"
app_publisher = "Cyvetech"
app_description = "Custom Frappe/ERPNext reports by Cyvetech"
app_email = "support@cyvetech.com"
app_license = "MIT"

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
