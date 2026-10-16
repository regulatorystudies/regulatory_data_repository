# Unified Scraper Dashboard

A Streamlit app with three tabs for pulling and analyzing federal rulemaking data on demand:
1. **Unified Agenda Data** — download a CSV of Unified Agenda actions for a year/season range.
2. **OIRA Review Data** — download and chart OIRA-reviewed actions for a year or year range.
3. **Unified Agenda Data Analysis** — run summary stats and plots for a single Unified Agenda.

## Components

Entry point: [`unified_scrapper.py`](unified_scrapper.py) — defines all three tabs and is what Streamlit runs.

It pulls in code from two places:

- [`unified_agenda_data/helper.py`](unified_agenda_data/helper.py) — downloads/parses Unified Agenda XML, disk-caches closed (immutable) agendas in `ua_cache/`. Backs tab 1.
- [`unified_agenda_data/unified_agenda_data_analysis.py`](unified_agenda_data/unified_agenda_data_analysis.py) — `run_analysis_for_dashboard()`, the summary/plot logic behind tab 3.
- [`oira_review_data_collector.py`](oira_review_data_collector.py) — only used for the `pandas_read_xml` (`pdx`) import it brings in via `from oira_review_data_collector import *`. Tab 2's own download/transform/chart logic is written inline in `unified_scrapper.py`, not called from this file.

**Dead code, not used by the dashboard** (don't edit these expecting it to change app behavior):
- `unified_agenda_data/unified_agenda_data.py` and `unified_agenda_data/dash_code.py`
- `oira.py` (an older standalone prototype of tab 2)
- the repo-root `unified_agenda_data/` package (`collector.py`, `dashboard.py`, `unified_agenda_data_analysis.py`) — see pitfall below.

## Running it locally

```bash
pip install -r requirements.txt
streamlit run dynamic_dashboard/unified_scrapper.py
```

Run from the **repo root**, not from inside `dynamic_dashboard/` — some internal paths assume that working directory. Open http://localhost:8501.

## Deployment

The [`Procfile`](../Procfile) runs the same entry point for Heroku-style hosting:

```
web: streamlit run dynamic_dashboard/unified_scrapper.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true
```

Optional env vars (both default to a writable directory next to the app, falling back to a temp dir on read-only filesystems like most PaaS deployments):
- `UA_OUTPUT_DIR` — where tab 1's requested CSVs are written.
- `UA_CACHE_DIR` — where tab 1's per-year/season disk cache (closed agendas only) is written.

## Common pitfalls

- **Two packages named `unified_agenda_data`.** One lives at the repo root, one inside `dynamic_dashboard/`. Because Streamlit runs the script from `dynamic_dashboard/`, that directory is first on `sys.path`, so `dynamic_dashboard/unified_agenda_data` is the one that actually gets imported — the `sys.path.insert(...)` for the repo-root copy in `unified_scrapper.py` has no effect, since Python has already cached the package under that name. If you need to change tab 1 or tab 3's logic, edit the copy **inside `dynamic_dashboard/`**, not the repo-root one.
- **`from oira_review_data_collector import *` looks unused but isn't** — it's the only place `pdx` (`pandas_read_xml`) gets into `unified_scrapper.py`'s namespace. Removing that import silently breaks tab 2's agency-list download (`NameError: pdx`).
- **"Display Data" / "Run Analysis" look like they do nothing** on first click for a large range — there's no progress bar, only `st.write` status lines from `status_callback`. Give it a few seconds before assuming it's stuck.
- **Year dropdowns go one year past the latest real data** (currently 2025 Spring is the real cap, UI allows selecting 2026). This is deliberate — the next agenda isn't published yet — and 2026 requests are quietly served from the latest published agenda (see `_resolve_actual_period` in `helper.py`) under the 2026 label. Don't "fix" this by removing the extra year option.
- **Stale cached data after a new Unified Agenda is published.** `ua_cache/` only skips re-downloading for *closed* year/seasons (`_is_live_period` in `helper.py`); if a cached file looks wrong after a new agenda is live, clear `dynamic_dashboard/ua_cache/`.
- **Agency list fetch depends on an external GitHub raw URL** (`zhoudanxie/regulatory_data_repository`, hardcoded in `unified_scrapper.py`), not a local file. If that repo/branch changes or GitHub is unreachable, both tab 1's agency filter and tab 2's agency names will fail — the `@st.cache_data` decorator means a successful first call stays cached for the rest of the session even if the network drops afterward.
- **lxml / lxml.etree parsing errors** on malformed XML from reginfo.gov are usually transient upstream issues, not bugs in this code — the OIRA XML parser (`oira_transformation`) already uses `recover=True`.
- **Module-level `st.image(...)` and `st.markdown(...)` calls** at the top of `unified_scrapper.py` run on every rerun (every widget interaction), not just once — that's normal Streamlit behavior, not a bug.
