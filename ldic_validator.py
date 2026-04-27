"""Minimal LDIC-G validator (MVP)."""

from __future__ import annotations

from typing import List


def validate_source(source: str) -> List[str]:
    errors: List[str] = []
    stack = []

    for lineno, raw in enumerate(source.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        upper = line.upper()

        if upper.startswith("SI ") and upper.endswith(" ALORS"):
            stack.append(("SI", lineno))
        elif upper == "SINON":
            if not stack or stack[-1][0] != "SI":
                errors.append(f"LDIC-004 ligne {lineno}: SINON sans SI")
        elif upper == "FIN":
            if not stack:
                errors.append(f"LDIC-004 ligne {lineno}: FIN sans ouverture")
            else:
                stack.pop()

        if " ALOR" in upper and " ALORS" not in upper:
            errors.append(f"LDIC-001 ligne {lineno}: mot-clé inconnu ALOR")

    for kind, lno in stack:
        errors.append(f"LDIC-003 ligne {lno}: bloc {kind} non fermé")

    # Very light mixed-language check.
    has_fr = any(tok in source.upper() for tok in ["LANGUE", "PROJET", "SI "])
    has_en = any(tok in source.upper() for tok in ["LANGUAGE", "PROJECT", "IF "])
    if has_fr and has_en:
        errors.append("LDIC-005: mélange FR/EN détecté")

    return errors
