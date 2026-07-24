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
theme tập trung với năm destination. Room version-1 schema và core DAO layer đã
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
và process restart đều đã qua. Google authentication, backend token verification,
networking và các tính năng sản phẩm khác vẫn chưa được triển khai.

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
