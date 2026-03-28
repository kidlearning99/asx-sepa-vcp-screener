import yfinance as yf
import json, os, time, hashlib, requests
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed

NETLIFY_TOKEN   = os.environ.get("NETLIFY_TOKEN", "")
NETLIFY_SITE_ID = os.environ.get("NETLIFY_SITE_ID", "")
MIN_MARKET_CAP  = 100_000_000
SEPA_MIN        = 3
VOL_BREAKOUT    = 1.5
VCP_MIN         = 2

ASX_TICKERS = [
    "CBA.AX","NAB.AX","WBC.AX","ANZ.AX","MQG.AX","SUN.AX","IAG.AX","QBE.AX",
    "BOQ.AX","BEN.AX","AMP.AX","HUB.AX","NHF.AX","MPL.AX","IFL.AX","GQG.AX",
    "BHP.AX","RIO.AX","FMG.AX","MIN.AX","PLS.AX","IGO.AX","LTR.AX","SFR.AX",
    "NST.AX","EVN.AX","NCM.AX","RRL.AX","WAF.AX","S32.AX","WHC.AX","NHC.AX",
    "YAL.AX","MGX.AX","GOR.AX","SGM.AX","AWC.AX","CMM.AX","DEG.AX","RED.AX",
    "WTC.AX","XRO.AX","TLX.AX","ALU.AX","MP1.AX","TNE.AX","PME.AX","NXT.AX",
    "DDR.AX","CPU.AX","SPT.AX","AD8.AX","SLX.AX","BVS.AX","SQ2.AX","ZIP.AX",
    "CSL.AX","RMD.AX","COH.AX","SHL.AX","PNV.AX","NEU.AX","ARX.AX","IDX.AX",
    "ACL.AX","HLS.AX","RHC.AX","VRT.AX","NAN.AX","CUV.AX","AVH.AX","MSB.AX",
    "WES.AX","WOW.AX","COL.AX","JBH.AX","HVN.AX","LOV.AX","PMV.AX","SUL.AX",
    "BRG.AX","NWL.AX","GUD.AX","MYR.AX","DMP.AX","ARB.AX","BAP.AX","ELD.AX",
    "FLT.AX","WEB.AX","CTD.AX","TCL.AX","APA.AX","AMC.AX","BXB.AX","ORA.AX",
    "IPL.AX","GMG.AX","DXS.AX","GPT.AX","SCG.AX","MGR.AX","CHC.AX","ABP.AX",
    "BWP.AX","DOW.AX","CIM.AX","GWA.AX","MND.AX","NSR.AX","LLC.AX","AZJ.AX",
    "WDS.AX","ORG.AX","STO.AX","BPT.AX","CVN.AX","BOE.AX","PDN.AX","AGL.AX",
    "REA.AX","SEK.AX","CAR.AX","IEL.AX","DHG.AX","TLS.AX","TPG.AX","SPK.AX",
]
ASX_TICKERS = list(dict.fromkeys(ASX_TICKERS))

def fmt_cap(c):
    if c >= 1e12: return f"${c/1e12:.1f}T"
    if c >= 1e9:  return f"${c/1e9:.1f}B"
    if c >= 1e6:  return f"${c/1e6:.0f}M"
    return f"${c:.0f}"

def fmt_pct(v):
    return ('+' if v >= 0 else '') + str(round(v, 2)) + '%'

