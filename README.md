# Todo App

PythonとFlaskで作成した、タスク管理用のWebアプリケーションです。

タスクの追加・編集・完了・削除・検索ができ、優先度や期限も管理できます。

## スクリーンショット

![Todoアプリの画面](docs/todo-app.png)

## 主な機能

- タスクの追加
- タスク名・優先度・期限の編集
- タスクの完了
- 削除前の確認
- タスク名による検索
- 優先度の色分け
- 期限切れタスクの警告
- 全件・未完了・完了・期限切れ件数の表示
- スマートフォン対応
- SQLiteによるデータ保存
- サーバー側の入力チェック
- 自動テスト

## 使用技術

- Python 3.13
- Flask 3.1
- SQLite
- HTML
- CSS
- Jinja
- JavaScript
- unittest
- Git

## プロジェクト構成

```text
TodoAppLearning/
├── app.py
├── database.py
├── requirements.txt
├── static/
│   └── style.css
├── templates/
│   ├── index.html
│   └── edit.html
└── tests/
    └── test_app.py
```

## 環境構築

リポジトリを取得します。

```powershell
git clone <リポジトリのURL>
cd TodoAppLearning
```

仮想環境を作成します。

```powershell
python -m venv .venv
```

仮想環境を有効にします。

```powershell
.\.venv\Scripts\Activate.ps1
```

必要なライブラリをインストールします。

```powershell
python -m pip install -r requirements.txt
```

## 起動方法

```powershell
python app.py
```

ブラウザで次のURLを開きます。

```text
http://127.0.0.1:5000
```

## テスト方法

```powershell
python -m unittest discover -s tests -v
```

テストでは一時データベースを使用するため、通常のタスクデータには影響しません。

## この開発で学んだこと

- Flaskのルーティング
- GETとPOSTの使い分け
- HTMLフォームからPythonへデータを渡す方法
- Jinjaによる動的なHTML表示
- SQLiteを使ったCRUD処理
- サーバー側で入力を検証する重要性
- CSS GridとFlexbox
- レスポンシブデザイン
- unittestによる自動テスト
- Gitによる変更履歴の管理

## 今後追加したい機能

- ユーザー登録・ログイン
- カテゴリとタグ
- 優先度や期限による並び替え
- Webサービスへの公開