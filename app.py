from datetime import date, datetime, timedelta
from functools import wraps
import os
import secrets

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database import (
    category_exists,
    complete_task,
    create_task,
    create_user,
    delete_task,
    get_categories,
    get_task,
    get_task_stats,
    get_tasks,
    get_user_by_username,
    init_db,
    update_task,
)


WEEKDAYS = "月火水木金土日"


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", secrets.token_hex(32)),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        MAX_CONTENT_LENGTH=1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    init_db()

    if os.environ.get("DEMO_MODE") == "1":
        demo_username = os.environ.get("DEMO_USERNAME", "demo_user")
        demo_password = os.environ.get("DEMO_PASSWORD", "portfolio123")
        demo_user = get_user_by_username(demo_username)
        if demo_user is None:
            user_id = create_user(
                demo_username, generate_password_hash(demo_password)
            )
            categories = {category["name"]: category["id"] for category in get_categories()}
            demo_tasks = (
                ("ポートフォリオを確認する", date.today(), "勉強"),
                ("30分ランニングする", date.today() + timedelta(days=1), "運動"),
                ("部屋を整理する", date.today() + timedelta(days=2), "生活"),
            )
            for name, deadline, category_name in demo_tasks:
                create_task(
                    name,
                    "中",
                    deadline.isoformat(),
                    categories[category_name],
                    user_id,
                )

    @app.before_request
    def prepare_request():
        if request.method == "POST" and not app.config["TESTING"]:
            token = request.form.get("csrf_token", "")
            stored_token = session.get("csrf_token", "")
            if not token or not stored_token or not secrets.compare_digest(token, stored_token):
                abort(400, "不正なリクエストです。ページを再読み込みしてお試しください。")

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
        )
        return response

    @app.context_processor
    def inject_global_values():
        session.setdefault("csrf_token", secrets.token_hex(32))
        return {"csrf_token": session["csrf_token"]}

    @app.template_filter("display_date")
    def display_date(value):
        try:
            parsed = date.fromisoformat(value)
        except (TypeError, ValueError):
            return value
        return f"{parsed.month}月{parsed.day}日（{WEEKDAYS[parsed.weekday()]}）"

    def login_required(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if "user_id" not in session:
                flash("続けるにはログインしてください。", "info")
                return redirect(url_for("login"))
            return view(*args, **kwargs)

        return wrapped_view

    def validate_task_form():
        name = request.form.get("name", "").strip()
        priority = request.form.get("priority", "中")
        deadline = request.form.get("deadline", "")
        category_id = request.form.get("category_id", type=int)
        if not name:
            return None, "タスク名を入力してください。"
        if len(name) > 100:
            return None, "タスク名は100文字以内で入力してください。"
        if priority not in {"高", "中", "低"}:
            return None, "優先度を選択してください。"
        if category_id is None or not category_exists(category_id):
            return None, "カテゴリを選択してください。"
        try:
            date.fromisoformat(deadline)
        except ValueError:
            return None, "正しい期限を入力してください。"
        return (name, priority, deadline, category_id), None

    def safe_return_url(default_endpoint="index"):
        target = request.form.get("return_to", "")
        if target.startswith("/") and not target.startswith("//"):
            return target
        return url_for(default_endpoint)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if "user_id" in session:
            return redirect(url_for("index"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            if not 3 <= len(username) <= 50:
                flash("ユーザー名は3〜50文字で入力してください。", "error")
            elif not 8 <= len(password) <= 128:
                flash("パスワードは8〜128文字で入力してください。", "error")
            elif get_user_by_username(username):
                flash("そのユーザー名はすでに使用されています。", "error")
            else:
                create_user(username, generate_password_hash(password))
                flash("アカウントを作成しました。ログインしてください。", "success")
                return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if "user_id" in session:
            return redirect(url_for("index"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            user = get_user_by_username(username)
            password = request.form.get("password", "")
            if user is None or not check_password_hash(user["password_hash"], password):
                flash("ユーザー名またはパスワードが違います。", "error")
            else:
                session.clear()
                session.permanent = True
                session.update(user_id=user["id"], username=user["username"])
                flash("おかえりなさい。今日のタスクを整理しましょう。", "success")
                return redirect(url_for("index"))
        return render_template("login.html")

    @app.post("/logout")
    @login_required
    def logout():
        session.clear()
        flash("ログアウトしました。", "info")
        return redirect(url_for("login"))

    @app.get("/")
    @login_required
    def index():
        keyword = request.args.get("q", "").strip()
        category_id = request.args.get("category_id", type=int)
        status = request.args.get("status", "all")
        sort = request.args.get("sort", "deadline")
        view = request.args.get("view", "all")
        status = status if status in {"all", "pending", "completed"} else "all"
        sort = sort if sort in {"deadline", "priority", "newest"} else "deadline"
        view = view if view in {"today", "upcoming", "all", "completed"} else "all"

        current_date = date.today()
        current_hour = datetime.now().hour
        greeting = "おはようございます" if current_hour < 11 else "こんにちは" if current_hour < 18 else "おつかれさまです"
        today = current_date.isoformat()
        stats = get_task_stats(today, session["user_id"])
        total = stats["total"] or 0
        completed = stats["completed"] or 0
        completion_rate = round(completed / total * 100) if total else 0
        has_filters = bool(keyword or category_id or view != "all" or sort != "deadline")
        tasks = get_tasks(
            session["user_id"], keyword, category_id, status, sort, view, today
        )

        task_groups = []
        if view == "all":
            groups = (
                ("期限切れ", [task for task in tasks if not task["done"] and task["deadline"] < today]),
                ("今日", [task for task in tasks if not task["done"] and task["deadline"] == today]),
                ("予定", [task for task in tasks if not task["done"] and task["deadline"] > today]),
                ("完了", [task for task in tasks if task["done"]]),
            )
            task_groups = [(label, items) for label, items in groups if items]
        else:
            task_groups = [({"today": "今日", "upcoming": "予定", "completed": "完了"}[view], tasks)] if tasks else []

        return render_template(
            "index.html",
            tasks=tasks,
            task_groups=task_groups,
            categories=get_categories(),
            keyword=keyword,
            selected_category_id=category_id,
            selected_status=status,
            selected_sort=sort,
            selected_view=view,
            today=today,
            greeting=greeting,
            today_label=f"{current_date.year}年{current_date.month}月{current_date.day}日（{WEEKDAYS[current_date.weekday()]}）",
            stats=stats,
            completion_rate=completion_rate,
            has_filters=has_filters,
            navigation_counts={
                "today": stats["due_today"] + stats["overdue"],
                "upcoming": max(stats["pending"] - stats["due_today"] - stats["overdue"], 0),
                "all": stats["total"],
                "completed": stats["completed"],
            },
            view_title={"today": "今日", "upcoming": "予定", "all": "すべてのタスク", "completed": "完了"}[view],
        )

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.post("/add")
    @login_required
    def add_task_route():
        values, error = validate_task_form()
        if error:
            flash(error, "error")
        else:
            create_task(*values, session["user_id"])
            flash("タスクを追加しました。", "success")
        return redirect(safe_return_url())

    @app.post("/complete/<int:task_id>")
    @login_required
    def complete_task_route(task_id):
        if not complete_task(task_id, session["user_id"]):
            abort(404)
        flash("タスクの状態を更新しました。", "success")
        return redirect(safe_return_url())

    @app.post("/delete/<int:task_id>")
    @login_required
    def delete_task_route(task_id):
        if not delete_task(task_id, session["user_id"]):
            abort(404)
        flash("タスクを削除しました。", "success")
        return redirect(safe_return_url())

    @app.route("/edit/<int:task_id>", methods=["GET", "POST"])
    @login_required
    def edit_task_route(task_id):
        task = get_task(task_id, session["user_id"])
        if task is None:
            abort(404)
        if request.method == "POST":
            values, error = validate_task_form()
            if error:
                flash(error, "error")
            else:
                update_task(task_id, *values, session["user_id"])
                flash("タスクを更新しました。", "success")
                return redirect(safe_return_url())
        return render_template("edit.html", task=task, categories=get_categories())

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="ページが見つかりません"), 404

    @app.errorhandler(400)
    def bad_request(error):
        return render_template("error.html", code=400, message=error.description), 400

    @app.errorhandler(413)
    def request_too_large(_error):
        return render_template("error.html", code=413, message="送信内容が大きすぎます"), 413

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
