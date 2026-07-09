import os
import re
import tempfile
import warnings
from typing import Optional

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
from lxml import etree

warnings.filterwarnings("ignore")

# Disk cache for parsed Unified Agenda data, keyed by year/season. Closed
# (immutable) agendas are cached here indefinitely so repeat requests -- and
# requests made after an app restart/redeploy -- skip the network fetch and
# XML parse entirely. The currently in-progress agenda is never written here
# since reginfo.gov keeps updating it until the season closes.
# UA_CACHE_DIR can be overridden via env var; falls back to a temp dir if the
# app directory isn't writable (e.g. read-only deployment filesystems).
_THIS_DIR = os.path.dirname(os.path.realpath(__file__))
_dashboard_dir = os.path.dirname(_THIS_DIR)
_ua_cache_default = os.path.join(_dashboard_dir, "ua_cache")
UA_CACHE_DIR = os.environ.get(
    "UA_CACHE_DIR",
    _ua_cache_default if os.access(_dashboard_dir, os.W_OK) else os.path.join(tempfile.gettempdir(), "ua_cache"),
)
os.makedirs(UA_CACHE_DIR, exist_ok=True)

def replace_noun(text):
    if text is None:
        text = "N/A"
    return text

def remove_html_tags(text):
    if text is not None:
        clean_text = re.compile(
            "<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});"
        )
        text_out = re.sub(clean_text, " ", text).strip()
    else:
        text_out = None
    return text_out

