"""Real vs. Nominal Exchange Rate Explorer (IMF CPI + exchange-rate data).
 
Run:  streamlit run app.py
 
Definitions
-----------
S(t)   = units of Country 2 currency per 1 unit of Country 1 currency
P1, P2 = monthly CPI (index) of Country 1 and Country 2
RER(t) = S(t) * P1(t) / P2(t)
RER*   = mean of RER(t) over valid months in the selected sample
Real Index(t) = 100 * RER(t) / RER*
"""
 
from __future__ import annotations
 
import io
import re
from typing import Optional
 
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots
 
# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
IMF_BASE = "https://api.imf.org/external/sdmx/3.0"
CPI_FLOW = "IMF.STA/CPI"      # CPI dataflow (agency/id)
ER_FLOW = "IMF.STA/ER"        # Exchange-rate dataflow (agency/id)
START_PERIOD = "1976-01"
HEADERS_CSV = {"Accept": "application/vnd.sdmx.data+csv;version=2.0.0"}
HEADERS_JSON = {"Accept": "application/vnd.sdmx.data+json;version=2.0.0"}
TIMEOUT = 60
 
# IMF member countries (ISO3 -> name) plus the Euro area (G163).
COUNTRIES: dict[str, str] = {
    "AFG": "Afghanistan", "ALB": "Albania", "DZA": "Algeria", "AGO": "Angola",
    "ATG": "Antigua and Barbuda", "ARG": "Argentina", "ARM": "Armenia",
    "ABW": "Aruba", "AUS": "Australia", "AUT": "Austria", "AZE": "Azerbaijan",
    "BHS": "Bahamas, The", "BHR": "Bahrain", "BGD": "Bangladesh",
    "BRB": "Barbados", "BLR": "Belarus", "BEL": "Belgium", "BLZ": "Belize",
    "BEN": "Benin", "BTN": "Bhutan", "BOL": "Bolivia",
    "BIH": "Bosnia and Herzegovina", "BWA": "Botswana", "BRA": "Brazil",
    "BRN": "Brunei Darussalam", "BGR": "Bulgaria", "BFA": "Burkina Faso",
    "BDI": "Burundi", "CPV": "Cabo Verde", "KHM": "Cambodia", "CMR": "Cameroon",
    "CAN": "Canada", "CAF": "Central African Republic", "TCD": "Chad",
    "CHL": "Chile", "CHN": "China (P.R. Mainland)", "COL": "Colombia",
    "COM": "Comoros", "COD": "Congo, Dem. Rep. of the", "COG": "Congo, Rep. of",
    "CRI": "Costa Rica", "CIV": "Côte d'Ivoire", "HRV": "Croatia",
    "CYP": "Cyprus", "CZE": "Czech Republic", "DNK": "Denmark",
    "DJI": "Djibouti", "DMA": "Dominica", "DOM": "Dominican Republic",
    "ECU": "Ecuador", "EGY": "Egypt", "SLV": "El Salvador",
    "GNQ": "Equatorial Guinea", "ERI": "Eritrea", "EST": "Estonia",
    "SWZ": "Eswatini", "ETH": "Ethiopia", "FJI": "Fiji", "FIN": "Finland",
    "FRA": "France", "GAB": "Gabon", "GMB": "Gambia, The", "GEO": "Georgia",
    "DEU": "Germany", "GHA": "Ghana", "GRC": "Greece", "GRD": "Grenada",
    "GTM": "Guatemala", "GIN": "Guinea", "GNB": "Guinea-Bissau", "GUY": "Guyana",
    "HTI": "Haiti", "HND": "Honduras", "HKG": "Hong Kong SAR", "HUN": "Hungary",
    "ISL": "Iceland", "IND": "India", "IDN": "Indonesia", "IRN": "Iran",
    "IRQ": "Iraq", "IRL": "Ireland", "ISR": "Israel", "ITA": "Italy",
    "JAM": "Jamaica", "JPN": "Japan", "JOR": "Jordan", "KAZ": "Kazakhstan",
    "KEN": "Kenya", "KIR": "Kiribati", "KOR": "Korea, Rep. of",
    "XKX": "Kosovo", "KWT": "Kuwait", "KGZ": "Kyrgyz Republic",
    "LAO": "Lao P.D.R.", "LVA": "Latvia", "LBN": "Lebanon", "LSO": "Lesotho",
    "LBR": "Liberia", "LBY": "Libya", "LTU": "Lithuania", "LUX": "Luxembourg",
    "MAC": "Macao SAR", "MDG": "Madagascar", "MWI": "Malawi", "MYS": "Malaysia",
    "MDV": "Maldives", "MLI": "Mali", "MLT": "Malta", "MHL": "Marshall Islands",
    "MRT": "Mauritania", "MUS": "Mauritius", "MEX": "Mexico",
    "FSM": "Micronesia, Fed. States of", "MDA": "Moldova", "MNG": "Mongolia",
    "MNE": "Montenegro", "MAR": "Morocco", "MOZ": "Mozambique", "MMR": "Myanmar",
    "NAM": "Namibia", "NRU": "Nauru", "NPL": "Nepal", "NLD": "Netherlands",
    "NZL": "New Zealand", "NIC": "Nicaragua", "NER": "Niger", "NGA": "Nigeria",
    "MKD": "North Macedonia", "NOR": "Norway", "OMN": "Oman", "PAK": "Pakistan",
    "PLW": "Palau", "PAN": "Panama", "PNG": "Papua New Guinea", "PRY": "Paraguay",
    "PER": "Peru", "PHL": "Philippines", "POL": "Poland", "PRT": "Portugal",
    "QAT": "Qatar", "ROU": "Romania", "RUS": "Russian Federation", "RWA": "Rwanda",
    "WSM": "Samoa", "SMR": "San Marino", "STP": "São Tomé and Príncipe",
    "SAU": "Saudi Arabia", "SEN": "Senegal", "SRB": "Serbia", "SYC": "Seychelles",
    "SLE": "Sierra Leone", "SGP": "Singapore", "SVK": "Slovak Republic",
    "SVN": "Slovenia", "SLB": "Solomon Islands", "SOM": "Somalia",
    "ZAF": "South Africa", "SSD": "South Sudan", "ESP": "Spain",
    "LKA": "Sri Lanka", "KNA": "St. Kitts and Nevis", "LCA": "St. Lucia",
    "VCT": "St. Vincent and the Grenadines", "SDN": "Sudan", "SUR": "Suriname",
    "SWE": "Sweden", "CHE": "Switzerland", "SYR": "Syria", "TWN": "Taiwan",
    "TJK": "Tajikistan", "TZA": "Tanzania", "THA": "Thailand",
    "TLS": "Timor-Leste", "TGO": "Togo", "TON": "Tonga",
    "TTO": "Trinidad and Tobago", "TUN": "Tunisia", "TUR": "Türkiye",
    "TKM": "Turkmenistan", "TUV": "Tuvalu", "UGA": "Uganda", "UKR": "Ukraine",
    "ARE": "United Arab Emirates", "GBR": "United Kingdom",
    "USA": "United States", "URY": "Uruguay", "UZB": "Uzbekistan",
    "VUT": "Vanuatu", "VEN": "Venezuela", "VNM": "Vietnam",
    "YEM": "Yemen", "ZMB": "Zambia", "ZWE": "Zimbabwe",
    "G163": "Euro area",
}
LABEL_TO_CODE = {f"{name} ({code})": code for code, name in COUNTRIES.items()}
LABELS = sorted(LABEL_TO_CODE, key=lambda s: s.lower())
 
 
# --------------------------------------------------------------------------- #
# IMF data access
# --------------------------------------------------------------------------- #
def _period_to_ts(p: str) -> Optional[pd.Timestamp]:
    """Convert '1990-M03', '1990-03' or '1990-03-01' to a month-start Timestamp."""
    p = str(p).strip()
    m = re.match(r"^(\d{4})-?M?(\d{1,2})", p)
    if not m:
        return None
    y, mo = int(m.group(1)), int(m.group(2))
    if not 1 <= mo <= 12:
        return None
    return pd.Timestamp(year=y, month=mo, day=1)
 
 
