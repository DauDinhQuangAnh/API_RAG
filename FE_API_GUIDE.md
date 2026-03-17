# FE API Guide (RAG Backend)

Tài liệu này dành cho Frontend tích hợp API của backend RAG.

## 1) Phạm vi tài liệu

**Bao gồm đầy đủ** các API sau:
- `GET /health`
- `GET /db/test`
- `GET /collections`
- `POST /collections`
- `GET /collections/{collection_name}`
- `PATCH /collections/{collection_name}`
- `DELETE /collections/{collection_name}`
- `POST /ingest`
- `POST /collections/{collection_name}/query`

**Không bao gồm theo yêu cầu:**
- API recommendation (`/recommendations/company/*`, `/recommendations/product/*`)
- API gọi trực tiếp Gemini (`/chat/gemini`)

---

## 2) Thông tin chung

- **Base URL local:** `http://127.0.0.1:8000`
- **Swagger UI:** `http://127.0.0.1:8000/docs`
- **Auth hiện tại:** chưa có auth token/bearer trong code
- **CORS:** mở (`*`) cho mọi origin/method/header

### Content-Type chuẩn
- JSON APIs: `application/json`
- Upload CSV: `multipart/form-data`

### Chuẩn lỗi
Backend trả lỗi theo format FastAPI:

```json
{
  "detail": "Error message"
}
```

---

## 3) Quy tắc quan trọng FE cần biết

### 3.1 Quy tắc tên collection
Khi tạo/sửa collection, backend sẽ làm sạch tên (`clean_collection_name`) theo rule:
- Chỉ cho phép ký tự: `a-z A-Z 0-9 _ . -`
- Xóa ký tự không hợp lệ
- Không cho phép dấu chấm liên tiếp (`..`)
- Cắt đầu/cuối nếu không phải ký tự chữ/số
- Độ dài hợp lệ: **3 -> 63 ký tự**

Nếu không đạt rule, backend trả `400`.

### 3.2 Dữ liệu query phụ thuộc metadata đã ingest
- `columns_to_answer` trong API query phải là các cột tồn tại trong metadata đã lưu khi ingest CSV.
- Nếu cột không tồn tại, câu trả lời retrieval sẽ thiếu dữ liệu ở cột đó.

---

## 4) API chi tiết

## 4.1 Health check
### `GET /health`
Dùng để kiểm tra service đang chạy.

#### Response thành công `200`
```json
{
  "status": "ok"
}
```

---

## 4.2 Test kết nối PostgreSQL
### `GET /db/test`
Dùng để kiểm tra backend kết nối được PostgreSQL hay chưa.

#### Response thành công (ví dụ) `200`
```json
{
  "status": "success",
  "message": "Connected to PostgreSQL successfully",
  "database": "weavecarbon",
  "version": "PostgreSQL 14.x ..."
}
```

#### Response lỗi (ví dụ) `200` (backend tự trả status field lỗi)
```json
{
  "status": "error",
  "message": "Failed to connect to PostgreSQL: ...",
  "database": "weavecarbon"
}
```

> Lưu ý: endpoint này hiện không ném HTTP error; nó trả JSON có `status` là `success/error`.

---

## 4.3 Danh sách collections
### `GET /collections`
Trả về danh sách tên collection trong ChromaDB.

#### Response thành công `200`
```json
{
  "collections": ["rag_collection_demo", "rag_collection_xxx"]
}
```

---

## 4.4 Tạo collection
### `POST /collections`
Tạo collection mới.

#### Request body
```json
{
  "name": "rag_collection_demo",
  "description": "Demo collection"
}
```

#### Field
- `name` (string, bắt buộc)
- `description` (string, optional)

#### Response thành công `200`
```json
{
  "name": "rag_collection_demo",
  "metadata": {
    "description": "Demo collection"
  },
  "count": 0
}
```

#### Lỗi thường gặp
- `400`: `Invalid collection name.`
- `400`: `Collection already exists.`

---

## 4.5 Lấy thông tin 1 collection
### `GET /collections/{collection_name}`

#### Path params
- `collection_name` (string)

#### Response thành công `200`
```json
{
  "name": "rag_collection_demo",
  "metadata": {
    "description": "Demo collection"
  },
  "count": 128
}
```

#### Lỗi thường gặp
- `404`: `Collection not found.`

---

## 4.6 Cập nhật collection
### `PATCH /collections/{collection_name}`
Đổi tên hoặc cập nhật metadata collection.

#### Path params
- `collection_name` (string)

#### Request body
```json
{
  "new_name": "rag_collection_new",
  "metadata": {
    "description": "Updated description"
  }
}
```

