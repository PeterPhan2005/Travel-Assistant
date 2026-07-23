# Setup máy phát triển

Tài liệu này mô tả môi trường phát triển cho repository. Script kiểm tra chỉ đọc
trạng thái máy, không cài package, không sửa shell profile và không thay đổi Android
project.

## Phiên bản bắt buộc

| Công cụ | Yêu cầu |
| --- | --- |
| Git | Bản hiện còn được hỗ trợ |
| Android Studio | Stable, bản Apple Silicon trên Mac ARM64 |
| Java | JDK 21; khớp `android/gradle/gradle-daemon-jvm.properties` |
| Android SDK | Platform `android-36.1`, Build-Tools `36.0.0`, Platform-Tools, Emulator và Command-line Tools (latest) |
| Android emulator | Ít nhất một AVD ARM64 có Google Play; acceleration phải hoạt động |
| Python | **Python 3.12.x**; không dùng Python 3.13/3.14 cho backend |
| Docker Desktop | Docker CLI và Docker daemon đều phải hoạt động |
| Node.js | Một release line LTS còn được hỗ trợ |
| npm | Bản đi kèm Node.js LTS |
| Codex CLI | Có thể chạy `codex --version` |

Ngoài emulator, cần một thiết bị Android thật để kiểm thử GPS và microphone.

## macOS Apple Silicon

### 1. Công cụ nền

Xác nhận máy và cài Xcode Command Line Tools nếu còn thiếu:

```bash
uname -m
sw_vers
xcode-select -p
```

Chỉ khi `xcode-select -p` thất bại, chạy:

```bash
xcode-select --install
```

