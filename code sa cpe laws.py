from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "lutong-bahay-secret-key"
DATABASE = "karinderya.db"

# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    
    # Orders table
    conn.execute("""
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
    
    # Users table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()

# =========================================================
# KARINDERYAS & MENUS (Hardcoded Data)
# =========================================================

restaurants = {
    1: {
        "name": "Karinderya Ni Maria",
        "address": "Quezon City",
        "lat": 14.6760,
        "lng": 121.0437
    },
    2: {
        "name": "Lutong Bahay Express",
        "address": "Quezon City",
        "lat": 14.6800,
        "lng": 121.0500
    },
    3: {
        "name": "Nanay's Karinderya",
        "address": "Quezon City",
        "lat": 14.6700,
        "lng": 121.0400
    },
    4: {
        "name": "Ate's Carinderia",
        "address": "Quezon City",
        "lat": 14.6900,
        "lng": 121.0550
    }
}

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
# ROUTES
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not username or not password:
            return render_template("register.html", error="All fields are required.")
        
        if password != confirm_password:
            return render_template("register.html", error="Passwords do not match.")

        conn = get_db()
        # Check if username already exists
        existing_user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        
        if existing_user:
            conn.close()
            return render_template("register.html", error="Username already exists. Please choose another.")

        # Encrypt the password and save the user
        hashed_password = generate_password_hash(password)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn.execute(
            "INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
            (username, hashed_password, created_at)
        )
        conn.commit()
        conn.close()

        # Automatically log the user in after registering
        session["username"] = username
        return redirect(url_for("nearby"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db()
        # Fetch user from database
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        # Check if user exists AND the hashed password matches
        if user and check_password_hash(user["password"], password):
            session["username"] = username
            return redirect(url_for("nearby"))

        return render_template("login.html", error="Invalid username or password.")

    return render_template("login.html")


@app.route("/nearby")
def nearby():
    if "username" not in session:
        return redirect(url_for("login"))
    
    return render_template("nearby.html", restaurants=restaurants)


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

        restaurant_data = restaurants.get(int(restaurant_id))
        if restaurant_data is None:
            return "Karinderya not found.", 404

        try:
            price = float(price)
        except ValueError:
            return "Invalid price.", 400

        username = session["username"]
        payment_status = "Pay on Pickup" if payment_method == "Cash on Pickup" else "Pending"
        order_status = "Waiting"
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db()
        cursor = conn.execute(
            """
            INSERT INTO orders 
            (username, restaurant_id, restaurant_name, food, price, payment_method, payment_status, order_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (username, int(restaurant_id), restaurant_data["name"], food, price, payment_method, payment_status, order_status, created_at)
        )
        conn.commit()
        order_id = cursor.lastrowid
        conn.close()

        return redirect(url_for("queue", order_id=order_id))

    # GET request handler for order confirmation page
    restaurant_id = request.args.get("restaurant_id")
    food = request.args.get("food")
    price = request.args.get("price")

    if not restaurant_id:
        return "Restaurant is required.", 400

    restaurant_data = restaurants.get(int(restaurant_id))
    if restaurant_data is None:
        return "Karinderya not found.", 404

    return render_template(
        "order.html",
        restaurant=restaurant_data,
        restaurant_id=restaurant_id,
        food=food,
        price=price
    )


@app.route("/queue/<int:order_id>")
def queue(order_id):
    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    order_data = conn.execute(
        "SELECT * FROM orders WHERE id = ? AND username = ?",
        (order_id, session["username"])
    ).fetchone()
    conn.close()

    if order_data is None:
        return "Order not found.", 404

    return render_template("queue.html", order=order_data)


@app.route("/orders")
def orders():
    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    customer_orders = conn.execute(
        "SELECT * FROM orders WHERE username = ? ORDER BY id DESC",
        (session["username"],)
    ).fetchall()
    conn.close()

    return render_template("orders.html", orders=customer_orders)


@app.route("/menu")
def menu():
    if "username" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("nearby"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":
    init_db()
    app.run(debug=True)