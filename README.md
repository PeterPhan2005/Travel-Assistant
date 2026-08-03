# Travel Assistant Planning Pack

Bộ tài liệu khởi tạo cho ứng dụng Android trợ lý du lịch cá nhân dành cho người Việt.

## Quyết định đã khóa

- Thị trường demo chính: Thành phố Hồ Chí Minh.
- Case quốc tế: Bangkok.
- Dữ liệu curated ban đầu: 30–50 POI.
- Team: 2 người.
- Hạn hoàn thành: 25/01/2027.
- Nền tảng demo: Android native.
- Mobile stack: Kotlin + Jetpack Compose.
- Backend: Python + FastAPI.
- Runtime AI: OpenAI Agents SDK với các agent chạy độc lập.
- Luồng runtime cốt lõi: Router → Discovery → deterministic ranking → Grounding
  Reviewer → Response Composer; Narration, Local Culture và Itinerary là các
  specialist agent tùy chọn theo intent.
- Auth: email/password và Google qua Firebase Authentication.
- Offline: itinerary, POI, narration và local-life content đã tải trước; tìm kiếm chỉ trong dữ liệu local.
- Giá: ưu tiên menu do quán cung cấp; luôn ghi thời điểm cập nhật.
- Narration: 100–200 từ, ưu tiên key points và nguồn.
- Ưu đãi, dị ứng/chế độ ăn, ảnh/ghi chú: ngoài MVP trừ khi truy vấn đề cập trực tiếp.

## Trạng thái hiện tại

