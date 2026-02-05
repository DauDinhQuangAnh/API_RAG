"""
Script để tải model về local cache
Chạy script này trước khi start API để tránh timeout
"""
from sentence_transformers import SentenceTransformer
import os

MODEL_NAME = "keepitreal/vietnamese-sbert"
# Hoặc model thay thế ổn định hơn:
# MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

print(f"Đang tải model: {MODEL_NAME}")
print("Vị trí cache mặc định:", os.path.expanduser("~/.cache/torch/sentence_transformers/"))

try:
    model = SentenceTransformer(MODEL_NAME)
    print(f"✓ Tải model thành công!")
    print(f"Model path: {model._model_card_vars.get('model_name', MODEL_NAME)}")
    
    # Test model
    test_embedding = model.encode(["Xin chào"])
    print(f"✓ Test encoding thành công! Dimension: {len(test_embedding[0])}")
    
except Exception as e:
    print(f"✗ Lỗi khi tải model: {e}")
    print("\nThử model thay thế:")
    alt_model = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    print(f"Đang tải: {alt_model}")
    model = SentenceTransformer(alt_model)
    print(f"✓ Tải model thay thế thành công!")
