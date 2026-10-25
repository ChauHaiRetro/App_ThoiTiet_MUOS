THỜI TIẾT VN — app xem thời tiết Việt Nam cho muOS (RG40XXH, 640x480)
=====================================================================

CÀI ĐẶT
1. Tắt máy, cắm thẻ SD (thẻ chứa muOS) vào máy tính.
2. Chép nguyên thư mục "ThoiTietVN" vào:
       MUOS/application/ThoiTietVN/
   (trên máy là /mnt/mmc/MUOS/application/ThoiTietVN/)
3. Cắm thẻ lại, bật máy, bật Wi-Fi (Configuration > Wi-Fi Network).
4. Mở Applications > Thời Tiết VN.

Nếu app không hiện trong danh sách, hãy đảm bảo mux_launch.sh có quyền chạy
(qua SSH: chmod +x /mnt/mmc/MUOS/application/ThoiTietVN/mux_launch.sh).

ĐIỀU KHIỂN
  Trái / Phải : đổi thành phố
  L1 / R1     : đổi màn hình (Hiện tại / 7 ngày / Toàn quốc)
  Lên / Xuống : cuộn danh sách (màn Toàn quốc)
  A           : mở chi tiết thành phố đang chọn (màn Toàn quốc)
  X           : làm mới dữ liệu
  Y           : đặt thành phố hiện tại làm mặc định (★)
  B / START   : thoát

TÍNH NĂNG
- 50 tỉnh thành / điểm du lịch: nhiệt độ, cảm giác như, độ ẩm, gió, UV,
  khả năng mưa, giờ mặt trời mọc/lặn, dự báo 24 giờ và 7 ngày.
- Màn "Toàn quốc" xem nhiệt độ cả nước trong 1 lần tải.
- Lưu bộ nhớ đệm (cache.json): mất mạng vẫn xem được dữ liệu lần trước.
- Tự làm mới sau 15 phút.

KHẮC PHỤC SỰ CỐ
- Xem weather.log trong thư mục app.
- Nút bấm không đúng: app ưu tiên mapping tay cầm của muOS. Nếu bấm nút mà
  hiện "Nút #n chưa gán", sửa số nút trong config.json mục "joystick_buttons".
- "Không tải được dữ liệu": kiểm tra Wi-Fi; app tự thử HTTPS, curl, wget, HTTP.

Dữ liệu thời tiết: Open-Meteo.com (CC BY 4.0). Font: DejaVu Sans (giấy phép tự do).
