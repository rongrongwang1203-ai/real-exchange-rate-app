"""
Real vs Nominal Exchange Rate Explorer (IMF data)
 
Streamlit app that compares the nominal exchange rate S(t) and the real exchange
rate index between two countries (or the Euro area) using IMF SDMX 3.0 data.
 
Run:  streamlit run app.py
"""
 
from __future__ import annotations
 
import io
from datetime import date
 
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots
 
# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
IMF_BASE = "https://api.imf.org/external/sdmx/3.0"
AGENCY = "IMF.STA"
CPI_FLOW = "CPI"      # dataflow id for consumer price indices
FX_FLOW = "ER"        # dataflow id for exchange rates
FLOW_VERSION = "+"    # "+" = latest stable version (SDMX 3.0 semantics)
CPI_KEY = "{code}.CPI._T.IX.M"
FX_KEY = "{code}.XDC_USD.PA_RT.M"
START_MONTH = "1976-01"
REQUEST_TIMEOUT = 60
CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours
 
# IMF country / area codes. The Euro area uses the IMF aggregate code G163.
# Coverage is checked live: a country with no CPI or FX series is reported to the user.
COUNTRIES: dict[str, str] = {
    "AFG": "Afghanistan", "ALB": "Albania", "DZA": "Algeria", "AGO": "Angola",
    "ATG": "Antigua and Barbuda", "ARG": "Argentina", "ARM": "Armenia", "ABW": "Aruba",
    "AUS": "Australia", "AUT": "Austria", "AZE": "Azerbaijan", "BHS": "Bahamas, The",
    "BHR": "Bahrain", "BGD": "Bangladesh", "BRB": "Barbados", "BLR": "Belarus",
    "BEL": "Belgium", "BLZ": "Belize", "BEN": "Benin", "BTN": "Bhutan",
    "BOL": "Bolivia", "BIH": "Bosnia and Herzegovina", "BWA": "Botswana", "BRA": "Brazil",
    "BRN": "Brunei Darussalam", "BGR": "Bulgaria", "BFA": "Burkina Faso", "BDI": "Burundi",
    "CPV": "Cabo Verde", "KHM": "Cambodia", "CMR": "Cameroon", "CAN": "Canada",
    "CAF": "Central African Republic", "TCD": "Chad", "CHL": "Chile", "CHN": "China (P.R.: Mainland)",
    "HKG": "China (P.R.: Hong Kong)", "MAC": "China (P.R.: Macao)", "COL": "Colombia",
    "COM": "Comoros", "COD": "Congo, Dem. Rep. of the", "COG": "Congo, Rep. of",
    "CRI": "Costa Rica", "CIV": "Côte d'Ivoire", "HRV": "Croatia", "CYP": "Cyprus",
    "CZE": "Czech Republic", "DNK": "Denmark", "DJI": "Djibouti", "DMA": "Dominica",
    "DOM": "Dominican Republic", "ECU": "Ecuador", "EGY": "Egypt", "SLV": "El Salvador",
    "GNQ": "Equatorial Guinea", "ERI": "Eritrea", "EST": "Estonia", "SWZ": "Eswatini",
    "ETH": "Ethiopia", "FJI": "Fiji", "FIN": "Finland", "FRA": "France", "GAB": "Gabon",
    "GMB": "Gambia, The", "GEO": "Georgia", "DEU": "Germany", "GHA": "Ghana",
    "GRC": "Greece", "GRD": "Grenada", "GTM": "Guatemala", "GIN": "Guinea",
    "GNB": "Guinea-Bissau", "GUY": "Guyana", "HTI": "Haiti", "HND": "Honduras",
    "HUN": "Hungary", "ISL": "Iceland", "IND": "India", "IDN": "Indonesia",
    "IRN": "Iran", "IRQ": "Iraq", "IRL": "Ireland", "ISR": "Israel", "ITA": "Italy",
    "JAM": "Jamaica", "JPN": "Japan", "JOR": "Jordan", "KAZ": "Kazakhstan", "KEN": "Kenya",
    "KIR": "Kiribati", "KOR": "Korea, Republic of", "XKX": "Kosovo", "KWT": "Kuwait",
    "KGZ": "Kyrgyz Republic", "LAO": "Lao P.D.R.", "LVA": "Latvia", "LBN": "Lebanon",
    "LSO": "Lesotho", "LBR": "Liberia", "LBY": "Libya", "LTU": "Lithuania",
    "LUX": "Luxembourg", "MDG": "Madagascar", "MWI": "Malawi", "MYS": "Malaysia",
    "MDV": "Maldives", "MLI": "Mali", "MLT": "Malta", "MRT": "Mauritania",
    "MUS": "Mauritius", "MEX": "Mexico", "FSM": "Micronesia", "MDA": "Moldova",
    "MNG": "Mongolia", "MNE": "Montenegro", "MAR": "Morocco", "MOZ": "Mozambique",
    "MMR": "Myanmar", "NAM": "Namibia", "NPL": "Nepal", "NLD": "Netherlands",
    "NZL": "New Zealand", "NIC": "Nicaragua", "NER": "Niger", "NGA": "Nigeria",
    "MKD": "North Macedonia", "NOR": "Norway", "OMN": "Oman", "PAK": "Pakistan",
    "PLW": "Palau", "PAN": "Panama", "PNG": "Papua New Guinea", "PRY": "Paraguay",
    "PER": "Peru", "PHL": "Philippines", "POL": "Poland", "PRT": "Portugal",
    "QAT": "Qatar", "ROU": "Romania", "RUS": "Russian Federation", "RWA": "Rwanda",
    "WSM": "Samoa", "STP": "São Tomé and Príncipe", "SAU": "Saudi Arabia", "SEN": "Senegal",
    "SRB": "Serbia", "SYC": "Seychelles", "SLE": "Sierra Leone", "SGP": "Singapore",
    "SVK": "Slovak Republic", "SVN": "Slovenia", "SLB": "Solomon Islands", "SOM": "Somalia",
    "ZAF": "South Africa", "SSD": "South Sudan", "ESP": "Spain", "LKA": "Sri Lanka",
    "KNA": "St. Kitts and Nevis", "LCA": "St. Lucia", "VCT": "St. Vincent and the Grenadines",
    "SDN": "Sudan", "SUR": "Suriname", "SWE": "Sweden", "CHE": "Switzerland",
    "SYR": "Syria", "TWN": "Taiwan Province of China", "TJK": "Tajikistan", "TZA": "Tanzania",
    "THA": "Thailand", "TLS": "Timor-Leste", "TGO": "Togo", "TON": "Tonga",
    "TTO": "Trinidad and Tobago", "TUN": "Tunisia", "TUR": "Türkiye", "TKM": "Turkmenistan",
    "UGA": "Uganda", "UKR": "Ukraine", "ARE": "United Arab Emirates", "GBR": "United Kingdom",
    "USA": "United States", "URY": "Uruguay", "UZB": "Uzbekistan", "VUT": "Vanuatu",
    "VEN": "Venezuela", "VNM": "Vietnam", "YEM": "Yemen", "ZMB": "Zambia", "ZWE": "Zimbabwe",
    "G163": "Euro area",
}
 
 
class IMFError(Exception):
    """Raised for IMF API failures that should be shown to the user."""
 
 
