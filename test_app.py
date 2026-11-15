"""
Comprehensive Test Suite for Campus Expense & Split Tracker
Verifies zero-data start, dynamic updates upon user input,
input validation edge-cases, settlement algorithms, and Tkinter GUI layout.
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
    print("RUNNING ZERO-DATA START & DYNAMIC UPDATE TEST SUITE")
    print("==================================================")

    test_db_path = "test_zero_campus.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    # --------------------------------------------------------------------------
    # 1. VERIFY ZERO-DATA INITIALIZATION
    # --------------------------------------------------------------------------
    print("\n[1/6] Verifying Clean Zero-Data Start...")
    db = main.DatabaseManager(test_db_path)

    metrics = db.get_summary_metrics()
    assert metrics["total_count"] == 0, f"Expected 0 records, got {metrics['total_count']}"
    assert metrics["total_spend"] == 0.0, f"Expected 0.0 spend, got {metrics['total_spend']}"
    assert metrics["highest_category"] == "N/A", f"Expected N/A, got {metrics['highest_category']}"

    # Verify restarts maintain 0 records
    db_restart = main.DatabaseManager(test_db_path)
    metrics_restart = db_restart.get_summary_metrics()
    assert metrics_restart["total_count"] == 0, f"Expected 0 records on restart, got {metrics_restart['total_count']}"
    print("✓ Application starts completely clean from zero records.")

    # --------------------------------------------------------------------------
    # 2. INPUT VALIDATION & NUMERIC EDGE CASES
    # --------------------------------------------------------------------------
    print("\n[2/6] Testing Input Validation Guards at Zero State...")
    app = main.CampusExpenseApp()
    app.db = db
    app.update()

    assert app.kpi_spend_val.cget("text") == "₹ 0.00"
    assert app.kpi_tx_val.cget("text") == "0 Records"
    assert app.kpi_cat_val.cget("text") == "N/A"
    assert len(app.tree.get_children()) == 0

    # Test blank item
    app.ent_item.delete(0, "end")
    app.ent_item.insert(0, "   ")
    app.ent_amount.insert(0, "100")
    app.combo_paid_by.set("Piyush")
    app.on_add_expense()
    assert db.get_summary_metrics()["total_count"] == 0, "Blank item should be rejected!"

    # Test non-numeric amount
    app.ent_item.delete(0, "end")
    app.ent_item.insert(0, "Lunch")
    app.ent_amount.delete(0, "end")
    app.ent_amount.insert(0, "abc")
    app.on_add_expense()
    assert db.get_summary_metrics()["total_count"] == 0, "Non-numeric amount should be rejected!"

    # Test zero amount
    app.ent_amount.delete(0, "end")
    app.ent_amount.insert(0, "0")
    app.on_add_expense()
    assert db.get_summary_metrics()["total_count"] == 0, "Zero amount should be rejected!"

    # Test negative amount
    app.ent_amount.delete(0, "end")
    app.ent_amount.insert(0, "-50.00")
    app.on_add_expense()
    assert db.get_summary_metrics()["total_count"] == 0, "Negative amount should be rejected!"

    # Test nan / inf amount protection
    for bad_amt in ["nan", "inf", "-inf"]:
        app.ent_amount.delete(0, "end")
        app.ent_amount.insert(0, bad_amt)
        app.on_add_expense()
        assert db.get_summary_metrics()["total_count"] == 0, f"'{bad_amt}' amount should be rejected!"

    # Test invalid split counts
    for bad_split in ["0", "-2", "21", "3.5", "abc"]:
        app.ent_amount.delete(0, "end")
        app.ent_amount.insert(0, "150.00")
        app.spin_split.delete(0, "end")
        app.spin_split.insert(0, bad_split)
        app.on_add_expense()
        assert db.get_summary_metrics()["total_count"] == 0, f"Invalid split '{bad_split}' should be rejected!"

    print("✓ All input validation guards verified at zero state.")

    # --------------------------------------------------------------------------
    # 3. DYNAMIC UPDATING AS USER GIVES INPUT
    # --------------------------------------------------------------------------
    print("\n[3/6] Testing Dynamic Updating as User Enters Records...")

    # Input 1: Piyush adds Food ₹ 450
    app.ent_item.delete(0, "end")
    app.ent_item.insert(0, "Cafeteria Lunch Combo")
    app.combo_category.set("Food")
    app.ent_amount.delete(0, "end")
    app.ent_amount.insert(0, "₹ 450.00")
    app.combo_paid_by.set("Piyush")
    app.spin_split.delete(0, "end")
    app.spin_split.insert(0, "3")
    app.on_add_expense()

    assert db.get_summary_metrics()["total_count"] == 1
    assert app.kpi_spend_val.cget("text") == "₹ 450.00"
    assert app.kpi_tx_val.cget("text") == "1 Records"
    assert "Food" in app.kpi_cat_val.cget("text")
    assert len(app.tree.get_children()) == 1

    # Input 2: Manan adds Travel ₹ 300
    app.ent_item.delete(0, "end")
    app.ent_item.insert(0, "Campus Uber Cab Fare")
    app.combo_category.set("Travel")
    app.ent_amount.delete(0, "end")
    app.ent_amount.insert(0, "300.00")
    app.combo_paid_by.set("Manan")
    app.spin_split.delete(0, "end")
    app.spin_split.insert(0, "3")
    app.on_add_expense()

    assert db.get_summary_metrics()["total_count"] == 2
    assert app.kpi_spend_val.cget("text") == "₹ 750.00"
    assert app.kpi_tx_val.cget("text") == "2 Records"

    # Input 3: Yukti adds Stationery ₹ 150
    app.ent_item.delete(0, "end")
    app.ent_item.insert(0, "Lab Manual & Xerox")
    app.combo_category.set("Stationery")
    app.ent_amount.delete(0, "end")
    app.ent_amount.insert(0, "150.00")
    app.combo_paid_by.set("Yukti")
    app.spin_split.delete(0, "end")
    app.spin_split.insert(0, "3")
    app.on_add_expense()

    assert db.get_summary_metrics()["total_count"] == 3
    assert app.kpi_spend_val.cget("text") == "₹ 900.00"
    assert app.kpi_tx_val.cget("text") == "3 Records"
    assert len(app.tree.get_children()) == 3

    print("✓ Dynamic storage and live UI updating confirmed.")

    # --------------------------------------------------------------------------
    # 4. SETTLEMENT COMPUTATION FOR DYNAMIC DATA
    # --------------------------------------------------------------------------
    print("\n[4/6] Verifying Settle-Up Calculations for Dynamic Entries...")
    summary, txs, total_spend = db.get_settlement_data()
    assert total_spend == 900.00
    assert summary["Piyush"]["paid"] == 450.00
    assert summary["Piyush"]["fair_share"] == 300.00
    assert summary["Piyush"]["net_balance"] == 150.00  # Gets back ₹150

    assert summary["Manan"]["paid"] == 300.00
    assert summary["Manan"]["fair_share"] == 300.00
    assert summary["Manan"]["net_balance"] == 0.00  # Settled up

    assert summary["Yukti"]["paid"] == 150.00
    assert summary["Yukti"]["fair_share"] == 300.00
    assert summary["Yukti"]["net_balance"] == -150.00  # Owes ₹150

    assert len(txs) == 1
    assert txs[0]["from"] == "Yukti"
    assert txs[0]["to"] == "Piyush"
    assert txs[0]["amount"] == 150.00
    print("✓ Settle-up modal mathematically resolves debts accurately.")

    # --------------------------------------------------------------------------
    # 5. FILTERING, SEARCH, CSV EXPORT & DELETION
    # --------------------------------------------------------------------------
    print("\n[5/6] Testing Real-Time Search, Filter, CSV Export & Deletion...")
    app.search_var.set("Uber")
    app.load_expenses()
    assert len(app.tree.get_children()) == 1

    app.export_to_csv()
    assert os.path.exists("expenses_report.csv")

    app.reset_filters()
    assert len(app.tree.get_children()) == 3

    # Delete all records
    for child in list(app.tree.get_children()):
        app.tree.selection_set(child)
        app.on_delete_selected()

    assert db.get_summary_metrics()["total_count"] == 0
    assert app.kpi_spend_val.cget("text") == "₹ 0.00"
    print("✓ Filter, search, CSV export, and deletion verified.")

    # --------------------------------------------------------------------------
    # 6. GEOMETRY CONSTRAINTS
    # --------------------------------------------------------------------------
    print("\n[6/6] Verifying Geometry & Projector Resolution Scaling...")
    app.geometry("1000x650")
    app.update_idletasks()
    assert app.minsize() == (850, 550)

    modal = main.SettleUpDialog(app, db)
    modal.update_idletasks()
    assert modal.minsize() == (660, 460)
    modal.destroy()

    app.destroy()

    # Clean up test database
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    print("\n==================================================")
    print("ALL TESTS PASSED WITH ZERO DEFECTS (100%)!")
    print("==================================================")

if __name__ == "__main__":
    run_all_tests()
