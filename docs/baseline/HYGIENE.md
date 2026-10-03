# Project Priory — Repository Hygiene & Secret Audit Report

This report documents repository hygiene candidates for cleanup, tracking status in Git, sensitive personal data and credentials audits, and proposed `.gitignore` updates.

Per ground rules: **No files were deleted**, no credentials were leaked or copied, and only non-destructive `.gitignore` updates are proposed and applied.

---

## 1. File Inventory & Git Tracking Audit

| Candidate Path | File Type / Description | Git Tracking Status | Rationale for Candidate Cleanup |
| :--- | :--- | :--- | :--- |
| `run_command.txt` | Text file (single shell command string) | **Tracked** (`git ls-files run_command.txt`) | Transient shell command artifact from manual testing; should not be version controlled. |
| `scratch_check_bank.py` | Scratch Python script for inspecting account bank items | **Tracked** (`git ls-files scratch_check_bank.py`) | One-off exploratory inspection script. References `os.getenv("GW2_API_KEY")`. Belongs in `scratch/`. |
| `scratch/` | Directory containing 20+ one-off debug and exploration scripts | **Untracked / Ignored** (`.gitignore` line 43) | Correctly ignored. Retained locally for developer reference. |
| `bin/cloudflared` | Mach-O 64-bit arm64 binary executable (Cloudflare tunnel) | **Untracked / Ignored** (`.gitignore` line 39: `bin/`) | Correctly ignored by Git. Binary executable should remain untracked. |
| `__pycache__/` | Compiled Python bytecode directories across packages | **Untracked / Ignored** (`.gitignore` line 7) | Correctly ignored across all subdirectories. |
| `.DS_Store` | macOS filesystem metadata files | **Untracked / Ignored** (`.gitignore` line 36) | Correctly ignored across repository. |
| `data/cache/api_items.json` | 1.18 MB JSON API response dump | **Tracked** (`git ls-files data/cache/api_items.json`) | Large API cache file tracked in Git. Should be generated dynamically or cached in ignored storage. |
| `data/cache/ontology_audit_manifest.json` | 133 KB JSON audit manifest | **Tracked** (`git ls-files data/cache/ontology_audit_manifest.json`) | Intermediate audit artifact tracked in repository history. |
| `data/cache/http_etags.json` | 6.08 MB HTTP caching ETags map | **Untracked / Ignored** (`.gitignore` line 44) | Correctly ignored by Git. |
| `data/cache/market_prices.json` | 569 B Trading Post price cache | **Untracked / Ignored** (`.gitignore` line 45) | Correctly ignored by Git. |
| `.env` | Local environment variables | **Untracked / Ignored** (`.gitignore` line 2) | Correctly ignored by Git. Contains live private credentials. |

---

## 2. Sensitive Data & Account Information Audit

A forensic scan of the requested files was performed to identify any exposure of real Guild Wars 2 account names, API keys, or personal identifiers:

### 2.1 `docs/research/api_model_discrepancy_audit.md`
* **Status**: **CONTAINS SENSITIVE DATA (LIVE CREDENTIALS & ACCOUNT METRICS)**
* **Findings**:
  * Line 6: Contains live GW2 API Application Key token GUID (`0F55D98D-2943-...`).
  * Line 7: Contains live ArenaNet Account ID GUID (`BE7CC931-...`) and account username string (`Xenext.3106`).
  * Lines 33, 34, 51, 56: Contains character names associated with the account (`Kerling`, `Legacy Of Harathi`).
  * Lines 50–62: Contains exact account snapshots including character levels, title unlocks (75 titles), wallet balances (1,325g, 5,391 Spirit Shards), and achievement progress.
* **Action Required**: The human maintainer should sanitize line 6 and line 7 before any public push or release of this repository, replacing the token with `<REDACTED_API_KEY>` and username with `<REDACTED_ACCOUNT>`.

### 2.2 `scratch_check_bank.py`
* **Status**: **CLEAN (NO HARDCODED SECRETS)**
* **Findings**:
  * Line 10: Calls `key = os.getenv("GW2_API_KEY")`.
  * Contains no hardcoded tokens, secret strings, or user account names.

### 2.3 `data/` and `data/cache/`
* **Status**: **CONTAINS PERSONAL ACCOUNT NAME IN LOCAL CACHE**
* **Findings**:
  * `data/cache/http_etags.json`: Contains cached account string `Xenext.3106` resulting from local API inspection calls to `/v2/account`. This file is ignored by `.gitignore` (line 44) and is not committed.
  * `data/cache/api_items.json`: Contains generic ArenaNet catalog item definitions (no user tokens or account names).
  * `data/cache/ontology_audit_manifest.json`: Contains catalog item mapping metrics (no personal data).
  * `data/cache/market_prices.json`: Contains public TP pricing data.

---

## 3. Applied `.gitignore` Improvements

The following entries have been appended to `.gitignore` to prevent committing transient scripts, test outputs, and developer scratch files:

```gitignore
# Transient root runner and scratch inspection scripts
run_command.txt
scratch_check_bank.py

# Data cache directory blanket ignore (while keeping data/ directory structure)
data/cache/*.json
!data/cache/.gitkeep

# Fitness check and competency question scratch files
tools/fitness/__pycache__/
docs/baseline/fitness/*.owl
```

Per rules: No files were deleted from Git index or disk.
