"""UNRUN V3 candidate: READY_FOR_PROFILE_BINDING; Claude-owned NEW store only.

Linux Python 3.12 -I -B HELPER SPEC.json SPEC_SHA256 SPEC_SIZE.
The rejected11380 sweep is immutable history. Only an independently registered
approved5ea FULL profile, complete audits and fresh whole cold replay can admit
a private OFFICIAL copy. Missing profile is a hard fence, not an override flag.
"""
from __future__ import annotations

import hashlib
import json
import os
import resource
import signal
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
import traceback
import types
from contextlib import closing
from pathlib import Path

HEAD = "5ea0499e8745366c8a9cc11246484fabde78ee6c"
CANONICAL_REPO = Path("/mnt/d/bctc_bank/bctc-ai-2025-current")
RUNNER = "scripts/experiments/run_gemini_json_income_tax_accounting_family_v1.py"
RUNNER_SHA = "f94b6c6b732cf259eed04b6a07ca57124f2ae84076111c5429b6e81f2af462fe"
FROZEN = {
    "src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py":
        "bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2",
    "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py":
        "d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5",
}
REJECTED_SWEEPS = {
    "2c472bd1009eb42d18080221ad22f6ba1344d6a19f3757f39d6d39d227a1aa2e":
        "0414/0417: doc225 wrong current-tax role; doc110 nonprinted deferred-tax label. "
        "Fix or hold through new code/source-authenticated replay; old artifacts are immutable.",
}
FIELDS = {"schema", "repo", "expected_head", "run_dir", "source_pdf_root", "expected_refs",
          "visible_audit_ref", "residual_spec_ref", "adapter_ref", "helper_ref", "out_dir", "limits", "run_profile_ref"}


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "Duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def exact_path(value):
    need(type(value) is str, "Path must be text")
    path = Path(value)
    need(path.is_absolute() and path.resolve() == path, "Absolute nonsymlink path required: " + value)
    return path


class Held:
    def __init__(self):
        self.files = {}

    @staticmethod
    def identity(value):
        return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
                value.st_mtime_ns, value.st_ctime_ns)

    @staticmethod
    def digest(fd):
        digest, size = hashlib.sha256(), 0
        while block := os.pread(fd, 1024 ** 2, size):
            digest.update(block)
            size += len(block)
        return digest.hexdigest(), size

    def open(self, reference):
        need(type(reference) is dict and set(reference) == {"path", "sha256", "size_bytes"},
             "Exact path/SHA/byte-count reference required")
        path = exact_path(reference["path"])
        need(type(reference["sha256"]) is str and len(reference["sha256"]) == 64
             and all(c in "0123456789abcdef" for c in reference["sha256"])
             and type(reference["size_bytes"]) is int and reference["size_bytes"] > 0, "Reference pin shape")
        key = str(path)
        if key not in self.files:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
            try:
                before = os.fstat(fd)
                need(stat.S_ISREG(before.st_mode) and self.digest(fd) == (reference["sha256"], reference["size_bytes"])
                     and self.identity(before) == self.identity(os.fstat(fd))
                     == self.identity(os.stat(path, follow_symlinks=False)), "Input byte/identity drift: " + key)
            except BaseException:
                os.close(fd)
                raise
            self.files[key] = (fd, self.identity(before), dict(reference))
        need(self.files[key][2] == reference, "Conflicting references for one path")
        return self.files[key][0]

    def read(self, reference, maximum):
        need(reference["size_bytes"] <= maximum, "Input exceeds declared metadata bound")
        fd = self.open(reference)
        raw = os.pread(fd, reference["size_bytes"] + 1, 0)
        need(len(raw) == reference["size_bytes"] and hashlib.sha256(raw).hexdigest() == reference["sha256"],
             "Metadata read differs")
        return raw

    def validate(self):
        for path, (fd, identity, reference) in self.files.items():
            need(identity == self.identity(os.fstat(fd)) == self.identity(os.stat(path, follow_symlinks=False))
                 and self.digest(fd) == (reference["sha256"], reference["size_bytes"]), "Final input drift: " + path)

    def close(self):
        for fd, _identity, _reference in self.files.values():
            os.close(fd)


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True, timeout=30).stdout.strip()


