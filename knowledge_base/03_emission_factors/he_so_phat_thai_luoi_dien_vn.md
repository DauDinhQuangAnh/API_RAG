# Hệ số Phát thải Lưới điện Quốc gia Việt Nam (Grid Emission Factor)

* **Cơ quan ban hành:** Cục Biến đổi khí hậu — Bộ Tài nguyên và Môi trường Việt Nam (DCC - MONRE).
* **Ứng dụng:** Tính toán phát thải khí nhà kính gián tiếp do tiêu thụ điện năng (Scope 2) cho các tổ chức, doanh nghiệp và nhà máy trên toàn lãnh thổ Việt Nam.

---

## 1. Bảng Hệ số Phát thải Lưới điện Việt Nam qua các năm

Hệ số phát thải lưới điện (Grid Emission Factor - $EF_{grid}$) của Việt Nam được tính toán theo phương pháp luận của Ban điều hành Cơ chế phát triển sạch (CDM Executive Board - UNFCCC), tính trên mức phát thải trung bình của toàn bộ các nhà máy điện phát vào lưới điện quốc gia (nhiệt điện than, nhiệt điện khí, thủy điện, năng lượng tái tạo):

| Năm công bố | Áp dụng cho kỳ kiểm kê | Hệ số phát thải ($tCO_2 / MWh$) | Hệ số quy đổi ($kgCO_2 / kWh$) | Văn bản công bố |
|---|---|---|---|---|
| **2023** | 2022 - 2023 | **0.6766** | **0.6766** | Công văn số 263/BĐKH-TTBĐKH của Cục Biến đổi khí hậu |
| **2022** | 2021 - 2022 | **0.7221** | **0.7221** | Công văn số 1184/BĐKH-TTBĐKH của Cục Biến đổi khí hậu |
| **2021** | 2020 - 2021 | **0.8034** | **0.8034** | Công văn số 672/BĐKH-TTBĐKH của Cục Biến đổi khí hậu |
| **2020** | 2019 - 2020 | **0.8649** | **0.8649** | Công văn số 215/BĐKH-TTBĐKH của Cục Biến đổi khí hậu |
| **2019** | 2018 - 2019 | **0.9130** | **0.9130** | Công văn số 136/BĐKH-TTBĐKH của Cục Biến đổi khí hậu |

*Nhận xét xu hướng:* Hệ số phát thải lưới điện Việt Nam có xu hướng giảm đều qua các năm nhờ việc đưa vào vận hành nhiều dự án điện mặt trời, điện gió và thủy điện, giúp giảm mức phát thải carbon trên mỗi kWh điện tiêu thụ.

---

## 2. Công thức tính phát thải Scope 2 từ điện năng tiêu thụ

$$E_{Scope 2} = Q_{electricity} \cdot EF_{grid}$$

Trong đó:
* $E_{Scope 2}$: Lượng phát thải khí nhà kính Scope 2 phát sinh ($tCO_2e$).
* $Q_{electricity}$: Tổng sản lượng điện năng tiêu thụ lấy từ hóa đơn tiền điện hoặc chỉ số công tơ tổng ($MWh$). Nếu hóa đơn ghi $kWh$, chia cho 1.000 để ra $MWh$.
* $EF_{grid}$: Hệ số phát thải lưới điện của năm tương ứng ($tCO_2 / MWh$).

*Ví dụ tính toán:*
Một nhà máy dệt may tiêu thụ $1.500.000 \text{ kWh}$ điện lưới trong năm 2023:
$$Q_{electricity} = 1.500 \text{ MWh}$$
Áp dụng $EF_{grid} = 0.6766 \text{ tCO}_2 / \text{MWh}$:
$$E_{Scope 2} = 1.500 \cdot 0.6766 = 1.014,9 \text{ tCO}_2e$$

---

## 3. Quy tắc khấu trừ điện mặt trời mái nhà tự dùng (On-site Solar)
* Lượng điện mặt trời mái nhà do cơ sở tự đầu tư sản xuất và tiêu thụ tại chỗ (không phát lên lưới) có **hệ số phát thải bằng 0 ($EF = 0 \text{ tCO}_2/MWh$)**.
* Cơ sở chỉ phải tính phát thải cho phần điện năng nhận từ lưới điện EVN.
* Doanh nghiệp phải xuất trình được biên bản nghiệm thu hệ thống điện mặt trời, đồng hồ đo đếm sản lượng điện mặt trời độc lập để kiểm toán viên xác nhận.
