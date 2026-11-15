import os
import main
from tkinter import messagebox

# Mock messageboxes so automated test doesn't block on popups
messagebox.showinfo = lambda *args, **kwargs: None
messagebox.showwarning = lambda *args, **kwargs: None
messagebox.showerror = lambda *args, **kwargs: None
messagebox.askyesno = lambda *args, **kwargs: True

# Clean previous test database if exists
if os.path.exists("test_campus.db"):
    os.remove("test_campus.db")

print("--- Testing DatabaseManager ---")
db = main.DatabaseManager("test_campus.db")
metrics = db.get_summary_metrics()
print("Initial metrics:", metrics)
assert metrics["total_count"] == 4, f"Expected 4 records, got {metrics['total_count']}"
assert metrics["total_spend"] == 1200.0, f"Expected 1200.0, got {metrics['total_spend']}"
assert "Food" in metrics["highest_category"], f"Expected Food, got {metrics['highest_category']}"

# Test fetching expenses
records = db.get_expenses()
assert len(records) == 4
print("Seeded records count verified: 4")

# Test distinct payers
payers = db.get_distinct_payers()
print("Distinct payers:", payers)
assert "Aarav Sharma" in payers
assert "Priya Patel" in payers
assert "Rohan Gupta" in payers
assert "Sneha Rao" in payers

# Test settlement data
summary, txs, total = db.get_settlement_data()
print("Total group spend:", total)
print("Settlement summary:")
for k, v in summary.items():
    print(f"  {k}: Paid={v['paid']}, Share={v['fair_share']}, Net={v['net_balance']}")

print("Settlement transactions:")
for t in txs:
    print(f"  {t['from']} -> {t['to']}: ₹{t['amount']:.2f}")

# Aarav paid 480, share 300 -> +180
# Priya paid 320, share 300 -> +20
# Rohan paid 160, share 300 -> -140
# Sneha paid 240, share 300 -> -60
assert abs(summary["Aarav Sharma"]["net_balance"] - 180.0) < 0.01
assert abs(summary["Priya Patel"]["net_balance"] - 20.0) < 0.01
assert abs(summary["Rohan Gupta"]["net_balance"] - (-140.0)) < 0.01
assert abs(summary["Sneha Rao"]["net_balance"] - (-60.0)) < 0.01

# Test adding an expense
new_id = db.add_expense("Movie Night Tickets", "Entertainment", 600.0, "Rohan Gupta", 3)
assert new_id == 5
assert db.get_summary_metrics()["total_count"] == 5

# Test search and filter
food_records = db.get_expenses(category_filter="Food")
assert len(food_records) == 2

search_records = db.get_expenses(search_query="Uber")
assert len(search_records) == 1
assert search_records[0]["item"] == "Campus Uber Cab Fare"

search_by_payer = db.get_expenses(search_query="Patel")
assert len(search_by_payer) == 1
assert search_by_payer[0]["paid_by"] == "Priya Patel"

# Test deleting expense
deleted = db.delete_expense(new_id)
assert deleted is True
assert db.get_summary_metrics()["total_count"] == 4

# Clean up test database
if os.path.exists("test_campus.db"):
    os.remove("test_campus.db")

print("--- Testing GUI Instantiation & Layout (headless) ---")
app = main.CampusExpenseApp()
app.update()
print("App window title:", app.title())
print("KPI Spend Label text:", app.kpi_spend_val.cget("text"))
print("KPI TX Label text:", app.kpi_tx_val.cget("text"))
print("KPI Category Label text:", app.kpi_cat_val.cget("text"))
print("Treeview children count:", len(app.tree.get_children()))

assert app.kpi_spend_val.cget("text") == "₹ 1,200.00"
assert app.kpi_tx_val.cget("text") == "4 Records"
assert "Food" in app.kpi_cat_val.cget("text")
assert len(app.tree.get_children()) == 4

# Test sorting
app.sort_tree_column("amount")
app.update()

# Test export to CSV
app.export_to_csv()
assert os.path.exists("expenses_report.csv")
with open("expenses_report.csv", "r", encoding="utf-8") as f:
    csv_lines = f.readlines()
print(f"Exported CSV has {len(csv_lines)} lines")
assert len(csv_lines) >= 6

# Test Settle Up modal creation
modal = main.SettleUpDialog(app, app.db)
modal.update()
report_text = modal.generate_report_text()
print("Generated settlement report sample:")
print(report_text[:250] + "...")
modal.destroy()

app.destroy()

print("\n==========================================")
print("ALL TESTS PASSED WITH 100% SUCCESS!")
print("==========================================")
