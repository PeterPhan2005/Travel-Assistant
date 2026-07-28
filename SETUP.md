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
percent-encode. FastAPI settings validation URL này. T033 tạo async SQLAlchemy
engine theo lifespan của từng app, nhưng engine chỉ kết nối khi nearby route cần
session: import và `GET /health` không mở database session hoặc chạy readiness
query. `GET /pois/nearby` tạo rồi luôn đóng một request-scoped `AsyncSession`.
SQLAlchemy models và Alembic migration vẫn quản lý schema; FastAPI không tạo
table ở runtime.

### Chạy migration backend

Export cấu hình local từ `.env`, rồi chạy Alembic trong `backend/`:

```bash
set -a
source .env
set +a
cd backend
alembic upgrade head
alembic current
```

Migration đầu tiên chạy `CREATE EXTENSION IF NOT EXISTS postgis`. Database role
phải có quyền cài extension nếu hạ tầng chưa cài PostGIS; downgrade không xóa
extension dùng chung. Kiểm tra round trip trên database rỗng bằng:

```bash
alembic downgrade base
alembic upgrade head
```

Không chạy downgrade trên database có dữ liệu cần giữ. Migration chỉ đọc
`DATABASE_URL`; không cần Firebase credential hoặc service-account file.

### Curated data HCMC và Bangkok

T031 dùng YAML làm định dạng authoring chuẩn. JSON cũng được loader chấp nhận
cho tooling, nhưng các package được track nằm tại:

```text
data/curated/hcmc/package-v1.yaml
data/curated/bangkok/package-v1.yaml
```

Mọi lệnh validation dưới đây hoàn toàn offline: không cần PostgreSQL đang chạy,
không khởi tạo FastAPI/Firebase và không gọi provider hay AI. Từ `backend/`,
validate cả hai package:

```bash
python -m app.data_pipeline validate
```

Validate một city hoặc một file YAML/JSON cụ thể:

```bash
python -m app.data_pipeline validate --city hcmc
python -m app.data_pipeline validate --city bkk
python -m app.data_pipeline validate --path ../data/curated/hcmc/package-v1.yaml
```

JSON Schema version 1 được sinh trực tiếp từ Pydantic contract để tránh drift.
Regenerate sau khi chủ động thay đổi contract rồi kiểm tra file committed:

```bash
python -m app.data_pipeline schema --write
python -m app.data_pipeline schema --check
```

Luôn chạy validation trước seed. Seed thay đổi database được chọn bởi
`DATABASE_URL`; chỉ dùng database development local hoặc database test dùng một
lần. Không seed production một cách tùy tiện. Loader từ chối database không có
dấu hiệu local/development/test. Sau khi nạp `.env` và chạy migration, seed từng
city từ `backend/`:

```bash
set -a
source ../.env
set +a
alembic upgrade head
python -m app.data_pipeline seed --city hcmc
python -m app.data_pipeline seed --city bkk
```

Mỗi package được ghi trong một transaction. Seed lại hai lệnh trên để xác nhận
idempotency an toàn; stable ID được upsert, record không đổi không bị rewrite,
không truncate dữ liệu và không xóa record chỉ vì nó vắng khỏi package:

```bash
python -m app.data_pipeline seed --city hcmc
python -m app.data_pipeline seed --city bkk
```

Chạy toàn bộ test, gồm test tích hợp tạo database PostGIS tạm có tên T031, từ
`backend/` khi disposable PostGIS service đang healthy:

```bash
pytest
```

Pipeline chỉ đọc nội dung repository, không fetch web/runtime, không sinh nội
dung bằng AI, không chứa user/preferences/trip/itinerary, không lưu vị trí người
dùng và không cần Firebase credential. Package starter cố ý nhỏ, chỉ giữ fact
có nguồn review được; mục tiêu 30–50 POI thuộc T092/T093, chưa hoàn thành ở
T031.

### Static travel-package artifact

T034 tạo hai static JSON file cho đúng một city mỗi lần chạy: một public data
file và một manifest chứa SHA-256 của chính xác các byte data file. Đây không
phải HTTP API endpoint. Builder chạy offline, không đọc PostgreSQL, không khởi
tạo FastAPI/Firebase và chỉ map các field public đã duyệt từ package T031 qua
allowlist Pydantic strict.

Từ `backend/`, regenerate HCMC artifact đã commit:

```bash
python -m app.travel_packages build \
  --city hcmc \
  --output-dir ../data/travel-packages/hcmc/1.0.0
```

Build Bangkok vào thư mục tạm riêng:

```bash
PACKAGE_TMP_DIR="$(mktemp -d)"
python -m app.travel_packages build \
  --city bkk \
  --output-dir "$PACKAGE_TMP_DIR"
```

Verify HCMC manifest/data pair và kiểm tra artifact committed không drift so
với YAML canonical hoặc builder:

```bash
python -m app.travel_packages verify \
  --manifest ../data/travel-packages/hcmc/1.0.0/hcmc-starter-v1-1.0.0.manifest.json
python -m app.travel_packages check
```