def _parse_csv(text: str) -> pd.Series:
    df = pd.read_csv(io.StringIO(text))
    cols = {c.upper(): c for c in df.columns}
    tcol = cols.get("TIME_PERIOD")
    vcol = cols.get("OBS_VALUE")
    if tcol is None or vcol is None:
        raise ValueError("Unexpected CSV layout from IMF API.")
    out = pd.DataFrame({
        "date": df[tcol].map(_period_to_ts),
        "value": pd.to_numeric(df[vcol], errors="coerce"),
    }).dropna()
    # If several series come back, keep the first one only.
    return out.drop_duplicates("date").set_index("date")["value"].sort_index()
 
 
def _parse_sdmx_json(payload: dict) -> pd.Series:
    data = payload.get("data", payload)
    ds = data["dataSets"][0]
    structure = data["structures"][0] if "structures" in data else data["structure"]
    obs_dims = structure["dimensions"]["observation"]
    time_dim = next(d for d in obs_dims if d.get("id") == "TIME_PERIOD")
    periods = [v.get("id") or v.get("value") for v in time_dim["values"]]
    series = next(iter(ds["series"].values()))
    rows = {}
    for idx, obs in series["observations"].items():
        ts = _period_to_ts(periods[int(idx)])
        try:
            val = float(obs[0])
        except (TypeError, ValueError):
            continue
        if ts is not None:
            rows[ts] = val
    return pd.Series(rows, dtype=float).sort_index()
 
 
