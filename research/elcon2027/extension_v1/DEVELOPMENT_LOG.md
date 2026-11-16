# Extension x1.0: development log (2026-11-12, before the freeze)

Everything here is simulator development. None of it is formal evidence.

1. **Baseline:** `baseline_manifest.txt` records the hashes of the original protocol, results,
   manuscripts v2–v5, review packages, `app/`, `tests/`, `data/`, `docs/`, and the author's
   Word-produced v5 PDF (`201b1c85…418d`).
   - That PDF's text matches the v5 DOCX (`d2bc5c38…`) on 209/209 paragraphs
     (`submission_v5/verification/check_docx_pdf_agreement.py`).
   - Its creator is Microsoft Word LTSC.
   - This shows that Word rendered v5. It does not show that the file opened without a repair
     prompt.
2. **Simulator** (`service.py`): written test-first. `tests/test_ext_inflight_service.py` failed
   at collection because the module was missing, then 11 tests failed on a keyword-argument
   defect in the event logger (`ticket_id=` instead of `ticket=`). After the fix, 12/12 passed.
3. **Assessor** (`assessor.py`): its faulty-trace tests (duplicate, missing effect, wrong adoption
   ticket, dispatch while invalid, commit after hold, censoring) were written in the same step as
   the implementation, not run first. This departs from the repository's test-first rule. All 6
   pass.
4. **Policies** (`policies.py`, R_LI and P_A): the tests failed at collection first, then passed
   5/5.
5. **Pilot 1** (scratch, not retained as results): all 24 cases × 6 policies, one replay. The
   behaviour matched the design. The matrix was not changed after this pilot.
6. **RQ3 harness:** the first version read the step field `output`, but the model field is
   `result`. This was fixed before the pilot. The replay pilot (R01–R04 × 5 modes) behaved as
   designed.
7. **Regression check pilot:** the 11 original single-resumer primary cases (C01 and C11b
   excluded; see protocol §8) × B0/B1/B2/P on the extension simulator gave 44/44 matches with the
   original decision paths and effect counts.
8. **Runner tests** (`tests/test_ext_runner.py`): written after pilot 1, as regression guards for
   the properties checked there. They are development tests, not evidence.
9. **Before the freeze:** full suite 224 passed (194 original + 30 extension); ruff clean;
   `git diff -- app tests` empty, so no tracked file was modified.
