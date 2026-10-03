# Addo Mart Database Management System

A web-based **Database Management System (DBMS)** built with **Flask, Python, MySQL, HTML5, CSS3, and Jinja2**.

The application provides a web interface for managing the **Addo Mart** supermarket database, allowing authenticated users to perform CRUD operations, search and filter records, manage relational data, and interact with multiple MySQL tables through a responsive interface.

> **Project Type:** Database Management / Flask Web Application
> **Database:** MySQL
> **Backend:** Python + Flask
> **Frontend:** HTML5 + CSS3 + Jinja2

---

## Features

### Authentication

* User login system backed by MySQL.
* Session-based authentication.
* Protected application routes.
* Logout functionality.

### Dashboard

The dashboard provides an overview of the database, including:

* Number of database tables
* Total number of records
* Largest table
* Database connection status
* Recent activity
* Quick access to database tables

### Database Management

Users can manage records across the application's database tables through the web interface.

Supported operations include:

* **Create** — Add new records
* **Read** — View existing records
* **Update** — Edit records
* **Delete** — Remove records
* **Search** — Find records using search and filtering functionality
* **Pagination** — Display records in manageable pages

### Relational Database Support

The application supports relationships between tables through foreign keys.

Related records can be displayed using meaningful values rather than only raw foreign-key IDs.

### User Interface

* Custom HTML and CSS
* Responsive layouts
* No Bootstrap or external CSS framework
* Jinja2 templates
* Clean database-management interface

---

## Technologies Used

| Technology                 | Purpose                     |
| -------------------------- | --------------------------- |
| **Python**                 | Application programming     |
| **Flask**                  | Web framework               |
| **MySQL**                  | Relational database         |
| **mysql-connector-python** | MySQL database connectivity |
| **HTML5**                  | Frontend structure          |
| **CSS3**                   | Frontend styling            |
| **Jinja2**                 | Server-side templating      |

---

## Database Structure

The Addo Mart database contains the following main tables:

| Table                  | Primary Key       | Purpose                       |
| ---------------------- | ----------------- | ----------------------------- |
| `Customer_information` | `Customer_id`     | Stores customer information   |
| `Employee`             | `Employee_id`     | Stores employee information   |
| `Suppliers`            | `Supplier_id`     | Stores supplier information   |
| `Products`             | `Product_id`      | Stores product information    |
| `Orders`               | `Order_id`        | Stores customer orders        |
| `OrderDetails`         | `OrderDetails_id` | Stores individual order items |

### Relationships

```text
Suppliers
    |
    └── Products
          |
          └── OrderDetails
                    |
                    └── Orders
                          |
                          └── Customer_information
```

The database uses primary keys and foreign keys to maintain relationships between related records.

---

## Project Structure

```text
Database-Management/
|
├── app.py
├── database.py
├── models.py
├── requirements.txt
├── README.md
|
├── static/
|   └── style.css
|
└── templates/
    ├── login.html
    ├── dashboard.html
    ├── tables.html
    ├── add_record.html
    └── edit_record.html
```

`__pycache__/` and other generated Python files are excluded from version control.

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/AddoRichmond-GH/Database-Management.git
```

Navigate into the project:

```bash
cd Database-Management
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure MySQL

Create or import the `Addo_Mart_db` database into your local MySQL server.

Configure the database connection in `database.py` using your own local MySQL credentials.

Do not commit real passwords, API keys, or other sensitive credentials to GitHub.

### 5. Start the Application

```bash
python app.py
```

The application should start on:

```text
http://127.0.0.1:5000
```

Open that address in your browser.

---

## Security Considerations

The application includes several security-conscious practices:

* Parameterized SQL queries are used for database operations.
* Authentication is required before accessing protected routes.
* Database credentials are kept out of the public repository.
* A Flask secret key is used for session management.

### Current Limitations

This is primarily a learning and demonstration project, so additional security improvements would be required before production deployment.

Examples include:

* Hashing user passwords using `werkzeug.security` or `bcrypt`
* Using environment variables for secrets
* Implementing stronger password policies
* Adding CSRF protection
* Improving session security
* Adding role-based access control
* Applying additional input validation
* Using a production-grade deployment configuration

---

## Application Architecture

### `app.py`

The main Flask application.

Responsible for:

* Routing
* Authentication flow
* Dashboard
* CRUD operations
* Search and pagination
* Form processing
* Session handling

### `database.py`

Responsible for database connectivity and database initialization.

Main responsibilities include:

* MySQL connection configuration
* Creating database connections
* Initializing authentication-related database structures
* Retrieving database table information

### `models.py`

Contains the application's table schema definitions.

This provides a centralized location for:

* Column definitions
* Primary keys
* Foreign keys
* Input types
* Table relationships

### `templates/`

Contains the Jinja2 HTML templates used by the Flask application.

### `static/style.css`

Contains the application's custom CSS styling.

---

## CRUD Operations

The application implements the four fundamental database operations:

| Operation  | Description                  |
| ---------- | ---------------------------- |
| **Create** | Add new database records     |
| **Read**   | Retrieve and display records |
| **Update** | Modify existing records      |
| **Delete** | Remove records               |

Example routes include:

```text
GET/POST /                       → Login
GET      /logout                 → Logout
GET      /dashboard              → Dashboard
GET      /table/<table>          → View records
GET/POST /table/<table>/add      → Add record
GET/POST /table/<table>/edit/... → Edit record
POST     /table/<table>/delete   → Delete record
```

---

## What I Learned

This project provided practical experience with:

* Relational database design
* MySQL
* SQL queries
* Primary and foreign keys
* CRUD operations
* Python
* Flask
* Jinja2
* HTML and CSS
* Database connectivity
* Authentication
* Web application structure
* Parameterized SQL queries
* Git and GitHub

---

## Future Improvements

Potential improvements for future versions include:

* Password hashing
* Role-based user permissions
* Database analytics and charts
* Advanced filtering
* CSV/Excel export
* Improved mobile responsiveness
* CSRF protection
* Cloud deployment
* Automated testing
* Audit logs

---

## Author

**Richmond Addo**

Cybersecurity Student | Python Developer | Database and Web Application Enthusiast

GitHub: [AddoRichmond-GH](https://github.com/AddoRichmond-GH)

---

## License

This project was created for educational and demonstration purposes.
