from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime, timedelta
import sqlite3

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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        streak INTEGER DEFAULT 0,
        email TEXT,
        password TEXT,
        balance REAL DEFAULT 0,
        savings REAL DEFAULT 0,
        last_active TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        category TEXT,
        date TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS income (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        saved REAL,
        date TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        target REAL,
        current REAL DEFAULT 0,
        completed INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        cost REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS todo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        text TEXT,
        completed INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()


# ---------------- HELPERS ----------------
def get_user_id(username):
    conn = get_db()
    user = conn.execute(
        "SELECT id FROM users WHERE username=?",
        (username,)
    ).fetchone()
    conn.close()
    return user["id"] if user else None

def update_streak(user_id):
    conn = get_db()

    user = conn.execute(
        "SELECT streak, last_active FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    now = datetime.utcnow()

    if user:
        last = user["last_active"]

        if last:
            last = datetime.fromisoformat(last)
            diff = now - last

            if diff < timedelta(days=1):
                conn.close()
                return
            elif diff < timedelta(days=2):
                streak = user["streak"] + 1
            else:
                streak = 1
        else:
            streak = 1

        conn.execute(
            "UPDATE users SET streak=?, last_active=? WHERE id=?",
            (streak, now.isoformat(), user_id)
        )
        conn.commit()

    conn.close()

@app.context_processor
def inject_user():
    username = request.view_args.get("username") if request.view_args else None
    return dict(current_user=username)


# ---------------- ROUTES ----------------

# INDEX
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

    #GET USER
    user = conn.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    # expenses
    expenses_data = conn.execute(
        "SELECT * FROM expenses WHERE user_id=?",
        (user_id,)
    ).fetchall()

    # income
    income_data = conn.execute(
        "SELECT * FROM income WHERE user_id=?",
        (user_id,)
    ).fetchall()

    # subscriptions
    subs_data = conn.execute(
        "SELECT * FROM subscriptions WHERE user_id=?",
        (user_id,)
    ).fetchall()

    conn.close()

    # calculations
    total_exp = sum([e["amount"] for e in expenses_data])
    total_inc = sum([i["amount"] for i in income_data])
    sub_cost = sum([s["cost"] for s in subs_data])
    # avoid division by zero
    food_percent = 0
    subs_percent = 0

    # category breakdown for food
    food_total = sum([e["amount"] for e in expenses_data if e["category"] == "Food & Dining"])

    if total_exp > 0:
        food_percent = round((food_total / total_exp) * 100)
        subs_percent = round((sub_cost / total_exp) * 100)

    # potential savings (if cancel subs)
    potential_savings = sub_cost

    # FINANCIAL SCORE (0–100)
    score = 0

    # simple scoring logic
    if total_inc > 0:
        savings_rate = user["savings"] / total_inc
        if savings_rate > 0.2:
            score += 40
        elif savings_rate > 0.1:
            score += 25
        else:
            score += 10

    if total_inc > total_exp:
        score += 30
    else:
        score += 10

    if user["streak"] > 5:
        score += 20
    else:
        score += 10

    # clamp to 100
    score = min(score, 100)

    return render_template(
    "dashboard.html",
    current_user=username,
    income=total_inc,
    expenses=total_exp,
    subscriptions=sub_cost,
    savings=user["savings"],
    balance=user["balance"],
    streak=user["streak"],
    food_percent=food_percent,
    subs_percent=subs_percent,
    potential_savings=potential_savings,
    score=score
)


# EXPENSES
from collections import defaultdict

@app.route("/expenses/<username>", methods=["GET", "POST"])
def expenses(username):
    user_id = get_user_id(username)

    if not user_id:
        return redirect(url_for("index"))

    conn = get_db()

    if request.method == "POST":
        amount = request.form.get("amount")
        category = request.form.get("category")

        if amount and category:
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
                (user_id, amount, category, datetime.utcnow().isoformat())
            )

            # update balance
            conn.execute("""
                UPDATE users
                SET balance = balance - ?
                WHERE id = ?
            """, (amount, user_id))

            conn.commit()

            update_streak(user_id)

    data = conn.execute(
        "SELECT * FROM expenses WHERE user_id=?",
        (user_id,)
    ).fetchall()

    conn.close()

    # ✅ total expenses
    total_expenses = sum([e["amount"] for e in data])

    # ✅ category breakdown
    category_totals = defaultdict(float)
    for e in data:
        category_totals[e["category"]] += e["amount"]

    labels = list(category_totals.keys())
    values = list(category_totals.values())

    return render_template(
        "expenses.html",
        data=data,
        username=username,
        total_expenses=total_expenses,
        labels=labels,
        values=values
    )

# UPDATE GOAL
@app.route("/update_goal/<username>/<int:goal_id>", methods=["POST"])
def update_goal(username, goal_id):
    user_id = get_user_id(username)

    if not user_id:
        return redirect(url_for("index"))

    amount = float(request.form.get("amount", 0))

    conn = get_db()

    # get user savings
    user = conn.execute(
        "SELECT savings FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    if not user or user["savings"] < amount:
        flash("Not enough savings!", "danger")
        conn.close()
        return redirect(url_for("goals", username=username))

    goal = conn.execute(
        "SELECT * FROM goals WHERE id=? AND user_id=?",
        (goal_id, user_id)
    ).fetchone()

    if goal:
        new_current = goal["current"] + amount
        completed = 1 if new_current >= goal["target"] else 0

        # update goal
        conn.execute(
            "UPDATE goals SET current=?, completed=? WHERE id=?",
            (new_current, completed, goal_id)
        )

        # subtract from savings
        conn.execute(
            "UPDATE users SET savings = savings - ? WHERE id=?",
            (amount, user_id)
        )

        conn.commit()

    conn.close()

    return redirect(url_for("goals", username=username))

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
            amount = float(amount)
            saved = float(saved)

            # ❗ safety check
            if saved > amount:
                flash("Saved amount cannot be greater than income", "danger")
                return redirect(url_for("income", username=username))

            # 1. save income record
            conn.execute(
                "INSERT INTO income (user_id, amount, saved, date) VALUES (?, ?, ?, ?)",
                (user_id, amount, saved, datetime.utcnow().isoformat())
            )

            # 2. update user balance + savings
            conn.execute("""
                UPDATE users
                SET balance = balance + ?,
                    savings = savings + ?
                WHERE id = ?
            """, (amount, saved, user_id))

            conn.commit()

    data = conn.execute(
        "SELECT * FROM income WHERE user_id=? ORDER BY date DESC",
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

    # GET USER (this was missing)
    user = conn.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    if request.method == "POST":
        target = request.form.get("target")

        if target:
            conn.execute(
                "INSERT INTO goals (user_id, target) VALUES (?, ?)",
                (user_id, float(target))
            )
            conn.commit()

    data = conn.execute(
        "SELECT * FROM goals WHERE user_id=?",
        (user_id,)
    ).fetchall()

    conn.close()

    return render_template(
        "goals.html",
        data=data,
        username=username,
        savings=user["savings"]  # ✅ now works
    )


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

        if name and cost is not None:
            conn.execute(
                "INSERT INTO subscriptions (user_id, name, cost) VALUES (?, ?, ?)",
                (user_id, name, float(cost))
            )
            conn.commit()

    data = conn.execute(
        "SELECT * FROM subscriptions WHERE user_id=?",
        (user_id,)
    ).fetchall()

    total_subs = sum([s["cost"] for s in data])

    conn.close()
    return render_template("subscriptions.html", data=data, username=username, total_subs=total_subs)

# DELETE SUBSCRIPTION
@app.route("/delete_subscription/<username>/<int:sub_id>", methods=["POST"])
def delete_subscription(username, sub_id):
    user_id = get_user_id(username)

    if not user_id:
        return redirect(url_for("index"))

    conn = get_db()

    conn.execute(
        "DELETE FROM subscriptions WHERE id=? AND user_id=?",
        (sub_id, user_id)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("subscriptions", username=username))

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

# DELETE TODO
@app.route("/delete_task/<username>/<int:task_id>")
def delete_task(username, task_id):
    user_id = get_user_id(username)

    if not user_id:
        return redirect(url_for("index"))

    conn = get_db()

    conn.execute(
        "DELETE FROM todo WHERE id=? AND user_id=?",
        (task_id, user_id)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("todo", username=username))

# COMPLETE TASK
@app.route("/complete_task/<username>/<int:task_id>")
def complete_task(username, task_id):
    user_id = get_user_id(username)

    if not user_id:
        return redirect(url_for("index"))

    conn = get_db()

    conn.execute("""
        UPDATE todo
        SET completed = 1
        WHERE id = ? AND user_id = ?
    """, (task_id, user_id))

    conn.commit()

    # streak boost
    update_streak(user_id)

    conn.close()

    return redirect(url_for("todo", username=username))

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

    # get income + expenses
    income_data = conn.execute(
        "SELECT * FROM income WHERE user_id=?",
        (user_id,)
    ).fetchall()

    expenses_data = conn.execute(
        "SELECT * FROM expenses WHERE user_id=?",
        (user_id,)
    ).fetchall()

    # tasks done
    tasks_done = conn.execute(
        "SELECT COUNT(*) as count FROM todo WHERE user_id=? AND completed=1",
        (user_id,)
    ).fetchone()["count"]

    conn.close()

    total_inc = sum([i["amount"] for i in income_data])
    total_exp = sum([e["amount"] for e in expenses_data])

    # --- SAME SCORE LOGIC ---
    score = 0

    if total_inc > 0:
        savings_rate = user["savings"] / total_inc
        if savings_rate > 0.2:
            score += 40
        elif savings_rate > 0.1:
            score += 25
        else:
            score += 10

    if total_inc > total_exp:
        score += 30
    else:
        score += 10

    if user["streak"] > 5:
        score += 20
    else:
        score += 10

    score = min(score, 100)

    # simple feedback text
    if score > 75:
        message = "You're in great financial shape!"
    elif score > 50:
        message = "You're doing well, keep improving!"
    else:
        message = "Needs attention — you can improve your habits."

    return render_template(
        "profile.html",
        user=user,
        username=username,
        score=score,
        tasks_done=tasks_done,
        message=message, level=user["streak"] // 3 + 1
    )

# ---------------- RUN ----------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)