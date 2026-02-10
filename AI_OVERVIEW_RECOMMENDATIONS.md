 # AI Recommendations - Overview Dashboard
 
 ## Tổng quan
 
 Phần **Khuyến nghị cải thiện** trên trang Overview hiển thị các gợi ý chiến lược cấp công ty để giảm carbon footprint tổng thể, khác với gợi ý cấp sản phẩm ở trang Product Detail.
 
 ---
 
 ## 1. Dữ liệu ngữ cảnh cần thiết
 
 ### A. Thống kê tổng hợp công ty
 | Field | Source | Mô tả |
 |-------|--------|-------|
 | `total_co2e` | `SUM(products.total_co2e)` | Tổng phát thải của toàn bộ SKU |
 | `sku_count` | `COUNT(products.id)` | Số lượng sản phẩm đang tracking |
 | `avg_confidence` | `AVG(products.data_confidence_score)` | Độ tin cậy dữ liệu trung bình |
 | `published_ratio` | Published / Total | Tỷ lệ sản phẩm đã công bố |
 
 ### B. Phân tích nguồn phát thải (Emission Breakdown)
 | Field | Source | Mô tả |
 |-------|--------|-------|
 | `materials_co2e` | `SUM(products.materials_co2e)` | Tổng phát thải từ vật liệu |
 | `production_co2e` | `SUM(products.production_co2e)` | Tổng phát thải từ sản xuất |
 | `transport_co2e` | `SUM(products.transport_co2e)` | Tổng phát thải từ vận chuyển |
 | `packaging_co2e` | `SUM(products.packaging_co2e)` | Tổng phát thải từ đóng gói |
 
 ### C. Xu hướng Carbon (6 tháng)
 | Field | Source | Mô tả |
 |-------|--------|-------|
 | `month` | `carbon_targets.month` | Tháng |
 | `actual_co2e` | `carbon_targets.actual_co2e` | Phát thải thực tế |
 | `target_co2e` | `carbon_targets.target_co2e` | Mục tiêu đặt ra |
 | `trend` | Calculated | Xu hướng tăng/giảm so với tháng trước |
 
 ### D. Mức độ sẵn sàng xuất khẩu
 | Field | Source | Mô tả |
 |-------|--------|-------|
 | `market_code` | `market_readiness.market_code` | Mã thị trường (EU, US, JP, KR) |
 | `readiness_score` | `market_readiness.readiness_score` | Điểm sẵn sàng (0-100) |
 | `requirements_missing` | `market_readiness.requirements_missing` | Các yêu cầu chưa đáp ứng |
 
 ### E. Thông tin vật liệu phổ biến
 | Field | Source | Mô tả |
 |-------|--------|-------|
 | `top_materials` | Aggregated | Top 5 vật liệu sử dụng nhiều nhất |
 | `recycled_ratio` | Calculated | Tỷ lệ sản phẩm dùng vật liệu tái chế |
 | `high_emission_materials` | Aggregated | Vật liệu có emission factor cao nhất |
 
 ### F. Thông tin logistics
 | Field | Source | Mô tả |
 |-------|--------|-------|
 | `transport_modes` | `shipment_legs` | Phân bố phương thức vận chuyển |
 | `avg_distance_km` | `shipments.total_distance_km` | Khoảng cách trung bình |
 | `air_freight_ratio` | Calculated | Tỷ lệ sử dụng đường hàng không |
 
 ---
 
 ## 2. SQL Query tổng hợp dữ liệu
 
 ```sql
 -- Lấy context cho AI recommendations cấp công ty
 WITH company_stats AS (
   SELECT 
     p.company_id,
     COUNT(p.id) as sku_count,
     SUM(p.total_co2e) as total_co2e,
     SUM(p.materials_co2e) as materials_total,
     SUM(p.production_co2e) as production_total,
     SUM(p.transport_co2e) as transport_total,
     SUM(p.packaging_co2e) as packaging_total,
     AVG(p.data_confidence_score) as avg_confidence,
     COUNT(CASE WHEN p.status = 'active' THEN 1 END)::float / COUNT(*) as published_ratio
   FROM products p
   WHERE p.company_id = $1
   GROUP BY p.company_id
 ),
 carbon_trend AS (
   SELECT 
     year, month, actual_co2e, target_co2e,
     LAG(actual_co2e) OVER (ORDER BY year, month) as prev_month
   FROM carbon_targets
   WHERE company_id = $1
   ORDER BY year DESC, month DESC
   LIMIT 6
 ),
 market_status AS (
   SELECT market_code, readiness_score, status, requirements_missing
   FROM market_readiness
   WHERE company_id = $1
 ),
 top_materials AS (
   SELECT 
     m.name,
     m.category,
     m.default_co2e_per_kg,
     COUNT(pm.id) as usage_count,
     SUM(pm.weight_kg) as total_weight
   FROM product_materials pm
   JOIN materials m ON pm.material_id = m.id
   JOIN products p ON pm.product_id = p.id
   WHERE p.company_id = $1
   GROUP BY m.id
   ORDER BY total_weight DESC
   LIMIT 5
 ),
 transport_analysis AS (
   SELECT 
     sl.transport_mode,
     COUNT(*) as leg_count,
     SUM(sl.co2e) as mode_co2e
   FROM shipment_legs sl
   JOIN shipments s ON sl.shipment_id = s.id
   WHERE s.company_id = $1
   GROUP BY sl.transport_mode
 )
 SELECT json_build_object(
   'stats', (SELECT row_to_json(company_stats.*) FROM company_stats),
   'carbon_trend', (SELECT json_agg(carbon_trend.*) FROM carbon_trend),
   'markets', (SELECT json_agg(market_status.*) FROM market_status),
   'top_materials', (SELECT json_agg(top_materials.*) FROM top_materials),
   'transport', (SELECT json_agg(transport_analysis.*) FROM transport_analysis)
 );
 ```
 
 ---
 
 ## 3. Logic phát hiện cơ hội (Opportunity Detection)
 
 ```typescript
 interface OpportunityContext {
   type: 'material' | 'transport' | 'production' | 'packaging' | 'compliance' | 'data_quality';
   priority: 'high' | 'medium' | 'low';
   trigger: string;
   potential_reduction: string;
 }
 
 function detectCompanyOpportunities(context: CompanyContext): OpportunityContext[] {
   const opportunities: OpportunityContext[] = [];
   
   // 1. Vật liệu chiếm > 40% tổng phát thải
   if (context.stats.materials_total / context.stats.total_co2e > 0.4) {
     opportunities.push({
       type: 'material',
       priority: 'high',
       trigger: 'materials_dominant',
       potential_reduction: '10-20%'
     });
   }
   
   // 2. Sử dụng đường hàng không > 30%
   const airRatio = context.transport.find(t => t.transport_mode === 'air')?.leg_count / totalLegs;
   if (airRatio > 0.3) {
     opportunities.push({
       type: 'transport',
       priority: 'high',
       trigger: 'high_air_freight',
       potential_reduction: '15-25%'
     });
   }
   
   // 3. Độ tin cậy dữ liệu thấp < 70%
   if (context.stats.avg_confidence < 70) {
     opportunities.push({
       type: 'data_quality',
       priority: 'medium',
       trigger: 'low_confidence',
       potential_reduction: 'Cải thiện accuracy'
     });
   }
   
   // 4. Thị trường chưa đạt chuẩn
   const lowMarkets = context.markets.filter(m => m.readiness_score < 70);
   if (lowMarkets.length > 0) {
     opportunities.push({
       type: 'compliance',
       priority: 'high',
       trigger: 'market_gaps',
       potential_reduction: 'Mở rộng xuất khẩu'
     });
   }
   
   // 5. Xu hướng tăng liên tục
   const increasing = context.carbon_trend.every((m, i, arr) => 
     i === 0 || m.actual_co2e >= arr[i-1].actual_co2e
   );
   if (increasing) {
     opportunities.push({
       type: 'production',
       priority: 'high',
       trigger: 'increasing_trend',
       potential_reduction: 'Đảo chiều xu hướng'
     });
   }
   
   return opportunities;
 }
 ```
 
 ---
 
 ## 4. API Endpoint
 
 ### `POST /functions/v1/generate-overview-recommendations`
 
 #### Request
 ```json
 {
   "company_id": "uuid",
   "context": {
     "stats": { ... },
     "carbon_trend": [ ... ],
     "markets": [ ... ],
     "top_materials": [ ... ],
     "transport": [ ... ]
   },
   "opportunities": [
     { "type": "material", "priority": "high", "trigger": "materials_dominant" }
   ],
   "language": "vi"
 }
 ```
 
