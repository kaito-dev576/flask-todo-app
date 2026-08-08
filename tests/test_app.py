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
        response = self.client.post(
            "/add",
            data={
                "name": "テスト用タスク",
                "priority": "高",
                "deadline": "2026-08-31",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "テスト用タスク".encode("utf-8"),
            response.data,
        )


if __name__ == "__main__":
    unittest.main()