def module_from_ref(held, reference, name):
    raw = held.read(reference, 4 * 1024 ** 2)
    module = types.ModuleType(name)
    module.__file__, module.__package__ = reference["path"], ""
    sys.modules[name] = module
    exec(compile(raw, reference["path"], "exec"), module.__dict__)
    held.validate()
    return module


def sqlite_checks(path):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as connection:
        connection.execute("PRAGMA query_only=ON")
        need(connection.execute("PRAGMA quick_check").fetchall() == [("ok",)]
             and connection.execute("PRAGMA foreign_key_check").fetchall() == [], "SQLite integrity failed")


def write_once(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def main(argv):
    held, out, repo, spec = Held(), None, None, None
    started = time.monotonic()
    cache_dir, previous_cache_prefix = None, sys.pycache_prefix
    record = {"schema": "F39_OFFICIAL_PROMOTION_DRAFT_V3", "status": "FAIL", "errors": [],
              "financial_acceptance": False, "family_terminal": False, "official_selection_written": False,
              "common204_gate_claimed": False, "provider_called": False}
    try:
        need(sys.platform == "linux" and sys.version_info[:2] == (3, 12) and sys.flags.isolated
             and sys.dont_write_bytecode and not sys.flags.optimize, "Linux Python 3.12 -I -B required")
        need(len(argv) == 3, "HELPER SPEC.json SPEC_SHA256 SPEC_SIZE required")
        spec_ref = {"path": argv[0], "sha256": argv[1], "size_bytes": int(argv[2])}
        spec = strict_json(held.read(spec_ref, 1024 ** 2))
        need(type(spec) is dict and set(spec) == FIELDS and spec["schema"] == "F39_OFFICIAL_PROMOTION_SPEC_V3",
             "Reviewed exact promotion spec required")
        need(spec["expected_head"] == HEAD, "A different run/code needs a separately reviewed draft revision")
        repo, run_dir = exact_path(spec["repo"]), exact_path(spec["run_dir"])
        pdf_root = exact_path(spec["source_pdf_root"])
        need(repo == CANONICAL_REPO and git(repo, "rev-parse", "HEAD") == HEAD
             and git(repo, "status", "--porcelain", "--untracked-files=all") == "",
             "Use the clean private READ-ONLY namespace clone at the original registered evidence path")
        held.open(spec["helper_ref"])
        need(exact_path(spec["helper_ref"]["path"]) == Path(__file__).resolve(), "Executed helper differs")
        # Pure external adapter imports stdlib only. Fail missing/unreviewed
        # profile before reading source stores/PDFs or creating any output.
        audit_module = module_from_ref(held, spec["adapter_ref"], "_reviewed_f39_closeout_adapter_v3")
        registered_profile = audit_module.approved_profile_reference_v3()
        need(spec["run_profile_ref"] == registered_profile, "Caller cannot replace the source-registered approved run profile")
        profile = audit_module.validate_run_profile_contract_v3(strict_json(held.read(registered_profile, 1024 ** 2)))
        need(profile["expected_head"] == HEAD, "Only exact reviewed5ea runtime is permitted")
        for reference in (profile["full_run_receipt_ref"], profile["synthetic_gate_receipt_ref"], profile["gate_reader_ref"]):
            held.open(reference)
        refs = spec["expected_refs"]
        need(type(refs) is dict and set(refs) == {"sweep", "audit", "results", "corpus_index"}, "Run-reference axis")
        need(all(type(refs[key]) is dict and set(refs[key]) == {"sha256", "size_bytes"}
                 for key in ("sweep", "audit", "results")), "Run paths cannot override their fixed filenames")
        need(refs == profile["expected_refs"], "Only the immutable approved NEW FULL run-reference axis is eligible")
        named = {key: {"path": str(run_dir / filename), **refs[key]}
                 for key, filename in (("sweep", "income-tax-sweep.json"), ("audit", "income-tax-audit.json"),
                                       ("results", "results.sqlite3"))}
        for reference in (*named.values(), refs["corpus_index"], spec["visible_audit_ref"], spec["residual_spec_ref"]):
            held.open(reference)
        # File presence, complete frontiers or owner checkboxes cannot cure a known wrong accepted role.
        need(refs["sweep"]["sha256"] not in REJECTED_SWEEPS,
             "BLOCKED_KNOWN_REJECTED_SWEEP: " + REJECTED_SWEEPS.get(refs["sweep"]["sha256"], ""))
        limits = spec["limits"]
        need(type(limits) is dict and set(limits) == {"as_bytes", "cpu_soft", "cpu_hard", "wall_seconds"}
             and all(type(v) is int and v > 0 for v in limits.values())
             and limits["as_bytes"] <= 4 * 1024 ** 3 and limits["cpu_soft"] < limits["cpu_hard"],
             "Owner-fixed resource contract; no cap increase or retry")
        resource.setrlimit(resource.RLIMIT_AS, (limits["as_bytes"], limits["as_bytes"]))
        resource.setrlimit(resource.RLIMIT_CPU, (limits["cpu_soft"], limits["cpu_hard"]))
        def interrupted(signum, _frame):
            raise RuntimeError("TERMINATED_BY_SIGNAL:" + str(signum))
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGXCPU, signal.SIGALRM):
            signal.signal(sig, interrupted)
        signal.alarm(limits["wall_seconds"])
        # -B prohibits writes, not reads of an adjacent .pyc. Project imports must
        # have a new empty cache namespace; helper modules execute captured bytes.
        cache_dir = tempfile.mkdtemp(prefix="f39-promotion-empty-import-cache-")
        sys.pycache_prefix = cache_dir
        bundle = audit_module.validate_f39_closeout_bundle_v1(
            repo=repo, run_dir=run_dir, source_pdf_root=pdf_root,
            visible_audit_path=exact_path(spec["visible_audit_ref"]["path"]),
            residual_spec_path=exact_path(spec["residual_spec_ref"]["path"]), expected_refs=refs)
        need(bundle["status"] == "VALIDATED_F39_CLOSEOUT_AUDITS_NOT_ACCEPTANCE"
             and bundle["financial_acceptance"] is False
             and bundle["official_promotion_eligible"] is True
              and bundle["approved_run_profile_ref"] == registered_profile
              and bundle["approved_run_profile"] == profile
              and bundle["retained_holds_preserved"] == [110, 225]
             and bundle["visible_audit_ref"] == spec["visible_audit_ref"]
             and bundle["residual_spec_ref"] == spec["residual_spec_ref"], "Both complete authenticated audit contracts required")
        audit = strict_json(held.read(named["audit"], 64 * 1024 ** 2))
        old_run_id = bundle["family_run_id"]
        need(audit["family_run_id"] == old_run_id and audit["sweep_id"] == bundle["sweep_id"]
             and audit["run_kind"] == "EXPERIMENTAL" and audit["provider_calls_performed"] is False
             and audit["cold_source_replay"] == "PASS_EXACT_INDEPENDENT_STORAGE_QUERY_NO_CACHE"
             and audit["results_reload"] == "PASS_EXACT", "Existing run/audit identity or mandatory replay differs")
        original_implementations, authorities = audit["implementation_refs"], audit["immutable_input_refs"]
        for reference in (*original_implementations, *authorities):
            held.open(reference)
        runner_ref = next(ref for ref in original_implementations if Path(ref["path"]) == repo / RUNNER)
        need(runner_ref["sha256"] == RUNNER_SHA, "Wrong F39 runner")
        for name, sha in FROZEN.items():
            need(next(ref for ref in original_implementations if Path(ref["path"]) == repo / name)["sha256"] == sha,
                 "Frozen source mismatch")
        sys.path.insert(0, str(repo / "src"))
        sys.path.insert(0, str(repo / "scripts/experiments"))
        runner = module_from_ref(held, runner_ref, "_reviewed_f39_promotion_runner")
        runner._assert_shared_pins_v1()
        index_path = exact_path(refs["corpus_index"]["path"])
        index = runner.validate_current_corpus_manifest_index_v1(strict_json(held.read(refs["corpus_index"], 1024 ** 2)))
        negative_axis = audit_module.validate_negative_admission_axis_v3(audit, index, profile)
        need(audit_module.digest(negative_axis) == bundle["negative_admission_axis_sha256"]
             and runner.same_typed_json_v1(negative_axis,
                 bundle["original_audit_metadata"]["registered_source_label_discrepancy_admission_axis"]),
             "Complete warm negative-label source admission differs from validated audit")
        artifact_root = index_path.parent.parent
        documents, selected_ids = runner._documents_v1(index, artifact_root)
        need(len(documents) == 271 and len(selected_ids) == 14945, "Entire FULL271 source axis required")
        database = runner.generic._content_ref(artifact_root, index["database_ref"])
        source_ref = {**index["database_ref"], "path": str(database)}
        held.open(source_ref)
        expected_authorities = [runner.generic._file_ref(index_path)]
        for document in documents:
            expected_authorities.extend(runner.generic._file_ref(runner.generic._content_ref(
                artifact_root, document["index_document"][name])) for name in ("document_manifest_ref", "selection_ref"))
        need(authorities == expected_authorities, "Complete original immutable authority axis differs")
        census_refs = audit["original_raw_money_census"]["document_census_refs"]
        need([item["document_ordinal"] for item in census_refs] == list(range(1, 272)), "Complete warm census axis required")
        for item in census_refs:
            held.open(item["census_ref"])
        runner._raw_census_summary_v1(census_refs)
        caption = audit["registered_section_caption_admission"]
        caption_axis = caption["document_admission_axis"]
        need(len(caption_axis) == 271 and caption["document_admission_axis_sha256"]
             == runner.canonical_json_sha256_v1(caption_axis), "Complete warm caption admission axis required")
        sqlite_checks(Path(named["results"]["path"]))
        with closing(sqlite3.connect(Path(named["results"]["path"]).as_uri() + "?mode=ro&immutable=1", uri=True)) as old_connection:
            need(old_connection.execute("SELECT sweep_id,sweep_sha256 FROM family_run WHERE family_run_id=?",
                                        (old_run_id,)).fetchall() == [(bundle["sweep_id"], refs["sweep"]["sha256"])],
                 "Stored canonical sweep bytes are not the exact provided sweep file")
        # The public store loader validates the whole sweep. Its full-object memory cost is unavoidable
        # with this API; the separate visual adapter streams rows and never invokes this path.
        sweep = runner.load_gemini_accounting_family_sweep_v1(Path(named["results"]["path"]), old_run_id)
        need(sweep["sweep_id"] == bundle["sweep_id"] and [t["document_ordinal"] for t in sweep["trials"]]
             == list(range(1, 272)), "Stored full sweep differs")
        runner.validate_source_observation_mapping_contract_v1(sweep)
        destination_dir = exact_path(spec["out_dir"])
        need(not os.path.lexists(destination_dir) and destination_dir.parent.is_dir(), "NEW output directory required")
        for authority in (repo, run_dir, pdf_root, artifact_root):
            need(not destination_dir.is_relative_to(authority) and not authority.is_relative_to(destination_dir),
                 "Output overlaps input authority")
        os.umask(0o077)
        destination_dir.mkdir(mode=0o700)
        out = destination_dir
        destination = out / "official-f39-family.sqlite3"
        implementation_refs = [*original_implementations, spec["helper_ref"], spec["adapter_ref"],
                                spec["visible_audit_ref"], spec["residual_spec_ref"], registered_profile,
                                profile["full_run_receipt_ref"], profile["synthetic_gate_receipt_ref"], profile["gate_reader_ref"]]
        need(len({ref["path"] for ref in implementation_refs}) == len(implementation_refs), "Duplicate implementation refs")
        replay = audit_module.bind_cold_replay_v3(
            runner._make_authenticated_source_replay_adapter_v1, negative_admission_axis=negative_axis,
            database=database, database_ref=index["database_ref"], artifact_root=artifact_root,
            corpus_index_ref={**runner.generic._file_ref(index_path), "path": index_path.relative_to(artifact_root).as_posix()},
            documents=documents, expected_census_refs=census_refs, source_pdf_root=pdf_root,
            implementation_refs=implementation_refs, authority_refs=authorities,
            expected_caption_admission_axis=caption_axis)
        held.validate()
        record["store_write_attempted"] = True
        record["official_selection_written"] = None  # commit may precede a signal/exception before return
        record["private_store_provisional_until_all_final_checks_pass"] = True
        stored = runner.ingest_gemini_accounting_family_sweep_v1(
            destination, sweep=sweep, corpus_index_ref=runner.generic._file_ref(index_path),
            implementation_refs=implementation_refs, run_kind="OFFICIAL", source_page_database=database,
            selected_page_json_version_ids=selected_ids, corpus_artifact_root=artifact_root,
            source_replay_adapter=replay, source_replay_adapter_ref=runner_ref)
        record["official_selection_written"] = True
        record["private_store_provisional_until_all_final_checks_pass"] = True
        runner._store_raw_money_censuses_v1(destination, family_run_id=stored["family_run_id"], census_refs=census_refs)
        loaded = runner.load_gemini_accounting_family_sweep_v1(destination, stored["family_run_id"])
        need(runner.same_typed_json_v1(loaded, sweep), "New OFFICIAL store exact reload differs")
        del loaded
        sqlite_checks(destination)
        with closing(sqlite3.connect(destination.as_uri() + "?mode=ro&immutable=1", uri=True)) as connection:
            counts = {table: connection.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
                      for table in ("family_run", "family_run_execution", "family_trial", "family_mapping",
                                    "family_current_selection", "family_selection_event", "f39_raw_money_census_v1")}
            need(counts == {"family_run": 1, "family_run_execution": 1, "family_trial": 271,
                            "family_mapping": sum(len(t["mappings"]) for t in sweep["trials"]),
                            "family_current_selection": 1, "family_selection_event": 1,
                            "f39_raw_money_census_v1": 271}, "New OFFICIAL store denominator differs")
            need(connection.execute("SELECT family_id,family_run_id FROM family_current_selection").fetchall()
                 == [("INCOME_TAX", stored["family_run_id"])], "Wrong current selection")
            need(connection.execute("SELECT family_run_id,run_kind FROM family_run_execution").fetchall()
                 == [(stored["family_run_id"], "OFFICIAL")], "Wrong execution kind/axis")
        for document in documents:
            source = document["manifest"]["document"]
            pdf = runner._safe_path(pdf_root / source["source_logical_name"])
            need(pdf.stat().st_size == source["source_size_bytes"] and runner.generic._sha256(pdf) == source["source_sha256"],
                 "Source PDF changed during final promotion callbacks")
        held.validate()
        need(git(repo, "rev-parse", "HEAD") == HEAD and git(repo, "status", "--porcelain", "--untracked-files=all") == "",
             "Final Git barrier failed")
        record.update(status="PASS_PRIVATE_OFFICIAL_SELECTION_NOT_FAMILY_ACCEPTANCE", official_selection_written=True,
                      family_run_id=stored["family_run_id"], sweep_id=sweep["sweep_id"], counts=counts,
                      audit_bundle=bundle, mandatory_source_replay="PASS_FRESH_WHOLE_SOURCE_CENSUS_AND_PDF_AUTHENTICATION",
                      exact_reload=True, quick_check="ok", foreign_key_rows=0,
                      store_ref=runner.generic._file_ref(destination), expected_head=HEAD)
        record["approved_run_profile_ref"] = registered_profile
        record["source_label_discrepancy_admission_axis_sha256"] = audit_module.digest(negative_axis)
        record["private_store_provisional_until_all_final_checks_pass"] = False
    except BaseException as error:
        record["errors"].append(type(error).__name__ + ": " + str(error))
        record["traceback"] = traceback.format_exc()
    finally:
        if sys.platform == "linux":
            signal.alarm(0)
        try:
            held.validate()
        except BaseException as error:
            record["errors"].append("FINAL_INPUT_BARRIER: " + str(error))
        finally:
            held.close()
        sys.pycache_prefix = previous_cache_prefix
        if cache_dir is not None:
            try:
                os.rmdir(cache_dir)  # empty directory created by this attempt only
            except OSError as error:
                record["errors"].append("UNEXPECTED_IMPORT_CACHE_CONTENT: " + str(error))
        if record["errors"]:
            record["status"] = "FAIL"
            if record.get("store_write_attempted") is True:
                record["private_store_provisional_until_all_final_checks_pass"] = True
        record["wall_seconds"] = round(time.monotonic() - started, 3)
        if out is not None:
            try:
                write_once(out / "F39_OFFICIAL_PROMOTION_RECEIPT_V3.json", record)
            except BaseException as error:
                record["status"] = "FAIL"
                if record.get("store_write_attempted") is True:
                    record["private_store_provisional_until_all_final_checks_pass"] = True
                record["errors"].append("FINAL_RECEIPT_WRITE: " + str(error))
        print(json.dumps(record if out is None else {k: record[k] for k in ("status", "errors", "official_selection_written")},
                         ensure_ascii=False), flush=True)
    return 0 if record["status"] == "PASS_PRIVATE_OFFICIAL_SELECTION_NOT_FAMILY_ACCEPTANCE" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