#### System Prompt cho LLM
```
Bạn là chuyên gia tư vấn giảm phát thải carbon cho doanh nghiệp thời trang/dệt may Việt Nam.

## Ngữ cảnh dự án
WeaveCarbon là nền tảng SaaS giúp doanh nghiệp SME ngành thời trang/dệt may Việt Nam đo lường, quản lý và tối ưu hóa dấu chân carbon (carbon footprint) của sản phẩm. Hệ thống hỗ trợ:
- Đánh giá carbon theo vòng đời sản phẩm (LCA): vật liệu, sản xuất, vận chuyển, đóng gói, end-of-life
- Quản lý chuỗi cung ứng và logistics đa chặng (đường bộ, đường biển, đường hàng không, đường sắt)
- Đảm bảo tuân thủ quy định xuất khẩu: EU CBAM, US Climate Act, JP JIS, KR K-ETS
- Theo dõi mục tiêu giảm phát thải theo tháng

Đối tượng người dùng chính là các doanh nghiệp vừa và nhỏ (SME) Việt Nam trong ngành dệt may, có nhu cầu xuất khẩu sang EU, US, Nhật Bản, Hàn Quốc.

## Nhiệm vụ
Dựa trên dữ liệu tổng hợp công ty được cung cấp, hãy đưa ra đúng 3 khuyến nghị chiến lược cấp công ty để giảm carbon footprint.

## Yêu cầu mỗi khuyến nghị:
1. Tiêu đề ngắn gọn (< 50 ký tự)
2. Mô tả cụ thể, hành động được (1-2 câu)
3. Mức độ ảnh hưởng: high/medium/low
4. Phần trăm giảm thiểu dự kiến (ví dụ: "15%")
5. Độ khó thực hiện: easy/medium/hard
6. Danh mục: material/transport/production/packaging/compliance/data_quality

## Nguyên tắc ưu tiên:
- Ưu tiên khuyến nghị có tác động lớn nhất (giảm CO2e nhiều nhất)
- Phù hợp với quy mô và nguồn lực SME Việt Nam
- Khả thi trong 3-6 tháng
- Hỗ trợ mục tiêu xuất khẩu EU/US
- Mỗi khuyến nghị nên thuộc danh mục khác nhau để đa dạng hóa chiến lược

## Format output
Trả về mảng JSON gồm đúng 3 object, mỗi object có các trường: id, title, description, impact, reduction, difficulty, category.
```

