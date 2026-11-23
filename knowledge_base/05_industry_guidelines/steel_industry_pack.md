# Cẩm nang Kiểm kê Carbon và Công nghệ Giảm phát thải Ngành Thép (Steel Industry Pack)

* **Phạm vi áp dụng:** Các nhà máy luyện cán thép, sản xuất phôi thép và gia công cơ khí kim loại đen (Mã HS 7201 - 7318).
* **Mức độ thâm dụng carbon:** Chiếm khoảng 7-9% tổng phát thải khí nhà kính toàn cầu và là ngành chịu ảnh hưởng mạnh nhất bởi cơ chế CBAM của EU.

---

## 1. Hai Tuyến Công nghệ Sản xuất Thép Chính

### Tuyến 1: Lò cao - Lò thổi oxy (BF-BOF: Blast Furnace - Basic Oxygen Furnace)
* **Nguyên liệu đầu vào:** Quặng sắt (Iron ore), Than cốc (Coke), Đá vôi (Limestone).
* **Cơ chế phản ứng:** Than cốc đóng vai trò vừa là chất khử hóa học (khử $Fe_2O_3$ thành $Fe$) vừa là nhiên liệu sinh nhiệt.
* **Đặc tính phát thải:** Thâm dụng carbon rất cao:
  * Suất phát thải trung bình: **1.8 - 2.3 tấn $CO_2e$ / tấn thép thô**.
  * Chủ yếu là phát thải trực tiếp Scope 1 từ phản ứng khử hóa học và khí thải lò cao ($CO, CO_2$).

### Tuyến 2: Lò điện hồ quang (EAF: Electric Arc Furnace)
* **Nguyên liệu đầu vào:** Thép phế liệu (Steel scrap) hoặc Sắt xốp khử trực tiếp (DRI).
* **Cơ chế phản ứng:** Dùng năng lượng điện cao thế tạo hồ quang điện để nấu chảy thép phế liệu.
* **Đặc tính phát thải:** Thấp hơn nhiều so với tuyến lò cao:
  * Suất phát thải trung bình: **0.4 - 0.7 tấn $CO_2e$ / tấn thép thô**.
  * Phát thải trực tiếp (Scope 1) rất ít (chủ yếu từ điện cực than chì bị ăn mòn và phun xỉ bọt).
  * Phát thải tập trung chủ yếu ở **Scope 2 (Điện năng tiêu thụ cao)**. Vì vậy, suất phát thải của thép EAF phụ thuộc trực tiếp vào mức độ "xanh" của lưới điện quốc gia ($EF_{grid}$).

---

## 2. Các Nguồn Phát thải Cần Kiểm kê trong Nhà máy Thép

| Nguồn phát thải | Phân loại Scope | Thiết bị / Hoạt động phát sinh | Phương pháp tính toán |
|---|---|---|---|
| **Đốt than cốc và than phun** | Scope 1 | Lò cao (Blast Furnace), Lò thiêu kết quặng (Sinter plant) | Khối lượng than tiêu thụ $\times$ Hệ số phát thải than |
| **Phản ứng khử đá vôi / đolomit** | Scope 1 | Lò vôi, Lò thổi BOF (Tạo xỉ khử tạp chất) | Khối lượng đá vôi $\times$ Hàm lượng $CaCO_3 \times \frac{44}{100}$ |
| **Ăn mòn điện cực than chì** | Scope 1 | Lò điện hồ quang EAF, Lò tinh luyện LF | Khối lượng điện cực tiêu hao $\times 3.664 \text{ tCO}_2/\text{tấn C}$ |
| **Đốt khí gas / dầu DO** | Scope 1 | Lò nung phôi cán lại (Reheating furnace) | Tiêu thụ khí CNG/LPG/Dầu $\times$ Hệ số phát thải |
| **Điện năng tiêu thụ** | Scope 2 | Lò EAF, Động cơ máy cán thép, Trạm biến áp | Sản lượng $kWh$ $\times$ Hệ số phát thải lưới điện VN |
| **Vận chuyển quặng / phế liệu** | Scope 3 | Xe tải, tàu hàng chở quặng sắt và thép vụn | Tấn-km $\times$ Hệ số phát thải phương tiện vận tải |

---

## 3. Lộ trình và Giải pháp Giảm phát thải Ngành Thép (Decarbonization)
1. **Chuyển dịch cơ cấu công nghệ:** Tăng tỷ trọng sản xuất thép bằng lò điện hồ quang (EAF) từ phế liệu thay thế dần các lò cao dung tích nhỏ gây ô nhiễm.
2. **Thu hồi năng lượng nhiệt thải (WHR):** Lắp đặt hệ thống thu hồi nhiệt thải từ khói lò cán thép để phát điện tự dùng.
3. **Sử dụng điện sạch:** Lắp đặt điện mặt trời mái nhà xưởng và ký hợp đồng mua bán điện trực tiếp (DPPA) với các trang trại điện gió/điện mặt trời.
4. **Công nghệ tương lai (Sau 2030):** Sử dụng Hydro xanh (Green Hydrogen) để khử trực tiếp quặng sắt (H2-DRI) thay cho than cốc, tạo ra "Thép xanh" không phát thải.
