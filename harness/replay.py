#!/usr/bin/env python3
"""Replay allowlisted python -c and git commands from evidence.md.

Local subprocess only. No network. argv0 allowlist is not sufficient:
python -c payloads go through an AST allowlist, and denied commands are
never passed to subprocess.run. Git is pointed at a temporary git
directory that does not load the checkout's config.
"""

from __future__ import annotations

import ast
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

from score import CMD_FIRST, RED_IN_FENCE, is_command_fence

REPO_ROOT = Path(__file__).resolve().parent.parent

PROCESS_EXIT = re.compile(r"(?i)process exit(?:s| code)?:?\s*(\d+)")
FENCE_SPAN = re.compile(r"^```([^\n]*)\n(.*?)```", re.M | re.S)

GIT_SUB = frozenset(
    {"status", "diff", "log", "show", "check-ignore", "ls-files", "rev-parse"}
)
GIT_REJECT_SUB = frozenset({"push", "commit", "reset"})
# Path-changing / config / pager-hook globals. Glued `--git-dir=/tmp` forms
# must not be skipped just because they start with "-".
GIT_BANNED_FLAGS = frozenset(
    {
        "--git-dir",
        "--work-tree",
        "--exec-path",
        "--config-env",
        "--namespace",
        "--bare",
        "--upload-pack",
        "--receive-pack",
        "--output",
        "--ext-diff",
        "--hard",
        "-C",
        "-c",
    }
)
# Fail-closed: unknown flags after an allowed subcommand are denied.
GIT_FLAGS_BY_SUB: dict[str, frozenset[str]] = {
    "status": frozenset(
        {"--short", "-s", "--ignored", "--porcelain", "-v", "--verbose"}
    ),
    "diff": frozenset(
        {
            "--cached",
            "--staged",
            "-p",
            "--patch",
            "--stat",
            "--name-only",
            "--name-status",
            "--no-color",
            "--no-ext-diff",
        }
    ),
    "log": frozenset(
        {"--oneline", "--stat", "-p", "--patch", "--no-color", "--name-only"}
    ),
    "show": frozenset(
        {"--stat", "-p", "--patch", "--no-color", "--name-only", "--oneline"}
    ),
    "check-ignore": frozenset({"-v", "--verbose", "-n", "--non-matching"}),
    "ls-files": frozenset(
        {
            "-o",
            "--others",
            "--cached",
            "-i",
            "--ignored",
            "-d",
            "--deleted",
            "-m",
            "--modified",
            "-z",
            "--exclude-standard",
            "-v",
            "--verbose",
        }
    ),
    "rev-parse": frozenset(
        {
            "--is-inside-work-tree",
            "--show-toplevel",
            "--abbrev-ref",
            "--verify",
            "--short",
        }
    ),
}
PYTHON_BINS = frozenset({"python", "python3"})
ALLOWED_ARGV0 = PYTHON_BINS | {"git"}

STMT_EXPR_ALLOWED = (
    ast.Module,
    ast.Expr,
    ast.Assert,
    ast.Assign,
    ast.For,
    ast.Try,
    ast.ExceptHandler,
    ast.Compare,
    ast.BoolOp,
    ast.BinOp,
    ast.UnaryOp,
    ast.Call,
    ast.Name,
    ast.Constant,
    ast.List,
    ast.Tuple,
    ast.keyword,
    ast.Pass,
    ast.Raise,
    ast.ImportFrom,
)

ALLOWED_CALLS = frozenset(
    {
        "print",
        "float",
        "int",
        "str",
        "list",
        "bool",
        "len",
        "range",
        "ValueError",
        "SystemExit",
    }
)

BANNED_NAMES = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "shutil",
        "pathlib",
        "socket",
        "ctypes",
        "pickle",
        "importlib",
        "runpy",
        "pty",
        "multiprocessing",
        "builtins",
        "__import__",
        "eval",
        "exec",
        "compile",
        "open",
        "getattr",
        "setattr",
        "globals",
        "locals",
        "vars",
        "breakpoint",
        "system",
        "popen",
        "popen2",
    }
)

