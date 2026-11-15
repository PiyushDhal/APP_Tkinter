"""
Campus Expense & Split Tracker
==============================
A presentation-ready desktop application built with Python, Tkinter (ttk), and SQLite3.
Designed for college students, flatmates, and campus project groups to log joint expenses,
track category spending, calculate per-person splits, and resolve group debts with minimal
settlement transactions.

Key Features:
- Self-contained SQLite3 database (campus_expenses.db) with auto-seeding on first launch.
- Presentation-grade modern ttk 'clam' UI with Segoe UI typography and High-DPI support.
- Sensible projector geometry: default 1000x650, minsize 850x550.
- Real-time Summary KPI Cards: Total Group Spend, Total Transactions, Highest Category.
- Clean input form with robust input validation (preventing blank, negative, 0, inf, or nan).
- Live real-time search (by item or payer) and category combobox filtering.
- Alternating striped Treeview data table with both horizontal & vertical scrollbars.
- Settle-Up modal with exact paise arithmetic, individual net balances, and minimal transactions.
- CSV report export ('expenses_report.csv') supporting both filtered and full views.

Author: Campus Expense Tracker Team
"""

import sys
import os
import math
import sqlite3
import csv
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Enable Windows High-DPI awareness so fonts render crisp and sharp on projectors & modern monitors
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================
DB_FILENAME = "campus_expenses.db"
CSV_DEFAULT_FILENAME = "expenses_report.csv"

CATEGORIES = [
    "Food",
    "Travel",
    "Stationery",
    "Utilities",
    "Entertainment",
    "Other"
]

DEFAULT_MEMBERS = ["Piyush", "Manan", "Yukti"]

CATEGORY_DISPLAY = {
    "Food": "🍔 Food",
    "Travel": "🚖 Travel",
    "Stationery": "📚 Stationery",
    "Utilities": "💡 Utilities",
    "Entertainment": "🎬 Entertainment",
    "Other": "📦 Other"
}


