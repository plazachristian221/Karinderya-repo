import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from openpyxl import Workbook
from openpyxl.styles import Font
from io import BytesIO
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, render_template, redirect, url_for, session, send_file, abort
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "karinderya.db"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_default_secret_key")

# =========================================================
# FLASK CONFIGURATION
# =========================================================

# =========================================================
# RAILWAY DEPLOYMENT CHECK
# =========================================================
@app.route("/railway-check", methods=["GET"])
def railway_check():
    return "RAILWAY IS RUNNING MY CURRENT APP.PY", 200

# =========================================================
# TEST ROUTE
# =========================================================
@app.route("/test", methods=["GET"])
def test():
    return "TEST ROUTE IS WORKING", 200

# =========================================================
# HEALTH CHECK
# =========================================================
@app.route("/health", methods=["GET"])
def health():
    return "OK", 200


def get_db():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("Warning: DATABASE_URL is not set. Falling back to SQLite for development.")
        return sqlite3.connect(DATABASE)

    try:
        conn = psycopg2.connect(database_url)
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL: {e}")
        raise

# Helper function to get columns for SQLite compatibility
def _table_columns(db_conn, table_name):
    if isinstance(db_conn, sqlite3.Connection):
        cursor = db_conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        return set(columns)
    else:
        cursor = db_conn.cursor()
        cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'")
        columns = [row[0] for row in cursor.fetchall()]
        return set(columns)


# =========================================================
# INITIALIZE DATABASE & ADMIN ACCOUNT
# =========================================================
def init_db():
    conn = get_db()
    try:
        # 1. CREATE TABLES
        if isinstance(conn, sqlite3.Connection):
             cursor = conn.cursor()
             cursor.execute("""
                 CREATE TABLE IF NOT EXISTS users (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     username TEXT UNIQUE NOT NULL,
                     password TEXT NOT NULL,
                     created_at TEXT NOT NULL
                 )
             """)
             cursor.execute("""
                 CREATE TABLE IF NOT EXISTS orders (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     username TEXT NOT NULL,
                     restaurant_id INTEGER NOT NULL,
                     restaurant_name TEXT NOT NULL,
                     food TEXT NOT NULL,
                     price REAL NOT NULL,
                     payment_method TEXT NOT NULL,
                     payment_status TEXT NOT NULL,
                     order_status TEXT NOT NULL,
                     created_at TEXT NOT NULL
                 )
             """)
             cursor.execute("""
                 CREATE TABLE IF NOT EXISTS menu_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    price REAL NOT NULL,
                    available INTEGER DEFAULT 1
                 )
             """)
             conn.commit()

        else:
             with conn.cursor() as cursor:
                 cursor.execute("""
                     CREATE TABLE IF NOT EXISTS users (
                         id SERIAL PRIMARY KEY,
                         username TEXT UNIQUE NOT NULL,
                         password TEXT NOT NULL,
                         created_at TEXT NOT NULL
                     )
                 """)
                 cursor.execute("""
                     CREATE TABLE IF NOT EXISTS orders (
                         id SERIAL PRIMARY KEY,
                         username TEXT NOT NULL,
                         restaurant_id INTEGER NOT NULL,
                         restaurant_name TEXT NOT NULL,
                         food TEXT NOT NULL,
                         price REAL NOT NULL,
                         payment_method TEXT NOT NULL,
                         payment_status TEXT NOT NULL,
                         order_status TEXT NOT NULL,
                         created_at TEXT NOT NULL
                     )
                 """)
                 cursor.execute("""
                     CREATE TABLE IF NOT EXISTS menu_items (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        price REAL NOT NULL,
                        available INTEGER DEFAULT 1
                     )
                 """)
                 conn.commit()

        # 2. SEED ADMIN ACCOUNT
        admin_username = "admin"
        admin_password = generate_password_hash("admin123")
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if isinstance(conn, sqlite3.Connection):
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (admin_username,))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO users (username, password, created_at)
                    VALUES (?, ?, ?)
                """, (admin_username, admin_password, created_at))
                conn.commit()
        else:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE username = %s", (admin_username,))
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO users (username, password, created_at)
                        VALUES (%s, %s, %s)
                    """, (admin_username, admin_password, created_at))
                    conn.commit()

    finally:
        conn.close()


