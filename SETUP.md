# Setup máy phát triển

## Phần mềm bắt buộc

1. Git.
2. Android Studio bản stable mới nhất.
3. Android SDK, emulator và một thiết bị Android thật để test GPS/microphone.
4. Python 3.12.
5. Docker Desktop.
6. Node.js LTS, chỉ để cài Codex CLI và một số CLI phụ trợ.
7. Codex CLI:

```bash
npm i -g @openai/codex
```

## Kiểm tra môi trường

```bash
git --version
python --version
docker --version
node --version
npm --version
codex --version
```

Trong Android Studio:

- Cài Android SDK Platform mới nhất đang stable.
- Cài Android SDK Build-Tools.
- Tạo một emulator có Google Play.
- Xác nhận có thể tạo và chạy một Empty Activity dùng Jetpack Compose.

## Backend virtual environment

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install fastapi "uvicorn[standard]" openai-agents pydantic-settings   sqlalchemy asyncpg alembic "psycopg[binary]" httpx   pytest pytest-asyncio ruff mypy
```

## Tài khoản dịch vụ cần chuẩn bị

- GitHub repository.
- Firebase project cho email/password và Google sign-in.
- Google Cloud project nếu dùng Google Maps/Places.
- OpenAI API project/key cho backend agent.
- PostgreSQL/PostGIS local qua Docker; cloud deployment chọn sau.