Serialization luôn dùng UTF-8, key sort tăng dần, entity sort theo stable ID,
separator không có whitespace và đúng một newline cuối file. Publication time
đến từ input đã validate; builder không dùng clock, random value, working
directory hoặc database ordering. Vì vậy input và builder không đổi sẽ tạo file
name, data bytes, manifest bytes và checksum giống hệt nhau ở mọi output
directory. File generated không được sửa tay.

Kiểm tra SHA-256 trực tiếp trên macOS:

```bash
shasum -a 256 \
  ../data/travel-packages/hcmc/1.0.0/hcmc-starter-v1-1.0.0.data.json
```

Giá trị phải khớp field `sha256` trong manifest; `byteSize` phải khớp chính xác
kích thước data file. Manifest dùng relative `dataFilename`, không chứa output
directory, hostname, user máy, credential hoặc checksum đệ quy.

Hai file có thể được host như static file thông thường. Từ repository root,
chạy server local:

```bash
python3 -m http.server 8000 \
  --directory data/travel-packages/hcmc/1.0.0
```

Trong terminal khác, download cả manifest và data:

```bash
DOWNLOAD_TMP_DIR="$(mktemp -d)"
curl --fail --silent --show-error \
  --output "$DOWNLOAD_TMP_DIR/hcmc-starter-v1-1.0.0.manifest.json" \
  http://127.0.0.1:8000/hcmc-starter-v1-1.0.0.manifest.json
curl --fail --silent --show-error \
  --output "$DOWNLOAD_TMP_DIR/hcmc-starter-v1-1.0.0.data.json" \
  http://127.0.0.1:8000/hcmc-starter-v1-1.0.0.data.json
shasum -a 256 "$DOWNLOAD_TMP_DIR/hcmc-starter-v1-1.0.0.data.json"
```

T034 chưa download, stage, import hoặc activate package trên Android. WorkManager,
checksum-before-activation và atomic Room activation vẫn thuộc T035.

### Đồng bộ travel package HCMC trên Android

T035 chỉ tải static artifact; không có backend package route và không gửi
Firebase token, UID, vị trí hoặc truy vấn. Debug build dùng endpoint local typed:

```text
http://10.0.2.2:8081/hcmc-starter-v1-1.0.0.manifest.json
```

Từ repository root, phục vụ đúng thư mục artifact đã commit và chỉ bind
loopback:

```bash
cd data/travel-packages/hcmc/1.0.0
python3 -m http.server 8081 --bind 127.0.0.1
```

Không dùng `127.0.0.1` trong Android emulator: địa chỉ đó trỏ vào chính emulator.
`10.0.2.2` mới trỏ tới loopback của host. Không bind server bằng `0.0.0.0` và
không expose server development này ra Internet.

Trong terminal khác, build/cài debug app bằng JDK 21:

```bash
cd android
export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
./gradlew installDebug
adb shell am start -n com.kltn.travelassistant/.MainActivity
```

Mở **Đã tải**, chọn **Tải gói dữ liệu** hoặc **Kiểm tra và cập nhật**. UI phải
đi qua các pha chờ/tải, kiểm tra, kích hoạt rồi báo thành công. Gói active phải
hiển thị phiên bản `1.0.0`; Khám phá phải đọc hai POI của artifact T034.

Kiểm tra khôi phục sau process restart và offline:

```bash
adb shell am force-stop com.kltn.travelassistant
adb shell am start -n com.kltn.travelassistant/.MainActivity
```

Xác nhận Downloads vẫn hiển thị gói đã tải phiên bản `1.0.0`, sau đó dừng static
server bằng `Ctrl-C` và xác nhận Khám phá vẫn dùng dữ liệu Room.

Để kiểm tra checksum lỗi mà không sửa artifact committed, tạo bản tạm:

```bash
PACKAGE_BAD_DIR="$(mktemp -d)"
cp data/travel-packages/hcmc/1.0.0/* "$PACKAGE_BAD_DIR/"
python3 - "$PACKAGE_BAD_DIR/hcmc-starter-v1-1.0.0.data.json" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
data = bytearray(path.read_bytes())
data[0] ^= 1
path.write_bytes(data)
PY
cd "$PACKAGE_BAD_DIR"
python3 -m http.server 8081 --bind 127.0.0.1
```

Giữ nguyên manifest để checksum không còn khớp. Trigger update lại trong
Downloads: app phải báo gói không hợp lệ, vẫn hiển thị phiên bản active `1.0.0`
và Explore vẫn dùng POI trước đó. Không package lỗi nào được thay dữ liệu active.

Chỉ khi chủ động kiểm tra first-install mới xóa toàn bộ debug app data:

```bash
adb shell pm clear com.kltn.travelassistant
```

Xóa app data cũng xóa mọi package offline đang active và trạng thái WorkManager.
Release package hosting chưa được cấu hình; release không cho cleartext.
Package sync chỉ chạy do người dùng yêu cầu, không có periodic/background
auto-update.

### POI provider và nearby HTTP API

