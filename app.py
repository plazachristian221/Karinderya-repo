import os
import sqlite3
from pathlib import Path
from datetime import datetime
from io import BytesIO
from contextlib import contextmanager 

import psycopg2
from psycopg2.extras import RealDictCursor
from openpyxl import Workbook
from openpyxl.styles import Font
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from flask import (
    Flask, request, render_template, redirect,
    url_for, session, send_file, abort, flash
)
BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "pet_store.db"

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY", "local-development-only-change-this"
)


# =====================================================
# DATABASE CONNECTION
# =====================================================

def get_db():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        if os.environ.get("RAILWAY_ENVIRONMENT"):
            raise RuntimeError(
                "DATABASE_URL is missing in Railway Variables."
            )

        conn = sqlite3.connect(str(DATABASE))
        conn.row_factory = sqlite3.Row
        return conn

    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://", "postgresql://", 1
        )

    return psycopg2.connect(
        database_url,
        connect_timeout=10,
        sslmode="require"
    )


def is_sqlite(conn):
    return isinstance(conn, sqlite3.Connection)


def placeholder(conn):
    return "?" if is_sqlite(conn) else "%s"

@contextmanager
def cursor_for(conn):
    cur = None
    try:
        if is_sqlite(conn):
            cur = conn.cursor()
        else:
            cur = conn.cursor(cursor_factory=RealDictCursor)
        yield cur
    finally:
        if cur is not None:
            cur.close()
# =====================================================
# DATABASE INITIALIZATION
# =====================================================

