"""
models.py

This module defines the schema (structure) of every table the GUI manages.

Keeping all table definitions in one place makes the app very easy to
extend: to add support for a NEW table, just add one new dictionary entry
below. No other code needs to change.

Each table entry has:
    - 'columns' : ordered list of column names (as they appear in MySQL)
    - 'pk'      : the primary key column name
    - 'fks'     : dictionary of { foreign_key_column: referenced_table }
                  used to build dropdowns for related data
    - 'types'   : dictionary of { column: html_input_type } so the form
                  renders appropriate input widgets (number, date, text)
"""

TABLE_SCHEMAS = {

"Customer_information": {
        "columns": ["Customer_id", "First_Name", "Last_Name", "Phone", "Email", "Address", "login_id"],
        "pk": "Customer_id",
        "fks": {},
        "types": {
            "Customer_id": "number",
            "First_Name": "text",
            "Last_Name": "text",
            "Phone": "text",
            "Email": "email",
            "Address": "text",
            "login_id": "text",
        },
    },

    "Employee": {
        "columns": ["Employee_id", "First_Name", "Last_Name", "Position", "Phone", "Salary"],
        "pk": "Employee_id",
        "fks": {},
        "types": {
            "Employee_id": "number",
            "First_Name": "text",
            "Last_Name": "text",
            "Position": "text",
            "Phone": "text",
            "Salary": "number",
        },
    },

    "Suppliers": {
        "columns": ["Supplier_id", "Supplier_Name", "Phone", "Email", "Address"],
        "pk": "Supplier_id",
        "fks": {},
        "types": {
            "Supplier_id": "number",
            "Supplier_Name": "text",
            "Phone": "text",
            "Email": "email",
            "Address": "text",
        },
    },

    "Products": {
        "columns": ["Product_id", "Product_Name", "Category", "UnitPrice", "StockQuantity", "Supplier_id"],
        "pk": "Product_id",
        "fks": {"Supplier_id": "Suppliers"},
        "types": {
            "Product_id": "number",
            "Product_Name": "text",
            "Category": "text",
            "UnitPrice": "number",
            "StockQuantity": "number",
            "Supplier_id": "number",
        },
    },

    "Orders": {
        "columns": ["Order_id", "Customer_id", "Employee_id", "OrderDate", "TotalAmount"],
        "pk": "Order_id",
        "fks": {"Customer_id": "Customer_information", "Employee_id": "Employee"},
        "types": {
            "Order_id": "number",
            "Customer_id": "number",
            "Employee_id": "number",
            "OrderDate": "date",
            "TotalAmount": "number",
        },
    },

    "OrderDetails": {
        "columns": ["OrderDetails_id", "Order_id", "Product_id", "Quantity", "UnitPrice", "SubTotal"],
        "pk": "OrderDetails_id",
        "fks": {"Order_id": "Orders", "Product_id": "Products"},
        "types": {
            "OrderDetails_id": "number",
            "Order_id": "number",
            "Product_id": "number",
            "Quantity": "number",
            "UnitPrice": "number",
            "SubTotal": "number",
        },
    },

}


def get_schema(table_name):
    """
    Return the schema dictionary for a given table name.
    Returns None if the table is not defined in models.py.
    """
    return TABLE_SCHEMAS.get(table_name)


def get_columns(table_name):
    """Return the ordered list of column names for a table."""
    schema = get_schema(table_name)
    return schema["columns"] if schema else []


def get_pk(table_name):
    """Return the primary key column for a table."""
    schema = get_schema(table_name)
    return schema["pk"] if schema else None


def get_fks(table_name):
    """Return the foreign key mapping for a table."""
    schema = get_schema(table_name)
    return schema["fks"] if schema else {}


def get_schema_from_db(table_name, cursor):
    """
    Build a schema dictionary dynamically by reading the REAL MySQL table
    structure from information_schema.

    This is a fallback used when a table is not defined in TABLE_SCHEMAS
    above. It allows the app to manage ANY existing table in the database,
    not just the ones pre-configured.

    Returns a dictionary shaped like the TABLE_SCHEMAS entries, or None if
    the table does not exist.
    """
    # 1. Read the columns and their data types (in order).
    cursor.execute(
        """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION
        """,
        (table_name,),
    )
    cols = cursor.fetchall()
    if not cols:
        return None

    columns = [c["COLUMN_NAME"] for c in cols]

    # Map MySQL data types to HTML input types.
    types = {}
    for c in cols:
        dt = c["DATA_TYPE"]
        if dt in ("int", "bigint", "smallint", "tinyint", "decimal", "float", "double"):
            types[c["COLUMN_NAME"]] = "number"
        elif dt in ("date", "datetime", "timestamp", "time"):
            types[c["COLUMN_NAME"]] = "date"
        else:
            types[c["COLUMN_NAME"]] = "text"

    # 2. Find the primary key column.
    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND CONSTRAINT_NAME = 'PRIMARY'
        """,
        (table_name,),
    )
    pk_row = cursor.fetchone()

    return {
        "columns": columns,
        "pk": pk_row["COLUMN_NAME"] if pk_row else columns[0],
        "fks": {},
        "types": types,
    }
