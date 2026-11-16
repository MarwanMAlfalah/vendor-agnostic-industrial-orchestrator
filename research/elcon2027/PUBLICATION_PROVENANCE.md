# Publication provenance: ElCon-EE 2027 recovery study

This file separates two things:
- the **historical experiment**, which was frozen and run in a local research repository in November 2026;
- the **publication snapshot**, which copied that work into this public history later.

The snapshot did not produce any result. It is neither an external preregistration nor the commit that ran the experiments.

## 1. Historical record (local research repository)

| Event | Local commit / record | Time (UTC) |
|---|---|---|
| Original protocol v1.0 frozen; effect simulator committed | commit `33ea97cc6585caf9ea294317b82f93d813c40d21` (`FROZEN_ANCHOR` in `app/integration/recovery_experiment.py`) | 2026-11-10T00:09:46Z |
| Runs `20261110T124221Z-33ea97c` and `20261110T124324Z-33ea97c` (later superseded) | HEAD `33ea97c` plus 10 uncommitted code files, hashed in each run's `manifest.json` | 2026-11-10T12:42:25Z, 12:43:28Z |
| Original code committed | commit `fb77698ff8db4fc271774b9d8711af8b496f29fd` | 2026-11-10T13:29:25Z |
| Authoritative original run `20261110T132939Z-fb77698` | HEAD `fb77698`, no uncommitted code (`manifest.json`) | 2026-11-10T13:29:42Z |
| Extension x1.0 frozen | `extension_v1/protocol/FREEZE_MANIFEST.txt`; the extension files were untracked working-tree files on top of `fb77698` | 2026-11-12T11:42:36Z |
| Extension run `20261112T114244Z-x1.0` | `manifest.json` records `git_head` `fb77698` and the untracked status | 2026-11-12T11:42:44Z to 11:42:51Z |

All times come from the authors' own commit metadata and run manifests. None of them is an
external timestamp.

## 2. What the publication snapshot is

- **What was copied:** on 2026-11-15 the files listed in §4 were copied, byte for byte, onto public `main` at `3c9f01761bb6df4b27f1651de5f7f39e485f7674`.
- **Sources:** the 30 files the two local commits added or changed (taken from commit `fb77698`), and 34 files from the research working tree.
- **Not public:** neither local commit (`33ea97c`, `fb77698`) is an ancestor of this history, and their Git objects are not in this repository.
- **Unchanged:** no frozen file, protocol, manifest or raw result was edited. Historical commit IDs inside them (for example `FROZEN_ANCHOR`, run names, `git_head`) are kept as written.
- **Changed for publication (not historical):**
  - `README.md` and `.gitignore`;
  - `research/elcon2027/results/README.md`: publication note and corrected bundle wording, starting from the authors' uncommitted 2026-11-11 edit of the version in `fb77698`;
  - new files: `research/elcon2027/README.md`, this file, and `research/elcon2027/constraints-recorded-20261111.txt` (versions copied from the 2026-11-11 environment record).
- **One changed shared file:** `app/agents/execution_agent.py` was changed by `fb77698` (opt-in step identity). Public `main` still had the pre-`fb77698` version (blob `0329e636…`), so the `fb77698` version was copied over it. No public change was overwritten.

## 3. What a reader can and cannot check without the local commits

**Can check from published files** (all executed on this snapshot on 2026-11-15):
- Frozen-file checksums:
  - `protocol/SHA256SUMS`: 4/4;
  - `extension_v1/protocol/FREEZE_MANIFEST.txt`: 27/27.
- Run-manifest hashes: 86/88 recorded values match.
- Both independent verifiers recompute every reported number from the raw records: exit 0.
- Unit tests: 246 passed in a fresh environment built with the recorded versions.
- 51 of the 64 transferred files match a SHA-256 recorded in a published manifest or checksum file:
  - all code and tests: protocol `README.md` freeze hashes, extension `FREEZE_MANIFEST.txt`, run-manifest `frozen_files` and `uncommitted_code_sha256`;
  - all protocol files and all run outputs.
- The other 13 are the manifests and checksum lists themselves, the two verifiers and their recorded outputs and logs, and two extension notes.

**Cannot check without the local commits:**
1. **That the published bytes are the content of `33ea97c`/`fb77698`.** The authoritative original run's `manifest.json` records only `head = fb77698` and an empty diff, with no per-file code hashes.
   - The link from that run to the published code is indirect: the extension run manifest, written on 2026-11-12 with HEAD `fb77698` and no uncommitted changes to those files, records hashes that match the published original-study modules.
   - That link still relies on the manifests being authentic.
