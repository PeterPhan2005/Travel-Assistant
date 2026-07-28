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
  thành với năm destination placeholder.
- Room version-2 schema và core DAO layer đã có; một bundled HCMC demo seed được
  import an toàn và idempotent. Explore dùng location context foreground một lần
  để tìm POI offline trong Room theo tên, bí danh và loại, chuẩn hóa dấu tiếng
  Việt, rồi xếp hạng bằng khoảng cách đường thẳng Haversine. Các destination còn
  lại vẫn là placeholder, ngoại trừ Profile đã có đăng ký/đăng nhập
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
  server timestamp. Android-to-backend transport hiện chỉ có cho preferences;
  live Google Places và agent runtime end-to-end chưa được triển khai. T041 đã
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
  tool/handoff/session/retrieval và tracing vẫn tắt. Itinerary specialist,
  reviewer, composer và code orchestration vẫn chưa có.
  Backend có
  thêm deterministic offline builder cho static travel-package data/manifest
  schema version 1; HCMC artifact hai POI đã được commit với exact-byte SHA-256.
  Android Downloads nay có HCMC-only package sync do người dùng kích hoạt qua
  WorkManager. App tải/resume static artifact vào app-private staging, kiểm tra
  strict manifest/data contract, exact byte size và SHA-256 trước khi kích hoạt
  nguyên tử trong Room; package active trước đó và itinerary vẫn được giữ khi
  mọi lỗi xảy ra. Bundled seed chỉ import khi chưa có active HCMC package hợp lệ.
  Debug endpoint dùng emulator localhost; release hosting chưa được cấu hình.
