"""Finite probe ownership, budget durability and honest unverified outcomes."""
import asyncio
from contextlib import contextmanager
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from types import SimpleNamespace
import uuid

import httpx
import pytest

from backend.app.config import Settings
from backend.app.core.providers.models import ProviderManifest
from backend.app.core.providers.registry import ProviderRegistry
from scripts import probe_task_inference as cli


@pytest.fixture
def report_path():
    path = Path("/tmp") / ("t010-fixture-" + uuid.uuid4().hex + ".json")
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


def test_ledger_durable_before_uncertain_send_and_preserved_on_restart(tmp_path):
    path = tmp_path / "ledger.json"
    with pytest.raises(RuntimeError):
        with cli.SendLedger(path) as ledger:
            ledger.consume("embeddings")
            assert json.loads(path.read_text())["spent"]["embeddings"] == 1
            assert stat.S_IMODE(path.stat().st_mode) == 0o600
            raise RuntimeError("uncertain transport outcome")
    with cli.SendLedger(path) as restored:
        with pytest.raises(cli.ProbeError):
            restored.consume("embeddings")
        for task in ("rerank", "decisions", "speech"):
            restored.consume(task)
    assert sum(json.loads(path.read_text())["spent"].values()) == 4


def test_ledger_refuses_concurrent_owner_and_never_resets_malformed_state(tmp_path):
    path = tmp_path / "ledger.json"
    with cli.SendLedger(path):
        with pytest.raises(cli.ProbeError):
            with cli.SendLedger(path):
                pass
    path.write_text('{"version":"wrong","spent":{}}')
    before = path.read_bytes()
    with pytest.raises(cli.ProbeError):
        with cli.SendLedger(path):
            pass
    assert path.read_bytes() == before


def test_ledger_refuses_symlink_and_nonprivate_file(tmp_path):
    target, link = tmp_path / "target", tmp_path / "link"
    target.write_text("private")
    target.chmod(0o600)
    link.symlink_to(target)
    with pytest.raises(cli.ProbeError):
        with cli.SendLedger(link):
            pass
    target.chmod(0o644)
    with pytest.raises(cli.ProbeError):
        with cli.SendLedger(target):
            pass


@pytest.mark.asyncio
async def test_transport_blocks_all_unowned_background_inference():
    with cli.OutboundGuard("embeddings", 0, None) as guard:
        async with httpx.AsyncClient(trust_env=False) as client:
            for url in ("https://openrouter.ai/api/v1/chat/completions",
                        "https://openrouter.ai/api/v1/embeddings",
                        "https://other-provider.invalid/generate"):
                with pytest.raises(httpx.RequestError):
                    await client.post(url)
    assert guard.external_sends == 0 and guard.blocked == 3


@pytest.mark.asyncio
async def test_transport_permit_requires_durable_ledger_and_is_one_shot(tmp_path, monkeypatch):
    actual = []

    async def synthetic_transport(_transport, request):
        actual.append(request.url.path)
        return httpx.Response(200, json={"fixture": True}, request=request)

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", synthetic_transport)
    path = tmp_path / "ledger.json"
    with cli.SendLedger(path) as ledger, cli.OutboundGuard("embeddings", 1, ledger) as guard:
        row = SimpleNamespace(public_id="openrouter::fixture")
        guard.selected = row
        guard.before_send("embeddings", row)
        assert json.loads(path.read_text())["spent"]["embeddings"] == 1
        async with httpx.AsyncClient(trust_env=False) as client:
            await client.post("https://openrouter.ai/api/v1/embeddings")
            with pytest.raises(httpx.RequestError):
                await client.post("https://openrouter.ai/api/v1/embeddings")
        with pytest.raises(cli.ProbeError):
            guard.before_send("embeddings", row)
        assert guard.external_sends == 1 and ledger.consumed == 1
    assert actual == ["/api/v1/embeddings"]


@pytest.mark.asyncio
async def test_catalog_guard_accepts_only_owned_sources(monkeypatch):
    seen = []

    async def synthetic_transport(_transport, request):
        seen.append(str(request.url))
        return httpx.Response(200, json={"data": []}, request=request)

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", synthetic_transport)
    with cli.OutboundGuard("decisions", 0, None) as guard:
        async with httpx.AsyncClient(trust_env=False) as client:
            await client.get("https://openrouter.ai/api/v1/models?output_modalities=decisions")
            with pytest.raises(httpx.RequestError):
                await client.get("https://openrouter.ai/api/v1/models?output_modalities=all")
    assert len(seen) == 1 and guard.external_sends == 0


