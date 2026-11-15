"""
Comprehensive Test Suite for Campus Expense & Split Tracker
Verifies zero-data start, dynamic payer autocomplete based purely on user input,
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
    print("RUNNING ZERO-DATA & DYNAMIC USER INPUT TEST SUITE")
    print("==================================================")

    test_db_path = "test_dynamic_campus.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    # --------------------------------------------------------------------------
    # 1. VERIFY ZERO-DATA & ZERO-NAME INITIALIZATION
    # --------------------------------------------------------------------------
    print("\n[1/6] Verifying Clean Zero-Data & Zero-Name Start...")
    db = main.DatabaseManager(test_db_path)

    metrics = db.get_summary_metrics()
    assert metrics["total_count"] == 0, f"Expected 0 records, got {metrics['total_count']}"
    assert metrics["total_spend"] == 0.0, f"Expected 0.0 spend, got {metrics['total_spend']}"
    assert metrics["highest_category"] == "N/A", f"Expected N/A, got {metrics['highest_category']}"

    payers = db.get_distinct_payers()
    assert len(payers) == 0, f"Expected 0 payers initially, got {payers}"
    print("✓ Application starts completely clean with zero records and zero pre-set names.")

    # --------------------------------------------------------------------------
    # 2. INPUT VALIDATION & NUMERIC EDGE CASES
    # --------------------------------------------------------------------------
    print("\n[2/6] Testing Input Validation Guards at Zero State...")
    app = main.CampusExpenseApp()
    app.db = db
    app.refresh_payer_autocomplete()
    app.update()

    assert app.kpi_spend_val.cget("text") == "₹ 0.00"
    assert app.kpi_tx_val.cget("text") == "0 Records"
    assert app.kpi_cat_val.cget("text") == "N/A"
    assert len(app.tree.get_children()) == 0
    assert len(app.combo_paid_by["values"]) == 0, "Dropdown should have 0 names initially!"
    assert app.combo_paid_by.get() == "", "Paid By field should be initially empty!"

    # Test blank item
    app.ent_item.delete(0, "end")
    app.ent_item.insert(0, "   ")
    app.ent_amount.insert(0, "100")
    app.combo_paid_by.set("Student1")
    app.on_add_expense()
    assert db.get_summary_metrics()["total_count"] == 0, "Blank item should be rejected!"

    # Test blank paid by
    app.ent_item.delete(0, "end")
    app.ent_item.insert(0, "Lunch")
    app.ent_amount.delete(0, "end")
    app.ent_amount.insert(0, "100")
    app.combo_paid_by.set("   ")
    app.on_add_expense()
    assert db.get_summary_metrics()["total_count"] == 0, "Blank paid_by should be rejected!"

    # Test non-numeric amount
    app.ent_item.delete(0, "end")
    app.ent_item.insert(0, "Lunch")
    app.ent_amount.delete(0, "end")
    app.ent_amount.insert(0, "abc")
    app.combo_paid_by.set("Student1")
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
    print("\n[3/6] Testing Dynamic Storage and Dropdown Growth as User Inputs Names...")

    # Input 1: User types "Alex", Food, ₹ 400
    app.ent_item.delete(0, "end")
    app.ent_item.insert(0, "Subway Sandwich")
    app.combo_category.set("Food")
    app.ent_amount.delete(0, "end")
    app.ent_amount.insert(0, "₹ 400.00")
    app.combo_paid_by.set("Alex")
    app.spin_split.delete(0, "end")
    app.spin_split.insert(0, "2")
    app.on_add_expense()

    assert db.get_summary_metrics()["total_count"] == 1
    assert app.kpi_spend_val.cget("text") == "₹ 400.00"
    assert app.kpi_tx_val.cget("text") == "1 Records"
    assert "Food" in app.kpi_cat_val.cget("text")
    assert len(app.tree.get_children()) == 1
    assert "Alex" in app.combo_paid_by["values"], "Dropdown should now dynamically include 'Alex'!"

    # Input 2: User types "Sam", Travel, ₹ 200
    app.ent_item.delete(0, "end")
    app.ent_item.insert(0, "Cab to Station")
    app.combo_category.set("Travel")
    app.ent_amount.delete(0, "end")
    app.ent_amount.insert(0, "200.00")
    app.combo_paid_by.set("Sam")
    app.spin_split.delete(0, "end")
    app.spin_split.insert(0, "2")
    app.on_add_expense()

    assert db.get_summary_metrics()["total_count"] == 2
    assert app.kpi_spend_val.cget("text") == "₹ 600.00"
    assert app.kpi_tx_val.cget("text") == "2 Records"
    assert "Alex" in app.combo_paid_by["values"]
    assert "Sam" in app.combo_paid_by["values"], "Dropdown should now dynamically include 'Sam'!"

    print("✓ Dynamic storage and dropdown autocomplete populated purely from user input.")

    # --------------------------------------------------------------------------
    # 4. SETTLEMENT COMPUTATION FOR DYNAMIC DATA
    # --------------------------------------------------------------------------
    print("\n[4/6] Verifying Settle-Up Calculations for User Input Data...")
    summary, txs, total_spend = db.get_settlement_data()
    assert total_spend == 600.00
    assert summary["Alex"]["paid"] == 400.00
    assert summary["Alex"]["fair_share"] == 300.00
    assert summary["Alex"]["net_balance"] == 100.00  # Gets back ₹100

    assert summary["Sam"]["paid"] == 200.00
    assert summary["Sam"]["fair_share"] == 300.00
    assert summary["Sam"]["net_balance"] == -100.00  # Owes ₹100

    assert len(txs) == 1
    assert txs[0]["from"] == "Sam"
    assert txs[0]["to"] == "Alex"
    assert txs[0]["amount"] == 100.00
    print("✓ Settle-up modal mathematically resolves debts accurately.")

    # --------------------------------------------------------------------------
    # 5. FILTERING, SEARCH, CSV EXPORT & DELETION
    # --------------------------------------------------------------------------
    print("\n[5/6] Testing Real-Time Search, Filter, CSV Export & Deletion...")
    app.search_var.set("Cab")
    app.load_expenses()
    assert len(app.tree.get_children()) == 1

    app.export_to_csv()
    assert os.path.exists("expenses_report.csv")

    app.reset_filters()
    assert len(app.tree.get_children()) == 2

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
