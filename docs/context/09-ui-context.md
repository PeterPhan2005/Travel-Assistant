# UI Context

## Product tone

- Friendly local guide.
- Informative, not verbose.
- Vietnamese-first.
- Explain why a recommendation fits.

## Primary navigation

Bottom navigation:

1. Khám phá
2. Trợ lý
3. Lịch trình
4. Đã tải
5. Cá nhân

## Key screens

- Sign in / sign up.
- Permission education.
- Nearby map/list.
- Assistant chat/query.
- POI comparison.
- POI detail + narration.
- Itinerary timeline.
- Downloaded destination packages.
- Preference profile.

## POI card rules

Show only fields with data:

- Name.
- Distance in km.
- Price and updated date.
- Rating and review count when available.
- Open/closed based on timestamped data.
- Space attributes when available.
- Why recommended.
- Source freshness.

## Offline UX

- Persistent but non-blocking offline indicator.
- Clearly mark “Dữ liệu đã tải ngày…”.
- Disable unsupported actions with explanation.

## Itinerary draft UX

- Biểu mẫu một ngày chỉ hỗ trợ Thành phố Hồ Chí Minh
  (`Asia/Ho_Chi_Minh`) và Bangkok (`Asia/Bangkok`).
- Người dùng phải nhập ngày local theo `YYYY-MM-DD`, giờ bắt đầu/kết thúc theo
  `HH:mm`, giờ bắt đầu phải trước giờ kết thúc trong cùng ngày, và số điểm dừng
  tối đa phải là số nguyên từ 1 đến 20.
- Nhu cầu/lưu ý là tùy chọn, tối đa 500 Unicode code point và không bị truncate.
- Heading `Lịch trình` nằm ngoài body scroll; explanation, form, result và đúng
  một explicit save action nằm trong inner scrolling content.
- Chỉ hành động `Tạo lịch trình nháp` mới bắt đầu generation; thay đổi field
  không tự generate và làm draft cũ hết hiệu lực.
- Timeline chỉ hiển thị output đã validate theo đúng city/date/timezone/window:
  item không rỗng, chronological, positive interval, không overlap, không vượt
  số điểm dừng; mọi assumption và safe warning được giữ nguyên.
- Draft luôn có nhãn chưa lưu. Chỉ tap `Lưu lịch trình` mới gọi save boundary;
  T070 không ghi Room/backend và production báo persistence chưa khả dụng cho
  đến T071.
- Production generation chỉ chạy online sau explicit tap và verified Firebase
  session. Nó gửi structured form tới `/v1/itinerary-drafts/generate`; offline
  hoặc signed-out không bắt đầu request, không tự retry khi trạng thái thay đổi,
  không mở Profile tự động và giữ nguyên form để người dùng retry rõ ràng.
- Không location vẫn là input hợp lệ cho city-level generation. Itinerary không
  tự xin quyền, không đọc location lịch sử và không tạo city-centre giả.