KEEP_ENV = ("HOME", "LANG", "LC_ALL", "LC_CTYPE", "TERM")
# Fixed stub. The evidence payload is passed in the environment, never interpolated.
REPLAY_STUB = (
    "import os, sys\n"
    "root = os.environ.get('DAGZ_REPLAY_ROOT', '')\n"
    "if root:\n"
    "    sys.path.insert(0, root)\n"
    "src = os.environ['DAGZ_REPLAY_C']\n"
    "exec(compile(src, '<replay>', 'exec'), {'__name__': '__main__'})\n"
)
# Command-line config overrides anything still visible for this one command.
# The temporary git dir below is what drops repo filter and gpg programs.
GIT_CONFIG_OVERRIDES = (
    "core.fsmonitor=",
    "core.hooksPath=/dev/null",
    "diff.external=",
    "core.pager=cat",
    "core.sshCommand=false",
    "maintenance.auto=false",
    "log.showSignature=false",
    "diff.ignoreSubmodules=all",
)
GIT_SKIP_SUBMODULES = ("status", "diff")
GIT_NO_EXTERNAL = ("diff", "show", "log")
PROXY_ENV = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
    "ALL_PROXY",
    "all_proxy",
    "FTP_PROXY",
    "ftp_proxy",
)

TIMEOUT_SEC = 15


class ReplayDenied(Exception):
    """Command is not executable under the PR4 sandbox. Do not spawn."""


class CommandPair(NamedTuple):
    command_body: str
    output_body: str | None
    claimed_exit: int | None
    historical_red: bool


def ast_always_ok(n: ast.AST) -> bool:
    return isinstance(
        n, (ast.alias, ast.expr_context, ast.cmpop, ast.operator, ast.unaryop, ast.boolop)
    )


def _check_importfrom(n: ast.ImportFrom) -> None:
    if n.level != 0 or not n.module:
        raise ReplayDenied("importfrom")
    if n.module != "harness_tmp" and not n.module.startswith("harness_tmp."):
        raise ReplayDenied("importfrom")
    for alias in n.names:
        if alias.name == "*":
            raise ReplayDenied("star_import")


def _check_call(n: ast.Call, imported: set[str]) -> None:
    if not isinstance(n.func, ast.Name):
        raise ReplayDenied("call")
    name = n.func.id
    if name not in ALLOWED_CALLS and name not in imported:
        raise ReplayDenied(f"call:{name}")


def _int_const(node: ast.AST) -> int | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value
    return None


def _check_size(node: ast.BinOp) -> None:
    """Reject constant allocations the 15s timeout would not stop."""
    if isinstance(node.op, ast.Pow):
        base, exp = _int_const(node.left), _int_const(node.right)
        if exp is not None and (exp < 0 or exp > 6):
            raise ReplayDenied("size")
        if base is not None and exp is not None and abs(base) ** exp > 1_000_000:
            raise ReplayDenied("size")
        return
    left, right = _int_const(node.left), _int_const(node.right)
    if isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
        if right is not None and right > 10_000:
            raise ReplayDenied("size")
    if isinstance(node.right, ast.Constant) and isinstance(node.right.value, str):
        if left is not None and left > 10_000:
            raise ReplayDenied("size")
    if (left is not None and abs(left) > 100_000) or (
        right is not None and abs(right) > 100_000
    ):
        raise ReplayDenied("size")


def replay_allowed_c(src: str) -> None:
    """Raise ReplayDenied if a python -c payload is not allowlisted."""
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        raise ReplayDenied("syntax") from exc
    imported: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            _check_importfrom(n)
            for alias in n.names:
                imported.add(alias.asname or alias.name)
    for n in ast.walk(tree):
        if ast_always_ok(n):
            continue
        if isinstance(n, ast.Attribute):
            raise ReplayDenied("attribute")
        if not isinstance(n, STMT_EXPR_ALLOWED):
            raise ReplayDenied(type(n).__name__)
        if isinstance(n, ast.Call):
            _check_call(n, imported)
        if isinstance(n, ast.Name) and n.id in BANNED_NAMES:
            raise ReplayDenied(f"banned_name:{n.id}")
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Pow, ast.Mult)):
            _check_size(n)


def command_text_from_fence(body: str) -> str:
    lines = list(body.splitlines())
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        raise ReplayDenied("empty_command")
    lines[0] = re.sub(r"^\$\s*", "", lines[0].strip())
    return "\n".join(lines)


def parse_command_argv(body: str) -> list[str]:
    text = command_text_from_fence(body)
    try:
        argv = shlex.split(text, posix=True)
    except ValueError as exc:
        raise ReplayDenied("shlex") from exc
    if not argv:
        raise ReplayDenied("empty_command")
    return argv


