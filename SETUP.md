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
- Firebase project cho email/password và Google sign-in.
- Google Cloud project nếu dùng Google Maps/Places.
- OpenAI API project/key cho backend agent.
- PostgreSQL/PostGIS local qua Docker; cloud deployment chọn sau.
