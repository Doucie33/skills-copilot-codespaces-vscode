"""Minimal LDIC-G runtime/interpreter (MVP)."""

from __future__ import annotations

from typing import Dict, Any
import re

from ldic_parser import Program, Assignment, IfBlock


_COMPARE_OPS = [">=", "<=", "!=", ">", "<", "="]
_NUM_UNIT_RE = re.compile(r"^(-?\d+(?:\.\d+)?)\s*([A-Za-z%/0-9]+)?$")


def _coerce_literal(raw: str) -> Any:
    token = raw.strip()
    upper = token.upper()
    if upper in {"ON", "OFF", "AUTO", "MANUEL", "LOCAL", "DISTANT"}:
        return upper
    m = _NUM_UNIT_RE.match(token)
    if m:
        number = float(m.group(1))
        unit = m.group(2)
        return (number, unit) if unit else number
    if token.startswith('"') and token.endswith('"'):
        return token[1:-1]
    return token


def _resolve_term(term: str, env: Dict[str, Any]) -> Any:
    term = term.strip()
    if term in env:
        return env[term]
    return _coerce_literal(term)


def _as_comparable(val: Any) -> Any:
    if isinstance(val, tuple) and len(val) == 2 and isinstance(val[0], (int, float)):
        return val[0]
    return val


def _evaluate_condition(condition: str, env: Dict[str, Any]) -> bool:
    cond = condition.strip()
    for op in _COMPARE_OPS:
        if op in cond:
            left, right = cond.split(op, 1)
            lv = _as_comparable(_resolve_term(left, env))
            rv = _as_comparable(_resolve_term(right, env))
            if op == "=":
                return lv == rv
            if op == "!=":
                return lv != rv
            if op == ">":
                return lv > rv
            if op == "<":
                return lv < rv
            if op == ">=":
                return lv >= rv
            if op == "<=":
                return lv <= rv
    raise ValueError(f"Condition non supportée: {condition}")


def _exec_assignment(assign: Assignment, env: Dict[str, Any]) -> None:
    env[assign.target] = _resolve_term(assign.expr, env)


def _exec_stmt(stmt: Any, env: Dict[str, Any]) -> None:
    if isinstance(stmt, Assignment):
        _exec_assignment(stmt, env)
        return
    if isinstance(stmt, IfBlock):
        body = stmt.then_body if _evaluate_condition(stmt.condition, env) else stmt.else_body
        for inner in body:
            _exec_stmt(inner, env)
        return
    raise ValueError(f"Statement inconnu: {stmt}")


def run_program(program: Program, inputs: Dict[str, Any] | None = None) -> Dict[str, Any]:
    env: Dict[str, Any] = {}

    # Initialize outputs with safety states.
    for out_name, safety in program.outputs:
        env[out_name] = _coerce_literal(safety)

    # Initialize declarations.
    for assign in program.variables + program.setpoints:
        _exec_assignment(assign, env)

    # External input values (sensors, overrides) win over defaults.
    if inputs:
        env.update(inputs)

    for stmt in program.statements:
        _exec_stmt(stmt, env)

    return env
