from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "secret"

DB = "database.db"

# ---------------- MOCK USERS ----------------
users = {
    "oleksii": {
        "email": "oleksii@test.com",
        "password": "1234",
        "role": "user",
        "balance": 1000
    },
    "olivia": {
        "email": "olivia@test.com",
        "password": "admin",
        "role": "admin",
        "balance": 1000
    }
}

# ---------------- CONTEXT ----------------
@app.context_processor
def inject_user():
    username = request.view_args.get("username") if request.view_args else None

    if username and username in users:
        user = users.get(username)

        return dict(
            current_user=username,
            balance=user["balance"],
            role=user["role"]
        )

    return dict(current_user=None, balance=None, role=None)


# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL,
        category TEXT,
        date TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS income (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL,
        saved REAL,
        date TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target REAL,
        current REAL,
        completed INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        cost REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS todo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT
    )
    """)

    conn.commit()
    conn.close()


# ---------------- STREAK ----------------
def update_streak():
    # simplified for now (no DB user tracking yet)
    pass


# ---------------- ROUTES ----------------

# LOGIN PAGE
@app.route("/")
def index():
    return render_template("index.html")


# LOGIN
@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    if not username or not password:
        flash("Fill all fields", "warning")
        return redirect(url_for("index"))

    user = users.get(username)

    if user and user["password"] == password:
        return redirect(url_for("dashboard", username=username))

    flash("Invalid credentials", "danger")
    return redirect(url_for("index"))


# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        if not username or not email or not password:
            flash("All fields required", "warning")
            return redirect(url_for("register"))

        if username in users:
            flash("Username exists", "danger")
            return redirect(url_for("register"))

        users[username] = {
            "email": email,
            "password": password,
            "role": "user",
            "balance": 1000
        }

        flash("Registered успешно", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


# DASHBOARD
@app.route("/dashboard/<username>")
def dashboard(username):
    if username not in users:
        return redirect(url_for("index"))

    conn = get_db()

    expenses = conn.execute("SELECT * FROM expenses").fetchall()
    income = conn.execute("SELECT * FROM income").fetchall()
    subs = conn.execute("SELECT * FROM subscriptions").fetchall()

    total_exp = sum([e["amount"] for e in expenses])
    total_inc = sum([i["amount"] for i in income])
    sub_cost = sum([s["cost"] for s in subs])

    conn.close()

    return render_template(
        "dashboard.html",
        username=username,
        expenses=total_exp,
        income=total_inc,
        subscriptions=sub_cost
    )


# EXPENSES
@app.route("/expenses/<username>", methods=["GET", "POST"])
def expenses(username):
    if username not in users:
        return redirect(url_for("index"))

    conn = get_db()

    if request.method == "POST":
        amount = request.form.get("amount")
        category = request.form.get("category")

        if amount and category:
            conn.execute(
                "INSERT INTO expenses (amount, category, date) VALUES (?, ?, ?)",
                (float(amount), category, datetime.utcnow().isoformat())
            )
            conn.commit()

    data = conn.execute("SELECT * FROM expenses").fetchall()
    conn.close()

    return render_template("expenses.html", data=data, username=username)

# income
@app.route("/income/<username>", methods=["GET", "POST"])
def income(username):
    if username not in users:
        return redirect(url_for("index"))

    conn = get_db()

    if request.method == "POST":
        amount = request.form.get("amount")
        saved = request.form.get("saved")

        if amount and saved:
            conn.execute(
                "INSERT INTO income (amount, saved, date) VALUES (?, ?, ?)",
                (float(amount), float(saved), datetime.utcnow().isoformat())
            )
            conn.commit()

    data = conn.execute("SELECT * FROM income").fetchall()
    conn.close()

    return render_template("income.html", data=data, username=username)

@app.route("/goals/<username>", methods=["GET", "POST"])
def goals(username):
    if username not in users:
        return redirect(url_for("index"))

    conn = get_db()

    if request.method == "POST":
        target = request.form.get("target")

        if target:
            conn.execute(
                "INSERT INTO goals (target, current, completed) VALUES (?, 0, 0)",
                (float(target),)
            )
            conn.commit()

    data = conn.execute("SELECT * FROM goals").fetchall()
    conn.close()

    return render_template("goals.html", data=data, username=username)

@app.route("/subscriptions/<username>", methods=["GET", "POST"])
def subscriptions(username):
    if username not in users:
        return redirect(url_for("index"))

    conn = get_db()

    if request.method == "POST":
        name = request.form.get("name")
        cost = request.form.get("cost")

        if name and cost:
            conn.execute(
                "INSERT INTO subscriptions (name, cost) VALUES (?, ?)",
                (name, float(cost))
            )
            conn.commit()

    data = conn.execute("SELECT * FROM subscriptions").fetchall()
    conn.close()

    return render_template("subscriptions.html", data=data, username=username)

# TODO
@app.route("/todo/<username>", methods=["GET", "POST"])
def todo(username):
    if username not in users:
        return redirect(url_for("index"))

    conn = get_db()

    if request.method == "POST":
        text = request.form.get("text")

        if text:
            conn.execute(
                "INSERT INTO todo (text) VALUES (?)",
                (text,)
            )
            conn.commit()

    data = conn.execute("SELECT * FROM todo").fetchall()
    conn.close()

    return render_template("todo.html", data=data, username=username)

# LEARN
@app.route("/learn/<username>")
def learn(username):
    if username not in users:
        return redirect(url_for("index"))

    return render_template("learn.html", username=username)


# PROFILE
@app.route("/profile/<username>")
def profile(username):
    if username not in users:
        return redirect(url_for("index"))

    return render_template("profile.html", username=username)


# ---------------- RUN ----------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)