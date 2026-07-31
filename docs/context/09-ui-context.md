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
- Chỉ hành động `Tạo lịch trình nháp` mới bắt đầu generation; thay đổi field
  không tự generate và làm draft cũ hết hiệu lực.
- Timeline chỉ hiển thị output đã validate theo đúng city/date/timezone/window:
  item không rỗng, chronological, positive interval, không overlap, không vượt
  số điểm dừng; mọi assumption và safe warning được giữ nguyên.
- Draft luôn có nhãn chưa lưu. Chỉ tap `Lưu lịch trình` mới gọi save boundary;
  T070 không ghi Room/backend và production báo persistence chưa khả dụng cho
  đến T071.
- Transport Assistant hiện không mang đủ structured constraint và
  candidate/evidence, nên production itinerary generation báo unavailable thay
  vì chuyển field sang prose hoặc tạo timeline giả.
