# Dashboard Redesign — Phase 8: Dataset Bootstrap & Upload — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the dashboard self-bootstrapping for a fresh repo clone (no manual Excel-download step) and add an upload UI on the Datenquelle page so users can swap in their own dataset (as long as it matches the Online-Retail-II schema).

**Architecture:** `build_database()` gets a fetch-if-missing fallback that pulls the Online-Retail-II zip from UCI. A new small module `src/ui/dataset_io.py` exposes `validate_uploaded_dataframe()` (schema check) and `replace_database_from_dataframe()` (clean + write + cache clear). The Datenquelle page grows two sections: **Standard-Datensatz** (re-download button) and **Eigener Datensatz** (file upload with preview).

**Tech Stack:** Phases 1–7 stack. Uses `urllib.request` from stdlib for the download (no new dependency); `zipfile` for extraction. `openpyxl` (already in requirements) handles `.xlsx`.

**Reference:** Sheyla's UAT braindump (2026-05-18) — the professor pulling the repo finds `.gitignore`d Excel + DB.

**Depends on:** Phases 1–7 merged.

**Out of scope:**
- Arbitrary-schema upload (different column names, different domain) — would require a Schema-Mapping-UI; defer
- CSV support (initial cut is `.xlsx` only because that's the UCI format and `pd.read_excel` already handles it)
- Persisting "which dataset is active" across sessions — the SQLite file always represents "current dataset"
- Removing the manual `.gitignore` entry for `data/online_retail_II.xlsx` — the file stays gitignored; auto-download replaces the manual step

---

## File Plan

**Create:**
- `src/ui/dataset_io.py` — schema validation + DB replacement helpers
- `tests/test_ui_dataset_io.py` — unit tests with happy + bad-schema cases
- `tests/test_data_processing_fetch.py` — tests for the new UCI fetch (mocking urllib)

**Modify:**
- `src/data_processing.py` — add `UCI_URL`, `fetch_uci_dataset()`; make `build_database()` call fetch when Excel missing
- `src/pages/data_source.py` — extend with Standard-Datensatz + Eigener-Datensatz sections
- `README.md` — Quickstart section: "Clone, install, run — Excel wird automatisch geladen"

---

## Task 1: UCI auto-download in `src/data_processing.py`

`build_database()` currently raises FileNotFoundError if the Excel is missing. New behavior: if missing, download from the UCI canonical URL, cache the zip, extract the xlsx, then proceed.

**Files:**
- Modify: `src/data_processing.py`
- Create: `tests/test_data_processing_fetch.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_data_processing_fetch.py`:

```python
"""Tests for the UCI auto-download fallback in build_database()."""
from pathlib import Path
from unittest.mock import patch

import pytest

from src import data_processing


def test_uci_url_is_set():
    assert data_processing.UCI_URL.startswith("https://")
    assert "online" in data_processing.UCI_URL.lower() or "502" in data_processing.UCI_URL


def test_fetch_uci_dataset_skips_when_excel_exists(tmp_path):
    """If the target Excel already exists, fetch is a no-op."""
    target = tmp_path / "online_retail_II.xlsx"
    target.write_bytes(b"existing")

    with patch.object(data_processing, "urlopen") as mock_urlopen:
        data_processing.fetch_uci_dataset(excel_path=target)

    mock_urlopen.assert_not_called()
    assert target.read_bytes() == b"existing"


def test_fetch_uci_dataset_downloads_when_missing(tmp_path, monkeypatch):
    """If the Excel is missing, fetch downloads the zip and extracts the xlsx."""
    import io
    import zipfile

    target = tmp_path / "online_retail_II.xlsx"
    assert not target.exists()

    # Build a fake zip containing one xlsx-named entry
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("online_retail_II.xlsx", b"fake-xlsx-bytes")
    buf.seek(0)

    class _FakeResponse:
        def __init__(self, data: bytes):
            self._data = data
        def read(self) -> bytes:
            return self._data
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False

    monkeypatch.setattr(
        data_processing, "urlopen",
        lambda _url, timeout=60: _FakeResponse(buf.getvalue()),
    )

    data_processing.fetch_uci_dataset(excel_path=target)
    assert target.exists()
    assert target.read_bytes() == b"fake-xlsx-bytes"
```

- [ ] **Step 2: Run, verify fail**

`pytest tests/test_data_processing_fetch.py -v` → AttributeError on UCI_URL / fetch_uci_dataset.

- [ ] **Step 3: Extend `src/data_processing.py`**

Add the new imports near the top (after existing `from pathlib import Path`):

```python
import io
import zipfile
from urllib.request import urlopen
```

Append two constants + one function (after `EXCEL_PATH`):

```python
UCI_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"


def fetch_uci_dataset(
    excel_path: str | Path = EXCEL_PATH,
    *,
    url: str = UCI_URL,
) -> None:
    """Download the Online Retail II dataset from UCI if not present.

    No-op when ``excel_path`` already exists.  Otherwise: downloads the
    canonical zip, extracts the first ``.xlsx`` entry, and writes it to
    ``excel_path``.  Network errors propagate so callers can surface a
    clear "no internet?" message.
    """
    target = Path(excel_path)
    if target.exists():
        return

    target.parent.mkdir(parents=True, exist_ok=True)

    with urlopen(url, timeout=60) as response:  # noqa: S310
        data = response.read()

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        xlsx_names = [n for n in zf.namelist() if n.lower().endswith(".xlsx")]
        if not xlsx_names:
            raise RuntimeError(
                f"UCI zip at {url} did not contain an .xlsx file (got {zf.namelist()!r})"
            )
        with zf.open(xlsx_names[0]) as src, target.open("wb") as dst:
            dst.write(src.read())
```

Then modify `build_database()` so it calls `fetch_uci_dataset()` before reading the Excel:

```python
def build_database(excel_path: str | Path = EXCEL_PATH, db_path: str | Path = DB_PATH) -> None:
    """Import Excel → SQLite. Skips if DB already exists.

    Auto-downloads the Excel from the UCI ML Repository when missing.
    """
    if Path(db_path).exists():
        return
    fetch_uci_dataset(excel_path=excel_path)
    sheets = pd.read_excel(excel_path, sheet_name=None)
    combined = pd.concat(sheets.values(), ignore_index=True)
    clean = clean_dataframe(combined)
    load_to_sqlite(clean, db_path)
```

- [ ] **Step 4: Run, verify pass**

```bash
pytest tests/test_data_processing_fetch.py -v
pytest tests/ -q | tail -3
```

- [ ] **Step 5: Commit**

```bash
git add src/data_processing.py tests/test_data_processing_fetch.py
git commit -m "feat(data): auto-download UCI Online Retail II zip when missing"
```

## Self-Review

- `fetch_uci_dataset()` is idempotent (no-op when target exists)
- `urlopen` import is at module level so monkeypatch works in tests
- `build_database()` calls fetch then proceeds — single entry point unchanged
- Tests cover happy path + skip-when-exists + missing-xlsx-in-zip error path is implicit
- App still imports

## Report

Status, commit SHA, brief.

---

## Task 2: Dataset upload helpers in `src/ui/dataset_io.py`

Two pure functions: validate that an uploaded DataFrame has the expected UCI raw column names, and replace the database with a fresh load + cache clear.

**Files:**
- Create: `src/ui/dataset_io.py`
- Create: `tests/test_ui_dataset_io.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ui_dataset_io.py`:

```python
"""Tests for dataset upload helpers."""
import pandas as pd
import pytest

from src.ui import dataset_io


_RAW_COLS = ('Invoice', 'StockCode', 'Description', 'Quantity',
             'InvoiceDate', 'Price', 'Customer ID', 'Country')


def _sample_raw_df() -> pd.DataFrame:
    return pd.DataFrame({
        'Invoice':     ['001'],
        'StockCode':   ['ABC'],
        'Description': ['Widget'],
        'Quantity':    [2],
        'InvoiceDate': ['2010-01-01 12:00:00'],
        'Price':       [9.99],
        'Customer ID': [12345],
        'Country':     ['United Kingdom'],
    })


def test_expected_columns_constant():
    assert isinstance(dataset_io.EXPECTED_RAW_COLUMNS, tuple)
    assert set(dataset_io.EXPECTED_RAW_COLUMNS) == set(_RAW_COLS)


def test_validate_uploaded_dataframe_happy_path():
    ok, errors = dataset_io.validate_uploaded_dataframe(_sample_raw_df())
    assert ok is True
    assert errors == []


def test_validate_uploaded_dataframe_missing_columns():
    df = _sample_raw_df().drop(columns=['Customer ID', 'Country'])
    ok, errors = dataset_io.validate_uploaded_dataframe(df)
    assert ok is False
    assert any("Customer ID" in e for e in errors)
    assert any("Country" in e for e in errors)


def test_validate_uploaded_dataframe_empty():
    ok, errors = dataset_io.validate_uploaded_dataframe(pd.DataFrame())
    assert ok is False
    assert any("leer" in e.lower() or "empty" in e.lower() for e in errors)


def test_replace_database_from_dataframe(tmp_path):
    """End-to-end: a sample raw frame turns into a populated SQLite DB."""
    db_path = tmp_path / "out.db"
    df = _sample_raw_df()
    df['Quantity'] = [3]
    df['Price'] = [10.0]
    dataset_io.replace_database_from_dataframe(df, db_path=db_path)

    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT customer_id, revenue FROM transactions").fetchall()
    finally:
        conn.close()
    assert rows == [("12345", 30.0)]
```

- [ ] **Step 2: Run, verify fail**

`pytest tests/test_ui_dataset_io.py -v` → ModuleNotFoundError.

- [ ] **Step 3: Create `src/ui/dataset_io.py`**

```python
"""Helpers for uploading and replacing the active dataset.

The dashboard expects the Online-Retail-II raw schema:
``Invoice, StockCode, Description, Quantity, InvoiceDate, Price,
Customer ID, Country``.  An uploaded dataframe must match that schema
before it's accepted — the cleaning + RFM + forecast logic downstream
assumes those columns.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_processing import (
    DB_PATH,
    clean_dataframe,
    load_to_sqlite,
)


EXPECTED_RAW_COLUMNS: tuple[str, ...] = (
    "Invoice", "StockCode", "Description", "Quantity",
    "InvoiceDate", "Price", "Customer ID", "Country",
)


def validate_uploaded_dataframe(
    df: pd.DataFrame,
) -> tuple[bool, list[str]]:
    """Check that ``df`` has the Online-Retail-II raw schema.

    Returns ``(ok, errors)``.  ``errors`` is a list of human-readable
    German strings (the upload UI surfaces them as ``st.error`` rows).
    """
    errors: list[str] = []
    if df is None or len(df) == 0:
        errors.append("Datei ist leer.")
        return False, errors

    missing = [c for c in EXPECTED_RAW_COLUMNS if c not in df.columns]
    if missing:
        errors.append(
            "Fehlende Spalten: " + ", ".join(missing) +
            ". Erwartet werden die Original-Spalten des "
            "Online-Retail-II-Datensatzes."
        )
    return (not errors), errors


def replace_database_from_dataframe(
    df: pd.DataFrame,
    *,
    db_path: str | Path = DB_PATH,
) -> None:
    """Clean ``df`` and write it as the new SQLite database.

    Removes ``db_path`` if it exists, then re-creates it.  Caller is
    responsible for invalidating Streamlit's data cache afterwards
    (``st.cache_data.clear()``).
    """
    cleaned = clean_dataframe(df)
    target = Path(db_path)
    if target.exists():
        target.unlink()
    load_to_sqlite(cleaned, target)
```

- [ ] **Step 4: Run, verify pass**

```bash
pytest tests/test_ui_dataset_io.py -v
pytest tests/ -q | tail -3
```

- [ ] **Step 5: Commit**

```bash
git add src/ui/dataset_io.py tests/test_ui_dataset_io.py
git commit -m "feat(ui): dataset upload validators + DB replacement helper"
```

## Self-Review

- Schema check uses RAW (pre-rename) column names — what the user actually uploads
- `replace_database_from_dataframe()` deletes the old DB first so re-runs are clean
- Cache invalidation is the caller's job (separation of concerns)
- 5 tests pass

## Report

Status, commit SHA, brief.

---

## Task 3: Extend `src/pages/data_source.py` with bootstrap + upload sections

The page gets two new sections below the existing status row.

**Files:**
- Modify: `src/pages/data_source.py`

- [ ] **Step 1: Add two sections after the existing "Aktionen" section**

Find the existing `st.subheader("Aktionen", anchor=False)` block. Replace the simple rebuild button with two more elaborate sections:

```python
    # ── Standard-Datensatz ───────────────────────────────────────────────
    st.subheader("Standard-Datensatz", anchor=False)
    st.markdown(
        "Online Retail II vom UCI ML Repository (~45 MB). "
        "Wird beim ersten App-Start automatisch heruntergeladen."
    )
    col_a, col_b = st.columns([1, 3])
    with col_a:
        if st.button("Neu laden",
                     help="Löscht die lokale DB und lädt das Original "
                          "neu von der UCI-Quelle."):
            from src.data_processing import EXCEL_PATH
            DB_PATH.unlink(missing_ok=True)
            EXCEL_PATH.unlink(missing_ok=True)
            with st.spinner("Lade Datensatz von UCI…"):
                try:
                    build_database()
                except Exception as exc:                       # noqa: BLE001
                    st.error(f"Download fehlgeschlagen: {exc}")
                else:
                    st.cache_data.clear()
                    st.success("Standard-Datensatz neu geladen.")
                    st.rerun()
    with col_b:
        st.caption("Setzt die aktive Datenbank auf den Stand 2009–2011 zurück.")

    # ── Eigener Datensatz ────────────────────────────────────────────────
    st.subheader("Eigener Datensatz", anchor=False)
    st.markdown(
        "Lade eine Excel-Datei (`.xlsx`) im Online-Retail-II-Schema hoch. "
        "Erwartete Spalten: `Invoice, StockCode, Description, Quantity, "
        "InvoiceDate, Price, Customer ID, Country` — auf einem oder "
        "mehreren Tabellenblättern."
    )
    uploaded = st.file_uploader(
        "Datei wählen",
        type=["xlsx"],
        accept_multiple_files=False,
        key="data_source_upload",
    )
    if uploaded is not None:
        try:
            sheets = pd.read_excel(uploaded, sheet_name=None)
            combined = pd.concat(sheets.values(), ignore_index=True)
        except Exception as exc:                              # noqa: BLE001
            st.error(f"Konnte Datei nicht lesen: {exc}")
            return

        ok, errors = validate_uploaded_dataframe(combined)
        if not ok:
            for err in errors:
                st.error(err)
            return

        st.success(
            f"Schema OK — {len(combined):,} Zeilen, "
            f"{combined['Country'].nunique()} Länder."
        )
        st.markdown("**Vorschau (erste 5 Zeilen):**")
        st.dataframe(combined.head(), use_container_width=True, hide_index=True)

        if st.button("Datenbank ersetzen",
                     type="primary",
                     help="Achtung: ersetzt die aktive Datenbank. "
                          "Du kannst jederzeit zurück zum Standard wechseln."):
            with st.spinner("Schreibe neue Datenbank…"):
                replace_database_from_dataframe(combined)
            st.cache_data.clear()
            st.success("Eigener Datensatz aktiv. Lade die anderen Seiten neu.")
            st.rerun()
