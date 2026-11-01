#!/usr/bin/env python3
"""Pre-flight environment check for the Electronics-extension pipeline (gex-llm-patterns issue #261).

Run it before any other script in this folder and again before every paid step.  It reports

* the interpreter, ``PYTHONNOUSERSITE`` and the user-site status of ``sys.path``;
* the packages the pipeline imports (version, where each was loaded from, drift from the audited baseline), a parquet
  round trip, and whether ``json_repair`` is importable (it changes the fallback JSON parser);
* the git commits of gex-llm-patterns and gex-database-infrastructure;
* the database: server version, date coverage of ``gex.options_daily_summary`` for SPY/QQQ/IWM, whether the source
  table of every series in ``common.SERIES`` is readable, and whether the four ``backups.gex_llm_regime_*`` tables
  and the summary view exist yet;
* OpenAI: whether a key is configured (never its value) and whether ``common.MODEL`` is served
  (``models.retrieve``, a free call);
* the surviving Phase 4A artefacts: existence, size and sha256, parse counts, and whether today's prompt builder
  reproduces every published prompt byte for byte;
* the ``src/`` pieces the pipeline reuses (prompt builder, classifier thresholds, JSON fallback parser) and the output
  directories (writable, free space).

The database session is read-only and no billable API call is made.  With ``--write`` the same facts are stored as
``results/env_check_<UTC stamp>.json`` so that every result can be traced to the environment that produced it.

Blockers (exit status 1): a required package or the parquet round trip fails; gex-llm-patterns is not a readable git
checkout; the database is unreachable, a required source table is unreadable or a symbol has no rows; there is no
OpenAI key or ``models.retrieve`` fails; a Phase 4A file is missing or differs from its audited digest, or the prompt
builder no longer reproduces the published prompts; the ``src/`` bridge does not import or the classifier thresholds
differ from the Paper 2 protocol; an output directory is not writable; ``--write`` cannot write.  With
``--require-tables`` missing ``backups.gex_llm_regime_*`` objects are blockers too.  Everything else (version drift,
user-site shadowing, ``json_repair`` importable, data ending before the window cap, ...) is a warning.

Usage, from the repository root::

    source ~/miniconda3/etc/profile.d/conda.sh && conda activate AutoGex
    export PYTHONNOUSERSITE=1 PYTHONPATH=$(pwd)
    python scripts/validation/electronics/00_env_check.py --write
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import io
import json
import logging
import math
import os
import platform
import re
import shutil
import site
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Sequence, Tuple

import common

if TYPE_CHECKING:  # psycopg2 is imported lazily so that a missing driver is reported instead of being fatal
    from psycopg2.extensions import cursor as Cursor

logger = logging.getLogger("electronics.env_check")

REPORT_SCHEMA = "gex_llm_env_check/1"
ISO_SECONDS = "%Y-%m-%dT%H:%M:%SZ"
LABEL_WIDTH = 28

SYMBOLS = ("SPY", "QQQ", "IWM")
INFRA_REPO_NAME = "gex-database-infrastructure"  # expected next to this repository
STATEMENT_TIMEOUT = "600s"  # project rule for every database session
CONNECT_TIMEOUT_S = 10
OPENAI_TIMEOUT_S = 30.0
GIT_TIMEOUT_S = 30
MIN_FREE_GIB = 1.0
OPTIONAL_ARM_PRIORITY = 4  # arms from this priority on (bridge_old) are diagnostic, so their sources are optional

# --------------------------------------------------------------------------- audited baseline
# Releases the loaders and the src/ bridge were audited against on 2026-10-28.  A different release is a warning:
# the audit has to be repeated, which does not mean the pipeline cannot run.
AUDITED_PYTHON = "3.12"


@dataclass(frozen=True)
class Package:
    name: str  # key in the report
    module: str  # import name
    dist: str  # distribution name, used when the module has no __version__
    baseline: str  # audited release series: "2.4" covers 2.4.0 and 2.4.3


PACKAGES: Tuple[Package, ...] = (
    Package("openai", "openai", "openai", "2.14"),
    Package("psycopg2", "psycopg2", "psycopg2-binary", "2.9"),
    Package("pandas", "pandas", "pandas", "2.3"),
    Package("pyarrow", "pyarrow", "pyarrow", "23"),
    Package("numpy", "numpy", "numpy", "2.4"),
    Package("scipy", "scipy", "scipy", "1.16"),
    Package("statsmodels", "statsmodels", "statsmodels", "0.14"),
    Package("matplotlib", "matplotlib", "matplotlib", "3.10"),
    Package("pyyaml", "yaml", "PyYAML", "6.0"),
)

# sha256 of the artefacts as audited on 2026-10-28.  The Phase 4A batch files and the research cache are git-ignored
# and the OpenAI-side copies of the January batch have expired, so the digest is the only evidence that they are
# unchanged.  Replace a digest only after confirming that the change to the file was intended.
KNOWN_SHA256: Dict[str, str] = {
    "phase4a_input": "95f83fed9768bbe0553d4434f934ce6a5bd892993812a925b185295f4391eef6",
    "phase4a_output": "dffd8e78e7e639eb4e4c110316214f0d35d54c390501ebcead9d0947336871bd",
    "research_cache_db": "7bdff7584ce679f7737d8c178331b0bd131112d9c5565199e1614b45a6e3caef",
}
PHASE4A_WINDOWS = 1476
PHASE4A_WINDOW_ENDS = (date(2020, 2, 13), date(2025, 12, 31))

EXPECTED_MODEL_CREATED = date(2026, 9, 14)  # created date of the gpt-6-luna model object at design time

# Paper 2 criteria: >= 70% same-sign days, mean |GEX| >= $5B, <= 5 sign flips, $3B low-conviction floor.
PROTOCOL_CLASSIFIER: Dict[str, float] = {
    "persistence_threshold": 0.70,
    "magnitude_threshold": 5e9,
    "max_sign_flips": 5,
    "low_conviction_mag": 3e9,
}
SRC_BRIDGE: Tuple[Tuple[str, str, str], ...] = (  # (label, module, attribute)
    ("prompt builder", "src.llm.mechanics_prompt_builder", "MechanicsPromptBuilder"),
    ("regime classifier", "src.validation.regime_classifier", "RegimeClassifier"),
    ("json fallback parser", "src.utils.json_parser", "extract_json"),
)

_API_KEY_PATTERN = re.compile(r"sk-[A-Za-z0-9_\-*]{3,}")
_RELKIND = {"r": "table", "p": "table", "v": "view", "m": "materialized view"}


# --------------------------------------------------------------------------- report plumbing
@dataclass
class Context:
    """Command-line options plus the blockers and warnings collected by the checks."""

    args: argparse.Namespace
    blockers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def blocker(self, message: str) -> None:
        logger.error("blocker: %s", message)
        self.blockers.append(message)

    def warn(self, message: str) -> None:
        logger.warning("%s", message)
        self.warnings.append(message)


@dataclass
class Section:
    """One block of the report: machine-readable ``facts`` (JSON) and the matching text ``lines``."""

    key: str
    title: str
    facts: Dict[str, Any] = field(default_factory=dict)
    lines: List[str] = field(default_factory=list)

    def add(self, label: str, value: Any = "") -> None:
        """Append a ``label  value`` line (an empty label continues the previous line)."""
        self.lines.append(f"{label:<{LABEL_WIDTH}}{value}".rstrip())


# --------------------------------------------------------------------------- helpers
def _first_line(exc: BaseException) -> str:
    """``ExcType: first line of the message`` (driver errors span several lines)."""
    text = str(exc).strip()
    return f"{type(exc).__name__}: {text.splitlines()[0]}" if text else type(exc).__name__


def _redact(text: str) -> str:
    """Mask anything that looks like an API key, including the configured one, before text is logged or stored."""
    try:
        secret = common.load_openai_key()
    except Exception:  # no key configured: only the pattern can match
        secret = ""
    if secret:
        text = text.replace(secret, "[redacted]")
    return _API_KEY_PATTERN.sub("sk-[redacted]", text)


def _key_present() -> bool:
    """True when ``common.load_openai_key`` finds a key; the value is never kept."""
    try:
        return bool(common.load_openai_key())
    except Exception:  # RuntimeError when absent, ValueError when config.json is malformed
        return False


def _rel(path: Path) -> str:
    """``path`` relative to the repository root when it lies inside it."""
    try:
        return str(path.relative_to(common.REPO_ROOT))
    except ValueError:
        return str(path)


def _on_baseline(version: str, baseline: str) -> bool:
    """True when ``version`` belongs to the audited release series (``2.4.3`` is on baseline ``2.4``)."""
    return version == baseline or version.startswith(baseline + ".")


def _import(name: str) -> Tuple[Optional[ModuleType], Optional[str]]:
    """Import ``name``; return (module, None) or (None, error text)."""
    try:
        return importlib.import_module(name), None
    except Exception as exc:  # broken binary wheels raise more than ImportError
        return None, _first_line(exc)


def _version(module: ModuleType, dist: str) -> str:
    """``module.__version__`` (first token: psycopg2 appends build flags), else the installed distribution's version."""
    declared = getattr(module, "__version__", None)
    if declared:
        return str(declared).split()[0]
    try:
        return importlib.metadata.version(dist)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _origin(module: ModuleType) -> Tuple[Optional[Path], str]:
    """(file or package directory, where it lies): ``env`` (under sys.prefix), ``user-site`` or ``other``."""
    file = getattr(module, "__file__", None) or next(iter(getattr(module, "__path__", [])), None)
    if file is None:
        return None, "unknown"
    path = Path(file).resolve()
    if path.is_relative_to(Path(site.getusersitepackages()).resolve()):
        return path, "user-site"
    return path, "env" if path.is_relative_to(Path(sys.prefix).resolve()) else "other"


