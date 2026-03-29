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

# Create a robust session to bypass Yahoo Finance Blocks on GitHub Actions
session = requests.Session()
retry = Retry(total=5, backoff_factor=2, status_forcelist=[ 429, 500, 502, 503, 504 ])
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive"
})

ASX_TICKERS = [
    "CBA.AX","BHP.AX","RIO.AX","NEM.AX","WBC.AX","NAB.AX","ANZ.AX","WES.AX",
    "MQG.AX","CSL.AX","WDS.AX","FMG.AX","TLS.AX","GMG.AX","XYZ.AX","RMD.AX",
    "WOW.AX","TCL.AX","QBE.AX","SIG.AX","BXB.AX","COL.AX","ALL.AX","AMC.AX",
    "NST.AX","STO.AX","EVN.AX","AAI.AX","NWS.AX","ORG.AX","LYC.AX","REA.AX",
    "FPH.AX","S32.AX","SUN.AX","IAG.AX","SCG.AX","SGH.AX","PLS.AX","CPU.AX",
    "JHX.AX","SOL.AX","WTC.AX","QAN.AX","APA.AX","XRO.AX","PME.AX","MPL.AX",
    "MEZ.AX","TLC.AX","BSL.AX","AIA.AX","MIN.AX","COH.AX","YAL.AX","VCX.AX",
    "NXG.AX","DPM.AX","SGP.AX","SHL.AX","ALQ.AX","ASX.AX","IFT.AX","LNW.AX",
    "ORI.AX","RHC.AX","TNE.AX","CHC.AX","REH.AX","GPT.AX","QUB.AX","CAR.AX",
    "AFI.AX","JBH.AX","ALD.AX","TPG.AX","MCY.AX","CSC.AX","WHC.AX","CEN.AX",
    "SFR.AX","NXT.AX","MGR.AX","A2M.AX","RMS.AX","AZJ.AX","PRU.AX","HUB.AX",
    "AGL.AX","GGP.AX","ARG.AX","DXS.AX","GMD.AX","ALX.AX","HVN.AX","APE.AX",
    "EDV.AX","IGO.AX","AII.AX","CDA.AX","BEN.AX","CGF.AX","WOR.AX","LTR.AX",
    "DNL.AX","NWL.AX","CWY.AX","DOW.AX","WGX.AX","GQG.AX","PDN.AX","SEK.AX",
    "NHC.AX","RRL.AX","CMM.AX","360.AX","SDF.AX","TLX.AX","BOQ.AX","VNT.AX",
    "ANN.AX","VAU.AX","VEA.AX","NIC.AX","EBO.AX","NSR.AX","SGM.AX","BRG.AX",
    "BFL.AX","4DX.AX","DRO.AX","WAF.AX","CNU.AX","MTS.AX","EMR.AX","TUA.AX",
    "SPK.AX","IFL.AX","PNI.AX","AMP.AX","AUB.AX","NHF.AX","TWE.AX","SUL.AX",
    "BPT.AX","ILU.AX","CIA.AX","MND.AX","FBU.AX","PXA.AX","MSB.AX","MFF.AX",
    "RSG.AX","BWP.AX","NWH.AX","SMR.AX","DBI.AX","RGN.AX","LSF.AX","HDN.AX",
    "CLW.AX","LOV.AX","RWC.AX","ORA.AX","MXT.AX","LLC.AX","FLT.AX","SX2.AX",
    "CQR.AX","TAH.AX","OBM.AX","BGL.AX","DRR.AX","EVT.AX","GNE.AX","ASB.AX",
    "ZIP.AX","PMV.AX","FRW.AX","IMD.AX","WAM.AX","ALK.AX","REG.AX","WLE.AX",
    "VGN.AX","PPT.AX","PDI.AX","CIP.AX","ZIM.AX","RYM.AX","RDX.AX","BGA.AX",
    "PRN.AX","MFG.AX","ARB.AX","ASK.AX","GLF.AX","GYG.AX","DTR.AX","SLC.AX",
    "DYL.AX","EOS.AX","JDO.AX","MGH.AX","GDG.AX","GOZ.AX","DMP.AX","EQR.AX",
    "MAQ.AX","INA.AX","CBO.AX","CYL.AX","ELD.AX","VUL.AX","WPR.AX","MAD.AX",
    "SRG.AX","DDR.AX","MAH.AX","RXR.AX","NEU.AX","SLX.AX","GNC.AX","KAR.AX",
    "LIN.AX","NEC.AX","SNL.AX","MAF.AX","ABB.AX","HLI.AX","BKI.AX","MI6.AX",
    "MP1.AX","DVP.AX","ELV.AX","NCK.AX","GNP.AX","CNI.AX","ARF.AX","TEA.AX",
    "SRL.AX","AUI.AX","PGF.AX","IRE.AX","GCI.AX","ARU.AX","UOS.AX","FFM.AX",
    "PNR.AX","ELS.AX","CU6.AX","ERA.AX","TBN.AX","SSM.AX","AIZ.AX","BRE.AX",
    "MLX.AX","BCI.AX","NAN.AX","OCL.AX","KCN.AX","SIQ.AX","IPX.AX","PYC.AX",
    "IEL.AX","DUI.AX","CKF.AX","LFG.AX","CAT.AX","APZ.AX","KLS.AX","DTL.AX",
    "RIC.AX","CMW.AX","WA1.AX","MMS.AX","HSN.AX","PL8.AX","HGH.AX","NGI.AX",
    "WEB.AX","CQE.AX","QRI.AX","LFS.AX","HMC.AX","RPL.AX","CIN.AX","DGT.AX",
    "GLS.AX","ABG.AX","PWH.AX","AOV.AX","BVS.AX","IDX.AX","TPW.AX","PPC.AX",
    "IPH.AX","C79.AX","FCL.AX","WBT.AX","WGN.AX","AAC.AX","VSL.AX","SDR.AX",
    "PPM.AX","RFF.AX","AVR.AX","NUF.AX","CCL.AX","MYS.AX","WGB.AX","SXE.AX",
    "DJW.AX","DXI.AX","CVL.AX","BMN.AX","QAL.AX","ING.AX","A4N.AX","SBM.AX",
    "CCP.AX","CXO.AX","BC8.AX","SRV.AX","TVN.AX","BNZ.AX","FML.AX","KKC.AX",
    "GNG.AX","SMI.AX","DUR.AX","HM1.AX","TCG.AX","GTK.AX","CWP.AX","BOE.AX",
    "UNI.AX","EIQ.AX","PNV.AX","EHL.AX","FGG.AX","IMR.AX","29M.AX","WHF.AX",
    "OPH.AX","MIR.AX","RXL.AX","LIC.AX","WIA.AX","COF.AX","PFP.AX","MYR.AX",
    "GWA.AX","MAU.AX","SHV.AX","SYL.AX","EQT.AX","CRN.AX","TWR.AX","FGX.AX",
    "LRV.AX","CHN.AX","SHA.AX","FPR.AX","LYL.AX","JMS.AX","AEF.AX","WC8.AX",
    "AYA.AX","STK.AX","ASG.AX","AFG.AX","CUV.AX","JIN.AX","FRS.AX","NMG.AX",
    "MEK.AX","A1G.AX","OML.AX","AEL.AX","AIS.AX","RAC.AX","AX1.AX","WQG.AX",
    "PIC.AX","OBL.AX","SKS.AX","AUC.AX","CDP.AX","SPZ.AX","IPG.AX","SVM.AX",
    "HZN.AX","MGX.AX","GLN.AX","BAP.AX","MMI.AX","MEI.AX","ALI.AX","WMI.AX",
    "NXL.AX","MTM.AX","EOL.AX","TYR.AX","BFG.AX","HLS.AX","AGI.AX","CVW.AX",
    "THL.AX","AMI.AX","PE1.AX","ASL.AX","BTR.AX","IGL.AX","APX.AX","QOR.AX",
    "INR.AX","CGS.AX","ACL.AX","ASM.AX","TTT.AX","DXC.AX","EUR.AX","BTL.AX",
    "BLX.AX","USL.AX","A1M.AX","TOK.AX","AZY.AX","RMC.AX","STX.AX","LGI.AX",
    "CEL.AX","VYS.AX","KGN.AX","TGN.AX","KSL.AX","SVT.AX","BRN.AX","BCN.AX",
    "PGC.AX","HCW.AX","LOT.AX","HUM.AX","VGL.AX","CTM.AX","GDI.AX","PPS.AX",
    "AAR.AX","FID.AX","TRE.AX","SST.AX","TBR.AX","RHI.AX","NVA.AX","SVR.AX",
    "PIA.AX","PBH.AX","PAC.AX","AMH.AX","MM8.AX","COG.AX","EBR.AX","MPW.AX",
    "FDR.AX","OMA.AX","DUG.AX","GVF.AX","CAY.AX","ACF.AX","GRX.AX","ATR.AX",
    "SXL.AX","WWI.AX","AEM.AX","PC2.AX","TOR.AX","AMA.AX","HCH.AX","TM1.AX",
    "KCC.AX","ACE.AX","MCM.AX","MVF.AX","FEX.AX","PSC.AX","HRN.AX","BML.AX",
    "SS1.AX","HRZ.AX","AQI.AX","ERM.AX","GG8.AX","ADH.AX","XRF.AX","TGM.AX",
    "WAX.AX","NVX.AX","VMM.AX","CDM.AX","A11.AX","EGH.AX","HLO.AX","PEN.AX",
    "NTU.AX","MYG.AX","BIS.AX","LAU.AX","TTM.AX","EML.AX","ORN.AX","KPG.AX",
    "GDF.AX","GRR.AX","FRI.AX","TTX.AX","STN.AX","LAM.AX","AD8.AX","CYM.AX",
    "POL.AX","WTM.AX","WRK.AX","CCV.AX","BHM.AX","WJL.AX","ETM.AX","OCC.AX",
    "LDX.AX","BBN.AX","CEH.AX","ATA.AX","BGD.AX","HAV.AX","WAR.AX",
    "ARX.AX","SPL.AX","AUE.AX","DXB.AX","WMA.AX","CUP.AX","EZL.AX","OMH.AX",
    "VTM.AX","SYR.AX","MYX.AX","BET.AX","EGR.AX","ARR.AX","TER.AX","GEM.AX",
    "SPD.AX","CAA.AX","EXR.AX","LKE.AX","SSG.AX","TGF.AX","JYC.AX","RNU.AX",
    "KOV.AX","CVN.AX","RCT.AX","NZM.AX","AVH.AX","COI.AX","MTO.AX","BBL.AX",
    "CVV.AX","AGE.AX","ELT.AX","RYD.AX","ONE.AX","MM1.AX","IVR.AX","FWD.AX",
    "KAU.AX","VVA.AX","FDV.AX","KGL.AX","SDI.AX","PLT.AX","CY5.AX","RDY.AX",
    "BTI.AX","FTI.AX","EMV.AX","FSA.AX","SGI.AX","DLI.AX","SKY.AX","CLX.AX",
    "CLV.AX","FXG.AX","MKR.AX","VLS.AX","SOM.AX","TLG.AX","NYR.AX","GML.AX",
    "RCE.AX","ENR.AX","MHJ.AX","BXN.AX","WAA.AX","ALC.AX","ERD.AX","SEC.AX",
    "SEA.AX","BWN.AX","OFX.AX","MEU.AX","AHC.AX","ZEO.AX","LSX.AX","BRI.AX",
    "ATX.AX","SHJ.AX","ACW.AX","GL1.AX","KAI.AX","URF.AX","FHE.AX","EL8.AX",
    "HGO.AX","PEX.AX","SLS.AX","MLG.AX","AEE.AX","ARL.AX","CXL.AX","QPM.AX",
    "PAR.AX","CNB.AX","SNC.AX","ART.AX","ANG.AX","HAS.AX","TKM.AX","TWD.AX",
    "ILA.AX","AL3.AX","DEV.AX","RML.AX","CRD.AX","FAL.AX","EM3.AX","AQZ.AX",
    "DRE.AX","CUE.AX","WOT.AX","GYG.AX","TEA.AX","NWL.AX",
]
ASX_TICKERS = list(dict.fromkeys(ASX_TICKERS))


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