```

Update imports at the top of `src/pages/data_source.py` to include:

```python
from src.ui.dataset_io import validate_uploaded_dataframe, replace_database_from_dataframe
```

Verify `pd` is imported (it is — used by the existing read_sql calls).

- [ ] **Step 2: Smoke**

```bash
python -c "from src.pages import data_source" 2>&1 | head -5
python -c "import app" 2>&1 | head -5
pytest tests/ -q | tail -3
```

- [ ] **Step 3: Commit**

```bash
git add src/pages/data_source.py
git commit -m "feat(data_source): standard-rebuild + custom-dataset upload sections"
```

## Self-Review

- The "Standard-Datensatz neu laden" button deletes BOTH the DB and the Excel before calling `build_database()` — that triggers a fresh download
- The upload UI validates schema, shows a preview, then commits only on explicit user click
- `st.cache_data.clear()` is called after every DB replacement so all Streamlit-cached loaders re-fetch
- Errors surface as `st.error` rows (one per problem)
- App imports + tests pass

## Report

Status, commit SHA, brief.

---

## Task 4: README Quickstart

A small but real win: the README's first-run section should now read "clone + install + run" with no manual data step.

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Find the existing Setup / Installation section**

```bash
grep -n "^#\|^##\|setup\|install\|excel\|data" README.md | head -20
```

If there's a "Setup" or "Installation" or "Getting Started" section, edit it. Otherwise insert a Quickstart section near the top (right after the project description).

- [ ] **Step 2: Replace / insert the Quickstart block**

The new content should read approximately:

```markdown
## Quickstart