def _git(repo: Path, *args: str) -> str:
    """Run a read-only git command in ``repo`` (no optional locks, so a concurrent git process is never blocked)."""
    done = subprocess.run(
        ["git", "-C", str(repo), "--no-optional-locks", *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=GIT_TIMEOUT_S,
    )
    return done.stdout.strip()


def git_info(repo: Path) -> Dict[str, Any]:
    """HEAD commit, branch and working-tree summary of ``repo``; ``sha`` is None (with ``error``) when unreadable."""
    try:
        sha = _git(repo, "rev-parse", "HEAD")
        branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
        status = _git(repo, "status", "--porcelain").splitlines()
    except subprocess.CalledProcessError as exc:
        return {"path": str(repo), "sha": None, "error": (exc.stderr or "").strip() or str(exc)}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"path": str(repo), "sha": None, "error": _first_line(exc)}
    untracked = sum(line.startswith("??") for line in status)
    return {
        "path": str(repo),
        "sha": sha,
        "branch": branch,
        "modified": len(status) - untracked,
        "untracked": untracked,
    }


def _file_facts(path: Path, expected_sha256: str) -> Dict[str, Any]:
    """Existence, size, mtime and sha256 of ``path`` next to its audited digest."""
    if not path.is_file():
        return {"path": str(path), "exists": False, "expected_sha256": expected_sha256}
    stat = path.stat()
    digest = common.sha256_file(path)
    return {
        "path": str(path),
        "exists": True,
        "size_bytes": stat.st_size,
        "mtime_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime(ISO_SECONDS),
        "sha256": digest,
        "expected_sha256": expected_sha256,
        "sha256_matches": digest == expected_sha256,
    }