Repository đã có Android architecture shell trong `android/`, với package hiện
có được giữ nguyên. Hilt, ViewModel/StateFlow và repository boundaries đã được
thiết lập trong T011. T012 đã bổ sung top-level Navigation Compose và Material 3
theme tập trung với năm destination. Room version-2 schema và core DAO layer đã
có; một bundled HCMC demo seed được import an toàn và idempotent. Các destination
vẫn tối giản; Explore đã có location context foreground một lần chỉ sau hành
động người dùng và tìm kiếm POI offline trong Room theo tên, bí danh hoặc loại,
với chuẩn hóa dấu tiếng Việt và xếp hạng khoảng cách đường thẳng. Không có
background tracking hoặc lưu vị trí. Debug build đã tích hợp dedicated Firebase
development client configuration và dùng Firebase automatic initialization;
release/production configuration vẫn tách riêng và chưa có. Profile đã triển
khai email/password registration, verification-aware sign-in, verification
refresh/resend, sign-out và Firebase-backed session restoration; kiểm thử tự
động và validation thủ công với Firebase development project, email verification
và process restart đều đã qua. Profile cũng hỗ trợ Google authentication qua
Credential Manager; Google ID credential chỉ được đổi tạm thời sang Firebase,
hủy picker không tạo lỗi, Firebase vẫn là nguồn phiên duy nhất và đăng xuất xóa
Credential Manager state. Downloads hiện có luồng HCMC package sync do người
dùng kích hoạt qua WorkManager: static manifest/data được tải hoặc resume trong
app-private staging, kiểm tra exact size/SHA-256 và strict contract trước khi
kích hoạt nguyên tử trong Room. Gói cũ và itinerary được giữ an toàn khi tải,
validation hoặc transaction thất bại; bundled seed chỉ chạy khi HCMC chưa có
active package hợp lệ. Debug dùng endpoint emulator localhost riêng, còn release
chưa có hosting và không cho cleartext. Android nearby transport và live Google
Places vẫn chưa được triển khai. Assistant gửi duy nhất confirmed text foreground
tới private `POST /v1/assistant/query`, hiển thị loading/cancel/retry cùng kết quả
structured và không persist transcript/response; audio không được upload.
Itinerary đã thay placeholder bằng biểu mẫu nháp một ngày cho HCMC/Bangkok,
validation local và timeline/warning/save UI typed. Timeline chỉ nhận kết quả
đã validate, không tự generate và không tự lưu. Production generator nay gửi
đúng structured fields tới private `POST /v1/itinerary-drafts/generate`, dùng
Firebase token ngay trước request, retry đúng một lần sau `401`, và không gửi
audio/transcript/candidate/evidence. Backend tự resolve curated candidate/evidence
trong request-scoped read-only session; khi không có location, thứ tự theo POI ID
ổn định và distance vẫn absent. Save production tiếp tục báo chưa persistence
cho đến T071. Authenticated deterministic validation đã render đúng timeline
HCMC/Bangkok trên Emulator và nubia V60/NX721J; cancellation, explicit retry,
offline/signed-out no-request, lifecycle non-restoration và privacy-safe logs đều
qua. Live OpenAI itinerary-model validation chưa chạy và được báo riêng.
Backend hiện có FastAPI application factory, settings được
validation, liveness endpoint `/health`, request ID, JSON error envelope thống
nhất và Firebase Admin ID-token verification cho endpoint UID-only `/auth/me`.
Backend đã có SQLAlchemy 2 typed models và Alembic migration đầu tiên cho dữ
liệu người dùng, chuyến đi, itinerary và curated POI/content trên
PostgreSQL/PostGIS. Curated pipeline version 1 dùng YAML/JSON contract strict,
JSON Schema sinh từ Pydantic và async transactional upsert để validate/seed các
starter package có nguồn cho HCMC và Bangkok một cách offline, idempotent.
POI provider boundary nội bộ và curated PostGIS adapter đã có với contract,
timeout/lỗi và provenance chuẩn hóa. Canonical `GET /pois/nearby` API hiện dùng
app-scoped async engine, request-scoped read-only session và optional Firebase
Bearer authentication để trả normalized curated POI với distance metre,
provenance/freshness và bounded `is_complete`. Chưa có live Google Places hoặc
live-model assistant validation; authenticated deterministic assistant
end-to-end validation đã qua trên Emulator và physical device. Android app chưa
gọi nearby API này. Backend đã có Router
Agent độc lập T041 với structured `RouterOutput`, một OpenAI Agents SDK run
không tool/handoff/session khi có cấu hình rõ ràng và deterministic fallback
khi thiếu cấu hình hoặc model thất bại. T042 bổ sung Discovery execution độc
lập dùng injected normalized POI/menu tools, deterministic evidence closure và
strict `DiscoveryOutput`; khi thiếu model hoặc model/output thất bại, cùng
run-local tool data được assemble deterministic mà không rerank hay tạo final
prose. T043 bổ sung Narration Agent độc lập: chỉ dùng factual claims đã duyệt
cho đúng một POI, thực thi một model run không tool/handoff/session khi có cấu
hình rõ ràng, ép exact requested range trong 100–200 từ và fail closed thành
`LIMITED` không nội dung khi evidence/configuration/output không đủ an toàn.
T044 đã bổ sung Local Culture Agent độc lập, chỉ nhận claim culture/etiquette có
nguồn, yêu cầu exact claim/source closure và ID hướng dẫn tuần tự, từ chối
stereotype/khái quát tuyệt đối cùng nội dung legal/medical, và trả `LIMITED`
không nội dung khi evidence, cấu hình hoặc output không đủ an toàn. T045 đã bổ
sung Itinerary Agent độc lập tạo lịch trình nháp một ngày từ đúng candidate và
evidence được cung cấp. Fallback không model giữ thứ tự candidate, áp dụng
required/excluded/preferred/max-stop, chia toàn bộ phút trong khung giờ thành
các mục không chồng lấn và luôn nêu hai giả định cố định; model output phải đóng
exact trên request hoặc quay về cùng planner deterministic. Agent không đọc hay
ghi itinerary đã lưu. T046 đã bổ sung Grounding Reviewer độc lập: request dùng
bounded candidate evidence để các lỗi missing/unknown source, price thiếu
timestamp, duplicate/conflicting identity và specialist reference sai đi qua
normal validation rồi được deterministic reviewer quyết định. Approved
`EvidenceBundle` toàn cục vẫn source-closed và không đổi; reviewer không tạo
fact/timestamp/ID/text thay thế. Model tùy chọn không thể làm yếu quyết định an
toàn. T047 đã bổ sung Response Composer độc lập chỉ nhận strict approved
`EvidenceBundle`, approved claim IDs, approved specialist outputs và warning an
toàn. Renderer deterministic giữ nguyên factual fragments, thứ tự Discovery,
missing POI fields, warning và exact claim/source union; model output chỉ được
chấp nhận khi bằng chính xác baseline này. T048 đã bổ sung strict
application-code orchestrator với typed `AgentRuntimeRequest`/`AgentRuntimeResult`,
Discovery prerequisite, specialist fan-out song song, Grounding/Composer tuần
tự, per-stage/overall timeout, tối đa một retry đủ điều kiện và safe partial
output. Runtime context chỉ nhận selected POI, approved evidence, ordered
candidates và explicit itinerary window; không có supervisor agent, shared
transcript/session. T061 thêm private assistant route và Android transport:
Firebase token lấy ngay trước request, 401 force-refresh tối đa một lần, không
auto retry lỗi khác, cancellation hủy active OkHttp call, và analytics no-op chỉ
nhận typed intent/outcome. T049 thêm package
observability inject được với one trace ID theo Agents SDK format cho mỗi
runtime request, exact request-ID correlation, canonical stage/attempt status,
latency và aggregate token usage. Query typed đọc bounded process-local FIFO
store; SDK export mặc định tắt, khi bật explicit vẫn luôn loại sensitive trace
data. Không có transcript/query/coordinate/content retention, cost calculation,
database observability hoặc HTTP observability route.
T050 bổ sung eval runner offline tại `backend/app/agent_evals/` với 43 fixture
synthetic có nhãn, strict schema version 1, metric basis-point theo target/check,
threshold regression đã commit và report JSON/Markdown byte-deterministic.
Lệnh `python -m app.agent_evals check` chạy real T041–T049 application
boundaries qua dependency in-memory được inject, không cần key/model, network,
database hoặc Firebase, và CI fail nếu case, threshold hay report baseline bị
drift. Report chỉ giữ case ID, target, check code và aggregate count; không giữ
query, coordinate, POI/evidence content hay final response.
Backend
cũng có builder offline, database-free để tạo và verify static travel-package
schema version 1 với manifest SHA-256; HCMC artifact hai POI đã được commit và
được Android T035 tải/kích hoạt mà không cần backend package endpoint.