# --------------------------------------------------------------------------- #
# Data access
# --------------------------------------------------------------------------- #
def _parse_period(p: str) -> pd.Timestamp | None:
    """Parse IMF monthly period strings like '1976-M01' or '1976-01' to month start."""
    p = str(p).strip()
    try:
        if "-M" in p:
            y, m = p.split("-M")
            return pd.Timestamp(year=int(y), month=int(m), day=1)
        return pd.Period(p, freq="M").to_timestamp()
    except Exception:
        return None
 
 
@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_imf_series(flow: str, key: str) -> pd.Series:
    """
    Fetch one monthly series from the IMF SDMX 3.0 API.
 
    Returns a float Series indexed by month-start timestamps (possibly empty if the IMF
    has no data for the key). Raises IMFError on network / server problems.
    Results are cached; exceptions are not cached.
    """
    url = f"{IMF_BASE}/data/dataflow/{AGENCY}/{flow}/{FLOW_VERSION}/{key}"
    params = {"c[TIME_PERIOD]": f"ge:{START_MONTH}"}
    headers = {"Accept": "application/vnd.sdmx.data+csv;version=2.0.0, text/csv;q=0.8"}
 
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.Timeout as e:
        raise IMFError(f"The IMF API timed out while requesting {key} ({flow}). Please retry.") from e
    except requests.exceptions.ConnectionError as e:
        raise IMFError(
            f"Could not connect to the IMF API ({IMF_BASE}). Check your internet connection "
            f"or whether api.imf.org is reachable from your network."
        ) from e
    except requests.exceptions.RequestException as e:
        raise IMFError(f"Unexpected network error requesting {key}: {e}") from e
 
    if resp.status_code == 404:
        # SDMX convention: 404 = no data for this key.
        return pd.Series(dtype="float64", name=key)
    if resp.status_code == 429:
        raise IMFError("The IMF API is rate-limiting requests (HTTP 429). Wait a minute and retry.")
    if resp.status_code >= 500:
        raise IMFError(f"The IMF API returned a server error (HTTP {resp.status_code}) for {key}. Try again later.")
    if resp.status_code != 200:
        snippet = resp.text[:300].replace("\n", " ")
        raise IMFError(
            f"The IMF API rejected the request for {key} (HTTP {resp.status_code}). "
            f"URL: {resp.url} — Response: {snippet}"
        )
 
    try:
        df = pd.read_csv(io.StringIO(resp.text))
    except Exception as e:
        raise IMFError(f"Could not parse the IMF response for {key}: {e}") from e
    if df.empty:
        return pd.Series(dtype="float64", name=key)
 
    cols = {c.upper().strip(): c for c in df.columns}
    if "TIME_PERIOD" not in cols or "OBS_VALUE" not in cols:
        raise IMFError(
            f"Unexpected IMF response format for {key}: columns were {list(df.columns)[:10]}. "
            "The API schema may have changed."
        )
 
    out = pd.DataFrame(
        {
            "date": df[cols["TIME_PERIOD"]].map(_parse_period),
            "value": pd.to_numeric(df[cols["OBS_VALUE"]], errors="coerce"),
        }
    ).dropna(subset=["date"])
    out = out.drop_duplicates(subset="date", keep="first").sort_values("date")
    s = out.set_index("date")["value"].astype("float64")
    s.name = key
    return s
 
 