def init_db():
    conn = get_db()
    p = placeholder(conn)

    try:
        cur = conn.cursor()

     
        # Add email column to existing databases if needed.
        if is_sqlite(conn):
            cur.execute("PRAGMA table_info(users)")
            columns = {row[1] for row in cur.fetchall()}

            if "email" not in columns:
                cur.execute("ALTER TABLE users ADD COLUMN email TEXT")

            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email
                ON users(email)
            """)
        else:
            cur.execute("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS email TEXT
            """)

            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email
                ON users(email)
            """)


        # Create the administrator account if it does not exist.
        cur.execute(
            f"SELECT id FROM users WHERE username = {p}",
            ("admin",)
        )

        if not cur.fetchone():
            admin_password = os.environ.get(
                "ADMIN_PASSWORD", "admin123"
            )

            cur.execute(
                f"""INSERT INTO users
                (username, password, role, created_at)
                VALUES ({p}, {p}, {p}, {p})""",
                (
                    "admin",
                    generate_password_hash(admin_password),
                    "admin",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            )

        # Add sample products without duplicating existing products.
        # This also adds the new products to an existing database.
        samples = [
            # DRY FOOD
            (
                "Puppy Chicken Dry Food 1kg", "Dry Food", "Dog",
                "Complete dry food for growing puppies.", 249.00, 20, ""
            ),
            (
                "Adult Dog Beef Kibble 1kg", "Dry Food", "Dog",
                "Everyday food for adult dogs.", 219.00, 25, ""
            ),
            (
                "Kitten Dry Food 1kg", "Dry Food", "Cat",
                "Dry food for kittens.", 269.00, 18, ""
            ),
            (
                "Adult Cat Food 1kg", "Dry Food", "Cat",
                "Daily food for adult cats.", 239.00, 22, ""
            ),

            # WET FOOD
            (
                "Premium Chicken Wet Food", "Wet Food", "Dog",
                "Tender chicken wet food for adult dogs.",
                85.00, 30, ""
            ),
            (
                "Tuna Wet Food", "Wet Food", "Cat",
                "Delicious tuna wet food for cats.",
                65.00, 25, ""
            ),
            (
                "Salmon Pate Wet Food", "Wet Food", "Cat",
                "Smooth salmon pate for adult cats.",
                75.00, 20, ""
            ),
            (
                "Beef and Liver Wet Food", "Wet Food", "Dog",
                "Savory beef and liver wet food for dogs.",
                95.00, 20, ""
            ),
            (
                "Ocean Fish Wet Food", "Wet Food", "Both",
                "Fish-based wet food for cats and dogs.",
                89.00, 15, ""
            ),
            (
                "Chicken Gravy Cat Food", "Wet Food", "Cat",
                "Chicken pieces in gravy for cats.",
                79.00, 24, ""
            ),
            (
                "Lamb Wet Food", "Wet Food", "Dog",
                "Lamb-flavored wet food for dogs.",
                99.00, 18, ""
            ),
            (
                "Salmon and Chicken Wet Food", "Wet Food", "Both",
                "A salmon and chicken wet food option for pets.",
                92.00, 20, ""
            ),

            # TREATS
            (
                "Chicken Flavor Pet Treats", "Treats", "Dog",
                "Reward treats for dogs.",
                89.00, 30, ""
            ),
            (
                "Crunchy Cat Treats", "Treats", "Cat",
                "Crunchy treats for cats.",
                69.00, 25, ""
            ),
            (
                "Mixed Pet Biscuits", "Treats", "Both",
                "Biscuits suitable for cats and dogs when appropriate.",
                79.00, 20, ""
            ),

            # PET SUPPLIES
            (
                "Catnip Toy", "Pet Supplies", "Cat",
                "A toy for cat playtime.",
                99.00, 15, ""
            ),
            (
                "Rubber Dog Chew Toy", "Pet Supplies", "Dog",
                "A chew toy for supervised dog play.",
                129.00, 15, ""
            ),
            (
                "Adjustable Dog Collar", "Pet Supplies", "Dog",
                "An adjustable collar for everyday walks.",
                149.00, 12, ""
            ),
            (
                "Pet Leash", "Pet Supplies", "Both",
                "A leash for walking compatible pets.",
                179.00, 12, ""
            ),
            (
                "Stainless Steel Pet Bowl", "Pet Supplies", "Both",
                "A reusable bowl for pet food and water.",
                119.00, 20, ""
            ),
            (
                "Pet Food Storage Container", "Pet Supplies", "Both",
                "A container for storing dry pet food.",
                199.00, 10, ""
            ),
            (
                "Pet Grooming Brush", "Pet Supplies", "Both",
                "A brush for routine pet grooming.",
                139.00, 12, ""
            ),
            (
                "Pet Shampoo 250ml", "Pet Supplies", "Both",
                "Pet shampoo for suitable coats and skin.",
                159.00, 15, ""
            ),
            (
                "Cat Litter 5kg", "Pet Supplies", "Cat",
                "Cat litter for household litter trays.",
                199.00, 20, ""
            ),
            (
                "Pet Carrier Bag", "Pet Supplies", "Both",
                "A carrier for transporting compatible pets.",
                499.00, 5, ""
            ),
            (
                "Pet Nail Clipper", "Pet Supplies", "Both",
                "A nail clipper designed for pet grooming.",
                129.00, 10, ""
            ),
            (
                "Pet Waste Bags", "Pet Supplies", "Dog",
                "Waste bags for cleaning up during walks.",
                49.00, 30, ""
            ),
        ]

        for item in samples:
            cur.execute(
                f"SELECT id FROM products WHERE name = {p}",
                (item[0],)
            )

            # Skip products that already exist.
            if cur.fetchone():
                continue

            cur.execute(
                f"""INSERT INTO products
                (name, category, pet_type, description,
                 price, stock, image_url, created_at)
                VALUES ({', '.join([p] * 8)})""",
                item + (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
            )

        conn.commit()


    finally:
        conn.close()


# =====================================================
# HOME PAGE
# =====================================================

@app.route("/")
def home():
    conn = get_db()

    try:
        with cursor_for(conn) as cur:
            cur.execute("""
                SELECT * FROM products
                WHERE stock > 0
                ORDER BY id DESC LIMIT 6
            """)
            products = cur.fetchall()

        return render_template("index.html", featured=products)

    finally:
        conn.close()


# =====================================================
# REGISTER
# =====================================================



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(username) < 3:
            flash("Username must be at least 3 characters.", "danger")
            return redirect(url_for("register"))

        if not email or "@" not in email:
            flash("Please enter a valid email address.", "danger")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        conn = get_db()
        p = placeholder(conn)

        try:
            with cursor_for(conn) as cur:
                cur.execute(
                    f"""SELECT id FROM users
                        WHERE username = {p} OR email = {p}""",
                    (username, email)
                )

                if cur.fetchone():
                    flash(
                        "That username or email is already registered.",
                        "danger"
                    )
                    return redirect(url_for("register"))

                cur.execute(
                    f"""INSERT INTO users
                        (username, email, password, role, created_at)
                        VALUES ({', '.join([p] * 5)})""",
                    (
                        username,
                        email,
                        generate_password_hash(password),
                        "customer",
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                )

            conn.commit()

        except (sqlite3.IntegrityError, psycopg2.IntegrityError):
            conn.rollback()
            flash(
                "That username or email is already registered.",
                "danger"
            )
            return redirect(url_for("register"))

        finally:
            conn.close()

        flash(
            "Registration successful! Please log in to continue.",
            "success"
        )
        return redirect(url_for("login"))

    return render_template("register.html")




# =====================================================
# LOGIN
# =====================================================



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        p = placeholder(conn)

        try:
            with cursor_for(conn) as cur:
                cur.execute(
                    f"SELECT * FROM users WHERE username = {p}",
                    (username,)
                )
                user = cur.fetchone()

        finally:
            conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["username"] = user["username"]
            session["role"] = user["role"]

            flash("Login successful!", "success")

            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("shop"))

        flash("Invalid username or password.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")

# =====================================================
# ADMIN ACCESS CONTROL
# =====================================================

def require_admin():
    if not session.get("username"):
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        abort(403)

    return None


# =====================================================
# PET FOOD SHOP
# =====================================================

@app.route("/shop")
def shop():
    conn = get_db()
    p = placeholder(conn)

    category = request.args.get("category", "").strip()
    pet_type = request.args.get("pet_type", "").strip()

    try:
        query = "SELECT * FROM products WHERE 1=1"
        params = []

        if category:
            query += f" AND category = {p}"
            params.append(category)

        if pet_type:
            query += f" AND pet_type = {p}"
            params.append(pet_type)

        query += " ORDER BY name"

        with cursor_for(conn) as cur:
            cur.execute(query, tuple(params))
            products = cur.fetchall()

        return render_template(
            "shop.html",
            products=products,
            category=category,
            pet_type=pet_type
        )

    finally:
        conn.close()


# =====================================================
# PRODUCT DETAILS
# =====================================================

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    conn = get_db()
    p = placeholder(conn)

    try:
        with cursor_for(conn) as cur:
            cur.execute(
                f"SELECT * FROM products WHERE id = {p}",
                (product_id,)
            )
            product = cur.fetchone()

        if not product:
            abort(404)

        return render_template("product.html", product=product)

    finally:
        conn.close()


# =====================================================
# PLACE ORDER
# =====================================================

@app.route("/order/<int:product_id>", methods=["POST"])
def place_order(product_id):
    if not session.get("username"):
        return redirect(url_for("login"))

    try:
        quantity = int(request.form.get("quantity", "1"))
    except ValueError:
        flash("Enter a valid quantity.", "error")
        return redirect(url_for(
            "product_detail", product_id=product_id
        ))

    payment_method = request.form.get("payment_method", "")

    if quantity < 1 or quantity > 100:
        flash("Quantity must be between 1 and 100.", "error")
        return redirect(url_for(
            "product_detail", product_id=product_id
        ))

    if payment_method not in ("Cash on Delivery", "GCash"):
        flash("Choose a valid payment method.", "error")
        return redirect(url_for(
            "product_detail", product_id=product_id
        ))

    conn = get_db()
    p = placeholder(conn)

    try:
        # Lock a PostgreSQL product row to prevent overselling.
        with cursor_for(conn) as cur:
            sql = f"SELECT * FROM products WHERE id = {p}"
            if not is_sqlite(conn):
                sql += " FOR UPDATE"

            cur.execute(sql, (product_id,))
            product = cur.fetchone()

            if not product:
                abort(404)

            if product["stock"] < quantity:
                flash("Not enough stock available.", "error")
                return redirect(url_for(
                    "product_detail", product_id=product_id
                ))

            price = float(product["price"])
            total = round(price * quantity, 2)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cur.execute(
                f"""INSERT INTO pet_orders
                (username, product_id, product_name, quantity,
                 unit_price, total_price, payment_method,
                 payment_status, order_status, created_at)
                VALUES ({', '.join([p] * 10)})""",
                (
                    session["username"],
                    product_id,
                    product["name"],
                    quantity,
                    price,
                    total,
                    payment_method,
                    "Pending",
                    "Processing",
                    now
                )
            )

            cur.execute(
                f"""UPDATE products SET stock = stock - {p}
                WHERE id = {p}""",
                (quantity, product_id)
            )

        conn.commit()
        flash("Your order has been placed!", "success")
        return redirect(url_for("my_orders"))

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# =====================================================
# CUSTOMER ORDER HISTORY
# =====================================================

@app.route("/my-orders")
def my_orders():
    if not session.get("username"):
        return redirect(url_for("login"))

    conn = get_db()
    p = placeholder(conn)

    try:
        with cursor_for(conn) as cur:
            cur.execute(
                f"""SELECT * FROM pet_orders
                WHERE username = {p}
                ORDER BY id DESC""",
                (session["username"],)
            )
            orders = cur.fetchall()

        return render_template("orders.html", orders=orders)

    finally:
        conn.close()


# =====================================================
# ADMIN DASHBOARD
# =====================================================

@app.route("/admin")
def admin_dashboard():
    denied = require_admin()
    if denied:
        return denied

    conn = get_db()

    try:
        with cursor_for(conn) as cur:
            cur.execute("SELECT * FROM products ORDER BY id DESC")
            products = cur.fetchall()

            cur.execute("SELECT * FROM pet_orders ORDER BY id DESC")
            orders = cur.fetchall()

            cur.execute("""
                SELECT id, username, role, created_at
                FROM users ORDER BY id DESC
            """)
            users = cur.fetchall()

        return render_template(
            "admin.html",
            products=products,
            orders=orders,
            users=users
        )

    finally:
        conn.close()


# =====================================================
# ADD PRODUCT (CREATE)
# =====================================================

@app.route("/admin/products/add", methods=["POST"])
def add_product():
    denied = require_admin()
    if denied:
        return denied

    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    pet_type = request.form.get("pet_type", "").strip()
    description = request.form.get("description", "").strip()
    image_url = request.form.get("image_url", "").strip()

    try:
        price = float(request.form.get("price", "0"))
        stock = int(request.form.get("stock", "0"))
    except ValueError:
        flash("Price or stock is invalid.", "error")
        return redirect(url_for("admin_dashboard"))

    if (
        not name
        or category not in (
            "Dry Food", "Wet Food", "Treats", "Pet Supplies"
        )
        or pet_type not in ("Dog", "Cat", "Both")
        or price <= 0
        or stock < 0
    ):
        flash("Please check the product details.", "error")
        return redirect(url_for("admin_dashboard"))

    conn = get_db()
    p = placeholder(conn)

    try:
        with cursor_for(conn) as cur:
            cur.execute(
                f"""INSERT INTO products
                (name, category, pet_type, description,
                 price, stock, image_url, created_at)
                VALUES ({', '.join([p] * 8)})""",
                (
                    name, category, pet_type, description,
                    price, stock, image_url,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            )

        conn.commit()
        flash("Product added successfully!", "success")

    finally:
        conn.close()

    return redirect(url_for("admin_dashboard"))


# =====================================================
# EDIT PRODUCT (UPDATE)
# =====================================================

@app.route("/admin/products/<int:product_id>/edit", methods=["POST"])
def edit_product(product_id):
    denied = require_admin()
    if denied:
        return denied

    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    pet_type = request.form.get("pet_type", "").strip()
    description = request.form.get("description", "").strip()
    image_url = request.form.get("image_url", "").strip()

    try:
        price = float(request.form.get("price", "0"))
        stock = int(request.form.get("stock", "0"))
    except ValueError:
        flash("Invalid price or stock.", "error")
        return redirect(url_for("admin_dashboard"))

    if (
        not name
        or category not in (
            "Dry Food", "Wet Food", "Treats", "Pet Supplies"
        )
        or pet_type not in ("Dog", "Cat", "Both")
        or price <= 0
        or stock < 0
    ):
        flash("Please check the product details.", "error")
        return redirect(url_for("admin_dashboard"))

    conn = get_db()
    p = placeholder(conn)

    try:
        with cursor_for(conn) as cur:
            cur.execute(
                f"""UPDATE products
                SET name={p}, category={p}, pet_type={p},
                    description={p}, price={p}, stock={p},
                    image_url={p}
                WHERE id={p}""",
                (
                    name, category, pet_type, description,
                    price, stock, image_url, product_id
                )
            )

        conn.commit()
        flash("Product updated successfully!", "success")

    finally:
        conn.close()

    return redirect(url_for("admin_dashboard"))


# =====================================================
# DELETE PRODUCT (DELETE)
# =====================================================

@app.route(
    "/admin/products/<int:product_id>/delete",
    methods=["POST"]
)
def delete_product(product_id):
    denied = require_admin()
    if denied:
        return denied

    conn = get_db()
    p = placeholder(conn)

    try:
        with cursor_for(conn) as cur:
            cur.execute(
                f"DELETE FROM products WHERE id = {p}",
                (product_id,)
            )

        conn.commit()
        flash("Product deleted.", "success")

    finally:
        conn.close()

    return redirect(url_for("admin_dashboard"))


# =====================================================
# EXPORT DATABASE TO EXCEL
# =====================================================

@app.route("/export-excel")
def export_excel():
    denied = require_admin()
    if denied:
        return denied

    conn = get_db()

    try:
        with cursor_for(conn) as cur:
            cur.execute("""
                SELECT id, username, role, created_at
                FROM users ORDER BY id
            """)
            users = cur.fetchall()

            cur.execute("SELECT * FROM products ORDER BY id")
            products = cur.fetchall()

            cur.execute("SELECT * FROM pet_orders ORDER BY id DESC")
            orders = cur.fetchall()

    finally:
        conn.close()

    workbook = Workbook()

    datasets = [
        (
            "Users",
            ["ID", "Username", "Role", "Created At"],
            users,
            ["id", "username", "role", "created_at"]
        ),
        (
            "Products",
            ["ID", "Name", "Category", "Pet Type",
             "Description", "Price", "Stock", "Image URL",
             "Created At"],
            products,
            ["id", "name", "category", "pet_type",
             "description", "price", "stock", "image_url",
             "created_at"]
        ),
        (
            "Orders",
            ["ID", "Username", "Product", "Quantity",
             "Unit Price", "Total", "Payment Method",
             "Payment Status", "Order Status", "Created At"],
            orders,
            ["id", "username", "product_name", "quantity",
             "unit_price", "total_price", "payment_method",
             "payment_status", "order_status", "created_at"]
        )
    ]

    for index, (title, headers, rows, keys) in enumerate(datasets):
        sheet = (
            workbook.active
            if index == 0
            else workbook.create_sheet()
        )
        sheet.title = title
        sheet.append(headers)

        for row in rows:
            sheet.append([row[key] for key in keys])

        for cell in sheet[1]:
            cell.font = Font(bold=True)

        sheet.freeze_panes = "A2"

        for column in sheet.columns:
            max_length = max(
                (len(str(cell.value)) for cell in column
                 if cell.value is not None),
                default=8
            )
            sheet.column_dimensions[
                column[0].column_letter
            ].width = min(max_length + 2, 40)

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="pet_store_database.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )


# =====================================================
# LOGOUT AND HEALTH CHECK
# =====================================================

@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out successfully!", "success")
    return redirect(url_for("home"))



@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/db-check")
def db_check():
    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()[0]

        return {
            "status": "success",
            "connected": True,
            "database": (
                "sqlite" if is_sqlite(conn) else "postgresql"
            ),
            "test_query": result
        }, 200

    except Exception:
        app.logger.exception("Database check failed")
        return {
            "status": "error",
            "connected": False,
            "message": "Check your database configuration and logs."
        }, 500

    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()
# =====================================================
# NEARBY PET STORES
# =====================================================

@app.route("/nearby")
def nearby():
    return render_template("nearby.html")

# =====================================================
# STARTUP
# =====================================================

init_db()

if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLASK_DEBUG") == "1",
        port=int(os.environ.get("PORT", 5000))
    )
