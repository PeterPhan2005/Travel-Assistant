# Project Overview

## Product

Ứng dụng Android trợ lý du lịch cá nhân cho người Việt, đóng vai trò như một người bản địa số. Sản phẩm nổi bật nhờ thuyết minh điểm đến theo vị trí, gợi ý ẩm thực thực tế, kiến thức đời sống địa phương và lịch trình cá nhân hóa.

Đầu ra ban đầu là text. Voice trong phạm vi ban đầu chỉ là speech-to-text để nhập
truy vấn, không phải audio narration hoặc text-to-speech.

## Primary users

- Người Việt du lịch trong nước.
- Một số case người Việt đi nước ngoài để demo.
- Ngôn ngữ chính: tiếng Việt.

## Demo geography

- Primary: Thành phố Hồ Chí Minh.
- International demo: Bangkok.
- Curated dataset: 30–50 POI tổng cộng.

## Core value proposition

Khi người dùng mở app tại một nơi, app hiểu vị trí hiện tại và có thể:

- Tóm tắt điểm đến gần đó bằng 100–200 từ.
- Giải thích lịch sử, văn hóa và key points có nguồn.
- Trả lời nhu cầu như “tôi muốn ăn phở gần đây”.
- So sánh địa điểm theo khoảng cách, giá, rating, giờ mở cửa và độ phù hợp.
- Xây dựng itinerary.
- Hoạt động hữu ích với dữ liệu đã tải trước khi mất mạng.

## Team and deadline

- Team size: 2.
- Deadline: 25/01/2027.

## Current implementation state

- Android architecture shell trong `android/` đã được xác thực với package hiện
  có được giữ nguyên; Hilt, ViewModel/StateFlow và repository boundaries đã được
  thiết lập. Top-level Navigation Compose và Material 3 theme tập trung đã hoàn
  thành với năm destination.
- Room version-2 schema và core DAO layer đã có; một bundled HCMC demo seed được
  import an toàn và idempotent. Explore dùng location context foreground một lần
  để tìm POI offline trong Room theo tên, bí danh và loại, chuẩn hóa dấu tiếng
  Việt, rồi xếp hạng bằng khoảng cách đường thẳng Haversine. Các destination còn
  Itinerary vẫn là placeholder. Assistant nay có query composer transient:
  text chỉnh sửa được, push-to-talk tiếng Việt qua Android `SpeechRecognizer`,
  và gửi foreground confirmed text tới private backend khi online. Loading,
  hủy, retry explicit, auth/offline/error và structured response đều là state
  typed; request/response không được persist. Quyền micrô chỉ được hỏi sau hành
  động người dùng, audio/bản ghi không được app lưu hay gửi. Profile đã có đăng ký/đăng nhập
  email-password, gửi/làm mới/gửi lại xác minh email, đăng xuất và khôi phục
  phiên dựa trên Firebase. Người dùng chưa xác minh không được xem nội dung
  Profile đã xác thực. Profile cũng có đăng nhập Google rõ ràng qua Android
  Credential Manager; Google ID credential chỉ tồn tại tạm thời khi đổi sang
  Firebase credential, còn Firebase current-user stream vẫn là nguồn phiên duy
  nhất. Hủy account picker là trạng thái có kiểm soát và đăng xuất xóa cả phiên
  Firebase lẫn Credential Manager state. Dedicated Firebase development client
  configuration đã được tích hợp riêng cho debug và Firebase tự động khởi tạo;
  production và release configuration vẫn tách riêng và chưa có. Kiểm thử tự
  động và kiểm thử thủ công với Firebase development project đã xác nhận các
  luồng email/password và Google, hủy picker, khôi phục phiên sau cold launch,
  đăng xuất và chọn lại tài khoản đều hoạt động. Preference infrastructure dùng
  DataStore theo account key băm, local revision/pending state và một unique
  connected WorkManager job gọi private backend client; token chỉ được lấy ngay
  trước request. Taxonomy/form chỉnh preference chưa được khóa. Không có
  background tracking hoặc lưu vị trí chính xác.