def get_country_data(code: str) -> pd.DataFrame:
    """CPI (index) and FX (local currency per USD) for one country, monthly."""
    cpi = fetch_imf_series(CPI_FLOW, CPI_KEY.format(code=code))
    if code == "USA":
        # The IMF has no XDC_USD series for the US itself; USD per USD is 1 by definition.
        idx = cpi.index if len(cpi) else pd.DatetimeIndex([])
        fx = pd.Series(1.0, index=idx)
    else:
        fx = fetch_imf_series(FX_FLOW, FX_KEY.format(code=code))
    return pd.DataFrame({"cpi": cpi, "fx_lcu_per_usd": fx})
 
 
# --------------------------------------------------------------------------- #
# Calculations
# --------------------------------------------------------------------------- #
def build_panel(d1: pd.DataFrame, d2: pd.DataFrame) -> pd.DataFrame:
    """Merge both countries on a complete monthly index and compute S and RER."""
    all_idx = d1.index.union(d2.index)
    if len(all_idx) == 0:
        return pd.DataFrame()
    end = max(all_idx.max(), pd.Timestamp(START_MONTH))
    full = pd.date_range(START_MONTH, end, freq="MS")
    p = pd.DataFrame(index=full)
    p.index.name = "date"
    p["cpi_1"] = d1["cpi"].reindex(full)
    p["cpi_2"] = d2["cpi"].reindex(full)
    p["fx_1_lcu_per_usd"] = d1["fx_lcu_per_usd"].reindex(full)
    p["fx_2_lcu_per_usd"] = d2["fx_lcu_per_usd"].reindex(full)
 
    # S = units of Country 2 currency per 1 unit of Country 1 currency
    #   = (C2 per USD) / (C1 per USD)
    p["S"] = p["fx_2_lcu_per_usd"] / p["fx_1_lcu_per_usd"]
    p["RER"] = p["S"] * p["cpi_1"] / p["cpi_2"]
 
    reasons = pd.DataFrame(index=full)
    reasons["missing CPI 1"] = ~(p["cpi_1"] > 0)
    reasons["missing CPI 2"] = ~(p["cpi_2"] > 0)
    reasons["missing FX 1"] = ~(p["fx_1_lcu_per_usd"] > 0)
    reasons["missing FX 2"] = ~(p["fx_2_lcu_per_usd"] > 0)
    p["valid"] = ~reasons.any(axis=1)
    p["invalid_reason"] = reasons.apply(lambda r: "; ".join(r.index[r.values]), axis=1)
    # Blank out derived values for invalid months so they never leak into stats/plots.
    p.loc[~p["valid"], ["S", "RER"]] = float("nan")
    return p
 
 