# =========================================================
# KARINDERYAS
# =========================================================
restaurants = {
    1: {"name": "Karinderya Ni Maria", "address": "Quezon City", "lat": 14.6760, "lng": 121.0437},
    2: {"name": "Lutong Bahay Express", "address": "Quezon City", "lat": 14.6800, "lng": 121.0500},
    3: {"name": "Nanay's Karinderya", "address": "Quezon City", "lat": 14.6700, "lng": 121.0400},
    4: {"name": "Ate's Carinderia", "address": "Quezon City", "lat": 14.6900, "lng": 121.0550}
}

# =========================================================
# MENUS
# =========================================================
menus = {
    1: [
        {"name": "Chicken Adobo", "price": 75},
        {"name": "Pork Sinigang", "price": 85},
        {"name": "Fried Bangus", "price": 90},
        {"name": "Pancit Canton", "price": 65}
    ],
    2: [
        {"name": "Beef Tapa", "price": 85},
        {"name": "Chicken Inasal", "price": 90},
        {"name": "Pork BBQ", "price": 75},
        {"name": "Ginisang Gulay", "price": 55}
    ],
    3: [
        {"name": "Pork Adobo", "price": 75},
        {"name": "Tinolang Manok", "price": 80},
        {"name": "Fried Tilapia", "price": 70},
        {"name": "Lumpiang Shanghai", "price": 60}
    ],
    4: [
        {"name": "Sisig", "price": 80},
        {"name": "Chicken Curry", "price": 85},
        {"name": "Pork Chop", "price": 90},
        {"name": "Mongo with Chicharon", "price": 65}
    ]
}


