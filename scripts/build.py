from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path


def run(
    args: list[str],
    cwd: Path | None = None,
    timeout: int = 120,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [str(arg) for arg in args]
    if os.name == "nt" and Path(command[0]).suffix.lower() in {".cmd", ".bat"}:
        command = [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", *command]
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
        check=False,
    )


def command_candidates(name: str) -> list[str]:
    candidates: list[Path] = []
    poppler_data = os.environ.get("POPPLER_DATADIR")
    if poppler_data and name in {"pdfinfo", "pdftoppm"}:
        candidates.append(Path(poppler_data).parents[1] / "Library" / "bin" / f"{name}.exe")
    found = shutil.which(name)
    if found:
        found_path = Path(found)
        candidates.append(found_path)
        for parent in found_path.parents:
            candidates.append(parent / "native" / "poppler" / "Library" / "bin" / f"{name}.exe")
    if os.name == "nt":
        extensions = [suffix.lower() for suffix in os.environ.get("PATHEXT", ".EXE;.CMD;.BAT").split(";")]
        for folder in os.environ.get("PATH", "").split(os.pathsep):
            if folder:
                base = Path(folder) / name
                candidates.extend(base.with_suffix(suffix) for suffix in extensions)
    unique: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).lower()
        if candidate.exists() and key not in seen:
            seen.add(key)
            unique.append(str(candidate))
    return unique


def xelatex_installer_args(path: str) -> list[str]:
    return ["--disable-installer"] if "miktex" in path.lower() else []


def poppler_data_candidates(path: str) -> list[Path]:
    return [
        candidate
        for parent in Path(path).parents
        for candidate in (
            parent / "share" / "poppler",
            parent / "native" / "poppler" / "share" / "poppler",
        )
    ]


def require(name: str, version_args: list[str]) -> str:
    candidates = command_candidates(name)
    if name in {"pdfinfo", "pdftoppm"}:
        candidates.sort(key=lambda path: "miktex" in path.lower())
    for path in candidates:
        try:
            result = run([path, *version_args], timeout=20)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            return path
    raise RuntimeError(f"Missing or non-runnable required command: {name}")


def parse_pdf_info(text: str) -> tuple[int, tuple[float, float]]:
    pages_match = re.search(r"^Pages:\s+(\d+)", text, re.MULTILINE)
    size_match = re.search(r"^Page size:\s+([\d.]+)\s+x\s+([\d.]+)", text, re.MULTILINE)
    if not pages_match or not size_match:
        raise ValueError("Could not read page count or page size from pdfinfo.")
    return int(pages_match.group(1)), (float(size_match.group(1)), float(size_match.group(2)))


def is_169(size: tuple[float, float], tolerance: float = 0.03) -> bool:
    width, height = size
    return height > 0 and abs(width / height - 16 / 9) <= tolerance


def note_pages(text: str) -> list[int]:
    return [int(value) for value in re.findall(r"^##\s*第\s*(\d+)\s*页", text, re.MULTILINE)]


def validate_elements(data: object, tex_text: str, pages: int) -> int:
    if not isinstance(data, list):
        raise ValueError("Element manifest must be a JSON array.")
    ids = re.findall(r"\\LessonElement\{([A-Za-z][A-Za-z0-9._:-]*)\}", tex_text)
    if len(ids) != len(set(ids)):
        raise ValueError("LessonElement IDs must be unique.")
    manifest_ids: list[str] = []
    for item in data:
        if not isinstance(item, dict) or not {"id", "page", "kind"} <= item.keys():
            raise ValueError("Each element needs id, page, and kind.")
        if "source_tex" not in item and "source_text" not in item:
            raise ValueError(f"Element {item.get('id')} needs source_tex or source_text.")
        if not isinstance(item["page"], int) or not 1 <= item["page"] <= pages:
            raise ValueError(f"Element {item.get('id')} has an invalid page.")
        manifest_ids.append(str(item["id"]))
    if len(manifest_ids) != len(set(manifest_ids)):
        raise ValueError("Manifest element IDs must be unique.")
    if set(ids) != set(manifest_ids):
        raise ValueError(f"Element IDs differ. tex={sorted(ids)}, manifest={sorted(manifest_ids)}")
    return len(ids)


