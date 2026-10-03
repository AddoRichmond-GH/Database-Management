"""
app.py

Main Flask application for the Database Management System GUI.

This app connects to the EXISTING MySQL database (Addo_Mart_db) and provides
a web interface to perform CRUD (Create, Read, Update, Delete) operations on
every table in that database.

Routes:
    /                          -> Login page (GET) / authenticate (POST)
    /dashboard                 -> Main dashboard with summary cards
    /table/<table_name>        -> View records (with search + pagination)
    /table/<table_name>/add    -> Add a new record (form + insert)
    /table/<table_name>/edit/<id> -> Edit an existing record (form + update)
    /table/<table_name>/delete/<id> -> Delete a record (with confirmation)
    /logout                    -> Log the user out
"""

import math
import os
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    abort,
)

import database
import models

# ---------------------------------------------------------------------------
# Flask app setup
# ---------------------------------------------------------------------------
app = Flask(__name__)

# Secret key needed for sessions (used to remember logged-in users).
# For production, replace this with a random secure value.
app.secret_key = "adora_gui_secret_key_change_me"

# Number of records shown on one page of the table view.
PAGE_SIZE = 10


# ---------------------------------------------------------------------------
# Product image helper
# ---------------------------------------------------------------------------
def _normalize(name):
    """Lowercase and strip spaces/punctuation for fuzzy image matching."""
    return "".join(c for c in name.lower() if c.isalnum())


def _product_image(product_name):
    """
    Return the static image filename for a product, or None if no image exists.

    Tries an exact normalized match first, then a 'first-word' match so that
    e.g. 'Nescafe Classic' matches 'Nescafe.jpg'.
    """
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    try:
        files = os.listdir(static_dir)
    except OSError:
        return None

    # Build lookup maps from the actual image filenames.
    exact = {}
    first_word = {}
    for f in files:
        base, ext = os.path.splitext(f)
        if ext.lower() not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
            continue
        exact[_normalize(base)] = f
        words = _normalize(base).split()
        if words:
            first_word.setdefault(words[0], f)

    target = _normalize(product_name)
    if target in exact:
        return exact[target]
    t_words = target.split()
    if t_words and t_words[0] in first_word:
        return first_word[t_words[0]]
    return None


# ---------------------------------------------------------------------------
# Login helpers
# ---------------------------------------------------------------------------
def login_required(func):
    """
    Decorator that protects a route.

    If the user is not logged in, they are redirected to the login page.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return func(*args, **kwargs)
    return wrapper


def admin_required(func):
    """
    Decorator that protects admin-only routes.

    If the user is not logged in, redirect to login.
    If the user is logged in but is not an admin, redirect them to their
    appropriate home page (customer portal for customers).
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        if session.get("role") != "admin":
            flash("You do not have permission to access that page.", "error")
            return redirect(url_for("store"))
        return func(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Login page.

    GET  -> show the login form.
    POST -> check username/password against the 'login' table in MySQL.

    If authentication succeeds, the user is redirected to the dashboard.
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Please enter both username and password.", "error")
            return redirect(url_for("login"))

        # Query the login users table for a matching username/password.
        db = database.get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM login WHERE username = %s AND password = %s",
            (username, password),
        )
        user = cursor.fetchone()
        cursor.close()
        db.close()

        if user:
            session["username"] = user["username"]
            session["user_id"] = user["id"]
            session["role"] = user.get("role", "customer")
            flash(f"Welcome back, {user['username']}!", "success")
            # Route users based on their role.
            if user.get("role") == "admin":
                return redirect(url_for("dashboard"))
            # Customers go to the storefront; respect a "next" target so
            # they return to the page they were trying to reach.
            nxt = request.form.get("next") or request.args.get("next", "")
            if nxt and nxt.startswith("/"):
                return redirect(nxt)
            return redirect(url_for("store"))
        else:
            flash("Invalid username or password. Try again.", "error")
            return redirect(url_for("login"))

    return render_template("login.html")


