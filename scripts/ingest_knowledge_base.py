#!/usr/bin/env python3
"""
WeaveCarbon - Knowledge Base Batch Ingestion Script
==================================================
Quét và nạp toàn bộ tài liệu trong thư mục rag/knowledge_base/ vào Chroma Vector Database.

Cách dùng:
    python scripts/ingest_knowledge_base.py [--dry-run] [--collection TÊN_COLLECTION]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Add project root to sys.path so we can import API_RAG_NEW
RAG_ROOT = Path(__file__).resolve().parent.parent
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch ingest documents from rag/knowledge_base into Chroma vector store."
    )
    parser.add_argument(
        "--collection",
        default="weavecarbon_compliance_kb",
        help="Target Chroma collection name (default: weavecarbon_compliance_kb)",
    )
    parser.add_argument(
        "--kb-dir",
        default=str(RAG_ROOT / "knowledge_base"),
        help="Path to knowledge base directory (default: rag/knowledge_base)",
    )
    parser.add_argument(
        "--profile",
        default="hybrid",
        choices=["hybrid", "semantic"],
        help="Chunking profile (default: hybrid)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files and statistics without indexing into Chroma",
    )
    return parser.parse_args()


def get_all_kb_files(kb_dir: Path) -> list[Path]:
    allowed_extensions = {".md", ".txt", ".pdf", ".docx", ".xlsx"}
    files = []
    for p in sorted(kb_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in allowed_extensions:
            # Skip INDEX.md if only catalog, or include it
            files.append(p)
    return files


def main() -> int:
    args = parse_args()
    kb_path = Path(args.kb_dir).resolve()

    if not kb_path.exists():
        print(f"[ERROR] Knowledge base directory does not exist: {kb_path}", file=sys.stderr)
        return 1

    files = get_all_kb_files(kb_path)
    if not files:
        print(f"[WARN] No documents found in {kb_path}")
        return 0

    print("=" * 70)
    print(" WEAVECARBON KNOWLEDGE BASE BATCH INGESTION")
    print("=" * 70)
    print(f"Target Collection : {args.collection}")
    print(f"Chunking Profile  : {args.profile}")
    print(f"Documents Found   : {len(files)} files")
    print(f"Root Directory    : {kb_path}")
    print("-" * 70)

    total_bytes = 0
    for idx, f in enumerate(files, 1):
        rel_path = f.relative_to(kb_path)
        size_kb = f.stat().st_size / 1024
        total_bytes += f.stat().st_size
        print(f" {idx:2d}. [{f.suffix.upper():4s}] {str(rel_path):<50} ({size_kb:6.2f} KB)")

    print("-" * 70)
    print(f"Total Size: {total_bytes / 1024:.2f} KB ({total_bytes} bytes)")

    if args.dry_run:
        print("\n[DRY RUN] Completed file scan. No records were written to Chroma.")
        return 0

    print("\nStarting ingestion into vector store...")

    try:
        from API_RAG_NEW.ingest_service import ingest_file_content
    except ImportError as e:
        print(
            f"[ERROR] Failed to import RAG ingest service: {e}\n"
            f"Please ensure Python environment dependencies are installed.",
            file=sys.stderr,
        )
        return 1

    success_count = 0
    error_count = 0

    for idx, f in enumerate(files, 1):
        rel_name = f.name
        try:
            content = f.read_bytes()
            resp = ingest_file_content(
                file_name=rel_name,
                raw_content=content,
                requested_collection_name=args.collection,
                chunking_profile=args.profile,
            )
            print(f" [{idx}/{len(files)}] [OK] {rel_name} -> {resp.chunks_ingested} chunks ingested")
            success_count += 1
        except Exception as exc:
            print(f" [{idx}/{len(files)}] [FAILED] {rel_name}: {exc}", file=sys.stderr)
            error_count += 1

    print("=" * 70)
    print(f"Ingestion Finished: {success_count} succeeded, {error_count} failed.")
    print("=" * 70)
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
