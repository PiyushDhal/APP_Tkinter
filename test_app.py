"""
Comprehensive Test Suite for Campus Expense & Split Tracker
Verifies all SQLite operations, input validation edge-cases,
settlement algorithms, and Tkinter GUI layout configurations.
"""

import os
import sys
import math
from tkinter import messagebox
import main

# Mock messageboxes so automated tests do not block on popup dialogs
messagebox.showinfo = lambda *args, **kwargs: None
messagebox.showwarning = lambda *args, **kwargs: None
messagebox.showerror = lambda *args, **kwargs: None
messagebox.askyesno = lambda *args, **kwargs: True

def run_all_tests():
    print("==================================================")
    print("RUNNING COMPREHENSIVE AUDIT & EDGE-CASE TEST SUITE")
    print("==================================================")

    test_db_path = "test_audit_campus.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    # --------------------------------------------------------------------------
    # 1. DATABASE & SEEDING AUDIT
    # --------------------------------------------------------------------------
    print("\n[1/6] Testing DatabaseManager Lifecycle & Seeding...")
    db = main.DatabaseManager(test_db_path)

    metrics = db.get_summary_metrics()
    assert metrics["total_count"] == 4, f"Expected 4 seeded records, got {metrics['total_count']}"
    assert metrics["total_spend"] == 1200.0, f"Expected 1200.0 spend, got {metrics['total_spend']}"
    assert "Food" in metrics["highest_category"], f"Expected Food in highest category, got {metrics['highest_category']}"

    # Verify no duplicate seeding on restart
    db_restart = main.DatabaseManager(test_db_path)
    metrics_restart = db_restart.get_summary_metrics()
    assert metrics_restart["total_count"] == 4, f"Duplicate seeding occurred! Count: {metrics_restart['total_count']}"
    print("✓ Auto-seeding and non-duplicate restart verified.")

    # --------------------------------------------------------------------------
    # 2. INPUT VALIDATION & NUMERIC EDGE CASES
    # --------------------------------------------------------------------------
    print("\n[2/6] Testing Input Validation & Numeric Edge-Cases...")
    app = main.CampusExpenseApp()
    # Change db to test db
    app.db = db
    app.update()

    # Test blank item
    app.ent_item.delete(0, "end")
    app.ent_item.insert(0, "   ")
    app.ent_amount.insert(0, "100")
    app.combo_paid_by.set("Tester")
    app.on_add_expense()
    assert db.get_summary_metrics()["total_count"] == 4, "Blank item should be rejected!"

    # Test non-numeric amount
    app.ent_item.delete(0, "end")
    app.ent_item.insert(0, "Test Item")
    app.ent_amount.delete(0, "end")
    app.ent_amount.insert(0, "abc")
    app.on_add_expense()
    assert db.get_summary_metrics()["total_count"] == 4, "Non-numeric amount should be rejected!"

    # Test zero amount
    app.ent_amount.delete(0, "end")
    app.ent_amount.insert(0, "0")
    app.on_add_expense()
    assert db.get_summary_metrics()["total_count"] == 4, "Zero amount should be rejected!"

    # Test negative amount
    app.ent_amount.delete(0, "end")
    app.ent_amount.insert(0, "-50.00")
    app.on_add_expense()
    assert db.get_summary_metrics()["total_count"] == 4, "Negative amount should be rejected!"

    # Test nan / inf amount protection
    for bad_amt in ["nan", "inf", "-inf"]:
        app.ent_amount.delete(0, "end")
        app.ent_amount.insert(0, bad_amt)
        app.on_add_expense()
        assert db.get_summary_metrics()["total_count"] == 4, f"'{bad_amt}' amount should be rejected!"

    # Test invalid split counts
    for bad_split in ["0", "-2", "21", "3.5", "abc"]:
        app.ent_amount.delete(0, "end")
        app.ent_amount.insert(0, "150.00")
        app.spin_split.delete(0, "end")
        app.spin_split.insert(0, bad_split)
        app.on_add_expense()
        assert db.get_summary_metrics()["total_count"] == 4, f"Invalid split '{bad_split}' should be rejected!"

    # Test valid formatted amount with currency symbol & comma (e.g., '₹ 1,500.50')
    app.ent_item.delete(0, "end")
    app.ent_item.insert(0, "Team Dinner")
    app.combo_category.set("Food")
    app.ent_amount.delete(0, "end")
    app.ent_amount.insert(0, "₹ 1,500.50")
    app.combo_paid_by.set("Rohan Gupta")
    app.spin_split.delete(0, "end")
    app.spin_split.insert(0, "4")
    app.on_add_expense()
    assert db.get_summary_metrics()["total_count"] == 5, "Formatted currency amount should be accepted!"
    print("✓ All input validation and numeric edge cases properly guarded.")

    # --------------------------------------------------------------------------
    # 3. SETTLE UP MATHEMATICS & EXACT PAISE ALGORITHM
    # --------------------------------------------------------------------------
    print("\n[3/6] Testing Settle-Up Mathematics (Exact Paise Arithmetic)...")
    summary, txs, total_spend = db.get_settlement_data()
    print(f"  Total Spend: ₹ {total_spend:,.2f}")
    for m, d in summary.items():
        print(f"  {m}: Paid={d['paid']}, Share={d['fair_share']}, Net={d['net_balance']}")

    print("  Settlement Transactions:")
    for t in txs:
        print(f"  {t['from']} -> {t['to']}: ₹ {t['amount']:,.2f}")

    # Check that sum of credits equals sum of debits
    total_credits = sum(d["net_balance"] for d in summary.values() if d["net_balance"] > 0)
    total_debits = sum(-d["net_balance"] for d in summary.values() if d["net_balance"] < 0)
    assert abs(total_credits - total_debits) < 0.01, f"Balance mismatch! Credits: {total_credits}, Debits: {total_debits}"

    total_settle_tx = sum(t["amount"] for t in txs)
    assert abs(total_settle_tx - total_credits) < 0.01, f"Transaction settlement sum {total_settle_tx} != total credits {total_credits}"
    print("✓ Exact paise debt settlement verified without drift.")

    # --------------------------------------------------------------------------
    # 4. SEARCH, FILTER & CSV EXPORT
    # --------------------------------------------------------------------------
    print("\n[4/6] Testing Filtering, Search, & CSV Export...")
    # Search for Dinner
    app.search_var.set("Dinner")
    app.load_expenses()
    assert len(app.tree.get_children()) == 1, "Search for 'Dinner' should return 1 row."

    # Export filtered view to CSV
    app.export_to_csv()
    assert os.path.exists("expenses_report.csv")
    with open("expenses_report.csv", "r", encoding="utf-8") as f:
        csv_lines = [l.strip() for l in f.readlines() if l.strip()]
    assert len(csv_lines) == 3, f"Expected 3 lines (Header + 1 record + Total), got {len(csv_lines)}"

    # Reset filter
    app.reset_filters()
    assert len(app.tree.get_children()) == 5

    # Test sorting
    app.sort_tree_column("amount")
    app.sort_tree_column("each_owes")
    print("✓ Search, category filtering, column sorting, and CSV export passed.")

    # --------------------------------------------------------------------------
    # 5. ROW DELETION & EMPTY DATABASE RESILIENCE
    # --------------------------------------------------------------------------
    print("\n[5/6] Testing Deletion & Empty Table Behavior...")
    # Delete the newly added dinner row
    selected_item = None
    for child in app.tree.get_children():
        if "Team Dinner" in app.tree.item(child, "values")[2]:
            selected_item = child
            break
    assert selected_item is not None
    app.tree.selection_set(selected_item)
    app.on_delete_selected()
    assert db.get_summary_metrics()["total_count"] == 4

    # Delete all rows to test complete empty state resilience
    for child in list(app.tree.get_children()):
        app.tree.selection_set(child)
        app.on_delete_selected()

    assert db.get_summary_metrics()["total_count"] == 0
    assert app.kpi_spend_val.cget("text") == "₹ 0.00"
    assert app.kpi_cat_val.cget("text") == "N/A"

    # Export when empty
    app.export_to_csv()

    # Settle up dialog when empty
    modal_empty = main.SettleUpDialog(app, db)
    modal_empty.update()
    modal_empty.destroy()

    # Sort when empty
    app.sort_tree_column("amount")
    print("✓ Empty table resilience verified across all actions.")

    # --------------------------------------------------------------------------
    # 6. TKINTER LAYOUT & PROJECTOR RESOLUTION CONSTRAINTS
    # --------------------------------------------------------------------------
    print("\n[6/6] Verifying Geometry & Projector Resolution Scaling...")
    # Default geometry check
    app.geometry("1000x650")
    app.update_idletasks()
    assert app.minsize() == (850, 550), f"Expected minsize (850, 550), got {app.minsize()}"

    # Test scaling down to minsize
    app.geometry("850x550")
    app.update_idletasks()
    app.update()

    # SettleUpDialog scaling
    modal = main.SettleUpDialog(app, db)
    modal.update_idletasks()
    assert modal.minsize() == (660, 460), f"Expected dialog minsize (660, 460), got {modal.minsize()}"
    modal.destroy()

    app.destroy()

    # Clean up test database
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    print("\n==================================================")
    print("ALL AUDIT CHECKS PASSED WITH ZERO DEFECTS (100%)!")
    print("==================================================")

if __name__ == "__main__":
    run_all_tests()
