"""
database.py

This module handles all MySQL database connections and setup for the app.

It connects to an EXISTING MySQL database (Addo_Mart_db) - it does NOT
create a new one. It also makes sure a "login" table exists so users can
authenticate to use the GUI.

Adjust the DB_CONFIG dictionary below to match your own MySQL setup.
"""

import mysql.connector

# ---------------------------------------------------------------------------
# DATABASE CONNECTION CONFIGURATION
# Change these values to match your local MySQL server.
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "host": "",          # Your MySQL host (usually localhost)
    "user": "",               # Your MySQL username
    "password": "",       # Your MySQL password
    "database": "",   # The EXISTING database to manage
}


def get_db():
    """
    Create and return a new MySQL connection.

    Returns a mysql.connector.connection object that the caller must close.
    Each request creates a fresh connection so we avoid threading issues.
    """
    return mysql.connector.connect(**DB_CONFIG)


def init_database():
    """
    Prepare the database for the GUI.

    1. Make sure the 'login' users table exists (for authentication).
    2. Make sure the 'role' column exists (admin / customer).
    3. Ensure the Customer_information table has a 'login_id' column used to
       link a customer account to their customer record.
    4. Insert a default admin user (admin / admin123) the first time.

    This function is called once when the Flask app starts.
    """
    db = get_db()
    cursor = db.cursor()

    # Create the login table if it does not already exist.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS login (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'customer'
        )
        """
    )

    # Add the 'role' column if it does not exist (for existing databases).
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'login'
          AND COLUMN_NAME = 'role'
        """
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "ALTER TABLE login ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'customer'"
        )

    # Ensure Customer_information has a login_id column to link accounts.
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'Customer_information'
          AND COLUMN_NAME = 'login_id'
        """
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "ALTER TABLE Customer_information ADD COLUMN login_id INT NULL"
        )

    # Ensure the default admin user exists with the 'admin' role.
    # This handles both a fresh database and one where the admin row was
    # created before the role column existed (which would default to 'customer').
    cursor.execute(
        """
        INSERT INTO login (username, password, role)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE role = 'admin'
        """,
        ("admin", "admin123", "admin"),
    )
    print("Default admin ensured -> username: admin, password: admin123, role: admin")

    db.commit()
    cursor.close()
    db.close()


def get_table_list():
    """
    Return a list of all table names in the connected database.

    This uses information_schema to fetch the real tables present in the
    existing database (excluding the 'login' table used by the app itself).
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT TABLE_NAME
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME != 'login'
        ORDER BY TABLE_NAME
        """,
        (DB_CONFIG["database"],),
    )
    tables = [row["TABLE_NAME"] for row in cursor.fetchall()]
    cursor.close()
    db.close()
    return tables
