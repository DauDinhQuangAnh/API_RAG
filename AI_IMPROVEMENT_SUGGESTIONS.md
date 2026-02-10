# AI Improvement Suggestions - Context & API Design

## Tổng quan

Phần "Gợi ý cải thiện từ AI" (Section G) trong trang Chi tiết Carbon Footprint cần đủ ngữ cảnh sản phẩm để LLM có thể đưa ra gợi ý hợp lý.

---

## Thông tin cần thu thập (Context Parameters)

### 1. Product Basic Info

| Parameter           | Type   | Mô tả                                  | Bắt buộc |
| ------------------- | ------ | -------------------------------------- | -------- |
| `productType`       | string | Loại sản phẩm (áo thun, quần, giày...) | ✅       |
| `productWeight`     | number | Khối lượng (gram)                      | ✅       |
| `quantity`          | number | Số lượng trong batch                   | ✅       |
| `destinationMarket` | string | Thị trường xuất khẩu (EU, US, JP...)   | ✅       |

### 2. Carbon Breakdown

| Parameter                 | Type   | Mô tả                        | Bắt buộc |
| ------------------------- | ------ | ---------------------------- | -------- |
| `totalCo2e`               | number | Tổng CO2e (kg)               | ✅       |
| `breakdown.materials`     | number | CO2e vật liệu                | ✅       |
| `breakdown.manufacturing` | number | CO2e sản xuất                | ✅       |
| `breakdown.transport`     | number | CO2e vận chuyển              | ✅       |
| `breakdown.packaging`     | number | CO2e đóng gói                | ⬜       |
| `breakdown.end_of_life`   | number | CO2e cuối vòng đời           | ⬜       |
| `highestStage`            | string | Giai đoạn phát thải cao nhất | ✅       |

### 3. Material Details

| Parameter                    | Type     | Mô tả                     | Bắt buộc |
| ---------------------------- | -------- | ------------------------- | -------- |
| `materials[].name`           | string   | Tên vật liệu              | ✅       |
| `materials[].percentage`     | number   | Tỷ lệ %                   | ✅       |
| `materials[].emissionFactor` | number   | Hệ số phát thải           | ✅       |
| `materials[].isRecycled`     | boolean  | Có phải tái chế không     | ✅       |
| `materials[].certifications` | string[] | Chứng nhận (GOTS, GRS...) | ⬜       |
| `materials[].source`         | string   | Nguồn (documented/proxy)  | ✅       |

### 4. Manufacturing Info

| Parameter                    | Type     | Mô tả                     | Bắt buộc |
| ---------------------------- | -------- | ------------------------- | -------- |
| `energySources[].type`       | string   | Loại năng lượng           | ✅       |
| `energySources[].percentage` | number   | Tỷ lệ %                   | ✅       |
| `manufacturingLocation`      | string   | Vị trí sản xuất           | ✅       |
| `processes[]`                | string[] | Quy trình (dệt, nhuộm...) | ⬜       |

### 5. Transport Info

| Parameter                  | Type    | Mô tả                           | Bắt buộc |
| -------------------------- | ------- | ------------------------------- | -------- |
| `transportLegs[].mode`     | string  | Phương thức (sea/air/road/rail) | ✅       |
| `transportLegs[].distance` | number  | Khoảng cách (km)                | ✅       |
| `totalDistance`            | number  | Tổng khoảng cách                | ✅       |
| `hasAirFreight`            | boolean | Có dùng hàng không không        | ✅       |

### 6. End-of-Life Info

| Parameter              | Type    | Mô tả                                         | Bắt buộc |
| ---------------------- | ------- | --------------------------------------------- | -------- |
| `endOfLifeStrategy`    | string  | Chiến lược (no_takeback/selective/data_based) | ⬜       |
| `recyclablePercentage` | number  | % có thể tái chế                              | ⬜       |
| `hasTakebackProgram`   | boolean | Có chương trình thu hồi                       | ⬜       |

### 7. Confidence & Compliance

| Parameter             | Type     | Mô tả                 | Bắt buộc |
| --------------------- | -------- | --------------------- | -------- |
| `confidenceScore`     | number   | Điểm tin cậy (0-100)  | ✅       |
| `proxyDataPercentage` | number   | % dữ liệu proxy       | ✅       |
| `complianceGaps[]`    | string[] | Các tiêu chí chưa đạt | ⬜       |
| `exportReady`         | boolean  | Đã sẵn sàng xuất khẩu | ✅       |

---

## Database Query - Thu thập ngữ cảnh

```sql
-- Query để thu thập đủ thông tin cho AI suggestions
SELECT
  -- Product basic
  p.id as product_id,
  p.name as product_name,
  p.category as product_type,
  p.weight_kg * 1000 as weight_grams,
  p.status,

  -- Carbon totals
  p.total_co2e,
  p.materials_co2e,
  p.production_co2e,
  p.transport_co2e,
  p.packaging_co2e,
  p.data_confidence_score,

  -- Company context
  c.target_markets,
  c.business_type,

  -- Materials with factors
  (
    SELECT json_agg(json_build_object(
      'name', m.name,
      'percentage', pm.percentage,
      'emission_factor', m.default_co2e_per_kg,
      'is_recycled', m.is_recycled,
      'certifications', m.certifications,
      'category', m.category
    ))
    FROM product_materials pm
    JOIN materials m ON pm.material_id = m.id
    WHERE pm.product_id = p.id
  ) as materials,

  -- Transport info
  (
    SELECT json_agg(json_build_object(
      'mode', sl.transport_mode,
      'distance_km', sl.distance_km,
      'co2e', sl.co2e
    ))
    FROM shipments s
    JOIN shipment_legs sl ON s.id = sl.shipment_id
    JOIN shipment_products sp ON s.id = sp.shipment_id
    WHERE sp.product_id = p.id
  ) as transport_legs

FROM products p
JOIN companies c ON p.company_id = c.id
WHERE p.id = $1;
```

