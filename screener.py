import yfinance as yf
import json, os, time, requests, random
from datetime import date, datetime
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

NETLIFY_TOKEN   = os.environ.get("NETLIFY_TOKEN", "")
NETLIFY_SITE_ID = os.environ.get("NETLIFY_SITE_ID", "")
MIN_MARKET_CAP  = 100_000_000
SEPA_MIN        = 3
VOL_BREAKOUT    = 1.5
VCP_MIN         = 2

session = requests.Session()
retry = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
})

def get_all_asx_tickers():
    try:
        import io
        url = "https://www.asx.com.au/asx/research/ASXListedCompanies.csv"
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        df = pd.read_csv(io.StringIO(resp.text), skiprows=1)
        col = [c for c in df.columns if 'code' in c.lower() or 'asx' in c.lower()][0]
        tickers = [str(row[col]).strip() + '.AX' for _, row in df.iterrows()
                   if str(row[col]).strip() and len(str(row[col]).strip()) <= 5]
        print(f"Loaded {len(tickers)} ASX tickers from ASX website")
        return tickers
    except Exception as e:
        print(f"Failed to fetch ASX tickers: {e}")
        return []

ASX_TICKERS = get_all_asx_tickers()

def fmt_cap(c):
    if c >= 1e12: return f"${c/1e12:.1f}T"
    if c >= 1e9:  return f"${c/1e9:.1f}B"
    if c >= 1e6:  return f"${c/1e6:.0f}M"
    return f"${c:.0f}"

def fmt_pct(v):
    return ('+' if v >= 0 else '') + str(round(v, 2)) + '%'

def _parse_date(raw):
    if raw is None: return None
    if hasattr(raw, 'date'): return raw.date()
    if isinstance(raw, str):
        try: return datetime.strptime(raw[:10], '%Y-%m-%d').date()
        except: return None
    return None

# ── Batch download price history for a chunk of tickers ──────────────────────
def download_chunk(tickers, period="1y"):
    """Download OHLCV for a batch of tickers in one request. Returns dict ticker->df."""
    try:
        raw = yf.download(
            tickers, period=period, interval="1d",
            group_by="ticker", auto_adjust=True,
            progress=False, threads=True
        )
    except Exception as e:
        print(f"  batch download error: {e}")
        return {}

    result = {}
    if len(tickers) == 1:
        t = tickers[0]
        if not raw.empty:
            result[t] = raw
        return result

    for t in tickers:
        try:
            df = raw[t].dropna(how='all')
            if not df.empty and len(df) >= 60:
                result[t] = df
        except Exception:
            pass
    return result