# ---------------------------------------------------------------------------
# Customer registration (create an account)
# ---------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Customer registration page.

    GET  -> show the registration form.
    POST -> create a login account (role = customer) and a matching
            Customer_information record, then log the customer in.
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()

        errors = []
        if not username or not password:
            errors.append("Username and password are required.")
        if not first_name or not last_name:
            errors.append("First name and last name are required.")

        db = database.get_db()
        cursor = db.cursor(dictionary=True)

        # Check if the username already exists.
        cursor.execute(
            "SELECT id FROM login WHERE username = %s", (username,)
        )
        if cursor.fetchone():
            errors.append("That username is already taken. Please choose another.")

        if errors:
            cursor.close()
            db.close()
            for e in errors:
                flash(e, "error")
            return render_template(
                "register.html",
                form_values=request.form,
            )

        try:
            # 1. Create the login account (role = customer).
            cursor.execute(
                "INSERT INTO login (username, password, role) VALUES (%s, %s, %s)",
                (username, password, "customer"),
            )
            login_id = cursor.lastrowid

            # 2. Create the customer record linked to this login.
            cursor.execute(
                "SELECT COALESCE(MAX(Customer_id), 0) AS m FROM Customer_information"
            )
            new_customer_id = cursor.fetchone()["m"] + 1
            cursor.execute(
                """
                INSERT INTO Customer_information
                    (Customer_id, First_Name, Last_Name, Phone, Email, Address, login_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (new_customer_id, first_name, last_name, phone, email, address, login_id),
            )

            db.commit()
            cursor.close()
            db.close()

            # Log the customer in automatically.
            session["username"] = username
            session["user_id"] = login_id
            session["role"] = "customer"
            session["customer_id"] = new_customer_id

            flash(
                f"Account created successfully! Welcome, {first_name} {last_name}!",
                "success",
            )
            return redirect(url_for("store"))

        except Exception as e:
            db.rollback()
            cursor.close()
            db.close()
            flash(f"Error creating account: {e}", "error")
            return render_template(
                "register.html",
                form_values=request.form,
            )

    return render_template("register.html", form_values={})


# ---------------------------------------------------------------------------
# Public storefront (no login required to browse)
# ---------------------------------------------------------------------------
@app.route("/")
@app.route("/store")
def store():
    """
    Public storefront.

    Anyone can browse products. Buying requires login/signup, which is
    enforced by the /customer/place_order route.
    """
    # If an admin is browsing, send them to the admin dashboard.
    if session.get("role") == "admin":
        return redirect(url_for("dashboard"))

    db = database.get_db()
    cursor = db.cursor(dictionary=True)

    # Find the customer record linked to this login (if logged in).
    customer = None
    if session.get("user_id"):
        cursor.execute(
            "SELECT * FROM Customer_information WHERE login_id = %s",
            (session.get("user_id"),),
        )
        customer = cursor.fetchone()

    # Load products for browsing.
    cursor.execute(
        "SELECT Product_id, Product_Name, Category, UnitPrice, StockQuantity "
        "FROM Products ORDER BY Product_Name"
    )
    products = cursor.fetchall()

    # Attach the matching image file to each product (None if no image exists).
    for p in products:
        p["image"] = _product_image(p["Product_Name"])

    # Load the customer's past orders.
    orders = []
    if customer:
        cursor.execute(
            """
            SELECT o.Order_id, o.OrderDate, o.TotalAmount,
                   COUNT(od.OrderDetails_id) AS line_count
            FROM Orders o
            LEFT JOIN OrderDetails od ON o.Order_id = od.Order_id
            WHERE o.Customer_id = %s
            GROUP BY o.Order_id, o.OrderDate, o.TotalAmount
            ORDER BY o.Order_id DESC
            """,
            (customer["Customer_id"],),
        )
        orders = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "store.html",
        username=session.get("username"),
        customer=customer,
        products=products,
        orders=orders,
        total_products=len(products),
    )


@app.route("/about")
def about():
    """Public About Us page."""
    return render_template(
        "about.html",
        username=session.get("username"),
    )


@app.route("/contact", methods=["GET", "POST"])
def contact():
    """Public Contact page."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        flash(
            f"Thank you{', ' + name if name else ''}! Your message has been received. "
            "We will get back to you soon.",
            "success",
        )
        return redirect(url_for("contact"))
    return render_template(
        "contact.html",
        username=session.get("username"),
    )