---

## Quy tắc tính toán context

### Xác định giai đoạn phát thải cao nhất

```typescript
function getHighestStage(breakdown: CarbonBreakdown): string {
  const stages = [
    { stage: 'materials', co2e: breakdown.materials },
    { stage: 'manufacturing', co2e: breakdown.production },
    { stage: 'transport', co2e: breakdown.transport },
    { stage: 'packaging', co2e: breakdown.packaging || 0 },
  ];
  return stages.sort((a, b) => b.co2e - a.co2e)[0].stage;
}
```

---

---

## API Call to LLM

### Endpoint

```
POST /functions/v1/generate-suggestions
```

### Request Body

```json
{
  "productContext": {
    "productType": "tshirt",
    "productWeight": 250,
    "destinationMarket": "eu",
    "totalCo2e": 4.48,
    "breakdown": {
      "materials": 2.45,
      "manufacturing": 1.35,
      "transport": 0.50,
      "packaging": 0.18
    },
    "highestStage": "materials",
    "materials": [
      { "name": "Recycled Polyester", "percentage": 60, "emissionFactor": 2.1, "isRecycled": true },
      { "name": "Cotton", "percentage": 40, "emissionFactor": 8.3, "isRecycled": false }
    ],
    "energySources": [
      { "type": "grid", "percentage": 100 }
    ],
    "transportLegs": [
      { "mode": "road", "distance": 200 },
      { "mode": "sea", "distance": 10000 }
    ],
    "confidenceScore": 78,
    "exportReady": false
  }
}
```

### System Prompt cho LLM

```
Bạn là chuyên gia tư vấn bền vững cho ngành dệt may Việt Nam.

## Ngữ cảnh dự án
WeaveCarbon là nền tảng SaaS giúp doanh nghiệp SME ngành thời trang/dệt may Việt Nam đo lường, quản lý và tối ưu hóa dấu chân carbon (carbon footprint) của sản phẩm. Hệ thống hỗ trợ:
- Đánh giá carbon theo vòng đời sản phẩm (LCA): vật liệu, sản xuất, vận chuyển, đóng gói, end-of-life
- Quản lý chuỗi cung ứng và logistics đa chặng (đường bộ, đường biển, đường hàng không, đường sắt)
- Đảm bảo tuân thủ quy định xuất khẩu: EU CBAM, US Climate Act, JP JIS, KR K-ETS
- Theo dõi mục tiêu giảm phát thải theo tháng

Đối tượng người dùng chính là các doanh nghiệp vừa và nhỏ (SME) Việt Nam trong ngành dệt may, có nhu cầu xuất khẩu sang EU, US, Nhật Bản, Hàn Quốc.

## Nhiệm vụ
Dựa trên dữ liệu carbon footprint chi tiết của một sản phẩm cụ thể được cung cấp, hãy đưa ra đúng 3 gợi ý cải thiện cấp sản phẩm để giảm carbon footprint.

## Yêu cầu mỗi gợi ý:
1. Tiêu đề ngắn gọn (< 50 ký tự)
2. Mô tả cụ thể, hành động được (action + expected outcome, 1-2 câu)
3. Ước tính % giảm phát thải (số nguyên, dựa trên industry benchmarks)
4. Mức độ khó thực hiện: easy/medium/hard
5. Danh mục: material/transport/manufacturing/packaging/end_of_life

## Nguyên tắc ưu tiên:
- Ưu tiên gợi ý cho giai đoạn phát thải cao nhất
- Phù hợp với quy mô và nguồn lực SME Việt Nam
- Khả thi và có thể hành động ngay
- Xem xét thị trường xuất khẩu để ưu tiên compliance-related suggestions
- Mỗi gợi ý nên thuộc danh mục khác nhau để đa dạng hóa chiến lược

## Format output
Trả về mảng JSON gồm đúng 3 object, mỗi object có các trường: id, type, title, description, potentialReduction, difficulty.
```

### Response Format

```json
{
  "suggestions": [
    {
      "id": "ai-sug-001",
      "type": "material",
      "title": "Tăng tỷ lệ polyester tái chế",
      "description": "Nâng recycled polyester từ 60% lên 85% có thể giảm 20% phát thải vật liệu, đồng thời đáp ứng yêu cầu EU Green Deal",
      "potentialReduction": 12,
      "difficulty": "medium"
    }
  ]
}
```

---

## Trạng thái triển khai

| Component            | Status     | Notes                        |
| -------------------- | ---------- | ---------------------------- |
| Context collector    | ⏳ Pending | Cần implement query          |
| Edge function        | ⏳ Pending | Cần tạo generate-suggestions |
| Frontend integration | ⏳ Pending | Thay demo data bằng API call |
