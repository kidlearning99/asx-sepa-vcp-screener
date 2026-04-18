import yfinance as yf
import json, os, time, hashlib, requests, random
from datetime import date, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

NETLIFY_TOKEN   = os.environ.get("NETLIFY_TOKEN", "")
NETLIFY_SITE_ID = os.environ.get("NETLIFY_SITE_ID", "")
MIN_MARKET_CAP  = 100_000_000
SEPA_MIN        = 3
VOL_BREAKOUT    = 1.5
VCP_MIN         = 2

# ── Robust HTTP session ───────────────────────────────────────────────────────
session = requests.Session()
retry = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive"
})

# ── Dynamic ASX ticker fetch ──────────────────────────────────────────────────
def get_all_asx_tickers():
    """Dynamically fetch all ASX-listed tickers from the ASX website."""
    try:
        import io
        import pandas as pd
        url = "https://www.asx.com.au/asx/research/ASXListedCompanies.csv"
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        df = pd.read_csv(io.StringIO(resp.text), skiprows=1)
        col = [c for c in df.columns if 'code' in c.lower() or 'asx' in c.lower()][0]
        tickers = [str(row[col]).strip() + '.AX' for _, row in df.iterrows()
                   if str(row[col]).strip() and len(str(row[col]).strip()) <= 5]
        print(f"Loaded {len(tickers)} ASX tickers from ASX website")
        return tickers
    except Exception as e:
        print(f"Failed to fetch ASX tickers dynamically: {e}")
        return []

ASX_TICKERS = get_all_asx_tickers()

# ── Formatting helpers ────────────────────────────────────────────────────────
def fmt_cap(c):
    if c >= 1e12: return f"${c/1e12:.1f}T"
    if c >= 1e9:  return f"${c/1e9:.1f}B"
    if c >= 1e6:  return f"${c/1e6:.0f}M"
    return f"${c:.0f}"

def fmt_pct(v):
    if v is None: return "—"
    return f"{v:+.1f}%"

def safe_round(v, d=2):
    try: return round(float(v), d)
    except: return None

# ── Fundamental helpers ───────────────────────────────────────────────────────
def _quarterly_revenue_trend(t):
    try:
        import pandas as pd
        fin = t.quarterly_financials
        if fin is None or fin.empty: return None, [], []
        rev_row = [r for r in fin.index if 'revenue' in str(r).lower() or 'total revenue' in str(r).lower()]
        if not rev_row: return None, [], []
        rev = fin.loc[rev_row[0]].dropna().sort_index()
        if len(rev) < 2: return None, list(rev.values), []
        vals = list(rev.values)
        qtrs = [str(d)[:7] for d in rev.index]
        growth = round((vals[-1] / vals[-2] - 1) * 100, 1) if vals[-2] != 0 else None
        return growth, vals, qtrs
    except: return None, [], []

def _quarterly_eps_trend(t):
    try:
        import pandas as pd
        earn = t.quarterly_earnings
        if earn is None or earn.empty: return None, [], []
        eps = earn['EPS'].dropna().sort_index() if 'EPS' in earn.columns else None
        if eps is None or len(eps) < 2: return None, [], []
        vals = list(eps.values)
        qtrs = [str(d)[:7] for d in eps.index]
        growth = round((vals[-1] / abs(vals[-2]) - 1) * 100, 1) if vals[-2] != 0 else None
        return growth, vals, qtrs
    except: return None, [], []

def _fetch_events(t):
    try:
        cal = t.calendar
        next_earnings = next_event_label = next_ex_div = None
        days_to_event = 9999
        today = date.today()

        if cal is not None and not (hasattr(cal, 'empty') and cal.empty):
            if isinstance(cal, dict):
                e = cal.get('Earnings Date') or cal.get('earningsDate')
                if e:
                    ed = e[0] if isinstance(e, list) else e
                    if hasattr(ed, 'date'): ed = ed.date()
                    elif isinstance(ed, str): ed = date.fromisoformat(ed[:10])
                    if ed >= today:
                        next_earnings = str(ed)
                        days_to_event = (ed - today).days
                        next_event_label = f"Earnings in {days_to_event}d"
                div = cal.get('Ex-Dividend Date') or cal.get('exDividendDate')
                if div:
                    if hasattr(div, 'date'): div = div.date()
                    elif isinstance(div, str): div = date.fromisoformat(str(div)[:10])
                    if isinstance(div, date) and div >= today:
                        next_ex_div = str(div)
                        d2 = (div - today).days
                        if d2 < days_to_event:
                            days_to_event = d2
                            next_event_label = f"Ex-Div in {d2}d"
        return next_earnings, next_event_label, next_ex_div, days_to_event
    except: return None, None, None, 9999

