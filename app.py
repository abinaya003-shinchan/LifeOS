from flask import Flask, render_template, request, jsonify
import sqlite3
import re

app = Flask(__name__)


def init_db():
    conn = sqlite3.connect("lifeos.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL DEFAULT 0,
            reminder_time TEXT DEFAULT '',
            completed INTEGER DEFAULT 0
        )
    """)

    try:
        cursor.execute("ALTER TABLE items ADD COLUMN amount REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE items ADD COLUMN reminder_time TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE items ADD COLUMN completed INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


@app.route("/", methods=["GET", "POST"])
def dashboard():
    message = ""

    if request.method == "POST":
        user_input = request.form.get("user_input", "").strip()

        if user_input:
            text = user_input.lower()
            amount = 0
            reminder_time = ""

            if (
                "₹" in user_input
                or "rs" in text
                or "spent" in text
                or "expense" in text
            ):
                category = "💰 Expense"

                match = re.search(
                    r"₹\s*(\d+(?:\.\d+)?)",
                    user_input
                )

                if not match:
                    match = re.search(
                        r"\b(?:rs\.?|rupees?)\s*(\d+(?:\.\d+)?)",
                        text
                    )

                if match:
                    amount = float(match.group(1))

            elif "remind" in text or "reminder" in text:
                category = "🔔 Reminder"

                time_match = re.search(
                    r"\b(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b",
                    text
                )

                if time_match:
                    reminder_time = time_match.group(1)

            elif (
                "buy" in text
                or "shopping" in text
                or "purchase" in text
            ):
                category = "🛒 Shopping"

            else:
                category = "✅ Task"

            conn = sqlite3.connect("lifeos.db")
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO items
                (text, category, amount, reminder_time)
                VALUES (?, ?, ?, ?)
            """, (
                user_input,
                category,
                amount,
                reminder_time
            ))

            conn.commit()
            conn.close()

            if reminder_time:
                message = (
                    f"{category} set for "
                    f"{reminder_time}: {user_input}"
                )

            elif category == "💰 Expense":
                message = (
                    f"{category} detected: "
                    f"{user_input} → ₹{amount:g}"
                )

            else:
                message = (
                    f"{category} detected: "
                    f"{user_input}"
                )

    conn = sqlite3.connect("lifeos.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM items
        WHERE category = '✅ Task'
        AND completed = 0
    """)
    task_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM items
        WHERE category = '💰 Expense'
    """)
    expense_total = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM items
        WHERE category = '🔔 Reminder'
    """)
    reminder_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM items
        WHERE category = '🛒 Shopping'
    """)
    shopping_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT text, category
        FROM items
        ORDER BY id DESC
        LIMIT 10
    """)
    activities = cursor.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        message=message,
        task_count=task_count,
        expense_count=expense_total,
        reminder_count=reminder_count,
        shopping_count=shopping_count,
        activities=activities
    )


@app.route("/tasks", methods=["GET", "POST"])
def tasks_page():
    conn = sqlite3.connect("lifeos.db")
    cursor = conn.cursor()

    if request.method == "POST":
        task_id = request.form.get("task_id")

        if task_id:
            cursor.execute("""
                UPDATE items
                SET completed = 1
                WHERE id = ?
            """, (task_id,))

            conn.commit()

    cursor.execute("""
        SELECT id, text, completed
        FROM items
        WHERE category = '✅ Task'
        ORDER BY id DESC
    """)

    tasks = cursor.fetchall()

    conn.close()

    return render_template(
        "tasks.html",
        tasks=tasks
    )


@app.route("/expenses")
def expenses_page():
    conn = sqlite3.connect("lifeos.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT text, amount
        FROM items
        WHERE category = '💰 Expense'
        ORDER BY id DESC
    """)

    expenses = cursor.fetchall()

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM items
        WHERE category = '💰 Expense'
    """)

    expense_total = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "expenses.html",
        expenses=expenses,
        expense_total=expense_total
    )


@app.route("/reminders")
def reminders_page():
    conn = sqlite3.connect("lifeos.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, text, reminder_time
        FROM items
        WHERE category = '🔔 Reminder'
        ORDER BY id DESC
    """)

    reminders = cursor.fetchall()

    conn.close()

    return render_template(
        "reminders.html",
        reminders=reminders
    )


@app.route("/api/reminders")
def reminder_api():
    conn = sqlite3.connect("lifeos.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, text, reminder_time
        FROM items
        WHERE category = '🔔 Reminder'
        AND reminder_time != ''
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    reminders = []

    for row in rows:
        reminders.append({
            "id": row[0],
            "text": row[1],
            "reminder_time": row[2]
        })

    return jsonify(reminders)


@app.route("/shopping", methods=["GET", "POST"])
def shopping_page():
    conn = sqlite3.connect("lifeos.db")
    cursor = conn.cursor()

    if request.method == "POST":
        item_id = request.form.get("item_id")

        if item_id:
            cursor.execute("""
                UPDATE items
                SET completed = 1
                WHERE id = ?
                AND category = '🛒 Shopping'
            """, (item_id,))

            conn.commit()

    cursor.execute("""
        SELECT id, text, completed
        FROM items
        WHERE category = '🛒 Shopping'
        ORDER BY id DESC
    """)

    shopping_items = cursor.fetchall()

    conn.close()

    return render_template(
        "shopping.html",
        shopping_items=shopping_items
    )


@app.route("/ai-assistant")
def ai_assistant():
    return render_template("ai_assistant.html")


# Create the database/table when Flask starts.
# This is important for Gunicorn/Render deployment.
init_db()


if __name__ == "__main__":
    app.run(debug=True)