def _parquet_round_trip() -> Optional[str]:
    """Write and read a small frame through pandas/pyarrow in memory; None on success, else the problem."""
    import pandas as pd

    frame = pd.DataFrame({"series_key": ["new_full"], "window_end": ["2026-10-09"], "net_gex": [1.5e9], "n": [30]})
    buffer = io.BytesIO()
    try:
        frame.to_parquet(buffer, engine="pyarrow")
        buffer.seek(0)
        restored = pd.read_parquet(buffer, engine="pyarrow")
    except Exception as exc:  # any failure here means parquet backups cannot be written
        return _first_line(exc)
    return None if restored.equals(frame) else "the frame changed in the round trip"


# --------------------------------------------------------------------------- checks
def check_python(ctx: Context, sec: Section) -> None:
    """Interpreter and conda environment."""
    version = platform.python_version()
    on_baseline = _on_baseline(version, AUDITED_PYTHON)
    sec.facts.update(
        version=version,
        implementation=platform.python_implementation(),
        executable=sys.executable,
        prefix=sys.prefix,
        platform=platform.platform(),
        conda_env=os.environ.get("CONDA_DEFAULT_ENV"),
        pythonpath=os.environ.get("PYTHONPATH"),
        cwd=os.getcwd(),
        repo_root=str(common.REPO_ROOT),
        audited_series=AUDITED_PYTHON,
        on_baseline=on_baseline,
    )
    verdict = "ok" if on_baseline else "DIFFERS"
    sec.add("version", f"{version} ({sec.facts['implementation']}); audited series {AUDITED_PYTHON}: {verdict}")
    sec.add("executable", sys.executable)
    sec.add("conda env", sec.facts["conda_env"] or "(none)")
    sec.add("platform", sec.facts["platform"])
    sec.add("PYTHONPATH", sec.facts["pythonpath"] or "(unset)")
    sec.add("working directory", sec.facts["cwd"])
    if not on_baseline:
        ctx.warn(f"python {version} differs from the audited {AUDITED_PYTHON}.x: repeat the compatibility checks")


def check_user_site(ctx: Context, sec: Section) -> None:
    """PYTHONNOUSERSITE and whether the user site is on sys.path (it can shadow the shared env)."""
    user_dir = Path(site.getusersitepackages())
    enabled = bool(site.ENABLE_USER_SITE)
    on_path = str(user_dir) in sys.path
    sec.facts.update(
        PYTHONNOUSERSITE=os.environ.get("PYTHONNOUSERSITE"),
        flags_no_user_site=bool(sys.flags.no_user_site),
        enable_user_site=enabled,
        user_site_dir=str(user_dir),
        user_site_dir_exists=user_dir.is_dir(),
        user_site_on_sys_path=on_path,
    )
    sec.add("PYTHONNOUSERSITE", sec.facts["PYTHONNOUSERSITE"] or "(unset)")
    sec.add("sys.flags.no_user_site", sys.flags.no_user_site)
    sec.add("site.ENABLE_USER_SITE", enabled)
    where = f"{'exists' if user_dir.is_dir() else 'absent'}, {'on' if on_path else 'not on'} sys.path"
    sec.add("user-site directory", f"{user_dir} ({where})")
    if enabled:
        ctx.warn(
            f"user site is active (PYTHONNOUSERSITE={sec.facts['PYTHONNOUSERSITE']!r}): packages under {user_dir} "
            "can shadow the env; export PYTHONNOUSERSITE=1"
        )