def xml_to_csv(file_path: str) -> pd.DataFrame:
    agenda_date, RIN, agency_code, agency_name, department_code, department_name = (
        [],
        [],
        [],
        [],
        [],
        [],
    )
    rule_title, abstract, priority, RIN_status, rule_stage, major = [], [], [], [], [], []
    CFR, legal_authority, legal_deadline_list, action_list = [], [], [], []
    regulatory_flexibility_analysis, statement_of_need = [], []
    summary_of_the_legal_basis, alternatives, federalism = [], [], []
    cost_and_benefits, risks, agency_contact_list = [], [], []

    parser = etree.XMLParser(encoding="UTF-8", recover=True)
    parsed_xml = etree.parse(file_path, parser)
    root = parsed_xml.getroot()

    for child in root:
        agenda_date.append(child.find("PUBLICATION")[0].text)
        RIN.append(child.find("RIN").text)
        agency_code.append(child.find("AGENCY")[0].text)

        if child.find("AGENCY").find("NAME") is not None:
            agency_name.append(child.find("AGENCY").find("NAME").text)
        else:
            agency_name.append("")

        if child.find("PARENT_AGENCY") is not None:
            department_code.append(child.find("PARENT_AGENCY")[0].text)
            department_name.append(child.find("PARENT_AGENCY")[1].text)
        else:
            department_code.append("")
            department_name.append("")

        rule_title.append(child.find("RULE_TITLE").text)
        abstract.append(remove_html_tags(child.find("ABSTRACT").text))

        priority.append(
            child.find("PRIORITY_CATEGORY").text
            if child.find("PRIORITY_CATEGORY") is not None
            else ""
        )
        RIN_status.append(
            child.find("RIN_STATUS").text if child.find("RIN_STATUS") is not None else ""
        )
        rule_stage.append(
            child.find("RULE_STAGE").text if child.find("RULE_STAGE") is not None else ""
        )
        major.append(
            child.find("MAJOR").text if child.find("MAJOR") is not None else ""
        )

        if child.find("CFR_LIST") is not None:
            cfr_text = ""
            for idx in range(len(list(child.find("CFR_LIST")))):
                add = child.find("CFR_LIST")[idx].text
                cfr_text = cfr_text + "; " + str(add) if cfr_text else add
            CFR.append(cfr_text)
        else:
            CFR.append("")

        if child.find("LEGAL_AUTHORITY_LIST") is not None:
            lauth_text = ""
            for idx in range(len(list(child.find("LEGAL_AUTHORITY_LIST")))):
                add = child.find("LEGAL_AUTHORITY_LIST")[idx].text
                lauth_text = lauth_text + "; " + str(add) if lauth_text else add
            legal_authority.append(lauth_text)
        else:
            legal_authority.append("")

        if child.find("LEGAL_DLINE_LIST") is not None:
            legal_deadlines = []
            if child.find("LEGAL_DLINE_LIST").find("LEGAL_DLINE_INFO") is not None:
                for element in child.find("LEGAL_DLINE_LIST").findall(
                    "LEGAL_DLINE_INFO"
                ):
                    lddl_text = (
                        replace_noun(element.find("DLINE_TYPE").text)
                        + "; "
                        + replace_noun(element.find("DLINE_ACTION_STAGE").text)
                        + "; "
                        + replace_noun(element.find("DLINE_DATE").text)
                        + "; "
                        + replace_noun(element.find("DLINE_DESC").text)
                    )
                    legal_deadlines.append(lddl_text)
            legal_deadline_list.append(legal_deadlines)
        else:
            legal_deadline_list.append([])

        if child.find("TIMETABLE_LIST") is not None:
            actions = []
            for element in child.find("TIMETABLE_LIST").findall("TIMETABLE"):
                if element.find("FR_CITATION") is not None:
                    action_text = (
                        element.find("TTBL_ACTION").text
                        + "; "
                        + element.find("TTBL_DATE").text
                        + "; "
                        + element.find("FR_CITATION").text
                    )
                else:
                    if element.find("TTBL_DATE") is not None:
                        action_text = (
                            element.find("TTBL_ACTION").text
                            + "; "
                            + element.find("TTBL_DATE").text
                        )
                    else:
                        action_text = element.find("TTBL_ACTION").text
                actions.append(action_text)
            action_list.append(actions)
        else:
            action_list.append([])

        regulatory_flexibility_analysis.append(
            child.find("RFA_REQUIRED").text
            if child.find("RFA_REQUIRED") is not None
            else ""
        )
        federalism.append(
            child.find("FEDERALISM").text
            if child.find("FEDERALISM") is not None
            else ""
        )

        if child.find("RPLAN_INFO") is not None:
            rplan = child.find("RPLAN_INFO")
            statement_of_need.append(
                rplan.find("STMT_OF_NEED").text
                if rplan.find("STMT_OF_NEED") is not None
                else ""
            )
            summary_of_the_legal_basis.append(
                rplan.find("LEGAL_BASIS").text
                if rplan.find("LEGAL_BASIS") is not None
                else ""
            )
            alternatives.append(
                rplan.find("ALTERNATIVES").text
                if rplan.find("ALTERNATIVES") is not None
                else ""
            )
            cost_and_benefits.append(
                rplan.find("COSTS_AND_BENEFITS").text
                if rplan.find("COSTS_AND_BENEFITS") is not None
                else ""
            )
            risks.append(
                rplan.find("RISKS").text if rplan.find("RISKS") is not None else ""
            )
        else:
            statement_of_need.append("")
            summary_of_the_legal_basis.append("")
            alternatives.append("")
            cost_and_benefits.append("")
            risks.append("")

        if child.find("AGENCY_CONTACT_LIST") is not None:
            agency_text = ""
            contacts = child.find("AGENCY_CONTACT_LIST").findall("CONTACT")
            if contacts:
                for element in contacts:
                    agency_text = ",".join(
                        [t.strip() for t in element.itertext() if t is not None]
                    )
                    agency_text = agency_text.strip(",")
                    agency_text = re.sub(r",,+", ",", agency_text)
            agency_contact_list.append(agency_text)
        else:
            agency_contact_list.append("")

    df_xml = pd.DataFrame(
        list(
            zip(
                agenda_date,
                RIN,
                agency_code,
                agency_name,
                department_code,
                department_name,
                rule_title,
                abstract,
                priority,
                RIN_status,
                rule_stage,
                major,
                CFR,
                legal_authority,
                legal_deadline_list,
                regulatory_flexibility_analysis,
                action_list,
                statement_of_need,
                summary_of_the_legal_basis,
                alternatives,
                federalism,
                cost_and_benefits,
                risks,
                agency_contact_list,
            )
        ),
        columns=[
            "agenda_date",
            "RIN",
            "agency_code",
            "agency_name",
            "department_code",
            "department_name",
            "rule_title",
            "abstract",
            "priority",
            "RIN_status",
            "rule_stage",
            "major",
            "CFR",
            "legal_authority",
            "legal_deadline_list",
            "regulatory_flexibility_analysis",
            "action_list",
            "statement_of_need",
            "summary_of_the_legal_basis",
            "alternatives",
            "federalism",
            "cost_and_benefits",
            "risks",
            "agency_contact_list",
        ],
    )

    lddl_max = max(len(l) for l in df_xml["legal_deadline_list"])
    lddl_cols = [f"legal_deadline{i}" for i in range(1, lddl_max + 1)]
    df_xml[lddl_cols] = pd.DataFrame(
        df_xml["legal_deadline_list"].tolist(), index=df_xml.index
    )
    action_max = max(len(l) for l in df_xml["action_list"])
    action_cols = [f"action{i}" for i in range(1, action_max + 1)]
    df_xml[action_cols] = pd.DataFrame(
        df_xml["action_list"].tolist(), index=df_xml.index
    )
    df_xml.drop(["legal_deadline_list", "action_list"], axis=1, inplace=True)
    return df_xml


