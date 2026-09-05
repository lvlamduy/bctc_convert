from __future__ import annotations

import importlib.util
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/operations/coordinate_family_workers_v1.py"
SPEC = importlib.util.spec_from_file_location("coordinate_family_workers_v1", SCRIPT)
assert SPEC and SPEC.loader
mail = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mail)


@pytest.fixture
def contract():
    return {
        "protocol_version": 1,
        "round_id": "test-round",
        "base_commit": "a" * 40,
        "roles": {
            "vps": {"family": "F36", "branch": "codex/f36", "allowed_paths": ["f36/*"]},
            "laptop": {"family": "F39", "branch": "codex/f39", "allowed_paths": ["f39/*"]},
        },
        "common_allowed_paths": ["coordination.json"],
        "frozen_sha256": {"shared.py": mail.sha256(b"frozen\n")},
    }


class MemoryS3:
    def __init__(self):
        self.objects = {}

    def get(self, key, version=None):
        return self.objects.get(key)

    def create(self, key, payload):
        data = mail.canonical(payload)
        if key in self.objects and self.objects[key][0] != data:
            raise mail.GateError("immutable conflict")
        self.objects[key] = data, "v1"
        return {"key": key, "version_id": "v1", "sha256": mail.sha256(data)}

    def keys(self, prefix):
        return sorted(key for key in self.objects if key.startswith(prefix))


@pytest.fixture
def mailbox(contract):
    box = mail.Mailbox(contract, MemoryS3())
    box.transport.create(f"{box.round_prefix}/contract.json", contract)
    return box


def add_joins(box, *workers):
    for worker in workers:
        box.transport.create(f"{box.round_prefix}/joins/{worker}.json", box.join_payload(worker))


def test_canonical_bytes_and_rejected_duplicates():
    assert mail.canonical({"z": "á", "a": 1}) == b'{"a":1,"z":"\\u00e1"}\n'
    with pytest.raises(mail.GateError, match="Duplicate"):
        mail.decode(b'{"a":1,"a":2}\n')
    with pytest.raises(mail.GateError):
        mail.decode(b'{"a":NaN}\n')


@pytest.mark.parametrize("error", ["AccessDenied", "InvalidAccessKeyId", "ExpiredToken", "404"])
def test_aws_permission_and_non_explicit_absence_errors_fail_closed(monkeypatch, error):
    def run(command, **kwargs):
        assert kwargs.get("shell") is None
        return subprocess.CompletedProcess(
            command,
            1,
            b"",
            (f"An error occurred ({error}) when calling the GetObject operation").encode(),
        )

    monkeypatch.setattr(mail.subprocess, "run", run)
    with pytest.raises(mail.GateError, match=error):
        mail.S3().call("get-object", [], missing_ok=True)


def test_only_expected_aws_error_codes_are_idempotent(monkeypatch):
    responses = iter(
        [
            b"An error occurred (NoSuchKey) when calling the GetObject operation",
            b"An error occurred (PreconditionFailed) when calling the PutObject operation",
            b"An error occurred (ConditionalRequestConflict) when calling the PutObject operation",
        ]
    )
    monkeypatch.setattr(
        mail.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 1, b"", next(responses)),
    )
    client = mail.S3()
    assert client.call("get-object", [], missing_ok=True) is None
    assert client.call("put-object", [], conflict_ok=True) is None
    with pytest.raises(mail.GateError, match="ConditionalRequestConflict"):
        client.call("put-object", [], conflict_ok=True)


@pytest.mark.parametrize("conflict", [False, True])
def test_create_is_conditional_and_downloads_exact_version(monkeypatch, conflict):
    client, payload, calls = mail.S3(), {"hello": "world"}, []

    def call(operation, args, **kwargs):
        assert operation == "put-object"
        assert args[args.index("--if-none-match") + 1] == "*"
        assert args[args.index("--server-side-encryption") + 1] == "AES256"
        assert Path(args[args.index("--body") + 1]).read_bytes() == mail.canonical(payload)
        assert kwargs["conflict_ok"]
        return None if conflict else {"VersionId": "immutable-version"}

    def get(key, version):
        calls.append((key, version))
        return mail.canonical(payload), "immutable-version"

    monkeypatch.setattr(client, "call", call)
    monkeypatch.setattr(client, "get", get)
    result = client.create("test/key", payload)
    assert calls == [("test/key", None if conflict else "immutable-version")]
    assert result["already_present"] is conflict
    assert result["sha256"] == mail.sha256(mail.canonical(payload))


@pytest.mark.parametrize("metadata", [None, {"VersionId": "v1"}])
def test_create_rejects_existing_different_bytes_and_failed_restore(monkeypatch, metadata):
    client = mail.S3()
    monkeypatch.setattr(client, "call", lambda *a, **k: metadata)
    monkeypatch.setattr(client, "get", lambda *a: (b"different", "v1"))
    with pytest.raises(mail.GateError, match="conflict or read-back mismatch"):
        client.create("key", {"expected": True})


def test_get_rejects_nonversioned_bucket(monkeypatch):
    client = mail.S3()
    monkeypatch.setattr(client, "call", lambda *a, **k: {"VersionId": "null"})
    with pytest.raises(mail.GateError, match="versioned"):
        client.get("key")


