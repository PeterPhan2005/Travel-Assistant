# Core User Flows

## A. Nearby narration

1. User mở app.
2. App xin location permission tại thời điểm cần.
3. App lấy vị trí hiện tại.
4. App tìm POI curated/online gần nhất.
5. User chọn POI hoặc “Giới thiệu nơi này”.
6. Narration agent tạo/tải bài 100–200 từ có nguồn.
7. User có thể mở dẫn đường hoặc lưu vào itinerary.

## B. Food query

1. User gõ hoặc bấm microphone và nói “Tôi muốn ăn phở”.
2. SpeechRecognizer trả transcript.
3. Router xác định intent `find_food` và entity `phở`.
4. Discovery agent tìm ứng viên.
5. Deterministic ranking service tính thứ hạng.
6. Grounding reviewer kiểm tra tính đầy đủ và nguồn.
7. Composer trả 3–5 card với lý do gợi ý.
8. User bấm “Dẫn đường”.

## C. Itinerary

1. User chọn ngày, thời gian, ngân sách và sở thích.
2. Itinerary agent tạo bản nháp có cấu trúc.
3. Constraint validator kiểm tra giờ mở cửa, trùng thời gian và quãng đường.
4. User chấp nhận/lưu.
5. Itinerary được đồng bộ theo tài khoản và đưa vào travel package.

## D. Offline

1. User tải travel package khi có mạng.
2. App lưu package version và dữ liệu vào Room/app storage.
3. Khi mất mạng, app chuyển sang offline capability.
4. Search chạy trên POI local.
5. App hiển thị timestamp của dữ liệu khi cần.