T025 đã bổ sung private resource canonical `GET /preferences` và
`PUT /preferences`. Backend chỉ dùng UID đã xác minh từ Firebase để đọc hoặc
upsert một generic JSON document schema version 1 có giới hạn chặt; GET khi chưa
có row trả document rỗng mà không ghi database, còn PUT thay toàn bộ document
trong một transaction. Android có repository preference offline-first tách khỏi
static package client: DataStore giữ document nhỏ, revision và pending state
theo account key băm; Firebase ID token chỉ được lấy ngay trước private request;
một unique WorkManager job có network constraint gửi snapshot mới nhất. Thành
công của request cũ không thể xóa pending edit có revision mới hơn. Taxonomy và
UI chỉnh sở thích vẫn chưa được khóa, và preferences chưa tham gia ranking hay
AI.

## Android app identifiers

- Package/namespace: `com.kltn.travelassistant`
- Application ID: `com.kltn.travelassistant`
- Launcher activity: `.MainActivity`
- Application model: a single `ComponentActivity` using Jetpack Compose

## Cách dùng với Codex

1. Codex phải đọc `AGENTS.md`.
2. Chọn đúng một file trong `tasks/`.
3. Đọc toàn bộ context được task liệt kê.
4. Chỉ sửa file trong phạm vi task.
5. Chạy các kiểm tra được yêu cầu.
6. Cập nhật `docs/context/12-progress-tracker.md`.
7. Không tự chuyển sang task tiếp theo.
