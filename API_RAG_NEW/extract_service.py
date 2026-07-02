"""
Document field extraction via Gemini — raw prompt, no RAG ingestion.
"""
from __future__ import annotations

import base64
import io
import json
import re
import zipfile

import pdfplumber
from google import genai

from API_RAG_NEW.config import GEMINI_MODEL, get_gemini_api_key

# --------------------------------------------------------------------------- #
# Per-kind extraction prompts
# --------------------------------------------------------------------------- #
_KIND_PROMPTS: dict[str, str] = {
    "electricity_bill": """
Đây là hóa đơn tiền điện. Hãy trích xuất các trường sau (trả về JSON):
- billing_period: kỳ thanh toán (ví dụ "2024-Q2" hoặc "2024-05")
- facility_name: tên cơ sở / nhà máy
- kwh: tổng lượng điện tiêu thụ (số thực, đơn vị kWh)
- amount_vnd: tổng tiền hóa đơn (số thực, VNĐ — nếu có)
- supplier: tên nhà cung cấp điện
- customer_name: tên khách hàng / doanh nghiệp
- customer_address: địa chỉ khách hàng
- invoice_number: số hóa đơn
""",
    "fuel_receipt": """
Đây là hóa đơn / phiếu mua nhiên liệu. Hãy trích xuất các trường sau (trả về JSON):
- billing_period: kỳ / ngày mua (ví dụ "2024-05-10")
- fuel_type: loại nhiên liệu (diesel / petrol / lpg / cng / coal / biomass / other)
- quantity_liters: số lượng (lít, số thực)
- unit_price_vnd: đơn giá (VNĐ/lít — nếu có)
- amount_vnd: tổng tiền (VNĐ — nếu có)
- supplier: tên trạm / nhà cung cấp
- invoice_number: số hóa đơn
""",
    "bom": """
Đây là bảng kê nguyên liệu (BOM). Hãy trích xuất các trường sau (trả về JSON):
- product_sku: mã SKU sản phẩm
- product_name: tên sản phẩm
- materials: danh sách nguyên liệu (mảng string)
- total_weight_kg: tổng khối lượng (kg — nếu có)
- supplier: nhà cung ứng chính
""",
    "logistics_invoice": """
Đây là hóa đơn vận chuyển / logistics. Hãy trích xuất các trường sau (trả về JSON):
- invoice_number: số hóa đơn
- date: ngày (YYYY-MM-DD)
- carrier: đơn vị vận chuyển
- transport_mode: phương thức (road / sea / air / rail)
- origin: điểm đi
- destination: điểm đến
- weight_kg: trọng lượng (kg — nếu có)
- distance_km: khoảng cách (km — nếu có)
- amount_vnd: tổng tiền (nếu có)
""",
    "supplier_declaration": """
Đây là tờ khai / cam kết từ nhà cung ứng. Hãy trích xuất các trường sau (trả về JSON):
- supplier_name: tên nhà cung ứng
- material: tên nguyên liệu / sản phẩm
- co2e_per_unit: phát thải CO₂e trên đơn vị (số thực — nếu có)
- unit: đơn vị tính
- method: phương pháp tính
- period: kỳ tính
- contact_person: người ký / liên hệ
- date: ngày khai (YYYY-MM-DD)
""",
    "export_invoice": """
Đây là hóa đơn xuất khẩu. Hãy trích xuất các trường sau (trả về JSON):
- invoice_number: số hóa đơn
- date: ngày (YYYY-MM-DD)
- seller: người bán
- buyer: người mua
- destination_country: nước nhập khẩu
- incoterms: điều kiện thương mại
- hs_code: mã HS
- total_amount_usd: tổng giá trị (USD — nếu có)
- weight_kg: trọng lượng (kg — nếu có)
""",
}

_DEFAULT_PROMPT = """
Đây là một chứng từ kinh doanh. Hãy trích xuất tất cả các trường thông tin có ý nghĩa
(số hóa đơn, ngày, tên, số liệu, đơn vị, v.v.) và trả về JSON.
"""

_JSON_RE = re.compile(r"\{[\s\S]*\}")

_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

