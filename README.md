# 🎓 Campus Expense & Split Tracker

A presentation-ready, high-contrast desktop application built in Python using **Tkinter (`tkinter` & `ttk`)** and **SQLite3 (`sqlite3`)**. Specifically designed for university students, flatmates, and campus groups to log shared expenses, analyze spending categories, calculate equal or custom splits, and compute optimal debt settlement plans.

---

## 🌟 Key Presentation Features

- **Self-Contained & Zero Setup:** Runs out of the box on standard Python 3.x installations without external dependencies or cloud databases. SQLite database (`campus_expenses.db`) is automatically created and initialized locally.
- **Zero-Data & Dynamic Roster:** Starts completely clean with zero initial records and no pre-set student names. The database, live dashboard KPIs, table, and student dropdown dynamically grow and recalculate in real time as the user inputs names and logs expenses.
- **Presentation-Grade Modern UI:**
  - Styled with the modern `ttk` `'clam'` theme.
  - Windows High-DPI awareness enabled for razor-sharp typography and crisp borders on classroom projectors and 4K displays.
  - Optimized projector resolution: Default geometry **`1000x650`** with a responsive **`minsize(850, 550)`** so widgets never clip on compact screens.
  - High-contrast color palette: Deep navy header (`#0F172A`), clean cards, vibrant category badges, and distinct status indicators.
- **Live Summary Dashboard Bar:**
  - **Total Group Spend (₹):** Live sum of all expenses.
  - **Total Transactions:** Total record count.
  - **Highest Expense Category:** Dynamically identified top budget drain with amount.
- **Robust Input Form:**
  - Inputs: Item / Place, Category (readonly combobox), Amount in ₹, Paid By (with auto-suggest from previous payers), and Split Between (1 to 20 spinbox).
  - Multi-tier input validation: Guards against empty strings, currency symbols, commas, non-numeric values, negative numbers, 0, `inf`, and `nan`.
- **Real-Time Search & Category Filtering:**
  - Live search box filtering simultaneously across *Item / Place* and *Paid By*.
  - Category dropdown filter ("All Categories", "Food", "Travel", "Stationery", "Utilities", "Entertainment", "Other").
  - Instant record count counter.
- **Data Table (`ttk.Treeview`):**
  - Dual scrollbars: Both **Vertical** and **Horizontal** scrollbars embedded with clean grid alignments.
  - Alternating row striping (`#FFFFFF` and `#F8FAFC`).
  - Columns: `ID`, `Date`, `Item / Place`, `Category`, `Total (₹)`, `Paid By`, `Split`, and dynamically calculated **`Each Owes (₹)`** (`amount / split_count`).
  - Interactive column header sorting (ascending / descending with numeric precision).
  - Double-click inspector modal for full transaction inspection.
- **Comprehensive Settle-Up Engine:**
  - Modal window displaying individual contributions vs. fair share with exact integer paise arithmetic (zero floating-point drift).
  - Color-coded balance status (🟢 Gets back ₹X vs. 🔴 Owes ₹Y).
  - **Optimal "Who Owes Whom" Plan:** Uses the greedy Min-Cash-Flow algorithm to resolve all debts in the absolute minimum number of peer-to-peer transfers.
  - One-click **"Copy to Clipboard"** for instant pasting into WhatsApp / group chats.
  - Save full settlement report to a formatted `.txt` file.
- **CSV Data Export:** One-click export to `expenses_report.csv` preserving active category/search filter views with summary row.

---

## 🚀 How to Run

### Requirements
- Python 3.8+ (Tested on Python 3.14 on Windows)
- Standard library modules only (`tkinter`, `sqlite3`, `csv`, `datetime`, `os`, `sys`, `math`)

### Launch Application
```bash
python main.py
```

### Run Automated Audit & Test Suite
```bash
python test_app.py
```

---

## 🗄️ Database Architecture

The local database file is stored at `campus_expenses.db`.

### `expenses` Table Schema
| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | PRIMARY KEY AUTOINCREMENT | Unique expense identifier |
| `item` | `TEXT` | NOT NULL | Expense description (e.g., "Cafeteria Lunch Combo") |
| `category` | `TEXT` | NOT NULL | Food, Travel, Stationery, Utilities, Entertainment, Other |
| `amount` | `REAL` | NOT NULL | Expense total in ₹ |
| `paid_by` | `TEXT` | NOT NULL | Student who paid upfront |
| `split_count`| `INTEGER` | NOT NULL | Number of members sharing this expense (1–20) |
| `date_added` | `TEXT` | NOT NULL | Auto-populated ISO date (`YYYY-MM-DD`) |

---

## 📐 Settlement Mathematics (Who Owes Whom)

The settlement window computes fair balances across group members using exact integer paise arithmetic:

1. **Total Group Spend in Paise:**
   $$\text{Total Paise} = \lfloor \text{Total} \times 100 \rceil$$

2. **Base Fair Share per Student:**
   $$\text{Base} = \lfloor \text{Total Paise} / N \rfloor, \quad \text{Remainder} = \text{Total Paise} \pmod N$$
   *(where $N$ is the count of distinct students participating)*

3. **Net Balance for Member $i$:**
   $$\text{Balance}_i = \text{Paid Paise}_i - \text{Share Paise}_i$$
   - If $\text{Balance}_i > 0$: Student paid more than their share $\rightarrow$ **Gets back money**
   - If $\text{Balance}_i < 0$: Student paid less than their share $\rightarrow$ **Owes money**

4. **Greedy Debt Settlement Algorithm (Min-Cash-Flow):**
   - Separates members into Creditors ($\text{Balance} > 0$) and Debtors ($\text{Balance} < 0$).
   - Recursively pairs the highest debtor with the highest creditor, settling the minimum of their balances:
     $$\text{Settlement} = \min(|\text{Debt}|, \text{Credit})$$
   - Minimizes the total number of peer-to-peer transactions needed to balance the entire group account to ₹0.00.

---

## 🎤 Classroom Presentation Demo Walkthrough

1. **Initial Screen:** Show the auto-seeded demo records (Total Group Spend = ₹ 1,200.00, 4 Records, Top Category = Food).
2. **Real-time Filter & Search:**
   - Type `"Uber"` in the search bar to demonstrate instant real-time table filtering.
   - Select `"Food"` from the Category dropdown to show category-specific expenses.
   - Click **"Reset"** to restore all records.
3. **Add New Expense:**
   - Add `"Physics Lab Manual"`, Category: `Stationery`, Amount: `₹ 120.00`, Paid By: `Rohan`, Split: `2`.
   - Show how the KPI summary cards instantly update, table row striping adjusts, the status bar gives immediate feedback, and `"Rohan"` is dynamically added to the Paid By autocomplete dropdown for future entries.
4. **Column Sorting:** Click on `Total (₹)` or `Each Owes (₹)` to demonstrate ascending/descending sorting.
5. **Settle Up Modal:**
   - Click **"🤝 Settle Up Summary"** (or press `Ctrl+S`).
   - Highlight the individual breakdown table (shows who paid what and their fair share).
   - Point out the step-by-step **"Who Owes Whom"** plan.
   - Click **"Copy Settlement to Clipboard"** to show real-world utility for messaging apps.
6. **CSV Export:** Click **"📥 Export to CSV"** to generate `expenses_report.csv` on disk.
