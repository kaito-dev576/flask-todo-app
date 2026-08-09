import unittest
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

import database
from app import app


class TodoAppTestCase(unittest.TestCase):
    def setUp(self):
        self.original_database_name = database.DATABASE_NAME
        self.database_path = Path(__file__).parent / "test.db"
        self.database_path.unlink(missing_ok=True)
        database.DATABASE_NAME = str(self.database_path)
        database.init_db()

        app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret-key",
        )
        self.client = app.test_client()

        database.create_user(
            "testuser",
            generate_password_hash("testpass123"),
        )
        database.create_user(
            "otheruser",
            generate_password_hash("otherpass123"),
        )
        self.user = database.get_user_by_username("testuser")
        self.other_user = database.get_user_by_username("otheruser")
        self.login_as(self.user)

    def tearDown(self):
        database.DATABASE_NAME = self.original_database_name
        self.database_path.unlink(missing_ok=True)

    def login_as(self, user):
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]

    def logout_for_test(self):
        with self.client.session_transaction() as session:
            session.clear()

    def create_task_for(self, user_id, name="テスト用タスク"):
        category = database.get_categories()[0]
        database.create_task(
            name,
            "中",
            "2026-08-31",
            category["id"],
            user_id,
        )
        return database.get_tasks(user_id)[0]

    def test_login_is_required_for_index(self):
        self.logout_for_test()
        response = self.client.get("/", follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("ログインしてください。".encode(), response.data)

    def test_user_can_be_registered(self):
        self.logout_for_test()
        response = self.client.post(
            "/register",
            data={
                "username": "newuser",
                "password": "newpass123",
            },
            follow_redirects=True,
        )

        user = database.get_user_by_username("newuser")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(user)
        self.assertNotEqual(user["password_hash"], "newpass123")
        self.assertTrue(
            check_password_hash(user["password_hash"], "newpass123")
        )
        self.assertIn("ユーザー登録が完了しました。".encode(), response.data)

    def test_user_can_log_in_and_log_out(self):
        self.logout_for_test()
        response = self.client.post(
            "/login",
            data={
                "username": "testuser",
                "password": "testpass123",
            },
            follow_redirects=True,
        )

        self.assertIn("ログインしました。".encode(), response.data)
        with self.client.session_transaction() as session:
            self.assertEqual(session["user_id"], self.user["id"])

        response = self.client.post("/logout", follow_redirects=True)
        self.assertIn("ログアウトしました。".encode(), response.data)
        with self.client.session_transaction() as session:
            self.assertNotIn("user_id", session)

    def test_wrong_password_is_rejected(self):
        self.logout_for_test()
        response = self.client.post(
            "/login",
            data={
                "username": "testuser",
                "password": "wrong-password",
            },
            follow_redirects=True,
        )

        self.assertIn(
            "ユーザー名またはパスワードが違います。".encode(),
            response.data,
        )

    def test_index_page_is_displayed(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Todo App".encode(), response.data)

    def test_task_can_be_added(self):
        category = database.get_categories()[0]
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

        tasks = database.get_tasks(self.user["id"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["user_id"], self.user["id"])
        self.assertEqual(tasks[0]["category_name"], category["name"])

    def test_task_can_be_completed(self):
        task = self.create_task_for(self.user["id"])
        self.client.post(f"/complete/{task['id']}")

        updated_task = database.get_task(task["id"], self.user["id"])
        self.assertEqual(updated_task["done"], 1)

    def test_task_can_be_edited(self):
        task = self.create_task_for(self.user["id"])
        category = database.get_categories()[1]
        self.client.post(
            f"/edit/{task['id']}",
            data={
                "name": "編集後",
                "priority": "高",
                "deadline": "2026-09-01",
                "category_id": str(category["id"]),
            },
        )

        updated_task = database.get_task(task["id"], self.user["id"])
        self.assertEqual(updated_task["name"], "編集後")
        self.assertEqual(updated_task["category_id"], category["id"])

    def test_task_can_be_deleted(self):
        task = self.create_task_for(self.user["id"])
        self.client.post(f"/delete/{task['id']}")

        deleted_task = database.get_task(task["id"], self.user["id"])
        self.assertIsNone(deleted_task)

    def test_tasks_can_be_searched(self):
        self.create_task_for(self.user["id"], "Pythonを勉強する")
        self.create_task_for(self.user["id"], "買い物へ行く")
        response = self.client.get("/?q=Python")

        self.assertIn("Pythonを勉強する".encode(), response.data)
        self.assertNotIn("買い物へ行く".encode(), response.data)

    def test_blank_task_name_is_rejected(self):
        category = database.get_categories()[0]
        response = self.client.post(
            "/add",
            data={
                "name": "   ",
                "priority": "高",
                "deadline": "2026-08-31",
                "category_id": str(category["id"]),
            },
            follow_redirects=True,
        )

        self.assertIn("タスク名を入力してください。".encode(), response.data)
        self.assertEqual(len(database.get_tasks(self.user["id"])), 0)

    def test_tasks_can_be_filtered_by_category(self):
        categories = database.get_categories()
        work_category = categories[0]
        study_category = categories[1]
        database.create_task(
            "会議の準備",
            "高",
            "2026-08-31",
            work_category["id"],
            self.user["id"],
        )
        database.create_task(
            "Pythonを勉強する",
            "中",
            "2026-08-31",
            study_category["id"],
            self.user["id"],
        )

        response = self.client.get(
            f"/?category_id={study_category['id']}"
        )
        self.assertIn("Pythonを勉強する".encode(), response.data)
        self.assertNotIn("会議の準備".encode(), response.data)

    def test_other_users_tasks_are_not_visible(self):
        self.create_task_for(self.user["id"], "自分のタスク")
        self.create_task_for(self.other_user["id"], "他人の秘密タスク")

        response = self.client.get("/")
        self.assertIn("自分のタスク".encode(), response.data)
        self.assertNotIn("他人の秘密タスク".encode(), response.data)

    def test_other_users_task_cannot_be_changed(self):
        task = self.create_task_for(
            self.other_user["id"],
            "他人のタスク",
        )
        category = database.get_categories()[0]

        self.client.post(f"/complete/{task['id']}")
        self.client.post(f"/delete/{task['id']}")
        self.client.post(
            f"/edit/{task['id']}",
            data={
                "name": "不正な変更",
                "priority": "高",
                "deadline": "2026-09-01",
                "category_id": str(category["id"]),
            },
        )

        unchanged_task = database.get_task(
            task["id"],
            self.other_user["id"],
        )
        self.assertIsNotNone(unchanged_task)
        self.assertEqual(unchanged_task["name"], "他人のタスク")
        self.assertEqual(unchanged_task["done"], 0)


if __name__ == "__main__":
    unittest.main()