#### Response
```json
{
  "recommendations": [
    {
      "id": "rec_001",
      "title": "Chuyển sang cotton hữu cơ",
      "description": "Thay thế 50% cotton thông thường bằng cotton hữu cơ cho các dòng sản phẩm chủ lực",
      "impact": "high",
      "reduction": "15%",
      "difficulty": "medium",
      "category": "material"
    }
  ]
}
```
 
 ---
 
 ## 5. So sánh với Product-level Suggestions
 
 | Aspect | Overview Recommendations | Product Suggestions |
 |--------|-------------------------|---------------------|
 | Scope | Toàn công ty | Từng sản phẩm |
 | Focus | Chiến lược, đầu tư | Cải tiến cụ thể |
 | Data | Aggregated stats | Product-specific |
 | Update frequency | Weekly/Monthly | On product change |
 | Cache TTL | 24 hours | 7 days |
 
 ---
 
 ## 6. Database Table: ai_recommendations
 
 Bảng đã tồn tại trong schema, sử dụng cho cả 2 loại recommendations:
 
 ```sql
 -- company-level: product_id = NULL
 -- product-level: product_id = specific product
 
 SELECT * FROM ai_recommendations 
 WHERE company_id = $1 
   AND product_id IS NULL  -- company-level
   AND is_implemented = false
 ORDER BY impact_level DESC, created_at DESC
 LIMIT 5;
 ```
 
 ---
 
 ## 7. Caching Strategy
 
 | Trigger | Action |
 |---------|--------|
 | Thêm/sửa sản phẩm | Invalidate sau 1 giờ |
 | Thêm shipment mới | Invalidate sau 1 giờ |
 | User request refresh | Generate mới ngay lập tức |
 | Cache TTL (24h) | Auto regenerate |
 
 ---
 
 ## 8. Trạng thái hiện tại
 
 - **Frontend**: Hiển thị demo data từ `dashboardData.ts`
 - **Backend**: Chưa có edge function
 - **Database**: Bảng `ai_recommendations` đã sẵn sàng
 - **Next step**: Implement edge function + integrate với Lovable AI Gateway