# =========================================================
# HOME
# =========================================================
@app.route("/")
def home():
    conn = get_db()
    featured = []
    try:
        if isinstance(conn, sqlite3.Connection):
             conn.row_factory = sqlite3.Row
             cursor = conn.cursor()
             featured = cursor.execute("""
                 SELECT * FROM menu_items WHERE available = 1 ORDER BY id DESC LIMIT 3
             """).fetchall()
        else:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM menu_items WHERE available = 1 ORDER BY id DESC LIMIT 3
                """)
                featured = cursor.fetchall()
    except Exception as e:
        print(f"Error fetching featured items: {e}")
    finally:
        conn.close()

    return render_template("index.html", featured=featured)


# =========================================================
# REGISTER
# =========================================================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not password or not confirm_password:
            return render_template("register.html", error="All fields are required.")

        if len(username) < 3:
            return render_template("register.html", error="Username must be at least 3 characters.")

        if len(password) < 6:
            return render_template("register.html", error="Password must be at least 6 characters.")

        if password != confirm_password:
            return render_template("register.html", error="Passwords do not match.")

        conn = get_db()
        try:
            if isinstance(conn, sqlite3.Connection):
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                existing_user = cursor.fetchone()
            else:
                 with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                    existing_user = cursor.fetchone()

            if existing_user:
                return render_template("register.html", error="Username already exists. Please choose another.")

            hashed_password = generate_password_hash(password)
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if isinstance(conn, sqlite3.Connection):
                cursor.execute("""
                    INSERT INTO users (username, password, created_at)
                    VALUES (?, ?, ?)
                """, (username, hashed_password, created_at))
            else:
                 with conn.cursor() as cursor:
                     cursor.execute("""
                         INSERT INTO users (username, password, created_at)
                         VALUES (%s, %s, %s)
                     """, (username, hashed_password, created_at))
            
            conn.commit()
            
            session["username"] = username
            return redirect(url_for("nearby"))

        finally:
            conn.close()

    return render_template("register.html")

# =========================================================
# LOGIN
# =========================================================
@app.route("/login", methods=["GET", "POST"])
def login():
     if request.method == "POST":
         username = request.form.get("username", "").strip()
         password = request.form.get("password", "")

         if not username or not password:
             return render_template("login.html", error="Please enter your username and password.")

         conn = get_db()
         user = None
         try:
            if isinstance(conn, sqlite3.Connection):
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                user = cursor.fetchone()
            else:
                 with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                     cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                     user = cursor.fetchone()
         finally:
             conn.close()

         if user and check_password_hash(user["password"], password):
             session["username"] = user["username"]
             
             # Redirect admin to dashboard, normal users to nearby
             if user["username"] == "admin":
                 return redirect(url_for("admin_dashboard"))
             return redirect(url_for("nearby"))

         return render_template("login.html", error="Invalid username or password.")

     return render_template("login.html")


# =========================================================
# ADMIN DASHBOARD
# =========================================================
@app.route("/admin")
def admin_dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    
    if session["username"] != "admin":
        return "Access Denied: Administrator privileges required.", 403
    
    conn = get_db()
    all_orders = []
    all_users = []
    try:
        if isinstance(conn, sqlite3.Connection):
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            all_orders = cursor.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
            all_users = cursor.execute("SELECT id, username, created_at FROM users").fetchall()
        else:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM orders ORDER BY id DESC")
                all_orders = cursor.fetchall()
                cursor.execute("SELECT id, username, created_at FROM users")
                all_users = cursor.fetchall()
    finally:
        conn.close()

    # Note: You will need to create 'admin.html' in your templates folder to render this properly.
    return render_template("admin.html", orders=all_orders, users=all_users)


# =========================================================
# NEARBY KARINDERYAS
# =========================================================
@app.route("/nearby")
def nearby():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("nearby.html", restaurants=restaurants)


# =========================================================
# RESTAURANT / KARINDERYA MENU
# =========================================================
@app.route("/restaurant/<int:restaurant_id>")
def restaurant(restaurant_id):
    if "username" not in session:
        return redirect(url_for("login"))

    restaurant_data = restaurants.get(restaurant_id)

    if restaurant_data is None:
        return "Karinderya not found.", 404

    restaurant_menu = menus.get(restaurant_id, [])

    return render_template(
        "restaurant.html",
        restaurant=restaurant_data,
        restaurant_id=restaurant_id,
        menu=restaurant_menu
    )

# =========================================================
# ORDER
# =========================================================
@app.route("/order", methods=["GET", "POST"])
def order():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        restaurant_id = request.form.get("restaurant_id")
        food = request.form.get("food")
        price = request.form.get("price")
        payment_method = request.form.get("payment_method")

        if not all([restaurant_id, food, price, payment_method]):
            return "Missing required fields.", 400

        try:
            restaurant_id = int(restaurant_id)
        except ValueError:
            return "Invalid restaurant.", 400

        restaurant_data = restaurants.get(restaurant_id)
        if restaurant_data is None:
            return "Karinderya not found.", 404

        try:
            price = float(price)
        except ValueError:
            return "Invalid price.", 400

        username = session["username"]

        if payment_method == "Cash on Pickup":
            payment_status = "Pay on Pickup"
        else:
            payment_status = "Pending"

        order_status = "Waiting"
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db()
        try:
             if isinstance(conn, sqlite3.Connection):
                  cursor = conn.cursor()
                  cursor.execute("""
                      INSERT INTO orders (
                          username, restaurant_id, restaurant_name,
                          food, price, payment_method,
                          payment_status, order_status, created_at
                      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                  """, (username, restaurant_id, restaurant_data["name"], food, price, payment_method, payment_status, order_status, created_at))
                  order_id = cursor.lastrowid
             else:
                  with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                      cursor.execute("""
                          INSERT INTO orders (
                              username, restaurant_id, restaurant_name,
                              food, price, payment_method,
                              payment_status, order_status, created_at
                          ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                          RETURNING id
                      """, (username, restaurant_id, restaurant_data["name"], food, price, payment_method, payment_status, order_status, created_at))
                      result = cursor.fetchone()
                      order_id = result["id"]
             conn.commit()
        finally:
            conn.close()

        return redirect(url_for("queue", order_id=order_id))

    restaurant_id = request.args.get("restaurant_id")
    food = request.args.get("food")
    price = request.args.get("price")

    if not restaurant_id:
        return "Restaurant is required.", 400

    try:
        restaurant_id = int(restaurant_id)
    except ValueError:
        return "Invalid restaurant.", 400

    restaurant_data = restaurants.get(restaurant_id)
    if restaurant_data is None:
        return "Karinderya not found.", 404

    return render_template(
        "order.html",
        restaurant=restaurant_data,
        restaurant_id=restaurant_id,
        food=food,
        price=price
    )


# =========================================================
# ORDER QUEUE
# =========================================================
@app.route("/queue/<int:order_id>")
def queue(order_id):
    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    customer_orders = []
    try:
         if isinstance(conn, sqlite3.Connection):
             conn.row_factory = sqlite3.Row
             cursor = conn.cursor()
             order_columns = _table_columns(conn, "orders")

             if {"user_id", "item_id"}.issubset(order_columns) and "user_id" in session:
                  customer_orders = cursor.execute("""
                      SELECT o.*, m.name AS item_name
                      FROM orders o
                      LEFT JOIN menu_items m ON m.id = o.item_id
                      WHERE o.user_id = ?
                      ORDER BY o.id DESC
                  """, (session.get("user_id"),)).fetchall()
             elif "username" in order_columns:
                  customer_orders = cursor.execute(
                      "SELECT * FROM orders WHERE username = ? ORDER BY id DESC",
                      (session["username"],)
                  ).fetchall()
             
         else:
             with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                 order_columns = _table_columns(conn, "orders")
                 
                 if "user_id" in order_columns and "item_id" in order_columns and "user_id" in session:
                     cursor.execute("""
                         SELECT o.*, m.name AS item_name
                         FROM orders o
                         LEFT JOIN menu_items m ON m.id = o.item_id
                         WHERE o.user_id = %s
                         ORDER BY o.id DESC
                     """, (session.get("user_id"),))
                     customer_orders = cursor.fetchall()
                 elif "username" in order_columns:
                      cursor.execute(
                          "SELECT * FROM orders WHERE username = %s ORDER BY id DESC",
                          (session["username"],)
                      )
                      customer_orders = cursor.fetchall()
    except Exception as e:
        app.logger.exception(f"Database error while loading orders: {e}")
        abort(500)
    finally:
        conn.close()

    return render_template("orders.html", orders=customer_orders)


# =========================================================
# MENU
# =========================================================
@app.route("/menu")
def menu():
    if "username" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("nearby"))


# =========================================================
# LOGOUT
# =========================================================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# =========================================================
# EXPORT EXCEL
# =========================================================
@app.route("/export-excel")
def export_excel():
    if "username" not in session:
        return redirect(url_for("login"))
        
    if session["username"] != "admin":
         return "Access Denied: Only administrators can export data.", 403

    conn = get_db()
    users = []
    orders_data = []
    
    try:
        if isinstance(conn, sqlite3.Connection):
             conn.row_factory = sqlite3.Row
             cursor = conn.cursor()
             users = cursor.execute("SELECT id, username, created_at FROM users ORDER BY id").fetchall()
             orders_data = cursor.execute("""
                 SELECT id, username, restaurant_id, restaurant_name,
                        food, price, payment_method, payment_status,
                        order_status, created_at
                 FROM orders ORDER BY id DESC
             """).fetchall()
        else:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT id, username, created_at FROM users ORDER BY id")
                users = cursor.fetchall()

                cursor.execute("""
                    SELECT id, username, restaurant_id, restaurant_name,
                           food, price, payment_method, payment_status,
                           order_status, created_at
                    FROM orders ORDER BY id DESC
                """)
                orders_data = cursor.fetchall()

    finally:
        conn.close()

    workbook = Workbook()

    # Users Sheet
    users_sheet = workbook.active
    users_sheet.title = "Users"
    users_sheet.append(["ID", "Username", "Created At"])

    for user in users:
        users_sheet.append([user["id"], user["username"], user["created_at"]])

    # Orders Sheet
    orders_sheet = workbook.create_sheet("Orders")
    orders_sheet.append([
        "ID", "Username", "Restaurant ID", "Restaurant Name",
        "Food", "Price", "Payment Method", "Payment Status",
        "Order Status", "Created At"
    ])

    for order_data in orders_data:
        orders_sheet.append([
            order_data["id"], order_data["username"],
            order_data["restaurant_id"], order_data["restaurant_name"],
            order_data["food"], order_data["price"],
            order_data["payment_method"], order_data["payment_status"],
            order_data["order_status"], order_data["created_at"]
        ])

    # Format
    for sheet in workbook.worksheets:
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        sheet.freeze_panes = "A2"
        
        for column in sheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                if cell.value is not None:
                    max_length = max(max_length, len(str(cell.value)))
            sheet.column_dimensions[column_letter].width = min(max_length + 2, 40)

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="karinderya_database.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# =========================================================
# DATABASE INITIALIZATION
# =========================================================
try:
    init_db()
except Exception as e:
    print("WARNING: Database initialization failed:")
    print(e)


# =========================================================
# START APPLICATION
# =========================================================
if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLASK_DEBUG") == "1",
        port=int(os.environ.get("PORT", 5000))
    )