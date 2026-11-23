# Phương pháp Phân bổ Phát thải Đa tầng cho Sản phẩm (Dynamic Allocation Rules)

* **Chuẩn mực tham chiếu:** ISO 14044 (Đánh giá Vòng đời Sản phẩm - LCA), GHG Protocol Product Life Cycle Standard, và Quy tắc Phân bổ Sản phẩm CBAM.
* **Mục đích:** Khi một nhà máy hoặc dây chuyền sản xuất tạo ra đồng thời nhiều loại sản phẩm và sản phẩm phụ (Co-products), làm sao phân bổ công bằng lượng phát thải tổng thể của nhà máy cho từng sản phẩm cụ thể.

---

## 1. Cây Phân cấp Phân bổ (Hierarchy of Allocation Methods)

Theo ISO 14044 và GHG Protocol, thứ tự ưu tiên khi thực hiện phân bổ phát thải:

```
[Mức 1: Tránh phân bổ (Avoid Allocation)]
   │ ├── Tách nhỏ quy trình phụ (Sub-division)
   │ └── Mở rộng hệ thống (System Expansion / Substitution)
   ▼
[Mức 2: Phân bổ theo Quan hệ Vật lý (Physical Allocation)]
   │ ├── Tỷ lệ khối lượng (Mass allocation)
   │ ├── Tỷ lệ thể tích / diện tích
   │ └── Tỷ lệ nhiệt trị (Energy / Calorific allocation)
   ▼
[Mức 3: Phân bổ theo Quan hệ Kinh tế (Economic Allocation)]
     └── Tỷ lệ giá trị thị trường doanh thu (Economic / Market value)
```

---

## 2. Chi tiết các Phương pháp Phân bổ

### Phương pháp 1: Phân bổ theo Khối lượng (Mass Allocation)
Áp dụng khi các sản phẩm đầu ra có cùng bản chất vật lý và giá trị tương đương:

$$E_i = E_{total} \times \frac{M_i}{\sum_{j=1}^n M_j}$$

* Trong đó:
  * $E_i$: Lượng phát thải phân bổ cho sản phẩm $i$.
  * $E_{total}$: Tổng lượng phát thải của phân xưởng.
  * $M_i$: Khối lượng sản phẩm $i$ sản xuất ra.

### Phương pháp 2: Phân bổ theo Kinh tế (Economic Allocation)
Bắt buộc áp dụng khi sản phẩm chính và sản phẩm phụ có giá trị chênh lệch quá lớn (ví dụ: dầu cọ tinh luyện và bã cọ, hoặc phôi thép cao cấp và xỉ lò cao):

$$E_i = E_{total} \times \frac{M_i \cdot P_i}{\sum_{j=1}^n (M_j \cdot P_j)}$$

* Trong đó:
  * $P_i$: Giá bán đơn vị trên thị trường của sản phẩm $i$ tại cổng nhà máy (Ex-works price).
  * $M_i \cdot P_i$: Tổng doanh thu tiềm năng của sản phẩm $i$.

---

## 3. Quy tắc đối với Phế liệu và Chất thải (Waste & Scrap Rules)
* **Chất thải (Waste):** Đầu ra không có giá trị kinh tế (giá bán $\le 0$) sẽ **không nhận bất kỳ lượng phát thải nào**. Toàn bộ phát thải của quá trình xử lý chất thải được tính dồn cho các sản phẩm chính.
* **Phế liệu tái chế nội bộ (Internal Scrap / Run-around scrap):** Phế liệu đầu thừa đuôi thẹo đưa ngược lại đầu lò nung không được coi là sản phẩm xuất khẩu và không làm giảm phát thải của chu trình.
* **Sản phẩm phụ có giá trị kinh tế thấp (Low-value by-products):** Ví dụ như xỉ hạt lò cao nghiền mịn (GGBS) trong ngành thép có thể được phân bổ phát thải theo giá trị kinh tế hoặc theo phương pháp khấu trừ nếu làm nguyên liệu thay thế cho clinker xi măng.
