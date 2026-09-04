from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_all_declared_dependencies_are_exact_pinned() -> None:
    module_path = ROOT / "scripts" / "check_dependency_pins.py"
    spec = importlib.util.spec_from_file_location("check_dependency_pins", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.main() == 0


def test_runtime_container_is_non_root_and_has_a_healthcheck() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "build-essential" not in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "--no-install-recommends libgomp1" in dockerfile
