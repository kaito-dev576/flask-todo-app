import os
import sqlite3
from contextlib import contextmanager


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_NAME = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "todo.db"))


@contextmanager
def connect():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_db():
    with connect() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                priority TEXT NOT NULL CHECK (priority IN ('高', '中', '低')),
                deadline TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
                category_id INTEGER NOT NULL REFERENCES categories(id),
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_user_deadline
                ON tasks(user_id, done, deadline);
        """)
        connection.executemany(
            "INSERT OR IGNORE INTO categories (name) VALUES (?)",
            [("勉強",), ("運動",), ("生活",)],
        )
        for old_name, new_name in (("仕事", "勉強"), ("学習", "運動")):
            old_category = connection.execute(
                "SELECT id FROM categories WHERE name = ?", (old_name,)
            ).fetchone()
            new_category = connection.execute(
                "SELECT id FROM categories WHERE name = ?", (new_name,)
            ).fetchone()
            if old_category and new_category:
                connection.execute(
                    "UPDATE tasks SET category_id = ? WHERE category_id = ?",
                    (new_category["id"], old_category["id"]),
                )
                connection.execute(
                    "DELETE FROM categories WHERE id = ?", (old_category["id"],)
                )


def create_user(username, password_hash):
    with connect() as connection:
        return connection.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        ).lastrowid


def get_user_by_username(username):
    with connect() as connection:
        return connection.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()


def get_categories():
    with connect() as connection:
        return connection.execute(
            """SELECT * FROM categories
               ORDER BY CASE name
                   WHEN '勉強' THEN 1
                   WHEN '運動' THEN 2
                   WHEN '生活' THEN 3
                   ELSE 4
               END, id"""
        ).fetchall()


def category_exists(category_id):
    with connect() as connection:
        return connection.execute(
            "SELECT 1 FROM categories WHERE id = ?", (category_id,)
        ).fetchone() is not None


def create_task(name, priority, deadline, category_id, user_id):
    with connect() as connection:
        return connection.execute(
            """INSERT INTO tasks (name, priority, deadline, category_id, user_id)
               VALUES (?, ?, ?, ?, ?)""",
            (name, priority, deadline, category_id, user_id),
        ).lastrowid


def get_tasks(
    user_id,
    keyword="",
    category_id=None,
    status="all",
    sort="deadline",
    view="all",
    today=None,
):
    query = """
        SELECT tasks.*, categories.name AS category_name
        FROM tasks
        JOIN categories ON categories.id = tasks.category_id
        WHERE tasks.user_id = ? AND tasks.name LIKE ?
    """
    parameters = [user_id, f"%{keyword}%"]
    if category_id is not None:
        query += " AND tasks.category_id = ?"
        parameters.append(category_id)
    if view == "today" and today:
        query += " AND tasks.deadline <= ?"
        parameters.append(today)
    elif view == "upcoming" and today:
        query += " AND tasks.done = 0 AND tasks.deadline > ?"
        parameters.append(today)
    elif view == "completed":
        query += " AND tasks.done = 1"
    elif status == "pending":
        query += " AND tasks.done = 0"
    elif status == "completed":
        query += " AND tasks.done = 1"

    order = {
        "deadline": "tasks.done, tasks.deadline, tasks.id DESC",
        "priority": (
            "tasks.done, CASE tasks.priority "
            "WHEN '高' THEN 1 WHEN '中' THEN 2 ELSE 3 END, tasks.deadline"
        ),
        "newest": "tasks.done, tasks.id DESC",
    }.get(sort, "tasks.done, tasks.deadline, tasks.id DESC")

    with connect() as connection:
        return connection.execute(f"{query} ORDER BY {order}", parameters).fetchall()


def get_task(task_id, user_id):
    with connect() as connection:
        return connection.execute(
            "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, user_id),
        ).fetchone()


def complete_task(task_id, user_id):
    with connect() as connection:
        cursor = connection.execute(
            """UPDATE tasks
               SET done = CASE done WHEN 1 THEN 0 ELSE 1 END
               WHERE id = ? AND user_id = ?""",
            (task_id, user_id),
        )
        return cursor.rowcount == 1


def update_task(task_id, name, priority, deadline, category_id, user_id):
    with connect() as connection:
        cursor = connection.execute(
            """UPDATE tasks
               SET name = ?, priority = ?, deadline = ?, category_id = ?
               WHERE id = ? AND user_id = ?""",
            (name, priority, deadline, category_id, task_id, user_id),
        )
        return cursor.rowcount == 1


def delete_task(task_id, user_id):
    with connect() as connection:
        cursor = connection.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)
        )
        return cursor.rowcount == 1


def get_task_stats(today, user_id):
    with connect() as connection:
        return connection.execute(
            """
            SELECT COUNT(*) AS total,
                   COALESCE(SUM(CASE WHEN done = 0 THEN 1 ELSE 0 END), 0) AS pending,
                   COALESCE(SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END), 0) AS completed,
                   COALESCE(SUM(CASE WHEN done = 0 AND deadline = ? THEN 1 ELSE 0 END), 0) AS due_today,
                   COALESCE(SUM(CASE WHEN done = 0 AND deadline < ? THEN 1 ELSE 0 END), 0) AS overdue
            FROM tasks
            WHERE user_id = ?
            """,
            (today, today, user_id),
        ).fetchone()