# ── Score one ticker from its price dataframe ─────────────────────────────────
def score_stock(ticker, hist):
    try:
        closes  = hist['Close']
        volumes = hist['Volume']

        price  = float(closes.iloc[-1])
        volume = float(volumes.iloc[-1])
        if price <= 0: return None

        ma50   = round(float(closes.tail(50).mean()), 3)
        ma150  = round(float(closes.tail(150).mean()), 3) if len(closes) >= 150 else round(float(closes.mean()), 3)
        ma200  = round(float(closes.tail(200).mean()), 3) if len(closes) >= 200 else round(float(closes.mean()), 3)
        ma200p = round(float(closes.tail(220).head(200).mean()), 3) if len(closes) >= 220 else ma200

        hi52   = float(closes.max())
        lo52   = float(closes.min())
        pct_hi = round(max(0, (hi52 - price) / hi52 * 100), 1) if hi52 > 0 else 0
        pct_lo = round((price - lo52) / lo52 * 100, 1) if lo52 > 0 else 0

        def perf(n):
            if len(closes) > n:
                old = float(closes.iloc[-n])
                return round((price - old) / old * 100, 2) if old > 0 else 0
            return 0

        chg1d   = round((price - float(closes.iloc[-2])) / float(closes.iloc[-2]) * 100, 2) if len(closes) >= 2 else 0
        chg5d   = perf(5)
        chg10d  = perf(10)
        chg20d  = perf(20)
        chg60d  = perf(60)
        chg250d = perf(min(250, len(closes) - 1))

        avg50v = float(volumes.tail(50).mean())
        volr   = round(volume / avg50v, 2) if avg50v > 0 else 1.0

        c_ma50  = price > ma50
        c_ma150 = ma50 > ma150
        c_ma200 = ma150 > ma200
        c_trend = ma200 > ma200p
        c_high  = pct_hi <= 25
        c_low   = pct_lo >= 25
        c_vol   = volr >= VOL_BREAKOUT

        sepa = sum([c_ma50, c_ma150, c_ma200, c_trend, c_high, c_low, c_vol])
        if sepa < SEPA_MIN: return None

        vcp = min(sum([
            abs(chg5d)  < abs(chg10d),
            abs(chg10d) < abs(chg20d),
            abs(chg20d) < abs(chg60d),
            volr < 0.8
        ]), 4)

        ve  = volr - 1.0
        pvr = min(round(abs(chg1d) / ve, 2) if ve > 0.1 else round(abs(chg1d) * 2, 2), 9.99)

        if sepa >= 5 and c_vol and vcp >= VCP_MIN: status = "breakout"
        elif sepa >= 4 and vcp >= VCP_MIN and pct_hi <= 15: status = "near-pivot"
        else: status = "watch"

                try:
            qf = t.quarterly_financials
            rev_quarters = []
            if qf is not None and not qf.empty:
                for key in ['Total Revenue', 'TotalRevenue', 'Revenue']:
                    if key in qf.index:
                        row = qf.loc[key].dropna().sort_index()
                        for dt, val in row.items():
                            try:
                                ts = pd.Timestamp(dt)
                                label = f"Q{ts.quarter}'{str(ts.year)[2:]}"
                                rev_quarters.append([label, float(val)])
                            except Exception:
                                pass
                        rev_quarters = rev_quarters[-8:]
                        break
        except Exception:
            rev_quarters = []
        
return {
            "_ticker_raw": ticker,
            "price": round(price, 3), "change": round(chg1d, 2),
            "ma50": ma50, "ma150": ma150, "ma200": ma200,
            "volRatio": volr, "pvr": pvr, "vcpScore": vcp, "sepaScore": sepa,
            "pctFromHigh": pct_hi, "pctAboveLow": pct_lo,
            "hi52": round(hi52, 2), "lo52": round(lo52, 2),
            "chg5d": chg5d, "chg60d": chg60d, "chg250d": chg250d,
            "status": status,
            "checks": {"ma50": c_ma50, "ma150": c_ma150, "ma200": c_ma200,
                       "trend": c_trend, "high": c_high, "low": c_low, "vol": c_vol},
            # filled in later by enrich_stock
            "ticker": ticker.replace('.AX', ''), "name": ticker.replace('.AX', ''),
            "sector": "", "mktcap": 0, "mktcapFmt": "",
            "shortSignal": "", "analysis": "",
            "revGrowth": None, "revTrend": None, "revQuarters": rev_quarters,
            "epsGrowth": None, "netMargin": None,
            "trailingEps": None, "forwardEps": None, "fundScore": 0,
            "nextEarnings": None, "nextEventLabel": None,
            "nextExDiv": None, "daysToEvent": None,
        }
    except Exception as e:
        print(f"  score_stock {ticker}: {e}")
        return None

