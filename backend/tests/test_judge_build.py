"""Contract and executable launcher checks for the isolated local judge build."""
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_judge_compose_is_keyless_loopback_only_and_separate():
    config = yaml.safe_load((ROOT / "docker-compose.judge.yml").read_text())
    assert config["name"] == "aegispr-judge"
    assert set(config["services"]) == {"backend", "frontend"}
    backend = config["services"]["backend"]
    assert backend["environment"]["NEBIUS_API_KEY"] == ""
    assert backend["environment"]["GITHUB_TOKEN"] == ""
    assert backend["environment"]["INFERENCE_BUDGET_USD"] == "0"
    assert "GPU_WORKER_URL" not in backend["environment"]
    assert "JUDGE_ACCESS_TOKEN" in backend["environment"]["API_ACCESS_TOKEN"]
    assert all(str(port).startswith("127.0.0.1:") for service in config["services"].values() for port in service["ports"])
    assert "aegis-data" not in config["volumes"]
    assert "aegis-runs" not in config["volumes"]


def launcher(tmp_path, monkeypatch):
    repo = tmp_path / "checkout"
    (repo / "scripts").mkdir(parents=True)
    shutil.copyfile(ROOT / "scripts/judge-test-build.sh", repo / "scripts/judge-test-build.sh")
    shutil.copyfile(ROOT / "docker-compose.judge.yml", repo / "docker-compose.judge.yml")
    binaries = tmp_path / "bin"
    binaries.mkdir()
    log = tmp_path / "docker-log.jsonl"
    fake = binaries / "docker"
    fake.write_text("""#!/usr/bin/env python3
import json, os, sys
with open(os.environ['JUDGE_TEST_LOG'], 'a') as stream:
    stream.write(json.dumps({'args':sys.argv[1:], 'provider_present':bool(os.getenv('NEBIUS_API_KEY')), 'access_length':len(os.getenv('JUDGE_ACCESS_TOKEN',''))})+'\\n')
if sys.argv[1:]==['info','--format','{{.ServerVersion}}']: print('29.1.3')
""")
    fake.chmod(0o700)
    monkeypatch.setenv("PATH", f"{binaries}:{os.environ['PATH']}")
    monkeypatch.setenv("JUDGE_TEST_LOG", str(log))
    monkeypatch.setenv("NEBIUS_API_KEY", "must-not-enter-judge-build")
    return repo, log


def invoke(repo, action="start"):
    return subprocess.run(["bash", str(repo / "scripts/judge-test-build.sh"), action], capture_output=True, text=True, timeout=10)


def test_launcher_uses_private_reusable_code_and_no_provider_passthrough(tmp_path, monkeypatch):
    repo, log = launcher(tmp_path, monkeypatch)
    first = invoke(repo)
    assert first.returncode == 0, first.stderr
    key_path = repo / "artifacts/judge/access-code"
    code = key_path.read_text().strip()
    assert len(code) == 64 and all(character in "0123456789abcdef" for character in code)
    assert stat.S_IMODE(key_path.stat().st_mode) == 0o600
    assert code not in first.stdout + first.stderr
    assert invoke(repo, "verify").returncode == 0
    assert key_path.read_text().strip() == code
    events = [json.loads(line) for line in log.read_text().splitlines()]
    assert all(not event["provider_present"] for event in events)
    compose = [event["args"] for event in events if "compose" in event["args"]]
    assert all(args[args.index("-p") + 1] == "aegispr-judge" for args in compose)
    assert any("app.services.fixture_acceptance" in args and "all" in args for args in compose)


def test_stop_preserves_volumes_and_rejects_unknown_actions(tmp_path, monkeypatch):
    repo, log = launcher(tmp_path, monkeypatch)
    assert invoke(repo).returncode == 0
    assert invoke(repo, "stop").returncode == 0
    entries = [json.loads(line)["args"] for line in log.read_text().splitlines()]
    stops = [args for args in entries if "down" in args]
    assert stops and all("--volumes" not in args and "-v" not in args for args in stops)
    assert invoke(repo, "destroy-production").returncode != 0


def test_launcher_refuses_a_symlinked_private_code(tmp_path, monkeypatch):
    repo, _ = launcher(tmp_path, monkeypatch)
    private = repo / "artifacts/judge"
    private.mkdir(parents=True)
    outside = tmp_path / "do-not-change"
    outside.write_text("preserve")
    (private / "access-code").symlink_to(outside)
    assert invoke(repo).returncode != 0
    assert outside.read_text() == "preserve"