`uname -m` phải trả về `arm64`. Cài Homebrew theo hướng dẫn tại
[brew.sh](https://brew.sh/), sau đó kiểm tra:

```bash
brew --version
git --version
```

Nếu Git còn thiếu:

```bash
brew install git
```

### 2. Android Studio, Java và Android SDK

1. Tải bản Mac Apple Silicon từ
   [Android Studio](https://developer.android.com/studio/install).
2. Kéo Android Studio vào `/Applications` và hoàn tất Setup Wizard.
3. Mở **Tools > SDK Manager**.
4. Trong **SDK Platforms**, cài Android SDK Platform `android-36.1`.
5. Trong **SDK Tools**, bật **Show Package Details** và cài:
   - Android SDK Build-Tools `36.0.0`.
   - Android SDK Platform-Tools.
   - Android SDK Command-line Tools (latest).
   - Android Emulator.
6. Mở **Tools > Device Manager**, tạo một Phone AVD dùng Google Play system
   image ARM64. Không chọn image `x86_64` trên Apple Silicon.

Project dùng JDK 21. Có thể dùng JetBrains Runtime đi cùng Android Studio:

```bash
export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
java -version
```

Thiết lập Android SDK cho terminal trong shell profile của bạn:

```bash
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
```

Mở terminal mới, sau đó kiểm tra độc lập từng thành phần:

```bash
adb version
emulator -version
sdkmanager --version
"$ANDROID_HOME/emulator/emulator" -accel-check
emulator -list-avds
sdkmanager --list
./android/gradlew --version
```

Nếu Command-line Tools chưa có, chạy `open -a "Android Studio"` rồi cài
**Android SDK Command-line Tools (latest)** trong SDK Manager trước. Sau đó có thể
bổ sung đúng SDK package của project bằng:

```bash
sdkmanager "platform-tools" "emulator" "platforms;android-36.1" "build-tools;36.0.0"
sdkmanager --licenses
```

Nếu `emulator -list-avds` không trả về tên nào, mở Android Studio bằng:

```bash
open -a "Android Studio"
```

Sau đó vào **Tools > Device Manager > Create Virtual Device**, chọn Phone,
Google Play system image ARM64 và hoàn tất wizard. Kiểm tra lại bằng
`emulator -list-avds`.

Kết nối và cho phép USB debugging trên thiết bị Android thật, rồi xác nhận:

```bash
adb devices -l
```

### 3. Python 3.12

Repository yêu cầu đúng Python 3.12. Trên Homebrew:

```bash
brew install python@3.12
export PATH="/opt/homebrew/opt/python@3.12/libexec/bin:$PATH"
python --version
python3 --version
python3.12 --version
```

Cả `python --version` và `python3.12 --version` phải báo `Python 3.12.x`.
Thêm dòng `export PATH=...` ở trên vào `~/.zshrc` bằng editor nếu muốn giữ cấu
hình cho terminal mới. Không thay thế requirement bằng Python 3.13 hoặc 3.14.

### 4. Node.js LTS, npm và Codex CLI

Tại thời điểm cập nhật tài liệu, Node.js 24 là một release line LTS. Homebrew
cài formula này ở dạng keg-only:

```bash
brew install node@24
export PATH="/opt/homebrew/opt/node@24/bin:$PATH"
node --version
node -p "process.release.lts"
npm --version
npm install -g @openai/codex
codex --version
```

`node -p "process.release.lts"` phải trả về tên LTS, không phải `undefined`.
Thêm dòng `export PATH=...` vào `~/.zshrc` bằng editor nếu muốn giữ cấu hình.

### 5. Docker Desktop

Cài bản Apple Silicon từ
[Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/),
mở ứng dụng và đợi engine khởi động. Docker CLI và daemon là hai kiểm tra riêng:

```bash
docker --version
docker info
```

`docker --version` chỉ chứng minh CLI có mặt. `docker info` phải có phần
`Server` và trả exit code `0` mới chứng minh daemon hoạt động.

## PostgreSQL/PostGIS local

Từ repository root, tạo file cấu hình local từ sample đã track:

```bash
cp .env.example .env
```

Các credential trong `.env.example` chỉ dành cho local development. Không dùng
chúng trong shared, staging hoặc production environment và không commit `.env`.
Compose dùng một PostgreSQL/PostGIS service tên `database`, chỉ publish cổng lên
loopback của máy và lưu database cluster trong named volume
`travel-assistant_postgres_data`. Host port mặc định là `5433` để không xung đột
với PostgreSQL local thường dùng `5432`; có thể đổi `POSTGRES_PORT` trong `.env`.
Khi thay đổi POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD hoặc POSTGRES_PORT
trong `.env`, phải cập nhật DATABASE_URL tương ứng để hai cấu hình không bị
lệch nhau.

Kiểm tra cấu hình và khởi động database:

```bash
docker compose config
docker compose up -d
docker compose ps
```

`docker compose ps` phải hiển thị service `database` ở trạng thái `healthy`.
Kiểm tra readiness trực tiếp và xem log bằng:

```bash
docker compose exec database sh -c 'PGPASSWORD="$POSTGRES_PASS" pg_isready --host=127.0.0.1 --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"'
docker compose logs database
docker compose logs --follow database
```

Xác nhận kết nối SQL và PostGIS:

```bash
docker compose exec database sh -c 'PGPASSWORD="$POSTGRES_PASS" psql --host=127.0.0.1 --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --command="SELECT current_database(), current_user;"'
docker compose exec database sh -c 'PGPASSWORD="$POSTGRES_PASS" psql --host=127.0.0.1 --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --command="SELECT PostGIS_Full_Version();"'
```

Connection URL cho SQLAlchemy async/asyncpg có format:

```text
postgresql+asyncpg://<user>:<password>@localhost:<port>/<database>
```

Với sample mặc định, URL là:

```text
postgresql+asyncpg://travel_assistant:local_dev_only_change_me@localhost:5433/travel_assistant
```

Nếu credential chứa ký tự đặc biệt, phần user/password trong URL phải được
percent-encode. `DATABASE_URL` được chuẩn bị cho task backend sau; T003 chưa tạo
FastAPI, SQLAlchemy hoặc Alembic application.

Dừng container nhưng giữ dữ liệu local:

```bash
docker compose down
```

Named volume vẫn tồn tại và được dùng lại ở lần `docker compose up -d` tiếp
theo. Chỉ khi chủ động muốn xóa toàn bộ database local và khởi tạo lại từ đầu,
chạy destructive reset sau:

```bash
docker compose down --volumes
```

Có thể kiểm tra volume hiện tại bằng:

```bash
docker volume ls --filter name=travel-assistant_postgres_data
```

## Kiểm tra toàn bộ repository

Từ repository root:

```bash
./scripts/verify-development-environment.sh
```

Script kiểm tra host, Xcode Command Line Tools/Homebrew trên macOS, Git, Java,
Node LTS, npm, Codex CLI, Python 3.12, Android Studio, Android SDK tools,
emulator acceleration, AVD, Android Gradle wrapper, Docker CLI và Docker daemon.
Script in tất cả lỗi rồi trả exit code `1` nếu còn prerequisite chưa đạt.

Chuỗi lệnh tương đương để chẩn đoán thủ công:

```bash
uname -m
sw_vers
xcode-select -p
brew --version
git --version
java -version
node --version
node -p "process.release.lts"
npm --version
codex --version
python --version
python3 --version
python3.12 --version
adb version
emulator -version
sdkmanager --version
"$ANDROID_HOME/emulator/emulator" -accel-check
emulator -list-avds
adb devices -l
docker --version
docker info
./android/gradlew --version
```

Không đưa `android/local.properties`, `.env`, credential hoặc API key vào Git.

## Firebase development cho Android

Android debug build kết nối duy nhất tới Firebase project dành cho development.
Firebase Android app trong project đó phải dùng package:

```text
com.kltn.travelassistant
```

Client configuration được đặt riêng cho debug tại:

```text
android/app/src/debug/google-services.json
```

File này chứa các identifier phía client để Firebase SDK chọn đúng project/app,
không phải service-account hay server credential. Repository track đúng file
development này để local build và CI có thể build debug mà không cần repository
secret. Firebase Security Rules, IAM và App Check ở task sau mới là các lớp bảo
vệ tài nguyên Firebase; không dựa vào việc giữ bí mật Android client config.

Để tải lại config mà không thay đổi các identifier do Firebase cấp:

1. Mở Firebase Console và chọn đúng project **development**, không chọn staging
   hoặc production.
2. Mở **Project settings > General > Your apps**.
3. Chọn Android app có package `com.kltn.travelassistant`. Nếu app chưa tồn tại,
   đăng ký đúng package này; không đổi application ID của Android project.
4. Chọn **Download google-services.json**.
5. Thay file tại `android/app/src/debug/google-services.json`; không đặt bản sao
   tại `android/app/`, `android/app/src/main/` hoặc repository root.
6. Từ repository root, kiểm tra package mà không in các identifier:

   ```bash
   jq -e \
     '[.client[]?.client_info?.android_client_info?.package_name] |
      length > 0 and all(. == "com.kltn.travelassistant")' \
     android/app/src/debug/google-services.json
   ```

7. Từ `android/`, xác nhận Google Services xử lý được debug config:

   ```bash
   ./gradlew :app:processDebugGoogleServices
   ```

Release/production phải có Firebase project và variant-specific config riêng;
chúng cố ý chưa có trong T020. Không chuyển development config tới module root,
vì vị trí đó có thể khiến release build sau này dùng nhầm project development.

Không bao giờ commit:

- service-account JSON hoặc Admin SDK private key;
- Firebase Admin credential;
- FCM server key/credential;
- OAuth client secret;
- production backend secret.

Các secret phía server phải nằm trong secret manager hoặc environment được quản
lý, không nằm trong Android app, GitHub Actions output hoặc repository.

## Backend virtual environment

macOS/Linux:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install --upgrade pip
```

Windows PowerShell (giữ lại quy trình tương ứng):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install --upgrade pip
pip install fastapi "uvicorn[standard]" openai-agents pydantic-settings sqlalchemy asyncpg alembic "psycopg[binary]" httpx pytest pytest-asyncio ruff mypy
```

Trên Windows, cài Python 3.12 từ
[python.org](https://www.python.org/downloads/) và bật **Add Python to PATH**.
Các lệnh `python --version`, `docker --version`, `docker info`, `node --version`
và `codex --version` vẫn là kiểm tra bắt buộc.

## Tài khoản dịch vụ cần chuẩn bị

- GitHub repository.
- Firebase development project đã đăng ký Android package
  `com.kltn.travelassistant`; email/password và Google sign-in vẫn thuộc các task
  sau.
- Google Cloud project nếu dùng Google Maps/Places.
- OpenAI API project/key cho backend agent.
- PostgreSQL/PostGIS local qua Docker; cloud deployment chọn sau.