def check_packages(ctx: Context, sec: Section) -> None:
    """Versions and load locations of the imported packages, a parquet round trip, and json_repair."""
    for pkg in PACKAGES:
        module, error = _import(pkg.module)
        if module is None:
            sec.facts[pkg.name] = {"module": pkg.module, "importable": False, "error": error}
            sec.add(pkg.name, f"IMPORT FAILED ({error})")
            ctx.blocker(f"package {pkg.name}: import failed ({error}); the AutoGex env must provide {pkg.dist}")
            continue
        version = _version(module, pkg.dist)
        path, origin = _origin(module)
        on_baseline = _on_baseline(version, pkg.baseline)
        sec.facts[pkg.name] = {
            "module": pkg.module,
            "importable": True,
            "version": version,
            "path": str(path) if path else None,
            "origin": origin,
            "audited_series": pkg.baseline,
            "on_baseline": on_baseline,
        }
        sec.add(pkg.name, f"{version:<12}[{origin}]{'' if origin == 'env' else f'  {path}'}")
        if origin in ("user-site", "other"):
            ctx.warn(
                f"package {pkg.name} {version} was loaded from the {origin} ({path}), not from {sys.prefix}; "
                "export PYTHONNOUSERSITE=1"
            )
        if not on_baseline:
            ctx.warn(f"package {pkg.name} {version} differs from the audited {pkg.baseline}.x: repeat the checks")

    if sec.facts["pandas"]["importable"] and sec.facts["pyarrow"]["importable"]:
        problem = _parquet_round_trip()
        sec.facts["parquet_round_trip"] = {"ok": problem is None, "error": problem}
        sec.add("parquet round trip", "ok (in memory)" if problem is None else f"FAILED ({problem})")
        if problem:
            ctx.blocker(f"parquet round trip through pandas/pyarrow failed ({problem}); backups cannot be written")

    module, _ = _import("json_repair")
    sec.facts["json_repair"] = {"importable": module is not None, "version": module and _version(module, "json-repair")}
    if module is None:
        sec.add("json_repair", "not importable (src.utils.json_parser runs without its repair strategy)")
    else:
        sec.add("json_repair", f"importable, {sec.facts['json_repair']['version']}")
        ctx.warn(
            "json_repair is importable: src.utils.json_parser gains a repair strategy, so parse_status 'fallback' "
            "results differ from runs made without it"
        )


def check_git(ctx: Context, sec: Section) -> None:
    """Commits that produced the results (the pipeline repository is required, the infra repository is not)."""
    repos = (
        ("gex-llm-patterns", common.REPO_ROOT, ctx.blocker),
        (INFRA_REPO_NAME, ctx.args.infra_repo, ctx.warn),
    )
    for name, path, report_problem in repos:
        info = sec.facts[name] = git_info(path)
        if info["sha"] is None:
            sec.add(name, f"UNREADABLE {path}: {info['error']}")
            report_problem(f"git: cannot read {name} at {path}: {info['error']}")
        else:
            sec.add(name, f"{info['sha']}  {info['branch']}  modified={info['modified']} untracked={info['untracked']}")


def _db_server(ctx: Context, sec: Section, cur: Cursor) -> None:
    """Server banner, session mode and the privilege the schema SQL will need."""
    schema = common.T_SERIES.split(".")[0]
    cur.execute(
        "SELECT version(), current_user, current_database(), current_setting('transaction_read_only'), "
        "has_schema_privilege(current_user, %s, 'CREATE')",
        (schema,),
    )
    banner, user, database, read_only, can_create = cur.fetchone()
    sec.facts.update(
        server_version=banner,
        user=user,
        database=database,
        session_read_only=read_only == "on",
        statement_timeout=STATEMENT_TIMEOUT,
        create_privilege_on_result_schema=can_create,
    )
    mode = "read-only" if read_only == "on" else "READ-WRITE"
    sec.add("connection", f"{sec.facts['connection']['host']} / {database} as {user} ({mode} session)")
    sec.add("server", banner.split(",")[0])
    sec.add("statement_timeout", STATEMENT_TIMEOUT)
    sec.add(f"CREATE on schema {schema}", "yes" if can_create else "no")
    if read_only != "on":
        ctx.blocker("database: the session is not read-only; this check must never be able to write")


