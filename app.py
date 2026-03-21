from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "secret"

DB = "database.db"

# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT,
        password TEXT,
        balance REAL DEFAULT 0,
        savings REAL DEFAULT 0,
        streak INTEGER DEFAULT 0,
        last_active TEXT
    )
    """)

    # EXPENSES
    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        category TEXT,
        date TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # INCOME
    cur.execute("""
    CREATE TABLE IF NOT EXISTS income (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        saved REAL,
        date TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # GOALS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        target REAL,
        current REAL,
        completed INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # SUBSCRIPTIONS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        cost REAL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # TODO
    cur.execute("""
    CREATE TABLE IF NOT EXISTS todo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        text TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()

# ---------------- HELPERS ----------------
def get_user_id(username):
    conn = get_db()
    user = conn.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    conn.close()

    return user["id"] if user else None


@app.context_processor
def inject_user():
    username = request.view_args.get("username") if request.view_args else None
    return dict(current_user=username)

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

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, password)
    ).fetchone()
    conn.close()

    if user:
        return redirect(url_for("dashboard", username=username))

    flash("Invalid login", "danger")
    return redirect(url_for("index"))


# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        if not username or not email or not password:
            flash("Fill all fields", "warning")
            return redirect(url_for("register"))

        conn = get_db()

        try:
            conn.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, password)
            )
            conn.commit()
            flash("Registered successfully", "success")
        except:
            flash("Username already exists", "danger")

        conn.close()
        return redirect(url_for("index"))

    return render_template("register.html")


# DASHBOARD
@app.route("/dashboard/<username>")
def dashboard(username):
    user_id = get_user_id(username)

    if not user_id:
        return redirect(url_for("index"))

    conn = get_db()

    expenses = conn.execute(
        "SELECT * FROM expenses WHERE user_id=?",
        (user_id,)
    ).fetchall()

    income = conn.execute(
        "SELECT * FROM income WHERE user_id=?",
        (user_id,)
    ).fetchall()

    subscriptions = conn.execute(
        "SELECT * FROM subscriptions WHERE user_id=?",
        (user_id,)
    ).fetchall()

    conn.close()

    return render_template("dashboard.html", username=username, expenses=expenses, income=income, subscriptions=subscriptions)


# EXPENSES
@app.route("/expenses/<username>", methods=["GET", "POST"])
def expenses(username):
    user_id = get_user_id(username)

    if not user_id:
        return redirect(url_for("index"))

    conn = get_db()  # ✅ MOVE THIS HERE (before POST)

    if request.method == "POST":
        amount = request.form.get("amount")
        category = request.form.get("category")

        if amount and category:
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
                (user_id, float(amount), category, datetime.utcnow().isoformat())
            )
            conn.commit()

    data = conn.execute(
        "SELECT * FROM expenses WHERE user_id=?",
        (user_id,)
    ).fetchall()

    conn.close()

    return render_template("expenses.html", data=data, username=username)

# INCOME
@app.route("/income/<username>", methods=["GET", "POST"])
def income(username):
    user_id = get_user_id(username)

    if not user_id:
        return redirect(url_for("index"))

    conn = get_db()

    if request.method == "POST":
        amount = request.form.get("amount")
        saved = request.form.get("saved")

        if amount and saved:
            conn.execute(
                "INSERT INTO income (user_id, amount, saved, date) VALUES (?, ?, ?, ?)",
                (user_id, float(amount), float(saved), datetime.utcnow().isoformat())
            )
            conn.commit()

    data = conn.execute(
        "SELECT * FROM income WHERE user_id=?",
        (user_id,)
    ).fetchall()

    conn.close()

    return render_template("income.html", data=data, username=username)

# GOALS
@app.route("/goals/<username>", methods=["GET", "POST"])
def goals(username):
    user_id = get_user_id(username)

    if not user_id:
        return redirect(url_for("index"))

    conn = get_db()

    if request.method == "POST":
        target = request.form.get("target")

        if target:
            conn.execute(
                "INSERT INTO goals (user_id, target, current, completed) VALUES (?, ?, 0, 0)",
                (user_id, float(target))
            )
            conn.commit()

    data = conn.execute(
        "SELECT * FROM goals WHERE user_id=?",
        (user_id,)
    ).fetchall()

    conn.close()

    return render_template("goals.html", data=data, username=username)

# SUBSCRIPTIONS
@app.route("/subscriptions/<username>", methods=["GET", "POST"])
def subscriptions(username):
    user_id = get_user_id(username)

    if not user_id:
        return redirect(url_for("index"))

    conn = get_db()

    if request.method == "POST":
        name = request.form.get("name")
        cost = request.form.get("cost")

        if name and cost:
            conn.execute(
                "INSERT INTO subscriptions (user_id, name, cost) VALUES (?, ?, ?)",
                (user_id, name, float(cost))
            )
            conn.commit()

    data = conn.execute(
        "SELECT * FROM subscriptions WHERE user_id=?",
        (user_id,)
    ).fetchall()

    conn.close()

    return render_template("subscriptions.html", data=data, username=username)

# TODO
@app.route("/todo/<username>", methods=["GET", "POST"])
def todo(username):
    user_id = get_user_id(username)

    if not user_id:
        return redirect(url_for("index"))

    conn = get_db()

    if request.method == "POST":
        text = request.form.get("text")

        if text:
            conn.execute(
                "INSERT INTO todo (user_id, text) VALUES (?, ?)",
                (user_id, text)
            )
            conn.commit()

    data = conn.execute(
        "SELECT * FROM todo WHERE user_id=?",
        (user_id,)
    ).fetchall()

    conn.close()

    return render_template("todo.html", data=data, username=username)

# LEARN
@app.route("/learn/<username>")
def learn(username):
    user_id = get_user_id(username)

    if not user_id:
        return redirect(url_for("index"))

    return render_template("learn.html", username=username)


# PROFILE
@app.route("/profile/<username>")
def profile(username):
    user_id = get_user_id(username)

    if not user_id:
        return redirect(url_for("index"))

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()
    conn.close()

    return render_template("profile.html", username=username, user=user)


# ---------------- RUN ----------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)