# RAG API - Hướng Dẫn Test Postman

**Base URL**: `http://localhost:8000`

---

## 1. Health Check
**Method**: `GET`  
**URL**: `/health`  
**Response**: `{"status": "ok"}`

---

## 2. Test PostgreSQL Connection
**Method**: `GET`  
**URL**: `/db/test`  
**Response**: 
```json
{
  "status": "success",
  "message": "Connected to PostgreSQL successfully",
  "database": "weavecarbon",
  "version": "PostgreSQL 14.x..."
}
```

---

## 3. Chat Trực Tiếp với Gemini (Không RAG)
**Method**: `POST`  
**URL**: `/chat/gemini`  
**Body** (JSON):
```json
{
  "query": "Giải thích carbon footprint là gì?",
  "api_key": "your_gemini_api_key"
}
```
*Note*: `api_key` có thể bỏ qua nếu đã set trong `.env`

---

## 4. List Collections
**Method**: `GET`  
**URL**: `/collections`  
**Response**: `{"collections": ["collection1", "collection2"]}`

---

## 5. Tạo Collection Mới
**Method**: `POST`  
**URL**: `/collections`  
**Body** (JSON):
```json
{
  "name": "my_collection",
  "description": "Collection mô tả carbon footprint"
}
```

---

## 6. Xem Thông Tin Collection
**Method**: `GET`  
**URL**: `/collections/{collection_name}`  
**Example**: `/collections/my_collection`

---

## 7. Cập Nhật Collection
**Method**: `PATCH`  
**URL**: `/collections/{collection_name}`  
**Body** (JSON):
```json
{
  "new_name": "renamed_collection",
  "metadata": {"updated": "true"}
}
```

---

## 8. Xóa Collection
**Method**: `DELETE`  
**URL**: `/collections/{collection_name}`

---

## 9. Upload CSV & Tạo Vector Embeddings
**Method**: `POST`  
**URL**: `/ingest`  
**Body** (form-data):
- `file`: (chọn file CSV)
- `index_column`: tên cột cần index (vd: "content")
- `collection_name`: tên collection (optional)

**Response**:
```json
{
  "collection_name": "rag_collection_xyz",
  "rows": 100,
  "chunks": 250
}
```

---

## 10. Query Collection với RAG
**Method**: `POST`  
**URL**: `/collections/{collection_name}/query`  
**Body** (JSON):
```json
{
  "query": "Carbon footprint trong ngành dệt may là gì?",
  "columns_to_answer": ["content", "title"],
  "number_docs_retrieval": 5
}
```

**Response**:
```json
{
  "metadatas": [...],
  "retrieved_data": "...",
  "answer": "Câu trả lời từ AI",
  "full_prompt": "..."
}
```

---

## Lưu Ý
- Cần set `GEMINI_API_KEY` trong file `.env`
- File CSV phải có cột tương ứng với `index_column`
- `number_docs_retrieval` từ 1-50 (mặc định: 3)
