# Hệ số Phát thải Giao thông Vận tải và Logistics (Scope 3 Upstream & Downstream)

* **Căn cứ chuẩn mực:** DEFRA (Bộ Môi trường, Thực phẩm và Nông thôn Vương quốc Anh) và GLEC Framework (Global Logistics Emissions Council).
* **Ứng dụng:** Tính toán phát thải chuỗi cung ứng, vận chuyển nguyên vật liệu từ nhà cung cấp về nhà máy (Upstream Transportation) và vận chuyển thành phẩm xuất khẩu sang cảng/châu Âu (Downstream Transportation).

---

## 1. Đơn vị đo lường trong Logistics Carbon Footprint
Phát thải vận chuyển hàng hóa được tính theo đơn vị:
$$\text{Tấn-Kilômét} \ (\text{Tonne-Kilometre - } \text{t.km})$$
$$\text{Lượng luân chuyển hàng hóa} = \text{Khối lượng hàng (tấn)} \times \text{Quãng đường vận chuyển (km)}$$

---

## 2. Bảng Hệ số Phát thải Vận tải theo Phương thức (DEFRA / GLEC)

| Phương thức vận tải | Loại phương tiện chi tiết | Hệ số phát thải ($kg CO_2e / \text{t.km}$) | Ghi chú mức tải trung bình |
|---|---|---|---|
| **Đường bộ (Road)** | Xe tải thùng 3.5 - 7.5 tấn | **0.5512** | Mức tải trung bình 50% |
| **Đường bộ (Road)** | Xe tải nặng 7.5 - 17 tấn | **0.3120** | Xe tải vận chuyển liên tỉnh |
| **Đường bộ (Road)** | Xe đầu kéo Container (>33 tấn) | **0.0894** | Vận chuyển container từ nhà máy ra cảng biển |
| **Đường sắt (Rail)** | Tàu hỏa chở hàng diesel | **0.0275** | Tuyến đường sắt Bắc - Nam |
| **Đường thủy nội địa (Inland Waterway)** | Sà lan chở hàng rời / container | **0.0336** | Vận tải thủy Đồng bằng sông Cửu Long / sông Hồng |
| **Đường biển (Maritime)** | Tàu Container cỡ lớn (>8.000 TEU) | **0.0152** | Tuyến vận tải biển Việt Nam - Châu Âu (Rotterdam, Hamburg) |
| **Đường biển (Maritime)** | Tàu hàng rời (Bulk Carrier) | **0.0078** | Vận chuyển quặng, than, xi măng đường biển |
| **Đường hàng không (Air Freight)** | Máy bay chở hàng chuyên dụng | **1.2150** | Vận chuyển hàng mẫu dệt may, linh kiện điện tử gấp |

*Nhận xét:* Vận tải đường biển có suất phát thải thấp nhất trên mỗi tấn-km ($0.0152 kgCO_2e/t.km$), thấp hơn gần 6 lần so với xe container đường bộ ($0.0894$) và thấp hơn 80 lần so với vận tải hàng không.

---

## 3. Ví dụ Tính toán Phát thải Lô hàng Xuất khẩu từ Việt Nam sang EU

**Bài toán:** Xuất khẩu 20 tấn cuộn thép mạ kẽm từ nhà máy tại Khu công nghiệp Nhơn Trạch (Đồng Nai) sang cảng Rotterdam (Hà Lan):
1. **Chặng 1 (Đường bộ):** Vận chuyển bằng xe container từ Nhơn Trạch đến Cảng Cái Mép (Vũng Tàu), cự ly $50 \text{ km}$.
   $$E_1 = 20 \text{ tấn} \times 50 \text{ km} \times 0.0894 \text{ kg}CO_2e/\text{t.km} = 89,4 \text{ kg}CO_2e$$
2. **Chặng 2 (Đường biển):** Vận chuyển bằng tàu biển từ Cảng Cái Mép sang Cảng Rotterdam, cự ly khoảng $16.500 \text{ km}$.
   $$E_2 = 20 \text{ tấn} \times 16.500 \text{ km} \times 0.0152 \text{ kg}CO_2e/\text{t.km} = 5.016,0 \text{ kg}CO_2e$$
3. **Tổng phát thải vận chuyển lô hàng (Scope 3):**
   $$E_{total} = 89,4 + 5.016,0 = 5.105,4 \text{ kg}CO_2e \approx 5,11 \text{ tấn } CO_2e$$
   Suất phát thải vận tải trên mỗi tấn thép:
   $$e = \frac{5.105,4}{20} = 255,27 \text{ kg}CO_2e / \text{tấn thép}$$