def _db_coverage(ctx: Context, sec: Section, cur: Cursor) -> None:
    """First/last trading date and day count of the master daily table for SPY, QQQ and IWM."""
    from psycopg2 import sql

    table, cap = common.SERIES["new_full"].source_table, common.WINDOW_END_CAP
    cur.execute(
        sql.SQL(
            "SELECT symbol, MIN(trading_date), MAX(trading_date), COUNT(DISTINCT trading_date) FROM {} "
            "WHERE symbol = ANY(%s) GROUP BY symbol"
        ).format(sql.Identifier(*table.split("."))),
        (list(SYMBOLS),),
    )
    found = {symbol: {"first_date": first, "last_date": last, "n_days": n} for symbol, first, last, n in cur.fetchall()}
    sec.facts["daily_summary"] = {"table": table, "window_end_cap": cap, "symbols": {s: found.get(s) for s in SYMBOLS}}
    sec.add(table)
    for symbol in SYMBOLS:
        row = found.get(symbol)
        if row is None:
            sec.add(f"  {symbol}", "NO ROWS")
            ctx.blocker(f"database: {table} has no rows for {symbol}")
            continue
        verdict = "" if row["last_date"] >= cap else f"  (ends before the window-end cap {cap})"
        sec.add(f"  {symbol}", f"{row['first_date']} .. {row['last_date']}  {row['n_days']:,} days{verdict}")
        if verdict:
            ctx.warn(f"database: {table} for {symbol} ends {row['last_date']}, before the window-end cap {cap}")


def _db_sources(ctx: Context, sec: Section, cur: Cursor) -> None:
    """Existence and SELECT privilege of the table behind every database-backed series in ``common.SERIES``."""
    required = {arm.series_key for arm in common.ARMS.values() if arm.priority < OPTIONAL_ARM_PRIORITY}
    sec.facts["series_sources"] = {}
    sec.add("series sources")
    for key, series in common.SERIES.items():
        if "/" in series.source_table:  # a file (jan2026_phase4a), reported under PHASE 4A
            continue
        cur.execute(
            "SELECT to_regclass(%s) IS NOT NULL, has_table_privilege(current_user, to_regclass(%s), 'SELECT')",
            (series.source_table, series.source_table),
        )
        exists, readable = cur.fetchone()
        mandatory = key in required
        state = "readable" if readable else ("not readable" if exists else "MISSING")
        sec.facts["series_sources"][key] = {
            "table": series.source_table,
            "exists": exists,
            "readable": bool(readable),
            "required": mandatory,
        }
        sec.add(f"  {key}", f"{series.source_table}: {state}{'' if mandatory else ' (optional)'}")
        if not readable:
            problem = ctx.blocker if mandatory else ctx.warn
            problem(f"database: source of series {key} ({series.source_table}) is {state}")


def _db_result_tables(ctx: Context, sec: Section, cur: Cursor) -> None:
    """Which backups.gex_llm_regime_* objects exist (the schema SQL is applied only after maintainer approval)."""
    from psycopg2 import sql

    schema = common.T_SERIES.split(".")[0]
    tables = [t.split(".")[1] for t in (common.T_SERIES, common.T_WINDOWS, common.T_RUNS, common.T_DETECTIONS)]
    view = common.T_RATES_VIEW.split(".")[1]
    cur.execute(
        "SELECT c.relname, c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = %s AND c.relname = ANY(%s)",
        (schema, tables + [view]),
    )
    kinds = dict(cur.fetchall())
    objects: Dict[str, Dict[str, Any]] = {}
    for name in tables + [view]:
        objects[name] = {"exists": name in kinds, "kind": _RELKIND.get(kinds.get(name, ""), None)}
        if name in tables and name in kinds:
            cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(schema, name)))
            objects[name]["n_rows"] = cur.fetchone()[0]
    n_found = sum(obj["exists"] for obj in objects.values())
    state = "absent" if n_found == 0 else ("complete" if n_found == len(objects) else "partial")
    sec.facts["result_tables"] = {"schema": schema, "state": state, "objects": objects}

    note = " (expected until the schema SQL is approved and applied)" if state == "absent" else ""
    sec.add(f"{schema}.gex_llm_regime_*", f"{state}: {n_found} of {len(objects)} objects exist{note}")
    for name, obj in objects.items():
        rows = f", {obj['n_rows']:,} rows" if "n_rows" in obj else ""
        sec.add(
            f"  {name.removeprefix('gex_llm_regime_')}",
            f"{obj['kind'] or 'other'}{rows}" if obj["exists"] else "missing",
        )
    if state != "complete":
        message = f"database: {schema}.gex_llm_regime_* objects are {state} ({n_found} of {len(objects)} exist)"
        if ctx.args.require_tables:
            ctx.blocker(message)
        elif state == "partial":
            ctx.warn(message)


def check_database(ctx: Context, sec: Section) -> None:
    """Connect read-only and report server, data coverage, source-table access and the result-table state."""
    import psycopg2

    params = {k: v for k, v in common.DB_PARAMS.items() if k != "password"}
    sec.facts["connection"] = params
    try:
        conn = psycopg2.connect(**{**common.DB_PARAMS, "connect_timeout": CONNECT_TIMEOUT_S})
    except psycopg2.Error as exc:
        sec.facts["connected"] = False
        sec.add("connection", f"FAILED {params}")
        ctx.blocker(f"database: cannot connect to {params}: {_first_line(exc)}")
        return
    sec.facts["connected"] = True
    try:
        # autocommit: a failed probe must not abort the ones after it; read-only: the server rejects any write
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = %s", (STATEMENT_TIMEOUT,))
            for step in (_db_server, _db_coverage, _db_sources, _db_result_tables):
                what = step.__name__.removeprefix("_db_")
                try:
                    step(ctx, sec, cur)
                except psycopg2.Error as exc:
                    sec.add(what, f"FAILED ({_first_line(exc)})")
                    ctx.blocker(f"database: {what} query failed: {_first_line(exc)}")
    finally:
        conn.close()


