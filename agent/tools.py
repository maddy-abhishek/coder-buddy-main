import pathlib
import subprocess
from typing import Tuple

from langchain_core.tools import tool

PROJECT_ROOT = pathlib.Path.cwd() / "generated_project"


def safe_path_for_project(path: str) -> pathlib.Path:
    p = (PROJECT_ROOT / path).resolve()
    if PROJECT_ROOT.resolve() not in p.parents and PROJECT_ROOT.resolve() != p.parent and PROJECT_ROOT.resolve() != p:
        raise ValueError("Attempt to write outside project root")
    return p


@tool
def write_file(path: str, content: str) -> str:
    """Writes content to a file at the specified path within the project root."""
    p = safe_path_for_project(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    return f"WROTE:{p}"


@tool
def read_file(path: str) -> str:
    """Reads content from a file at the specified path within the project root."""
    p = safe_path_for_project(path)
    if not p.exists():
        return ""
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


@tool
def get_current_directory() -> str:
    """Returns the current working directory."""
    return str(PROJECT_ROOT)


@tool
def list_files(directory: str = ".") -> str:
    """Lists all files in the specified directory within the project root."""
    p = safe_path_for_project(directory)
    if not p.is_dir():
        return f"ERROR: {p} is not a directory"
    files = [str(f.relative_to(PROJECT_ROOT)) for f in p.glob("**/*") if f.is_file()]
    return "\n".join(files) if files else "No files found."


@tool
def run_cmd(cmd: str, cwd: str = None, timeout: int = 30) -> Tuple[int, str, str]:
    """Runs a shell command in the specified directory and returns the result."""
    cwd_dir = safe_path_for_project(cwd) if cwd else PROJECT_ROOT
    res = subprocess.run(cmd, shell=True, cwd=str(cwd_dir), capture_output=True, text=True, timeout=timeout)
    return res.returncode, res.stdout, res.stderr


@tool
def run_tests() -> tuple[int, str, str]:
    """Runs tests for the project based on detected project type.
    Returns (returncode, stdout, stderr).
    """
    # Check for common project files
    if (PROJECT_ROOT / "pyproject.toml").exists() or (PROJECT_ROOT / "setup.py").exists() or (PROJECT_ROOT / "requirements.txt").exists():
        # Python project
        # Try pytest first, fallback to unittest
        if (PROJECT_ROOT / "pytest.ini").exists() or (PROJECT_ROOT / "pyproject.toml").exists():
            cmd = "pytest"
        else:
            cmd = "python -m unittest discover -v"
        return run_cmd.run({"cmd": cmd, "cwd": str(PROJECT_ROOT), "timeout": 60})
    elif (PROJECT_ROOT / "package.json").exists():
        # Node.js project
        cmd = "npm test"
        return run_cmd.run({"cmd": cmd, "cwd": str(PROJECT_ROOT), "timeout": 60})
    elif (PROJECT_ROOT / "Cargo.toml").exists():
        # Rust project
        cmd = "cargo test"
        return run_cmd.run({"cmd": cmd, "cwd": str(PROJECT_ROOT), "timeout": 60})
    else:
        # Fallback: try to detect by file extensions
        py_files = list(PROJECT_ROOT.glob("**/*.py"))
        js_files = list(PROJECT_ROOT.glob("**/*.js")) + list(PROJECT_ROOT.glob("**/*.ts"))
        if py_files:
            # Try pytest
            cmd = "pytest"
            rc, out, err = run_cmd.run({"cmd": cmd, "cwd": str(PROJECT_ROOT), "timeout": 60})
            if rc == 0 or "no tests ran" not in out.lower():
                return rc, out, err
            # Fallback to unittest
            cmd = "python -m unittest discover -v"
            return run_cmd.run({"cmd": cmd, "cwd": str(PROJECT_ROOT), "timeout": 60})
        elif js_files:
            cmd = "npm test"
            return run_cmd.run({"cmd": cmd, "cwd": str(PROJECT_ROOT), "timeout": 60})
        else:
            return (1, "", "No test framework detected and no source files found.")


def init_project_root():
    PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
    return str(PROJECT_ROOT)