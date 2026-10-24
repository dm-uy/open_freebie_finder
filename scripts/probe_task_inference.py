"""Finite T-010 isolated proxy proof. Diagnostics contain no inference content."""
import argparse
import asyncio
from collections import Counter
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import logging
import os
from pathlib import Path
import stat
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from backend.app.config import get_settings
from backend.app.core.providers.registry import ProviderRegistry
from backend.app.core.tasks.catalog import TASKS, SOURCE_PATHS, DISPATCH_PATHS, PROFILE_REVISION
from backend.app.core.tasks.protocol import parse_json, validate_audio, validate_response
from backend.app.core.tasks.transport import TaskExecutor

LEDGER_PATH = Path("/tmp/t010-live-budget.json")
TEMP_ROOTS = {Path("/tmp").resolve(), Path("/private/tmp").resolve()}
VERSION = "T-010-v1.0.0"
READINESS_SECONDS = 35
_permit = ContextVar("t010_probe_send_permit", default=None)


class ProbeError(Exception):
    def __init__(self, reason="probe_unavailable"):
        self.reason = reason
        super().__init__("Task probe unavailable.")


def _private_file(path, *, create=True):
    """Open a regular owned0600 file without following links or blocking on FIFOs."""
    flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
    created = False
    try:
        fd = os.open(path, flags | os.O_CREAT | os.O_EXCL, 0o600) if create else os.open(path, flags)
        created = create
    except FileExistsError:
        fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
            raise ProbeError("unsafe_private_file")
        return fd, created
    except BaseException:
        os.close(fd)
        raise


def _write_fd(fd, value):
    data = json.dumps(value, sort_keys=True, allow_nan=False).encode()
    os.lseek(fd, 0, os.SEEK_SET)
    os.ftruncate(fd, 0)
    offset = 0
    while offset < len(data):
        offset += os.write(fd, data[offset:])
    os.fsync(fd)


class SendLedger:
    """Persistent reservations survive uncertain sends and CLI restarts."""
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else LEDGER_PATH
        self.fd = None
        self.value = None
        self.consumed = 0

    def __enter__(self):
        try:
            self.fd, created = _private_file(self.path)
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if created:
                self.value = {"version": VERSION, "spent": {task: 0 for task in TASKS}}
                _write_fd(self.fd, self.value)
            else:
                if os.fstat(self.fd).st_size > 4096:
                    raise ProbeError("invalid_budget_ledger")
                self.value = parse_json(os.read(self.fd, 4097))
            spent = self.value.get("spent")
            if (set(self.value) != {"version", "spent"} or self.value["version"] != VERSION
                    or type(spent) is not dict or set(spent) != set(TASKS)
                    or any(type(v) is not int or v not in (0, 1) for v in spent.values())):
                raise ProbeError("invalid_budget_ledger")
            return self
        except BaseException as exc:
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise ProbeError("budget_unavailable") from None

    def consume(self, task):
        if self.fd is None or task not in TASKS or self.value["spent"][task] != 0:
            raise ProbeError("budget_exhausted")
        self.value["spent"][task] = 1
        # Reservation is durable before transport receives a one-shot permit.
        try:
            _write_fd(self.fd, self.value)
        except OSError:
            raise ProbeError("budget_unavailable") from None
        self.consumed += 1

    def __exit__(self, *_):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


class OutboundGuard:
    """Reject unrelated inference before network I/O, including background work."""
    def __init__(self, task, max_sends, ledger):
        self.task, self.max_sends, self.ledger = task, max_sends, ledger
        self.external_sends = self.proxy_posts = self.blocked = 0
        self.local_origin = None
        self.selected = None

    def before_send(self, task, row):
        if self.max_sends != 1 or task != self.task or row is not self.selected or self.ledger is None:
            raise ProbeError("unexpected_inference")
        self.ledger.consume(task)
        _permit.set({"owner": self, "task": task, "used": False})

    def __enter__(self):
        self.original = httpx.AsyncHTTPTransport.handle_async_request
        owner = self

        async def guarded(transport, request):
            url = request.url
            origin = (url.scheme, url.host, url.port)
            if owner.local_origin == origin:
                local_path = "/v1" + {"embeddings": "/embeddings", "rerank": "/rerank",
                                      "decisions": "/decisions", "speech": "/audio/speech"}[owner.task]
                allowed = request.method == "GET" and url.path == "/v1/models"
                if request.method == "POST" and url.path == local_path and owner.max_sends == 1 and owner.proxy_posts == 0:
                    owner.proxy_posts += 1
                    allowed = True
                if not allowed:
                    owner.blocked += 1
                    raise httpx.RequestError("Probe isolation rejected a local operation.", request=request)
            elif origin == ("https", "openrouter.ai", None) or origin == ("https", "openrouter.ai", 443):
                path = url.raw_path.decode("ascii", "strict")
                if request.method == "GET" and path in {"/api/v1/models", *SOURCE_PATHS.values()}:
                    pass
                elif request.method == "POST" and path == DISPATCH_PATHS[owner.task]:
                    permit = _permit.get()
                    if (not permit or permit["owner"] is not owner or permit["used"]
                            or owner.external_sends != 0 or owner.max_sends != 1):
                        owner.blocked += 1
                        raise httpx.RequestError("Probe isolation rejected inference.", request=request)
                    permit["used"] = True
                    owner.external_sends += 1
                else:
                    owner.blocked += 1
                    raise httpx.RequestError("Probe isolation rejected an external operation.", request=request)
            else:
                owner.blocked += 1
                raise httpx.RequestError("Probe isolation rejected an external origin.", request=request)
            return await owner.original(transport, request)

        httpx.AsyncHTTPTransport.handle_async_request = guarded
        return self

    def __exit__(self, *_):
        httpx.AsyncHTTPTransport.handle_async_request = self.original