def _harness_cli_paths(repo_root: Path) -> frozenset[Path]:
    return frozenset(
        {
            (repo_root / "harness" / "score.py").resolve(),
            (repo_root / "harness" / "run.py").resolve(),
        }
    )


def _resolve_script(script: str, repo_root: Path) -> Path:
    raw = Path(script)
    if raw.is_absolute():
        return raw.resolve()
    return (repo_root / raw).resolve()


def classify_python(argv: list[str], repo_root: Path) -> str:
    args = argv[1:]
    c_payloads: list[str] = []
    positionals: list[str] = []
    i = 0
    while i < len(args):
        tok = args[i]
        if positionals:
            # Args after the script belong to the script, not the interpreter.
            positionals.append(tok)
            i += 1
            continue
        if tok == "-c":
            if i + 1 >= len(args):
                raise ReplayDenied("missing_-c")
            c_payloads.append(args[i + 1])
            i += 2
            continue
        if tok == "-m" or tok.startswith("-m"):
            raise ReplayDenied("-m")
        if tok.startswith("-"):
            raise ReplayDenied(f"python_flag:{tok}")
        positionals.append(tok)
        i += 1
    if positionals and c_payloads:
        raise ReplayDenied("python_mixed_args")
    if positionals:
        script = _resolve_script(positionals[0], repo_root)
        if script in _harness_cli_paths(repo_root):
            return "harness_cli"
        raise ReplayDenied("python_file")
    if len(c_payloads) != 1:
        raise ReplayDenied("python_-c")
    replay_allowed_c(c_payloads[0])
    return "python-c"


def _git_flag_key(tok: str) -> str:
    """Flag name with any `=value` stripped (`--git-dir=/tmp` → `--git-dir`)."""
    if tok.startswith("--"):
        return tok.split("=", 1)[0]
    return tok


def classify_git(argv: list[str]) -> str:
    tokens = argv[1:]
    i = 0
    # Do not skip unknown "-" tokens. Any global option is a sandbox hole
    # (`--git-dir=`, `--work-tree=`, `-C`, `-c`, `--config-env=`).
    while i < len(tokens) and tokens[i].startswith("-"):
        raise ReplayDenied(f"git_global:{_git_flag_key(tokens[i])}")
    if i >= len(tokens):
        raise ReplayDenied("git_no_subcommand")
    sub = tokens[i]
    i += 1
    if sub in GIT_REJECT_SUB or sub not in GIT_SUB:
        raise ReplayDenied(f"git {sub}")
    allowed_flags = GIT_FLAGS_BY_SUB[sub]
    while i < len(tokens):
        tok = tokens[i]
        if tok == "--":
            break
        if tok.startswith("-"):
            key = _git_flag_key(tok)
            if key in GIT_BANNED_FLAGS or key not in allowed_flags:
                raise ReplayDenied(f"git_flag:{key}")
        i += 1
    return "git"


def classify_argv(argv: list[str], repo_root: Path | None = None) -> str:
    """Return 'python-c' | 'git' | 'harness_cli'. Raise ReplayDenied otherwise."""
    repo_root = (repo_root or REPO_ROOT).resolve()
    if not argv:
        raise ReplayDenied("empty_command")
    argv0 = Path(argv[0]).name
    if argv0 == "pytest":
        raise ReplayDenied("pytest_not_executed_v1")
    if argv0 not in ALLOWED_ARGV0:
        raise ReplayDenied(f"argv0:{argv0}")
    if argv0 == "git":
        return classify_git(argv)
    return classify_python(argv, repo_root)


def _fence_spans(text: str) -> list[tuple[str, str, int, int]]:
    return [
        (m.group(1), m.group(2), m.start(), m.end()) for m in FENCE_SPAN.finditer(text)
    ]


def _next_command_start(
    fences: list[tuple[str, str, int, int]], start: int, text_len: int
) -> int:
    for k in range(start, len(fences)):
        if is_command_fence(fences[k][1]):
            return fences[k][2]
    return text_len