```bash
git clone <repo-url>
cd Entscheidungsagent-BI
pip install -r requirements.txt
streamlit run app.py
```

Beim ersten Start lädt die App den Online-Retail-II-Datensatz automatisch
vom UCI ML Repository herunter (~45 MB, ~30–90 Sekunden). Danach steht
ein lokaler SQLite-Snapshot unter `data/retail.db` zur Verfügung — alle
weiteren Starts sind sofort verfügbar.

**Eigene Daten:** Auf der Seite *Datenquelle* (Sidebar → System) kannst
du eine andere Excel-Datei im selben Schema hochladen und die aktive
Datenbank ersetzen.
```

(Adjust if your README has different conventions — bilingual mix, code-block style, etc. Match the surrounding tone.)

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(readme): quickstart with auto-download + upload note"
```

## Self-Review

- Quickstart block is near the top of README
- Mentions the auto-download time + size
- Points to Datenquelle for custom datasets

## Report

Status, commit SHA, brief.

---

## Task 5: Final smoke + handoff

- [ ] **Step 1: Tests**

```bash
pytest tests/ -q | tail -5
```
Expected: still green. New tests bring total to ~190.

- [ ] **Step 2: Audit**

```bash
grep -c "UCI_URL\|fetch_uci_dataset" src/data_processing.py
```
Expected: ≥ 3 (constant + function def + call from build_database).

