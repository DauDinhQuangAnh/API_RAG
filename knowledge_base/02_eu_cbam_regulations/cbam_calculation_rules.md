# Phương pháp và Công thức Tính toán Phát thải Gắn trong Hàng hóa theo CBAM

* **Căn cứ pháp lý:** Phụ lục IV của Regulation (EU) 2023/956 và Hướng dẫn kỹ thuật của Ủy ban Châu Âu (Guidance document on CBAM implementation for installation operators outside the EU).

---

## 1. Khái niệm Phát thải Gắn liền (Embedded Emissions)
Phát thải gắn liền là tổng lượng khí nhà kính phát thải trong quá trình sản xuất ra một đơn vị sản phẩm (tính bằng tấn $CO_2e$ trên mỗi tấn sản phẩm - $tCO_2e / \text{tấn}$).
CBAM phân chia hàng hóa thành 2 nhóm:
* **Hàng hóa Đơn giản (Simple Goods):** Hàng hóa được sản xuất chỉ từ nguyên liệu thô và nhiên liệu không chứa phát thải gắn liền (ví dụ: clinker nung từ đá vôi, hydro sản xuất bằng điện phân).
* **Hàng hóa Phức hợp (Complex Goods):** Hàng hóa được sản xuất bằng cách sử dụng các hàng hóa khác cũng thuộc phạm vi điều chỉnh của CBAM làm tiền chất (Precursors). Ví dụ: Thép tấm cán nguội được làm từ phôi thép (tiền chất).

---

## 2. Công thức tính toán cho Hàng hóa Đơn giản

Đối với hàng hóa đơn giản $g$, lượng phát thải riêng trực tiếp ($SEE_g$) được tính bằng:

$$SEE_g = \frac{AttrEm_g}{AL_g}$$

Trong đó:
* $SEE_g$: Lượng phát thải riêng gắn liền trực tiếp của hàng hóa $g$ ($tCO_2e / \text{tấn}$).
* $AttrEm_g$: Tổng lượng phát thải trực tiếp được phân bổ cho quy trình sản xuất hàng hóa $g$ trong kỳ báo cáo ($tCO_2e$).
* $AL_g$: Tổng sản lượng hàng hóa $g$ được sản xuất trong kỳ báo cáo (tấn).

---

## 3. Công thức tính toán cho Hàng hóa Phức hợp

Đối với hàng hóa phức hợp, lượng phát thải gắn liền bao gồm cả phát thải của chính quy trình đó cộng với phát thải từ các tiền chất (Precursors) được tiêu thụ:

$$SEE_g = \frac{AttrEm_g + \sum_{i=1}^n M_{prec,i} \cdot SEE_{prec,i}}{AL_g}$$

Trong đó:
* $M_{prec,i}$: Khối lượng tiền chất $i$ được tiêu thụ trong quy trình sản xuất ra sản lượng $AL_g$ của hàng hóa $g$.
* $SEE_{prec,i}$: Lượng phát thải riêng gắn liền trực tiếp của tiền chất $i$ ($tCO_2e / \text{tấn}$).

---

## 4. Phát thải Gián tiếp (Indirect Embedded Emissions)
Phát thải gián tiếp phát sinh từ lượng điện năng tiêu thụ trong quá trình sản xuất:

$$SEE_{indir, g} = \frac{Em_{indir, g}}{AL_g} = \frac{E_{cons, g} \cdot EF_{el}}{AL_g}$$

Trong đó:
* $E_{cons, g}$: Tổng lượng điện năng tiêu thụ để sản xuất ra hàng hóa $g$ ($MWh$).
* $EF_{el}$: Hệ số phát thải của điện năng ($tCO_2 / MWh$). Theo quy định CBAM, ưu tiên sử dụng:
  1. Hợp đồng mua bán điện trực tiếp (PPA) hoặc nguồn phát điện tại chỗ (điện mặt trời mái nhà, nhà máy điện tự cấp).
  2. Hệ số phát thải trung bình lưới điện của quốc gia xuất xứ (Việt Nam).
  3. Giá trị mặc định của EU do Ủy ban Châu Âu công bố.

---

## 5. Phân bổ nhiệt lượng và sản phẩm phụ (Co-products)
Khi quy trình sản xuất sinh ra nhiều sản phẩm đồng thời (ví dụ: sản phẩm chính và sản phẩm phụ), việc phân bổ phát thải phải thực hiện theo nguyên tắc:
1. **Phân bổ theo tỷ lệ kinh tế:** Dựa trên giá trị thị trường của từng sản phẩm nếu không thể tách riêng mặt vật lý.
2. **Phân bổ theo nhiệt trị hoặc khối lượng:** Áp dụng cho các sản phẩm năng lượng hoặc có bản chất vật lý tương đồng.
3. Các phế liệu, chất thải không có giá trị kinh tế sẽ không được phân bổ phát thải (phát thải dồn hết cho sản phẩm hữu ích).