_EXT_MIME: dict[str, str] = {
    ".pdf":  "application/pdf",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".webp": "image/webp",
    ".xlsx": "xlsx",          # handled separately
    ".csv":  "text/csv",
    ".txt":  "text/plain",
    ".xml":  "application/xml",
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _ext(filename: str) -> str:
    return ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""


def _mime(filename: str, content_type: str | None) -> str:
    return _EXT_MIME.get(_ext(filename), content_type or "application/octet-stream")


def _parse_json(text: str) -> dict:
    m = _JSON_RE.search(text or "")
    if not m:
        return {"raw_answer": (text or "").strip()}
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        return {"raw_answer": (text or "").strip()}


def _pdf_to_text(file_bytes: bytes) -> str:
    """Extract plain text from a PDF using pdfplumber."""
    parts: list[str] = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
                if t.strip():
                    parts.append(t.strip())
    except Exception:
        pass
    return "\n".join(parts)


def _xlsx_to_text(file_bytes: bytes) -> str:
    """
    XLSX = ZIP containing XML files.  Extract readable text from the
    shared strings table and sheet XMLs using only stdlib.
    """
    tag_re = re.compile(r"<[^>]+>")
    parts: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            # Priority order: shared strings → sheets → other xl/ xml files
            targets = sorted(
                (n for n in zf.namelist() if n.startswith("xl/") and n.endswith(".xml")),
                key=lambda n: (
                    0 if "sharedStrings" in n else
                    1 if "worksheets" in n else
                    2
                ),
            )
            for name in targets:
                raw_xml = zf.read(name).decode("utf-8", errors="replace")
                plain = tag_re.sub(" ", raw_xml)
                plain = re.sub(r"\s+", " ", plain).strip()
                if plain:
                    parts.append(plain)
    except Exception:
        pass
    return " ".join(parts)


def _call_gemini_text(client: genai.Client, instruction: str, body: str) -> str:
    prompt = f"{instruction}\n\n---NỘI DUNG TÀI LIỆU---\n{body[:8000]}"
    return client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    ).text or ""


def _call_gemini_vision(client: genai.Client, instruction: str,
                        file_bytes: bytes, mime: str) -> str:
    # Dict-based multimodal content — compatible with google-genai SDK
    contents = [
        {
            "role": "user",
            "parts": [
                {
                    "inline_data": {
                        "mime_type": mime,
                        "data": base64.b64encode(file_bytes).decode(),
                    }
                },
                {"text": instruction},
            ],
        }
    ]
    return client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
    ).text or ""


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def extract_document(
    filename: str,
    file_bytes: bytes,
    kind: str = "other",
    language: str = "vi",
    content_type: str | None = None,
) -> dict:
    """
    Extract structured fields from a document using Gemini (raw prompt).
    No RAG ingestion.  Returns a dict of field_name → value.
    """
    api_key = get_gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=api_key)
    ext = _ext(filename)
    mime = _mime(filename, content_type)

    kind_prompt = _KIND_PROMPTS.get(kind, _DEFAULT_PROMPT).strip()
    instruction = (
        f"{kind_prompt}\n\n"
        f"Ngôn ngữ phản hồi: {language}.\n"
        "Chỉ trả về JSON object thuần, không giải thích thêm. "
        "Nếu không tìm thấy giá trị cho một trường, bỏ qua trường đó."
    )

    raw: str

    if ext == ".pdf":
        # Try text extraction first; fall back to vision for scanned PDFs
        text = _pdf_to_text(file_bytes)
        if text.strip():
            raw = _call_gemini_text(client, instruction, text)
        else:
            raw = _call_gemini_vision(client, instruction, file_bytes, "application/pdf")

    elif ext == ".xlsx":
        text = _xlsx_to_text(file_bytes)
        if text.strip():
            raw = _call_gemini_text(client, instruction, text)
        else:
            raw = ""   # can't vision an XLSX — return empty

    elif mime in _IMAGE_MIMES:
        raw = _call_gemini_vision(client, instruction, file_bytes, mime)

    else:
        # CSV, TXT, XML — plain text
        try:
            text = file_bytes.decode("utf-8", errors="replace")
        except Exception:
            text = file_bytes.decode("latin-1", errors="replace")
        raw = _call_gemini_text(client, instruction, text)

    return _parse_json(raw)