def _quarterly_revenue_trend(ticker_obj):
    try:
        qf = ticker_obj.quarterly_financials
        if qf is None or qf.empty: return None, None, []
        rev_row = None
        for label in ['Total Revenue', 'Revenue', 'Net Revenue', 'Revenues']:
            if label in qf.index:
                rev_row = qf.loc[label]
                break
        if rev_row is None: return None, None, []
        rev_row = rev_row.dropna()
        if len(rev_row) < 2: return None, None, []
        rev_vals = list(rev_row.values)
        rev_cols = list(rev_row.index)
        quarters = []
        for i, (col, val) in enumerate(zip(rev_cols, rev_vals)):
            if i >= 4: break
            try:
                lbl = col.strftime('%b %y') if hasattr(col, 'strftime') else str(col)[:7]
                quarters.append((lbl, round(float(val) / 1e6, 1)))
            except Exception: pass
        rev_growth_pct = None
        if len(rev_vals) >= 4:
            q0, q4 = float(rev_vals[0]), float(rev_vals[3])
            if q4 != 0: rev_growth_pct = round((q0 - q4) / abs(q4) * 100, 1)
        rev_trend = None
        if len(rev_vals) >= 3:
            q0, q1, q2 = float(rev_vals[0]), float(rev_vals[1]), float(rev_vals[2])
            if q1 != 0 and q2 != 0:
                chg_recent = (q0 - q1) / abs(q1) * 100
                chg_prev   = (q1 - q2) / abs(q2) * 100
                if q0 > q1 > q2: rev_trend = 'accelerating' if chg_recent > chg_prev else 'growing'
                elif q0 > q1: rev_trend = 'growing'
                elif q0 < q1: rev_trend = 'declining'
                else: rev_trend = 'flat'
        elif len(rev_vals) >= 2:
            q0, q1 = float(rev_vals[0]), float(rev_vals[1])
            if q1 != 0: rev_trend = 'growing' if q0 > q1 else 'declining' if q0 < q1 else 'flat'
        return rev_growth_pct, rev_trend, quarters
    except Exception: return None, None, []

