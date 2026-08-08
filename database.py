import sqlite3


DATABASE_NAME = "todo.db"

#データベースを初期化する関数
def init_db():
    connection = sqlite3.connect(DATABASE_NAME)

    #SQL命令を送る,まだ存在しない場合だけ作る,
    #整数,重複しない識別番号,1、2、3と自動で増える
    #値なしで保存できない
    #0：未完了
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            priority TEXT NOT NULL,
            deadline TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    #変更を確定
    connection.commit()
    #接続を終了
    connection.close()


#タスクを保存する関数
def create_task(name, priority, deadline):
    connection = sqlite3.connect(DATABASE_NAME)

    #SQLiteへSQL命令
    connection.execute(
        """
        INSERT INTO tasks (name, priority, deadline)
        VALUES (?, ?, ?)
        """,
        (name, priority, deadline),
    )

    connection.commit()
    connection.close()


#保存されている全タスクを取得する関数,検索キーワードを受け取る
def get_tasks(keyword=""):
    connection = sqlite3.connect(DATABASE_NAME)
    #列名で使えるようにする
    connection.row_factory = sqlite3.Row

    if keyword:
        tasks = connection.execute(
            """
            SELECT *
            FROM tasks
            WHERE name LIKE ?
            ORDER BY done, deadline
            """,
            (f"%{keyword}%",),
        ).fetchall()
    else:

        tasks = connection.execute(
            """
            SELECT *
            FROM tasks
            ORDER BY done, deadline
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