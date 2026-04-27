"""Minimal LDIC-G compiler (MVP) producing JSON for runtime."""

from __future__ import annotations

from typing import Dict, Any

from ldic_parser import parse_program, Assignment, IfBlock


def _stmt_to_dict(stmt: object) -> Dict[str, Any]:
    if isinstance(stmt, Assignment):
        return {"type": "assign", "target": stmt.target, "expr": stmt.expr}
    if isinstance(stmt, IfBlock):
        return {
            "type": "if",
            "condition": stmt.condition,
            "then": [_stmt_to_dict(s) for s in stmt.then_body],
            "else": [_stmt_to_dict(s) for s in stmt.else_body],
        }
    return {"type": "unknown", "repr": repr(stmt)}


def compile_to_json_model(source: str) -> Dict[str, Any]:
    program = parse_program(source)
    return {
        "sensors": program.sensors,
        "outputs": [{"name": n, "safety": s} for n, s in program.outputs],
        "variables": [{"name": a.target, "expr": a.expr} for a in program.variables],
        "setpoints": [{"name": a.target, "expr": a.expr} for a in program.setpoints],
        "statements": [_stmt_to_dict(s) for s in program.statements],
    }
