"""Minimal LDIC-G parser (MVP).

Supported subset:
- VARIABLE / CONSIGNE declarations
- CAPTEUR / SORTIE declarations
- Assignments: Nom = Valeur
- Conditionals: SI ... ALORS / SINON / FIN
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple
import re


@dataclass
class Assignment:
    target: str
    expr: str


@dataclass
class IfBlock:
    condition: str
    then_body: List[object]
    else_body: List[object]


@dataclass
class Program:
    sensors: List[str]
    outputs: List[Tuple[str, str]]  # (name, safety_state)
    variables: List[Assignment]
    setpoints: List[Assignment]
    statements: List[object]


_COMMENT_RE = re.compile(r"//.*$")


def strip_comments(line: str) -> str:
    return _COMMENT_RE.sub("", line).strip()


def parse_assignment_line(line: str) -> Optional[Assignment]:
    if "=" not in line:
        return None
    left, right = line.split("=", 1)
    target = left.strip()
    expr = right.strip()
    if not target:
        return None
    return Assignment(target=target, expr=expr)


def parse_program(source: str) -> Program:
    lines = [strip_comments(raw) for raw in source.splitlines()]
    lines = [ln for ln in lines if ln]

    sensors: List[str] = []
    outputs: List[Tuple[str, str]] = []
    variables: List[Assignment] = []
    setpoints: List[Assignment] = []

    idx = 0

    def parse_block(stop_tokens: set[str]) -> List[object]:
        nonlocal idx
        out: List[object] = []
        while idx < len(lines):
            line = lines[idx]
            upper = line.upper()
            if upper in stop_tokens:
                return out

            if upper.startswith("SI ") and upper.endswith(" ALORS"):
                cond = line[3:-6].strip()
                idx += 1
                then_body = parse_block({"SINON", "FIN"})
                else_body: List[object] = []
                if idx < len(lines) and lines[idx].upper() == "SINON":
                    idx += 1
                    else_body = parse_block({"FIN"})
                if idx >= len(lines) or lines[idx].upper() != "FIN":
                    raise ValueError("Bloc SI non fermé (FIN manquant)")
                out.append(IfBlock(condition=cond, then_body=then_body, else_body=else_body))
                idx += 1
                continue

            assign = parse_assignment_line(line)
            if assign:
                out.append(assign)
            idx += 1
        return out

    while idx < len(lines):
        line = lines[idx]
        upper = line.upper()

        if upper.startswith("CAPTEUR "):
            parts = line.split()
            if len(parts) >= 2:
                sensors.append(parts[1])
            idx += 1
            continue

        if upper.startswith("SORTIE "):
            parts = line.split()
            if len(parts) >= 2:
                name = parts[1]
                safety = "OFF"
                if "ETAT_SECURITE" in upper:
                    tokenized = line.split()
                    for i, tok in enumerate(tokenized):
                        if tok.upper() == "ETAT_SECURITE" and i + 1 < len(tokenized):
                            safety = tokenized[i + 1]
                            break
                outputs.append((name, safety))
            idx += 1
            continue

        if upper.startswith("VARIABLE "):
            assign = parse_assignment_line(line[len("VARIABLE ") :].strip())
            if assign:
                variables.append(assign)
            idx += 1
            continue

        if upper.startswith("CONSIGNE "):
            body = line[len("CONSIGNE ") :].strip()
            assign = parse_assignment_line(body)
            if assign:
                setpoints.append(assign)
            idx += 1
            continue

        if upper.startswith("SI ") and upper.endswith(" ALORS"):
            statements = parse_block(set())
            return Program(
                sensors=sensors,
                outputs=outputs,
                variables=variables,
                setpoints=setpoints,
                statements=statements,
            )

        idx += 1

    idx = 0
    statements = parse_block(set())
    return Program(
        sensors=sensors,
        outputs=outputs,
        variables=variables,
        setpoints=setpoints,
        statements=statements,
    )
