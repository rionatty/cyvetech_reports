# Cyvetech Reports

Custom Frappe/ERPNext reports by Cyvetech.

**Repository:** https://github.com/rionatty/cyvetech_reports.git

## Reports Included

- **Sales Analysis Report** — Detailed sales breakdown by invoice line with grouping by Route, Customer, Item, Item Group, and Date
- **Cash Collection Report** — Payment collection tracking by route/sales person
- **Van Stock Movement** — Stock movement tracking per van/route
- **Item List Report** — Item catalogue report
- **General Ledger Print** — Custom general ledger print format

## Customizations

- **Accounts Receivable enhancements** — extends the standard ERPNext Accounts Receivable report:
  - Customer Name column, regardless of the *Customer Naming By* setting
  - Mode of Payment and Paid To (bank/cash account name, without account code) columns for Payment Entry rows
  - Rows sorted by customer name A–Z on load
  - *Remove Customer Negative Balance* checkbox filter to hide negative-outstanding rows
  - Print toolbar button with field selection; the selected fields are remembered per user, so subsequent prints are one click (change them via menu > *Select Print Fields*)

## Installation

### Fresh Install

```bash
cd ~/frappe-bench

bench get-app cyvetech_reports https://github.com/rionatty/cyvetech_reports.git

bench --site your-site install-app cyvetech_reports

bench --site your-site migrate
bench --site your-site clear-cache
bench restart
```

### Update Existing Installation

```bash
cd ~/frappe-bench/apps/cyvetech_reports
git pull origin main

cd ~/frappe-bench
bench --site your-site migrate
bench --site your-site clear-cache
bench restart
```
