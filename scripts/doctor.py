from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from datetime import datetime
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
RUNTIME_DIR = SKILL_DIR / ".runtime"
VENV_DIR = RUNTIME_DIR / "venv"


def run(args: list[str], cwd: Path | None = None, timeout: int = 60) -> subprocess.CompletedProcess[str]:
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
        check=False,
    )


def first_line(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "")


def xelatex_installer_args(path: str) -> list[str]:
    return ["--disable-installer"] if "miktex" in path.lower() else []


def command_candidates(name: str) -> list[str]:
    candidates: list[Path] = []
    direct = Path(name)
    if direct.is_absolute():
        candidates.append(direct)
    found = shutil.which(name)
    if found:
        found_path = Path(found)
        candidates.append(found_path)
        for parent in found_path.parents:
            candidates.append(parent / "native" / "poppler" / "Library" / "bin" / f"{name}.exe")
    if os.name == "nt" and not direct.is_absolute():
        extensions = [suffix.lower() for suffix in os.environ.get("PATHEXT", ".EXE;.CMD;.BAT").split(";")]
        for folder in os.environ.get("PATH", "").split(os.pathsep):
            if not folder:
                continue
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


def probe(name: str, version_args: list[str]) -> dict[str, str]:
    candidates = command_candidates(name)
    if not candidates:
        return {"status": "missing"}
    last: dict[str, str] = {"status": "failed", "path": candidates[-1]}
    for path in candidates:
        try:
            result = run([path, *version_args], timeout=20)
        except (OSError, subprocess.TimeoutExpired) as exc:
            last = {"status": "failed", "path": path, "detail": str(exc)}
            continue
        output = result.stdout + "\n" + result.stderr
        version = first_line(output)
        if result.returncode == 0:
            return {"status": "ok", "path": path, "version": version}
        last = {
            "status": "failed",
            "path": path,
            "version": version,
            "detail": "\n".join(output.splitlines()[-8:]).strip(),
        }
    return last


def venv_python() -> Path:
    return VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def check_matplotlib(python: Path) -> dict[str, str]:
    if not python.exists():
        return {"status": "missing", "detail": "Create the local virtual environment first."}
    result = run(
        [str(python), "-c", "import matplotlib; print(matplotlib.__version__)"],
        timeout=30,
    )
    return {
        "status": "ok" if result.returncode == 0 else "missing",
        "version": first_line(result.stdout),
        "detail": first_line(result.stderr),
    }


def smoke_test(xelatex: dict[str, str]) -> dict[str, str]:
    if xelatex.get("status") != "ok":
        detail = xelatex.get("detail") or "XeLaTeX is unavailable."
        return {"status": "blocked", "detail": detail}
    with tempfile.TemporaryDirectory(prefix="lesson-slides-doctor-") as temp_name:
        temp = Path(temp_name)
        for name in ("smoke-test.tex", "lesson-theme.sty"):
            shutil.copy2(SKILL_DIR / "assets" / name, temp / name)
        result = run(
            [
                xelatex["path"],
                *xelatex_installer_args(xelatex["path"]),
                "-interaction=nonstopmode",
                "-halt-on-error",
                "smoke-test.tex",
            ],
            cwd=temp,
            timeout=90,
        )
        pdf = temp / "smoke-test.pdf"
        if result.returncode == 0 and pdf.exists():
            return {"status": "ok"}
        detail = "\n".join((result.stdout + "\n" + result.stderr).splitlines()[-12:])
        return {"status": "failed", "detail": detail}


def self_test() -> None:
    assert first_line("\n\nalpha\nbeta") == "alpha"
    assert first_line("") == ""
    expected = Path("Scripts/python.exe" if os.name == "nt" else "bin/python")
    assert venv_python().relative_to(VENV_DIR) == expected
    assert xelatex_installer_args(r"E:\MiKTeX\xelatex.exe") == ["--disable-installer"]
    assert xelatex_installer_args(r"C:\texlive\xelatex.exe") == []
    print("doctor self-test: ok")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check and record the lesson-slide runtime.")
    parser.add_argument("--create-venv", action="store_true")
    parser.add_argument("--write", action="store_true", help="Write .runtime/environment.json.")
    parser.add_argument(
        "--image-tool",
        choices=("available", "unavailable", "unknown"),
        default="unknown",
        help="Record host-level image generation availability.",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0

    if args.create_venv and not venv_python().exists():
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        venv.EnvBuilder(with_pip=True).create(VENV_DIR)

    python_check = probe(sys.executable, ["--version"])
    xelatex = probe("xelatex", ["--version"])
    checks = {
        "python": python_check,
        "xelatex": xelatex,
        "pdfinfo": probe("pdfinfo", ["-v"]),
        "pdftoppm": probe("pdftoppm", ["-v"]),
        "local_venv": {
            "status": "ok" if venv_python().exists() else "missing",
            "path": str(venv_python()),
        },
        "matplotlib": check_matplotlib(venv_python()),
        "image_generation": {"status": args.image_tool},
        "latex_smoke_test": smoke_test(xelatex),
    }

    ready = all(
        checks[name]["status"] == "ok"
        for name in ("python", "xelatex", "pdfinfo", "pdftoppm", "latex_smoke_test")
    )
    manifest = {
        "schema": 1,
        "checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "ready_for_latex": ready,
        "checks": checks,
    }

    if args.write:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        path = RUNTIME_DIR / "environment.json"
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"recorded: {path}")

    for name, result in checks.items():
        detail = (
            result.get("version")
            if result["status"] in {"ok", "available"}
            else result.get("detail") or result.get("version") or result.get("path", "")
        )
        print(f"{name}: {result['status']}" + (f" - {detail}" if detail else ""))
    print(f"ready_for_latex: {str(ready).lower()}")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
