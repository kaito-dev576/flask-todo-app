import tempfile
import unittest
from pathlib import Path

import database
from app import app


class TodoAppTestCase(unittest.TestCase):
    def setUp(self):
        self.original_database_name = database.DATABASE_NAME
        #テスト中だけ使用する一時フォルダを作ります
        self.temporary_directory = tempfile.TemporaryDirectory()

        #通常の todo.dbではなく、一時的な test.dbを使用するよう変更
        database.DATABASE_NAME = str(
            Path(self.temporary_directory.name) / "test.db"
        )

        #一時データベースに tasksテーブルを作ります
        database.init_db()

        #Flaskをテストモードにします
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"

        #ブラウザの代わりにページを操作するテスト用クライアント
        self.client = app.test_client()

    def tearDown(self):
        database.DATABASE_NAME = self.original_database_name
        self.temporary_directory.cleanup()

    def test_index_page_is_displayed(self):
        #トップページへGETアクセス
        response = self.client.get("/")

        #正常であることを確認
        self.assertEqual(response.status_code, 200)
        #返されたHTML内に Todo Appという文字が含まれているか確認
        self.assertIn(
            "Todo App".encode("utf-8"),
            response.data,
        )

    def test_task_can_be_added(self):
        #テスト用データベースから最初のカテゴリを取得
        categories = database.get_categories()
        category = categories[0]

        response = self.client.post(
            "/add",
            data={
                "name": "テスト用タスク",
                "priority": "高",
                "deadline": "2026-08-31",
                "category_id": str(category["id"]),
            },
            follow_redirects=True,
        )

        tasks = database.get_tasks()
        added_task = tasks[0]

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "テスト用タスク".encode("utf-8"),
            response.data,
        )
        self.assertEqual(
            added_task["category_id"],
            category["id"],
        )
        #選択したカテゴリ名が正しく取得できるか確認
        self.assertEqual(
            added_task["category_name"],
            category["name"],
        )

    #タスクを作成し、完了URLへPOST送信したあと、doneが 1になったか確認
    def test_task_can_be_completed(self):
        database.create_task(
            "完了テスト",
            "中",
            "2026-08-31",
        )
        task = database.get_tasks()[0]

        response = self.client.post(
            f"/complete/{task['id']}",
            follow_redirects=True,
        )

        updated_task = database.get_task(task["id"])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(updated_task["done"], 1)


    def test_task_can_be_edited(self):
        categories = database.get_categories()
        category = categories[1]

        database.create_task(
            "編集前",
            "低",
            "2026-08-31",
        )
        task = database.get_tasks()[0]

        response = self.client.post(
            f"/edit/{task['id']}",
            data={
                "name": "編集後",
                "priority": "高",
                "deadline": "2026-09-01",
                "category_id": str(category["id"]),
            },
            follow_redirects=True,
        )

        updated_task = database.get_task(task["id"])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(updated_task["name"], "編集後")
        self.assertEqual(updated_task["priority"], "高")
        self.assertEqual(
            updated_task["deadline"],
            "2026-09-01",
        )
        self.assertEqual(
            updated_task["category_id"],
            category["id"],
        )


    #削除後の取得結果が Noneになることを確認
    def test_task_can_be_deleted(self):
        database.create_task(
            "削除テスト",
            "低",
            "2026-08-31",
        )
        task = database.get_tasks()[0]

        response = self.client.post(
            f"/delete/{task['id']}",
            follow_redirects=True,
        )

        deleted_task = database.get_task(task["id"])

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(deleted_task)


    #検索結果に一致するタスクだけが表示されることを確認
    def test_tasks_can_be_searched(self):
        database.create_task(
            "Pythonを勉強する",
            "高",
            "2026-08-31",
        )
        database.create_task(
            "買い物へ行く",
            "低",
            "2026-08-31",
        )

        response = self.client.get("/?q=Python")

        self.assertIn(
            "Pythonを勉強する".encode("utf-8"),
            response.data,
        )
        self.assertNotIn(
            "買い物へ行く".encode("utf-8"),
            response.data,
        )


    #空白だけのタスクが保存されないことを確認
    def test_blank_task_name_is_rejected(self):
        response = self.client.post(
            "/add",
            data={
                "name": "   ",
                "priority": "高",
                "deadline": "2026-08-31",
            },
            follow_redirects=True,
        )

        self.assertIn(
            "タスク名を入力してください。".encode("utf-8"),
            response.data,
        )
        self.assertEqual(len(database.get_tasks()), 0)


    def test_tasks_can_be_filtered_by_category(self):
        categories = database.get_categories()
        work_category = categories[0]
        study_category = categories[1]

        database.create_task(
            "会議の準備",
            "高",
            "2026-08-31",
            work_category["id"],
        )

        database.create_task(
            "Pythonを勉強する",
            "中",
            "2026-08-31",
            study_category["id"],
        )

        response = self.client.get(
            f"/?category_id={study_category['id']}"
        )

        self.assertIn(
            "Pythonを勉強する".encode("utf-8"),
            response.data,
        )
        self.assertNotIn(
            "会議の準備".encode("utf-8"),
            response.data,
        )


if __name__ == "__main__":
    unittest.main()