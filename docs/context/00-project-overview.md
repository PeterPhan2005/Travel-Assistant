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
  Profile đã xác thực. Dedicated Firebase development client configuration đã
  được tích hợp riêng cho debug và Firebase tự động khởi tạo; production và
  release configuration vẫn tách riêng và chưa có. Kiểm thử tự động và kiểm thử
  thủ công với Firebase development project đã xác nhận đăng ký, gửi/xác minh
  email, khôi phục phiên chưa xác minh và đã xác minh, đăng xuất rồi đăng nhập
  lại đều hoạt động. Google authentication, backend token verification,
  networking và các hành vi sản phẩm khác vẫn chưa hoàn thành. Không có
  background tracking hoặc lưu vị trí chính xác.
- Local PostgreSQL/PostGIS Docker Compose infrastructure đã có; backend
  application, database schema/migrations, data pipeline và agent runtime chưa
  được triển khai.