def _fetch(flow: str, key: str) -> pd.Series:
    """Fetch one monthly series; returns an empty Series if unavailable."""
    url = f"{IMF_BASE}/data/dataflow/{flow}/+/{key}"
    params = {"c[TIME_PERIOD]": f"ge:{START_PERIOD}"}
    last_err: Optional[Exception] = None
    for headers, parser in ((HEADERS_CSV, "csv"), (HEADERS_JSON, "json")):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
            if r.status_code == 404:
                return pd.Series(dtype=float)
            r.raise_for_status()
            s = _parse_csv(r.text) if parser == "csv" else _parse_sdmx_json(r.json())
            return s[s.index >= pd.Timestamp(START_PERIOD + "-01")]
        except Exception as exc:  # try the next format
            last_err = exc
    raise RuntimeError(f"IMF request failed for {key}: {last_err}")
 
 
@st.cache_data(show_spinner=False, ttl=24 * 3600)
def load_cpi(code: str) -> pd.Series:
    return _fetch(CPI_FLOW, f"{code}.CPI._T.IX.M")
 
 
@st.cache_data(show_spinner=False, ttl=24 * 3600)
def load_xdc_usd(code: str) -> pd.Series:
    """Local currency units per USD (period average)."""
    return _fetch(ER_FLOW, f"{code}.XDC_USD.PA_RT.M")
 
 
def build_dataset(c1: str, c2: str) -> pd.DataFrame:
    """Monthly panel with P1, P2, S and RER for the full available history."""
    p1, p2 = load_cpi(c1), load_cpi(c2)
    x1, x2 = load_xdc_usd(c1), load_xdc_usd(c2)
 
    # The US dollar is the IMF numeraire: its rate is 1 by definition.
    if c1 == "USA" and x1.empty:
        x1 = pd.Series(1.0, index=p1.index)
    if c2 == "USA" and x2.empty:
        x2 = pd.Series(1.0, index=p2.index)
 
    df = pd.concat({"P1": p1, "P2": p2, "XDC1_per_USD": x1, "XDC2_per_USD": x2}, axis=1)
    df = df.sort_index()
    # S = units of C2 per 1 unit of C1 = (C2 per USD) / (C1 per USD)
    df["S"] = df["XDC2_per_USD"] / df["XDC1_per_USD"]
    df["RER"] = df["S"] * df["P1"] / df["P2"]
    df.index.name = "date"
    return df
 
 
# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="Real & Nominal Exchange Rates", layout="wide")
st.title("Real & Nominal Exchange Rate Explorer")
st.caption(
    "Source: IMF (CPI and period-average exchange rates, monthly, from Jan 1976 where available). "
    "S(t) = Country 2 currency units per 1 unit of Country 1 currency. "
    "RER(t) = S(t) × P1(t) / P2(t)."
)
 
col_a, col_b = st.columns(2)
with col_a:
    l1 = st.selectbox("Country 1 (base currency)", LABELS,
                      index=LABELS.index("United States (USA)"))
with col_b:
    l2 = st.selectbox("Country 2 (quote currency)", LABELS,
                      index=LABELS.index("Euro area (G163)"))
c1, c2 = LABEL_TO_CODE[l1], LABEL_TO_CODE[l2]
 
if c1 == c2:
    st.warning("Please choose two different countries.")
    st.stop()
 
try:
    with st.spinner("Fetching data from the IMF…"):
        data = build_dataset(c1, c2)
except Exception as exc:
    st.error(f"Could not retrieve IMF data: {exc}")
    st.stop()
 
valid = data.dropna(subset=["S", "P1", "P2", "RER"])
if valid.empty:
    missing = []
    if load_cpi(c1).empty:
        missing.append(f"CPI for {COUNTRIES[c1]}")
    if load_cpi(c2).empty:
        missing.append(f"CPI for {COUNTRIES[c2]}")
    if load_xdc_usd(c1).empty and c1 != "USA":
        missing.append(f"exchange rate for {COUNTRIES[c1]}")
    if load_xdc_usd(c2).empty and c2 != "USA":
        missing.append(f"exchange rate for {COUNTRIES[c2]}")
    st.error(
        "No overlapping valid months for this pair. "
        + ("Missing from the IMF: " + "; ".join(missing) + "." if missing
           else "The series do not overlap in time.")
    )
    st.stop()
 