def _check_model(ctx: Context, sec: Section) -> None:
    """``models.retrieve(common.MODEL)``: a free metadata call that also records the model object's created time."""
    facts: Dict[str, Any] = {"model": common.MODEL}
    sec.facts["model_check"] = facts
    try:
        client = common.openai_client().with_options(timeout=OPENAI_TIMEOUT_S, max_retries=1)
        model = client.models.retrieve(common.MODEL)
    except Exception as exc:  # authentication, 404, connection and timeout errors all mean "not usable"
        status = getattr(exc, "status_code", None)
        facts.update(
            available=False, error_type=type(exc).__name__, status_code=status, message=_redact(str(exc))[:300]
        )
        sec.add("model", f"{common.MODEL}: NOT AVAILABLE ({facts['error_type']}, status {status})")
        ctx.blocker(
            f"openai: models.retrieve({common.MODEL!r}) failed: {facts['error_type']} (status {status}): "
            f"{facts['message']}"
        )
        return
    created = datetime.fromtimestamp(model.created, tz=timezone.utc)
    facts.update(
        available=True,
        id=model.id,
        created=model.created,
        created_utc=created.strftime(ISO_SECONDS),
        owned_by=model.owned_by,
        base_url=str(client.base_url),
    )
    sec.add("endpoint", facts["base_url"])
    sec.add("model", f"{common.MODEL}: id {model.id}, created {facts['created_utc']}, owned_by {model.owned_by}")
    if model.id != common.MODEL:
        ctx.warn(f"openai: models.retrieve({common.MODEL!r}) returned id {model.id!r}")
    if created.date() != EXPECTED_MODEL_CREATED:
        ctx.warn(
            f"openai: {common.MODEL} was created {facts['created_utc']}, not on {EXPECTED_MODEL_CREATED}; the alias "
            "may point to a newer snapshot, so results are not comparable with the design-time probe"
        )


def check_openai(ctx: Context, sec: Section) -> None:
    """API key presence (never the value) and model availability."""
    present = _key_present()
    sec.facts["api_key_present"] = present
    sec.add("api key", "present (value never printed)" if present else "MISSING")
    if not present:
        ctx.blocker("openai: no API key (config/config.json OPEN_AI_KEY, or env OPEN_AI_KEY / OPENAI_API_KEY)")
    skipped = "--skip-model-check" if ctx.args.skip_model_check else None
    if skipped or not present:
        reason = skipped or "no API key"
        sec.facts["model_check"] = {"model": common.MODEL, "skipped": True, "reason": reason}
        sec.add("model", f"{common.MODEL}: not checked ({reason})")
    else:
        _check_model(ctx, sec)


def _prompt_fidelity(windows: Dict[date, List[float]]) -> Dict[str, Any]:
    """Rebuild every Phase 4A prompt from its parsed values and compare it with the prompt stored in the batch file."""
    checked = identical = 0
    first_mismatch: Optional[date] = None
    with open(common.PHASE4A_INPUT_JSONL) as fh:
        for line in fh:
            record = json.loads(line)
            window_end = date.fromisoformat(record["custom_id"].replace("window-", ""))
            stored = record["body"]["messages"][0]["content"]
            rebuilt = common.build_prompt(common.obfuscate(windows[window_end]))
            checked += 1
            if stored == rebuilt:
                identical += 1
            elif first_mismatch is None:
                first_mismatch = window_end
    return {"checked": checked, "identical": identical, "first_mismatch": first_mismatch}


def _check_phase4a_content(ctx: Context, sec: Section) -> None:
    """Parse the two Phase 4A files with the shared loaders and verify that the prompt text is unchanged."""
    try:
        windows = common.load_phase4a_inputs()
        outputs = common.load_phase4a_outputs()
        fidelity = _prompt_fidelity(windows)
    except Exception as exc:  # any malformed record must be reported, not crash the check
        sec.facts["content_error"] = _first_line(exc)
        sec.add("content", f"UNREADABLE ({_first_line(exc)})")
        ctx.blocker(f"phase4a: the batch files cannot be parsed with the shared loaders: {_first_line(exc)}")
        return
    first_end, last_end = min(windows), max(windows)
    same_windows = set(outputs) == set(windows)
    sec.facts.update(
        n_windows=len(windows),
        first_window_end=first_end,
        last_window_end=last_end,
        n_output_lines=len(outputs),
        outputs_match_inputs=same_windows,
        prompt_fidelity=fidelity,
    )
    sec.add("windows parsed", f"{len(windows):,} ({first_end} .. {last_end}); output lines {len(outputs):,}")
    sec.add("prompt fidelity", f"{fidelity['identical']:,} of {fidelity['checked']:,} prompts rebuilt byte for byte")
    if (len(windows), first_end, last_end) != (PHASE4A_WINDOWS, *PHASE4A_WINDOW_ENDS):
        ctx.warn(
            f"phase4a: parsed {len(windows)} windows {first_end}..{last_end}, expected {PHASE4A_WINDOWS} windows "
            f"{PHASE4A_WINDOW_ENDS[0]}..{PHASE4A_WINDOW_ENDS[1]}"
        )
    if not same_windows:
        ctx.warn("phase4a: the output file does not cover exactly the windows of the input file")
    n_differ = fidelity["checked"] - fidelity["identical"]
    if n_differ:
        ctx.blocker(
            f"phase4a: the prompt builder no longer reproduces the published prompts ({n_differ} of "
            f"{fidelity['checked']} differ, first at window {fidelity['first_mismatch']}); the 'prompt text "
            "unchanged' premise of the design is broken"
        )


