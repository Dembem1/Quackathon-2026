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

# ─── TRACK DATA ─────────────────────────────────────────────
TRACKS = {
    "saving": {
        "title": "Saving",
        "theory": [
            {
                "title": "Pay Yourself First",
                "body": "Saving isn’t what’s left over — it’s what you take first. Even small amounts build habits.",
                "highlight": "Pay yourself first."
            },
            {
                "title": "50/30/20 Rule",
                "body": "Split income into needs (50%), wants (30%), savings (20%).",
                "highlight": "50 needs · 30 wants · 20 savings"
            }
        ],
        "quiz": [
            {
                "q": "What does 'pay yourself first' mean?",
                "opts": [
                    "Spend first",
                    "Save before spending",
                    "Only save leftovers"
                ],
                "a": 1
            },
            {
                "q": "What is 20% in the rule?",
                "opts": [
                    "Rent",
                    "Savings",
                    "Food"
                ],
                "a": 1
            }
        ]
    },

    "investing": {
        "title": "Investing",
        "theory": [
            {
                "title": "Compound Interest",
                "body": "Your money earns money, then that earns more.",
                "highlight": "Start early."
            },
            {
                "title": "Index Funds",
                "body": "Own many companies instead of picking one.",
                "highlight": "Diversify."
            }
        ],
        "quiz": [
            {
                "q": "What is compound interest?",
                "opts": [
                    "Flat interest",
                    "Interest on interest",
                    "Bank fee"
                ],
                "a": 1
            },
            {
                "q": "What is an index fund?",
                "opts": [
                    "One stock",
                    "Many companies",
                    "Savings account"
                ],
                "a": 1
            }
        ]
    },

    "credit": {
        "title": "Credit",
        "theory": [
            {
                "title": "Credit Score",
                "body": "Shows how reliable you are with money.",
                "highlight": "Pay on time."
            }
        ],
        "quiz": [
            {
                "q": "What improves credit score?",
                "opts": [
                    "Late payments",
                    "On-time payments",
                    "Ignoring bills"
                ],
                "a": 1
            }
        ]
    },

    "subscriptions": {
        "title": "Subscriptions",
        "theory": [
            {
                "title": "Subscription Creep",
                "body": "Small payments add up quickly.",
                "highlight": "Track everything."
            }
        ],
        "quiz": [
            {
                "q": "What is subscription creep?",
                "opts": [
                    "One big payment",
                    "Lots of small subscriptions",
                    "Free trial"
                ],
                "a": 1
            }
        ]
    },

    "rent": {
        "title": "Rent & Bills",
        "theory": [
            {
                "title": "30% Rule",
                "body": "Don’t spend more than 30% on rent.",
                "highlight": "Stay under 30%."
            }
        ],
        "quiz": [
            {
                "q": "Recommended rent %?",
                "opts": [
                    "10%",
                    "30%",
                    "70%"
                ],
                "a": 1
            }
        ]
    }
}

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

    # personalised tips
    tips = []
    # ❗ spending too much
    if total_exp > total_inc:
        tips.append("You're spending more than you earn. Try reducing non-essential expenses.")

    # ❗ low savings
    if user["savings"] < total_inc * 0.2:
        tips.append("Try to save at least 20% of your income.")

    # ❗ high subscriptions
    if sub_cost > total_inc * 0.15:
        tips.append("Your subscriptions are high. Consider cancelling unused ones.")

    # ❗ food spending
    food_total = sum([e["amount"] for e in expenses_data if e["category"] == "Food & Dining"])
    if total_exp > 0 and (food_total / total_exp) > 0.4:
        tips.append("You spend a lot on food. Cooking at home could save money.")

    tips = tips[:3]  # show only top 3

    # fallback
    if not tips:
        tips.append("You're doing great! Keep managing your finances wisely.")

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
    score=score, tips=tips
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
    return render_template("learn.html", current_user=username)
  
# LEARN TOPIC
@app.route("/learn/<username>/<topic_id>")
def learn_topic(username, topic_id):
    topic = TRACKS.get(topic_id)
    if not topic:
        return "Topic not found"
    return render_template("learn_topic.html", topic=topic, current_user=username, topic_id=topic_id)

# HANDLE QUIZ 
@app.route("/quiz/<username>/<topic_id>", methods=["GET", "POST"])
def quiz(username, topic_id):
    topic = TRACKS.get(topic_id)

    if not topic:
        return "Topic not found"

    results = []
    score = 0

    if request.method == "POST":
        for i, q in enumerate(topic["quiz"]):
            selected = request.form.get(f"q{i}")
            correct = q.get("a")

            is_correct = selected is not None and int(selected) == correct

            if is_correct:
                score += 1

            results.append({
                "question": q["q"],
                "selected": int(selected) if selected else None,
                "correct": correct,
                "options": q["opts"],
                "is_correct": is_correct
            })

    return render_template(
        "quiz.html",
        topic=topic,
        current_user=username,
        results=results,
        score=score
    )

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

@app.route("/benchmark/<username>")
def benchmark(username):
    user_id = get_user_id(username)
    if not user_id:
        return redirect(url_for("index"))
    return render_template("benchmark.html", username=username)

# ---------------- RUN ----------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)

