# Product Requirements

## MVP in scope

- Đăng ký/đăng nhập bằng email-password và Google.
- Đồng bộ sở thích theo tài khoản.
- Lấy vị trí foreground khi người dùng mở app.
- Hiển thị POI gần vị trí hiện tại.
- Khám phá du lịch rộng, không chỉ ẩm thực: restaurant/food, café, landmark,
  check-in/scenic, history/culture, museum/gallery, religious/cultural place,
  market/shopping, nightlife, park/nature, family attraction, entertainment,
  wellness/spa, transportation place, local-life và general travel POI khi có
  evidence/provider coverage.
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
- Hotel booking hoặc inventory/availability không có contract được duyệt.
- Ưu đãi.
- Audio response realtime.
- LLM chạy trên thiết bị.
- Turn-by-turn navigation tự xây.
- Background geofencing.
- Ảnh hoặc ghi chú người dùng.
- Mạng xã hội/cộng đồng đầy đủ.
- Lọc dị ứng/chế độ ăn nếu người dùng không đề cập trong truy vấn.

## Product rules

- Bộ curated cố định có đúng 42 POI: 30 HCMC và 12 Bangkok. Đây là trust anchor,
  high-confidence evidence set và downloadable offline dataset, không phải toàn
  bộ POI được biết khi online.
- Nguyên tắc sản phẩm là **online breadth, offline trusted depth**. Online có thể
  dùng curated data, approved live POI provider và fresh evidence khi cần;
  offline chỉ dùng active downloaded curated package.
- Price/menu ưu tiên nguồn trực tiếp của venue/restaurant/operator và phải có
  `source_updated_at`/`retrieved_at` phù hợp. Historical/cultural claim ưu tiên
  official venue, museum, government/tourism authority, sau đó
  university/institutional source; reputable editorial source chỉ bổ sung. POI
  identity/address ưu tiên official venue/government/tourism source.
- User review hoặc social-media post không bao giờ là nguồn duy nhất cho price,
  historical/cultural claim hoặc important opening-hours fact. Missing fact giữ
  nguyên missing; LLM không bao giờ là factual source.
- AI chỉ được tổng hợp hoặc suy luận từ dữ liệu và nguồn hiện có; nội dung suy
  luận phải được gắn nhãn. Nếu không có bằng chứng cho một fact, assistant phải
  nói rõ là chưa có dữ liệu và không được tự điền hoặc phát minh fact đó.
- Thiếu dữ liệu không gian quán thì bỏ trường; khi người dùng hỏi trực tiếp mới trả lời “chưa có dữ liệu”.
- Giá phải có `source_type` và `updated_at`.
- Explore và Assistant dùng chung Travel Discovery Core. Area resolution,
  provider merge, deduplication, ranking và retrieval policy thuộc application
  code, không thuộc model.
- Canonical area ID/boundary/alias/membership do ứng dụng sở hữu và
  `AreaResolver` xử lý deterministic. LLM không được invent area geography hoặc
  mô tả external provider result count như census đầy đủ của một area.
- Khi online, application có thể mở bounded fresh research cho long-tail hoặc
  freshness-sensitive question. Model không tự tạo unlimited search/fetch loop;
  webpage là untrusted data, evidence phải được extract/validate trước khi agent
  dùng và Grounding Reviewer luôn bắt buộc.
- Không promise unsupported hotel booking, payment hoặc turn-by-turn navigation.
