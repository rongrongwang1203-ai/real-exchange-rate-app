Real & Nominal Exchange Rate Explorer

A Streamlit app that pulls monthly CPI and exchange-rate data from the IMF and plots the nominal exchange rate and a real exchange rate index for any two IMF countries (or the Euro area).

Economics
S(t) = units of Country 2 currency per 1 unit of Country 1 currency
P1(t), P2(t) = monthly CPI of Country 1 and Country 2
RER(t) = S(t) × P1(t) / P2(t)
RER* = average of RER(t) over valid months in the selected sample
Real Index(t) = 100 × RER(t) / RER* (recomputed whenever the dates change)
Nominal S(t) is plotted in actual currency units (not normalized)

IMF exchange rates are local-currency units per USD (XDC_USD). The app converts: S = (Country 2 per USD) / (Country 1 per USD). For the United States the rate is set to 1 if the IMF returns no series.

A rising Real Index means Country 1's currency has appreciated in real terms against Country 2's (Country 1 goods have become relatively more expensive).

Data
Series	IMF key	Dataflow
CPI (all items, index)	{ISO3}.CPI._T.IX.M	IMF.STA/CPI
Exchange rate (period average)	{ISO3}.XDC_USD.PA_RT.M	IMF.STA/ER

Base URL: https://api.imf.org/external/sdmx/3.0. Euro area code: G163. Data are requested from January 1976 onward; many countries start later, and some have gaps. Months where any of S, P1, P2 is missing are excluded from RER* and the charts, and the app tells you how many were dropped.

Features
Country 1 / Country 2 selectors (IMF members + Euro area)
Month-range slider for the sample period
Chart modes: Real, Nominal, or Both (dual y-axes)
CSV download of all observations and calculations in the selected window (CPIs, rates per USD, S, RER, Real Index, RER*, validity flag)
Responses cached for 24 hours
Run

Requires Python 3.12.

bash
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
Caveats
Only the IMF endpoint format given in the assignment hints was available to me; I could not test it live. The app requests SDMX-CSV first and falls back to SDMX-JSON, and parses TIME_PERIOD/OBS_VALUE. If the IMF changes dataflow IDs (IMF.STA/CPI, IMF.STA/ER) or the version path, edit the CPI_FLOW / ER_FLOW constants at the top of app.py.
Individual euro-area members report legacy national-currency rates before joining the euro; for a euro-consistent series use the Euro area (G163).
Some countries have discontinued or rebased CPI series, or hyperinflation episodes, so the index can be extreme.
Country list is hard-coded; countries without IMF data show an explanatory error.