def check_phase4a(ctx: Context, sec: Section) -> None:
    """Existence and digests of the surviving Phase 4A artefacts, then their content."""
    artefacts = (
        ("phase4a_input", "input", common.PHASE4A_INPUT_JSONL, ctx.blocker),
        ("phase4a_output", "output", common.PHASE4A_OUTPUT_JSONL, ctx.blocker),
        ("research_cache_db", "research cache", common.RESEARCH_CACHE_DB, ctx.warn),
    )
    sec.facts["batch_id"] = common.PHASE4A_BATCH_ID
    files = sec.facts["files"] = {}
    for key, label, path, report_problem in artefacts:
        facts = files[key] = _file_facts(path, KNOWN_SHA256[key])
        sec.add(label, _rel(path))
        if not facts["exists"]:
            sec.add("", "MISSING")
            report_problem(f"phase4a: {label} file is missing: {_rel(path)}")
            continue
        verdict = "matches the audited digest" if facts["sha256_matches"] else "DIFFERS from the audited digest"
        sec.add("", f"{facts['size_bytes']:,} B  sha256 {facts['sha256']}  ({verdict})")
        if not facts["sha256_matches"]:
            report_problem(
                f"phase4a: {label} file {_rel(path)} has sha256 {facts['sha256']}, the audited digest is "
                f"{facts['expected_sha256']}"
            )
    if files["phase4a_input"]["exists"] and files["phase4a_output"]["exists"]:
        _check_phase4a_content(ctx, sec)


def check_bridge(ctx: Context, sec: Section) -> None:
    """Import the src/ pieces the pipeline reuses and compare the classifier thresholds with the Paper 2 protocol."""
    sec.facts["imports"] = {}
    for label, module_name, attr in SRC_BRIDGE:
        module, error = _import(module_name)
        if module is not None and not hasattr(module, attr):
            error = f"{module_name} has no attribute {attr}"
        sec.facts["imports"][label] = {"module": module_name, "attribute": attr, "ok": error is None, "error": error}
        sec.add(label, f"{module_name}.{attr}: {'ok' if error is None else f'FAILED ({error})'}")
        if error:
            ctx.blocker(f"src bridge: {label} ({module_name}.{attr}) is unusable: {error}")
    try:
        observed = {name: getattr(common.classifier(), name) for name in PROTOCOL_CLASSIFIER}
        version = common.classifier_version()
    except Exception as exc:  # usually the import failure reported above
        sec.facts["classifier"] = {"error": _first_line(exc)}
        sec.add("classifier", f"UNUSABLE ({_first_line(exc)})")
        ctx.blocker(f"src bridge: RegimeClassifier cannot be constructed: {_first_line(exc)}")
        return
    off = {n: (observed[n], want) for n, want in PROTOCOL_CLASSIFIER.items() if not math.isclose(observed[n], want)}
    sec.facts["classifier"] = {"version": version, "thresholds": observed, "matches_protocol": not off}
    sec.add("classifier", version)
    sec.add("", "thresholds match the Paper 2 protocol" if not off else f"thresholds DIFFER from the protocol: {off}")
    if off:
        detail = ", ".join(f"{name} {got} (protocol {want})" for name, (got, want) in off.items())
        ctx.blocker(f"src bridge: classifier thresholds differ from the Paper 2 protocol: {detail}")


def check_disk(ctx: Context, sec: Section) -> None:
    """The directories the pipeline writes to: writable, and enough free space."""
    targets = (
        ("raw backups + parquet", common.BACKUP_ROOT),
        ("results (YAML/JSON)", common.RESULTS_DIR),
        ("figures", common.FIGURE_OUTPUT_DIR),
    )
    sec.facts["locations"] = {}
    for label, path in targets:
        probe = path
        while not probe.exists():  # the scripts create missing directories, so the nearest existing parent decides
            probe = probe.parent
        writable = os.access(probe, os.W_OK | os.X_OK)
        free_gib = shutil.disk_usage(probe).free / 2**30
        sec.facts["locations"][label] = {"path": str(path), "writable": writable, "free_gib": round(free_gib, 1)}
        sec.add(label, f"{_rel(path)}  {'writable' if writable else 'NOT WRITABLE'}, {free_gib:,.0f} GiB free")
        if not writable:
            ctx.blocker(f"disk: {path} is not writable")
        elif free_gib < MIN_FREE_GIB:
            ctx.warn(f"disk: only {free_gib:.2f} GiB free under {path}")


