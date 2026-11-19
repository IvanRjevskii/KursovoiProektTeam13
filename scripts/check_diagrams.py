"""Проверка диаграмм команды 13 перед отрисовкой (запускается в CI и локально).

Автор: Ржевский И. А. (тимлид). Лабораторная работа № 5.

Что проверяется в каждом src/**/*.puml:
 1. имя после @startuml совпадает с именем файла (PNG не перезаписывают друг друга);
 2. есть title, а у диаграмм C4 — ещё и легенда (LAYOUT_WITH_LEGEND);
 3. нет макросов жёсткого позиционирования Rel_U/Rel_D/Rel_L/Rel_R и их длинных форм;
 4. в файлах участников нет skinparam (стили — только в главных файлах);
 5. у каждой связи Rel(...) есть описание действия и протокол (4 аргумента);
 6. диаграмма классов соответствует коду: каждый класс, интерфейс и перечисление
    с диаграммы есть в файле кода, указанном в заголовке строкой «Код: ...».
При любой ошибке скрипт завершается с кодом 1 — сборка в GitHub Actions «падает» (❌).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
MAIN_FILES = {"main", "main-context", "main-landscape", "dynamic_process", "main-deployment"}
BANNED_REL = re.compile(r"\bRel_(U|D|L|R|Up|Down|Left|Right|Back|Neighbor)\b")
CLASS_DECL = re.compile(r"^\s*(?:abstract\s+)?(class|interface|enum)\s+(\w+)", re.M)
CODE_REF = re.compile(r"Код:\s*(\S+)")


def split_args(text: str) -> list[str]:
    """Делит аргументы макроса по запятым вне кавычек."""
    args, current, quoted = [], [], False
    for ch in text:
        if ch == '"':
            quoted = not quoted
        if ch == "," and not quoted:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    args.append("".join(current).strip())
    return args


def rel_calls(body: str) -> list[tuple[int, list[str]]]:
    calls = []
    for number, line in enumerate(body.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("Rel(") and stripped.endswith(")"):
            calls.append((number, split_args(stripped[4:-1])))
    return calls


def check_file(path: Path) -> list[str]:
    errors: list[str] = []
    rel = path.relative_to(ROOT)
    text = path.read_text(encoding="utf-8")
    body = "\n".join("" if l.strip().startswith("'") else l for l in text.splitlines())
    first = text.strip().splitlines()[0] if text.strip() else ""
    name = first.removeprefix("@startuml").strip().strip('"')
    if name != path.stem:
        errors.append(f"{rel}: после @startuml должно стоять имя файла «{path.stem}», а стоит «{name}»")
    if not text.rstrip().endswith("@enduml"):
        errors.append(f"{rel}: файл должен заканчиваться строкой @enduml")
    if not re.search(r"^\s*title\s+\S", body, re.M):
        errors.append(f"{rel}: нет заголовка title")
    is_c4 = "<C4/" in body or "C4-PlantUML" in body
    if is_c4 and "LAYOUT_WITH_LEGEND()" not in body and "SHOW_LEGEND()" not in body:
        errors.append(f"{rel}: у диаграммы C4 нет легенды LAYOUT_WITH_LEGEND()")
    for match in BANNED_REL.finditer(body):
        line = body[: match.start()].count("\n") + 1
        errors.append(f"{rel}:{line}: макрос {match.group(0)} запрещён методичкой, используйте Rel()")
    if path.stem not in MAIN_FILES and re.search(r"^\s*skinparam\b", body, re.M):
        errors.append(f"{rel}: skinparam в файле участника запрещён — стили только в главных файлах")
    for line, args in rel_calls(body):
        if len(args) < 4 or not args[2].strip('"') or not args[3].strip('"'):
            errors.append(f"{rel}:{line}: у связи нет описания действия или протокола")
    if not is_c4:
        ref = CODE_REF.search(text)
        declared = {m.group(2) for m in CLASS_DECL.finditer(body)}
        if ref and declared:
            code_path = ROOT / ref.group(1)
            if not code_path.exists():
                errors.append(f"{rel}: файл кода {ref.group(1)} не найден")
            else:
                code = code_path.read_text(encoding="utf-8")
                for cls in sorted(declared):
                    if not re.search(rf"\b(class|interface|type|enum)\s+{cls}\b", code):
                        errors.append(f"{rel}: класс {cls} есть на диаграмме, но нет в {ref.group(1)}")
    return errors


def main() -> int:
    files = sorted(SRC.rglob("*.puml"))
    errors = [e for f in files for e in check_file(f)]
    for e in errors:
        print(f"[ERROR] {e}")
    print(f"[INFO] Проверено файлов: {len(files)}, ошибок: {len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