def extract_pairs(evidence: str) -> list[CommandPair]:
    """Command fence + optional following non-command output fence."""
    fences = _fence_spans(evidence)
    pairs: list[CommandPair] = []
    i = 0
    while i < len(fences):
        _info, body, _start, end = fences[i]
        if not is_command_fence(body):
            i += 1
            continue
        out_body: str | None = None
        out_end = end
        next_i = i + 1
        if next_i < len(fences) and not is_command_fence(fences[next_i][1]):
            out_body = fences[next_i][1]
            out_end = fences[next_i][3]
            consume_to = next_i + 1
        else:
            consume_to = i + 1
        next_cmd = _next_command_start(fences, consume_to, len(evidence))
        if out_body is not None:
            prose = evidence[end : fences[i + 1][2]] + evidence[out_end:next_cmd]
        else:
            prose = evidence[end:next_cmd]
        claimed: int | None = None
        match = PROCESS_EXIT.search(prose)
        if match is not None:
            claimed = int(match.group(1))
        historical = bool(out_body is not None and RED_IN_FENCE.search(out_body))
        pairs.append(
            CommandPair(
                command_body=body,
                output_body=out_body,
                claimed_exit=claimed,
                historical_red=historical,
            )
        )
        i = consume_to
    return pairs


def collapse_ws(s: str) -> str:
    return " ".join(s.split())


def is_under_examples(run_dir: Path, repo_root: Path | None = None) -> bool:
    repo_root = (repo_root or REPO_ROOT).resolve()
    try:
        run_dir.resolve().relative_to((repo_root / "examples").resolve())
    except ValueError:
        return False
    return True


def _path_dirs(repo_root: Path) -> str:
    """PATH with the repo, '.', and the user bin directories removed."""
    home = Path.home().resolve()
    skip = {home / "bin", home / ".local" / "bin"}
    root = repo_root.resolve()
    kept: list[str] = []
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry or entry == ".":
            continue
        try:
            resolved = Path(entry).resolve()
        except OSError:
            continue
        if resolved in skip:
            continue
        try:
            resolved.relative_to(root)
        except ValueError:
            kept.append(str(resolved))
    return os.pathsep.join(kept)


def trusted_python() -> Path:
    """The interpreter already running the harness, not the path in the evidence."""
    path = Path(sys.executable).resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ReplayDenied("python_binary")
    return path


def trusted_git(repo_root: Path) -> Path:
    found = shutil.which("git", path=_path_dirs(repo_root))
    if not found:
        raise ReplayDenied("git_binary")
    path = Path(found).resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ReplayDenied("git_binary")
    try:
        path.relative_to(repo_root.resolve())
    except ValueError:
        return path
    raise ReplayDenied("git_inside_repo")


def replay_env(repo_root: Path) -> dict[str, str]:
    env = {key: os.environ[key] for key in KEEP_ENV if key in os.environ}
    env["NO_PROXY"] = "*"
    env["PYTHONNOUSERSITE"] = "1"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    env["GIT_PAGER"] = "cat"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["PATH"] = _path_dirs(repo_root)
    for key in PROXY_ENV:
        env.pop(key, None)
    return env


def _c_payload(argv: list[str]) -> str:
    args = argv[1:]
    for i, tok in enumerate(args):
        if tok == "-c" and i + 1 < len(args):
            return args[i + 1]
    raise ReplayDenied("missing_-c")


def python_spawn(argv: list[str], repo_root: Path) -> tuple[list[str], dict[str, str]]:
    env = replay_env(repo_root)
    env["DAGZ_REPLAY_ROOT"] = str(repo_root.resolve())
    env["DAGZ_REPLAY_C"] = _c_payload(argv)
    spawn = [str(trusted_python()), "-I", "-S", "-c", REPLAY_STUB]
    return spawn, env


def _read_regular(path: Path) -> bytes | None:
    """Read a non-symlink file. None if it is missing, a symlink, or unreadable."""
    if path.is_symlink() or not path.is_file():
        return None
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return None
    try:
        chunks: list[bytes] = []
        while True:
            block = os.read(fd, 1 << 20)
            if not block:
                return b"".join(chunks)
            chunks.append(block)
    except OSError:
        return None
    finally:
        os.close(fd)


def _write_regular(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o644)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


def _copy_regular_tree(src: Path, dst: Path) -> None:
    if src.is_symlink() or not src.is_dir():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for entry in os.scandir(src):
        target = dst / entry.name
        if entry.is_symlink():
            continue
        if entry.is_file(follow_symlinks=False):
            data = _read_regular(Path(entry.path))
            if data is not None:
                _write_regular(target, data)
        elif entry.is_dir(follow_symlinks=False):
            _copy_regular_tree(Path(entry.path), target)