def _quarterly_eps_trend(ticker_obj):
    try:
        qe = ticker_obj.quarterly_earnings
        if qe is None or qe.empty:
            qf = ticker_obj.quarterly_financials
            if qf is not None and not qf.empty:
                for label in ['Net Income', 'Net Income Common Stockholders', 'Net Income Applicable To Common Shares']:
                    if label in qf.index:
                        ni = qf.loc[label].dropna()
                        if len(ni) >= 2:
                            vals = list(ni.values)
                            g = round((float(vals[0]) - float(vals[1])) / abs(float(vals[1])) * 100, 1) if vals[1] != 0 else None
                            tr = 'growing' if vals[0] > vals[1] else 'declining' if vals[0] < vals[1] else 'flat'
                            return g, tr, []
            return None, None, []
        eps_col = 'Reported EPS' if 'Reported EPS' in qe.columns else (qe.columns[0] if len(qe.columns) else None)
        if eps_col is None: return None, None, []
        eps_vals = qe[eps_col].dropna()
        if len(eps_vals) < 2: return None, None, []
        vals = list(eps_vals.values)
        quarters = [(str(idx)[:7], round(float(v), 3)) for idx, v in zip(eps_vals.index[:4], vals[:4])]
        eps_growth_pct = None
        if len(vals) >= 4 and vals[3] != 0: eps_growth_pct = round((float(vals[0]) - float(vals[3])) / abs(float(vals[3])) * 100, 1)
        elif len(vals) >= 2 and vals[1] != 0: eps_growth_pct = round((float(vals[0]) - float(vals[1])) / abs(float(vals[1])) * 100, 1)
        eps_trend = None
        if len(vals) >= 2: eps_trend = 'growing' if float(vals[0]) > float(vals[1]) else 'declining' if float(vals[0]) < float(vals[1]) else 'flat'
        return eps_growth_pct, eps_trend, quarters
    except Exception: return None, None, []

