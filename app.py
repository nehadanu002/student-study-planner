
from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import date, timedelta
import os

app = Flask(__name__)

# Database configuration
DATABASE = os.path.join(os.path.dirname(__file__), "study_planner.db")


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subject TEXT NOT NULL,
            due_date TEXT NOT NULL,
            priority TEXT NOT NULL,
            completed INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


# Initialize database when the application starts
init_db()


@app.route("/")
def home():
    search = request.args.get("search", "").strip()
    subject = request.args.get("subject", "").strip()
    priority = request.args.get("priority", "").strip()
    status = request.args.get("status", "all")

    conn = get_db()

    # Search and filter tasks
    tasks = conn.execute("""
        SELECT * FROM tasks
        WHERE title LIKE ?
        AND subject LIKE ?
        AND (? = '' OR priority = ?)
        AND (
            ? = 'all'
            OR (? = 'pending' AND completed = 0)
            OR (? = 'completed' AND completed = 1)
        )
        ORDER BY completed ASC, due_date ASC
    """, (
        f"%{search}%",
        f"%{subject}%",
        priority,
        priority,
        status,
        status,
        status
    )).fetchall()

    # Dashboard statistics
    all_tasks = conn.execute(
        "SELECT * FROM tasks"
    ).fetchall()

    total = len(all_tasks)
    completed = sum(task["completed"] for task in all_tasks)
    pending = total - completed

    progress = round((completed / total) * 100) if total else 0

    today = date.today()
    next_week = today + timedelta(days=7)

    # Overdue tasks
    overdue_count = sum(
        1 for task in all_tasks
        if not task["completed"]
        and task["due_date"] < today.isoformat()
    )

    # Upcoming deadlines
    upcoming_tasks = [
        task for task in all_tasks
        if not task["completed"]
        and today.isoformat() <= task["due_date"]
        <= next_week.isoformat()
    ]

    # Available subjects
    subjects = conn.execute("""
        SELECT DISTINCT subject
        FROM tasks
        ORDER BY subject
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        tasks=tasks,
        total=total,
        completed=completed,
        pending=pending,
        progress=progress,
        overdue_count=overdue_count,
        upcoming_tasks=upcoming_tasks,
        today=today.isoformat(),
        search=search,
        subjects=subjects,
        selected_subject=subject,
        selected_priority=priority,
        selected_status=status
    )


# Add a task
@app.route("/add", methods=["POST"])
def add_task():
    title = request.form.get("title", "").strip()
    subject = request.form.get("subject", "").strip()
    due_date = request.form.get("due_date", "")
    priority = request.form.get("priority", "Medium")

    if (
        title and subject and due_date
        and priority in ["Low", "Medium", "High"]
    ):
        conn = get_db()

        conn.execute("""
            INSERT INTO tasks (title, subject, due_date, priority)
            VALUES (?, ?, ?, ?)
        """, (title, subject, due_date, priority))

        conn.commit()
        conn.close()

    return redirect(url_for("home"))


# Mark a task complete or pending
@app.route("/complete/<int:task_id>", methods=["POST"])
def complete_task(task_id):
    conn = get_db()

    conn.execute("""
        UPDATE tasks
        SET completed = CASE
            WHEN completed = 0 THEN 1
            ELSE 0
        END
        WHERE id = ?
    """, (task_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("home"))


# Delete a task
@app.route("/delete/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    conn = get_db()

    conn.execute(
        "DELETE FROM tasks WHERE id = ?",
        (task_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("home"))


# Edit a task
@app.route("/edit/<int:task_id>", methods=["GET", "POST"])
def edit_task(task_id):
    conn = get_db()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        subject = request.form.get("subject", "").strip()
        due_date = request.form.get("due_date", "")
        priority = request.form.get("priority", "Medium")

        if (
            title and subject and due_date
            and priority in ["Low", "Medium", "High"]
        ):
            conn.execute("""
                UPDATE tasks
                SET title = ?, subject = ?, due_date = ?, priority = ?
                WHERE id = ?
            """, (
                title,
                subject,
                due_date,
                priority,
                task_id
            ))

            conn.commit()
            conn.close()

            return redirect(url_for("home"))

    task = conn.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (task_id,)
    ).fetchone()

    conn.close()

    if task is None:
        return "Task not found", 404

    return render_template("edit.html", task=task)


if __name__ == "__main__":
    app.run(debug=True)