def test_report_destination_is_private_and_never_follows_links(report_path, tmp_path):
    cli.write_report(report_path, {"status": "UNVERIFIED"})
    assert stat.S_IMODE(report_path.stat().st_mode) == 0o600
    report_path.unlink()
    target = tmp_path / "untouched"
    target.write_text("keep")
    report_path.symlink_to(target)
    with pytest.raises(cli.ProbeError):
        cli.write_report(report_path, {"status": "UNVERIFIED"})
    assert target.read_text() == "keep"


def test_unsafe_output_is_rejected_before_preparing_any_probe(monkeypatch, tmp_path):
    calls = []

    async def forbidden(*args):
        calls.append(args)
        raise AssertionError("No packet may run")

    monkeypatch.setattr(cli, "run_probe", forbidden)
    assert cli.main(["--task", "embeddings", "--max-sends", "1", "--output", str(tmp_path / "outside.json")]) == 2
    assert calls == []


def test_actual_cli_help_and_absent_credentials(tmp_path, report_path):
    script = Path(cli.__file__).resolve()
    help_run = subprocess.run([sys.executable, str(script), "--help"], cwd=tmp_path, text=True, capture_output=True, check=True)
    assert "--max-sends" in help_run.stdout
    assert "--model" not in help_run.stdout and "--url" not in help_run.stdout and "--key" not in help_run.stdout
    env = dict(os.environ)
    env.update(OPENROUTER_API_KEY="", PROXY_MASTER_KEY="", FREE_ACCOUNT_CONFIRMATIONS="[]")
    outcome = subprocess.run([sys.executable, str(script), "--task", "embeddings", "--output", str(report_path)],
                             cwd=tmp_path, env=env, text=True, capture_output=True)
    assert outcome.returncode == 2, outcome.stderr
    report = json.loads(report_path.read_text())
    assert report["status"] == "UNVERIFIED"
    assert report["reason"] == "missing_credentials_or_profile"
    assert report["actual_send_count"] == 0 and report["consumed_send_count"] == 0
    assert stat.S_IMODE(report_path.stat().st_mode) == 0o600


def test_actual_cli_parser_denied_task_never_infers(monkeypatch, tmp_path, report_path):
    from scripts import probe_multi_provider
    monkeypatch.setenv("OPENROUTER_API_KEY", "fixture-key")
    settings = Settings(_env_file=None, proxy_master_key=None, free_account_confirmations=[])
    manifest = ProviderManifest(id="openrouter", name="Fixture", base_url="https://openrouter.ai/api/v1",
        models_endpoint="https://openrouter.ai/api/v1/models", eligibility_profile="openrouter_zero_price",
        auth={"type": "bearer", "api_key_env": "OPENROUTER_API_KEY"})
    registry = ProviderRegistry(settings=settings, manifests=[manifest])
    binding = registry.tasks.binding("speech")
    registry.tasks.publish("speech", {"data": [{"id": "fixture/speech",
        "architecture": {"input_modalities": ["text"], "output_modalities": ["speech"]},
        "pricing": {"prompt": "0", "completion": "0", "request": "0"}, "supported_voices": ["one"]}]}, binding)
    monkeypatch.setattr(cli, "_build_registry", lambda: registry)
    monkeypatch.setattr(cli, "LEDGER_PATH", tmp_path / "budget.json")

    @contextmanager
    def fixture_serve(application):
        # This is a denied CLI test, not external/live delivery certification.
        assert application.state.provider_registry is registry
        yield "http://127.0.0.1:1"

    monkeypatch.setattr(probe_multi_provider, "serve", fixture_serve)
    assert cli.main(["--task", "speech", "--max-sends", "1", "--output", str(report_path)]) == 2
    report = json.loads(report_path.read_text())
    assert report["status"] == "UNVERIFIED" and report["reason"] == "unsupported_enforcement"
    assert report["actual_send_count"] == 0 and report["consumed_send_count"] == 0
    assert sum(json.loads((tmp_path / "budget.json").read_text())["spent"].values()) == 0
