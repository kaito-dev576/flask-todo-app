#読み込み
from flask import Flask, flash, redirect, render_template, request, session, url_for
from datetime import date
import os
from functools import wraps
from database import (
    complete_task as complete_task_in_db,
    create_task,
    delete_task as delete_task_from_db,
    get_task,
    get_tasks,
    get_task_stats,
    get_categories,
    init_db,
    update_task as update_task_in_db,
    create_user,
    get_user_by_username,
)
from werkzeug.security import check_password_hash, generate_password_hash

#Flaskアプリ本体を作成
app = Flask(__name__)

#Windowsなどに設定された SECRET_KEYを取得
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "development-secret-key",
)

#実行
init_db()


def login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("ログインしてください。")
            return redirect(url_for("login"))

        return view_function(*args, **kwargs)

    return wrapped_view


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get(
            "username",
            "",
        ).strip()

        password = request.form.get(
            "password",
            "",
        )

        if len(username) < 3:
            flash("ユーザー名は3文字以上で入力してください。")
            return redirect(url_for("register"))

        if len(username) > 50:
            flash("ユーザー名は50文字以内で入力してください。")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("パスワードは8文字以上で入力してください。")
            return redirect(url_for("register"))

        if len(password) > 128:
            flash("パスワードは128文字以内で入力してください。")
            return redirect(url_for("register"))

        existing_user = get_user_by_username(username)

        if existing_user is not None:
            flash("そのユーザー名はすでに使われています。")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)

        create_user(
            username,
            password_hash,
        )

        flash("ユーザー登録が完了しました。")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get(
            "username",
            "",
        ).strip()

        password = request.form.get(
            "password",
            "",
        )

        user = get_user_by_username(username)

        if user is None or not check_password_hash(
            user["password_hash"],
            password,
        ):
            flash("ユーザー名またはパスワードが違います。")
            return redirect(url_for("login"))

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]

        flash("ログインしました。")
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()

    flash("ログアウトしました。")
    return redirect(url_for("login"))


#直後の関数を実行
@app.route("/")
@login_required
def index():
    keyword = request.args.get("q", "").strip()
    category_id = request.args.get(
        "category_id",
        type=int,
    )
    today = date.today().isoformat()

    tasks = get_tasks(
        session["user_id"],
        keyword,
        category_id,
    )
    categories = get_categories()
    stats = get_task_stats(
        today,
        session["user_id"],
    )

    return render_template(
        "index.html",
        tasks=tasks,
        categories=categories,
        keyword=keyword,
        selected_category_id=category_id,
        today=today,
        stats=stats,
    )


@app.route("/add", methods=["POST"])
@login_required
def add_task():
    name = request.form.get("name", "").strip()
    priority = request.form.get("priority", "")
    deadline = request.form.get("deadline", "")
    category_id = request.form.get(
        "category_id",
        type=int,
    )

    if not name:
        flash("タスク名を入力してください。")
        return redirect(url_for("index"))

    if priority not in ["高", "中", "低"]:
        flash("優先度は高・中・低から選択してください。")
        return redirect(url_for("index"))

    if category_id is None:
        flash("カテゴリを選択してください。")
        return redirect(url_for("index"))

    try:
        date.fromisoformat(deadline)
    except ValueError:
        flash("正しい期限を入力してください。")
        return redirect(url_for("index"))

    create_task(
        name,
        priority,
        deadline,
        category_id,
        session["user_id"],
    )

    flash("タスクを追加しました。")
    return redirect(url_for("index"))


@app.route("/complete/<int:task_id>", methods=["POST"])
@login_required
#URLから取得したIDを、関数の task_idで受け取る
def complete_task(task_id):
    #対象タスクを完了にします
    complete_task_in_db(
        task_id,
        session["user_id"],
    )

    #トップページへ戻ります
    return redirect(url_for("index"))


@app.route("/delete/<int:task_id>", methods=["POST"])
@login_required
def delete_task(task_id):
    #削除関数を実行
    delete_task_from_db(
        task_id,
        session["user_id"],
    )

    return redirect(url_for("index"))


@app.route("/edit/<int:task_id>", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    task = get_task(
        task_id,
        session["user_id"],
    )
    categories = get_categories()

    if task is None:
        flash("指定されたタスクはありません。")
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        priority = request.form.get("priority", "")
        deadline = request.form.get("deadline", "")
        category_id = request.form.get(
            "category_id",
            type=int,
        )

        if not name:
            flash("タスク名を入力してください。")
            return redirect(
                url_for("edit_task", task_id=task_id)
            )

        if priority not in ["高", "中", "低"]:
            flash("優先度が正しくありません。")
            return redirect(
                url_for("edit_task", task_id=task_id)
            )

        if category_id is None:
            flash("カテゴリを選択してください。")
            return redirect(
                url_for("edit_task", task_id=task_id)
            )

        try:
            date.fromisoformat(deadline)
        except ValueError:
            flash("正しい期限を入力してください。")
            return redirect(
                url_for("edit_task", task_id=task_id)
            )

        update_task_in_db(
            task_id,
            name,
            priority,
            deadline,
            category_id,
            session["user_id"],
        )

        flash("タスクを更新しました。")
        return redirect(url_for("index"))

    return render_template(
        "edit.html",
        task=task,
        categories=categories,
    )


#普段の起動ではデバッグモードが無効
if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG") == "1"
    app.run(debug=debug_mode)