CHECKS: Tuple[Tuple[str, str, Callable[[Context, Section], None]], ...] = (
    ("python", "PYTHON", check_python),
    ("user_site", "USER SITE", check_user_site),
    ("packages", "PACKAGES", check_packages),
    ("git", "GIT", check_git),
    ("database", "DATABASE", check_database),
    ("openai", "OPENAI", check_openai),
    ("phase4a", "PHASE 4A ARTEFACTS", check_phase4a),
    ("bridge", "SRC BRIDGE", check_bridge),
    ("disk", "OUTPUT LOCATIONS", check_disk),
)


# --------------------------------------------------------------------------- report
def build_report(ctx: Context, sections: Sequence[Section], generated_at: datetime, elapsed_s: float) -> Dict[str, Any]:
    """All facts as one JSON-serialisable dict (the content of the ``--write`` file)."""
    return {
        "schema": REPORT_SCHEMA,
        "generated_at_utc": generated_at.strftime(ISO_SECONDS),
        "hostname": socket.gethostname(),
        "elapsed_s": round(elapsed_s, 1),
        "result": "blocked" if ctx.blockers else "ok",
        "blockers": ctx.blockers,
        "warnings": ctx.warnings,
        **{sec.key: sec.facts for sec in sections},
    }


def render_text(report: Dict[str, Any], sections: Sequence[Section]) -> str:
    """Human-readable report: one block per section, then the blocker and warning summary."""
    lines = [f"Electronics pipeline environment check, {report['generated_at_utc']} on {report['hostname']}"]
    for sec in sections:
        lines += ["", sec.title, *(f"  {line}" for line in sec.lines)]
    lines += ["", "SUMMARY", f"  {'blockers':<{LABEL_WIDTH}}{len(report['blockers'])}"]
    lines += [f"    - {message}" for message in report["blockers"]]
    lines += [f"  {'warnings':<{LABEL_WIDTH}}{len(report['warnings'])}"]
    lines += [f"    - {message}" for message in report["warnings"]]
    lines += [f"  {'RESULT':<{LABEL_WIDTH}}{'BLOCKED' if report['blockers'] else 'OK'} ({report['elapsed_s']} s)"]
    return "\n".join(lines)


def write_report(report: Dict[str, Any], out_dir: Path, generated_at: datetime) -> Path:
    """Store the facts as ``env_check_<UTC stamp>.json`` (written under a temporary name first, then renamed)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"env_check_{generated_at.strftime('%Y%m%dT%H%M%SZ')}.json"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(common.dumps(report, indent=2) + "\n")
    os.replace(tmp, path)
    return path


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog="Exit status: 0 = no blocker (warnings allowed), 1 = at least one blocker. "
        "The database session is read-only and no billable API call is made.",
    )
    parser.add_argument("--write", action="store_true", help="also store the facts as env_check_<UTC stamp>.json")
    parser.add_argument("--out-dir", type=Path, help=f"directory for --write (default: {_rel(common.RESULTS_DIR)})")
    parser.add_argument(
        "--require-tables",
        action="store_true",
        help="treat missing backups.gex_llm_regime_* objects as a blocker (use before steps that write to them)",
    )
    parser.add_argument(
        "--skip-model-check", action="store_true", help="do not call the OpenAI API (key presence is still checked)"
    )
    parser.add_argument(
        "--infra-repo",
        type=Path,
        default=common.REPO_ROOT.parent / INFRA_REPO_NAME,
        help="gex-database-infrastructure checkout (default: %(default)s)",
    )
    args = parser.parse_args(argv)
    if args.out_dir is not None and not args.write:
        parser.error("--out-dir only applies together with --write")
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    common.setup_logging()
    started = time.monotonic()
    generated_at = common.utcnow()
    ctx = Context(args)

    sections: List[Section] = []
    for key, title, check in CHECKS:
        logger.info("checking %s", title.lower())
        sec = Section(key, title)
        try:
            check(ctx, sec)
        except Exception as exc:  # one crashing check must not hide the others
            logger.exception("check %s crashed", key)
            sec.facts["crashed"] = _redact(_first_line(exc))
            ctx.blocker(f"{key}: the check itself crashed ({sec.facts['crashed']})")
        sections.append(sec)

    report = build_report(ctx, sections, generated_at, time.monotonic() - started)
    print(render_text(report, sections))
    if args.write:
        try:
            path = write_report(report, args.out_dir or common.RESULTS_DIR, generated_at)
        except OSError as exc:
            logger.error("cannot write the JSON snapshot: %s", exc)
            return 1
        print(f"\nsnapshot written to {path}")
    return 1 if ctx.blockers else 0


if __name__ == "__main__":
    sys.exit(main())