def self_test() -> None:
    pages, size = parse_pdf_info("Pages:          12\nPage size:      1600 x 900 pts\n")
    assert pages == 12
    assert is_169(size)
    assert note_pages("## 第 1 页：封面\n\n## 第2页：概念") == [1, 2]
    assert validate_elements(
        [{"id": "s01-x", "page": 1, "kind": "formula", "source_tex": "x"}],
        r"\LessonElement{s01-x}{x}",
        1,
    ) == 1
    assert xelatex_installer_args(r"E:\MiKTeX\xelatex.exe") == ["--disable-installer"]
    assert xelatex_installer_args(r"C:\texlive\xelatex.exe") == []
    assert Path(r"C:\deps\native\poppler\share\poppler") in poppler_data_candidates(
        r"C:\deps\bin\override\pdftoppm.cmd"
    )
    print("build self-test: ok")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile, validate, and render a Beamer lesson.")
    parser.add_argument("tex", nargs="?")
    parser.add_argument("--notes")
    parser.add_argument("--elements")
    parser.add_argument("--output-dir")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0
    if not args.tex:
        parser.error("tex is required unless --self-test is used")

    tex = Path(args.tex).resolve()
    if not tex.exists():
        raise FileNotFoundError(tex)
    output_dir = Path(args.output_dir).resolve() if args.output_dir else tex.parent / "build"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        xelatex = require("xelatex", ["--version"])
        pdfinfo = require("pdfinfo", ["-v"])
        pdftoppm = require("pdftoppm", ["-v"])
    except RuntimeError as exc:
        print(exc)
        return 1

    command = [
        xelatex,
        *xelatex_installer_args(xelatex),
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-output-directory={output_dir}",
        tex.name,
    ]
    for pass_number in (1, 2):
        result = run(command, cwd=tex.parent, timeout=180)
        if result.returncode != 0:
            tail = "\n".join((result.stdout + "\n" + result.stderr).splitlines()[-30:])
            print(f"XeLaTeX pass {pass_number} failed:\n{tail}")
            return 1

    pdf = output_dir / f"{tex.stem}.pdf"
    log = output_dir / f"{tex.stem}.log"
    if not pdf.exists():
        print(f"Expected PDF was not created: {pdf}")
        return 1

    info_result = run([pdfinfo, str(pdf)], timeout=30)
    if info_result.returncode != 0:
        print(info_result.stderr)
        return 1
    pages, size = parse_pdf_info(info_result.stdout)
    if not is_169(size):
        print(f"Page ratio is not 16:9: {size[0]} x {size[1]}")
        return 1

    if args.notes:
        notes = Path(args.notes).resolve()
        numbers = note_pages(notes.read_text(encoding="utf-8"))
        expected = list(range(1, pages + 1))
        if numbers != expected:
            print(f"Speaker-note pages do not match the PDF. expected={expected}, found={numbers}")
            return 1

    if args.elements:
        elements = Path(args.elements).resolve()
        try:
            mapped = validate_elements(
                json.loads(elements.read_text(encoding="utf-8")),
                tex.read_text(encoding="utf-8"),
                pages,
            )
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"Element mapping failed: {exc}")
            return 1
        print(f"mapped elements: {mapped}")

    if log.exists():
        log_text = log.read_text(encoding="utf-8", errors="replace")
        overfull = len(re.findall(r"Overfull \\[hv]box", log_text))
        undefined = len(re.findall(r"Undefined control sequence|undefined references?", log_text, re.I))
        print(f"log warnings: overfull={overfull}, undefined={undefined}")
        if undefined:
            return 1

    previews = output_dir / "previews"
    previews.mkdir(exist_ok=True)
    for old in previews.glob("slide-*.png"):
        old.unlink()
    render_env = os.environ.copy()
    poppler_data = next((path for path in poppler_data_candidates(pdftoppm) if path.exists()), None)
    if poppler_data:
        render_env["POPPLER_DATADIR"] = str(poppler_data)
    print(f"render tool: {pdftoppm}")
    print(f"poppler data: {poppler_data or 'not found'}")
    render = run(
        [pdftoppm, "-png", "-r", "144", str(pdf), str(previews / "slide")],
        timeout=180,
        env=render_env,
    )
    if render.returncode != 0:
        print(render.stderr)
        return 1
    rendered = len(list(previews.glob("slide-*.png")))
    if rendered != pages:
        print(f"Rendered preview count mismatch: PDF={pages}, previews={rendered}")
        return 1

    print(f"built: {pdf}")
    print(f"pages: {pages}")
    print(f"previews: {previews}")
    print("manual visual inspection is still required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