def apply_window(panel: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    w = panel.loc[(panel.index >= start) & (panel.index <= end)].copy()
    rer_star = w.loc[w["valid"], "RER"].mean() if w["valid"].any() else float("nan")
    w["RER_star"] = rer_star
    w["real_index"] = 100 * w["RER"] / rer_star
    return w
 
 
# --------------------------------------------------------------------------- #
# UI helpers
# --------------------------------------------------------------------------- #
def label(code: str) -> str:
    return f"{COUNTRIES[code]} ({code})"
 
 
def make_chart(w: pd.DataFrame, view: str, n1: str, n2: str) -> go.Figure:
    nominal_name = f"Nominal S(t): {n2} per 1 {n1}"
    real_name = "Real Index (RER* = 100)"
    v = w[w["valid"]]
 
    if view == "Both":
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=v.index, y=v["S"], name=nominal_name, mode="lines"), secondary_y=False)
        fig.add_trace(go.Scatter(x=v.index, y=v["real_index"], name=real_name, mode="lines"), secondary_y=True)
        fig.update_yaxes(title_text=f"Nominal S ({n2} per 1 {n1})", secondary_y=False)
        fig.update_yaxes(title_text="Real Index (100 = sample average)", secondary_y=True)
        fig.add_hline(y=100, line_dash="dot", line_color="grey", secondary_y=True)
    else:
        fig = go.Figure()
        if view == "Nominal":
            fig.add_trace(go.Scatter(x=v.index, y=v["S"], name=nominal_name, mode="lines"))
            fig.update_yaxes(title_text=f"Nominal S ({n2} per 1 {n1})")
        else:
            fig.add_trace(go.Scatter(x=v.index, y=v["real_index"], name=real_name, mode="lines"))
            fig.update_yaxes(title_text="Real Index (100 = sample average)")
            fig.add_hline(y=100, line_dash="dot", line_color="grey")
 
    fig.update_layout(
        height=520,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    fig.update_xaxes(title_text="Month")
    return fig
 
 
# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #
def main() -> None:
    st.set_page_config(page_title="Real vs Nominal Exchange Rates", layout="wide")
    st.title("Real vs Nominal Exchange Rates")
    st.caption(
        "Source: IMF (SDMX 3.0 API) — monthly CPI and period-average exchange rates. "
        "S(t) = Country 2 currency units per 1 unit of Country 1 currency."
    )
 
    codes = sorted(COUNTRIES, key=lambda c: COUNTRIES[c])
    c1_col, c2_col = st.columns(2)
    with c1_col:
        code1 = st.selectbox("Country 1 (base currency)", codes, index=codes.index("USA"), format_func=label)
    with c2_col:
        code2 = st.selectbox("Country 2 (quote currency)", codes, index=codes.index("G163"), format_func=label)
 
    if code1 == code2:
        st.error("Please choose two different countries/areas.")
        st.stop()
 
    # ---- Fetch ----
    try:
        with st.spinner("Fetching data from the IMF…"):
            d1 = get_country_data(code1)
            d2 = get_country_data(code2)
    except IMFError as e:
        st.error(f"**IMF data request failed.** {e}")
        st.info("You can retry; successful responses are cached, failed ones are not.")
        st.stop()
 
    # ---- Coverage checks ----
    problems = []
    for code, d in ((code1, d1), (code2, d2)):
        if d["cpi"].dropna().empty:
            problems.append(f"{label(code)}: no monthly CPI series found at the IMF.")
        if d["fx_lcu_per_usd"].dropna().empty:
            problems.append(f"{label(code)}: no monthly exchange-rate series (local currency per USD) found at the IMF.")
    if problems:
        st.error("Cannot compute the real exchange rate for this pair:\n\n" + "\n".join(f"- {p}" for p in problems))
        st.stop()
 
    panel = build_panel(d1, d2)
    if not panel["valid"].any():
        st.error("The two countries have no overlapping months with complete CPI and exchange-rate data.")
        st.stop()
 
    # ---- Sample period selector ----
    months = [ts.strftime("%Y-%m") for ts in panel.index]
    valid_months = [ts.strftime("%Y-%m") for ts in panel.index[panel["valid"]]]
    default = (valid_months[0], valid_months[-1])
    st.subheader("Sample period")
    start_s, end_s = st.select_slider(
        "Select start and end month (RER* is recomputed for this window)",
        options=months,
        value=default,
    )
    start, end = pd.Timestamp(start_s + "-01"), pd.Timestamp(end_s + "-01")
 
    w = apply_window(panel, start, end)
    n_total = len(w)
    n_valid = int(w["valid"].sum())
    if n_valid == 0:
        st.error("No valid months in the selected window. Widen the sample period.")
        st.stop()
 
    # ---- Dropped months notice ----
    n_drop = n_total - n_valid
    if n_drop > 0:
        reason_counts = {
            r: int(w["invalid_reason"].str.contains(r).sum())
            for r in ["missing CPI 1", "missing CPI 2", "missing FX 1", "missing FX 2"]
        }
        detail = ", ".join(f"{k}: {v}" for k, v in reason_counts.items() if v)
        first_valid = w.index[w["valid"]].min().strftime("%Y-%m")
        last_valid = w.index[w["valid"]].max().strftime("%Y-%m")
        st.warning(
            f"{n_drop} of {n_total} months in the selected window were dropped because of missing data "
            f"({detail}; a month can have several causes). Valid data run from {first_valid} to {last_valid}. "
            "Dropped months are excluded from RER* and the chart, but appear in the CSV with validity flag = False."
        )
    else:
        st.success(f"All {n_total} months in the window are valid.")
 
    # ---- Metrics ----
    rer_star = float(w["RER_star"].iloc[0])
    m1, m2, m3 = st.columns(3)
    m1.metric("Valid months", f"{n_valid} / {n_total}")
    m2.metric("RER* (sample average RER)", f"{rer_star:,.4f}")
    last_row = w[w["valid"]].iloc[-1]
    m3.metric(f"Latest Real Index ({last_row.name.strftime('%Y-%m')})", f"{last_row['real_index']:.1f}")
 
    # ---- Chart ----
    view = st.radio("Chart view", ["Real", "Nominal", "Both"], horizontal=True, index=2)
    st.plotly_chart(make_chart(w, view, COUNTRIES[code1], COUNTRIES[code2]), use_container_width=True)
    st.caption(
        "Real Index > 100: Country 1's currency is stronger in real terms than its sample average "
        "(Country 1 goods are relatively expensive vs. Country 2). Index < 100: weaker in real terms."
    )
 
    # ---- CSV download ----
    export = w.reset_index().rename(
        columns={
            "date": "month",
            "cpi_1": f"CPI_{code1}",
            "cpi_2": f"CPI_{code2}",
            "fx_1_lcu_per_usd": f"FX_{code1}_LCU_per_USD",
            "fx_2_lcu_per_usd": f"FX_{code2}_LCU_per_USD",
            "S": f"S_{code2}_per_{code1}",
            "RER": "RER",
            "RER_star": "RER_star",
            "real_index": "Real_Index",
            "valid": "valid_flag",
            "invalid_reason": "invalid_reason",
        }
    )
    export["month"] = export["month"].dt.strftime("%Y-%m")
    export.insert(1, "country_1", code1)
    export.insert(2, "country_2", code2)
    csv_bytes = export.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV (all months in window)",
        data=csv_bytes,
        file_name=f"rer_{code1}_{code2}_{start_s}_{end_s}.csv",
        mime="text/csv",
    )
 
    with st.expander("Preview data table"):
        st.dataframe(export, use_container_width=True, hide_index=True)
 
    st.caption(f"Data retrieved {date.today().isoformat()}. API responses are cached for {CACHE_TTL_SECONDS // 3600} hours.")
 
 
if __name__ == "__main__":
    main()
 