# ==============================================================================
# DATABASE MANAGER
# ==============================================================================
class DatabaseManager:
    """Handles all SQLite3 database operations, connection lifecycles, and demo seeding."""

    def __init__(self, db_path=DB_FILENAME):
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        """Returns a new SQLite connection with Row factory enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """Creates the expenses table and automatically seeds realistic demo data if empty."""
        try:
            conn = self.get_connection()
            try:
                with conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS expenses (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            item TEXT NOT NULL,
                            category TEXT NOT NULL,
                            amount REAL NOT NULL,
                            paid_by TEXT NOT NULL,
                            split_count INTEGER NOT NULL,
                            date_added TEXT NOT NULL
                        )
                    """)
                    cursor.execute("SELECT COUNT(*) AS cnt FROM expenses")
                    row = cursor.fetchone()
                    if row and row["cnt"] == 0:
                        self.seed_demo_data(cursor)
            finally:
                conn.close()
        except sqlite3.Error as err:
            print(f"Database Initialization Error: {err}", file=sys.stderr)

    def seed_demo_data(self, cursor):
        """Seeds 4 realistic campus expense records for Piyush, Manan, and Yukti."""
        today = datetime.now().strftime("%Y-%m-%d")
        demo_records = [
            ("Cafeteria Lunch Combo", "Food", 450.00, "Piyush", 3, today),
            ("Campus Uber Cab Fare", "Travel", 300.00, "Manan", 3, today),
            ("Lab Manual & Xerox", "Stationery", 150.00, "Yukti", 3, today),
            ("Hostel Night Snacks", "Food", 210.00, "Piyush", 3, today)
        ]
        cursor.executemany("""
            INSERT INTO expenses (item, category, amount, paid_by, split_count, date_added)
            VALUES (?, ?, ?, ?, ?, ?)
        """, demo_records)

    def add_expense(self, item, category, amount, paid_by, split_count, date_added=None):
        """Inserts a new expense into SQLite3 with clean connection handling."""
        if not date_added:
            date_added = datetime.now().strftime("%Y-%m-%d")

        conn = self.get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO expenses (item, category, amount, paid_by, split_count, date_added)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (item, category, amount, paid_by, split_count, date_added))
                return cursor.lastrowid
        except sqlite3.Error as err:
            print(f"Database Insert Error: {err}", file=sys.stderr)
            raise
        finally:
            conn.close()

    def delete_expense(self, expense_id):
        """Deletes an expense record by its primary key ID."""
        conn = self.get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
                return cursor.rowcount > 0
        except sqlite3.Error as err:
            print(f"Database Delete Error: {err}", file=sys.stderr)
            return False
        finally:
            conn.close()

    def get_expenses(self, category_filter="All", search_query=""):
        """Fetches expenses filtered by category and search keyword (item or paid_by)."""
        query = "SELECT * FROM expenses WHERE 1=1"
        params = []

        if category_filter and category_filter not in ("All", "All Categories"):
            query += " AND category = ?"
            params.append(category_filter)

        if search_query:
            # Escape literal wildcards for strict search
            escaped_q = search_query.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query += " AND (LOWER(item) LIKE ? ESCAPE '\\' OR LOWER(paid_by) LIKE ? ESCAPE '\\')"
            wildcard = f"%{escaped_q}%"
            params.extend([wildcard, wildcard])

        query += " ORDER BY id DESC"

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.Error as err:
            print(f"Database Query Error: {err}", file=sys.stderr)
            return []
        finally:
            conn.close()

    def get_summary_metrics(self):
        """Calculates live KPI metrics: Total Group Spend, Total Count, and Highest Category."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total_count, COALESCE(SUM(amount), 0.0) AS total_spend FROM expenses")
            overall = cursor.fetchone()
            total_count = overall["total_count"] if overall else 0
            total_spend = overall["total_spend"] if overall else 0.0

            cursor.execute("""
                SELECT category, SUM(amount) AS cat_sum
                FROM expenses
                GROUP BY category
                ORDER BY cat_sum DESC
                LIMIT 1
            """)
            top_cat_row = cursor.fetchone()
            if top_cat_row and top_cat_row["cat_sum"] and top_cat_row["cat_sum"] > 0:
                cat_name = top_cat_row["category"]
                display_cat = CATEGORY_DISPLAY.get(cat_name, cat_name)
                highest_category = f"{display_cat} (₹{top_cat_row['cat_sum']:,.2f})"
            else:
                highest_category = "N/A"

            return {
                "total_spend": total_spend,
                "total_count": total_count,
                "highest_category": highest_category
            }
        except sqlite3.Error as err:
            print(f"Database Summary Error: {err}", file=sys.stderr)
            return {
                "total_spend": 0.0,
                "total_count": 0,
                "highest_category": "N/A"
            }
        finally:
            conn.close()

    def get_distinct_payers(self):
        """Returns sorted list of distinct student names who have paid expenses."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT paid_by FROM expenses ORDER BY paid_by ASC")
            rows = cursor.fetchall()
            return [row["paid_by"] for row in rows if row["paid_by"] and row["paid_by"].strip()]
        except sqlite3.Error as err:
            print(f"Database Distinct Payers Error: {err}", file=sys.stderr)
            return []
        finally:
            conn.close()

    def get_settlement_data(self):
        """
        Calculates group spend, member payments, fair shares, and net balances.
        Uses exact integer paise arithmetic to completely eliminate floating-point drift.
        Generates simplified optimal transactions to settle all debts (Greedy Min-Cash-Flow).
        Returns: (members_summary, transactions_to_settle, total_group_spend)
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT amount, paid_by, split_count FROM expenses")
            rows = cursor.fetchall()
        except sqlite3.Error as err:
            print(f"Database Settlement Query Error: {err}", file=sys.stderr)
            return {}, [], 0.0
        finally:
            conn.close()

        if not rows:
            return {}, [], 0.0

        total_group_spend = sum(row["amount"] for row in rows)

        # Accumulate total paid by each student
        contributions = {}
        for row in rows:
            payer = row["paid_by"].strip()
            contributions[payer] = contributions.get(payer, 0.0) + row["amount"]

        members = sorted(contributions.keys())
        num_members = len(members)

        if num_members == 0:
            return {}, [], 0.0

        # Exact paise arithmetic
        total_paise = int(round(total_group_spend * 100))
        base_share_paise = total_paise // num_members
        rem_paise = total_paise % num_members

        fair_shares_paise = {}
        for idx, member in enumerate(members):
            fair_shares_paise[member] = base_share_paise + (1 if idx < rem_paise else 0)

        members_summary = {}
        net_paise = {}
        for member in members:
            paid_paise = int(round(contributions[member] * 100))
            share_paise = fair_shares_paise[member]
            net = paid_paise - share_paise
            net_paise[member] = net
            members_summary[member] = {
                "paid": paid_paise / 100.0,
                "fair_share": share_paise / 100.0,
                "net_balance": net / 100.0
            }

        # Greedy debt settlement algorithm
        debtors = []    # [name, paise_they_owe]
        creditors = []  # [name, paise_they_receive]

        for name, bal in net_paise.items():
            if bal < 0:
                debtors.append([name, -bal])
            elif bal > 0:
                creditors.append([name, bal])

        # Sort highest debtor and highest creditor first for minimal repayments
        debtors.sort(key=lambda x: x[1], reverse=True)
        creditors.sort(key=lambda x: x[1], reverse=True)

        transactions = []
        i, j = 0, 0
        while i < len(debtors) and j < len(creditors):
            debtor_name, debt_amt = debtors[i]
            creditor_name, cred_amt = creditors[j]

            settle = min(debt_amt, cred_amt)
            if settle > 0:
                transactions.append({
                    "from": debtor_name,
                    "to": creditor_name,
                    "amount": settle / 100.0
                })

            debtors[i][1] -= settle
            creditors[j][1] -= settle

            if debtors[i][1] == 0:
                i += 1
            if creditors[j][1] == 0:
                j += 1

        return members_summary, transactions, total_group_spend


# ==============================================================================
# SETTLE UP MODAL DIALOG
# ==============================================================================
class SettleUpDialog(tk.Toplevel):
    """Modern modal dialog displaying student balance breakdown & debt settlement instructions."""

    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.parent = parent
        self.db = db_manager
        self.title("🤝 Group Settle Up Summary — Campus Expense Tracker")
        self.geometry("760x560")
        self.minsize(660, 460)
        self.configure(bg="#F8FAFC")
        self.transient(parent)
        self.grab_set()

        # Center on parent window
        self.center_dialog(760, 560)

        self.members_summary, self.transactions, self.total_spend = self.db.get_settlement_data()
        self.setup_ui()

    def center_dialog(self, width, height):
        self.update_idletasks()
        pw = self.parent.winfo_width()
        ph = self.parent.winfo_height()
        px = self.parent.winfo_rootx()
        py = self.parent.winfo_rooty()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        w = min(width, sw - 40)
        h = min(height, sh - 80)
        x = max(0, px + (pw - w) // 2)
        y = max(0, py + (ph - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def setup_ui(self):
        # Header banner
        header_frame = tk.Frame(self, bg="#1E293B", padx=20, pady=12)
        header_frame.pack(fill=tk.X)

        title_lbl = tk.Label(
            header_frame,
            text="🤝 Group Balance Sheet & Settle-Up Plan",
            font=("Segoe UI", 14, "bold"),
            fg="#FFFFFF",
            bg="#1E293B"
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = tk.Label(
            header_frame,
            text="Calculates each student's net balance and generates minimal transactions to settle all debts.",
            font=("Segoe UI", 9),
            fg="#94A3B8",
            bg="#1E293B"
        )
        subtitle_lbl.pack(anchor="w", pady=(1, 0))

        # Main content container
        content_frame = tk.Frame(self, bg="#F8FAFC", padx=16, pady=10)
        content_frame.pack(fill=tk.BOTH, expand=True)

        if not self.members_summary:
            empty_lbl = tk.Label(
                content_frame,
                text="No expenses recorded yet.\nAdd expenses in the main window to compute settlement balances.",
                font=("Segoe UI", 11),
                fg="#64748B",
                bg="#F8FAFC",
                justify="center"
            )
            empty_lbl.pack(pady=60)
            return

        # Top Metric Stat Cards
        stats_frame = tk.Frame(content_frame, bg="#F8FAFC")
        stats_frame.pack(fill=tk.X, pady=(0, 8))

        member_count = len(self.members_summary)
        avg_share = (self.total_spend / member_count) if member_count else 0.0

        pills = [
            ("TOTAL GROUP SPEND", f"₹ {self.total_spend:,.2f}", "#2563EB", "#EFF6FF"),
            ("ACTIVE STUDENTS", f"{member_count} Members", "#0D9488", "#F0FDFA"),
            ("EQUAL FAIR SHARE", f"₹ {avg_share:,.2f} / student", "#7C3AED", "#F5F3FF")
        ]

        for idx, (label, val, accent, pill_bg) in enumerate(pills):
            p = tk.Frame(stats_frame, bg=pill_bg, bd=1, relief="solid", padx=12, pady=6)
            p.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0 if idx == 0 else 6, 0))
            tk.Label(p, text=label, font=("Segoe UI", 8, "bold"), fg=accent, bg=pill_bg).pack(anchor="w")
            tk.Label(p, text=val, font=("Segoe UI", 12, "bold"), fg="#0F172A", bg=pill_bg).pack(anchor="w", pady=(1, 0))

        # Section 1: Individual Breakdown Table
        lbl_sec1 = tk.Label(
            content_frame,
            text="1. Individual Student Balances (Paid vs. Fair Share)",
            font=("Segoe UI", 10, "bold"),
            fg="#1E293B",
            bg="#F8FAFC"
        )
        lbl_sec1.pack(anchor="w", pady=(2, 4))

        table_frame = tk.Frame(content_frame, bg="#FFFFFF", bd=1, relief="solid")
        table_frame.pack(fill=tk.X, pady=(0, 6))

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        columns = ("name", "paid", "share", "net", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=4)
        self.tree.heading("name", text="Student Name", anchor="w")
        self.tree.heading("paid", text="Total Paid (₹)", anchor="e")
        self.tree.heading("share", text="Fair Share (₹)", anchor="e")
        self.tree.heading("net", text="Net Balance (₹)", anchor="e")
        self.tree.heading("status", text="Status", anchor="center")

        self.tree.column("name", width=160, anchor="w")
        self.tree.column("paid", width=100, anchor="e")
        self.tree.column("share", width=100, anchor="e")
        self.tree.column("net", width=110, anchor="e")
        self.tree.column("status", width=160, anchor="center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.tree.tag_configure("positive", foreground="#059669", font=("Segoe UI", 9, "bold"))
        self.tree.tag_configure("negative", foreground="#DC2626", font=("Segoe UI", 9, "bold"))
        self.tree.tag_configure("neutral", foreground="#475569")

        for member, data in self.members_summary.items():
            paid_str = f"₹ {data['paid']:,.2f}"
            share_str = f"₹ {data['fair_share']:,.2f}"
            net = data["net_balance"]

            if net > 0.009:
                net_str = f"+₹ {net:,.2f}"
                status_str = f"🟢 Gets back ₹{net:,.2f}"
                tag = "positive"
            elif net < -0.009:
                net_str = f"-₹ {abs(net):,.2f}"
                status_str = f"🔴 Owes ₹{abs(net):,.2f}"
                tag = "negative"
            else:
                net_str = "₹ 0.00"
                status_str = "⚪ Settled Up"
                tag = "neutral"

            self.tree.insert("", "end", values=(member, paid_str, share_str, net_str, status_str), tags=(tag,))

        # Section 2: Who Owes Whom (Optimal Settlement Instructions)
        lbl_sec2 = tk.Label(
            content_frame,
            text="2. Recommended Settlement Transactions (Who Owes Whom)",
            font=("Segoe UI", 10, "bold"),
            fg="#1E293B",
            bg="#F8FAFC"
        )
        lbl_sec2.pack(anchor="w", pady=(4, 4))

        settle_box = tk.Frame(content_frame, bg="#FFFFFF", bd=1, relief="solid", padx=8, pady=6)
        settle_box.pack(fill=tk.BOTH, expand=True)

        if not self.transactions:
            settle_none = tk.Label(
                settle_box,
                text="🎉 All accounts are balanced! Nobody owes anything.",
                font=("Segoe UI", 10, "bold"),
                fg="#059669",
                bg="#FFFFFF"
            )
            settle_none.pack(pady=12)
        else:
            settle_canvas = tk.Canvas(settle_box, bg="#FFFFFF", highlightthickness=0)
            settle_vsb = ttk.Scrollbar(settle_box, orient="vertical", command=settle_canvas.yview)
            settle_inner = tk.Frame(settle_canvas, bg="#FFFFFF")

            settle_inner.bind("<Configure>", lambda e: settle_canvas.configure(scrollregion=settle_canvas.bbox("all")))
            settle_canvas.create_window((0, 0), window=settle_inner, anchor="nw")
            settle_canvas.configure(yscrollcommand=settle_vsb.set)

            settle_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            settle_vsb.pack(side=tk.RIGHT, fill=tk.Y)

            for idx, tx in enumerate(self.transactions, 1):
                row_f = tk.Frame(settle_inner, bg="#F8FAFC", bd=1, relief="solid", padx=8, pady=5)
                row_f.pack(fill=tk.X, expand=True, pady=2)

                step_lbl = tk.Label(row_f, text=f"Step {idx}", font=("Segoe UI", 8, "bold"), fg="#64748B", bg="#F8FAFC")
                step_lbl.pack(side=tk.LEFT, padx=(0, 8))

                payer_lbl = tk.Label(row_f, text=tx["from"], font=("Segoe UI", 9, "bold"), fg="#DC2626", bg="#F8FAFC")
                payer_lbl.pack(side=tk.LEFT)

                arrow_lbl = tk.Label(row_f, text="  ➔  pays  ➔  ", font=("Segoe UI", 8), fg="#64748B", bg="#F8FAFC")
                arrow_lbl.pack(side=tk.LEFT)

                payee_lbl = tk.Label(row_f, text=tx["to"], font=("Segoe UI", 9, "bold"), fg="#059669", bg="#F8FAFC")
                payee_lbl.pack(side=tk.LEFT)

                amt_lbl = tk.Label(row_f, text=f"₹ {tx['amount']:,.2f}", font=("Segoe UI", 9, "bold"), fg="#1E3A8A", bg="#F8FAFC")
                amt_lbl.pack(side=tk.RIGHT)

        # Bottom Button Bar
        btn_bar = tk.Frame(self, bg="#E2E8F0", padx=14, pady=8)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        copy_btn = tk.Button(
            btn_bar,
            text="📋 Copy Settlement to Clipboard",
            font=("Segoe UI", 9, "bold"),
            bg="#2563EB",
            fg="#FFFFFF",
            activebackground="#1D4ED8",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.copy_to_clipboard
        )
        copy_btn.pack(side=tk.LEFT)

        export_txt_btn = tk.Button(
            btn_bar,
            text="💾 Save Report (.txt)",
            font=("Segoe UI", 9),
            bg="#FFFFFF",
            fg="#1E293B",
            activebackground="#F1F5F9",
            relief="solid",
            bd=1,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.save_txt_report
        )
        export_txt_btn.pack(side=tk.LEFT, padx=8)

        close_btn = tk.Button(
            btn_bar,
            text="Close",
            font=("Segoe UI", 9),
            bg="#FFFFFF",
            fg="#1E293B",
            activebackground="#F1F5F9",
            relief="solid",
            bd=1,
            padx=14,
            pady=4,
            cursor="hand2",
            command=self.destroy
        )
        close_btn.pack(side=tk.RIGHT)

    def generate_report_text(self):
        """Builds a formatted text representation for clipboard or file export."""
        lines = []
        lines.append("=" * 64)
        lines.append("       CAMPUS EXPENSE TRACKER - GROUP SETTLEMENT REPORT")
        lines.append(f"       Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 64)
        lines.append(f"Total Group Spend:  ₹ {self.total_spend:,.2f}")
        lines.append(f"Active Members:     {len(self.members_summary)} students")
        if self.members_summary:
            lines.append(f"Equal Fair Share:   ₹ {(self.total_spend / len(self.members_summary)):,.2f} per student")
        lines.append("-" * 64)
        lines.append(f"{'Student Name':<22} {'Paid (₹)':>12} {'Share (₹)':>12} {'Net Balance':>14}")
        lines.append("-" * 64)

        for m, data in self.members_summary.items():
            net = data["net_balance"]
            sign = "+" if net > 0.009 else ("-" if net < -0.009 else "")
            net_str = f"{sign}₹{abs(net):,.2f}"
            lines.append(f"{m:<22} {data['paid']:>12,.2f} {data['fair_share']:>12,.2f} {net_str:>14}")

        lines.append("=" * 64)
        lines.append("RECOMMENDED SETTLEMENT TRANSACTIONS (WHO OWES WHOM):")
        lines.append("-" * 64)
        if not self.transactions:
            lines.append("All expenses are evenly settled! No transactions required.")
        else:
            for idx, tx in enumerate(self.transactions, 1):
                lines.append(f"[{idx}] {tx['from']} pays {tx['to']} ➔ ₹ {tx['amount']:,.2f}")
        lines.append("=" * 64)
        return "\n".join(lines)

    def copy_to_clipboard(self):
        """Copies formatted settlement summary to OS clipboard."""
        report = self.generate_report_text()
        self.clipboard_clear()
        self.clipboard_append(report)
        messagebox.showinfo("Copied to Clipboard", "Settlement report copied! You can now paste it into WhatsApp or chat groups.", parent=self)

    def save_txt_report(self):
        """Exports the settlement report to a text file."""
        report = self.generate_report_text()
        default_filename = f"settlement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = filedialog.asksaveasfilename(
            parent=self,
            title="Save Settlement Report",
            defaultextension=".txt",
            initialfile=default_filename,
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(report)
                messagebox.showinfo("Export Successful", f"Settlement report saved successfully to:\n{filepath}", parent=self)
            except Exception as e:
                messagebox.showerror("Export Failed", f"Could not save file:\n{str(e)}", parent=self)


# ==============================================================================
# MAIN APPLICATION WINDOW
# ==============================================================================
class CampusExpenseApp(tk.Tk):
    """Main Application Controller for Campus Expense & Split Tracker."""

    def __init__(self):
        super().__init__()
        self.title("Campus Expense & Split Tracker")
        self.geometry("1000x650")
        self.minsize(850, 550)
        self.configure(bg="#F1F5F9")

        # Center on screen
        self.center_window(1000, 650)

        # Database Manager
        self.db = DatabaseManager(DB_FILENAME)

        # Sorting state for Treeview: {column_id: bool_reverse}
        self.sort_state = {}

        # Configure TTK Styles
        self.setup_styles()

        # Build UI Components
        self.build_ui()

        # Initial Load
        self.load_expenses()
        self.update_summary_kpis()
        self.refresh_payer_autocomplete()

        # Global Keybindings
        self.bind("<Control-f>", lambda e: self.ent_search.focus_set())
        self.bind("<Escape>", lambda e: self.reset_filters())
        self.bind("<Control-s>", lambda e: self.open_settle_up_modal())
        self.bind("<Control-e>", lambda e: self.export_to_csv())

    def center_window(self, width, height):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = min(width, sw - 40)
        h = min(height, sh - 80)
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def setup_styles(self):
        """Applies clam theme and high-contrast styling."""
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        bg_surface = "#FFFFFF"
        fg_text = "#0F172A"
        header_bg = "#E2E8F0"
        select_bg = "#DBEAFE"
        select_fg = "#1E3A8A"

        # Frame styles
        self.style.configure("TFrame", background="#F1F5F9")
        self.style.configure("Surface.TFrame", background=bg_surface)

        # LabelFrame styling
        self.style.configure(
            "TLabelframe",
            background=bg_surface,
            bordercolor="#CBD5E1",
            relief="solid",
            borderwidth=1
        )
        self.style.configure(
            "TLabelframe.Label",
            background=bg_surface,
            foreground="#1E293B",
            font=("Segoe UI", 9, "bold")
        )

        # Labels
        self.style.configure("TLabel", background="#F1F5F9", foreground=fg_text, font=("Segoe UI", 9))
        self.style.configure("Surface.TLabel", background=bg_surface, foreground=fg_text, font=("Segoe UI", 9))
        self.style.configure("Form.TLabel", background=bg_surface, foreground="#334155", font=("Segoe UI", 9, "bold"))

        # Buttons with explicit reliefs and active mappings
        self.style.configure(
            "Primary.TButton",
            font=("Segoe UI", 9, "bold"),
            background="#2563EB",
            foreground="#FFFFFF",
            padding=(10, 5),
            relief="flat",
            borderwidth=0
        )
        self.style.map(
            "Primary.TButton",
            background=[("pressed", "#1E40AF"), ("active", "#1D4ED8"), ("disabled", "#94A3B8")],
            foreground=[("disabled", "#F1F5F9")]
        )

        self.style.configure(
            "Secondary.TButton",
            font=("Segoe UI", 9),
            background="#FFFFFF",
            foreground="#1E293B",
            padding=(8, 4),
            relief="solid",
            borderwidth=1,
            bordercolor="#CBD5E1"
        )
        self.style.map(
            "Secondary.TButton",
            background=[("pressed", "#E2E8F0"), ("active", "#F8FAFC")],
            foreground=[("active", "#0F172A")]
        )

        self.style.configure(
            "Danger.TButton",
            font=("Segoe UI", 9, "bold"),
            background="#DC2626",
            foreground="#FFFFFF",
            padding=(8, 4),
            relief="flat",
            borderwidth=0
        )
        self.style.map(
            "Danger.TButton",
            background=[("pressed", "#991B1B"), ("active", "#B91C1C"), ("disabled", "#FCA5A5")],
            foreground=[("disabled", "#FFFFFF")]
        )

        self.style.configure(
            "Success.TButton",
            font=("Segoe UI", 9, "bold"),
            background="#059669",
            foreground="#FFFFFF",
            padding=(8, 4),
            relief="flat",
            borderwidth=0
        )
        self.style.map(
            "Success.TButton",
            background=[("pressed", "#065F46"), ("active", "#047857"), ("disabled", "#6EE7B7")],
            foreground=[("disabled", "#FFFFFF")]
        )

        self.style.configure(
            "Purple.TButton",
            font=("Segoe UI", 9, "bold"),
            background="#7C3AED",
            foreground="#FFFFFF",
            padding=(10, 5),
            relief="flat",
            borderwidth=0
        )
        self.style.map(
            "Purple.TButton",
            background=[("pressed", "#5B21B6"), ("active", "#6D28D9"), ("disabled", "#C4B5FD")],
            foreground=[("disabled", "#FFFFFF")]
        )

        # Treeview styling
        self.style.configure(
            "Treeview",
            background=bg_surface,
            foreground=fg_text,
            rowheight=26,
            fieldbackground=bg_surface,
            font=("Segoe UI", 9),
            bordercolor="#CBD5E1",
            borderwidth=1
        )
        self.style.map(
            "Treeview",
            background=[("selected", select_bg)],
            foreground=[("selected", select_fg)]
        )

        self.style.configure(
            "Treeview.Heading",
            background=header_bg,
            foreground="#0F172A",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padding=(5, 5),
            bordercolor="#CBD5E1"
        )
        self.style.map(
            "Treeview.Heading",
            background=[("active", "#CBD5E1")],
            foreground=[("active", "#0F172A")]
        )

        # Combobox, Entry, Spinbox styling
        self.style.configure("TCombobox", padding=3)
        self.style.configure("TEntry", padding=3)
        self.style.configure("TSpinbox", padding=3)

    def build_ui(self):
        """Constructs the complete application layout using pure pack at the root."""
        # 1. Header Banner
        self.build_header()

        # 2. KPI Summary Dashboard Cards
        self.build_kpi_dashboard()

        # 3. Main Body Frame (Input Form + Data Table with Filters)
        body_frame = tk.Frame(self, bg="#F1F5F9", padx=12, pady=2)
        body_frame.pack(fill=tk.BOTH, expand=True)

        # Input Form (LabelFrame)
        self.build_input_form(body_frame)

        # Filter & Search Bar
        self.build_filter_bar(body_frame)

        # Data Table (Treeview)
        self.build_data_table(body_frame)

        # 4. Action Bar (Bottom)
        self.build_action_bar()

    def build_header(self):
        """Creates presentation header bar with app branding."""
        header_frame = tk.Frame(self, bg="#0F172A", padx=16, pady=10)
        header_frame.pack(fill=tk.X)

        left_box = tk.Frame(header_frame, bg="#0F172A")
        left_box.pack(side=tk.LEFT)

        app_title = tk.Label(
            left_box,
            text="🎓 Campus Expense & Split Tracker",
            font=("Segoe UI", 15, "bold"),
            fg="#FFFFFF",
            bg="#0F172A"
        )
        app_title.pack(anchor="w")

        app_sub = tk.Label(
            left_box,
            text="Shared budget tracking, category breakdown & optimal student debt settlement",
            font=("Segoe UI", 8),
            fg="#94A3B8",
            bg="#0F172A"
        )
        app_sub.pack(anchor="w", pady=(1, 0))

        # Right side info pill
        right_box = tk.Frame(header_frame, bg="#0F172A")
        right_box.pack(side=tk.RIGHT)

        db_badge = tk.Label(
            right_box,
            text="● SQLite: campus_expenses.db",
            font=("Segoe UI", 8, "bold"),
            fg="#10B981",
            bg="#1E293B",
            padx=8,
            pady=3,
            relief="flat"
        )
        db_badge.pack(anchor="e")

    def build_kpi_dashboard(self):
        """Builds 3 modern high-contrast KPI cards."""
        dash_container = tk.Frame(self, bg="#F1F5F9", padx=12, pady=2)
        dash_container.pack(fill=tk.X, pady=(4, 2))

        # Card 1: Total Group Spend
        c1 = tk.Frame(dash_container, bg="#FFFFFF", bd=1, relief="solid", padx=12, pady=8)
        c1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        tk.Label(c1, text="TOTAL GROUP SPEND", font=("Segoe UI", 8, "bold"), fg="#2563EB", bg="#FFFFFF").pack(anchor="w")
        self.kpi_spend_val = tk.Label(c1, text="₹ 0.00", font=("Segoe UI", 15, "bold"), fg="#0F172A", bg="#FFFFFF")
        self.kpi_spend_val.pack(anchor="w", pady=(2, 0))
        tk.Label(c1, text="Combined spending across group", font=("Segoe UI", 8), fg="#64748B", bg="#FFFFFF").pack(anchor="w")

        # Card 2: Total Transactions
        c2 = tk.Frame(dash_container, bg="#FFFFFF", bd=1, relief="solid", padx=12, pady=8)
        c2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        tk.Label(c2, text="TOTAL TRANSACTIONS", font=("Segoe UI", 8, "bold"), fg="#059669", bg="#FFFFFF").pack(anchor="w")
        self.kpi_tx_val = tk.Label(c2, text="0 Records", font=("Segoe UI", 15, "bold"), fg="#0F172A", bg="#FFFFFF")
        self.kpi_tx_val.pack(anchor="w", pady=(2, 0))
        tk.Label(c2, text="Logged student expense items", font=("Segoe UI", 8), fg="#64748B", bg="#FFFFFF").pack(anchor="w")

        # Card 3: Highest Spend Category
        c3 = tk.Frame(dash_container, bg="#FFFFFF", bd=1, relief="solid", padx=12, pady=8)
        c3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))
        tk.Label(c3, text="HIGHEST EXPENSE CATEGORY", font=("Segoe UI", 8, "bold"), fg="#D97706", bg="#FFFFFF").pack(anchor="w")
        self.kpi_cat_val = tk.Label(c3, text="N/A", font=("Segoe UI", 14, "bold"), fg="#0F172A", bg="#FFFFFF")
        self.kpi_cat_val.pack(anchor="w", pady=(2, 0))
        tk.Label(c3, text="Top budget consumption", font=("Segoe UI", 8), fg="#64748B", bg="#FFFFFF").pack(anchor="w")

    def build_input_form(self, parent):
        """Constructs the clean grid input form inside a LabelFrame."""
        form_frame = ttk.LabelFrame(parent, text=" ➕ Add New Expense ", padding=10)
        form_frame.pack(fill=tk.X, pady=(2, 6))

        for col in range(6):
            form_frame.columnconfigure(col, weight=1)

        # Row 0: Labels
        ttk.Label(form_frame, text="Item / Place Description *", style="Form.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", padx=4, pady=(0, 2))
        ttk.Label(form_frame, text="Category *", style="Form.TLabel").grid(row=0, column=2, sticky="w", padx=4, pady=(0, 2))
        ttk.Label(form_frame, text="Amount in ₹ *", style="Form.TLabel").grid(row=0, column=3, sticky="w", padx=4, pady=(0, 2))
        ttk.Label(form_frame, text="Paid By (Student Name) *", style="Form.TLabel").grid(row=0, column=4, sticky="w", padx=4, pady=(0, 2))
        ttk.Label(form_frame, text="Split Between (1-20) *", style="Form.TLabel").grid(row=0, column=5, sticky="w", padx=4, pady=(0, 2))

        # Row 1: Entry Controls
        self.ent_item = ttk.Entry(form_frame, font=("Segoe UI", 9))
        self.ent_item.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=(0, 6))

        self.combo_category = ttk.Combobox(form_frame, values=CATEGORIES, state="readonly", font=("Segoe UI", 9))
        self.combo_category.set("Food")
        self.combo_category.grid(row=1, column=2, sticky="ew", padx=4, pady=(0, 6))

        self.ent_amount = ttk.Entry(form_frame, font=("Segoe UI", 9))
        self.ent_amount.grid(row=1, column=3, sticky="ew", padx=4, pady=(0, 6))

        self.combo_paid_by = ttk.Combobox(form_frame, values=DEFAULT_MEMBERS, font=("Segoe UI", 9))
        self.combo_paid_by.set("Piyush")
        self.combo_paid_by.grid(row=1, column=4, sticky="ew", padx=4, pady=(0, 6))

        self.spin_split = ttk.Spinbox(form_frame, from_=1, to=20, font=("Segoe UI", 9), justify="center")
        self.spin_split.set(3)
        self.spin_split.grid(row=1, column=5, sticky="ew", padx=4, pady=(0, 6))

        # Row 2: Form Action Buttons
        btn_container = tk.Frame(form_frame, bg="#FFFFFF")
        btn_container.grid(row=2, column=0, columnspan=6, sticky="e", padx=4, pady=(2, 0))

        btn_clear = ttk.Button(btn_container, text="🧹 Clear Fields", style="Secondary.TButton", command=self.clear_form)
        btn_clear.pack(side=tk.RIGHT, padx=(6, 0))

        btn_add = ttk.Button(btn_container, text="➕ Add Expense", style="Primary.TButton", command=self.on_add_expense)
        btn_add.pack(side=tk.RIGHT)

        # Bind Enter key inside entry widgets to trigger add expense
        self.ent_item.bind("<Return>", lambda e: self.on_add_expense())
        self.ent_amount.bind("<Return>", lambda e: self.on_add_expense())
        self.combo_paid_by.bind("<Return>", lambda e: self.on_add_expense())

    def build_filter_bar(self, parent):
        """Constructs search and category filtering controls."""
        filter_frame = tk.Frame(parent, bg="#F1F5F9", pady=3)
        filter_frame.pack(fill=tk.X)

        # Real-time Search Box
        tk.Label(filter_frame, text="🔍 Search:", font=("Segoe UI", 9, "bold"), fg="#334155", bg="#F1F5F9").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.load_expenses())
        self.ent_search = ttk.Entry(filter_frame, textvariable=self.search_var, width=22, font=("Segoe UI", 9))
        self.ent_search.pack(side=tk.LEFT, padx=(4, 12))

        # Filter by Category Combobox
        tk.Label(filter_frame, text="📁 Category Filter:", font=("Segoe UI", 9, "bold"), fg="#334155", bg="#F1F5F9").pack(side=tk.LEFT)
        filter_options = ["All Categories"] + CATEGORIES
        self.combo_filter_cat = ttk.Combobox(filter_frame, values=filter_options, state="readonly", width=15, font=("Segoe UI", 9))
        self.combo_filter_cat.set("All Categories")
        self.combo_filter_cat.bind("<<ComboboxSelected>>", lambda e: self.load_expenses())
        self.combo_filter_cat.pack(side=tk.LEFT, padx=(4, 8))

        # Reset Filter Button
        btn_reset = ttk.Button(filter_frame, text="Reset", style="Secondary.TButton", command=self.reset_filters)
        btn_reset.pack(side=tk.LEFT)

        # Right-aligned Record Counter
        self.lbl_record_count = tk.Label(
            filter_frame,
            text="Showing 0 records",
            font=("Segoe UI", 8),
            fg="#64748B",
            bg="#F1F5F9"
        )
        self.lbl_record_count.pack(side=tk.RIGHT)

    def build_data_table(self, parent):
        """Constructs the ttk.Treeview data table with both horizontal & vertical scrollbars."""
        table_container = tk.Frame(parent, bg="#FFFFFF", bd=1, relief="solid")
        table_container.pack(fill=tk.BOTH, expand=True, pady=(2, 4))

        # Grid manager inside table_container ensures neat corners between scrollbars
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

        columns = ("id", "date", "item", "category", "amount", "paid_by", "split", "each_owes")
        self.tree = ttk.Treeview(table_container, columns=columns, show="headings", selectmode="browse")

        col_defs = [
            ("id", "ID", 45, 35, "center"),
            ("date", "Date", 90, 75, "center"),
            ("item", "Item / Place", 210, 130, "w"),
            ("category", "Category", 115, 90, "center"),
            ("amount", "Total (₹)", 105, 80, "e"),
            ("paid_by", "Paid By", 130, 95, "w"),
            ("split", "Split", 65, 50, "center"),
            ("each_owes", "Each Owes (₹)", 110, 85, "e")
        ]

        for col_id, heading_text, width, minw, anchor in col_defs:
            self.tree.heading(
                col_id,
                text=heading_text,
                anchor=anchor,
                command=lambda c=col_id: self.sort_tree_column(c)
            )
            self.tree.column(col_id, width=width, minwidth=minw, anchor=anchor)

        vsb = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # Alternating Row Striping with explicit foreground for high contrast
        self.tree.tag_configure("oddrow", background="#FFFFFF", foreground="#0F172A")
        self.tree.tag_configure("evenrow", background="#F8FAFC", foreground="#0F172A")

        # Shortcuts: Delete key to delete row, double click for details inspector
        self.tree.bind("<Delete>", lambda e: self.on_delete_selected())
        self.tree.bind("<Double-1>", lambda e: self.on_row_double_click(e))

    def build_action_bar(self):
        """Constructs bottom action bar with Delete, CSV Export, and Settle Up buttons."""
        bar = tk.Frame(self, bg="#FFFFFF", bd=1, relief="solid", padx=14, pady=8)
        bar.pack(fill=tk.X, side=tk.BOTTOM)

        # Left: Live status label
        self.status_lbl = tk.Label(
            bar,
            text="Ready. Select an expense to inspect or delete. Press Ctrl+S for Settle-Up.",
            font=("Segoe UI", 9),
            fg="#475569",
            bg="#FFFFFF"
        )
        self.status_lbl.pack(side=tk.LEFT)

        # Right: Action Buttons
        settle_btn = ttk.Button(bar, text="🤝 Settle Up Summary", style="Purple.TButton", command=self.open_settle_up_modal)
        settle_btn.pack(side=tk.RIGHT, padx=(6, 0))

        export_btn = ttk.Button(bar, text="📥 Export to CSV", style="Success.TButton", command=self.export_to_csv)
        export_btn.pack(side=tk.RIGHT, padx=6)

        del_btn = ttk.Button(bar, text="🗑️ Delete Selected", style="Danger.TButton", command=self.on_delete_selected)
        del_btn.pack(side=tk.RIGHT)

    # ==========================================================================
    # LOGIC & EVENT HANDLERS
    # ==========================================================================
    def on_add_expense(self):
        """Validates inputs with full protection against blanks, non-numbers, negative, 0, inf, and nan."""
        item = self.ent_item.get().strip()
        category = self.combo_category.get().strip()
        amount_raw = self.ent_amount.get().strip()
        paid_by = " ".join(self.combo_paid_by.get().split())
        split_raw = self.spin_split.get().strip()

        # Item validation
        if not item:
            messagebox.showwarning("Validation Error", "Please enter an Item or Place description.\n(e.g., 'Subway Sandwich', 'Auto Rickshaw').")
            self.ent_item.focus_set()
            return

        if len(item) > 100:
            item = item[:100]

        # Category validation
        if not category or category not in CATEGORIES:
            messagebox.showwarning("Validation Error", f"Please select a valid Category from:\n{', '.join(CATEGORIES)}")
            self.combo_category.focus_set()
            return

        # Amount validation: handles currency symbols, commas, nan, inf, zero, negative
        amount_clean = amount_raw.replace("₹", "").replace("Rs.", "").replace("Rs", "").replace(",", "").strip()
        if not amount_clean:
            messagebox.showwarning("Validation Error", "Please enter the expense Amount in ₹.")
            self.ent_amount.focus_set()
            return

        try:
            amount = float(amount_clean)
            if math.isnan(amount) or math.isinf(amount) or amount <= 0:
                raise ValueError("Amount must be a positive finite number.")
            if amount > 10_000_000:
                raise ValueError("Amount cannot exceed ₹ 10,000,000.00.")
        except ValueError:
            messagebox.showerror("Validation Error", "Invalid Amount! Please enter a valid positive number.\n(e.g., 250 or 49.50)")
            self.ent_amount.focus_set()
            return

        # Paid By validation
        if not paid_by:
            messagebox.showwarning("Validation Error", "Please specify who paid for this expense.")
            self.combo_paid_by.focus_set()
            return

        if len(paid_by) > 60:
            paid_by = paid_by[:60]

        # Split Count validation
        try:
            split_count = int(split_raw)
            if split_count < 1 or split_count > 20:
                raise ValueError("Out of range")
        except ValueError:
            messagebox.showerror("Validation Error", "Split Between must be a whole number between 1 and 20.")
            self.spin_split.focus_set()
            return

        # Insert into database
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            new_id = self.db.add_expense(item, category, round(amount, 2), paid_by, split_count, today)
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to save expense:\n{str(e)}")
            return

        # UI updates
        self.clear_form()
        self.load_expenses()
        self.update_summary_kpis()
        self.refresh_payer_autocomplete()
        self.status_lbl.configure(text=f"✓ Added expense #{new_id}: '{item}' (₹{amount:,.2f} paid by {paid_by})")

    def clear_form(self):
        """Resets the input form fields."""
        self.ent_item.delete(0, tk.END)
        self.combo_category.set("Food")
        self.ent_amount.delete(0, tk.END)
        self.combo_paid_by.set("Piyush")
        self.spin_split.set(3)
        self.ent_item.focus_set()

    def reset_filters(self):
        """Clears search and resets category dropdown to All."""
        self.search_var.set("")
        self.combo_filter_cat.set("All Categories")
        self.load_expenses()

    def load_expenses(self):
        """Queries the database and populates the Treeview."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        category_filter = self.combo_filter_cat.get()
        search_query = self.search_var.get()

        rows = self.db.get_expenses(category_filter=category_filter, search_query=search_query)

        for idx, row in enumerate(rows):
            amount = row["amount"]
            split = row["split_count"]
            each_owes = round(amount / split, 2) if split > 0 else 0.0
            cat_display = CATEGORY_DISPLAY.get(row["category"], row["category"])

            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            self.tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row["id"],
                    row["date_added"],
                    row["item"],
                    cat_display,
                    f"₹ {amount:,.2f}",
                    row["paid_by"],
                    f"{split} ways",
                    f"₹ {each_owes:,.2f}"
                ),
                tags=(tag,)
            )

        total_in_db = self.db.get_summary_metrics()["total_count"]
        showing_cnt = len(rows)
        if category_filter != "All Categories" or search_query:
            self.lbl_record_count.configure(text=f"Showing {showing_cnt} of {total_in_db} records (Filtered)")
        else:
            self.lbl_record_count.configure(text=f"Showing {showing_cnt} of {total_in_db} records")

    def update_summary_kpis(self):
        """Refreshes the 3 top dashboard metric cards."""
        metrics = self.db.get_summary_metrics()
        self.kpi_spend_val.configure(text=f"₹ {metrics['total_spend']:,.2f}")
        self.kpi_tx_val.configure(text=f"{metrics['total_count']} Records")
        self.kpi_cat_val.configure(text=metrics['highest_category'])

    def refresh_payer_autocomplete(self):
        """Updates the Paid By combobox dropdown with all distinct student names."""
        db_payers = self.db.get_distinct_payers()
        all_payers = sorted(list(set(DEFAULT_MEMBERS + db_payers)))
        self.combo_paid_by["values"] = all_payers

    def on_delete_selected(self):
        """Prompts confirmation and deletes selected expense row."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Selection Required", "Please select an expense row from the table to delete.")
            return

        item_id = selected[0]
        row_values = self.tree.item(item_id, "values")
        if not row_values or len(row_values) < 6:
            return

        item_name = row_values[2]
        amount_str = row_values[4]
        payer = row_values[5]

        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete this expense?\n\n"
            f"• ID: {item_id}\n"
            f"• Item: {item_name}\n"
            f"• Amount: {amount_str}\n"
            f"• Paid By: {payer}\n\n"
            f"This action cannot be undone.",
            icon="warning"
        )

        if confirm:
            if self.db.delete_expense(int(item_id)):
                self.load_expenses()
                self.update_summary_kpis()
                self.refresh_payer_autocomplete()
                self.status_lbl.configure(text=f"✓ Deleted expense #{item_id}: '{item_name}'")
            else:
                messagebox.showerror("Error", "Could not delete the selected record from the database.")

    def on_row_double_click(self, event):
        """Shows detailed information when double clicking a row."""
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        vals = self.tree.item(item_id, "values")
        if not vals or len(vals) < 8:
            return

        detail_msg = (
            f"Expense Details (ID: {vals[0]})\n"
            f"{'='*38}\n"
            f"Date Added:    {vals[1]}\n"
            f"Item / Place:  {vals[2]}\n"
            f"Category:      {vals[3]}\n"
            f"Total Amount:  {vals[4]}\n"
            f"Paid By:       {vals[5]}\n"
            f"Split Count:   {vals[6]}\n"
            f"Each Owes:     {vals[7]}"
        )
        messagebox.showinfo("Expense Details", detail_msg)

    def sort_tree_column(self, col):
        """Sorts Treeview rows when clicking a column header."""
        children = self.tree.get_children("")
        if not children:
            return

        items = [(self.tree.set(k, col), k) for k in children]
        reverse = self.sort_state.get(col, False)

        def convert_val(val_tuple):
            val = val_tuple[0]
            # Strip currency, emojis, commas, or extra text for clean numeric sort
            cleaned = (
                val.replace("₹", "")
                .replace(",", "")
                .replace("ways", "")
                .replace("🍔", "")
                .replace("🚖", "")
                .replace("📚", "")
                .replace("💡", "")
                .replace("🎬", "")
                .replace("📦", "")
                .strip()
            )
            try:
                return (0, float(cleaned))
            except ValueError:
                return (1, val.lower())

        items.sort(key=convert_val, reverse=reverse)

        for index, (_, k) in enumerate(items):
            self.tree.move(k, "", index)
            tag = "evenrow" if index % 2 == 0 else "oddrow"
            self.tree.item(k, tags=(tag,))

        # Toggle sort direction
        self.sort_state[col] = not reverse

    def export_to_csv(self):
        """Exports currently filtered or all records to 'expenses_report.csv'."""
        default_path = os.path.abspath(CSV_DEFAULT_FILENAME)
        try:
            category_filter = self.combo_filter_cat.get()
            search_query = self.search_var.get()
            records = self.db.get_expenses(category_filter=category_filter, search_query=search_query)

            if not records:
                messagebox.showinfo("No Data to Export", "There are no expenses matching the current view to export.")
                return

            with open(default_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # Header row
                writer.writerow([
                    "ID",
                    "Date Added",
                    "Item / Place",
                    "Category",
                    "Total Amount (INR)",
                    "Paid By",
                    "Split Count",
                    "Each Owes (INR)"
                ])

                total_spend = 0.0
                for r in records:
                    amt = r["amount"]
                    split = r["split_count"]
                    each = round(amt / split, 2) if split > 0 else 0.0
                    total_spend += amt
                    writer.writerow([
                        r["id"],
                        r["date_added"],
                        r["item"],
                        r["category"],
                        f"{amt:.2f}",
                        r["paid_by"],
                        split,
                        f"{each:.2f}"
                    ])

                # Summary Row
                writer.writerow([])
                writer.writerow(["", "", "", "TOTAL SPEND", f"{total_spend:.2f}", "", "", ""])

            self.status_lbl.configure(text=f"✓ Exported {len(records)} records to {os.path.basename(default_path)}")
            messagebox.showinfo(
                "Export Successful",
                f"Expenses successfully exported to CSV!\n\n"
                f"• File: {default_path}\n"
                f"• Total Records: {len(records)}\n"
                f"• Exported Spend: ₹ {total_spend:,.2f}"
            )
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export CSV:\n{str(e)}")

    def open_settle_up_modal(self):
        """Opens the Settle Up Modal dialog."""
        SettleUpDialog(self, self.db)


# ==============================================================================
# APPLICATION ENTRY POINT
# ==============================================================================
def main():
    app = CampusExpenseApp()
    app.mainloop()


if __name__ == "__main__":
    main()