# ---------------------------------------------------------------------------
# Customer home (portal) - browse products, view orders, place orders
# ---------------------------------------------------------------------------
@app.route("/customer")
@login_required
def customer_home():
    """Customer portal home page (legacy route -> redirect to storefront)."""
    # If the current user is an admin, send them to the admin dashboard.
    if session.get("role") == "admin":
        return redirect(url_for("dashboard"))
    return redirect(url_for("store"))


# ---------------------------------------------------------------------------
# Customer place order (uses the logged-in customer's own record)
# ---------------------------------------------------------------------------
@app.route("/customer/place_order", methods=["GET", "POST"])
@login_required
def customer_place_order():
    """Let the logged-in customer place an order with multiple products."""
    if session.get("role") == "admin":
        return redirect(url_for("dashboard"))

    db = database.get_db()
    cursor = db.cursor(dictionary=True)

    # Find the customer record linked to this login.
    cursor.execute(
        "SELECT * FROM Customer_information WHERE login_id = %s",
        (session.get("user_id"),),
    )
    customer = cursor.fetchone()
    if not customer:
        cursor.close()
        db.close()
        flash(
            "No customer profile found for your account. Please contact support.",
            "error",
        )
        return redirect(url_for("store"))

    # Load products for the cart.
    cursor.execute(
        "SELECT Product_id, Product_Name, UnitPrice, StockQuantity "
        "FROM Products ORDER BY Product_Name"
    )
    products = cursor.fetchall()

    # Attach the matching image file to each product (None if no image exists).
    for p in products:
        p["image"] = _product_image(p["Product_Name"])

    if request.method == "POST":
        product_ids = request.form.getlist("product_id[]")
        quantities = request.form.getlist("quantity[]")

        lines = []
        for pid, qty in zip(product_ids, quantities):
            if not pid:
                continue
            try:
                q = int(qty or 0)
            except ValueError:
                q = 0
            if q > 0:
                lines.append((int(pid), q))

        if not lines:
            cursor.close()
            db.close()
            flash("Please add at least one product with a valid quantity.", "error")
            return render_template(
                "customer_order.html",
                products=products,
                customer=customer,
                username=session.get("username"),
            )

        try:
            # --- Next Order_id ---
            cursor.execute("SELECT COALESCE(MAX(Order_id), 0) AS m FROM Orders")
            new_order_id = cursor.fetchone()["m"] + 1

            # --- Next OrderDetails_id ---
            cursor.execute(
                "SELECT COALESCE(MAX(OrderDetails_id), 0) AS m FROM OrderDetails"
            )
            next_detail_id = cursor.fetchone()["m"] + 1

            # --- Default employee (first one) so customer doesn't pick one ---
            cursor.execute(
                "SELECT Employee_id FROM Employee ORDER BY Employee_id LIMIT 1"
            )
            emp_row = cursor.fetchone()
            default_employee_id = emp_row["Employee_id"] if emp_row else None

            order_total = 0.0
            detail_rows = []
            for pid, qty in lines:
                cursor.execute(
                    "SELECT Product_id, Product_Name, UnitPrice "
                    "FROM Products WHERE Product_id = %s",
                    (pid,),
                )
                prod = cursor.fetchone()
                if not prod:
                    raise ValueError(f"Product {pid} does not exist.")
                unit_price = float(prod["UnitPrice"])
                subtotal = round(unit_price * qty, 2)
                order_total += subtotal
                detail_rows.append(
                    {
                        "product_id": pid,
                        "product_name": prod["Product_Name"],
                        "quantity": qty,
                        "unit_price": unit_price,
                        "subtotal": subtotal,
                    }
                )
                next_detail_id += 1

            order_total = round(order_total, 2)

            # Insert the order (Employee_id may be NULL if no employees exist).
            cursor.execute(
                """
                INSERT INTO Orders
                    (Order_id, Customer_id, Employee_id, OrderDate, TotalAmount)
                VALUES (%s, %s, %s, NOW(), %s)
                """,
                (new_order_id, customer["Customer_id"], default_employee_id, order_total),
            )

            for det in detail_rows:
                cursor.execute(
                    """
                    INSERT INTO OrderDetails
                        (OrderDetails_id, Order_id, Product_id, Quantity,
                         UnitPrice, SubTotal)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        next_detail_id - 1
                        if next_detail_id - 1 >= 0
                        else next_detail_id,
                        new_order_id,
                        det["product_id"],
                        det["quantity"],
                        det["unit_price"],
                        det["subtotal"],
                    ),
                )
                next_detail_id += 1

            db.commit()

            # Fetch the order date for the receipt.
            cursor.execute(
                "SELECT OrderDate FROM Orders WHERE Order_id = %s",
                (new_order_id,),
            )
            order_date_row = cursor.fetchone()
            order_date = order_date_row["OrderDate"] if order_date_row else None

            cursor.close()
            db.close()

            # Render a printable POS receipt that auto-opens the print dialog.
            return render_template(
                "receipt.html",
                username=session.get("username"),
                customer=customer,
                order_id=new_order_id,
                order_date=order_date,
                lines=detail_rows,
                total=order_total,
            )

        except Exception as e:
            db.rollback()
            cursor.close()
            db.close()
            flash(f"Error placing order: {e}", "error")
            return render_template(
                "customer_order.html",
                products=products,
                customer=customer,
                username=session.get("username"),
            )

    cursor.close()
    db.close()

    return render_template(
        "customer_order.html",
        products=products,
        customer=customer,
        username=session.get("username"),
    )


@app.route("/logout")
def logout():
    """Log the current user out and return to the login page."""
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    """
    Main dashboard.

    Shows summary cards:
        - Total number of tables in the database
        - Total number of records across all tables
        - Recent activities (latest 5 records added to any table)

    Also lists buttons to open each table's management view.
    """
    tables = database.get_table_list()

    # ---- Gather record counts for every table ----
    db = database.get_db()
    cursor = db.cursor(dictionary=True)

    record_counts = {}
    total_records = 0
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) AS cnt FROM `{table}`")
            count = cursor.fetchone()["cnt"]
            record_counts[table] = count
            total_records += count
        except Exception:
            record_counts[table] = 0

    # ---- Determine the table with the most records ----
    table_with_most = max(record_counts, key=record_counts.get) if tables else None

    # ---- Recent activity: last 5 records from each table, with timestamp ----
    # MySQL does not store created_at for existing tables, so we show the
    # latest rows using the primary key as a proxy for "most recent".
    recent_activities = []
    for table in tables:
        schema = models.get_schema(table)
        if not schema:
            continue
        pk = schema["pk"]
        try:
            cursor.execute(
                f"SELECT * FROM `{table}` ORDER BY `{pk}` DESC LIMIT 3"
            )
            rows = cursor.fetchall()
            for row in rows:
                primary_value = row.get(pk, "")
                label = "".join(
                    [f"{k}={v}; " for k, v in list(row.items())[:2]]
                )
                recent_activities.append(
                    {
                        "table": table,
                        "record": label,
                        "pk": pk,
                        "pk_value": primary_value,
                    }
                )
        except Exception:
            continue

    # Keep only the newest 8 activities across all tables.
    recent_activities = recent_activities[:8]

    cursor.close()
    db.close()

    return render_template(
        "dashboard.html",
        tables=tables,
        record_counts=record_counts,
        total_records=total_records,
        total_tables=len(tables),
        table_with_most=table_with_most,
        recent_activities=recent_activities,
        username=session.get("username"),
    )


# ---------------------------------------------------------------------------
# View records in a table (Read) with search and pagination
# ---------------------------------------------------------------------------
@app.route("/table/<table_name>")
@login_required
def view_table(table_name):
    """
    Show all records of one table.

    Supports:
        - Searching (with ?q= search text)
        - Pagination (with ?page= page number, PAGE_SIZE rows per page)
    """
    schema = models.get_schema(table_name)
    db = database.get_db()
    cursor = db.cursor(dictionary=True)

    # If the table is not pre-configured, build its schema from the database.
    if schema is None:
        schema = models.get_schema_from_db(table_name, cursor)
    if schema is None:
        cursor.close()
        db.close()
        abort(404)  # Table does not exist -> not found

    columns = schema["columns"]
    pk = schema["pk"]
    fks = schema["fks"]

    # Read query parameters
    search_query = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1

    # ---- Build the WHERE clause for searching ----
    # We search text columns using LIKE. Numeric columns are compared
    # as-is so the database handles them naturally.
    where = ""
    params = []
    if search_query:
        like_clauses = []
        for col in columns:
            like_clauses.append(f"`{col}` LIKE %s")
            params.append(f"%{search_query}%")
        where = "WHERE " + " OR ".join(like_clauses)

    # ---- Get total matching rows (for pagination) ----
    cursor.execute(
        f"SELECT COUNT(*) AS total FROM `{table_name}` {where}", params
    )
    total_rows = cursor.fetchone()["total"]
    total_pages = max(1, math.ceil(total_rows / PAGE_SIZE))
    if page > total_pages:
        page = total_pages

    offset = (page - 1) * PAGE_SIZE

    # ---- Fetch records for the current page ----
    cursor.execute(
        f"""
        SELECT * FROM `{table_name}`
        {where}
        ORDER BY `{pk}` DESC
        LIMIT %s OFFSET %s
        """,
        params + [PAGE_SIZE, offset],
    )
    rows = cursor.fetchall()

    # ---- Build label maps for foreign keys (dropdown display) ----
    # e.g. for Products.Supplier_id -> map supplier_id -> "Nestle Ghana Ltd"
    fk_labels = {}
    for fk_col, ref_table in fks.items():
        ref_schema = models.get_schema(ref_table)
        if not ref_schema:
            continue
        ref_pk = ref_schema["pk"]
        ref_label_col = ref_schema["columns"][1]  # usually name/description
        try:
            cursor.execute(
                f"SELECT `{ref_pk}`, `{ref_label_col}` FROM `{ref_table}`"
            )
            fk_labels[fk_col] = {
                row[ref_pk]: row[ref_label_col] for row in cursor.fetchall()
            }
        except Exception:
            fk_labels[fk_col] = {}

    cursor.close()
    db.close()

    return render_template(
        "tables.html",
        table_name=table_name,
        columns=columns,
        rows=rows,
        pk=pk,
        fks=fks,
        fk_labels=fk_labels,
        search_query=search_query,
        page=page,
        total_pages=total_pages,
        total_rows=total_rows,
        page_size=PAGE_SIZE,
        username=session.get("username"),
    )


# ---------------------------------------------------------------------------
# Add a new record (Create / INSERT)
# ---------------------------------------------------------------------------
@app.route("/table/<table_name>/add", methods=["GET", "POST"])
@login_required
def add_record(table_name):
    """
    Add a new record to a table.

    GET  -> show an empty form built from the table schema.
    POST -> validate + INSERT the record, then redirect to the table view.
    """
    schema = models.get_schema(table_name)
    db = database.get_db()
    cursor = db.cursor(dictionary=True)

    # If the table is not pre-configured, build its schema from the database.
    if schema is None:
        schema = models.get_schema_from_db(table_name, cursor)
    if schema is None:
        cursor.close()
        db.close()
        abort(404)

    columns = schema["columns"]
    pk = schema["pk"]
    fks = schema["fks"]
    types = schema["types"]

    # Build dropdown options for foreign key fields.
    fk_options = {}
    for fk_col, ref_table in fks.items():
        ref_schema = models.get_schema(ref_table)
        if not ref_schema:
            continue
        ref_pk = ref_schema["pk"]
        ref_label = ref_schema["columns"][1]
        cursor.execute(
            f"SELECT `{ref_pk}`, `{ref_label}` FROM `{ref_table}` ORDER BY `{ref_label}`"
        )
        fk_options[fk_col] = cursor.fetchall()

    if request.method == "POST":
        # Collect the submitted values for every column except the primary key
        # (primary keys in MySQL INT columns are usually auto-generated by the
        # schema, but here we allow entering the id manually to match the SQL).
        form_values = {}
        missing = []
        for col in columns:
            value = request.form.get(col, "").strip()
            if value == "":
                missing.append(col)
            else:
                form_values[col] = value

        if missing:
            cursor.close()
            db.close()
            flash(f"Missing required field(s): {', '.join(missing)}", "error")
            return render_template(
                "add_record.html",
                table_name=table_name,
                columns=columns,
                pk=pk,
                fks=fks,
                fk_options=fk_options,
                types=types,
                form_values=request.form,
            )

        # Build and execute the INSERT query safely (parameterized).
        col_list = ", ".join([f"`{c}`" for c in columns])
        placeholders = ", ".join(["%s"] * len(columns))
        values = [form_values[c] for c in columns]

        sql = f"INSERT INTO `{table_name}` ({col_list}) VALUES ({placeholders})"
        try:
            cursor.execute(sql, values)
            db.commit()
            flash(f"Record added to {table_name} successfully!", "success")
        except Exception as e:
            db.rollback()
            flash(f"Error adding record: {e}", "error")
        finally:
            cursor.close()
            db.close()

        return redirect(url_for("view_table", table_name=table_name))

    cursor.close()
    db.close()

    return render_template(
        "add_record.html",
        table_name=table_name,
        columns=columns,
        pk=pk,
        fks=fks,
        fk_options=fk_options,
        types=types,
        form_values={},
    )


# ---------------------------------------------------------------------------
# Edit an existing record (Update / UPDATE)
# ---------------------------------------------------------------------------
@app.route("/table/<table_name>/edit/<int:record_id>", methods=["GET", "POST"])
@login_required
def edit_record(table_name, record_id):
    """
    Edit an existing record.

    GET  -> load the current values into the form.
    POST -> UPDATE the record with the submitted values.
    """
    schema = models.get_schema(table_name)
    db = database.get_db()
    cursor = db.cursor(dictionary=True)

    # If the table is not pre-configured, build its schema from the database.
    if schema is None:
        schema = models.get_schema_from_db(table_name, cursor)
    if schema is None:
        cursor.close()
        db.close()
        abort(404)

    columns = schema["columns"]
    pk = schema["pk"]
    fks = schema["fks"]
    types = schema["types"]

    # Load the existing record.
    cursor.execute(
        f"SELECT * FROM `{table_name}` WHERE `{pk}` = %s", (record_id,)
    )
    record = cursor.fetchone()
    if not record:
        cursor.close()
        db.close()
        flash("Record not found.", "error")
        return redirect(url_for("view_table", table_name=table_name))

    # Build dropdown options for foreign key fields.
    fk_options = {}
    for fk_col, ref_table in fks.items():
        ref_schema = models.get_schema(ref_table)
        if not ref_schema:
            continue
        ref_pk = ref_schema["pk"]
        ref_label = ref_schema["columns"][1]
        cursor.execute(
            f"SELECT `{ref_pk}`, `{ref_label}` FROM `{ref_table}` ORDER BY `{ref_label}`"
        )
        fk_options[fk_col] = cursor.fetchall()

    if request.method == "POST":
        # Collect submitted values (all columns except the primary key).
        update_values = []
        set_clauses = []
        for col in columns:
            if col == pk:
                continue
            value = request.form.get(col, "").strip()
            set_clauses.append(f"`{col}` = %s")
            update_values.append(value)

        update_values.append(record_id)

        sql = (
            f"UPDATE `{table_name}` SET {', '.join(set_clauses)} "
            f"WHERE `{pk}` = %s"
        )
        try:
            cursor.execute(sql, update_values)
            db.commit()
            flash(f"Record {pk}={record_id} updated successfully!", "success")
        except Exception as e:
            db.rollback()
            flash(f"Error updating record: {e}", "error")
        finally:
            cursor.close()
            db.close()

        return redirect(url_for("view_table", table_name=table_name))

    cursor.close()
    db.close()

    return render_template(
        "edit_record.html",
        table_name=table_name,
        columns=columns,
        pk=pk,
        fks=fks,
        fk_options=fk_options,
        types=types,
        record=record,
        record_id=record_id,
    )


# ---------------------------------------------------------------------------
# Place an order for a brand-new customer
# ---------------------------------------------------------------------------
@app.route("/place_order", methods=["GET", "POST"])
@login_required
def place_order():
    """
    Customer order placement page.

    GET  -> show a form where a brand-new customer can be entered along with
            an employee, order date, and a cart of products + quantities.
    POST -> In a single transaction:
                1. Insert the new customer into Customer_information.
                2. Insert the order into Orders (with computed TotalAmount).
                3. Insert each cart line into OrderDetails.
            Auto-generates Customer_id, Order_id, and OrderDetails_id because
            those primary keys are NOT auto-increment in the table schema.
    """
    db = database.get_db()
    cursor = db.cursor(dictionary=True)

    # ---- Load employees for the dropdown ----
    cursor.execute(
        "SELECT Employee_id, First_Name, Last_Name FROM Employee ORDER BY First_Name"
    )
    employees = cursor.fetchall()

    # ---- Load products for the cart ----
    cursor.execute(
        "SELECT Product_id, Product_Name, UnitPrice, StockQuantity "
        "FROM Products ORDER BY Product_Name"
    )
    products = cursor.fetchall()

    if request.method == "POST":
        # --- New customer details ---
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        employee_id = request.form.get("employee_id", "").strip()
        order_date = request.form.get("order_date", "").strip() or None

        # --- Cart items (parallel lists) ---
        product_ids = request.form.getlist("product_id[]")
        quantities = request.form.getlist("quantity[]")

        # Validate basic required fields.
        errors = []
        if not first_name or not last_name:
            errors.append("Customer first and last name are required.")
        if not employee_id:
            errors.append("Please select an employee.")
        if not product_ids:
            errors.append("Please add at least one product to the order.")

        # Build the list of order lines (product_id + quantity).
        lines = []
        if not errors:
            for pid, qty in zip(product_ids, quantities):
                if not pid:
                    continue
                try:
                    q = int(qty or 0)
                except ValueError:
                    q = 0
                if q > 0:
                    lines.append((int(pid), q))

        if not lines:
            errors.append("Please add at least one product with a valid quantity.")

        if errors:
            cursor.close()
            db.close()
            for e in errors:
                flash(e, "error")
            return render_template(
                "place_order.html",
                employees=employees,
                products=products,
                form_values=request.form,
                username=session.get("username"),
            )

        try:
            # --- Next Customer_id ---
            cursor.execute("SELECT COALESCE(MAX(Customer_id), 0) AS m FROM Customer_information")
            new_customer_id = cursor.fetchone()["m"] + 1

            # --- Next Order_id ---
            cursor.execute("SELECT COALESCE(MAX(Order_id), 0) AS m FROM Orders")
            new_order_id = cursor.fetchone()["m"] + 1

            # --- Next OrderDetails_id ---
            cursor.execute(
                "SELECT COALESCE(MAX(OrderDetails_id), 0) AS m FROM OrderDetails"
            )
            next_detail_id = cursor.fetchone()["m"] + 1

            # 1. Insert the new customer.
            cursor.execute(
                """
                INSERT INTO Customer_information
                    (Customer_id, First_Name, Last_Name, Phone, Email, Address)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (new_customer_id, first_name, last_name, phone, email, address),
            )

            # 2. Compute subtotals for each line and the order total.
            order_total = 0.0
            detail_rows = []
            for pid, qty in lines:
                # Fetch the product's unit price.
                cursor.execute(
                    "SELECT Product_id, UnitPrice FROM Products WHERE Product_id = %s",
                    (pid,),
                )
                prod = cursor.fetchone()
                if not prod:
                    raise ValueError(f"Product {pid} does not exist.")
                unit_price = float(prod["UnitPrice"])
                subtotal = round(unit_price * qty, 2)
                order_total += subtotal
                detail_rows.append((next_detail_id, pid, qty, unit_price, subtotal))
                next_detail_id += 1

            order_total = round(order_total, 2)

            # 3. Insert the order.
            cursor.execute(
                """
                INSERT INTO Orders
                    (Order_id, Customer_id, Employee_id, OrderDate, TotalAmount)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (new_order_id, new_customer_id, employee_id, order_date, order_total),
            )

            # 4. Insert each order detail line.
            for detail_id, pid, qty, unit_price, subtotal in detail_rows:
                cursor.execute(
                    """
                    INSERT INTO OrderDetails
                        (OrderDetails_id, Order_id, Product_id, Quantity,
                         UnitPrice, SubTotal)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (detail_id, new_order_id, pid, qty, unit_price, subtotal),
                )

            db.commit()
            cursor.close()
            db.close()

            flash(
                f"Order #{new_order_id} placed successfully for {first_name} "
                f"{last_name}! Total: GHS {order_total:.2f}",
                "success",
            )
            return redirect(url_for("dashboard"))

        except Exception as e:
            db.rollback()
            cursor.close()
            db.close()
            flash(f"Error placing order: {e}", "error")
            return render_template(
                "place_order.html",
                employees=employees,
                products=products,
                form_values=request.form,
                username=session.get("username"),
            )

    cursor.close()
    db.close()

    return render_template(
        "place_order.html",
        employees=employees,
        products=products,
        form_values={},
        username=session.get("username"),
    )


