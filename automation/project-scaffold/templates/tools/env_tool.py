#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conda & Mamba Environment Manager and Hardware Diagnostic Tool.

Zero-dependency standard library utility for:
1. Environment diagnosis (NVIDIA GPU, CUDA, Mamba, Miniforge, Python version).
2. One-command environment setup with Mamba acceleration and daemon runner patching.
3. Sanitizing dirty/bloated Conda exports into lean, declarative environment.yml files.
4. Exporting clean, portable environment specifications from the active environment.
"""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

SYSTEM_C_LIBRARIES_PREFIXES = (
    "ca-certificates",
    "certifi",
    "vc",
    "vc14",
    "vs2015",
    "ucrt",
    "m2w64",
    "pthread",
    "openssl",
    "bzip2",
    "libzlib",
    "zlib",
    "zstd",
    "libexpat",
    "expat",
    "libffi",
    "libhwloc",
    "libiconv",
    "liblzma",
    "libsqlite",
    "libwinpthread",
    "libxml2",
    "libdeflate",
    "libjpeg",
    "libpng",
    "libtiff",
    "libwebp",
    "libxcb",
    "libblas",
    "libcblas",
    "liblapack",
    "libboost",
    "intel-openmp",
    "llvm-openmp",
    "tbb",
    "sqlite",
    "tzdata",
    "xz",
    "icu",
    "tk",
    "cuda-cccl",
    "cuda-cudart",
    "cuda-cupti",
    "cuda-libraries",
    "cuda-nvrtc",
    "cuda-nvtx",
    "cuda-opencl",
    "cuda-profiler-api",
    "cuda-runtime",
    "cuda-version",
    "libcublas",
    "libcufft",
    "libcurand",
    "libcusolver",
    "libcusparse",
    "libnpp",
    "libnvjitlink",
    "libnvjpeg",
    "xorg",
    "msys2",
    "win_inet_pton",
    "pysocks",
    "qhull",
    "munkres",
    "kiwisolver",
    "cycler",
    "contourpy",
    "fonttools",
    "freetype",
    "lerc",
    "mpg123",
    "lame",
    "soxr",
)


def _get_registered_conda_roots() -> List[Path]:
    """Read Conda installation and environment roots dynamically from registry and standard paths."""
    roots: List[Path] = []

    # 1. Environment variables
    for var in ("MAMBA_ROOT_PREFIX", "CONDA_ROOT", "CONDA_EXE", "MAMBA_EXE", "CONDA_PREFIX"):
        val = os.environ.get(var)
        if val:
            p = Path(val)
            if p.is_file():
                p = p.parent.parent
            if p.is_dir() and p not in roots:
                roots.append(p)

    # 2. ~/.conda/environments.txt (Universal Conda registration file on Windows/macOS/Linux)
    env_file = Path.home() / ".conda" / "environments.txt"
    if env_file.is_file():
        try:
            for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line:
                    p = Path(line)
                    if p.is_dir() and p not in roots:
                        roots.append(p)
        except Exception:
            pass

    # 3. Standard user & system directory paths
    sys_drive = os.environ.get("SystemDrive", "C:")
    candidates = [
        Path.home() / "miniforge3",
        Path.home() / "mambaforge",
        Path.home() / "miniconda3",
        Path.home() / "anaconda3",
        Path(os.environ.get("LOCALAPPDATA", "")) / "miniforge3",
        Path(os.environ.get("LOCALAPPDATA", "")) / "miniconda3",
        Path(os.environ.get("LOCALAPPDATA", "")) / "anaconda3",
        Path(os.environ.get("ProgramData", f"{sys_drive}/ProgramData")) / "miniforge3",
        Path(os.environ.get("ProgramData", f"{sys_drive}/ProgramData")) / "miniconda3",
        Path(os.environ.get("ProgramData", f"{sys_drive}/ProgramData")) / "anaconda3",
        Path(f"{sys_drive}/miniforge3"),
        Path(f"{sys_drive}/miniconda3"),
        Path(f"{sys_drive}/anaconda3"),
    ]
    for c in candidates:
        if c.is_dir() and c not in roots:
            roots.append(c)

    return roots


def find_mamba_executable() -> Optional[str]:
    """Find Mamba executable on system PATH or dynamic Conda/Miniforge locations."""
    # 1. Environment variable override
    mamba_exe = os.environ.get("MAMBA_EXE")
    if mamba_exe and Path(mamba_exe).is_file():
        return mamba_exe

    # 2. System PATH
    found = shutil.which("mamba")
    if found:
        return found

    # 3. Dynamic lookup from registered Conda roots
    for root in _get_registered_conda_roots():
        for sub in (
            Path("condabin") / "mamba.bat",
            Path("Scripts") / "mamba.exe",
            Path("bin") / "mamba",
        ):
            cand = root / sub
            if cand.is_file():
                return str(cand)

    return None


def find_conda_executable() -> Optional[str]:
    """Find Conda executable on system PATH or dynamic Conda locations."""
    # 1. Environment variable override
    conda_exe = os.environ.get("CONDA_EXE")
    if conda_exe and Path(conda_exe).is_file():
        return conda_exe

    # 2. System PATH
    found = shutil.which("conda")
    if found:
        return found

    # 3. Dynamic lookup from registered Conda roots
    for root in _get_registered_conda_roots():
        for sub in (
            Path("condabin") / "conda.bat",
            Path("Scripts") / "conda.exe",
            Path("bin") / "conda",
        ):
            cand = root / sub
            if cand.is_file():
                return str(cand)

    return None


def detect_gpu_info() -> Dict[str, Optional[str]]:
    """Detect NVIDIA GPU name, driver version, and VRAM using nvidia-smi."""
    info = {
        "available": False,
        "name": None,
        "driver_version": None,
        "cuda_version": None,
        "vram_total_mb": None,
        "vram_free_mb": None,
    }
    smi = shutil.which("nvidia-smi")
    if not smi:
        # Check standard Windows nvidia-smi location dynamically
        sys_root = os.environ.get("SystemRoot", r"C:\Windows")
        default_smi = Path(sys_root) / "System32" / "nvidia-smi.exe"
        if default_smi.is_file():
            smi = str(default_smi)

    if not smi:
        return info

    try:
        proc = subprocess.run(
            [smi, "--query-gpu=name,driver_version,memory.total,memory.free", "--format=csv,noheader,nounits"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            parts = [p.strip() for p in proc.stdout.strip().splitlines()[0].split(",")]
            if len(parts) >= 4:
                info["available"] = True
                info["name"] = parts[0]
                info["driver_version"] = parts[1]
                info["vram_total_mb"] = parts[2]
                info["vram_free_mb"] = parts[3]

        # Query CUDA version
        proc_cuda = subprocess.run(
            [smi],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            check=False,
        )
        if proc_cuda.returncode == 0:
            m = re.search(r"CUDA Version:\s*(\d+\.\d+)", proc_cuda.stdout)
            if m:
                info["cuda_version"] = m.group(1)
    except Exception:
        pass

    return info


def run_doctor() -> int:
    """Print complete environment diagnostic checkup."""
    print("=" * 66)
    print(" 🏥 Conda & Hardware Diagnostics Doctor (env_tool)")
    print("=" * 66)

    # 1. Python runtime
    print("• Host Python:")
    print(f"  - Version     : {sys.version.split()[0]} ({sys.platform})")
    print(f"  - Executable  : {sys.executable}")
    active_conda = os.environ.get("CONDA_DEFAULT_ENV")
    active_prefix = os.environ.get("CONDA_PREFIX")
    if active_conda or active_prefix:
        print(f"  - Active Env  : {active_conda or '<prefix>'} ({active_prefix})")
    else:
        print("  - Active Env  : None (running in host/system environment)")

    # 2. Package Managers (Mamba / Conda)
    print("\n• Environment Managers:")
    mamba_bin = find_mamba_executable()
    if mamba_bin:
        print(f"  - Mamba       : ✅ FOUND ({mamba_bin})")
    else:
        print("  - Mamba       : ❌ Not detected")

    conda_bin = find_conda_executable()
    if conda_bin:
        print(f"  - Conda       : ✅ FOUND ({conda_bin})")
    else:
        print("  - Conda       : ❌ Not detected")

    # 3. Hardware & GPU
    print("\n• Hardware & Compute Accelerators:")
    gpu = detect_gpu_info()
    if gpu["available"]:
        print(f"  - NVIDIA GPU  : ✅ {gpu['name']}")
        print(f"  - Driver      : v{gpu['driver_version']} (Supported CUDA: v{gpu['cuda_version'] or 'Unknown'})")
        print(f"  - VRAM        : {gpu['vram_total_mb']} MB Total (Free: {gpu['vram_free_mb']} MB)")
    else:
        print("  - NVIDIA GPU  : ℹ️ No NVIDIA GPU detected via nvidia-smi (CPU mode)")

    # 4. Project Local Environment
    print("\n• Workspace Environment Status:")
    local_conda = Path("./.conda")
    local_venv = Path("./.venv")
    env_yaml = Path("./environment.yml")

    if local_conda.is_dir():
        print("  - Local .conda: ✅ Present (Prefix mode detected)")
    elif local_venv.is_dir():
        print("  - Local .venv : ✅ Present (venv mode detected)")
    else:
        print("  - Local Env   : ℹ️ No local .conda/.venv directory in current folder")

    if env_yaml.is_file():
        print(f"  - Specification: ✅ environment.yml found ({env_yaml.stat().st_size} bytes)")
    else:
        print("  - Specification: ⚠️ No environment.yml in current directory")

    print("=" * 66)
    return 0


def sanitize_environment_yaml(
    content: str,
    target_name: Optional[str] = None,
    target_python: Optional[str] = None,
) -> str:
    """Sanitize bloated or dirty Conda environment export.

    Strips:
    - `prefix: ...`
    - System transitive C/C++ runtimes (ca-certificates, m2w64, vc14, ucrt, etc.)
    - Build hashes (`=h...`, `_0`, etc.)
    Preserves:
    - Channels
    - Essential data science, AI, and developer packages
    - Pip requirements block
    """
    lines = content.splitlines()
    cleaned_lines: List[str] = []
    in_dependencies = False
    in_pip = False
    pip_lines: List[str] = []

    name = target_name
    channels: List[str] = []

    for line in lines:
        stripped = line.strip()

        # Extract name if not overridden
        if stripped.startswith("name:") and not target_name:
            name = stripped.split(":", 1)[1].strip()
            continue
        elif stripped.startswith("name:"):
            continue

        # Strip prefix
        if stripped.startswith("prefix:"):
            continue

        # Track sections
        if stripped == "channels:":
            in_dependencies = False
            continue

        if stripped == "dependencies:":
            in_dependencies = True
            continue

        if in_dependencies and stripped.startswith("- pip:"):
            in_pip = True
            continue

        # Channels block
        if not in_dependencies:
            if stripped.startswith("- "):
                ch = stripped[2:].strip()
                # filter out raw anaconda urls
                if not ch.startswith("http://") and not ch.startswith("https://"):
                    if ch not in channels:
                        channels.append(ch)
            continue

        # Inside pip
        if in_pip:
            if stripped.startswith("- "):
                req = stripped[2:].strip()
                # clean requirement
                pip_lines.append(req)
            continue

        # Inside conda dependencies
        if in_dependencies and not in_pip:
            if stripped.startswith("- "):
                pkg_spec = stripped[2:].strip()
                # Extract package name and version
                # e.g., "python=3.12.13=h..." -> pkg="python", ver="3.12.13"
                parts = pkg_spec.split("=")
                pkg_name = parts[0].strip()

                # Filter out system C/C++ transitive packages
                is_system_bloat = any(pkg_name.lower().startswith(p) for p in SYSTEM_C_LIBRARIES_PREFIXES)
                if is_system_bloat:
                    continue

                if pkg_name == "python":
                    if target_python:
                        cleaned_lines.append(f"  - python={target_python}")
                    elif len(parts) >= 2:
                        cleaned_lines.append(f"  - python={parts[1]}")
                    else:
                        cleaned_lines.append("  - python=3.14")
                    continue

                # Clean versions (keep >= or single =, strip build hash)
                if len(parts) >= 2:
                    ver = parts[1].strip()
                    cleaned_lines.append(f"  - {pkg_name}={ver}")
                else:
                    cleaned_lines.append(f"  - {pkg_name}")

    # Build standardized output
    if not name:
        name = "project-env"

    # Default essential channels if none parsed
    if not channels:
        channels = ["conda-forge", "defaults"]
    elif "conda-forge" not in channels:
        channels.insert(0, "conda-forge")

    output: List[str] = [f"name: {name}", "channels:"]
    for ch in channels:
        output.append(f"  - {ch}")

    output.append("dependencies:")
    # Ensure python is first
    py_line = next((l for l in cleaned_lines if "python" in l), None)
    if py_line:
        output.append(py_line)
        cleaned_lines.remove(py_line)
    else:
        output.append(f"  - python={target_python or '3.14'}")

    # Ensure pip is included
    if "  - pip" not in cleaned_lines:
        output.append("  - pip")

    for cl in sorted(set(cleaned_lines)):
        output.append(cl)

    if pip_lines:
        output.append("  - pip:")
        for pl in sorted(set(pip_lines)):
            output.append(f"      - {pl}")

    return "\n".join(output) + "\n"


def update_daemon_scripts(project_dir: Path, target_python: Path) -> List[str]:
    """Patch daemon scripts (run_daemon.ps1 / run_daemon.bat) to point to target python."""
    updated: List[str] = []
    py_path_str = str(target_python.resolve())

    # 1. PowerShell run_daemon.ps1
    ps1_file = project_dir / "run_daemon.ps1"
    if ps1_file.is_file():
        content = ps1_file.read_text(encoding="utf-8")
        # Replace $condaPython = "..."
        new_content = re.sub(
            r'(\$condaPython\s*=\s*")[^"]+(")',
            lambda m: f"{m.group(1)}{py_path_str}{m.group(2)}",
            content,
        )
        if new_content != content:
            ps1_file.write_text(new_content, encoding="utf-8")
            updated.append("run_daemon.ps1")

    # 2. Batch run_daemon.bat
    bat_file = project_dir / "run_daemon.bat"
    if bat_file.is_file():
        content = bat_file.read_text(encoding="utf-8")
        # Replace set CONDA_ENV=...
        env_dir_str = str(target_python.parent.resolve())
        new_content = re.sub(
            r'(set\s+CONDA_ENV=)[^\r\n]+',
            lambda m: f"{m.group(1)}{env_dir_str}",
            content,
        )
        if new_content != content:
            bat_file.write_text(new_content, encoding="utf-8")
            updated.append("run_daemon.bat")

    return updated


def run_setup(
    env_file: Path,
    use_prefix: bool = False,
    custom_name: Optional[str] = None,
    dry_run: bool = False,
) -> int:
    """Execute environment creation with Mamba/Conda and update daemons."""
    if not env_file.is_file():
        print(f"❌ Error: Environment file '{env_file}' not found!", file=sys.stderr)
        return 1

    installer = find_mamba_executable() or find_conda_executable()
    if not installer:
        print("❌ Error: Neither Mamba nor Conda was found on system!", file=sys.stderr)
        return 1

    tool_name = "mamba" if "mamba" in installer.lower() else "conda"
    cmd = [installer, "env", "create", "-f", str(env_file)]

    if use_prefix:
        cmd.extend(["-p", "./.conda"])
    elif custom_name:
        cmd.extend(["-n", custom_name])

    print(f"🚀 Running Environment Setup via {tool_name.upper()}:")
    print(f"   Command: {' '.join(cmd)}")

    if dry_run:
        print("ℹ️ Dry-run mode enabled: skipping actual command execution.")
        return 0

    res = subprocess.run(cmd)
    if res.returncode != 0:
        print(f"❌ Error: {tool_name} failed with exit code {res.returncode}", file=sys.stderr)
        return res.returncode

    # Locate newly created python executable
    if use_prefix:
        py_exec = Path("./.conda/python.exe") if sys.platform == "win32" else Path("./.conda/bin/python")
    else:
        # Check standard envs location
        py_exec = Path(sys.executable)

    if py_exec.exists():
        patched = update_daemon_scripts(Path("."), py_exec)
        if patched:
            print(f"✅ Successfully patched daemon runner scripts: {', '.join(patched)}")

    print(f"🎉 Environment successfully configured via {tool_name}!")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="env_tool",
        description="Conda & Mamba Environment Manager & Hardware Diagnostics",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: doctor
    subparsers.add_parser("doctor", help="Inspect Python, Mamba/Conda, NVIDIA GPU, and workspace environment")

    # Command: setup
    setup_p = subparsers.add_parser("setup", help="Create environment from environment.yml with Mamba acceleration")
    setup_p.add_argument("-f", "--file", type=Path, default=Path("environment.yml"), help="Path to environment.yml")
    setup_p.add_argument("-p", "--prefix", action="store_true", help="Create as local project prefix (./.conda)")
    setup_p.add_argument("-n", "--name", type=str, help="Custom environment name (overrides name in YAML)")
    setup_p.add_argument("--dry-run", action="store_true", help="Print command without executing")

    # Command: sanitize
    san_p = subparsers.add_parser("sanitize", help="Sanitize a bloated/dirty Conda export into a lean declarative file")
    san_p.add_argument("input", type=Path, help="Input bloated YAML file")
    san_p.add_argument("-o", "--output", type=Path, help="Output sanitized YAML file (defaults to stdout)")
    san_p.add_argument("-n", "--name", type=str, help="Target environment name")
    san_p.add_argument("--python", type=str, default="3.14", help="Target Python version (default: 3.14)")

    # Command: export
    exp_p = subparsers.add_parser("export", help="Export lean environment.yml from active Conda environment")
    exp_p.add_argument("-o", "--output", type=Path, default=Path("environment.yml"), help="Output path (default: environment.yml)")
    exp_p.add_argument("-n", "--name", type=str, help="Environment name")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command or args.command == "doctor":
        return run_doctor()

    if args.command == "setup":
        return run_setup(args.file, use_prefix=args.prefix, custom_name=args.name, dry_run=args.dry_run)

    if args.command == "sanitize":
        if not args.input.is_file():
            print(f"❌ Error: File '{args.input}' not found!", file=sys.stderr)
            return 1
        content = args.input.read_text(encoding="utf-8", errors="replace")
        cleaned = sanitize_environment_yaml(content, target_name=args.name, target_python=args.python)
        if args.output:
            args.output.write_text(cleaned, encoding="utf-8")
            print(f"✅ Sanitized {args.input.name} -> {args.output} ({len(cleaned.splitlines())} lines)")
        else:
            print(cleaned)
        return 0

    if args.command == "export":
        conda_bin = find_conda_executable() or find_mamba_executable()
        if not conda_bin:
            print("❌ Error: Neither conda nor mamba found to export environment.", file=sys.stderr)
            return 1
        proc = subprocess.run(
            [conda_bin, "env", "export", "--no-builds"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            print(f"❌ Export failed: {proc.stderr}", file=sys.stderr)
            return proc.returncode
        cleaned = sanitize_environment_yaml(proc.stdout, target_name=args.name)
        args.output.write_text(cleaned, encoding="utf-8")
        print(f"✅ Exported active environment to {args.output} ({len(cleaned.splitlines())} lines)")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