- Local PostgreSQL/PostGIS Docker Compose infrastructure đã có. Backend hiện có
  FastAPI application factory, settings validation, liveness health check,
  request correlation IDs, JSON error envelope và Firebase Admin ID-token
  verification với revocation checking cho endpoint UID-only `/auth/me`.
  SQLAlchemy 2 typed schema và Alembic migration foundation đã có cho dữ liệu
  người dùng, trip/itinerary và curated POI/content trên PostGIS. Curated
  pipeline schema version 1 đã có YAML canonical packages cho HCMC và Bangkok,
  strict validation/JSON Schema cùng async transactional idempotent seed.
  Provider-neutral POI contract và curated PostGIS adapter đã có với timeout,
  lỗi và provenance được chuẩn hóa. `GET /pois/nearby` dùng optional Firebase
  Bearer authentication, app-scoped async engine và request-scoped read-only
  session để trả normalized curated POI với distance metre,
  provenance/freshness và bounded `is_complete`. Canonical private
  `GET /preferences` và `PUT /preferences` đọc hoặc thay toàn bộ bounded generic
  schema-version-1 document theo authenticated Firebase UID. GET missing-row
  không ghi dữ liệu; PUT upsert user/preference trong một transaction với
  server timestamp. Android-to-backend transport hiện có cho preferences và
  confirmed-text Assistant; live Google Places chưa được triển khai. T041 đã
  bổ sung Router Agent độc lập trả strict `RouterOutput`: một OpenAI Agents SDK
  run không tool/handoff/session khi cả key và model được cấu hình rõ ràng, hoặc
  deterministic fallback khi thiếu cấu hình hay model thất bại. T042 bổ sung
  Discovery Agent độc lập trả strict `DiscoveryOutput` từ normalized T032 POI
  provider và read-only selected-curated menu boundary. Evidence/source/claim
  được assemble deterministic, candidate order/missing values được giữ nguyên,
  model output phải đóng exact trên run-local tools và no-model/model-failure
  đều có deterministic execution; không có final prose. T043 đã bổ sung
  Narration Agent độc lập nhận một `NarrationRequest` đã validate và chỉ trả
  `NarrationOutput`: complete output phải dùng claim/source đúng POI, plain text
  trong exact requested range thuộc 100–200 từ; thiếu evidence, cấu hình hoặc
  output an toàn trả deterministic content-free `LIMITED`. Narration run không
  có tool/handoff/session, không discovery/database/provider access và tracing
  vẫn tắt. T044 đã bổ sung Local Culture Agent độc lập chỉ dùng claim culture
  hoặc etiquette được cung cấp, bắt buộc exact claim/source closure và guidance
  ID tuần tự, từ chối stereotype/khái quát tuyệt đối cùng legal/medical advice,
  và fail closed thành `LIMITED` không nội dung. Agent không có
  tool/handoff/session/retrieval và tracing vẫn tắt. T045 đã bổ sung Itinerary
  Agent độc lập chỉ tạo lịch trình nháp một ngày từ candidate/evidence được cung
  cấp. Planner deterministic giữ thứ tự candidate, áp dụng constraint, chia đều
  toàn bộ phút trong exact local window, không chồng lấn và dùng hai assumption
  cố định; model output không đóng exact sẽ quay về cùng planner. Agent không có
  route/tool/handoff/session/database/provider access và không đọc hoặc sửa
  itinerary đã lưu. T046 đã bổ sung Grounding Reviewer độc lập nhận đúng một
  `GroundingReviewRequest` và chỉ trả `GroundingReviewOutput`. Pure reviewer
  nhận bounded untrusted candidate evidence nên missing/unknown support,
  incomplete price freshness và duplicate/conflicting identity đều đi qua
  normal validation để được quyết định đầy đủ/disjoint trên canonical claim
  universe. Approved `EvidenceBundle` của T040 vẫn source-closed và không đổi.
  Reviewer kiểm tra supplied freshness và specialist claim/source/POI closure;
  model tùy chọn không thể làm yếu deterministic rejection, tạo ID/fact/
  timestamp hoặc viết lại specialist content. Agent không có
  tool/handoff/session/retrieval, route/database/provider access và tracing vẫn
  tắt. T047 đã bổ sung Response Composer độc lập nhận đúng strict approved
  `EvidenceBundle`, approved claim IDs, approved specialist outputs và warning
  an toàn. Pure renderer trả Vietnamese plain text deterministic, giữ exact
  specialist/claim fragments, Discovery order, UI omission và exact
  claim/source union; optional model output chỉ được nhận khi bằng toàn bộ
  baseline deterministic. T048 đã bổ sung application-code orchestrator strict
  nhận `AgentRuntimeRequest` và trả `AgentRuntimeResult`: Router chạy trước,
  Discovery prerequisite chạy khi được plan, ba specialist độc lập fan-out
  song song, rồi Grounding Reviewer và Response Composer. Mỗi service call tách
  biệt, không transcript/session dùng chung; policy immutable giới hạn timeout
  từng stage, overall deadline và tối đa một retry cho timeout/lỗi typed
  retryable. Runtime context optional chỉ bổ sung selected POI, approved
  evidence, ordered candidates và explicit local itinerary window. Approved
  grounding decisions được chuyển thành strict `EvidenceBundle` không sửa hay
  phát minh fact; cancellation giữ nguyên và safe partial output được bảo toàn.
  T049 đã bổ sung observability inject được: mỗi runtime request có một Agents
  SDK-format trace ID tương quan exact với request ID, stage/attempt observation
  canonical, aggregate token usage và query boundary trên bounded process-local
  FIFO store. Local observation hoạt động khi thiếu OpenAI configuration; SDK
  export chỉ bật explicit theo request, luôn
  `trace_include_sensitive_data=false`, và không lưu query, transcript,
  coordinate hay agent content. T050 đã bổ sung eval runner offline strict với
  43 fixture synthetic (Router 6; sáu agent target tiếp theo mỗi target 5;
  runtime 7), metric basis-point, committed threshold 100% và canonical
  JSON/Markdown reports. Runner gọi real T041–T049 boundaries bằng dependency
  deterministic được inject, chạy không key/model/network/database/Firebase và
  CI fail khi case, threshold hoặc committed report regress. Report không giữ
  raw query/output, coordinate, POI/evidence content hay final prose. Private
  `POST /v1/assistant/query` yêu cầu Firebase auth, map strict text/locale và
  optional request-only origin vào T048, rồi trả safe public subset. Không có
  observability route.
  Backend có
  thêm deterministic offline builder cho static travel-package data/manifest
  schema version 1; HCMC artifact hai POI đã được commit với exact-byte SHA-256.
  Android Downloads nay có HCMC-only package sync do người dùng kích hoạt qua
  WorkManager. App tải/resume static artifact vào app-private staging, kiểm tra
  strict manifest/data contract, exact byte size và SHA-256 trước khi kích hoạt
  nguyên tử trong Room; package active trước đó và itinerary vẫn được giữ khi
  mọi lỗi xảy ra. Bundled seed chỉ import khi chưa có active HCMC package hợp lệ.
  Debug endpoint dùng emulator localhost; release hosting chưa được cấu hình.