# ── Enrich one passing stock with metadata from t.info ────────────────────────
def enrich_stock(r):
    ticker = r["_ticker_raw"]
    try:
        t    = yf.Ticker(ticker)
        inf2 = t.info or {}

        mktcap = float(inf2.get('marketCap') or 0)
        if mktcap < MIN_MARKET_CAP and mktcap > 0:
            return None   # filter by market cap now that we have it

        r["mktcap"]    = int(mktcap)
        r["mktcapFmt"] = fmt_cap(mktcap)
        r["name"]      = inf2.get('longName', ticker.replace('.AX', ''))
        r["sector"]    = inf2.get('sector', '') or inf2.get('industry', '') or ''
        r["ticker"]    = ticker.replace('.AX', '')

        pm = inf2.get('profitMargins')
        te = inf2.get('trailingEps')
        fe = inf2.get('forwardEps')
        rg = inf2.get('revenueGrowth')
        eg = inf2.get('earningsGrowth')

        if pm is not None: r["netMargin"]   = round(pm * 100, 1)
        if te is not None: r["trailingEps"] = round(float(te), 3)
        if fe is not None: r["forwardEps"]  = round(float(fe), 3)
        if rg is not None: r["revGrowth"]   = round(rg * 100, 1)
        if eg is not None: r["epsGrowth"]   = round(eg * 100, 1)

        rv = r["revGrowth"]
        if rv is not None:
            r["revTrend"] = 'accelerating' if rv > 20 else 'growing' if rv > 5 else 'declining' if rv < 0 else 'flat'

        fs = 0
        if rv is not None and rv > 5:  fs += 1
        if rv is not None and rv > 20: fs += 1
        if r["epsGrowth"] is not None and r["epsGrowth"] > 0: fs += 1
        r["fundScore"] = min(fs, 3)

        # Calendar (inline)
        try:
            today = date.today()
            cal   = t.calendar
            if isinstance(cal, dict):
                ed_list = cal.get('Earnings Date') or cal.get('earningsDate') or []
                if isinstance(ed_list, (list, tuple)) and ed_list: ed = _parse_date(ed_list[0])
                elif ed_list: ed = _parse_date(ed_list)
                else: ed = None
                if ed:
                    days = (ed - today).days
                    if -30 <= days <= 180:
                        r["nextEarnings"] = str(ed)
                        r["daysToEvent"]  = days
                        if days == 0:    r["nextEventLabel"] = "⚡ RESULTS TODAY"
                        elif days <= 7:  r["nextEventLabel"] = f"⚡ Results in {days}d"
                        elif days <= 30: r["nextEventLabel"] = f"📅 Results in {days}d"
                        else:            r["nextEventLabel"] = f"📅 Results {ed.strftime('%d %b')}"
                xd = cal.get('Ex-Dividend Date') or cal.get('exDividendDate')
                if xd:
                    d2 = _parse_date(xd)
                    if d2 and (d2 - today).days >= -7:
                        r["nextExDiv"] = d2.strftime('%d %b %Y')
        except Exception:
            pass

    except Exception:
        pass  # keep stock with defaults if t.info fails

    # Build short signals and analysis text
    volr    = r["volRatio"]
    chg250d = r["chg250d"]
    vcp     = r["vcpScore"]
    sepa    = r["sepaScore"]
    pct_hi  = r["pctFromHigh"]
    hi52    = r["hi52"]
    pvr     = r["pvr"]
    rev_trend       = r["revTrend"]
    next_event_label = r["nextEventLabel"]
    rev_growth_pct  = r["revGrowth"]
    eps_growth_pct  = r["epsGrowth"]
    trailing_eps    = r["trailingEps"]
    name            = r["name"]
    c_vol           = r["checks"]["vol"]
    c_ma50          = r["checks"]["ma50"]
    c_ma150         = r["checks"]["ma150"]
    c_ma200         = r["checks"]["ma200"]

    sigs = []
    if c_vol:                           sigs.append(f"Vol {volr}x avg")
    if chg250d > 50:                    sigs.append(f"+{chg250d}% 12M")
    if vcp >= 3:                        sigs.append("VCP tightening")
    if pct_hi < 5:                      sigs.append("Near 52W high")
    if rev_trend == 'accelerating':     sigs.append("↑↑ Revenue accelerating")
    elif rev_trend == 'growing':        sigs.append("↑ Revenue growing")
    if next_event_label and ('⚡' in next_event_label or '📅' in next_event_label):
        sigs.append(next_event_label)
    if not sigs: sigs.append(f"SEPA {sepa}/7")
    r["shortSignal"] = " · ".join(sigs[:3])

    tr   = "strongly uptrending" if chg250d > 40 else "uptrending" if chg250d > 15 else "recovering"
    mas  = "fully aligned (Price>MA50>MA150>MA200)" if (c_ma50 and c_ma150 and c_ma200) else "partially aligned"
    vls  = f"Volume is {volr}x the 50-day average" if volr >= 1.5 else f"Volume at {volr}x average"
    vcpd = ["no base","early base","developing VCP","good VCP (volume drying up)","textbook VCP (volume at lows)"][vcp]
    fund_ctx = ""
    if rev_growth_pct is not None:
        td = " (accelerating)" if rev_trend == 'accelerating' else " (growing)" if rev_trend == 'growing' else ""
        if rev_growth_pct > 20:  fund_ctx += f" Revenue growing strongly +{rev_growth_pct}% YoY{td}."
        elif rev_growth_pct > 5: fund_ctx += f" Revenue +{rev_growth_pct}% YoY{td}."
        elif rev_growth_pct < 0: fund_ctx += f" Revenue declined {rev_growth_pct}% YoY."
    if eps_growth_pct is not None and eps_growth_pct > 0:
        fund_ctx += f" EPS growth +{eps_growth_pct}%."
    elif trailing_eps and trailing_eps > 0:
        fund_ctx += f" Profitable (trailing EPS ${trailing_eps})."
    catalyst = f" CATALYST: {next_event_label}." if next_event_label else ""

    r["analysis"] = (
        f"{name} is {tr} over 12 months ({fmt_pct(chg250d)}), MAs {mas}. "
        f"Forming {vcpd}, {pct_hi}% below 52W high of ${round(hi52,2)}. "
        f"{vls}. SEPA {sepa}/7, PVR {pvr}.{fund_ctx}{catalyst}"
    )

    del r["_ticker_raw"]
    return r