# ---------------------------------------------------------------------------
# Delete a record (Delete / DELETE) with confirmation
# ---------------------------------------------------------------------------
@app.route("/table/<table_name>/delete/<int:record_id>", methods=["POST"])
@login_required
def delete_record(table_name, record_id):
    """
    Delete a record.

    The tables.html page shows a JavaScript confirmation dialog before this
    route is hit, so accidental deletions are prevented.
    """
    schema = models.get_schema(table_name)
    db = database.get_db()
    cursor = db.cursor(dictionary=True)

    # If the table is not pre-configured, build its schema from the database.
    if schema is None:
        schema = models.get_schema_from_db(table_name, cursor)
    if schema is None:
        cursor.close()
        db.close()
        abort(404)

    pk = schema["pk"]

    try:
        cursor.execute(
            f"DELETE FROM `{table_name}` WHERE `{pk}` = %s", (record_id,)
        )
        db.commit()
        flash(f"Record {pk}={record_id} deleted from {table_name}.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error deleting record: {e}", "error")
    finally:
        cursor.close()
        db.close()

    return redirect(url_for("view_table", table_name=table_name))


# ---------------------------------------------------------------------------
# Start the app
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Prepare the database (create the login users table).
    database.init_database()
    # Run the development server with debug mode.
    app.run(debug=True, port=5000)