T032 thêm contract bất biến, provider-neutral tại `app/providers/poi/` và
curated adapter đọc các bảng T030 bằng một `AsyncSession` được caller inject.
T033 wire adapter này vào canonical route `GET /pois/nearby`; app factory không
tạo engine/session ở import time và route không lưu hoặc log origin/query. Nó
lọc theo city, bán kính metre, category và text tối giản; PostGIS geography thực
hiện radius/distance, sau đó kết quả được sắp theo distance metre và stable POI
ID mà HTTP layer không xếp hạng lại.
Provenance/freshness được map sang model typed; SQLAlchemy/GeoAlchemy row và
payload tùy ý không đi qua boundary.

Chỉ có route `GET /pois/nearby`; không có alias `/pois` hoặc `/nearby`. Query
bắt buộc gồm `city` (`hcmc` hoặc `bkk`), `latitude`, `longitude`.
`radius_metres` mặc định 5.000, phải từ 1 đến 50.000; `limit` mặc định 5, phải
từ 1 đến 20. `query` và `category` là filter tùy chọn. Response chỉ chứa
normalized destination POI, `distance_metres`, typed `sources`, `retrieved_at`,
`freshness_at`, `returned_count` và `is_complete`; request origin không được
echo hoặc persist. Facts chưa được provider hỗ trợ như rating, price level và
opening hours giữ `null` thay vì được tự điền.

Authentication của nearby route là tùy chọn: thiếu `Authorization` được phép và
không gọi Firebase verifier; nếu header được gửi thì phải là Firebase `Bearer`
token hợp lệ. Token malformed, invalid, expired hoặc revoked bị từ chối bằng
controlled auth error, không bị coi là anonymous. Kết quả không personalize
theo UID và không trả UID. `/auth/me` vẫn bắt buộc authentication, còn
`/health` vẫn public và database-free.

Chưa có live Google Places adapter, HTTP call, SDK hoặc Google Places API-key
setting, nên T033 không cần Google API key.
`google_places` mới chỉ là provider namespace dành cho adapter tương lai; field
mask, Google type/price/hour và lỗi provider phải được normalize bên trong
adapter đó thay vì lộ payload Google.

Trước khi gọi nearby API local, database phải healthy, đã migration đến head và
đã seed cả hai city bằng các lệnh ở phần trên. Provider deadline vẫn được bound;
timeout/unavailable/misconfigured map thành 503, rate limit thành 429, invalid
request thành 400, invalid response thành 502, unsupported thành 501 và internal
failure thành sanitized 500. Caller cancellation tiếp tục propagate, không có
retry/backoff hoặc giá trị `Retry-After` được tự tạo.

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
python -m pip install --requirement requirements-dev.txt
```

Windows PowerShell:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install --requirement requirements-dev.txt
```

