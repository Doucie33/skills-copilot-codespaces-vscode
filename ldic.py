#!/usr/bin/env python3
"""LDIC-G MVP CLI.

Usage:
  python ldic.py validate examples/maison.ldic
  python ldic.py compile examples/maison.ldic --output programme.json
  python ldic.py run examples/maison.ldic --inputs '{"Temp_Salon": 19}'
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from ldic_compiler import compile_to_json_model
from ldic_parser import parse_program
from ldic_runtime import run_program
from ldic_validator import validate_source


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def cmd_validate(args: argparse.Namespace) -> int:
    source = _read(args.file)
    errors = validate_source(source)
    if errors:
        for err in errors:
            print(err)
        return 1
    print("OK: validation réussie")
    return 0


def cmd_compile(args: argparse.Namespace) -> int:
    source = _read(args.file)
    errors = validate_source(source)
    if errors:
        for err in errors:
            print(err)
        return 1

    model = compile_to_json_model(source)
    out = json.dumps(model, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"Écrit: {args.output}")
    else:
        print(out)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    source = _read(args.file)
    errors = validate_source(source)
    if errors:
        for err in errors:
            print(err)
        return 1

    inputs = json.loads(args.inputs) if args.inputs else {}
    program = parse_program(source)
    env = run_program(program, inputs=inputs)
    print(json.dumps(env, indent=2, ensure_ascii=False, default=str))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ldic", description="LDIC-G MVP CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_val = sub.add_parser("validate", help="Valider un programme LDIC-G")
    p_val.add_argument("file")
    p_val.set_defaults(func=cmd_validate)

    p_comp = sub.add_parser("compile", help="Compiler vers modèle JSON")
    p_comp.add_argument("file")
    p_comp.add_argument("--output", "-o")
    p_comp.set_defaults(func=cmd_compile)

    p_run = sub.add_parser("run", help="Exécuter une passe de logique")
    p_run.add_argument("file")
    p_run.add_argument("--inputs", help="JSON des entrées (capteurs)")
    p_run.set_defaults(func=cmd_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