def fetch_stock(ticker):
    try:
        t    = yf.Ticker(ticker)
        hist = t.history(period="1y")
        if hist.empty or len(hist) < 60:
            return None
        info   = t.fast_info
        price  = float(hist['Close'].iloc[-1])
        mktcap = float(getattr(info, 'market_cap', 0) or 0)
        volume = float(hist['Volume'].iloc[-1])
        if price <= 0 or mktcap < MIN_MARKET_CAP:
            return None
        closes  = hist['Close']
        volumes = hist['Volume']
        ma50    = round(float(closes.tail(50).mean()), 3)
        ma150   = round(float(closes.tail(150).mean()), 3) if len(closes) >= 150 else round(float(closes.mean()), 3)
        ma200   = round(float(closes.tail(200).mean()), 3) if len(closes) >= 200 else round(float(closes.mean()), 3)
        ma200p  = round(float(closes.tail(220).head(200).mean()), 3) if len(closes) >= 220 else ma200
        hi52    = float(closes.max())
        lo52    = float(closes.min())
        pct_hi  = round(max(0, (hi52 - price) / hi52 * 100), 1) if hi52 > 0 else 0
        pct_lo  = round((price - lo52) / lo52 * 100, 1) if lo52 > 0 else 0
        def perf(n):
            if len(closes) > n:
                old = float(closes.iloc[-n])
                return round((price - old) / old * 100, 2) if old > 0 else 0
            return 0
        chg1d   = round((price - float(closes.iloc[-2])) / float(closes.iloc[-2]) * 100, 2) if len(closes) >= 2 else 0
        chg5d   = perf(5); chg10d = perf(10); chg20d = perf(20); chg60d = perf(60)
        chg250d = perf(min(250, len(closes) - 1))
        avg50v  = float(volumes.tail(50).mean())
        volr    = round(volume / avg50v, 2) if avg50v > 0 else 1.0
        c_ma50  = price > ma50;  c_ma150 = ma50 > ma150;  c_ma200 = ma150 > ma200
        c_trend = ma200 > ma200p; c_high = pct_hi <= 25;  c_low = pct_lo >= 25
        c_vol   = volr >= VOL_BREAKOUT
        sepa    = sum([c_ma50, c_ma150, c_ma200, c_trend, c_high, c_low, c_vol])
        if sepa < SEPA_MIN:
            return None
        vcp = 0
        if abs(chg5d)  < abs(chg10d): vcp += 1
        if abs(chg10d) < abs(chg20d): vcp += 1
        if abs(chg20d) < abs(chg60d): vcp += 1
        if volr < 0.8: vcp += 1
        vcp = min(vcp, 4)
        ve  = volr - 1.0
        pvr = round(abs(chg1d) / ve, 2) if ve > 0.1 else round(abs(chg1d) * 2, 2)
        pvr = min(pvr, 9.99)
        if sepa >= 5 and c_vol and vcp >= VCP_MIN:   status = "breakout"
        elif sepa >= 4 and vcp >= VCP_MIN and pct_hi <= 15: status = "near-pivot"
        else: status = "watch"
        sigs = []
        if c_vol:           sigs.append(f"Vol {volr}x avg")
        if chg250d > 50:    sigs.append(f"+{chg250d}% 12M")
        if vcp >= 3:        sigs.append("VCP tightening")
        if pct_hi < 5:      sigs.append("Near 52W high")
        if not sigs:        sigs.append(f"SEPA {sepa}/7")
        sector = ""
        try: sector = t.info.get('sector','') or t.info.get('industry','') or ''
        except: pass
        try: name = t.info.get('longName', ticker.replace('.AX',''))
        except: name = ticker.replace('.AX','')
        tr  = "strongly uptrending" if chg250d > 40 else "uptrending" if chg250d > 15 else "recovering"
        mas = "fully aligned (Price>MA50>MA150>MA200)" if (c_ma50 and c_ma150 and c_ma200) else "partially aligned"
        vls = f"Volume is {volr}x the 50-day average" if volr >= 1.5 else f"Volume at {volr}x average"
        vcpd = ["no base","early base","developing VCP","good VCP (volume drying up)","textbook VCP (volume at lows)"][vcp]
        analysis = (f"{name} is {tr} over 12 months ({fmt_pct(chg250d)}), MAs {mas}. "
                    f"Forming {vcpd}, {pct_hi}% below 52W high of ${round(hi52,2)}. "
                    f"{vls}. SEPA {sepa}/7, PVR {pvr}.")
        return {
            "ticker": ticker.replace('.AX',''), "name": name, "sector": sector,
            "price": round(price,3), "change": round(chg1d,2),
            "ma50": ma50, "ma150": ma150, "ma200": ma200,
            "volRatio": volr, "pvr": pvr, "vcpScore": vcp, "sepaScore": sepa,
            "pctFromHigh": pct_hi, "pctAboveLow": pct_lo,
            "hi52": round(hi52,2), "lo52": round(lo52,2),
            "chg5d": round(chg5d,2), "chg60d": round(chg60d,2), "chg250d": round(chg250d,2),
            "mktcap": int(mktcap), "mktcapFmt": fmt_cap(mktcap), "status": status,
            "checks": {"ma50":c_ma50,"ma150":c_ma150,"ma200":c_ma200,
                       "trend":c_trend,"high":c_high,"low":c_low,"vol":c_vol},
            "shortSignal": " · ".join(sigs[:3]), "analysis": analysis,
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
            if done % 20 == 0:
                print(f"  {done}/{len(ASX_TICKERS)} done, {len(results)} passed")
            time.sleep(0.05)
    results.sort(key=lambda x: (x['sepaScore'], x['vcpScore']), reverse=True)
    return results

def publish(html_path):
    if not NETLIFY_TOKEN or not NETLIFY_SITE_ID:
        print("Netlify not configured — skipping publish")
        return
    print("Publishing to Netlify...")
    with open(html_path, 'rb') as f:
        content = f.read()
    sha = hashlib.sha1(content).hexdigest()
    r = requests.post(
        f"https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_ID}/deploys",
        headers={"Authorization": f"Bearer {NETLIFY_TOKEN}", "Content-Type": "application/json"},
        json={"files": {"/index.html": sha}})
    deploy = r.json()
    did = deploy.get("id")
    if not did:
        print(f"Deploy failed: {deploy}")
        return
    r2 = requests.put(
        f"https://api.netlify.com/api/v1/deploys/{did}/files/index.html",
        headers={"Authorization": f"Bearer {NETLIFY_TOKEN}", "Content-Type": "application/octet-stream"},
        data=content)
    if r2.status_code == 200:
        print(f"Published: {deploy.get('ssl_url') or deploy.get('url')}")
    else:
        print(f"Upload failed: {r2.status_code}")

if __name__ == "__main__":
    print(f"SEPA+VCP ASX Screener — {date.today()}")
    data = fetch_all()
    b = sum(1 for r in data if r['status'] == 'breakout')
    p = sum(1 for r in data if r['status'] == 'near-pivot')
    w = sum(1 for r in data if r['status'] == 'watch')
    print(f"Results: {len(data)} | Breakouts:{b} | Near Pivot:{p} | Watch:{w}")
    if not data:
        print("No stocks passed filters.")
        exit()
    import build_dashboard
    html = build_dashboard.build(data)
    os.makedirs('data', exist_ok=True)
    import json as js
    with open('data/latest.json', 'w') as f:
        js.dump({"updated": date.today().isoformat(), "data": data}, f)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Dashboard built: {len(html):,} chars")
    publish('index.html')
    print("Done!")
