"""
Script để test kết nối PostgreSQL
Chạy: python test_postgres.py
"""
from database import get_db_connection

if __name__ == "__main__":
    print("Testing PostgreSQL connection...")
    print("-" * 50)
    
    db = get_db_connection()
    result = db.test_connection()
    
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    print(f"Database: {result['database']}")
    
    if result['status'] == 'success':
        print(f"Version: {result.get('version', 'N/A')}")
        print("\n✓ Kết nối thành công!")
    else:
        print("\n✗ Kết nối thất bại!")
        print("Vui lòng kiểm tra:")
        print("  - PostgreSQL đã chạy chưa")
        print("  - Thông tin trong .env có đúng không")
        print("  - Database 'weavecarbon' đã được tạo chưa")
