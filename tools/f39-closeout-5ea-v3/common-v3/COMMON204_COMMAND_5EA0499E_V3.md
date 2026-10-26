# COMMON204 at 5ea0499e V3 ? UNRUN / Claude-owned launch only

This additive command preserves all204 documents / 11,454 selected pages,
index acc1d08e? / source DB a14904a4?, canonical evidence paths and cold
persistence/replay. ONE new output/store; no subset/base cache/provider/
re-extraction/old-artifact cleanup.

Gate authority is only CODEX_F39_T5_TESTS_20261026_V1/f39-t5-nonlegacy-20261026-v2/
test-receipt.json, raw SHA256
7acbb5d786678af256db1847f2276031b5c180069c42e4fc607680e11188386a,8392 bytes.
It reports Python3.12.3/Ruff0/pytest0/all28 modules. The fixed reader rejects
L2/focused/failed/incomplete/caller-resealed evidence, regardless of PASS wording.

Tests ran at53b6b16a6818b5f71ccb7285e55ed730c4ae14ae; runtime is STRICT
5ea0499e8745366c8a9cc11246484fabde78ee6c. Direct parent53b and sole added
checkpoint Markdown delta are verified. All32 receipt source/test files,
two frozen files and package initializer must match BOTH commits' Git blobs
and raw runtime LF bytes. This is explicit docs-only equivalence, no generic
commit relaxation/CRLF normalization. Owner-reported execution evidence is
not independent test attestation; reader binds reported JUnit/ruff hashes
without rereading their bodies. No corpus/PDF/financial acceptance follows.

Claude0440 schedules F37 ingest -> F39 FULL271 -> COMMON204 serially.
Host-RAM/caps/timeouts/fresh run-parent/log/terminal receipt/private namespace
remain Claude-owned. Historical2GiB test cap is not corpus resource approval.
No parallel project job, unchanged retry or automatic cap raise authorized.

INSIDE the reviewed private namespace, bind Claude's clean read-only5ea clone at
/mnt/d/bctc_bank/bctc-ai-2025-current because registered refs name that root.
Do not use actual5092 worktree, rewrite evidence, monkeypatch ROOT, create
symlink substitutes or mount anything in this review. Reports2025-current only;
standalone2024 excluded, printed comparative2024 retained.

~~~bash
set -euo pipefail
repo=/mnt/d/bctc_bank/bctc-ai-2025-current
expected=5ea0499e8745366c8a9cc11246484fabde78ee6c
artifact=/srv/bctc-restore/dev-shm/bctc-ai-27-bank-family-live-v1
index="$artifact/current-corpus-manifest-indexes/32c474f657f9484244e9675a0ca4801cb49b4923971dfb7bea17081904154747.json"
database="$artifact/current-corpus-freeze-inputs/store-a14904a492e6beae165b81f7aa1738352a9824e113f1b163a46ee277d37e0220.sqlite3"
pdf_root=/mnt/d/bctc_bank/restore-20260905T014806Z/source
reader=/mnt/d/bctc_bank/restore-tools/drafts/f39-current-code-common-5ea0499e-20261026-v3/f39_synthetic_gate_reader_v3.py
reader_sha=f1420be9028b3fe59ace246f11d8b2dd2f1d17acac51e2de59b637082d03431d
reader_bytes=23719
gate=/mnt/d/bctc_bank/restore-receipts/CODEX_F39_T5_TESTS_20261026_V1/f39-t5-nonlegacy-20261026-v2/test-receipt.json
# Owner selects ONE fresh attempt parent; preserve failures, never reuse.
out=/home/bctc/claude-runs/f39-common204-5ea0499e-T2-owner-approved-v3/official
cache_dir="$(dirname "$out")/python312-import-cache-empty-5ea0499e-v3"

test "$(git -C "$repo" rev-parse HEAD)" = "$expected"
test -z "$(git -C "$repo" status --porcelain --untracked-files=all)"
test ! -e "$out"
test -d "$(dirname "$out")"
test -d "$pdf_root"
test ! -e "$cache_dir"
test ! -L "$cache_dir"
test "$(stat -c %s "$index")" = 317566
test "$(stat -c %s "$database")" = 553984000

printf '%s  %s\n' \
  f94b6c6b732cf259eed04b6a07ca57124f2ae84076111c5429b6e81f2af462fe "$repo/scripts/experiments/run_gemini_json_income_tax_accounting_family_v1.py" \
  370236b18345bea95315e9e41492ea4306dce35b5da0a2fb7dad6b54cdf26d88 "$repo/src/bctc_ai/evaluation/gemini_json_income_tax_family_v1.py" \
  96f72e7343e20b888414bd1ff9fb62719acf85d6743a27c4e5ba2e0e9aa879f4 "$repo/src/bctc_ai/evaluation/gemini_json_income_tax_source_label_discrepancy_v1.py" \
  c8788461c2e3aed5068c9ba3c329f39bfd13d2cf8dea7aede724bbff6b017bcf "$repo/config/families/tm-income-tax-source-label-discrepancies-v1.json" \
  bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2 "$repo/src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py" \
  d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5 "$repo/scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py" \
  72431fa5e6bd5679a0c9701296da9a5b037b34ec2734da50c9b6bbefacec16be "$repo/data/registered/gemini_json_first_27bank_vietnamese_page_scope_v2.json" \
  acc1d08e45e5a05925c434ae1c96fd6bc481a0e6ca61fc9f78e155efca7365b1 "$index" \
  a14904a492e6beae165b81f7aa1738352a9824e113f1b163a46ee277d37e0220 "$database" \
  | sha256sum --check --strict -