Trên Windows, cài Python 3.12 từ
[python.org](https://www.python.org/downloads/) và bật **Add Python to PATH**.
Các lệnh `python --version`, `docker --version`, `docker info`, `node --version`
và `codex --version` vẫn là kiểm tra bắt buộc.

Backend yêu cầu `DATABASE_URL` và `FIREBASE_PROJECT_ID` hợp lệ ngay khi tạo
application. Engine được tạo theo app lifespan nhưng chỉ kết nối khi nearby
route cần session; `/health` không chạm database. `FIREBASE_PROJECT_ID` chọn
đúng Firebase development project mà backend chấp nhận token; đây là
identifier, không phải secret. Từ repository root, tạo `.env` local nếu chưa có:

```bash
cp .env.example .env
```

Sau đó, từ `backend/`, nạp các biến local, migrate và seed trước khi chạy
Uvicorn ở factory mode:

```bash
set -a
source ../.env
set +a
alembic upgrade head
python -m app.data_pipeline seed --city hcmc
python -m app.data_pipeline seed --city bkk
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

`DATABASE_URL` và `FIREBASE_PROJECT_ID` là biến bắt buộc. `APP_NAME`,
`APP_ENVIRONMENT`, `APP_VERSION` và `LOG_LEVEL` có default an toàn cho local
development và có thể được override bằng environment. Không commit `.env` hoặc
dùng credential trong `.env.example` ngoài máy development.

### Router Agent độc lập

T041 cung cấp Router Agent độc lập trong `backend/app/agents/router/`; chưa có
FastAPI assistant route hoặc application orchestration. Router chỉ nhận
`RouterRequest` đã validate và chỉ trả strict `RouterOutput`. Model path dùng
đúng một OpenAI Agents SDK run với structured output, không tool, handoff,
session, conversation ID hoặc shared state; tracing tắt cho đến T049.

Hai biến sau là tùy chọn cho riêng model path:

```text
OPENAI_API_KEY
OPENAI_ROUTER_MODEL
```

Cả hai phải nonblank; model phải được chọn rõ ràng vì Router không dựa vào
default model của SDK. Nếu thiếu một trong hai, Router không gọi mạng và dùng
deterministic fallback. Model exception hoặc output không hợp lệ cũng dùng cùng
fallback; caller cancellation vẫn propagate. Hai giá trị này là cấu hình
runtime, không thêm vào global FastAPI `Settings`, và không cần để import package
hoặc chạy `/health`. Không commit, in hoặc log API key/model response.

Xác nhận sáu fallback intent mà không cần database, Firebase hoặc OpenAI:

```bash
env -u OPENAI_API_KEY \
  -u OPENAI_ROUTER_MODEL \
  -u DATABASE_URL \
  -u FIREBASE_PROJECT_ID \
  python - <<'PY'
import asyncio
from app.agents.contracts import RouterRequest
from app.agents.router import RouterService

QUERIES = (
    "Tìm địa điểm gần tôi",
    "Giới thiệu chợ Bến Thành",
    "Phong tục địa phương",
    "Lên lịch trình một ngày",
    "Tôi cần hỗ trợ du lịch",
    "Viết mã Python giúp tôi",
)

async def main() -> None:
    service = RouterService()
    for query in QUERIES:
        request = RouterRequest(
            user_query=query,
            locale="vi-VN",
            city=None,
            preferences=None,
        )
        output = await service.route(request)
        print(output.model_dump_json())

asyncio.run(main())
PY
```

Live validation là tùy chọn và không chạy trong CI. Đọc API key im lặng, chọn
model ID hiện có trong OpenAI project, chạy một request cho mỗi intent và chỉ in
normalized `RouterOutput`:

```bash
printf 'OPENAI_API_KEY: '
read -r -s OPENAI_API_KEY
printf '\n'
export OPENAI_API_KEY
export OPENAI_ROUTER_MODEL="<explicit-model-id>"
python - <<'PY'
import asyncio
from app.agents.contracts import RouterRequest
from app.agents.router import RouterService

QUERIES = (
    "Tìm địa điểm gần tôi",
    "Giới thiệu chợ Bến Thành",
    "Phong tục địa phương",
    "Lên lịch trình một ngày",
    "Tôi cần hỗ trợ du lịch",
    "Viết mã Python giúp tôi",
)

async def main() -> None:
    service = RouterService()
    for query in QUERIES:
        output = await service.route(
            RouterRequest(
                user_query=query,
                locale="vi-VN",
                city=None,
                preferences=None,
            )
        )
        print(output.model_dump_json())

asyncio.run(main())
PY
unset OPENAI_API_KEY OPENAI_ROUTER_MODEL
```

Không paste key vào command history. Nếu live command bị hủy hoặc thất bại, luôn
unset hai biến ngay; không in raw SDK response, preference document hoặc
exception.

### Discovery Agent độc lập

T042 cung cấp Discovery Agent độc lập tại
`backend/app/agents/discovery/`; chưa có assistant route, orchestration hoặc
narration generation. Public boundary nhận một `DiscoveryRequest` đã validate
và chỉ trả `DiscoveryOutput`. POI tool gọi trực tiếp provider-neutral boundary
T032 được inject, không gọi HTTP `/pois/nearby`; menu reader dùng cùng
`AsyncSession` do caller sở hữu, chỉ đọc menu của curated POI đã được POI tool
chọn và không commit.

Hai biến sau là tùy chọn cho riêng model path:

```text
OPENAI_API_KEY
OPENAI_DISCOVERY_MODEL
```

Cả hai phải nonblank và model phải được chọn rõ ràng. Nếu thiếu một trong hai,
Discovery vẫn gọi normalized POI/menu tools nhưng không gọi OpenAI: evidence,
source/claim ID, completeness và output được assemble hoàn toàn deterministic.
Model failure hoặc output không khớp exact run-local registry cũng dùng cùng
deterministic result, không retry provider/database call đã thành công. Tracing
và sensitive trace data vẫn tắt đến T049. Không commit, in hoặc log API key,
model response, origin, query, source URL hoặc menu content.

Để reproduce dữ liệu local hiện tại, khởi động PostGIS rồi migrate, validate và
seed hai package từ `backend/`:

```bash
set -a
source ../.env
set +a
alembic upgrade head
python -m app.data_pipeline validate
python -m app.data_pipeline seed --city hcmc
python -m app.data_pipeline seed --city bkk
```

Sau đó xác nhận deterministic Discovery cho HCMC và Bangkok mà không cần
Firebase hoặc OpenAI:

```bash
unset OPENAI_API_KEY OPENAI_DISCOVERY_MODEL FIREBASE_PROJECT_ID
python - <<'PY'
import asyncio
import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agents.contracts import (
    DiscoveryOrigin,
    DiscoveryRequest,
    FactKind,
    SupportedCity,
)
from app.agents.discovery import DiscoveryService, SqlAlchemyPoiMenuReader
from app.providers.poi.curated import CuratedPoiProvider

REQUESTS = (
    DiscoveryRequest(
        city=SupportedCity.HCMC,
        origin=DiscoveryOrigin(latitude=10.7799, longitude=106.7),
        radius_metres=5_000,
        limit=5,
        query=None,
        category=None,
        requested_fact_kinds=(
            FactKind.CATEGORY,
            FactKind.IDENTITY,
            FactKind.MENU_ITEM,
            FactKind.OPENING_HOURS,
            FactKind.PRICE,
            FactKind.RATING,
        ),
    ),
    DiscoveryRequest(
        city=SupportedCity.BANGKOK,
        origin=DiscoveryOrigin(latitude=13.746508, longitude=100.493096),
        radius_metres=5_000,
        limit=5,
        query=None,
        category=None,
        requested_fact_kinds=(
            FactKind.CATEGORY,
            FactKind.IDENTITY,
            FactKind.MENU_ITEM,
            FactKind.OPENING_HOURS,
            FactKind.PRICE,
            FactKind.RATING,
        ),
    ),
)

async def main() -> None:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            service = DiscoveryService(
                CuratedPoiProvider(session),
                SqlAlchemyPoiMenuReader(session),
            )
            for request in REQUESTS:
                first = await service.discover(request)
                second = await service.discover(request)
                assert first.model_dump_json() == second.model_dump_json()
                serialized = first.model_dump(mode="json", exclude_none=True)
                assert "origin" not in serialized
                print(first.model_dump_json(exclude_none=True))
    finally:
        await engine.dispose()

asyncio.run(main())
PY
```

Starter data hiện tại phải trả hai HCMC POI theo distance/ID order và một Wat
Pho ở Bangkok. Cả hai city có zero menu rows; rating, price và opening hours
không được tự điền. Output không có origin hoặc final prose.

Live-model check là tùy chọn. Đọc key im lặng, đặt một model ID được OpenAI
project hỗ trợ, chạy cùng script trên và chỉ in normalized `DiscoveryOutput`;
sau đó unset ngay:

```bash
printf 'OPENAI_API_KEY: '
read -r -s OPENAI_API_KEY
printf '\n'
export OPENAI_API_KEY
export OPENAI_DISCOVERY_MODEL="<explicit-model-id>"
# Chạy script deterministic ở trên.
unset OPENAI_API_KEY OPENAI_DISCOVERY_MODEL
```

Không dùng model identifier từ provider khác nếu chưa có adapter được duyệt.

### Narration Agent độc lập

T043 cung cấp Narration Agent độc lập tại
`backend/app/agents/narration/`; chưa có assistant route, orchestration,
Grounding Reviewer hoặc Response Composer. Public boundary nhận đúng một
`NarrationRequest` đã validate và chỉ trả `NarrationOutput`. Agent không có
tool, handoff, MCP, session, provider call hoặc database access.

Model path chỉ được bật khi cả hai biến sau nonblank:

```text
OPENAI_API_KEY
OPENAI_NARRATION_MODEL
```

Model ID phải được chọn rõ ràng; Narration không dùng default model của SDK.
Nếu thiếu cấu hình, không có claim/source dùng được, model lỗi hoặc output
không đóng exact trên request, service trả deterministic `LIMITED` với
`narration_text=None`, key points/claim IDs/source IDs rỗng và một lý do an
toàn. Caller cancellation vẫn propagate; không retry. Tracing và sensitive
trace data vẫn tắt đến T049.

Complete output chỉ được thử khi evidence có ít nhất một factual claim gắn đúng
POI và mọi source reference đã đóng trong `EvidenceBundle`. Source label, URL,
publisher, POI name và category không tự trở thành fact. Output complete phải
là plain text, nằm trong exact requested word range và đồng thời trong biên
100–200 từ; used source IDs phải bằng đúng sorted union source IDs của used
claim IDs. HTML, Markdown, unknown/unrelated references và internal runtime
terminology đều fail closed thành `LIMITED`. Starter package hiện có zero
production narration record; đây là trạng thái hợp lệ và không được bù bằng
fact tự tạo.

Xác nhận fallback không cần OpenAI, database hoặc Firebase từ `backend/`:

```bash
env -u OPENAI_API_KEY \
  -u OPENAI_NARRATION_MODEL \
  -u DATABASE_URL \
  -u FIREBASE_PROJECT_ID \
  python - <<'PY'
import asyncio
from datetime import datetime, timezone

from app.agents.contracts import (
    EvidenceBundle,
    FactKind,
    FactualClaim,
    NarrationRequest,
    NarrationWordRange,
    PoiIdentity,
    SourceRecord,
    SourceType,
    SupportedCity,
)
from app.agents.narration import NarrationService

source = SourceRecord(
    source_id="manual-source",
    source_type=SourceType.OFFICIAL_INSTITUTION,
    label="Nguồn chính thức",
    publisher=None,
    url=None,
    published_at=None,
    retrieved_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
)
claim = FactualClaim(
    claim_id="manual-claim",
    evidence_id="manual-evidence",
    fact_kind=FactKind.HISTORY,
    statement="Một fact lịch sử đã được nguồn chính thức xác nhận.",
    supporting_source_ids=("manual-source",),
    poi_id="curated:manual-poi",
    freshness_at=None,
    price=None,
)
request = NarrationRequest(
    poi=PoiIdentity(
        poi_id="curated:manual-poi",
        canonical_name="POI kiểm tra",
        city=SupportedCity.HCMC,
        category="museum",
    ),
    evidence=EvidenceBundle(sources=(source,), claims=(claim,)),
    locale="vi-VN",
    word_range=NarrationWordRange(
        minimum_words=100,
        maximum_words=200,
    ),
)

async def main() -> None:
    service = NarrationService()
    first = await service.narrate(request)
    second = await service.narrate(request)
    assert first.model_dump_json() == second.model_dump_json()
    assert first.narration_text is None
    assert first.key_points == ()
    assert first.used_claim_ids == ()
    assert first.used_source_ids == ()
    print(first.model_dump_json())

asyncio.run(main())
PY
```

Live-model validation là tùy chọn, không chạy trong CI. Đọc API key im lặng,
đặt một OpenAI model ID được project hỗ trợ, dùng request có đủ factual claims
đã duyệt và chỉ in normalized `NarrationOutput`. Không in/store model input,
source statements hoặc API key; luôn unset ngay sau kiểm tra:

```bash
printf 'OPENAI_API_KEY: '
read -r -s OPENAI_API_KEY
printf '\n'
export OPENAI_API_KEY
export OPENAI_NARRATION_MODEL="<explicit-model-id>"
# Chạy request NarrationService có evidence đã duyệt.
unset OPENAI_API_KEY OPENAI_NARRATION_MODEL
```

Không dùng model identifier từ provider khác khi chưa có adapter được duyệt.

### Local Culture Agent độc lập

T044 cung cấp Local Culture Agent độc lập tại
`backend/app/agents/local_culture/`; chưa có assistant route, orchestration,
Grounding Reviewer, Response Composer hoặc Itinerary Agent. Public boundary
nhận đúng một `LocalCultureRequest` đã validate và chỉ trả
`LocalCultureOutput`. Agent không có tool, handoff, MCP, session, provider call,
database access hoặc external retrieval.

Model path chỉ được bật khi cả hai biến sau nonblank:

```text
OPENAI_API_KEY
OPENAI_LOCAL_CULTURE_MODEL
```

Model ID phải được chọn rõ ràng; Local Culture không dùng default model của SDK.
Nếu thiếu cấu hình, không có culture/etiquette claim có source dùng được, model
lỗi hoặc output không an toàn, service trả deterministic `LIMITED` với guidance
rỗng, `respectful_caution=None` và một lý do an toàn. Caller cancellation vẫn
propagate; không retry. Tracing và sensitive trace data vẫn tắt đến T049.

Complete output chỉ dùng claim `culture`/`etiquette` đã cung cấp. Mỗi guidance
item có ID tuần tự `culture-guidance-001`, `culture-guidance-002`, ... và
`source_ids` phải bằng đúng sorted union source IDs của `claim_ids`. Source
metadata, city, locale và topic không tự trở thành cultural evidence. HTML,
Markdown, internal terminology, stereotype, population-wide absolute
generalization, identity-group personality description, superiority/inferiority
comparison và legal/medical advice đều fail closed. `respectful_caution` chỉ
được để `None` hoặc dùng đúng một generic application-owned caution; model
không được tự tạo factual caution. Starter package hiện có không chứa dedicated
culture/etiquette claim; đây là trạng thái hợp lệ và phải trả `LIMITED`.

Xác nhận fallback không cần OpenAI, database hoặc Firebase từ `backend/`:

```bash
env -u OPENAI_API_KEY \
  -u OPENAI_LOCAL_CULTURE_MODEL \
  -u DATABASE_URL \
  -u FIREBASE_PROJECT_ID \
  python - <<'PY'
import asyncio
from datetime import datetime, timezone

from app.agents.contracts import (
    EvidenceBundle,
    FactKind,
    FactualClaim,
    LocalCultureRequest,
    SourceRecord,
    SourceType,
    SupportedCity,
)
from app.agents.local_culture import LocalCultureService

source = SourceRecord(
    source_id="manual-culture-source",
    source_type=SourceType.OFFICIAL_INSTITUTION,
    label="Nguồn chính thức",
    retrieved_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
)
claim = FactualClaim(
    claim_id="manual-culture-claim",
    evidence_id="manual-culture-evidence",
    fact_kind=FactKind.ETIQUETTE,
    statement="Tại địa điểm này, khách được đề nghị nói nhỏ.",
    supporting_source_ids=("manual-culture-source",),
)
request = LocalCultureRequest(
    city=SupportedCity.HCMC,
    topic="Ứng xử tại địa điểm",
    locale="vi-VN",
    evidence=EvidenceBundle(sources=(source,), claims=(claim,)),
)

async def main() -> None:
    service = LocalCultureService()
    first = await service.advise(request)
    second = await service.advise(request)
    assert first.model_dump_json() == second.model_dump_json()
    assert first.guidance == ()
    assert first.respectful_caution is None
    print(first.model_dump_json())

asyncio.run(main())
PY
```

Có thể sinh schema qua
`LocalCultureRequest.model_json_schema()` và
`LocalCultureOutput.model_json_schema()` mà không cần external service.

Live-model validation là tùy chọn, không chạy trong CI. Đọc API key im lặng,
đặt một OpenAI model ID được project hỗ trợ, dùng request có đủ claim
culture/etiquette đã duyệt và chỉ in normalized `LocalCultureOutput`. Không
in/store API key, model input, claim statement, source metadata hoặc raw SDK
response; luôn unset ngay sau kiểm tra:

```bash
printf 'OPENAI_API_KEY: '
read -r -s OPENAI_API_KEY
printf '\n'
export OPENAI_API_KEY
export OPENAI_LOCAL_CULTURE_MODEL="<explicit-model-id>"
# Chạy request LocalCultureService có evidence đã duyệt.
unset OPENAI_API_KEY OPENAI_LOCAL_CULTURE_MODEL
```

Không dùng model identifier từ provider khác khi chưa có adapter được duyệt.

Firebase Admin dùng Google Application Default Credentials (ADC). Trên môi
trường Google được quản lý, cấp danh tính workload phù hợp và để ADC tự tìm
credential. Khi phát triển local, service-account JSON là server secret: lưu nó
bên ngoài repository rồi trỏ biến process
`GOOGLE_APPLICATION_CREDENTIALS` tới file bên ngoài đó. Ví dụ chỉ dùng
placeholder:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="<absolute-path-outside-repository>"
```

Không thêm biến này hoặc nội dung JSON vào `.env`, không copy file vào
`backend/`, `data/` hoặc `.github/`, và không commit hay log đường dẫn/nội dung
credential. Application không tự đọc JSON; ADC xử lý credential.

Trong terminal khác, gọi liveness endpoint:

```bash
curl --include http://127.0.0.1:8000/health
curl --include \
  --header 'X-Request-ID: local-check-001' \
  http://127.0.0.1:8000/health
curl --include http://127.0.0.1:8000/auth/me
curl --include \
  --header 'Authorization: Bearer <Firebase-ID-token>' \
  http://127.0.0.1:8000/auth/me
curl --include --get \
  --data-urlencode 'city=hcmc' \
  --data-urlencode 'latitude=10.7799' \
  --data-urlencode 'longitude=106.7000' \
  http://127.0.0.1:8000/pois/nearby
curl --include --get \
  --data-urlencode 'city=bkk' \
  --data-urlencode 'latitude=13.746508' \
  --data-urlencode 'longitude=100.493096' \
  http://127.0.0.1:8000/pois/nearby
curl --include --get \
  --data-urlencode 'city=hcmc' \
  --data-urlencode 'latitude=10.7799' \
  --data-urlencode 'longitude=106.7000' \
  --data-urlencode 'query=chiến tranh' \
  --data-urlencode 'category=museum' \
  --data-urlencode 'radius_metres=2000' \
  --data-urlencode 'limit=3' \
  http://127.0.0.1:8000/pois/nearby
curl --include http://127.0.0.1:8000/missing
```

Mọi response có header `X-Request-ID`; JSON error cũng chứa cùng request ID.
`GET /health` không cần authentication và chỉ kiểm tra process liveness. Nó
không kiểm tra PostgreSQL readiness hoặc bất kỳ external service nào.
`GET /auth/me` chỉ chấp nhận `Authorization: Bearer <ID-token>` và chỉ trả về
Firebase UID sau khi Firebase Admin xác minh chữ ký, audience/project, expiry,
revocation và trạng thái disabled. Revocation checking có thể gọi Firebase qua
mạng; lỗi credential, certificate hoặc mạng trả lỗi service có kiểm soát.
Không đặt token thật trong command history hoặc tài liệu.

`GET /pois/nearby` không cần authentication khi header bị thiếu; có thể thêm
placeholder `Authorization: Bearer <Firebase-ID-token>` để thử optional-auth
trong môi trường development. Một header đã gửi nhưng không hợp lệ luôn bị từ
chối. `distance_metres` luôn dùng metre; `sources`, `retrieved_at` và
`freshness_at` mô tả provenance/freshness an toàn khi dữ liệu nguồn có sẵn.
Ngay trước khi server ghi access log, query string được bỏ khỏi ASGI scope nên
tọa độ origin, query text và category không xuất hiện trong access-log request
line; route vẫn nhận đủ query parameters để validation và discovery.

Android app chưa gọi `/auth/me` hoặc `/pois/nearby`; transport private hiện chỉ
phục vụ preference sync.

### Đồng bộ preference riêng tư

Hai endpoint canonical sau đều private và bắt buộc Firebase Bearer ID token:

```text
GET /preferences
PUT /preferences
```

Không endpoint nào nhận UID từ path, query hoặc body. Backend chỉ dùng UID từ
dependency Firebase đã verify. Ví dụ dưới đây chỉ dùng placeholder, không thay
bằng token thật trong tài liệu hoặc lịch sử shell:

```bash
curl --include \
  --header 'Authorization: Bearer <Firebase-ID-token>' \
  http://127.0.0.1:8000/preferences

curl --include \
  --request PUT \
  --header 'Authorization: Bearer <Firebase-ID-token>' \
  --header 'Content-Type: application/json' \
  --data '{"schema_version":1,"preferences":{"neutral_test_key":"Giữ Unicode"}}' \
  http://127.0.0.1:8000/preferences
```

`neutral_test_key` chỉ minh họa contract, không phải taxonomy sản phẩm. Public
envelope chỉ có `schema_version`, `preferences`; response thêm `updated_at`.
Version được hỗ trợ là `1`. `preferences` phải là JSON object và chỉ chứa null,
boolean, integer từ -1.000.000.000.000 đến 1.000.000.000.000, string tối đa 512
ký tự, array tối đa 50 item và object tối đa 50 key. Key dài 1–64 ký tự, nesting
tối đa 6 container level, tổng tối đa 500 value và serialized envelope tối đa
16 KiB. Decimal, NaN/infinity, binary, tuple, unknown top-level field và object
tùy ý bị từ chối. Unicode/Vietnamese được giữ nguyên.

GET khi user/preference chưa tồn tại trả:

```json
{
  "schema_version": 1,
  "preferences": {},
  "updated_at": null
}
```

GET này read-only và không tạo row. PUT validate full document rồi transactionally
upsert đúng một `users` row và một `user_preferences` row; nó thay toàn bộ
document, không merge field. Conflict policy là **server-receipt-order last
write wins**: mỗi PUT thành công replace complete document, transaction commit
sau là winner, và `updated_at` do PostgreSQL/server sinh. Client clock không
được dùng để chọn winner.

Android debug dùng typed backend base URL:

```text
http://10.0.2.2:8000/
```

Release để base URL rỗng cho đến khi có HTTPS hosting và cấm cleartext. Client
preference tách hẳn client static travel-package, không follow redirect và chỉ
gắn `Authorization: Bearer <ID token>` vào origin backend đã validate. Token
được lấy từ Firebase ngay trước mỗi request, không đi vào DataStore, Room,
WorkManager Data, UI/ViewModel state hay log. Một 401 được force-refresh token
và retry đúng một lần; 401 thứ hai là authentication failure.

Local representation nằm trong app-private DataStore theo SHA-256 account key:
schema version, complete document, monotonic local revision, pending flag và
server timestamp gần nhất. Local edit được fsync bởi DataStore trước khi enqueue.
WorkManager dùng một unique one-time work `preference-sync`, network constraint
`CONNECTED`, exponential backoff 30 giây và không có periodic work. Work Data
không chứa UID/account key, token, email hoặc document. Worker luôn đọc account
đang verified và complete snapshot mới nhất lúc thực thi.

Nếu local revision đổi khi PUT đang chạy, success của request cũ không clear
pending; WorkManager retry sẽ gửi snapshot mới. Nhiều offline edit collapse vào
complete snapshot mới nhất. Khi account verified active, pending local data được
PUT trước; nếu không pending thì GET refresh cache. GET không bao giờ overwrite
pending edit. Sign-out ngừng expose account cũ nhưng giữ pending record cho đúng
account đó; account khác dùng key khác và không thể thấy/gửi record cũ.

Không có preference form vì taxonomy chưa được khóa. Vì vậy manual runtime chỉ
kiểm tra automatic GET/cache sau verified sign-in; local edit/offline/revision
race được tái hiện qua deterministic test seam. Chạy:

```bash
cd backend
ruff check .
mypy --strict app tests
pytest

cd ../android
./gradlew testDebugUnitTest
./gradlew connectedDebugAndroidTest
```

Các test Android tương ứng là `PreferenceDocumentCodecTest`,
`PreferenceNetworkTest`, `PreferenceSyncEngineTest`,
`PreferenceDataStoreTest` và `PreferenceWorkRequestFactoryTest`. Với development
project, start PostgreSQL, migrate, start Uvicorn, cài debug app, sign in bằng
account verified rồi xác nhận WorkManager gọi GET và DataStore nhận document.
Tắt backend/network rồi chạy `PreferenceDataStoreTest` để tái hiện durable
pending/restart; chạy `PreferenceSyncEngineTest` để tái hiện edit mới trong khi
request cũ in-flight; chạy lại với hai account để xác nhận isolation. Không log
token, UID, full document hoặc database URL. Static package test hiện có tiếp
tục xác nhận download không có Authorization.

Dừng server bằng `Ctrl+C`. Có thể deactivate virtual environment bằng:

```bash
deactivate
```

## Tài khoản dịch vụ cần chuẩn bị

- GitHub repository.
- Firebase development project đã đăng ký Android package
  `com.kltn.travelassistant`; email/password và Google provider phải được bật,
  SHA-1/SHA-256 debug phải được đăng ký và config debug phải chứa OAuth client
  dành cho Credential Manager. Backend dùng cùng expected development project
  ID và ADC; service-account local phải nằm ngoài repository.
- Google Cloud project nếu dùng Google Maps/Places.
- OpenAI API project/key cho backend agent.
- PostgreSQL/PostGIS local qua Docker; cloud deployment chọn sau.
