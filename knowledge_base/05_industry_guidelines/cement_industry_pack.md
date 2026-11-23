# Cẩm nang Kiểm kê Carbon và Công nghệ Giảm phát thải Ngành Xi măng (Cement Industry Pack)

* **Phạm vi áp dụng:** Các nhà máy sản xuất Clinker, trạm nghiền xi măng, cơ sở sản xuất xi măng poóc lăng (Mã CN 2523).
* **Mức độ thâm dụng carbon:** Chiếm khoảng 7-8% tổng lượng phát thải $CO_2$ toàn cầu và là ngành công nghiệp vật liệu xây dựng phát thải lớn nhất tại Việt Nam.

---

## 1. Cơ chế Phát sinh Khí nhà kính trong Sản xuất Xi măng

Sản xuất xi măng có cấu trúc phát thải rất đặc thù: **Phần lớn phát thải đến từ phản ứng phân hủy hóa học của nguyên liệu (Process emissions), không chỉ đơn thuần là do đốt nhiên liệu**:

```
                                    TỔNG PHÁT THẢI SẢN XUẤT CLINKER
                                                 │
                  ┌──────────────────────────────┴──────────────────────────────┐
                  ▼                                                             ▼
     [Phát thải Phản ứng Hóa học (~60%)]                         [Phát thải Đốt cháy Nhiên liệu (~40%)]
Quá trình nung Canxi Cacbonat:                                Đốt than cám, dầu, rác thải để tạo nhiệt độ
$CaCO_3 \xrightarrow{t^\circ} CaO + CO_2 \uparrow$          nung luyện clinker lên $1450^\circ C$ trong lò quay
Phát thải cố định không thể tránh khỏi nếu dùng đá vôi
```

* **Suất phát thải trung bình:**
  * Sản xuất Clinker: **0.82 - 0.90 tấn $CO_2e$ / tấn Clinker**.
  * Sản xuất Xi măng thông thường (PCB40): **0.65 - 0.75 tấn $CO_2e$ / tấn xi măng**.

---

## 2. Công thức Kiểm kê Phát thải Quy trình Nung Canxi Cacbonat (IPCC Tier 2)

$$E_{process} = Q_{clinker} \cdot EF_{clinker}$$

Hệ số phát thải Clinker phụ thuộc vào hàm lượng Ô-xít Canxi ($CaO$) và Ô-xít Magiê ($MgO$) trong Clinker:

$$EF_{clinker} = \left( \%CaO \times \frac{44}{56} + \%MgO \times \frac{44}{40} \right) \times (1 - \%CaO_{non-carb}) \times CKD$$

Trong đó:
* $\frac{44}{56}$: Tỷ lệ phân tử lượng giữa $CO_2$ và $CaO$ ($= 0.7857$).
* $CKD$: Hệ số hiệu chỉnh bụi lò clinker thoát ra ngoài (thường lấy $1.02$).
* Giá trị mặc định quốc tế cho clinker: $0.525 \text{ tấn } CO_2 / \text{tấn Clinker}$.

---

## 3. Các Giải pháp Giảm phát thải Trọng điểm cho Ngành Xi măng (Decarbonization)
1. **Thay thế Clinker bằng phụ gia khoáng hoạt tính:**
   * Tăng cường sử dụng xỉ hạt lò cao (GGBS), tro bay nhiệt điện (Fly ash), puzolan hoặc đá vôi mịn để thay thế một phần clinker trong xi măng thành phẩm. Giảm tỷ lệ clinker/xi măng từ 85% xuống 65-70% giúp giảm phát thải tức thì 20%.
2. **Đồng xử lý chất thải làm nhiên liệu thay thế (Alternative Fuels - AF):**
   * Sử dụng rác thải sinh hoạt RDF, lốp xe cũ cắt nhỏ, bùn thải công nghiệp, sinh khối (vỏ hạt điều, mùn cưa) thay thế than cám trong vòi đốt lò quay. Tỷ lệ thay thế nhiệt (TSR) tại châu Âu đạt >50%, tại Việt Nam đang phấn đấu đạt 15-20%.
3. **Lắp đặt hệ thống phát điện tận dụng nhiệt thừa khí thải (WHR):**
   * Tận dụng nhiệt khí thải ở tháp trao đổi nhiệt ($SP$) và tháp làm nguội clinker ($AQC$) để chạy tuabin phát điện, đáp ứng 25 - 30% tổng nhu cầu điện của toàn nhà máy, giảm đáng kể phát thải Scope 2.