# Execute only captured authenticated reader bytes, no project imports.
env -i PATH=/usr/bin:/bin HOME=/home/bctc \
  /srv/bctc-runtime/venv/bin/python3.12 -I -B -X "pycache_prefix=$cache_dir" - \
  "$reader" "$reader_sha" "$reader_bytes" "$repo" "$gate" "$index" <<'PINNED_F39_GATE'
import hashlib,json,os,stat,sys
from pathlib import Path
p_text,expected_sha,size_text,repo_text,gate_text,index_text=sys.argv[1:]
if sys.version_info[:2]!=(3,12) or not sys.flags.isolated or not sys.dont_write_bytecode:
    raise SystemExit('Python3.12 -I -B required')
p=Path(p_text); size=int(size_text)
def need(ok,message):
    if not ok: raise SystemExit(message)
def identity(x):
    return tuple(getattr(x,k) for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns'))
need(p.is_absolute() and '..' not in p.parts
     and all(not x.is_symlink() for x in (p,*p.parents)),'reader path unsafe')
with p.open('rb') as stream:
    before=os.fstat(stream.fileno())
    raw=stream.read(size+1)
    need(stat.S_ISREG(before.st_mode) and before.st_size==size
         and len(raw)==size and hashlib.sha256(raw).hexdigest()==expected_sha,'reader pin differs')
    scope={'__name__':'_approved_f39_gate_v3','__file__':str(p)}
    exec(compile(raw,str(p),'exec'),scope)
    result=scope['validate_f39_synthetic_gate_v1'](
        repo=Path(repo_text),
        receipt_ref={'path':gate_text,
                     'sha256':'7acbb5d786678af256db1847f2276031b5c180069c42e4fc607680e11188386a',
                     'size_bytes':8392},
        expected_head='5ea0499e8745366c8a9cc11246484fabde78ee6c')
    need(result['status']=='VERIFIED_53B_SOURCE_EQUIVALENT_TO_5EA','full gate did not verify')
    with scope['_held_file'](
            Path(index_text),'acc1d08e45e5a05925c434ae1c96fd6bc481a0e6ca61fc9f78e155efca7365b1',317566) as held:
        index=scope['_strict_json'](held['raw'])
        need(type(index.get('documents')) is list and len(index['documents'])==204,
             'COMMON document axis differs')
        need(index['summary']['document_count']==204 and index['summary']['page_count']==11454
             and sum(d['page_count'] for d in index['documents'])==11454,
             'COMMON selected page denominator differs')
    stream.seek(0)
    need(stream.read(size+1)==raw and identity(before)==identity(os.fstat(stream.fileno()))
         ==identity(p.stat()) and all(not x.is_symlink() for x in (p,*p.parents)),
         'reader drifted during full gate')
print(json.dumps(result,sort_keys=True,separators=(',',':')))
PINNED_F39_GATE

# Fresh cache only after gate; -B writes none, -X avoids old adjacent .pyc reads.
mkdir -m 700 -- "$cache_dir"
test "$(git -C "$repo" rev-parse HEAD)" = "$expected"
test -z "$(git -C "$repo" status --porcelain --untracked-files=all)"
env -i PATH=/usr/bin:/bin HOME=/home/bctc \
  /srv/bctc-runtime/venv/bin/python3.12 -I -B -X "pycache_prefix=$cache_dir" \
  "$repo/scripts/experiments/run_gemini_json_income_tax_accounting_family_v1.py" \
  --repo-root "$repo" \
  --corpus-index "$index" \
  --source-page-database "$database" \
  --artifact-root "$artifact" \
  --source-pdf-root "$pdf_root" \
  --source-page-scope "$repo/data/registered/gemini_json_first_27bank_vietnamese_page_scope_v2.json" \
  --output-dir "$out" \
  --results-database "$out/results.sqlite3"
~~~

Do not pre-create out: runner exclusively creates it. Preserve failed outputs/
cache. This whole204 cold diagnostic/persistence is not a seal. Actual source
replay, observation, SQLite and whole PDF/residual reviews remain required.
T2 adapter/promoter separately binds expected_source_label_discrepancy_axis and
the exact new run profile; command grants no OFFICIAL promotion or F41 opening.

ROOT-only synthetic plan: capture reader/testfile/verbatim8392-byte receipt fixture
into ONE new own Codex test branch descended from5ea and commit exact sources.
Use ONE fresh LF Linux clone under root's run namespace. Explicitly set
F39_GATE_TEST_SOURCE_REPO to that own fresh clone; run only this packet's testfile
under serialized Python3.12 -I -B wrapper/caps. Tests create an owned temporary
local shared Git clone detached5ea; source branch remains untouched and no
corpus/SQLite/PDF/provider is used. Do not test in Claude's branch. This packet's
author performed no reader import/AST/compile/lint/tests/WSL/COMMON launch.