def fetch_all():
    print(f"Fetching price history for {len(ASX_TICKERS)} ASX stocks in batches...")

    # Step 1: batch download price history (fast — one request per 50 stocks)
    BATCH = 50
    hist_map = {}
    for i in range(0, len(ASX_TICKERS), BATCH):
        chunk = ASX_TICKERS[i:i+BATCH]
        batch_result = download_chunk(chunk)
        hist_map.update(batch_result)
        pct = min(i + BATCH, len(ASX_TICKERS))
        print(f"  Price data: {pct}/{len(ASX_TICKERS)} tickers fetched, {len(hist_map)} with data")
        time.sleep(0.5)   # small pause between batches

    print(f"Price history: {len(hist_map)} tickers with ≥60 days data")

    # Step 2: score all stocks from price data (CPU only, no network)
    candidates = []
    for ticker, hist in hist_map.items():
        r = score_stock(ticker, hist)
        if r:
            candidates.append(r)
    print(f"Passed SEPA filters: {len(candidates)} stocks — now enriching with metadata...")

    # Step 3: enrich passing stocks with t.info (parallel, but only ~candidates)
    results = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(enrich_stock, r): r["ticker"] for r in candidates}
        done = 0
        for f in as_completed(futs):
            done += 1
            r = f.result()
            if r:
                results.append(r)

    results.sort(key=lambda x: (x['sepaScore'], x['vcpScore']), reverse=True)
    return results

# Deployment is handled by GitHub Pages via the workflow — no publish function needed.

if __name__ == "__main__":
    print(f"SEPA+VCP ASX Screener - {date.today()}")
    data = fetch_all()
    b = sum(1 for r in data if r['status'] == 'breakout')
    p = sum(1 for r in data if r['status'] == 'near-pivot')
    w = sum(1 for r in data if r['status'] == 'watch')
    print(f"Results: {len(data)} | Breakouts:{b} | NearPivot:{p} | Watch:{w}")
    if not data:
        print("No stocks passed filters — building empty dashboard.")
    try:
        import build_dashboard
        html = build_dashboard.build(data)
        with open('index.html', 'w', encoding='utf-8') as f: f.write(html)
        print(f"Dashboard built: {len(html):,} chars")
        print("index.html ready — GitHub Pages deployment handled by workflow.")
    except Exception as ex:
        import traceback
        tb = traceback.format_exc()
        print(f"BUILD FAILED:\n{tb}")
        fallback = f'<html><body><pre style="padding:20px">Build error ({date.today()}):\n{tb}</pre></body></html>'
        with open('index.html', 'w', encoding='utf-8') as f: f.write(fallback)
        print("Wrote fallback index.html for debugging")