def _fetch_events(ticker_obj):
    next_earnings = next_event_label = next_ex_div = days_to_event = None
    today = date.today()
    try:
        cal = ticker_obj.calendar
        if isinstance(cal, dict):
            ed_list = cal.get('Earnings Date', [])
            if not ed_list and 'earningsDate' in cal: ed_list = cal.get('earningsDate', [])
            if isinstance(ed_list, (list, tuple)) and ed_list: ed = _parse_date(ed_list[0])
            elif ed_list and not isinstance(ed_list, (list, tuple)): ed = _parse_date(ed_list)
            else: ed = None
            if ed:
                days = (ed - today).days
                if -30 <= days <= 180:
                    next_earnings = str(ed)
                    days_to_event = days
                    if days == 0: next_event_label = "⚡ RESULTS TODAY"
                    elif 0 < days <= 7: next_event_label = f"⚡ Results in {days}d"
                    elif 0 < days <= 30: next_event_label = f"📅 Results in {days}d"
                    elif 0 < days <= 180: next_event_label = f"📅 Results {ed.strftime('%d %b')}"
                    else: next_event_label = f"Results {abs(days)}d ago"
            xd = cal.get('Ex-Dividend Date') or cal.get('exDividendDate')
            if xd:
                d2 = _parse_date(xd)
                if d2 and (d2 - today).days >= -7: next_ex_div = d2.strftime('%d %b %Y')
        elif hasattr(cal, 'columns'):
            for col in ['Earnings Date', 'earningsDate']:
                if col in cal.columns and not cal[col].empty:
                    ed = _parse_date(cal[col].iloc[0])
                    if ed:
                        days = (ed - today).days
                        if -30 <= days <= 180:
                            next_earnings = str(ed)
                            days_to_event = days
                            if days == 0: next_event_label = "⚡ RESULTS TODAY"
                            elif 0 < days <= 7: next_event_label = f"⚡ Results in {days}d"
                            elif 0 < days <= 30: next_event_label = f"📅 Results in {days}d"
                            elif 0 < days <= 180: next_event_label = f"📅 Results {ed.strftime('%d %b')}"
                            else: next_event_label = f"Results {abs(days)}d ago"
                    break
    except Exception: pass
    if not next_earnings:
        try:
            ed_df = ticker_obj.get_earnings_dates(limit=4)
            if ed_df is not None and not ed_df.empty:
                for idx in ed_df.index:
                    d = _parse_date(idx)
                    if d and d >= today:
                        days = (d - today).days
                        if days <= 180:
                            next_earnings = str(d)
                            days_to_event = days
                            next_event_label = f"⚡ Results in {days}d" if days <= 7 else f"📅 Results in {days}d" if days <= 30 else f"📅 Results {d.strftime('%d %b')}"
                        break
        except Exception: pass
    return next_earnings, next_event_label, next_ex_div, days_to_event

