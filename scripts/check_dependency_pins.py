from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = ("requirements.txt", "requirements-dev.txt", "requirements-eval.txt")
EXACT_PIN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.-]*(?:\[[A-Za-z0-9_,.-]+\])?==[^\s;]+(?:\s*;.*)?$"
)


def main() -> int:
    failures: list[str] = []
    for relative_path in FILES:
        path = ROOT / relative_path
        for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("-r "):
                referenced = (path.parent / line[3:].strip()).resolve()
                if not referenced.is_file() or referenced.parent != ROOT:
                    failures.append(f"{relative_path}:{line_number}: unsafe/missing include")
                continue
            if not EXACT_PIN.fullmatch(line):
                failures.append(f"{relative_path}:{line_number}: dependency is not exact-pinned")

    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Dependency pin check passed for {len(FILES)} requirement files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