def season_transform(season: str) -> str:
    sea_no_option = ["04", "10"]
    if season == "fall":
        return sea_no_option[1]
    if season == "spring":
        return sea_no_option[0]
    raise ValueError('Invalid season: use "spring" or "fall".')

def _cache_file_path(year, season) -> str:
    if year == 2012:
        name = f"REGINFO_RIN_DATA_{year}.csv"
    else:
        name = f"REGINFO_RIN_DATA_{year}{season_transform(season)}.csv"
    return os.path.join(UA_CACHE_DIR, name)


def _resolve_actual_period(year, season):
    """2026 has no Unified Agenda published yet. A "fall" request for it is
    quietly served from the latest published agenda (Fall 2025) instead --
    callers keep labeling output using the year/season the user picked.
    "Spring" isn't offered in the UI for 2026, but multi-year range requests
    can still reach it internally; there's no equivalent to serve, so it
    yields no data (year=None signals "nothing to fetch" to download_file)."""
    if year == 2026:
        return (2025, "fall") if season == "fall" else (None, None)
    return year, season


def _is_live_period(year, season) -> bool:
    """True if (year, season) is the currently in-progress agenda, which
    reginfo.gov may still revise. If we can't confirm it's closed, treat it
    as live so we never persist a possibly-incomplete file to disk."""
    try:
        latest_year, latest_season = get_latest_year_season()
    except Exception:
        return True
    return year == latest_year and season == latest_season


@st.cache_data(ttl=3600, show_spinner=False)
def download_file(
    year, season, directory, _status_callback: Optional[callable] = None
) -> Optional[pd.DataFrame]:
    """Download a Unified Agenda XML, parse it, and return the resulting
    DataFrame. Closed year/seasons are read from / saved to UA_CACHE_DIR on
    disk, so repeat requests (including after an app restart) skip the
    network fetch and XML parse. The in-progress agenda is never cached to
    disk. `@st.cache_data` additionally keeps results in memory for the
    current process, so repeat requests within an hour are instant."""
    year, season = _resolve_actual_period(year, season)
    if year is None:
        return None
    live = _is_live_period(year, season)
    cache_path = _cache_file_path(year, season)

    if not live and os.path.exists(cache_path):
        try:
            df = pd.read_csv(cache_path)
            if _status_callback:
                _status_callback(f"{os.path.basename(cache_path)} loaded from cache.")
            return df
        except Exception:
            pass  # cached file unreadable -- fall through and re-fetch

    if year == 2012:
        file_name = f"REGINFO_RIN_DATA_{year}.xml"
        file_url = f"https://www.reginfo.gov/public/do/XMLViewFileAction?f=REGINFO_RIN_DATA_{year}.xml"
    else:
        season_no = season_transform(season)
        file_name = f"REGINFO_RIN_DATA_{year}{season_no}.xml"
        file_url = f"https://www.reginfo.gov/public/do/XMLViewFileAction?f=REGINFO_RIN_DATA_{year}{season_no}.xml"

    try:
        r = requests.get(file_url, allow_redirects=True)
        r.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=True) as tmp:
            tmp.write(r.content)
            tmp.flush()
            df = xml_to_csv(tmp.name)
        if not live:
            try:
                df.to_csv(cache_path, index=False)
            except Exception:
                pass  # cache write failures (e.g. read-only fs) shouldn't break the app
        if _status_callback:
            _status_callback(f"{file_name} downloaded and parsed.")
        return df
    except Exception as e:
        err_msg = f"ERROR: {file_name} cannot be downloaded or parsed. {e}"
        if _status_callback:
            _status_callback(err_msg)
        return None