def fetch_stock(ticker):
    # Added sleep here to ensure workers space out their Yahoo Finance API requests and avoid Rate Limits
    time.sleep(1 + random.uniform(0, 1))

    try:
        # Removed session=session which caused Yahoo API exception
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
        ma50 = round(float(closes.tail(50).mean()), 3)
        ma150 = round(float(closes.tail(150).mean()), 3) if len(closes) >= 150 else round(float(closes.mean()), 3)
        ma200 = round(float(closes.tail(200).mean()), 3) if len(closes) >= 200 else round(float(closes.mean()), 3)
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

        chg1d = round((price - float(closes.iloc[-2])) / float(closes.iloc[-2]) * 100, 2) if len(closes) >= 2 else 0
        chg5d, chg10d, chg20d, chg60d = perf(5), perf(10), perf(20), perf(60)
        chg250d = perf(min(250, len(closes) - 1))

        avg50v = float(volumes.tail(50).mean())
        volr = round(volume / avg50v, 2) if avg50v > 0 else 1.0

        c_ma50, c_ma150, c_ma200 = price > ma50, ma50 > ma150, ma150 > ma200
        c_trend, c_high, c_low, c_vol = ma200 > ma200p, pct_hi <= 25, pct_lo >= 25, volr >= VOL_BREAKOUT

        sepa = sum([c_ma50, c_ma150, c_ma200, c_trend, c_high, c_low, c_vol])
        if sepa < SEPA_MIN: return None

        vcp = min(sum([abs(chg5d) < abs(chg10d), abs(chg10d) < abs(chg20d), abs(chg20d) < abs(chg60d), volr < 0.8]), 4)
        ve = volr - 1.0
        pvr = min(round(abs(chg1d) / ve, 2) if ve > 0.1 else round(abs(chg1d) * 2, 2), 9.99)

        if sepa >= 5 and c_vol and vcp >= VCP_MIN: status = "breakout"
        elif sepa >= 4 and vcp >= VCP_MIN and pct_hi <= 15: status = "near-pivot"
        else: status = "watch"

        sector = name = ""
        rev_growth_pct = eps_growth_pct = net_margin_pct = trailing_eps = forward_eps = None
        fund_score = 0
        rev_trend = eps_trend = None
        rev_quarters = eps_quarters = []

        try:
            inf2 = t.info
            sector = inf2.get('sector', '') or inf2.get('industry', '') or ''
            name = inf2.get('longName', ticker.replace('.AX', ''))
            pm, te, fe = inf2.get('profitMargins'), inf2.get('trailingEps'), inf2.get('forwardEps')
            if pm is not None: net_margin_pct = round(pm * 100, 1)
            if te is not None: trailing_eps = round(float(te), 3)
            if fe is not None: forward_eps = round(float(fe), 3)

            rev_growth_pct, rev_trend, rev_quarters = _quarterly_revenue_trend(t)
            if rev_growth_pct is None:
                rg = inf2.get('revenueGrowth')
                if rg is not None: rev_growth_pct = round(rg * 100, 1)

            eps_growth_pct, eps_trend, eps_quarters = _quarterly_eps_trend(t)
            if eps_growth_pct is None:
                eg = inf2.get('earningsGrowth')
                if eg is not None: eps_growth_pct = round(eg * 100, 1)

            if rev_growth_pct is not None and rev_growth_pct > 5: fund_score += 1
            if rev_growth_pct is not None and rev_growth_pct > 20: fund_score += 1
            if eps_growth_pct is not None and eps_growth_pct > 0: fund_score += 1
            fund_score = min(fund_score, 3)
        except Exception:
            name = ticker.replace('.AX', '')

        next_earnings, next_event_label, next_ex_div, days_to_event = _fetch_events(t)

        sigs = []
        if c_vol: sigs.append(f"Vol {volr}x avg")
        if chg250d > 50: sigs.append(f"+{chg250d}% 12M")
        if vcp >= 3: sigs.append("VCP tightening")
        if pct_hi < 5: sigs.append("Near 52W high")
        if rev_trend == 'accelerating': sigs.append("↑↑ Revenue accelerating")
        elif rev_trend == 'growing': sigs.append("↑ Revenue growing")
        if next_event_label and ('⚡' in next_event_label or '📅' in next_event_label): sigs.append(next_event_label)
        if not sigs: sigs.append(f"SEPA {sepa}/7")

        tr = "strongly uptrending" if chg250d > 40 else "uptrending" if chg250d > 15 else "recovering"
        mas = "fully aligned (Price>MA50>MA150>MA200)" if (c_ma50 and c_ma150 and c_ma200) else "partially aligned"
        vls = f"Volume is {volr}x the 50-day average" if volr >= 1.5 else f"Volume at {volr}x average"
        vcpd = ["no base","early base","developing VCP","good VCP (volume drying up)","textbook VCP (volume at lows)"][vcp]

        fund_ctx = ""
        if rev_growth_pct is not None:
            trend_desc = " (accelerating)" if rev_trend == 'accelerating' else " (growing QoQ)" if rev_trend == 'growing' else ""
            if rev_growth_pct > 20: fund_ctx += f" Net revenue growing strongly +{rev_growth_pct}% YoY{trend_desc} — fundamental momentum supports breakout."
            elif rev_growth_pct > 5: fund_ctx += f" Net revenue +{rev_growth_pct}% YoY{trend_desc}."
            elif rev_growth_pct < 0: fund_ctx += f" Net revenue declined {rev_growth_pct}% YoY — if monitor fundamentals before entry."
        if eps_growth_pct is not None and eps_growth_pct > 0: fund_ctx += f" EPS growth +{eps_growth_pct}% confirms expanding profitability."
        elif trailing_eps and trailing_eps > 0: fund_ctx += f" Profitable (trailing EPS ${trailing_eps})."

        catalyst = f" CATALYST: {next_event_label}." if next_event_label else ""

        analysis = (
            f"{name} is {tr} over 12 months ({fmt_pct(chg250d)}), MAs {mas}. "
            f"Forming {vcpd}, {pct_hi}% below 52W high of ${round(hi52,2)}. "
            f"{vls}. SEPA {sepa}/7, PVR {pvr}. "
            f"{fund_ctx}{catalyst}"
        )

        return {
            "ticker": ticker.replace('.AX',''), "name": name, "sector": sector,
            "price": round(price,3), "change": round(chg1d,2),
            "ma50": ma50, "ma150": ma150, "ma200": ma200,
            "volRatio": volr, "pvr": pvr, "vcpScore": vcp, "sepaScore": sepa,
            "pctFromHigh": pct_hi, "pctAboveLow": pct_lo,
            "hi52": round(hi52,2), "lo52": round(lo52,2),
            "chg5d": round(chg5d,2), "chg60d": round(chg60d,2), "chg250d": round(chg250d,2),
            "mktcap": int(mktcap), "mktcapFmt": fmt_cap(mktcap), "status": status,
            "checks": {"ma50":c_ma50,"ma150":c_ma150,"ma200":c_ma200,"trend":c_trend,"high":c_high,"low":c_low,"vol":c_vol},
            "shortSignal": " · ".join(sigs[:3]), "analysis": analysis,
            "revGrowth": rev_growth_pct, "revTrend": rev_trend, "revQuarters": rev_quarters,
            "epsGrowth": eps_growth_pct, "epsTrend": eps_trend, "epsQuarters": eps_quarters,
            "netMargin": net_margin_pct, "trailingEps": trailing_eps, "forwardEps": forward_eps, "fundScore": fund_score,
            "nextEarnings": next_earnings, "nextEventLabel": next_event_label, "nextExDiv": next_ex_div, "daysToEvent": days_to_event
        }

    except Exception as e:
        print(f"  {ticker}: {e}")
        return None

