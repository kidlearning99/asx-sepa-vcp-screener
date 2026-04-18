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

def get_all_asx_tickers():
    try:
        import io, pandas as pd
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
        except Exception: return None
    return None

def fetch_stock(ticker):
    # Short sleep to avoid Yahoo rate limits but still be fast
    time.sleep(0.3 + random.uniform(0, 0.4))
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1y")
        if hist.empty or len(hist) < 60: return None

        info = t.fast_info
        price = float(hist['Close'].iloc[-1])
        mktcap = float(getattr(info, 'market_cap', 0) or 0)
        volume = float(hist['Volume'].iloc[-1])
        if price <= 0 or mktcap < MIN_MARKET_CAP: return None

        closes = hist['Close']
        volumes = hist['Volume']
        ma50   = round(float(closes.tail(50).mean()), 3)
        ma150  = round(float(closes.tail(150).mean()), 3) if len(closes) >= 150 else round(float(closes.mean()), 3)
        ma200  = round(float(closes.tail(200).mean()), 3) if len(closes) >= 200 else round(float(closes.mean()), 3)
        ma200p = round(float(closes.tail(220).head(200).mean()), 3) if len(closes) >= 220 else ma200

        hi52 = float(closes.max())
        lo52 = float(closes.min())
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

        c_ma50   = price > ma50
        c_ma150  = ma50 > ma150
        c_ma200  = ma150 > ma200
        c_trend  = ma200 > ma200p
        c_high   = pct_hi <= 25
        c_low    = pct_lo >= 25
        c_vol    = volr >= VOL_BREAKOUT

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

        # ── Fundamentals from t.info (already cached — no extra network call) ──
        sector = name = ""
        rev_growth_pct = eps_growth_pct = net_margin_pct = trailing_eps = forward_eps = None
        fund_score = 0
        rev_trend = None
        next_earnings = next_event_label = next_ex_div = days_to_event = None

        try:
            inf2 = t.info or {}
            sector = inf2.get('sector', '') or inf2.get('industry', '') or ''
            name   = inf2.get('longName', ticker.replace('.AX', ''))

            pm = inf2.get('profitMargins')
            te = inf2.get('trailingEps')
            fe = inf2.get('forwardEps')
            if pm is not None: net_margin_pct = round(pm * 100, 1)
            if te is not None: trailing_eps   = round(float(te), 3)
            if fe is not None: forward_eps    = round(float(fe), 3)

            rg = inf2.get('revenueGrowth')
            eg = inf2.get('earningsGrowth')
            if rg is not None: rev_growth_pct = round(rg * 100, 1)
            if eg is not None: eps_growth_pct = round(eg * 100, 1)

            # Simple trend labels from annual growth
            if rev_growth_pct is not None:
                rev_trend = 'accelerating' if rev_growth_pct > 20 else 'growing' if rev_growth_pct > 5 else 'declining' if rev_growth_pct < 0 else 'flat'

            if rev_growth_pct is not None and rev_growth_pct > 5:  fund_score += 1
            if rev_growth_pct is not None and rev_growth_pct > 20: fund_score += 1
            if eps_growth_pct is not None and eps_growth_pct > 0:  fund_score += 1
            fund_score = min(fund_score, 3)

            # ── Calendar (inline, single try) ──
            try:
                today = date.today()
                cal = t.calendar
                if isinstance(cal, dict):
                    ed_list = cal.get('Earnings Date') or cal.get('earningsDate') or []
                    if isinstance(ed_list, (list, tuple)) and ed_list: ed = _parse_date(ed_list[0])
                    elif ed_list: ed = _parse_date(ed_list)
                    else: ed = None
                    if ed:
                        days = (ed - today).days
                        if -30 <= days <= 180:
                            next_earnings = str(ed)
                            days_to_event = days
                            if days == 0:      next_event_label = "⚡ RESULTS TODAY"
                            elif days <= 7:    next_event_label = f"⚡ Results in {days}d"
                            elif days <= 30:   next_event_label = f"📅 Results in {days}d"
                            else:              next_event_label = f"📅 Results {ed.strftime('%d %b')}"
                    xd = cal.get('Ex-Dividend Date') or cal.get('exDividendDate')
                    if xd:
                        d2 = _parse_date(xd)
                        if d2 and (d2 - today).days >= -7:
                            next_ex_div = d2.strftime('%d %b %Y')
            except Exception:
                pass

        except Exception:
            name = ticker.replace('.AX', '')

        # ── Short signals ──
        sigs = []
        if c_vol:                    sigs.append(f"Vol {volr}x avg")
        if chg250d > 50:             sigs.append(f"+{chg250d}% 12M")
        if vcp >= 3:                 sigs.append("VCP tightening")
        if pct_hi < 5:               sigs.append("Near 52W high")
        if rev_trend == 'accelerating': sigs.append("↑↑ Revenue accelerating")
        elif rev_trend == 'growing':    sigs.append("↑ Revenue growing")
        if next_event_label and ('⚡' in next_event_label or '📅' in next_event_label):
            sigs.append(next_event_label)
        if not sigs: sigs.append(f"SEPA {sepa}/7")

        # ── Analysis text ──
        tr   = "strongly uptrending" if chg250d > 40 else "uptrending" if chg250d > 15 else "recovering"
        mas  = "fully aligned (Price>MA50>MA150>MA200)" if (c_ma50 and c_ma150 and c_ma200) else "partially aligned"
        vls  = f"Volume is {volr}x the 50-day average" if volr >= 1.5 else f"Volume at {volr}x average"
        vcpd = ["no base","early base","developing VCP","good VCP (volume drying up)","textbook VCP (volume at lows)"][vcp]

        fund_ctx = ""
        if rev_growth_pct is not None:
            trend_desc = " (accelerating)" if rev_trend == 'accelerating' else " (growing)" if rev_trend == 'growing' else ""
            if rev_growth_pct > 20:   fund_ctx += f" Revenue growing strongly +{rev_growth_pct}% YoY{trend_desc} — fundamental momentum supports breakout."
            elif rev_growth_pct > 5:  fund_ctx += f" Revenue +{rev_growth_pct}% YoY{trend_desc}."
            elif rev_growth_pct < 0:  fund_ctx += f" Revenue declined {rev_growth_pct}% YoY — monitor fundamentals before entry."
        if eps_growth_pct is not None and eps_growth_pct > 0:
            fund_ctx += f" EPS growth +{eps_growth_pct}% confirms expanding profitability."
        elif trailing_eps and trailing_eps > 0:
            fund_ctx += f" Profitable (trailing EPS ${trailing_eps})."
        catalyst = f" CATALYST: {next_event_label}." if next_event_label else ""

        analysis = (
            f"{name} is {tr} over 12 months ({fmt_pct(chg250d)}), MAs {mas}. "
            f"Forming {vcpd}, {pct_hi}% below 52W high of ${round(hi52,2)}. "
            f"{vls}. SEPA {sepa}/7, PVR {pvr}. "
            f"{fund_ctx}{catalyst}"
        )

        return {
            "ticker": ticker.replace('.AX', ''), "name": name, "sector": sector,
            "price": round(price, 3), "change": round(chg1d, 2),
            "ma50": ma50, "ma150": ma150, "ma200": ma200,
            "volRatio": volr, "pvr": pvr, "vcpScore": vcp, "sepaScore": sepa,
            "pctFromHigh": pct_hi, "pctAboveLow": pct_lo,
            "hi52": round(hi52, 2), "lo52": round(lo52, 2),
            "chg5d": round(chg5d, 2), "chg60d": round(chg60d, 2), "chg250d": round(chg250d, 2),
            "mktcap": int(mktcap), "mktcapFmt": fmt_cap(mktcap), "status": status,
            "checks": {"ma50": c_ma50, "ma150": c_ma150, "ma200": c_ma200,
                       "trend": c_trend, "high": c_high, "low": c_low, "vol": c_vol},
            "shortSignal": " · ".join(sigs[:3]), "analysis": analysis,
            "revGrowth": rev_growth_pct, "revTrend": rev_trend,
            "epsGrowth": eps_growth_pct,
            "netMargin": net_margin_pct, "trailingEps": trailing_eps, "forwardEps": forward_eps,
            "fundScore": fund_score,
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
        futures = {ex.submit(fetch_stock, t): t for t in ASX_TICKERS}
        done = 0
        for f in as_completed(futures):
            done += 1
            r = f.result()
            if r: results.append(r)
            if done % 100 == 0:
                print(f"  {done}/{len(ASX_TICKERS)} processed, {len(results)} passed filters")
    results.sort(key=lambda x: (x['sepaScore'], x['vcpScore']), reverse=True)
    return results

def publish(html_path):
    if not NETLIFY_TOKEN or not NETLIFY_SITE_ID: return
    print("Publishing to Netlify...")
    try:
        with open(html_path, 'rb') as f: content = f.read()
        sha = hashlib.sha1(content).hexdigest()
        r = requests.post(
            f"https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_ID}/deploys",
            headers={"Authorization": f"Bearer {NETLIFY_TOKEN}", "Content-Type": "application/json"},
            json={"files": {"/index.html": sha}}
        )
        try: deploy = r.json()
        except Exception:
            print(f"Netlify non-JSON response. HTTP {r.status_code}: {r.text[:200]}")
            return
        did = deploy.get("id")
        if not did: return
        r2 = requests.put(
            f"https://api.netlify.com/api/v1/deploys/{did}/files/index.html",
            headers={"Authorization": f"Bearer {NETLIFY_TOKEN}", "Content-Type": "application/octet-stream"},
            data=content
        )
        if r2.status_code == 200: print(f"Published: {deploy.get('ssl_url') or deploy.get('url')}")
        else: print(f"Netlify Upload Failed: {r2.status_code}")
    except Exception as err:
        print(f"Deployment failure: {err}")

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
        publish('index.html')
    except Exception as ex:
        import traceback
        tb = traceback.format_exc()
        print(f"BUILD FAILED:\n{tb}")
        fallback = f'<html><body><pre style="padding:20px">Build error ({date.today()}):\n{tb}</pre></body></html>'
        with open('index.html', 'w', encoding='utf-8') as f: f.write(fallback)
        print("Wrote fallback index.html for debugging")
        publish('index.html')