# ── Buy/Sell volume estimation (OBV-based) ────────────────────────────────────
def _calc_buy_sell_volume(hist):
    """Estimate buy vs sell volume using price-action heuristic."""
    try:
        closes = hist['Close'].values
        opens  = hist['Open'].values
        vols   = hist['Volume'].values
        buy_vol = sell_vol = 0.0
        for i in range(len(closes)):
            rng = closes[i] - opens[i]
            bar_range = abs(rng)
            if bar_range < 0.0001:
                buy_vol  += vols[i] * 0.5
                sell_vol += vols[i] * 0.5
            else:
                ratio = (closes[i] - opens[i]) / (bar_range * 2) + 0.5  # 0..1
                buy_vol  += vols[i] * ratio
                sell_vol += vols[i] * (1 - ratio)
        total = buy_vol + sell_vol
        buy_pct  = round(buy_vol  / total * 100, 1) if total > 0 else 50.0
        sell_pct = round(sell_vol / total * 100, 1) if total > 0 else 50.0
        return buy_pct, sell_pct
    except: return 50.0, 50.0

def _calc_rsi(closes, period=14):
    try:
        import pandas as pd
        delta = pd.Series(closes).diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return round(float(rsi.iloc[-1]), 1)
    except: return None

def _calc_atr(hist, period=14):
    try:
        import pandas as pd
        high = hist['High']
        low  = hist['Low']
        close= hist['Close']
        tr = pd.concat([high - low,
                        (high - close.shift()).abs(),
                        (low  - close.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        price = close.iloc[-1]
        return round(float(atr), 3), round(float(atr / price * 100), 2)
    except: return None, None

def _calc_bollinger(closes, period=20):
    try:
        import pandas as pd
        s = pd.Series(closes)
        mid = s.rolling(period).mean()
        std = s.rolling(period).std()
        upper = mid + 2 * std
        lower = mid - 2 * std
        price = s.iloc[-1]
        u, l, m = float(upper.iloc[-1]), float(lower.iloc[-1]), float(mid.iloc[-1])
        bw = round((u - l) / m * 100, 1) if m > 0 else None
        pos = round((price - l) / (u - l) * 100, 1) if (u - l) > 0 else None
        return round(u,3), round(l,3), round(m,3), bw, pos
    except: return None, None, None, None, None

# ── Main stock fetch ──────────────────────────────────────────────────────────
def fetch_stock(ticker):
    time.sleep(1 + random.uniform(0, 1))
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1y")
        if hist.empty or len(hist) < 60: return None

        info  = t.fast_info
        price = float(hist['Close'].iloc[-1])
        mktcap = float(getattr(info, 'market_cap', 0) or 0)
        if price <= 0 or mktcap < MIN_MARKET_CAP: return None

        closes  = hist['Close']
        volumes = hist['Volume']
        highs   = hist['High']
        lows    = hist['Low']

        # ── Moving averages ───────────────────────────────────────────────
        ma50  = round(float(closes.tail(50).mean()), 3)
        ma150 = round(float(closes.tail(150).mean()), 3) if len(closes) >= 150 else round(float(closes.mean()), 3)
        ma200 = round(float(closes.tail(200).mean()), 3) if len(closes) >= 200 else round(float(closes.mean()), 3)
        ma200_slope = closes.tail(200) if len(closes) >= 200 else closes
        ma200p = round(float(ma200_slope.head(len(ma200_slope)//2).mean()), 3)

        # ── Volume ────────────────────────────────────────────────────────
        vol_today   = float(volumes.iloc[-1])
        vol_avg20   = float(volumes.tail(20).mean())
        vol_avg50   = float(volumes.tail(50).mean())
        volr        = round(vol_today / vol_avg20, 2) if vol_avg20 > 0 else 1.0
        vol_5d_avg  = float(volumes.tail(5).mean())
        vol_trend   = round((vol_5d_avg / vol_avg20 - 1) * 100, 1) if vol_avg20 > 0 else 0.0
        # Dollar volume
        dollar_vol  = round(vol_today * price / 1e6, 2)  # in $M
        # Buy/sell split
        buy_pct, sell_pct = _calc_buy_sell_volume(hist.tail(10))

        # ── Price changes ──────────────────────────────────────────────────
        def pct(n):
            if len(closes) > n: return round((float(closes.iloc[-1]) / float(closes.iloc[-n-1]) - 1) * 100, 2)
            return 0.0
        chg1d   = pct(1)
        chg5d   = pct(5)
        chg20d  = pct(20)
        chg60d  = pct(60)
        chg250d = pct(min(249, len(closes)-1))

        # ── 52-week high / low ────────────────────────────────────────────
        hi52  = round(float(highs.tail(252).max()), 3)
        lo52  = round(float(lows.tail(252).min()), 3)
        pct_from_hi = round((price / hi52 - 1) * 100, 1) if hi52 > 0 else 0.0
        pct_from_lo = round((price / lo52 - 1) * 100, 1) if lo52 > 0 else 0.0

        # ── Technical indicators ──────────────────────────────────────────
        rsi = _calc_rsi(closes.values)
        atr, atr_pct = _calc_atr(hist)
        bb_upper, bb_lower, bb_mid, bb_bw, bb_pos = _calc_bollinger(closes.values)

        # ── Pivot / near-pivot ────────────────────────────────────────────
        recent_hi = round(float(highs.tail(10).max()), 3)
        near_pivot = price >= recent_hi * 0.98 and price <= recent_hi * 1.05

        # ── SEPA checks ───────────────────────────────────────────────────
        c_ma50    = price > ma50
        c_ma150   = price > ma150
        c_ma200   = price > ma200
        c_trend   = ma50 > ma150 > ma200
        c_trend200 = ma200 > ma200p  # MA200 trending up
        c_high    = price >= hi52 * 0.75
        c_low     = price >= lo52 * 1.25
        c_vol     = volr >= VOL_BREAKOUT

        sepa_score = sum([c_ma50, c_ma150, c_ma200, c_trend, c_high, c_low, c_trend200])

        # ── VCP checks ────────────────────────────────────────────────────
        w1  = float(closes.tail(10).std())
        w2  = float(closes.tail(5).std())
        w3  = float(closes.tail(3).std())
        contraction = w1 > 0 and w2 < w1 * 0.8 and w3 < w2 * 0.8
        v1  = float(volumes.tail(10).mean())
        v2  = float(volumes.tail(5).mean())
        vol_dry   = v2 < v1 * 0.8
        tight_action = w3 < price * 0.02
        vcp_score = sum([contraction, vol_dry, c_vol, tight_action])

        # ── Status ────────────────────────────────────────────────────────
        if sepa_score >= SEPA_MIN and c_vol:
            status = "Breakout"
        elif sepa_score >= SEPA_MIN and near_pivot:
            status = "NearPivot"
        elif sepa_score >= SEPA_MIN:
            status = "Watch"
        else:
            status = "None"

        # ── Extended info (info2) ─────────────────────────────────────────
        name = ticker.replace('.AX', '')
        sector = industry = None
        pe_ratio = pb_ratio = ps_ratio = peg_ratio = None
        debt_equity = roe = roa = current_ratio = quick_ratio = None
        div_yield = div_rate = payout_ratio = None
        profit_margin = gross_margin = operating_margin = None
        fcf = fcf_per_share = None
        beta = short_ratio = None
        rev_growth_pct = rev_trend = rev_quarters = None
        eps_growth_pct = eps_trend = eps_quarters = None
        net_margin_pct = trailing_eps = forward_eps = None
        fund_score = 0

        try:
            inf2 = t.info or {}
            name     = inf2.get('longName') or inf2.get('shortName') or ticker.replace('.AX','')
            sector   = inf2.get('sector')
            industry = inf2.get('industry')

            # Valuation
            pe_ratio  = safe_round(inf2.get('trailingPE'))
            pb_ratio  = safe_round(inf2.get('priceToBook'))
            ps_ratio  = safe_round(inf2.get('priceToSalesTrailing12Months'))
            peg_ratio = safe_round(inf2.get('pegRatio'))

            # Balance sheet ratios
            debt_equity   = safe_round(inf2.get('debtToEquity'))
            roe           = safe_round(inf2.get('returnOnEquity', 0) * 100 if inf2.get('returnOnEquity') else None)
            roa           = safe_round(inf2.get('returnOnAssets', 0) * 100 if inf2.get('returnOnAssets') else None)
            current_ratio = safe_round(inf2.get('currentRatio'))
            quick_ratio   = safe_round(inf2.get('quickRatio'))

            # Dividends
            raw_dy = inf2.get('dividendYield')
            div_yield    = safe_round(raw_dy * 100 if raw_dy else None)
            div_rate     = safe_round(inf2.get('dividendRate'))
            payout_ratio = safe_round(inf2.get('payoutRatio', 0) * 100 if inf2.get('payoutRatio') else None)

            # Margins
            pm = inf2.get('profitMargins')
            profit_margin   = safe_round(pm * 100 if pm else None)
            gm = inf2.get('grossMargins')
            gross_margin    = safe_round(gm * 100 if gm else None)
            om = inf2.get('operatingMargins')
            operating_margin = safe_round(om * 100 if om else None)
            net_margin_pct   = profit_margin

            # FCF
            fcf_raw = inf2.get('freeCashflow')
            fcf     = round(fcf_raw / 1e6, 1) if fcf_raw else None  # in $M
            shares  = inf2.get('sharesOutstanding')
            fcf_per_share = round(fcf_raw / shares, 3) if fcf_raw and shares else None

            # Risk metrics
            beta       = safe_round(inf2.get('beta'))
            short_ratio = safe_round(inf2.get('shortRatio'))

            # EPS
            trailing_eps = safe_round(inf2.get('trailingEps'))
            forward_eps  = safe_round(inf2.get('forwardEps'))

            # Fundamental scoring
            rev_growth_pct, rev_trend, rev_quarters = _quarterly_revenue_trend(t)
            if rev_growth_pct is None:
                rg = inf2.get('revenueGrowth')
                if rg is not None: rev_growth_pct = round(rg * 100, 1)

            eps_growth_pct, eps_trend, eps_quarters = _quarterly_eps_trend(t)
            if eps_growth_pct is None:
                eg = inf2.get('earningsGrowth')
                if eg is not None: eps_growth_pct = round(eg * 100, 1)

            if rev_growth_pct is not None and rev_growth_pct > 5:  fund_score += 1
            if rev_growth_pct is not None and rev_growth_pct > 20: fund_score += 1
            if eps_growth_pct is not None and eps_growth_pct > 0:  fund_score += 1
            fund_score = min(fund_score, 3)
        except Exception:
            name = ticker.replace('.AX', '')

        next_earnings, next_event_label, next_ex_div, days_to_event = _fetch_events(t)

        # ── Short signals ──────────────────────────────────────────────────
        sigs = []
        if c_vol:          sigs.append(f"Vol {volr}x avg")
        if chg250d > 50:   sigs.append(f"+{chg250d}% YTD")
        if near_pivot:     sigs.append("Near Pivot")
        if vcp_score >= 3: sigs.append("VCP")
        if rsi and rsi > 70: sigs.append(f"RSI {rsi}")

        # ── Analysis text ──────────────────────────────────────────────────
        analysis_parts = []
        if c_trend:    analysis_parts.append("Stage 2 uptrend confirmed")
        if contraction: analysis_parts.append("VCP contraction in progress")
        if c_vol:      analysis_parts.append(f"Volume surge {volr}x 20-day avg")
        if near_pivot: analysis_parts.append(f"Near pivot at ${recent_hi:.2f}")
        if rsi:        analysis_parts.append(f"RSI {rsi}")
        if bb_pos:     analysis_parts.append(f"BB position {bb_pos}%")
        analysis = ". ".join(analysis_parts) if analysis_parts else "Monitoring"

        return {
            "ticker": ticker, "name": name, "sector": sector, "industry": industry,
            "price": round(price, 3),
            "ma50": ma50, "ma150": ma150, "ma200": ma200,
            "hi52": hi52, "lo52": lo52,
            "pctFromHi": pct_from_hi, "pctFromLo": pct_from_lo,
            # Volume
            "volume": int(vol_today), "volAvg20": int(vol_avg20), "volAvg50": int(vol_avg50),
            "volr": volr, "volTrend": vol_trend, "dollarVol": dollar_vol,
            "buyPct": buy_pct, "sellPct": sell_pct,
            # Price changes
            "chg1d": round(chg1d,2), "chg5d": round(chg5d,2),
            "chg20d": round(chg20d,2), "chg60d": round(chg60d,2), "chg250d": round(chg250d,2),
            # Technical
            "rsi": rsi, "atr": atr, "atrPct": atr_pct,
            "bbUpper": bb_upper, "bbLower": bb_lower, "bbMid": bb_mid,
            "bbBw": bb_bw, "bbPos": bb_pos,
            # SEPA/VCP
            "sepa": sepa_score, "vcp": vcp_score,
            "mktcap": int(mktcap), "mktcapFmt": fmt_cap(mktcap), "status": status,
            "checks": {"ma50":c_ma50,"ma150":c_ma150,"ma200":c_ma200,"trend":c_trend,
                       "trend200":c_trend200,"high":c_high,"low":c_low,"vol":c_vol},
            "nearPivot": near_pivot, "recentHi": recent_hi,
            "shortSignal": " · ".join(sigs[:3]), "analysis": analysis,
            # Fundamentals
            "revGrowth": rev_growth_pct, "revTrend": rev_trend, "revQuarters": rev_quarters,
            "epsGrowth": eps_growth_pct, "epsTrend": eps_trend, "epsQuarters": eps_quarters,
            "netMargin": net_margin_pct, "grossMargin": gross_margin, "operatingMargin": operating_margin,
            "profitMargin": profit_margin,
            "trailingEps": trailing_eps, "forwardEps": forward_eps, "fundScore": fund_score,
            "peRatio": pe_ratio, "pbRatio": pb_ratio, "psRatio": ps_ratio, "pegRatio": peg_ratio,
            "debtEquity": debt_equity, "roe": roe, "roa": roa,
            "currentRatio": current_ratio, "quickRatio": quick_ratio,
            "divYield": div_yield, "divRate": div_rate, "payoutRatio": payout_ratio,
            "fcf": fcf, "fcfPerShare": fcf_per_share,
            "beta": beta, "shortRatio": short_ratio,
            # Events
            "nextEarnings": next_earnings, "nextEventLabel": next_event_label,
            "nextExDiv": next_ex_div, "daysToEvent": days_to_event,
        }
    except Exception as e:
        print(f"  {ticker}: {e}")
        return None

def fetch_all():
    print(f"Fetching {len(ASX_TICKERS)} ASX stocks...")
    results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_stock, t): t for t in ASX_TICKERS}
        done = 0
        for f in as_completed(futs):
            done += 1
            r = f.result()
            if r: results.append(r)
            if done % 100 == 0:
                print(f"  {done}/{len(ASX_TICKERS)} processed, {len(results)} passed filters")
    return results

if __name__ == "__main__":
    print(f"SEPA+VCP ASX Screener - {date.today()}")
    data = fetch_all()
    b = sum(1 for r in data if r['status'] == 'Breakout')
    p = sum(1 for r in data if r['status'] == 'NearPivot')
    w = sum(1 for r in data if r['status'] == 'Watch')
    print(f"Results: {len(data)} | Breakouts:{b} | NearPivot:{p} | Watch:{w}")
    if not data:
        print("No stocks passed filters — building empty dashboard.")

    try:
        import build_dashboard
        html = build_dashboard.build(data)
        with open('index.html', 'w', encoding='utf-8') as f: f.write(html)
        print(f"Dashboard built: {len(html):,} chars")
        build_dashboard.publish('index.html')
    except Exception as ex:
        import traceback
        tb = traceback.format_exc()
        print(f"BUILD FAILED:\n{tb}")
        fallback = f'<html><body><pre style="padding:20px">Build error ({date.today()}):\n{tb}</pre></body></html>'
        with open('index.html', 'w', encoding='utf-8') as f: f.write(fallback)
        print("Wrote fallback index.html for debugging")
        build_dashboard.publish('index.html')