def _build_registry():
    settings = get_settings().model_copy(update={"free_account_confirmations": [], "routing_provider_priority": []})
    source = ProviderRegistry(settings=settings)
    manifest = source.get_manifest("openrouter")
    if manifest is None:
        raise ProbeError("missing_profile")
    return ProviderRegistry(settings=settings, manifests=[manifest])


def _candidate_hashes():
    root = Path(__file__).resolve().parents[1]
    paths = sorted((root / "backend/app").rglob("*.py")) + [Path(__file__).resolve()]
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths if path.is_file() and not path.is_symlink()}


def _payload(task, row):
    value = {"model": row.public_id}
    if task == "embeddings":
        value["input"] = "A short task probe."
    elif task == "rerank":
        value.update(query="Which is a fruit?", documents=["An apple is a fruit.", "A chair is furniture."])
    elif task == "decisions":
        value.update(state="An apple is a fruit.", questions={"fruit": {"type": "noul",
            "instructions": "Does the text describe a fruit?", "criteria": {"false": "No", "true": "Yes"}}})
    else:
        caps = row.capabilities
        voices, formats = sorted(caps.get("voices", [])), sorted(caps.get("formats", []))
        if not voices or not formats:
            raise ProbeError("capability_unavailable")
        value.update(input="A short task probe.", voice=voices[0], response_format=formats[0])
    return value


class _Events(logging.Handler):
    def __init__(self, rid):
        super().__init__()
        self.rid, self.rows = rid, []

    def emit(self, record):
        try:
            value = json.loads(record.getMessage())
            if value.get("event") == "task_request" and value.get("request_id") == self.rid:
                self.rows.append({"attempt_count": value.get("attempt_count"),
                                  "delivery": value.get("delivery")})
        except (ValueError, TypeError, AttributeError):
            pass


@contextmanager
def _capture(rid):
    logger = logging.getLogger("backend.app.core.tasks.transport")
    old_level = logger.level
    handler = _Events(rid)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)