def _gitdir_pointer(entry: Path) -> Path:
    try:
        text = entry.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ReplayDenied("git_dir") from exc
    raw = ""
    for line in text.splitlines():
        if line.startswith("gitdir:"):
            raw = line.split(":", 1)[1].strip()
            break
    if not raw:
        raise ReplayDenied("git_dir")
    path = Path(raw)
    if not path.is_absolute():
        path = entry.parent / path
    path = path.resolve()
    if path.is_symlink() or not path.is_dir():
        raise ReplayDenied("git_dir")
    return path


def _common_git_dir(git_dir: Path) -> Path:
    marker = git_dir / "commondir"
    if not marker.exists():
        return git_dir
    if marker.is_symlink() or not marker.is_file():
        raise ReplayDenied("git_dir")
    raw = marker.read_text(encoding="utf-8", errors="replace").strip()
    if not raw:
        raise ReplayDenied("git_dir")
    path = Path(raw)
    if not path.is_absolute():
        path = git_dir / path
    path = path.resolve()
    if not path.is_dir():
        raise ReplayDenied("git_dir")
    return path


class ReplayGitDir:
    """Temporary git dir sharing objects, with the checkout config left behind.

    Clean filters, signature programs, hooks, and includes live in the
    checkout's config. Replaying against that directory would run them.
    """

    def __init__(self, repo_root: Path) -> None:
        self.root = repo_root
        self._tmp: tempfile.TemporaryDirectory[str] | None = None
        self.git_dir: Path | None = None

    def env_updates(self) -> dict[str, str]:
        if self.git_dir is None:
            return {}
        return {
            "GIT_DIR": str(self.git_dir),
            "GIT_WORK_TREE": str(self.root),
        }

    def close(self) -> None:
        if self._tmp is not None:
            self._tmp.cleanup()
            self._tmp = None
            self.git_dir = None

    @classmethod
    def open(cls, repo_root: Path) -> "ReplayGitDir":
        obj = cls(repo_root.resolve())
        try:
            try:
                obj._populate()
            except OSError as exc:
                raise ReplayDenied("git_dir") from exc
        finally:
            # _populate sets git_dir only after the temp dir is ready.
            if obj.git_dir is None:
                obj.close()
        return obj

    def _locate(self) -> tuple[Path, Path] | None:
        entry = self.root / ".git"
        if entry.is_symlink():
            raise ReplayDenied("git_dir")
        if not entry.exists():
            return None
        if entry.is_dir():
            git_dir = entry.resolve()
        elif entry.is_file():
            git_dir = _gitdir_pointer(entry)
        else:
            raise ReplayDenied("git_dir")
        return git_dir, _common_git_dir(git_dir)

    def _populate(self) -> None:
        located = self._locate()
        if located is None:
            return
        git_dir, common = located
        self._tmp = tempfile.TemporaryDirectory(prefix="dagz-replay-git-")
        dest = Path(self._tmp.name) / "git"
        objects = dest / "objects"
        (objects / "info").mkdir(parents=True)
        (dest / "refs").mkdir()
        alternate = str((common / "objects").resolve())
        if "\n" in alternate:
            raise ReplayDenied("git_dir")
        _write_regular(objects / "info" / "alternates", (alternate + "\n").encode())
        head = _read_regular(git_dir / "HEAD")
        if head is None:
            raise ReplayDenied("git_dir")
        _write_regular(dest / "HEAD", head)
        index = _read_regular(git_dir / "index")
        if index is not None:
            _write_regular(dest / "index", index)
        sources = (common,) if common == git_dir else (common, git_dir)
        for source in sources:
            for name in ("packed-refs", "shallow"):
                payload = _read_regular(source / name)
                if payload is not None:
                    _write_regular(dest / name, payload)
            exclude = _read_regular(source / "info" / "exclude")
            if exclude is not None:
                _write_regular(dest / "info" / "exclude", exclude)
            _copy_regular_tree(source / "refs", dest / "refs")
        _write_regular(
            dest / "config",
            b"[core]\n"
            b"\trepositoryformatversion = 0\n"
            b"\tfilemode = true\n"
            b"\tbare = false\n"
            b"\tlogallrefupdates = false\n"
            b"[log]\n"
            b"\tshowSignature = false\n",
        )
        self.git_dir = dest