#### Field
- `new_name` (string, optional)
- `metadata` (object, optional)
- Ít nhất phải có 1 field (`new_name` hoặc `metadata`)

#### Response thành công `200`
```json
{
  "name": "rag_collection_new",
  "metadata": {
    "description": "Updated description"
  },
  "count": 128
}
```

#### Lỗi thường gặp
- `404`: `Collection not found.`
- `400`: `Nothing to update (new_name or metadata required).`
- `400`: `Invalid new_name.`

---

## 4.7 Xóa collection
### `DELETE /collections/{collection_name}`

#### Path params
- `collection_name` (string)

#### Response thành công `200`
```json
{
  "detail": "Collection deleted successfully."
}
```

#### Lỗi thường gặp
- `404`: `Collection not found.`

---

## 4.8 Ingest dữ liệu CSV
### `POST /ingest`
Upload CSV, tách chunk theo `index_column`, embed và lưu vào Chroma collection.

#### Content-Type
`multipart/form-data`

#### Form fields
- `file` (file CSV, bắt buộc)
- `index_column` (string, bắt buộc): tên cột chứa text để chunk/index
- `collection_name` (string, optional): nếu không truyền backend sẽ tự sinh tên

#### Ví dụ request (cURL)
```bash
curl -X POST "http://127.0.0.1:8000/ingest" ^
  -F "file=@data.csv" ^
  -F "index_column=content" ^
  -F "collection_name=rag_collection_demo"
```

#### Response thành công `200`
```json
{
  "collection_name": "rag_collection_demo",
  "rows": 100,
  "chunks": 356
}
```

#### Lỗi thường gặp
- `400`: `Only CSV files are supported.`
- `400`: `Failed to read CSV: ...`
- `400`: `Column 'xxx' not found.`
- `400`: `No valid text to chunk.`
- `400`: `Invalid collection_name.`
- `400`: `No data available to process.`

#### Ghi chú cho FE
- Sau ingest thành công, lưu lại `collection_name` để dùng cho màn hình query.
- `rows` là số dòng CSV gốc; `chunks` là số đoạn text sau khi chunk.

---

## 4.9 Query trong collection (RAG)
### `POST /collections/{collection_name}/query`
Tìm vector theo câu hỏi và generate câu trả lời dựa trên dữ liệu retrieve.

#### Path params
- `collection_name` (string)

#### Request body
```json
{
  "query": "Sản phẩm nào có phát thải cao nhất?",
  "columns_to_answer": ["product_name", "total_co2e", "chunk"],
  "number_docs_retrieval": 3
}
```

#### Field
- `query` (string, bắt buộc)
- `columns_to_answer` (string[], bắt buộc)
- `number_docs_retrieval` (integer, optional, default `3`, min `1`, max `50`)

#### Response thành công `200`
```json
{
  "metadatas": [
    [
      {
        "doc_id": "...",
        "chunk": "...",
        "product_name": "T-Shirt A",
        "total_co2e": 12.3
      }
    ]
  ],
  "retrieved_data": "\n1) Product_name: T-Shirt A Total_co2e: 12.3 Chunk: ...\n",
  "answer": "... câu trả lời từ LLM ...",
  "full_prompt": "... prompt đầy đủ backend gửi cho LLM ..."
}
```

#### Lỗi thường gặp
- `404`: `Collection not found.`
- `500`: lỗi từ LLM/Gemini hoặc lỗi runtime nội bộ

#### Ghi chú cho FE
- `metadatas` là dữ liệu retrieve thô, dùng để render nguồn tham chiếu.
- `retrieved_data` là bản text đã format từ `columns_to_answer`.
- `answer` là nội dung chính để hiển thị chat.
- `full_prompt` có thể dài; FE cân nhắc ẩn hoặc chỉ dùng debug mode.

---

## 5) Suggested FE flow (MVP)

1. Check server: gọi `GET /health`.
2. Tạo collection mới (`POST /collections`) hoặc chọn collection có sẵn (`GET /collections`).
3. Upload CSV qua `POST /ingest`.
4. Lưu `collection_name` vào state/context.
5. Gọi `POST /collections/{collection_name}/query` cho màn hình hỏi đáp.
6. Hiển thị `answer` + (optional) nguồn từ `metadatas`.

---

## 6) Checklist tích hợp FE

- Handle đầy đủ HTTP status `200/400/404/500`.
- Với upload file, bắt buộc dùng `multipart/form-data`.
- Validate client-side cho `collection_name` theo rule 3-63 ký tự.
- Với query, đảm bảo `columns_to_answer` map đúng cột của CSV đã ingest.
- Timeout UI cho ingest/query vì có thể tốn thời gian.