2. **The ancestry field.** `anchor_is_ancestor_or_head` in `recovery_experiment.code_revision()` is `false` in any checkout of this history (executed: `false`). The field is recorded, not enforced, and it was not altered.
3. **The 2026-11-11 clean-clone rerun** of `fb77698`, which reproduced 60/60 trial rows and 18/18 pipeline rows. It needs that commit; its record is not published.
4. **The first superseded run's code.** `20261110T124221Z-33ea97c/manifest.json` records SHA-256 values for uncommitted versions of `app/integration/recovery_experiment.py` (`a22e0403…`) and `tests/test_elcon_recovery_experiment.py` (`abba93cb…`). Those versions differ from the versions in `fb77698`. The exact source versions corresponding to these two hashes were not recovered from the inspected checkout or Git history. The run is marked superseded in `results/README.md`.
5. **Commit and freeze times.** They are self-reported (§1).

**Reruns:** rerunning the simulations from this snapshot does not need the old history. Both runners check frozen files by SHA-256, not by Git ancestry. Such reruns were not performed for publication.

## 4. Files transferred byte for byte (SHA-256)

**Source A:** the file as committed in local `fb77698` (added by `33ea97c` or `fb77698`).
**Source B:** an untracked file in the research working tree.

Every hash was checked against its source after copying: 64/64 match.