def fetch_all():
    print(f"Fetching {len(ASX_TICKERS)} ASX stocks...")
    results = []
    # FIX: REDUCED MAX WORKERS TO 2 TO AVOID YAHOO FINANCE RATE LIMITING!
    with ThreadPoolExecutor(max_workers=2) as ex:
        futures = {ex.submit(fetch_stock, t): t for t in ASX_TICKERS}
        done = 0
        for f in as_completed(futures):
            done += 1
            r = f.result()
            if r: results.append(r)
            if done % 10 == 0:
                print(f"  {done}/{len(ASX_TICKERS)} done, {len(results)} passed")
    results.sort(key=lambda x: (x['sepaScore'], x['vcpScore']), reverse=True)
    return results

def publish(html_path):
    if not NETLIFY_TOKEN or not NETLIFY_SITE_ID: return
    print("Publishing to Netlify...")
    try:
        with open(html_path, 'rb') as f: content = f.read()
        sha = hashlib.sha1(content).hexdigest()
        r = requests.post(f"https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_ID}/deploys", headers={"Authorization": f"Bearer {NETLIFY_TOKEN}", "Content-Type": "application/json"}, json={"files": {"/index.html": sha}})
        try:
            deploy = r.json()
        except BaseException as e:
            print(f"Netlify gave non-JSON response. HTTP {r.status_code}. Output: {r.text[:200]}")
            return
        did = deploy.get("id")
        if not did: return
        r2 = requests.put(f"https://api.netlify.com/api/v1/deploys/{did}/files/index.html", headers={"Authorization": f"Bearer {NETLIFY_TOKEN}", "Content-Type": "application/octet-stream"}, data=content)
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
    print(f"Results: {len(data)} | Breakouts:{b} | Near Pivot:{p} | Watch:{w}")
    if not data: 
        print("No stocks passed filters, exiting instead of building an empty report.")
        exit()
    try:
        import build_dashboard
        html = build_dashboard.build(data)
        os.makedirs('data', exist_ok=True)
        import json as js
        with open('data/latest.json', 'w') as f: js.dump({"updated": date.today().isoformat(), "data": data}, f)
        with open('index.html', 'w', encoding='utf-8') as f: f.write(html)
        print(f"Dashboard built: {len(html):,} chars")
        publish('index.html')
    except Exception as ex:
        print(f"Script crashed in the final build/deploy phase: {ex}")