def git_spawn(
    argv: list[str], repo_root: Path, git_dir: ReplayGitDir
) -> tuple[list[str], dict[str, str]]:
    tokens = argv[1:]
    if not tokens:
        raise ReplayDenied("git_no_subcommand")
    sub, rest = tokens[0], tokens[1:]
    config: list[str] = []
    for item in GIT_CONFIG_OVERRIDES:
        config.extend(["-c", item])
    extra: list[str] = []
    # status and diff otherwise hash a submodule with that repo's config.
    if sub in GIT_SKIP_SUBMODULES:
        extra.append("--ignore-submodules=all")
    if sub in GIT_NO_EXTERNAL:
        extra.extend(["--no-ext-diff", "--no-textconv"])
    spawn = [str(trusted_git(repo_root)), *config, sub, *extra, *rest]
    env = replay_env(repo_root)
    env.update(git_dir.env_updates())
    return spawn, env


def _run(
    argv: list[str], repo_root: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(repo_root),
        shell=False,
        timeout=TIMEOUT_SEC,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def _command_preview(body: str) -> str:
    try:
        return command_text_from_fence(body)
    except ReplayDenied:
        return body.strip()


def _record(
    pair: CommandPair,
    *,
    argv: list[str] | None = None,
    action: str,
    reason: str | None = None,
    exit_code: int | None = None,
    expected_exit: int | None = None,
    match: bool | None = None,
) -> dict:
    return {
        "command": _command_preview(pair.command_body),
        "argv": argv,
        "action": action,
        "reason": reason,
        "exit": exit_code,
        "expected_exit": expected_exit,
        "match": match,
        "historical_red": pair.historical_red,
    }


def replay_evidence(evidence: str, *, repo_root: Path | None = None) -> dict:
    """Replay command/output pairs. Denied commands never call subprocess.run."""
    repo_root = (repo_root or REPO_ROOT).resolve()
    pairs_out: list[dict] = []
    mismatch = False
    unreplayable = False
    for pair in extract_pairs(evidence):
        try:
            argv = parse_command_argv(pair.command_body)
        except ReplayDenied as exc:
            unreplayable = True
            pairs_out.append(
                _record(pair, action="denied", reason=str(exc) or "unreplayable_command")
            )
            continue
        try:
            kind = classify_argv(argv, repo_root)
        except ReplayDenied as exc:
            unreplayable = True
            pairs_out.append(
                _record(
                    pair,
                    argv=argv,
                    action="denied",
                    reason=str(exc) or "unreplayable_command",
                )
            )
            continue
        if kind == "harness_cli":
            pairs_out.append(_record(pair, argv=argv, action="harness_cli"))
            continue
        if pair.historical_red:
            pairs_out.append(_record(pair, argv=argv, action="historical_red"))
            continue
        expected = 0 if pair.claimed_exit is None else pair.claimed_exit
        git_dir = None
        try:
            try:
                if kind == "python-c":
                    spawn, env = python_spawn(argv, repo_root)
                else:
                    git_dir = ReplayGitDir.open(repo_root)
                    spawn, env = git_spawn(argv, repo_root, git_dir)
            except ReplayDenied as exc:
                unreplayable = True
                pairs_out.append(
                    _record(
                        pair,
                        argv=argv,
                        action="denied",
                        reason=str(exc) or "unreplayable_command",
                    )
                )
                continue
            try:
                completed = _run(spawn, repo_root, env)
            except subprocess.TimeoutExpired:
                mismatch = True
                pairs_out.append(
                    _record(
                        pair,
                        argv=spawn,
                        action="mismatch",
                        reason="timeout",
                        expected_exit=expected,
                        match=False,
                    )
                )
                continue
            combined = (completed.stdout or "") + (completed.stderr or "")
            out_ok = True
            if pair.output_body is not None and pair.output_body.strip():
                out_ok = collapse_ws(pair.output_body) in collapse_ws(combined)
            exit_ok = completed.returncode == expected
            if not out_ok or not exit_ok:
                mismatch = True
                reason = "exit" if not exit_ok else "stdout"
                pairs_out.append(
                    _record(
                        pair,
                        argv=spawn,
                        action="mismatch",
                        reason=reason,
                        exit_code=completed.returncode,
                        expected_exit=expected,
                        match=False,
                    )
                )
                continue
            pairs_out.append(
                _record(
                    pair,
                    argv=spawn,
                    action="executed",
                    exit_code=completed.returncode,
                    expected_exit=expected,
                    match=True,
                )
            )
        finally:
            if git_dir is not None:
                git_dir.close()
    return {
        "skipped": None,
        "pairs": pairs_out,
        "mismatch": mismatch,
        "unreplayable": unreplayable,
    }
