# Product Requirements

## MVP in scope

- Đăng ký/đăng nhập bằng email-password và Google.
- Đồng bộ sở thích theo tài khoản.
- Lấy vị trí foreground khi người dùng mở app.
- Hiển thị POI gần vị trí hiện tại.
- Tìm kiếm text và voice-to-text bằng tiếng Việt.
- Truy vấn “tôi muốn ăn phở” và trả về 3–5 lựa chọn.
- Hiển thị khoảng cách km, giá và ngày cập nhật giá, rating nổi bật, giờ hoạt động, không gian khi có dữ liệu.
- Narration 100–200 từ, ưu tiên key points và nguồn.
- Nội dung đời sống địa phương.
- Tạo itinerary một ngày và lưu.
- Mở Google Maps hoặc app bản đồ để dẫn đường.
- Tải travel package trước chuyến đi.
- Offline: xem itinerary, POI, narration, local-life content; tìm kiếm chỉ trong dữ liệu đã tải.

## Out of scope for MVP

- CMS/admin.
- Booking và thanh toán.
- Ưu đãi.
- Audio response realtime.
- LLM chạy trên thiết bị.
- Turn-by-turn navigation tự xây.
- Background geofencing.
- Ảnh hoặc ghi chú người dùng.
- Mạng xã hội/cộng đồng đầy đủ.
- Lọc dị ứng/chế độ ăn nếu người dùng không đề cập trong truy vấn.

## Product rules

- Món đặc trưng ưu tiên curated/editor/community verified.
- AI chỉ được tổng hợp hoặc suy luận từ dữ liệu và nguồn hiện có; nội dung suy
  luận phải được gắn nhãn. Nếu không có bằng chứng cho một fact, assistant phải
  nói rõ là chưa có dữ liệu và không được tự điền hoặc phát minh fact đó.
- Thiếu dữ liệu không gian quán thì bỏ trường; khi người dùng hỏi trực tiếp mới trả lời “chưa có dữ liệu”.
- Giá phải có `source_type` và `updated_at`.
- Khi online, agent được tự mở rộng tìm kiếm qua các nguồn được phép để thu thập
  bằng chứng, nhưng không được biến thông tin không có nguồn thành fact và không
  tự thực hiện hành động có chi phí hoặc thay đổi dữ liệu đã lưu mà không có xác
  nhận.