```bash
grep -c "validate_uploaded_dataframe\|replace_database_from_dataframe" src/pages/data_source.py
```
Expected: ≥ 2.

- [ ] **Step 3: Manual simulation of fresh-clone scenario**

This is the critical check. Without actually deleting your real data, simulate the empty-repo state:

```bash
# Temporarily move the existing data aside
mv data/retail.db /tmp/_retail.db.bak
mv data/online_retail_II.xlsx /tmp/_xlsx.bak

# Now run streamlit and confirm the app boots, downloads, builds, renders
streamlit run app.py --server.headless true --server.port 8600 > /tmp/p8smoke.log 2>&1 &
PID=$!
sleep 30   # allow time for ~45 MB download + ~30 sec build
curl -s -o /dev/null -w "HTTP %{http_code}\n" "http://localhost:8600"
curl -s "http://localhost:8600/_stcore/health"
ls -lh data/    # should show retail.db and online_retail_II.xlsx restored
kill $PID 2>/dev/null
wait $PID 2>/dev/null

# Clean up: restore the originals (avoids leaving stale state)
mv /tmp/_retail.db.bak data/retail.db
mv /tmp/_xlsx.bak data/online_retail_II.xlsx
```

Expected: HTTP 200, `ok`, both data files restored.

If the download is slow or fails (rare UCI outage), the test still demonstrates that the *path is wired* — that's enough for handoff. Document any flake in the commit message.