def test_contract_tamper_rejected(mailbox):
    mailbox.transport.objects[f"{mailbox.round_prefix}/contract.json"] = b"{}\n", "v2"
    with pytest.raises(mail.GateError, match="contract"):
        mailbox.status()


def test_missing_peer_never_allows_check(mailbox, tmp_path):
    add_joins(mailbox, "vps")
    assert mailbox.status()["handshake"] == "PENDING"
    with pytest.raises(mail.GateError, match="Both matching joins"):
        mailbox.check("vps", tmp_path)


def test_wrong_contract_join_rejected(mailbox):
    payload = mailbox.join_payload("laptop")
    payload["contract_sha256"] = "0" * 64
    mailbox.transport.create(f"{mailbox.round_prefix}/joins/laptop.json", payload)
    with pytest.raises(mail.GateError, match="Join"):
        mailbox.status()


def test_informal_ack_is_visible_but_not_a_join(mailbox):
    mailbox.transport.objects[f"{mail.PREFIX}/events/laptop-ack.json"] = (
        b'{ "worker": "laptop", "state": "ACK" }',
        "v1",
    )
    result = mailbox.status()
    assert result["handshake"] == "PENDING"
    assert result["events"] == []
    assert result["informational_inbox"][0]["informational_only"] is True


def test_closed_round_does_not_auto_reclaim(mailbox, tmp_path):
    add_joins(mailbox, "vps", "laptop")
    event = {**mailbox.envelope("vps"), "state": "RELEASED", "created_at": "old"}
    mailbox.transport.create(f"{mail.PREFIX}/events/test-round/old.json", event)
    assert mailbox.status()["round_closed"]
    with pytest.raises(mail.GateError, match="released rounds"):
        mailbox.check("vps", tmp_path)


@pytest.fixture
def repo(tmp_path, contract):
    def run(*args):
        return (
            subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)
            .stdout.decode()
            .strip()
        )

    run("init", "-b", "codex/f36")
    run("config", "user.name", "Mailbox test")
    run("config", "user.email", "mailbox-test@example.invalid")
    for name in ("f36", "f39"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "adapter.py").write_text("original\n", encoding="utf-8")
    (tmp_path / "shared.py").write_bytes(b"frozen\n")
    run("add", ".")
    run("commit", "-m", "test base")
    contract["base_commit"] = run("rev-parse", "HEAD")
    return tmp_path, contract, run


def test_repo_gate_accepts_owned_edits_and_matching_joins(repo):
    path, contract, _ = repo
    box = mail.Mailbox(contract, MemoryS3())
    box.transport.create(f"{box.round_prefix}/contract.json", contract)
    add_joins(box, "vps", "laptop")
    (path / "f36/adapter.py").write_text("updated\n", encoding="utf-8")
    assert box.check("vps", path) == contract["base_commit"]


@pytest.mark.parametrize("which", ["branch", "frozen", "peer", "untracked", "ancestor"])
def test_repo_gate_rejects_scope_or_authority_drift(repo, which):
    path, contract, run = repo
    if which == "branch":
        run("switch", "-c", "wrong")
    elif which == "frozen":
        (path / "shared.py").write_bytes(b"changed\n")
    elif which == "peer":
        (path / "f39/adapter.py").write_text("changed\n", encoding="utf-8")
    elif which == "untracked":
        (path / "secret.txt").write_bytes(b"not allowed")
    else:
        contract["base_commit"] = "0" * 40
    with pytest.raises(mail.GateError):
        mail.check_repo(contract, "vps", path)


def test_repo_gate_rejects_committed_peer_changes(repo):
    path, contract, run = repo
    (path / "f39/adapter.py").write_bytes(b"changed\n")
    run("add", ".")
    run("commit", "-m", "peer edit")
    with pytest.raises(mail.GateError, match="peer-owned"):
        mail.check_repo(contract, "vps", path)


def test_repo_gate_rejects_staged_peer_change_hidden_by_working_tree(repo):
    path, contract, run = repo
    (path / "f39/adapter.py").write_bytes(b"staged peer change\n")
    run("add", "f39/adapter.py")
    (path / "f39/adapter.py").write_bytes(b"original\n")
    assert run("diff", "--name-only", "HEAD") == ""
    with pytest.raises(mail.GateError, match="peer-owned"):
        mail.check_repo(contract, "vps", path)


@pytest.mark.parametrize("field", ["bucket", "region", "prefix"])
def test_contract_rejects_different_fixed_mailbox(contract, field):
    contract[field] = "unexpected"
    with pytest.raises(mail.GateError, match="fixed mailbox"):
        mail.Mailbox(contract, MemoryS3())


def test_send_ready_cannot_bypass_pending_join(mailbox, tmp_path):
    with pytest.raises(mail.GateError, match="Both matching joins"):
        mailbox.send("vps", "READY_FOR_INTEGRATION", "not ready", tmp_path)


def test_bad_contract_role_rejected(contract):
    changed = deepcopy(contract)
    changed["roles"]["laptop"]["family"] = "F36"
    with pytest.raises(mail.GateError, match="ownership"):
        mail.Mailbox(changed, MemoryS3())
