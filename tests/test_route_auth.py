from __future__ import annotations

import ast
from pathlib import Path


MAIN_MODULE = Path(__file__).resolve().parents[1] / "API_RAG_NEW" / "main.py"
ROUTE_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


def _is_internal_auth_dependency(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Depends"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "require_internal_api_key"
    )


def test_every_non_health_api_route_requires_internal_auth() -> None:
    module = ast.parse(MAIN_MODULE.read_text(encoding="utf-8"))
    included_routers = [
        node
        for node in ast.walk(module)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "include_router"
    ]
    unprotected: list[str] = []
    discovered_routes = 0

    for function in (
        node
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ):
        for decorator in function.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not isinstance(decorator.func, ast.Attribute):
                continue
            if not isinstance(decorator.func.value, ast.Name):
                continue
            if decorator.func.value.id != "app" or decorator.func.attr not in ROUTE_METHODS:
                continue

            discovered_routes += 1
            path = ast.literal_eval(decorator.args[0])
            if path in {"/health", "/ready"}:
                continue

            dependencies = next(
                (
                    keyword.value
                    for keyword in decorator.keywords
                    if keyword.arg == "dependencies"
                ),
                None,
            )
            protected = (
                isinstance(dependencies, (ast.List, ast.Tuple))
                and any(_is_internal_auth_dependency(item) for item in dependencies.elts)
            )
            if not protected:
                unprotected.append(f"{decorator.func.attr.upper()} {path}")

    assert included_routers == [], "Extend this policy test before adding an API router."
    assert discovered_routes > 1
    assert unprotected == []