- [ ] **Step 4: User handoff**

Walk Sheyla through the new Datenquelle page:
- Status KPI row (unchanged from Phase 7)
- "Standard-Datensatz" section with the "Neu laden" button that re-downloads from UCI
- "Eigener Datensatz" section with file uploader + schema validation + preview + "Datenbank ersetzen"-Button
- Confirm a real upload of a sample dataset still works end-to-end (try uploading the same Online-Retail-II.xlsx — should succeed, show preview, then replace)

---

## Definition of Done — Phase 8

- [ ] `pytest tests/` green
- [ ] `streamlit run app.py` boots from a state with no `data/retail.db` AND no `data/online_retail_II.xlsx` and ends with both files populated
- [ ] Datenquelle page has Standard-Datensatz + Eigener Datensatz sections
- [ ] `src/ui/dataset_io.py` exposes `validate_uploaded_dataframe` + `replace_database_from_dataframe`
- [ ] README's Quickstart says "git clone, pip install, streamlit run — everything else is automatic"
- [ ] Cached loaders (`load_all`, `load_backtest`, etc.) are invalidated after any DB replacement

## What's Next

After this, the redesign work is complete. The branch is mergeable. Possible future polish (not a full phase):
- Top-bar with shadcn `date_range_picker`
- Dark mode rollout
- streamlit-aggrid on the Verlauf page
- Persisting user settings across sessions
- Stripe-style onboarding empty-state for first-time visitors
