Real vs Nominal Exchange Rates (IMF data)

A Streamlit app that compares the nominal exchange rate and the real exchange rate index for any two IMF countries (or the Euro area) using monthly data from the IMF SDMX 3.0 API.

Setup

Requires Python 3.12.

bash
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
Run
bash
streamlit run app.py

The app opens at http://localhost:8501. It needs internet access to https://api.imf.org.

How to use
Pick Country 1 (base currency) and Country 2 (quote currency). The Euro area is IMF code G163.
Choose the sample start and end month. RER* is recomputed whenever the window changes.
Toggle Real / Nominal / Both. "Both" uses two y-axes: nominal S(t) on the left in actual currency units, Real Index on the right.
Download the CSV of every month in the window, including dropped months (flagged invalid).
Data
Series	Dataflow	Key
CPI (index)	IMF.STA:CPI	{ISO3}.CPI._T.IX.M
Exchange rate (period average, local currency per USD)	IMF.STA:ER	{ISO3}.XDC_USD.PA_RT.M

Requests go to https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/{flow}/+/{key} with a c[TIME_PERIOD]=ge:1976-01 filter, requesting SDMX-CSV. The dataflow IDs, version and keys are constants at the top of app.py if the IMF changes them. Responses are cached for 6 hours (st.cache_data); failed requests are not cached.

Formulas

IMF exchange rates are local currency units per 1 USD. With E1, E2 the IMF rates for Country 1 and 2 and P1, P2 their CPIs:

S(t) = E2(t) / E1(t) — units of Country 2 currency per 1 unit of Country 1 currency
RER(t) = S(t) × P1(t) / P2(t)
RER* = mean of RER(t) over valid months in the selected window
Real Index(t) = 100 × RER(t) / RER*

A month is valid only if both CPIs and both exchange rates are present and positive. Invalid months are excluded from RER* and the chart, and the app reports how many were dropped and why. In the CSV they appear with valid_flag = False, an invalid_reason, and blank S / RER / Real Index.

Interpretation: a higher RER means Country 1's goods are relatively more expensive (real appreciation of Country 1's currency) versus its sample average.

CSV columns

month, country_1, country_2, CPI_<c1>, CPI_<c2>, FX_<c1>_LCU_per_USD, FX_<c2>_LCU_per_USD, S_<c2>_per_<c1>, RER, RER_star, Real_Index, valid_flag, invalid_reason

Known data limitations
Coverage varies widely. Many countries lack monthly CPI or exchange rates back to 1976, or have gaps. Only months where all four inputs exist are used.
RER* depends on the window. The Real Index is relative to the selected sample average, not an absolute or long-run equilibrium level. Different windows give different indices.
CPI base years differ by country. This is harmless for the Real Index (the base cancels in the ratio to RER*), but the raw RER level is not comparable across pairs or base-year choices.
United States: the IMF does not publish a USD-per-USD series, so the app sets the US rate to 1.0.
Euro area (G163): CPI and the euro exchange rate begin when the aggregate series begins (euro from 1999 in most cases); earlier months will be dropped. Individual euro members have their own legacy currencies before joining.
Hyperinflation, redenominations and regime changes (e.g. Argentina, Venezuela, Zimbabwe) can create large breaks or unreliable values. Check the chart and CSV.
Exchange rates are period averages (PA_RT), not end-of-period, and CPI is the headline all-items index (_T).
Country list is static. It is built into the app; countries without IMF series show an error rather than being hidden. IMF codes, dataflow versions and data are revised over time, and the SDMX 3.0 endpoint is relatively new, so the response format may change.
Latest months may be missing or revised as the IMF updates.
Troubleshooting
"Could not connect to the IMF API": check network/proxy settings.
HTTP 4xx/5xx errors: the message includes the request URL; open it in a browser to inspect the response. Failures are not cached, so just retry.
No series found: that country has no data for the requested key at the IMF.
