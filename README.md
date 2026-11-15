# Campus Expense and Split Tracker

A desktop application built with Python, Tkinter, and SQLite to help students and roommates track shared expenses, split costs, and calculate who owes whom.

## Features

- Welcome landing screen with one-click navigation to the tracker dashboard.
- Expense entry form with item description, category, amount, payer name, and split count.
- Input validation to catch blank fields, negative values, and non-numeric inputs.
- Live summary cards displaying total group spend, total transactions, and the highest spending category.
- Dynamic payer suggestions that save new names as you enter them.
- Real-time search by item name or payer, along with category-based filtering.
- Expense table with alternating row colors, sorting, scrollbars, and per-person cost calculations.
- Settle-up window that calculates net balances and the minimum transactions required to settle group debts.
- Export expenses to a CSV file and an option to reset all stored records to zero.

## Project Structure

- `main.py`: Contains the complete application code, including the Tkinter UI and SQLite database operations.
- `campus_expenses.db`: Local SQLite database file where expense records are stored.
- `expenses_report.csv`: Default output file when exporting expenses to CSV.
- `test_app.py`: Test suite verifying database initialization, input validation, calculations, and UI transitions.

## Requirements

- Python 3.8 or higher
- Built entirely with Python standard libraries (`tkinter`, `sqlite3`, `csv`, `datetime`, `math`, `os`, `sys`). No external pip dependencies are needed.

## How to Run

1. Clone the repository:
```bash
git clone https://github.com/PiyushDhal/APP_Tkinter.git
cd APP_Tkinter
```

2. Run the application:
```bash
python main.py
```

3. Run the automated tests:
```bash
python test_app.py
```