def reorder_columns(df):
    action_col = [c for c in df if c.startswith("action")]
    other_col = [c for c in df if not c.startswith("action")]
    return df[other_col + action_col]


@st.cache_data(ttl=3600)
def get_latest_year_season():
    page = requests.get("https://www.reginfo.gov/public/do/eAgendaXmlReport")
    page.raise_for_status()
    soup = BeautifulSoup(page.content, "html.parser")
    newest_file_info = soup.select("li")[0].text[1:-6]
    current_year_season = re.split(r"\s", newest_file_info, 1)
    current_year = int(current_year_season[1])
    current_season = current_year_season[0].lower()
    return current_year, current_season


def collect_ua_data(
    start_year: int,
    start_season: str,
    end_year: int,
    end_season: str,
    directory: None,
    status_callback=None):
    result_dfs = []
    sea_option = ["spring", "fall"]

    def log(msg):
        if status_callback:
            status_callback(msg)

    if end_year == start_year:
        if start_year == 2012:
            df = download_file(start_year, "fall", directory, status_callback)
            if df is None:
                return None
            out_name = f"REGINFO_RIN_DATA_{start_year}.csv"
            df.to_csv(os.path.join(directory, out_name), index=False)
            log(f"Created {out_name}")
            return df

        if start_season == end_season:
            df = download_file(start_year, start_season, directory, status_callback)
            if df is None:
                return None
            season_no = season_transform(start_season)
            out_name = f"REGINFO_RIN_DATA_{start_year}{season_no}.csv"
            df.to_csv(os.path.join(directory, out_name), index=False)
            log(f"Created {out_name}")
            return df

        # both seasons in same year
        df1 = download_file(start_year, start_season, directory, status_callback)
        df2 = download_file(end_year, end_season, directory, status_callback)
        if df1 is None or df2 is None:
            return None
        df = pd.concat([df1, df2], ignore_index=True)
        df = reorder_columns(df)
        out_name = f"REGINFO_RIN_DATA_{start_year}{start_season}&{end_season}.csv"
        df.to_csv(os.path.join(directory, out_name), index=False)
        log(f"Created {out_name}")
        return df

    # Multiple years
    if start_year == 2012:
        result_dfs.append(download_file(start_year, "fall", directory, status_callback))
    else:
        if start_season == "fall":
            result_dfs.append(download_file(start_year, start_season, directory, status_callback))
        else:
            for s in sea_option:
                result_dfs.append(download_file(start_year, s, directory, status_callback))

    for year in range(start_year + 1, end_year):
        if year == 2012:
            result_dfs.append(download_file(year, "fall", directory, status_callback))
        else:
            for s in sea_option:
                result_dfs.append(download_file(year, s, directory, status_callback))

    if end_year == 2012:
        result_dfs.append(download_file(end_year, "fall", directory, status_callback))
    else:
        if end_season == "spring":
            result_dfs.append(download_file(end_year, end_season, directory, status_callback))
        else:
            for s in sea_option:
                result_dfs.append(download_file(end_year, s, directory, status_callback))

    # Filter out failed downloads
    result_dfs = [d for d in result_dfs if d is not None]
    if not result_dfs:
        return None

    df = pd.concat(result_dfs, ignore_index=True)
    # A range spanning 2025-2026 can pull Fall 2025 twice (once as the tail
    # end of 2025, once as 2026's stand-in) -- collapse exact-duplicate rows.
    df = df.drop_duplicates()
    df = reorder_columns(df)
    out_name = f"REGINFO_RIN_DATA_{start_year}{start_season}-{end_year}{end_season}.csv"
    df.to_csv(os.path.join(directory, out_name), index=False)
    log(f"Created {out_name}")
    return df
