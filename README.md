# Addo Mart Database Management System

A user-friendly **web-based Database Management System** built with **Flask (Python)**, **HTML5**, and **CSS3**. This GUI connects to your **existing MySQL database** (`Addo_Mart_db`) and lets you perform full **CRUD** (Create, Read, Update, Delete) operations on every table — all through a clean, modern web interface.

No external CSS frameworks (like Bootstrap) are used. Everything is hand-written in plain HTML and CSS.

---

## ✨ Features

- **Login / Authentication** – Users are authenticated against the `login` table in the database.
- **Dashboard** – Shows summary cards:
  - Total number of tables
  - Total number of records
  - Largest table
  - Database connection status
  - Recent activity
  - Buttons to access each table
- **Table Management** – For every database table:
  - View all records in a clean table format
  - **Add** new records via forms
  - **Edit** existing records
  - **Delete** records with a confirmation dialog
  - **Search** / filter records
  - **Pagination** (10 records per page)
- **Foreign Key Support** – Dropdowns show friendly names (e.g. a product's supplier name) instead of raw IDs.
- **Beginner-Friendly Code** – Fully commented, easy to read, and easy to extend.

---

## 📁 Project Structure

```
Database_GUI/
│
├── app.py               # Main Flask application (all routes & logic)
├── database.py          # MySQL connection + authentication setup
├── models.py            # Table schema definitions (easy to add new tables)
├── requirements.txt     # Python dependencies
│
├── templates/           # HTML templates (Jinja2)
│   ├── login.html       # Login page
│   ├── dashboard.html   # Dashboard with summary cards
│   ├── tables.html      # Table records view (search, pagination, actions)
│   ├── add_record.html  # Form to add a new record
│   └── edit_record.html # Form to edit an existing record
│
├── static/
│   └── style.css        # All styling (modern, responsive)
│
└── README.md            # This file
```

---

## 🗃️ Database Used

This project connects to the existing **`Addo_Mart_db`** MySQL database, which contains these tables:

| Table | Primary Key | Description |
|--------|-------------|-------------|
| `Customer_information` | `Customer_id` | Store customers |
| `Employee` | `Employee_id` | Store employees |
| `Suppliers` | `Supplier_id` | Store suppliers |
| `Products` | `Product_id` | Store products (FK → Suppliers) |
| `Orders` | `Order_id` | Store orders (FK → Customers, Employees) |
| `OrderDetails` | `OrderDetails_id` | Order line items (FK → Orders, Products) |

The app discovers the tables automatically via `information_schema`, so it works with the tables present in your database.

---

## 🚀 How to Run Locally

### 1. Prerequisites
- **Python 3.8+** installed on your machine.
- **MySQL** installed and running locally.
- The **`Addo_Mart_db`** database already created (you can import the provided `Addo Mart.sql` file).

### 2. Install Dependencies

Open a terminal inside the `Database_GUI` folder and run:

```bash
pip install -r requirements.txt
```

This installs:
- `Flask` – the web framework
- `mysql-connector-python` – the MySQL driver

### 3. Configure the Database Connection

Open **`database.py`** and update the `DB_CONFIG` dictionary with your MySQL credentials:

```python
DB_CONFIG = {
    "host": "localhost",          # Your MySQL host
    "user": "root",               # Your MySQL username
    "password": "your_password",  # Your MySQL password
    "database": "Addo_Mart_db",   # Your existing database
}
```

### 4. Run the Application

```bash
python app.py
```

You should see output similar to:
```
 * Running on http://127.0.0.1:5000
```

### 5. Open in Browser

Go to **http://127.0.0.1:5000** in your browser.

Log in with the default account:
- **Username:** `admin`
- **Password:** `admin123`

> The first time the app runs, it automatically creates the `login` table (if it doesn't exist) and inserts this default admin user.

---

## 🔑 Changing the Default Login

The default admin credentials are created in `database.py` (`init_database()`). You can change them, or add more users by inserting rows into the `login` table:

```python
INSERT INTO login (username, password) VALUES ('myusername', 'mypassword');
```

---

## 🔧 How to Add a New Table

Adding a new table is very easy. Follow these steps:

1. **Create the table in MySQL** (if not already there).
2. **Add its schema to `models.py`** by adding one entry to the `TABLE_SCHEMAS` dictionary.

Example — adding a `Departments` table:

```python
"Departments": {
    "columns": ["Department_id", "Department_Name", "Location"],
    "pk": "Department_id",
    "fks": {},
    "types": {
        "Department_id": "number",
        "Department_Name": "text",
        "Location": "text",
    },
},
```

That's it! The table will automatically appear on the dashboard and in the sidebar, with full CRUD + search + pagination support.

### Schema explanation:
- **`columns`** – Ordered list of column names (must match the MySQL table).
- **`pk`** – The primary key column.
- **`fks`** – Dict mapping foreign key columns to their referenced tables (used to build dropdowns). Empty `{}` if none.
- **`types`** – Dict mapping each column to an HTML input type (`text`, `number`, `date`, `email`).

---

## 🧠 How Each File Works

### `app.py`
The heart of the application. Contains all Flask routes:
- `GET/POST /` – Login
- `GET /logout` – Logout
- `GET /dashboard` – Dashboard summary
- `GET /table/<table>` – View records (search + pagination)
- `GET/POST /table/<table>/add` – Add record
- `GET/POST /table/<table>/edit/<id>` – Edit record
- `POST /table/<table>/delete/<id>` – Delete record

All CRUD queries are **parameterized** (safe from SQL injection) and use the schema from `models.py`.

### `database.py`
Handles the MySQL connection:
- `DB_CONFIG` – your connection settings
- `get_db()` – returns a fresh MySQL connection
- `init_database()` – creates the `login` table + default admin user
- `get_table_list()` – lists all tables in the connected database

### `models.py`
Central place for all table definitions. This is what makes the app easy to extend. No changes needed in `app.py` when adding tables.

### `templates/*.html`
Jinja2 HTML templates. Each page is a separate template:
- `login.html` – login form
- `dashboard.html` – summary cards + table access buttons + recent activity
- `tables.html` – the main data table with search, pagination, and edit/delete buttons
- `add_record.html` – form for creating new records
- `edit_record.html` – form for updating records (primary key is read-only)

### `static/style.css`
All styling for the app — modern, responsive, and professional. Organized with CSS variables for easy theme customization.

---

## 🛡️ Security Notes

- All SQL queries use **parameterized statements** to prevent SQL injection.
- Routes are protected with a `login_required` decorator.
- **Note:** For simplicity, passwords are stored in plain text. For a production system, store **hashed passwords** using a library like `bcrypt` or `werkzeug.security`.
- The Flask `secret_key` should be changed to a random value before deploying publicly.

---

## 🧪 Sample CRUD Operations the App Performs

| Operation | SQL Query | Route |
|-----------|-----------|-------|
| **Create** | `INSERT INTO table (cols) VALUES (...)` | `/table/<table>/add` |
| **Read** | `SELECT * FROM table WHERE ... LIMIT ... OFFSET ...` | `/table/<table>` |
| **Update** | `UPDATE table SET col = ... WHERE pk = ...` | `/table/<table>/edit/<id>` |
| **Delete** | `DELETE FROM table WHERE pk = ...` | `/table/<table>/delete/<id>` |

---

## 📃 License
This is a learning/demo project. Feel free to modify and use it as you wish.