| Path | Source | SHA-256 |
|---|---|---|
| `app/agents/execution_agent.py` | A | `0895fc97b371b51d3d55f795a12f2cd7f504f5d85913b418a4f28b22cca8851c` |
| `app/integration/maintenance_effect_adapter.py` | A | `86e7eb4f59b5e2d56e72e2af576f79a62da857c2b3699de34be8870913b37a2e` |
| `app/integration/maintenance_effect_service.py` | A | `72b7fd57173da05c15d5df5103025b458275a6a35e74ab150d25d81f973370ac` |
| `app/integration/recovery_experiment.py` | A | `8d6e1e5e5402b0ab70da72c746cc23a59e8aad1654b8b404029a514b152ece3b` |
| `app/integration/recovery_guard.py` | A | `24cd5892f6a041a48456edc20268311c3018d55c84ffe01446fa10bb8ec2203c` |
| `app/integration/recovery_journal.py` | A | `9569bc5697aff66a6703c9486d91ad4638d597127c26623b910afc6a5b885566` |
| `app/integration/recovery_policies.py` | A | `27932dc2464468204aa668c796712eee8d1e26c94576d01440d42675b3d40f7e` |
| `research/elcon2027/protocol/README.md` | A | `1e31f4fc5e6626fb2004e3fd0af4d63f7146e832d560077c3303043762012b03` |
| `research/elcon2027/protocol/SHA256SUMS` | A | `53f0d9a39b150840e7ce1e51b3bdc4a4c0e313b56bbf399aae90c072d18cee05` |
| `research/elcon2027/protocol/oracle_table.json` | A | `381e3bee6045d96c51dba2ed2845a0cc9cbdef894fd0f493197cd8e6969911a9` |
| `research/elcon2027/protocol/protocol.md` | A | `a9daa3879ccd2545a3a34890946ea29fd0b1d128fcdcabfe9eee373961835474` |
| `research/elcon2027/protocol/service_review.md` | A | `24618a97f75bf29555699c2413a7ebc77686d23837c79cfdc8a9d5103338afc1` |
| `research/elcon2027/results/20261110T124221Z-33ea97c/REPORT.md` | A | `76092f1eb79221628185469cbfc58112ae11a3dd9906d658cc89c46dbaca91d9` |
| `research/elcon2027/results/20261110T124221Z-33ea97c/manifest.json` | A | `7d7c247b08257b75ec14dcc098ab758923cbee6ce29512bf50e8b30672a6171f` |
| `research/elcon2027/results/20261110T124221Z-33ea97c/pipeline_crosscheck.csv` | A | `5e0c6a751f47d48a22ccf8d7ab174ab970ab6dc772b43df1f78ea9839a3b1f69` |
| `research/elcon2027/results/20261110T124221Z-33ea97c/raw_trials.jsonl` | A | `46195e42117fbb3d27bcc255f3d080206ac0b0242566efe484153d8f731a372a` |
| `research/elcon2027/results/20261110T124221Z-33ea97c/summary.json` | A | `bf67ff0aef2b7ff816d5d86e4b3431be2a398c36e732d69c11ee985f1c40b116` |
| `research/elcon2027/results/20261110T124221Z-33ea97c/trials.csv` | A | `0d8bc91e03c6672c2b07ff22f4f2628f73c6d330f6a37602dc9cc15451063b47` |
| `research/elcon2027/results/20261110T124324Z-33ea97c/REPORT.md` | A | `4e912e8b027a298ebc0ddf48e5e8a5f309e284b256ea0d9b3ec546c4b3d8eb21` |
| `research/elcon2027/results/20261110T124324Z-33ea97c/manifest.json` | A | `c8e4678e9e96a51434c8c95d38e0a628ca9f249df46c94cfe4855ed5ee168907` |
| `research/elcon2027/results/20261110T124324Z-33ea97c/pipeline_crosscheck.csv` | A | `4c673150aecc5e887b38d66c1c526fea01587b5a02bae355f62e792cd42412ff` |
| `research/elcon2027/results/20261110T124324Z-33ea97c/raw_trials.jsonl` | A | `38f0e7cef4001836f1999bdbed7ce2fee346d58d56fc71b9483e4ed56fe9ce18` |
| `research/elcon2027/results/20261110T124324Z-33ea97c/summary.json` | A | `1f745ffd48d2a8013ac06b1bf21a9723544eba1bc876d4fce4ade02b9984a9df` |
| `research/elcon2027/results/20261110T124324Z-33ea97c/trials.csv` | A | `fb8890c433839e53214e10e1b9edc04a4aa0e118428f4735845ca34f1af2c5f8` |
| `tests/test_elcon_langgraph_recovery.py` | A | `26443e83907734c0ca1b1b826e5cc9e26d2a27b52ac5254cccf4c2e33bf0ad39` |
| `tests/test_elcon_protocol_oracle.py` | A | `0384f7e55d3e6e8bdd272e7593035adac833e1686e1cc1c5c61efeed32a1dc47` |
| `tests/test_elcon_recovery_experiment.py` | A | `21fbcc0c5f46731b82ff2c93d8d5231e75f4067f080d4350c809e0c9b38c87a1` |
| `tests/test_elcon_recovery_guard.py` | A | `5c3bfdd5e078c852b4964b68e2ef26e00b83ace4a6d996bcfd461932d39196e7` |
| `tests/test_elcon_recovery_policies.py` | A | `92cfed433a000552bf3f97f2311cc8bb6f94f36b11c7e017f4d6ccd58cb8ef47` |
| `tests/test_maintenance_effect_service.py` | A | `24512aa1021e193018c8ef16af8f81eb9e587193a7a421cf9e394c372746619c` |
| `app/integration/inflight/__init__.py` | B | `84d308fb965c4aa067889f795f7405a7613d66b5e4a0f6f9fa0d8bc6200933f1` |
| `app/integration/inflight/assessor.py` | B | `f2da6fbdf6c1b007533bf2a7ebd7bb7f97c3dd265e5ae4b941e1e98e63be0167` |
| `app/integration/inflight/experiment.py` | B | `6605626792e69a97e00a8914ee50ead6aabb50fb0e415cb2cf929585d8eb2431` |
| `app/integration/inflight/pipeline_replay.py` | B | `9c956b0b99b37bf0e275a1c63c7a00317aa74bd7fb717290b6589463c44c0d30` |
| `app/integration/inflight/policies.py` | B | `8472a049689e057f39d2cd172fca4af712d26d85694923af1ef19567cac36158` |
| `app/integration/inflight/runner.py` | B | `dd65c08de507ebfa246af97935ca6b77d508d7d626ac4dcf3f4646c5c8ff2235` |
| `app/integration/inflight/service.py` | B | `59dec91d877addac505ace3b69e3cc8c7a1905660b97d40a825c7da535de1ca2` |
| `tests/test_ext_assessor.py` | B | `a48ec9f4e0956aac4075852d977c2ac00bbbf838ca40c719fa726eadd68b1278` |
| `tests/test_ext_inflight_service.py` | B | `b2d048644f8ebce95926758d5964b62cfb308d86af89c46bce0d84e4159ea2d5` |
| `tests/test_ext_policies.py` | B | `00d5e32669942b1e9606562c771e45441af98c3051bf6ebefde74b16064dcbf1` |
| `tests/test_ext_runner.py` | B | `fdb31bbb2c36998acc91100d4b117fd5d466b01d93aff3ef96240fa36809cb50` |
| `research/elcon2027/extension_v1/protocol/protocol.md` | B | `67cb463766150bcc5c6d4373428cb6596dae9fb37d3f3bd255cf0341a066414d` |
| `research/elcon2027/extension_v1/protocol/cases.json` | B | `9ba073274adcb4d5736363858cadca5ad4c8591265f2ac931a7e6d39fa8ecfc2` |
| `research/elcon2027/extension_v1/protocol/FREEZE_MANIFEST.txt` | B | `c28b8d1ecc221d725c1af1fea0f00e7f22ada3b5dbe217ac8ed7deebe219ec7e` |
| `research/elcon2027/extension_v1/results/20261112T114244Z-x1.0/manifest.json` | B | `ba92fb1b0290484b3399f6b3181210703ae73093ea41589f4c07c765103c0dd6` |
| `research/elcon2027/extension_v1/results/20261112T114244Z-x1.0/raw_executions.jsonl` | B | `3609da0ebc81c6c48a55af210ce37e5f9cb469318e635082d0f8de7049adfb42` |
| `research/elcon2027/extension_v1/results/20261112T114244Z-x1.0/raw_replay.jsonl` | B | `c2855565479641c1ee127af7a4038e7248339cb5728d52032124dec75465c0b9` |
| `research/elcon2027/extension_v1/results/20261112T114244Z-x1.0/executions.csv` | B | `86e13d418efec64156bc4401f70ed3445b2b710df95a7839d5db5d8210d8bddc` |
| `research/elcon2027/extension_v1/results/20261112T114244Z-x1.0/replay.csv` | B | `296437666661492c42046e3f0fcf216fa7813d39658ffe1316ef59ab4cf01012` |
| `research/elcon2027/extension_v1/results/20261112T114244Z-x1.0/regression_original_cases.csv` | B | `b8ed324365c9b904e6f8fb0a4f1358fb46c9abab27a83222a161289764d84060` |
| `research/elcon2027/extension_v1/results/20261112T114244Z-x1.0/summary.json` | B | `bcee47a42589ca64908cf43c34665e5aa0e86aa5c3c663f2b57028ef3bb7ef7e` |
| `research/elcon2027/extension_v1/verification/verify_extension.py` | B | `b722fa5c914a6f2b0ecdb7fe5b699bd838c59054feaf19c5060ec2177deb7f24` |
| `research/elcon2027/extension_v1/verification/verify_extension_20261112T114244Z-x1.0.log` | B | `d30cf41b19946100d51959072bdf9c8c4b3f7e387704a7280e46e69ed63b6ddc` |
| `research/elcon2027/extension_v1/DEVELOPMENT_LOG.md` | B | `40ee150eacf2c023d4b015ec273302d88f094e3b4e4fdadcdbc0f6ede71b2d84` |
| `research/elcon2027/extension_v1/README.md` | B | `e1860a5bbfd2abea1cb1d3d37a077f49d3088470b0937114c78e47fbcbc4c493` |
| `research/elcon2027/results/20261110T132939Z-fb77698/manifest.json` | B | `f715bab2d2cd0d374430291db13125650d288a5972075f16b38e171bcee70686` |
| `research/elcon2027/results/20261110T132939Z-fb77698/raw_trials.jsonl` | B | `0894fc84de6d162baae7d728fd4ed1611be6dcce01099ba635133f76efe99d69` |
| `research/elcon2027/results/20261110T132939Z-fb77698/trials.csv` | B | `865550f902baae049fb1e26ccc06af9ed4490dfdd5010089b15801357b38e2c6` |
| `research/elcon2027/results/20261110T132939Z-fb77698/summary.json` | B | `eac4c06a300d690fbb1fece920f771513c832d2b195914ed664a2296c28e1de6` |
| `research/elcon2027/results/20261110T132939Z-fb77698/REPORT.md` | B | `1aa69039dfdf20a3976fbbe4f6ddade60bb55c9d12d540e332d78257c0219dbe` |
| `research/elcon2027/results/20261110T132939Z-fb77698/pipeline_crosscheck.csv` | B | `4c673150aecc5e887b38d66c1c526fea01587b5a02bae355f62e792cd42412ff` |
| `research/elcon2027/submission_v2/release_candidate/verification/verify_results.py` | B | `6aaa53f1451907c4e61f504b6f7ffe577870a038ef4564f1db1f0b235f74f7ad` |
| `research/elcon2027/submission_v2/release_candidate/verification/verify_output.json` | B | `40fb1709de60eff2a428249bc827f8ed21b7775d9be253f6ca07b6e21c33400d` |
| `research/elcon2027/submission_v2/release_candidate/verification/test_and_environment_record.txt` | B | `8013462a1de0cc7262a7b397a5344039a050aed9058dcc7f0dde601c32074121` |
