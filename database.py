import sqlite3


DATABASE_NAME = "todo.db"

#データベースを初期化する関数
def init_db():
    connection = sqlite3.connect(DATABASE_NAME)

    #カテゴリを保存する新しい表を作ります
    #カテゴリの識別番号
    #カテゴリ名を保存
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        """
    )

    #タスクがどのカテゴリに所属するかをカテゴリIDで保存
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            priority TEXT NOT NULL,
            deadline TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            category_id INTEGER REFERENCES categories(id)
        )
        """
    )

    columns = connection.execute(
        "PRAGMA table_info(tasks)"
    ).fetchall()

    #列名だけのリストを作ります
    column_names = [
        column[1]
        for column in columns
    ]

    if "category_id" not in column_names:
        connection.execute(
            """
            ALTER TABLE tasks
            ADD COLUMN category_id INTEGER
            REFERENCES categories(id)
            """
        )

    connection.executemany(
        """
        INSERT OR IGNORE INTO categories (name)
        VALUES (?)
        """,
        [
            ("仕事",),
            ("学習",),
            ("生活",),
        ],
    )

    connection.commit()
    connection.close()


#タスクを保存する関数
def create_task(
    name,
    priority,
    deadline,
    category_id=None,
):
    connection = sqlite3.connect(DATABASE_NAME)

    connection.execute(
        """
        INSERT INTO tasks (
            name,
            priority,
            deadline,
            category_id
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            name,
            priority,
            deadline,
            category_id,
        ),
    )

    connection.commit()
    connection.close()


#保存されている全タスクを取得する関数,検索キーワードを受け取る
def get_tasks(keyword=""):
    connection = sqlite3.connect(DATABASE_NAME)
    #列名で使えるようにする
    connection.row_factory = sqlite3.Row

    #タスクとカテゴリの情報を結合
    #タスクのカテゴリIDと、カテゴリテーブルのIDが同じデータを結び付けます
    if keyword:
        tasks = connection.execute(
            """
            SELECT
                tasks.*,
                categories.name AS category_name
            FROM tasks
            LEFT JOIN categories
                ON tasks.category_id = categories.id
            WHERE tasks.name LIKE ?
            ORDER BY tasks.done, tasks.deadline
            """,
            (f"%{keyword}%",),
        ).fetchall()
    else:

        tasks = connection.execute(
            """
           SELECT
                tasks.*,
                categories.name AS category_name
            FROM tasks
            LEFT JOIN categories
                ON tasks.category_id = categories.id
            ORDER BY tasks.done, tasks.deadline
            """
        ).fetchall()

    connection.close()

    return tasks


#タスクを完了させる関数
def complete_task(task_id):
    connection = sqlite3.connect(DATABASE_NAME)

    connection.execute(
        """
        UPDATE tasks
        SET done = 1
        WHERE id = ?
        """,
        (task_id,),
    )

    connection.commit()
    connection.close()


#タスクを削除する関数
def delete_task(task_id):
    connection = sqlite3.connect(DATABASE_NAME)

    connection.execute(
        """
        DELETE FROM tasks
        WHERE id = ?
        """,
        (task_id,),
    )

    connection.commit()
    connection.close()


def get_task(task_id):
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row

    task = connection.execute(
        """
        SELECT *
        FROM tasks
        WHERE id = ?
        """,
        (task_id,),

    #該当するデータを1件だけ取得
    ).fetchone()

    connection.close()

    return task


def update_task(task_id, name, priority, deadline):
    connection = sqlite3.connect(DATABASE_NAME)

    connection.execute(
        """
        UPDATE tasks
        SET name = ?, priority = ?, deadline = ?
        WHERE id = ?
        """,
        (name, priority, deadline, task_id),
    )

    connection.commit()
    connection.close()


def get_task_stats(today):
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row

    stats = connection.execute(
        """
        SELECT
            COUNT(*) AS total,
            COUNT(
                CASE WHEN done = 0 THEN 1 END
            ) AS pending,
            COUNT(
                CASE WHEN done = 1 THEN 1 END
            ) AS completed,
            COUNT(
                CASE
                    WHEN done = 0 AND deadline < ?
                    THEN 1
                END
            ) AS overdue
        FROM tasks
        """,
        (today,),
    ).fetchone()

    connection.close()

    return stats


#categoriesテーブルの全件を取得し、ID順に返します
def get_categories():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row

    categories = connection.execute(
        """
        SELECT *
        FROM categories
        ORDER BY id
        """
    ).fetchall()

    connection.close()

    return categories