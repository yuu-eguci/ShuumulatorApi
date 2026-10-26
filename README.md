ShuumulatorApi
===

株トレードシミュレーター Shuumulator の API サーバー。
Django + Django REST framework で動く。

- Docker: 対応!
- Python: 3.13
- Django: 5.2.18 LTS
- Linter: ruff
- Test: Django test runner

## バージョン

| 種類 | バージョン |
|---|---|
| Python | 3.13 (Docker・CI とも) |
| Django | 5.2.18 (LTS) |
| Django REST framework | 3.18.3 |
| PyJWT | 2.15.1 |
| django-cors-headers | 4.9.0 |
| whitenoise | 6.12.0 |
| PyMySQL | 1.2.3 (本番の MySQL 用。MySQL 8.4 でテスト確認済み) |
| ruff | 0.17.2 |
| pip-audit | 2.10.1 |

依存は `requirements.in` / `requirements-dev.in` に書き、ハッシュ付きの `requirements.txt` / `requirements-dev.txt` を作る。

```bash
docker run --rm -v "$PWD":/work -w /work python:3.13-slim sh -c "pip install pip-tools && \
  pip-compile --upgrade --generate-hashes --allow-unsafe --no-strip-extras requirements.in && \
  pip-compile --upgrade --generate-hashes --allow-unsafe --no-strip-extras requirements-dev.in"
```

## パッと実行してみたい

```bash
cp .env.example .env   # 値はローカル専用のダミーに書き換える
docker compose build
docker compose run --rm api python manage.py test
docker compose up      # http://localhost:8000/
```

ログインを試すには `user` テーブルに id=1 のユーザーが要る。`docker compose up` したまま別のターミナルで:

```bash
docker compose exec api python manage.py shell -c "from app.models import User; User.objects.get_or_create(id=1, defaults={'name': 'local'})"
curl -s -H 'Content-Type: application/json' \
  -d "{\"code\": \"$(grep ^SHUUMULATOR_LOGIN_CODE= .env | cut -d= -f2)\"}" \
  http://localhost:8000/api-token-auth/
```

- DB はコンテナ内の SQLite。コンテナを消すとデータも消える。
- テストは SQLite とダミーデータだけで動く。外部 API や本番 DB にはつながない。

## Lint・テスト・脆弱性チェック

```bash
docker compose run --rm api ruff check .
docker compose run --rm api python manage.py test
docker compose run --rm api pip-audit
```

## 環境変数

| 名前 | 用途 |
|---|---|
| `DJANGO_SECRET_KEY` | Django と JWT 署名のキー。本番では必須。ローカルで未設定なら起動ごとにランダム生成 |
| `SHUUMULATOR_LOGIN_CODE` | ログイン用コード。未設定ならログインできない |
| `DJANGO_ALLOWED_HOSTS` | 追加で許可するホスト (カンマ区切り) |
| `WEB_BASE_URL` | 本番の CORS 許可オリジン |
| `DJANGO_DATABASE_NAME` / `_USER` / `_PASSWORD` / `_SERVER` | 本番の MySQL 接続先 |
| `DJANGO_DATABASE_SSL_CA` | 本番の MySQL のサーバー証明書を検証する CA ファイル |

本番 (`config/production.py`) は、キーが無い・50 文字未満・`.env.example` のダミー値のときは起動しない。

## API

認証失敗は 403 を返す。

| メソッド・パス | 内容 |
|---|---|
| `POST /api-token-auth/` | `{"code": "..."}` を送ると `{"token": "<JWT>"}` (user_id=1, 1 時間有効) |
| `GET /api/v1/user/{id}/` | ヘッダー `Authorization: JWT <token>` が有効なら `{"hello": true}` |
| `GET /api/v1/portfolio/{user_id}/` | 保有中の銘柄。`{"tradings": [{code, name, buy, bought_at, current_price}]}`。`current_price` は銘柄ごとの最新価格 (無ければ `null`) |
| `GET /api/v1/realized/{user_id}/?each=year\|month\|week\|day` | 確定損益。`{user_id, each, realized: [{gain, lost, label}], win_rate, total_gain, total_lost}`。取引が無ければ空リストと 0 |

`portfolio` と `realized` は自分の `user_id` だけ見られる。他人の `user_id` は 403、数値でない `user_id` は 400。

## セキュリティについて

- 2021 年のコミット履歴に `SECRET_KEY` とログイン用コードが直書きされていた。公開済みなので漏えい済みとして扱い、その値は使わない。
- 本番環境が残っているなら、キーとログイン用コードを新しい値に差し替える必要がある。これはこのリポジトリの作業範囲外。

## デプロイ

Azure App Service へのデプロイジョブは削除している。GitHub Actions は lint・テスト・脆弱性チェックと Docker でのテストだけを実行する。

本番用の設定 `config/production.py` は残している。`WEBSITE_HOSTNAME` がある環境で使われる。
