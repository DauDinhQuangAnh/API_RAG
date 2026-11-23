# Bảng Hệ số Phát thải Nhiên liệu Đốt cháy Cố định và Di động (IPCC 2006)

* **Căn cứ khoa học:** Hướng dẫn kiểm kê khí nhà kính quốc gia năm 2006 của Ban Liên chính phủ về Biến đổi Khí hậu (2006 IPCC Guidelines for National Greenhouse Gas Inventories - Volume 2: Energy).
* **Ứng dụng:** Tính toán phát thải trực tiếp (Scope 1) từ quá trình đốt cháy nhiên liệu trong lò hơi, lò nung, máy phát điện, xe nâng và phương tiện vận tải nội bộ nhà máy.

---

## 1. Bảng Hệ số Phát thải Nhiên liệu Cố định (Stationary Combustion)

Bảng dưới đây quy định hệ số phát thải mặc định cho quá trình đốt nhiên liệu trong lò hơi, lò nung công nghiệp:

| Loại nhiên liệu | Đơn vị đo lường | Nhiệt trị ròng mặc định ($NCV$ - $TJ / Gg$ hoặc $MJ / kg$) | Hệ số phát thải $CO_2$ ($kg CO_2 / TJ$) | Hệ số phát thải $CO_2$ trên đơn vị vật lý | Ghi chú / Ứng dụng |
|---|---|---|---|---|---|
| **Than antraxit (Than cám VN)** | Tấn | 26.7 | 98.300 | **2.624,6 kg $CO_2$ / tấn** | Nhiệt điện, Lò hơi dệt nhuộm, Nhà máy xi măng |
| **Than bitum (Than nhập khẩu)** | Tấn | 25.8 | 94.600 | **2.440,7 kg $CO_2$ / tấn** | Nhà máy điện, luyện kim |
| **Dầu DO (Diesel Oil)** | Lít / Tấn | 43.0 | 74.100 | **2.680,0 kg $CO_2$ / $m^3$** (~2,68 kg/Lít) | Máy phát điện dự phòng, đầu đốt lò hơi |
| **Dầu FO (Fuel Oil)** | Tấn | 40.4 | 77.400 | **3.127,0 kg $CO_2$ / tấn** | Lò hơi công nghiệp nặng, sấy |
| **Khí dầu mỏ hóa lỏng (LPG)** | Tấn / kg | 47.3 | 63.100 | **2.984,6 kg $CO_2$ / tấn** (~2,98 kg/kg) | Lò nung gốm sứ, gia nhiệt kim loại |
| **Khí thiên nhiên nén (CNG)** | $1.000 Nm^3$ | 48.0 | 56.100 | **2.020,0 kg $CO_2$ / $1000 Nm^3$** | Nhiên liệu sạch cho lò hơi hiện đại |
| **Sinh khối - Viên nén gỗ (Wood Pellets)** | Tấn | 17.5 | 112.000 (Biogenic) | **0 kg $CO_2$ / tấn (Net Fossil)** | $CO_2$ sinh học được tính bằng 0 trong Scope 1 hóa thạch |
| **Trấu / Bã mía (Biomass)** | Tấn | 15.0 | 100.000 (Biogenic) | **0 kg $CO_2$ / tấn (Net Fossil)** | Chỉ tính phát thải vết $CH_4$ và $N_2O$ |

*Lưu ý về Sinh khối (Biomass):* Theo hướng dẫn GHG Protocol và IPCC, khí $CO_2$ phát thải từ việc đốt sinh khối bền vững (gỗ, mùn cưa, trấu) được coi là phát thải sinh học (Biogenic $CO_2$) thuộc chu trình carbon ngắn, do đó được báo cáo riêng và **không cộng vào tổng phát thải Scope 1 hóa thạch**.

---

## 2. Công thức tính toán phát thải đốt cháy nhiên liệu (Tier 1)

$$E_{Scope 1} = \sum_{i} \left( Q_i \cdot NCV_i \cdot EF_{CO_2, i} \cdot 10^{-3} \right)$$

Trong đó:
* $E_{Scope 1}$: Tổng lượng phát thải $CO_2$ từ đốt nhiên liệu ($tCO_2$).
* $Q_i$: Khối lượng hoặc thể tích nhiên liệu loại $i$ tiêu thụ (tấn, lít, $m^3$).
* $NCV_i$: Nhiệt trị ròng của nhiên liệu $i$ ($TJ / \text{đơn vị}$ hoặc $GJ / \text{đơn vị}$).
* $EF_{CO_2, i}$: Hệ số phát thải $CO_2$ của nhiên liệu $i$ ($kg CO_2 / TJ$).
* Nếu sử dụng trực tiếp hệ số phát thải trên đơn vị vật lý ($EF_{phy, i}$):

$$E_{Scope 1} = \sum_{i} \left( Q_i \cdot EF_{phy, i} \cdot 10^{-3} \right)$$

*Ví dụ tính toán:*
Một nhà máy sử dụng $500 \text{ tấn}$ than cám antraxit trong tháng:
$$E = 500 \cdot 2.624,6 \cdot 10^{-3} = 1.312,3 \text{ tấn } CO_2$$
