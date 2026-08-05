#!/usr/bin/env python3
"""ESP-IDF Windows build runner.

Compiles project2_task/esp32/testpro4 with the Windows ESP-IDF environment
installed by Espressif IDF Installation Manager (EIM). The firmware is mirrored
to a guarded build workspace first so sdkconfig/build output does not dirty the
candidate project tree. By default the guarded build directory is kept between
runs, so ESP-IDF/Ninja/ccache can perform incremental rebuilds.

Usage:
    python run_espidf_build.py [PROJECT_DIR]

Exit codes:
    0  - build succeeded
    1  - ESP-IDF build failed
    2  - environment or project setup error
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


DEFAULT_TARGET = os.environ.get("ESP_IDF_TARGET", "esp32s3")
DEFAULT_JOBS = max(1, int(os.environ.get("ESP_IDF_BUILD_JOBS", str(os.cpu_count() or 1))))
DEFAULT_ACTIVATION_SCRIPT = Path(
    os.environ.get(
        "ESP_IDF_ACTIVATION_SCRIPT",
        "",
    )
)


def default_build_root() -> Path:
    env_root = os.environ.get("ESP_IDF_BUILD_ROOT")
    if env_root:
        return Path(env_root)
    return Path(tempfile.gettempdir()) / "project2_espidf_windows_build"


def default_project_dir(script_dir: Path) -> Path:
    if script_dir.name.lower() == "tools":
        return script_dir.parent / "project2_task"
    return script_dir.parent / "workspace" / "project2_task"


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def resolve_inside(path: Path, base: Path, label: str) -> Path:
    resolved = path.resolve()
    base_resolved = base.resolve()
    if resolved != base_resolved and base_resolved not in resolved.parents:
        raise RuntimeError(f"{label} is outside build root: {resolved}")
    return resolved


def should_copy(src: Path, dst: Path) -> bool:
    if not dst.exists():
        return True
    src_stat = src.stat()
    dst_stat = dst.stat()
    return src_stat.st_size != dst_stat.st_size or src_stat.st_mtime_ns != dst_stat.st_mtime_ns


def mirror_tree_incremental(src_root: Path, dst_root: Path) -> tuple[int, int, int]:
    copied = 0
    removed = 0
    kept = 0

    ignored_dirs = {".git", "build", "__pycache__"}
    ignored_suffixes = (".pyc", ".pyo", ".log")

    src_files: set[Path] = set()
    for src in src_root.rglob("*"):
        rel = src.relative_to(src_root)
        if any(part in ignored_dirs for part in rel.parts):
            continue
        if src.is_dir():
            continue
        if src.name.endswith(ignored_suffixes):
            continue
        src_files.add(rel)
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if should_copy(src, dst):
            shutil.copy2(src, dst)
            copied += 1
        else:
            kept += 1

    for dst in sorted(dst_root.rglob("*"), reverse=True):
        rel = dst.relative_to(dst_root)
        if rel.parts and rel.parts[0] == "build":
            continue
        if dst.is_dir():
            try:
                dst.rmdir()
            except OSError:
                pass
            continue
        if rel not in src_files:
            dst.unlink()
            removed += 1

    return copied, kept, removed


def copy_firmware_project(project_dir: Path, build_root: Path, clean_copy: bool) -> tuple[Path, Path, tuple[int, int, int]]:
    firmware_src = project_dir / "esp32" / "testpro4"
    if not firmware_src.is_dir():
        raise RuntimeError(f"firmware project not found: {firmware_src}")
    if not (firmware_src / "CMakeLists.txt").is_file():
        raise RuntimeError(f"missing CMakeLists.txt under: {firmware_src}")

    build_root = build_root.resolve()
    work_project = build_root / "project2_task"
    firmware_dst = work_project / "esp32" / "testpro4"
    resolve_inside(firmware_dst, build_root, "firmware build copy")

    if clean_copy and firmware_dst.exists():
        shutil.rmtree(firmware_dst)
    firmware_dst.parent.mkdir(parents=True, exist_ok=True)

    stats = mirror_tree_incremental(firmware_src, firmware_dst)
    return work_project, firmware_dst, stats


def run_powershell_build(
    firmware_dir: Path,
    activation_script: Path,
    target: str,
    set_target: bool,
    jobs: int,
) -> int:
    build_dir = firmware_dir / "build"
    lines = [
        "$ErrorActionPreference = 'Stop'",
        f". {ps_quote(str(activation_script))}",
        f"Set-Location -LiteralPath {ps_quote(str(firmware_dir))}",
        "$idfCommand = Get-Command idf.py -ErrorAction Stop",
        "$idfDisplay = if ($idfCommand.Source) { $idfCommand.Source } else { $idfCommand.Definition }",
        'Write-Host "[espidf] idf_py=$idfDisplay"',
        "$env:IDF_CCACHE_ENABLE = '1'",
        "$env:CCACHE_ENABLE = '1'",
        f"$env:CMAKE_BUILD_PARALLEL_LEVEL = '{jobs}'",
        f"$env:NINJAFLAGS = '-j{jobs}'",
    ]
    if set_target or not (build_dir / "CMakeCache.txt").exists():
        lines.extend(
            [
                f"idf.py -B {ps_quote(str(build_dir))} set-target {ps_quote(target)}",
                "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }",
            ]
        )
    else:
        lines.append(f'Write-Host "[espidf] reuse_build_dir={str(build_dir)}"')
    lines.extend(
        [
            f"cmake --build {ps_quote(str(build_dir))} --parallel {jobs}",
            "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }",
        ]
    )
    script = "\n".join(lines)

    cmd = [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        script,
    ]
    return subprocess.run(cmd, cwd=str(firmware_dir)).returncode


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Build ESP-IDF firmware with Windows EIM.")
    parser.add_argument("project_dir", nargs="?", default=str(default_project_dir(script_dir)))
    parser.add_argument("--target", default=DEFAULT_TARGET)
    parser.add_argument(
        "--jobs",
        type=int,
        default=DEFAULT_JOBS,
        help="parallel build jobs passed to CMake/Ninja; defaults to logical CPU count or ESP_IDF_BUILD_JOBS",
    )
    parser.add_argument("--activation-script", default=str(DEFAULT_ACTIVATION_SCRIPT))
    parser.add_argument("--build-root", default=str(default_build_root()))
    parser.add_argument(
        "--clean-copy",
        action="store_true",
        help="remove the guarded firmware copy before mirroring; use after project reset or when a clean build is required",
    )
    parser.add_argument(
        "--set-target",
        action="store_true",
        help="force idf.py set-target before build; by default this is skipped when the build cache already exists",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).resolve()
    activation_script = Path(args.activation_script).resolve()
    build_root = Path(args.build_root).resolve()

    try:
        if not project_dir.is_dir():
            raise RuntimeError(f"project dir not found: {project_dir}")
        if not activation_script.is_file():
            raise RuntimeError(f"ESP-IDF activation script not found: {activation_script}")

        work_project, firmware_dir, mirror_stats = copy_firmware_project(
            project_dir, build_root, args.clean_copy
        )
    except Exception as exc:
        print(f"[espidf] ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"[espidf] source            = {project_dir}")
    print(f"[espidf] build_copy        = {work_project}")
    print(f"[espidf] firmware_copy     = {firmware_dir}")
    print(f"[espidf] activation_script = {activation_script}")
    print(f"[espidf] target            = {args.target}")
    print(f"[espidf] jobs              = {args.jobs}")
    print(f"[espidf] clean_copy        = {args.clean_copy}")
    print(f"[espidf] set_target        = {args.set_target}")
    print(
        "[espidf] mirror            = "
        f"copied={mirror_stats[0]} kept={mirror_stats[1]} removed={mirror_stats[2]}"
    )
    print("[espidf] note=Windows EIM incremental build; no Docker, WSL, flash, or monitor")
    sys.stdout.flush()

    try:
        rc = run_powershell_build(
            firmware_dir,
            activation_script,
            args.target,
            args.set_target,
            args.jobs,
        )
    except FileNotFoundError as exc:
        print(f"[espidf] ERROR: failed to start PowerShell: {exc}", file=sys.stderr)
        return 2

    if rc != 0:
        print(f"[espidf] ERROR: build failed with exit code {rc}", file=sys.stderr)
        return 1

    build_dir = firmware_dir / "build"
    bins = sorted(build_dir.glob("*.bin"))
    for bin_path in bins:
        print(f"[espidf] output_bin        = {bin_path}")
    print("[espidf] Build finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