months = list(pd.period_range(valid.index.min(), valid.index.max(), freq="M"))
month_labels = [m.strftime("%Y-%m") for m in months]
start_lbl, end_lbl = st.select_slider(
    "Sample period (start – end month)",
    options=month_labels,
    value=(month_labels[0], month_labels[-1]),
)
start, end = pd.Timestamp(start_lbl + "-01"), pd.Timestamp(end_lbl + "-01")
 
sample = data.loc[(data.index >= start) & (data.index <= end)].copy()
sample_valid = sample.dropna(subset=["S", "P1", "P2", "RER"])
if sample_valid.empty:
    st.error("No valid observations in the selected sample period.")
    st.stop()
 
rer_star = sample_valid["RER"].mean()  # recalculated whenever dates change
sample["RealIndex"] = 100 * sample["RER"] / rer_star
 
m1, m2, m3 = st.columns(3)
m1.metric("RER* (sample mean)", f"{rer_star:,.4f}")
m2.metric("Valid months", f"{len(sample_valid):,}")
m3.metric("Latest Real Index", f"{sample_valid['RER'].iloc[-1] / rer_star * 100:,.1f}")
 
view = st.radio("Series to plot", ["Real", "Nominal", "Both"], horizontal=True)
 
cur1 = f"{COUNTRIES[c1]}"
cur2 = f"{COUNTRIES[c2]}"
nom_title = f"Nominal S(t): {cur2} currency units per 1 {cur1} currency unit"
real_title = f"Real Index (100 = sample mean RER*)"
 
plot_df = sample.dropna(subset=["S", "RealIndex"])
fig = make_subplots(specs=[[{"secondary_y": view == "Both"}]])
if view in ("Real", "Both"):
    fig.add_trace(
        go.Scatter(x=plot_df.index, y=plot_df["RealIndex"], name="Real Index",
                   mode="lines", line=dict(color="#1f77b4")),
        secondary_y=False,
    )
if view in ("Nominal", "Both"):
    fig.add_trace(
        go.Scatter(x=plot_df.index, y=plot_df["S"], name="Nominal S(t)",
                   mode="lines", line=dict(color="#d62728")),
        secondary_y=(view == "Both"),
    )
if view in ("Real", "Both"):
    fig.add_hline(y=100, line_dash="dot", line_color="gray",
                  secondary_y=False)
if view == "Both":
    fig.update_yaxes(title_text=real_title, secondary_y=False)
    fig.update_yaxes(title_text=nom_title, secondary_y=True, showgrid=False)
elif view == "Real":
    fig.update_yaxes(title_text=real_title)
else:
    fig.update_yaxes(title_text=nom_title)
fig.update_xaxes(title_text="Month")
fig.update_layout(height=520, hovermode="x unified",
                  legend=dict(orientation="h", y=1.08),
                  margin=dict(l=10, r=10, t=30, b=10))
st.plotly_chart(fig, use_container_width=True)
 
# Gap notice
n_months = len(pd.period_range(start, end, freq="M"))
if len(sample_valid) < n_months:
    st.info(f"{n_months - len(sample_valid)} of {n_months} months in the window lack "
            "data for at least one series and are excluded from RER* and the charts.")
 
# CSV download
out = sample.reset_index().rename(columns={
    "date": "Month",
    "P1": f"CPI_{c1}",
    "P2": f"CPI_{c2}",
    "XDC1_per_USD": f"{c1}_units_per_USD",
    "XDC2_per_USD": f"{c2}_units_per_USD",
    "S": f"S_{c2}_per_{c1}",
    "RER": "RER",
    "RealIndex": "Real_Index",
})
out["Month"] = out["Month"].dt.strftime("%Y-%m")
out["RER_star"] = rer_star
out["Valid_Observation"] = sample[["S", "P1", "P2", "RER"]].notna().all(axis=1).values
st.download_button(
    "Download CSV (selected sample period)",
    data=out.to_csv(index=False).encode("utf-8"),
    file_name=f"rer_{c1}_{c2}_{start_lbl}_{end_lbl}.csv",
    mime="text/csv",
)
with st.expander("Preview data"):
    st.dataframe(out, use_container_width=True)
 
