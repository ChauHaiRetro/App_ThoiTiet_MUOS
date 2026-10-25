# 🌤️ THỜI TIẾT VN

![Platform](https://img.shields.io/badge/OS-muOS-blue?style=flat-square)
![Device](https://img.shields.io/badge/Device-Anbernic%20RG40XX%20H-red?style=flat-square)
![Resolution](https://img.shields.io/badge/Resolution-640x480-green?style=flat-square)
![Python](https://img.shields.io/badge/Language-Python-yellow?style=flat-square)

**Thời Tiết VN** là ứng dụng xem dự báo thời tiết dành riêng cho thiết bị handheld chạy hệ điều hành **muOS** (tối ưu hóa cho màn hình 3.5 inch, độ phân giải 640x480 của Anbernic RG40XX H).

---

## ✨ Tính Năng Nổi Bật

- 📍 **Dữ liệu phong phú:** Hỗ trợ 50 tỉnh thành & điểm du lịch tại Việt Nam (hiển thị nhiệt độ, cảm giác thực tế, độ ẩm, sức gió, chỉ số UV, khả năng mưa, giờ mặt trời mọc/lặn, dự báo 24 giờ và 7 ngày).
- 🗺️ **Màn hình "Toàn quốc":** Xem tổng quan nhiệt độ toàn bộ các tỉnh thành chỉ trong một lần tải dữ liệu.
- ⚡ **Hỗ trợ Offline (Cache):** Tự động lưu dữ liệu vào `cache.json`. Nếu mất mạng Wi-Fi, app vẫn hiển thị thông tin thời tiết của lần cập nhật gần nhất.
- 🔄 **Tự động làm mới:** Cập nhật dữ liệu thời tiết tự động sau mỗi 15 phút.

---

## 📦 Hướng Dẫn Cài Đặt

1. **Tải về:** Tải gói cài đặt (`ThoiTietVN.muxapp` hoặc `.zip`) trong mục **Releases** mới nhất.
2. **Sao chép vào thẻ nhớ:** 
   - Tắt máy và cắm thẻ nhớ SD (chứa hệ điều hành **muOS**) vào máy tính.
   - Chép file cài đặt vào thư mục `Archive` trên thẻ nhớ (đường dẫn: `MUOS/archive/` hoặc góc ngoài thẻ nhớ tùy cấu hình).
   - Eject (ngắt kết nối an toàn) và rút thẻ nhớ ra.
3. **Cài đặt trên thiết bị:** 
   - Cắm thẻ nhớ lại vào máy handheld và bật nguồn.
   - Kết nối Wi-Fi (**Configuration > Wi-Fi Network**).
   - Vào **Applications > Archive Manager** (hoặc Archive), chọn file cài đặt `ThoiTietVN` để máy tiến hành tự động giải nén & cài đặt.
4. **Trải nghiệm:** Sau khi cài đặt hoàn tất, vào mục **Applications** trên muOS và chọn **Thời Tiết VN**.

---

## 🎮 Hướng Dẫn Điều Khiển (Controls)

| Phím bấm | Thao tác / Chức năng |
| :--- | :--- |
| **Trái / Phải** | Đổi tỉnh / thành phố |
| **L1 / R1** | Đổi màn hình (*Hiện tại* ↔ *7 ngày* ↔ *Toàn quốc*) |
| **Lên / Xuống** | Cuộn danh sách (tại màn hình *Toàn quốc*) |
| **Phím A** | Xem chi tiết thành phố đang chọn (tại màn hình *Toàn quốc*) |
| **Phím X** | Làm mới dữ liệu thời tiết ngay lập tức |
| **Phím Y** | Đặt thành phố hiện tại làm mặc định (★) |
| **Phím B / START** | Thoát ứng dụng |

---

## 🛠️ Khắc Phục Sự Cố

- **Kiểm tra nhật ký lỗi:** Mở file `weather.log` trong thư mục ứng dụng để xem chi tiết.
- **Nút bấm bị sai:** Ứng dụng ưu tiên theo mapping tay cầm của muOS. Nếu màn hình báo `"Nút #n chưa gán"`, hãy chỉnh sửa lại mã số nút bấm trong file `config.json` tại mục `"joystick_buttons"`.
- **Lỗi "Không tải được dữ liệu":** Kiểm tra lại kết nối Wi-Fi. Ứng dụng sẽ tự động thử lần lượt các phương thức kết nối: HTTPS, `curl`, `wget`, và HTTP.

---

## 📜 Tín Dụng & Giấy Phép (Credits)

- **Dữ liệu thời tiết:** Cung cấp bởi [Open-Meteo.com](https://open-meteo.com/) (*Giấy phép CC BY 4.0*).
- **Font chữ:** Phông chữ [DejaVu Sans](https://dejavu-fonts.github.io/) (*Giấy phép mã nguồn tự do*).