async def run_probe(task, max_sends=0):
    """Run only current eligible admission; blocked inventory consumes no send."""
    report = {"version": VERSION, "task": task, "status": "UNVERIFIED", "reason": "probe_unavailable",
              "actual_send_count": 0, "consumed_send_count": 0, "monetary_observation": "unavailable",
              "started_at": datetime.now(timezone.utc).isoformat(), "candidate_hashes": _candidate_hashes()}
    guard = ledger = registry = None
    try:
        if task not in TASKS or type(max_sends) is not int or max_sends not in (0, 1):
            raise ProbeError("invalid_arguments")
        registry = _build_registry()
        manifest = registry.get_manifest("openrouter")
        if registry.profile_skip(manifest):
            raise ProbeError("missing_credentials_or_profile")
        # No direct-provider qualifications can run with this registry/settings.
        if ([m.id for m in registry.get_manifests()] != ["openrouter"]
                or registry.settings.free_account_confirmations):
            raise ProbeError("isolation_unavailable")
        from backend.app.main import create_app
        from scripts.probe_multi_provider import serve
        rid = "t010-" + uuid.uuid4().hex
        # Mode0 does not reserve/modify the inference ledger.
        with SendLedger() if max_sends else nullcontext(None) as ledger:
            if ledger is not None and ledger.value["spent"][task]:
                raise ProbeError("budget_exhausted")
            with OutboundGuard(task, max_sends, ledger) as guard, _capture(rid) as events:
                application = create_app(provider_registry=registry)
                application.state.task_executor = TaskExecutor(registry, before_send=guard.before_send)
                with serve(application) as base:
                    url = httpx.URL(base)
                    guard.local_origin = (url.scheme, url.host, url.port)
                    deadline = time.monotonic() + READINESS_SECONDS
                    while registry.tasks.states[task] == "unverified" and time.monotonic() < deadline:
                        await asyncio.sleep(0.05)
                    snapshot = registry.tasks.inventory(task)
                    report.update(inventory_count=len(snapshot["data"]),
                        eligibility_counts=dict(Counter(row["eligibility"] for row in snapshot["data"])),
                        exclusion_reasons=dict(Counter(row["reason"] for row in snapshot["data"])))
                    rows = registry.tasks.eligible_rows(task)
                    if not rows:
                        inventory = registry.tasks.inventory(task)
                        reasons = sorted({row["reason"] for row in inventory["data"]})
                        report["reason"] = reasons[0] if len(reasons) == 1 else "no_eligible_candidate"
                        report["inventory_state"] = registry.tasks.states[task]
                    else:
                        row = sorted(rows, key=lambda value: value.public_id)[0]
                        report.update(candidate_id=row.public_id, source_revision=row.source_revision,
                                      profile_revision=PROFILE_REVISION, assurance=row.verdict.assurance)
                        if not max_sends:
                            report["reason"] = "preflight_only"
                        else:
                            guard.selected = row
                            payload = _payload(task, row)
                            headers = {"X-Request-ID": rid}
                            if registry.settings.proxy_master_key:
                                headers["Authorization"] = "Bearer " + registry.settings.proxy_master_key
                            local_path = {"embeddings": "/embeddings", "rerank": "/rerank",
                                          "decisions": "/decisions", "speech": "/audio/speech"}[task]
                            async with httpx.AsyncClient(trust_env=False, follow_redirects=False, timeout=35) as client:
                                response = await client.post(base + "/v1" + local_path, json=payload, headers=headers)
                            report.update(http_status=response.status_code, response_bytes=len(response.content))
                            if response.status_code == 200:
                                if task == "speech":
                                    validate_audio(payload, response.content, response.headers.get("Content-Type", ""))
                                else:
                                    # The proxy has already verified the exact raw identity;
                                    # the consuming socket sees its requested public ID.
                                    validate_response(task, payload, parse_json(response.content), row.public_id)
                                matching = [event for event in events.rows if event == {"attempt_count": 1, "delivery": "success"}]
                                if response.headers.get("X-Request-ID") == rid and len(matching) == 1 and guard.external_sends == 1:
                                    report.update(status="PASS", reason="delivered")
                                else:
                                    report["reason"] = "delivery_evidence_unavailable"
                            else:
                                report["reason"] = "proxy_delivery_unavailable"
                if guard.blocked:
                    report.update(status="UNVERIFIED", reason="isolation_violation")
    except ProbeError as exc:
        report["reason"] = exc.reason
    except Exception:
        report["reason"] = "probe_unavailable"
    finally:
        if guard is not None:
            report["actual_send_count"] = guard.external_sends
        if ledger is not None:
            report["consumed_send_count"] = ledger.consumed
        if registry is not None and registry.is_private_identifier(report.get("candidate_id", "")):
            report.pop("candidate_id", None)
            report.update(status="UNVERIFIED", reason="private_identifier")
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
    return report


def _open_report(path):
    path = Path(path)
    # Direct private temporary files avoid user-controlled parent symlink races.
    if not path.is_absolute() or path.parent.resolve() not in TEMP_ROOTS or path.name == LEDGER_PATH.name:
        raise ProbeError("unsafe_output")
    if path.parent not in {Path("/tmp"), Path("/private/tmp")}:
        raise ProbeError("unsafe_output")
    try:
        fd, _ = _private_file(path)
        return fd
    except (OSError, ProbeError):
        raise ProbeError("unsafe_output") from None


def write_report(path, report):
    fd = _open_report(path)
    try:
        _write_fd(fd, report)
    finally:
        os.close(fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, choices=TASKS)
    parser.add_argument("--max-sends", type=int, choices=(0, 1), default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        # Validate and retain the private report destination before any packet.
        fd = _open_report(args.output)
    except ProbeError:
        print(json.dumps({"status": "UNVERIFIED", "reason": "unsafe_output"}))
        return 2
    try:
        report = asyncio.run(run_probe(args.task, args.max_sends))
        _write_fd(fd, report)
    except OSError:
        print(json.dumps({"status": "UNVERIFIED", "reason": "report_unavailable"}))
        return 2
    finally:
        os.close(fd)
    print(json.dumps({key: report[key] for key in ("task", "status", "reason", "actual_send_count", "consumed_send_count")}))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
