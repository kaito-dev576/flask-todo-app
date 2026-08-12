import unittest
from pathlib import Path

from werkzeug.security import generate_password_hash

import database
from app import create_app


class TodoAppTestCase(unittest.TestCase):
    def setUp(self):
        self.original_database = database.DATABASE_NAME
        self.database_path = Path(__file__).parent / "test-runtime.db"
        self.database_path.unlink(missing_ok=True)
        database.DATABASE_NAME = str(self.database_path)
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-key"})
        self.client = self.app.test_client()

        database.create_user("testuser", generate_password_hash("testpass123"))
        database.create_user("otheruser", generate_password_hash("otherpass123"))
        self.user = database.get_user_by_username("testuser")
        self.other = database.get_user_by_username("otheruser")
        self.login(self.user)

    def tearDown(self):
        database.DATABASE_NAME = self.original_database
        self.database_path.unlink(missing_ok=True)

    def login(self, user):
        with self.client.session_transaction() as user_session:
            user_session.clear()
            user_session.update(user_id=user["id"], username=user["username"])

    def create_task(
        self,
        user=None,
        name="テスト用タスク",
        priority="中",
        deadline="2026-08-31",
    ):
        user = user or self.user
        category = database.get_categories()[0]
        task_id = database.create_task(
            name, priority, deadline, category["id"], user["id"]
        )
        return database.get_task(task_id, user["id"])

    def test_login_is_required(self):
        with self.client.session_transaction() as user_session:
            user_session.clear()
        response = self.client.get("/", follow_redirects=True)
        self.assertIn("続けるにはログインしてください".encode(), response.data)
        self.assertIn("今日やることを確認して".encode(), response.data)

    def test_register_login_and_logout(self):
        with self.client.session_transaction() as user_session:
            user_session.clear()

        response = self.client.post(
            "/register",
            data={"username": "newuser", "password": "newpass123"},
            follow_redirects=True,
        )
        self.assertIn("アカウントを作成しました".encode(), response.data)

        response = self.client.post(
            "/login",
            data={"username": "newuser", "password": "newpass123"},
            follow_redirects=True,
        )
        self.assertIn("おかえりなさい".encode(), response.data)
        self.assertIn("すべてのタスク".encode(), response.data)

        response = self.client.post("/logout", follow_redirects=True)
        self.assertIn("ログアウトしました".encode(), response.data)

    def test_duplicate_username_is_rejected(self):
        with self.client.session_transaction() as user_session:
            user_session.clear()
        response = self.client.post(
            "/register",
            data={"username": "testuser", "password": "testpass123"},
            follow_redirects=True,
        )
        self.assertIn("すでに使用されています".encode(), response.data)

    def test_wrong_password_is_rejected(self):
        with self.client.session_transaction() as user_session:
            user_session.clear()
        response = self.client.post(
            "/login",
            data={"username": "testuser", "password": "wrongpass"},
            follow_redirects=True,
        )
        self.assertIn("パスワードが違います".encode(), response.data)

    def test_task_crud(self):
        category = database.get_categories()[0]
        self.client.post(
            "/add",
            data={
                "name": "作品を仕上げる",
                "priority": "高",
                "deadline": "2026-09-01",
                "category_id": category["id"],
            },
        )
        task = database.get_tasks(self.user["id"])[0]

        self.client.post(
            f"/edit/{task['id']}",
            data={
                "name": "READMEを仕上げる",
                "priority": "中",
                "deadline": "2026-09-02",
                "category_id": category["id"],
            },
        )
        self.assertEqual(
            database.get_task(task["id"], self.user["id"])["name"],
            "READMEを仕上げる",
        )

        self.client.post(f"/complete/{task['id']}")
        self.assertEqual(database.get_task(task["id"], self.user["id"])["done"], 1)
        self.client.post(f"/complete/{task['id']}")
        self.assertEqual(database.get_task(task["id"], self.user["id"])["done"], 0)

        self.client.post(f"/delete/{task['id']}")
        self.assertIsNone(database.get_task(task["id"], self.user["id"]))

    def test_quick_add_uses_default_priority(self):
        category = database.get_categories()[0]
        self.client.post(
            "/add",
            data={
                "name": "優先度なしで追加",
                "deadline": "2026-09-01",
                "category_id": category["id"],
            },
        )
        task = database.get_tasks(self.user["id"])[0]
        self.assertEqual(task["priority"], "中")
        self.assertEqual(
            [category["name"] for category in database.get_categories()],
            ["勉強", "運動", "生活"],
        )

    def test_invalid_task_values_are_rejected(self):
        category = database.get_categories()[0]
        cases = [
            {"name": " ", "priority": "中", "deadline": "2026-09-01", "category_id": category["id"]},
            {"name": "x", "priority": "最優先", "deadline": "2026-09-01", "category_id": category["id"]},
            {"name": "x", "priority": "中", "deadline": "invalid", "category_id": category["id"]},
            {"name": "x", "priority": "中", "deadline": "2026-09-01", "category_id": 99999},
        ]
        for data in cases:
            self.client.post("/add", data=data)
        self.assertEqual(len(database.get_tasks(self.user["id"])), 0)

    def test_search_filter_and_sort(self):
        first = self.create_task(name="Pythonを学ぶ", priority="低")
        second = self.create_task(name="面接資料を作る", priority="高")
        database.complete_task(first["id"], self.user["id"])

        self.assertIn("Pythonを学ぶ".encode(), self.client.get("/?q=Python").data)
        completed = self.client.get("/?status=completed").data
        self.assertIn("Pythonを学ぶ".encode(), completed)
        self.assertNotIn("面接資料を作る".encode(), completed)

        tasks = database.get_tasks(self.user["id"], sort="priority")
        self.assertEqual(tasks[0]["id"], second["id"])

    def test_stats_include_due_today_and_overdue(self):
        self.create_task(name="今日のタスク", deadline="2026-08-11")
        self.create_task(name="期限切れタスク", deadline="2026-08-10")
        done = self.create_task(name="完了済み", deadline="2026-08-09")
        database.complete_task(done["id"], self.user["id"])

        stats = database.get_task_stats("2026-08-11", self.user["id"])
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["due_today"], 1)
        self.assertEqual(stats["overdue"], 1)
        self.assertEqual(stats["completed"], 1)

    def test_today_upcoming_and_completed_views(self):
        overdue = self.create_task(name="期限切れ", deadline="2026-08-10")
        today = self.create_task(name="今日", deadline="2026-08-11")
        upcoming = self.create_task(name="予定", deadline="2026-08-12")
        done = self.create_task(name="完了済み", deadline="2026-08-11")
        database.complete_task(done["id"], self.user["id"])

        today_tasks = database.get_tasks(
            self.user["id"], view="today", today="2026-08-11"
        )
        self.assertEqual(
            {task["id"] for task in today_tasks},
            {overdue["id"], today["id"], done["id"]},
        )

        upcoming_tasks = database.get_tasks(
            self.user["id"], view="upcoming", today="2026-08-11"
        )
        self.assertEqual([task["id"] for task in upcoming_tasks], [upcoming["id"]])

        completed_tasks = database.get_tasks(self.user["id"], view="completed")
        self.assertEqual([task["id"] for task in completed_tasks], [done["id"]])

    def test_other_users_data_is_isolated(self):
        own = self.create_task(name="自分のタスク")
        other = self.create_task(self.other, "他人のタスク")

        response = self.client.get("/")
        self.assertIn("自分のタスク".encode(), response.data)
        self.assertNotIn("他人のタスク".encode(), response.data)
        self.assertEqual(self.client.post(f"/delete/{other['id']}").status_code, 404)
        self.assertEqual(self.client.post(f"/complete/{other['id']}").status_code, 404)
        self.assertIsNotNone(database.get_task(other["id"], self.other["id"]))

    def test_unsafe_return_url_is_not_used(self):
        task = self.create_task()
        response = self.client.post(
            f"/complete/{task['id']}",
            data={"return_to": "https://example.com"},
        )
        self.assertEqual(response.headers["Location"], "/")

    def test_csrf_protection_rejects_missing_token(self):
        self.app.config["TESTING"] = False
        try:
            response = self.client.post("/logout")
        finally:
            self.app.config["TESTING"] = True
        self.assertEqual(response.status_code, 400)
        self.assertIn("不正なリクエスト".encode(), response.data)

    def test_security_headers_are_set(self):
        response = self.client.get("/")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])

    def test_user_content_is_escaped(self):
        self.create_task(name='<script>alert("xss")</script>')
        response = self.client.get("/")
        self.assertNotIn(b"<script>alert", response.data)
        self.assertIn(b"&lt;script&gt;", response.data)

    def test_unknown_task_returns_custom_404(self):
        response = self.client.get("/edit/99999")
        self.assertEqual(response.status_code, 404)
        self.assertIn("ページが見つかりません".encode(), response.data)

    def test_health_check(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
