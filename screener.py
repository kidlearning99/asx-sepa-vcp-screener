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
    "DYL.AX","EOS.AX","DTRO.AX","JDO.AX","MGH.AX","GDG.AX","GOZ.AX","DMP.AX",
    "EQR.AX","MAQ.AX","INA.AX","CBO.AX","CYL.AX","ELD.AX","VUL.AX","WPR.AX",
    "MAD.AX","SRG.AX","DDR.AX","MAH.AX","RXR.AX","NEU.AX","SLX.AX","GNC.AX",
    "KAR.AX","LIN.AX","NEC.AX","SNL.AX","MAF.AX","ABB.AX","HLI.AX","BKI.AX",
    "MI6.AX","MP1.AX","DVP.AX","ELV.AX","NCK.AX","GNP.AX","CNI.AX","ARF.AX",
    "TEA.AX","SRL.AX","ORE.AX","AUI.AX","PGF.AX","IRE.AX","GCI.AX","ARU.AX",
    "UOS.AX","FFM.AX","PNR.AX","ELS.AX","CU6.AX","ERA.AX","TBN.AX","SSM.AX",
    "AIZ.AX","BRE.AX","MLX.AX","BCI.AX","NAN.AX","MC2.AX","OCL.AX","KCN.AX",
    "SIQ.AX","IPX.AX","PYC.AX","IEL.AX","DUI.AX","CKF.AX","LFG.AX","CAT.AX",
    "APZ.AX","KLS.AX","DTL.AX","RIC.AX","CMW.AX","WA1.AX","MMS.AX","HSN.AX",
    "PL8.AX","HGH.AX","NGI.AX","CHI.AX","WEB.AX","CQE.AX","QRI.AX","LFS.AX",
    "HMC.AX","SGLLV.AX","RPL.AX","CIN.AX","DGT.AX","GLS.AX","ABG.AX","BGP.AX",
    "PWH.AX","AOV.AX","BVS.AX","IDX.AX","TPW.AX","PPC.AX","IPH.AX","SGR.AX",
    "C79.AX","FCL.AX","WBT.AX","WGN.AX","PMT.AX","AAC.AX","VSL.AX","SDR.AX",
    "PPM.AX","RFF.AX","AVR.AX","NUF.AX","CCL.AX","MYS.AX","WGB.AX","SXE.AX",
    "DJW.AX","DXI.AX","CVL.AX","BMN.AX","QAL.AX","ING.AX","A4N.AX","SBM.AX",
    "CCP.AX","CXO.AX","BC8.AX","SRV.AX","SKC.AX","TVN.AX","BNZ.AX","FML.AX",
    "KKC.AX","GNG.AX","SMI.AX","DUR.AX","HM1.AX","TCG.AX","GTK.AX","CWP.AX",
    "BOE.AX","UNI.AX","EIQ.AX","PNV.AX","EHL.AX","FGG.AX","IMR.AX","BMC.AX",
    "29M.AX","WHF.AX","OPH.AX","MIR.AX","RXL.AX","LIC.AX","WIA.AX","KSC.AX",
    "COF.AX","MOT.AX","PFP.AX","MYR.AX","GWA.AX","MAU.AX","MA1.AX","SHV.AX",
    "SYL.AX","EQT.AX","CRN.AX","TWR.AX","FGX.AX","LRV.AX","CHN.AX","SHA.AX",
    "FPR.AX","LYL.AX","JMS.AX","AEF.AX","WC8.AX","AYA.AX","STK.AX","ASG.AX",
    "AFG.AX","CUV.AX","JIN.AX","FRS.AX","NMG.AX","MEK.AX","A1G.AX","OML.AX",
    "AEL.AX","AIS.AX","OCA.AX","RAC.AX","AX1.AX","WQG.AX","PIC.AX","OBL.AX",
    "SKS.AX","AUC.AX","SGQ.AX","CDP.AX","SPZ.AX","IPG.AX","SVM.AX","HZN.AX",
    "MGX.AX","GLN.AX","BAP.AX","MMI.AX","MEI.AX","ALI.AX","WMI.AX","TVNOA.AX",
    "NXL.AX","MTM.AX","EOL.AX","TYR.AX","BFG.AX","HLS.AX","AGI.AX","CVW.AX",
    "THL.AX","AMI.AX","PE1.AX","ASL.AX","BTR.AX","IGL.AX","APX.AX","QOR.AX",
    "INR.AX","CGS.AX","ACL.AX","ASM.AX","TTT.AX","DXC.AX","EUR.AX","BTL.AX",
    "BLX.AX","USL.AX","A1M.AX","TOK.AX","AZY.AX","RMC.AX","STX.AX","AIH.AX",
    "LGI.AX","CEL.AX","VYS.AX","KGN.AX","TGN.AX","KSL.AX","SKT.AX","SVL.AX",
    "BRN.AX","BCN.AX","PGC.AX","HCW.AX","LOT.AX","FRSOA.AX","HUM.AX","VGL.AX",
    "CTM.AX","GDI.AX","PPS.AX","AAR.AX","FID.AX","TRE.AX","KP2.AX","SST.AX",
    "TBR.AX","RHI.AX","NVA.AX","SVR.AX","PIA.AX","REV.AX","PBH.AX","PAC.AX",
    "AMH.AX","MM8.AX","COG.AX","EBR.AX","MPW.AX","SGQOC.AX","BM1.AX","MRE.AX",
    "FDR.AX","OMA.AX","DUG.AX","GVF.AX","CAY.AX","ACF.AX","GRX.AX","ATR.AX",
    "SXL.AX","WWI.AX","AEM.AX","PC2.AX","TOR.AX","AMA.AX","BOC.AX","HCH.AX",
    "REP.AX","SM1.AX","TM1.AX","3DA.AX","SFC.AX","KCC.AX","ACE.AX","MCM.AX",
    "MVF.AX","BCNOD.AX","FEX.AX","PSC.AX","HRN.AX","BML.AX","SS1.AX","HRZ.AX",
    "AQI.AX","ERM.AX","GG8.AX","ADH.AX","XRF.AX","TGM.AX","WAX.AX","CVC.AX",
    "NVX.AX","VMM.AX","CDM.AX","A11.AX","PLA.AX","EGH.AX","HLO.AX","PEN.AX",
    "NTU.AX","MYG.AX","BIS.AX","RIV.AX","LED.AX","LAU.AX","TTM.AX","EML.AX",
    "PWR.AX","ORN.AX","KPG.AX","GDF.AX","GRR.AX","FRI.AX","TTX.AX","STN.AX",
    "LAM.AX","AD8.AX","WHI.AX","CYM.AX","POL.AX","BBT.AX","WTM.AX","WRK.AX",
    "CCV.AX","BHM.AX","6KA.AX","IMB.AX","WJL.AX","ETM.AX","SLD.AX","OCC.AX",
    "LDX.AX","BBN.AX","BKY.AX","EUROC.AX","CEH.AX","ATA.AX","BGD.AX","HAV.AX",
    "WAR.AX","ARX.AX","SPL.AX","AUE.AX","DXB.AX","WMA.AX","CUP.AX","TM1O.AX",
    "EZL.AX","OMH.AX","VTM.AX","SYR.AX","MYX.AX","BET.AX","EGR.AX","ARR.AX",
    "TER.AX","GEM.AX","SPD.AX","CAA.AX","EXR.AX","LKE.AX","SSG.AX","AS1.AX",
    "TGF.AX","JYC.AX","PRG.AX","RNU.AX","KOV.AX","CVN.AX","AR1.AX","RCT.AX",
    "NZM.AX","AVH.AX","COI.AX","MTO.AX","BBL.AX","CVV.AX","AGE.AX","ELT.AX",
    "RYD.AX","ONE.AX","MM1.AX","TSO.AX","IVR.AX","FWD.AX","KAU.AX","VVA.AX",
    "APW.AX","PEB.AX","FDV.AX","KGL.AX","SKO.AX","SDI.AX","PLT.AX","AEU.AX",
    "CY5.AX","RDY.AX","QGL.AX","BTI.AX","IKE.AX","TVNO.AX","FTI.AX","EMV.AX",
    "FSA.AX","SGI.AX","DLI.AX","SKY.AX","CLX.AX","CLV.AX","FXG.AX","EWC.AX",
    "MKR.AX","VLS.AX","SOM.AX","TLG.AX","NYR.AX","GML.AX","EPI.AX","GBM.AX",
    "RCE.AX","ENR.AX","MHJ.AX","BXN.AX","WAA.AX","GPR.AX","ALC.AX","ERD.AX",
    "SEC.AX","SEA.AX","ALR.AX","BWN.AX","OFX.AX","MEU.AX","AHC.AX","ZEO.AX",
    "BRL.AX","LSX.AX","ASMO.AX","BRI.AX","ATX.AX","SHJ.AX","CMA.AX","ACW.AX",
    "GL1.AX","AUEO.AX","KAI.AX","URF.AX","FHE.AX","EL8.AX","RND.AX","HGO.AX",
    "DAI.AX","PEX.AX","SLS.AX","VNL.AX","MLG.AX","GOW.AX","PLY.AX","AEE.AX",
    "AKM.AX","NOL.AX","ARL.AX","CXL.AX","QPM.AX","PAR.AX","CNB.AX","G50.AX",
    "SNC.AX","ART.AX","ANG.AX","HAS.AX","TKM.AX","TWD.AX","ILA.AX","MXI.AX",
    "AL3.AX","EMP.AX","VFY.AX","MPK.AX","DEV.AX","RML.AX","AT4.AX","OIL.AX",
    "SBZ.AX","CRD.AX","FAL.AX","EM3.AX","AQZ.AX","CAM.AX","GLB.AX","5EA.AX",
    "DRE.AX","CUE.AX","HPG.AX","PTN.AX","WOT.AX",
]
ASX_TICKERS = list(dict.fromkeys(ASX_TICKERS))


def fmt_cap(c):
    if c >= 1e12: return f"${c/1e12:.1f}T"
    if c >= 1e9:  return f"${c/1e9:.1f}B"
    if c >= 1e6:  return f"${c/1e6:.0f}M"
    return f"${c:.0f}"

def fmt_pct(v):
    return ('+' if v >= 0 else '') + str(round(v, 2)) + '%'


def _parse_earnings_date(raw):
    """Return a date object from various formats yfinance might give."""
    from datetime import datetime
    if raw is None:
        return None
    if hasattr(raw, 'date'):
        return raw.date()
    if isinstance(raw, str):
        try:
            return datetime.strptime(raw[:10], '%Y-%m-%d').date()
        except Exception:
            return None
    return None


def fetch_stock(ticker):
    try:
        t    = yf.Ticker(ticker)
        hist = t.history(period="1y")
        if hist.empty or len(hist) < 60:
            return None

        info     = t.fast_info
        price    = float(hist['Close'].iloc[-1])
        mktcap   = float(getattr(info, 'market_cap', 0) or 0)
        volume   = float(hist['Volume'].iloc[-1])
        if price <= 0 or mktcap < MIN_MARKET_CAP:
            return None

        closes  = hist['Close']
        volumes = hist['Volume']
        ma50    = round(float(closes.tail(50).mean()),  3)
        ma150   = round(float(closes.tail(150).mean()), 3) if len(closes) >= 150 else round(float(closes.mean()), 3)
        ma200   = round(float(closes.tail(200).mean()), 3) if len(closes) >= 200 else round(float(closes.mean()), 3)
        ma200p  = round(float(closes.tail(220).head(200).mean()), 3) if len(closes) >= 220 else ma200

        hi52   = float(closes.max())
        lo52   = float(closes.min())
        pct_hi = round(max(0, (hi52 - price) / hi52 * 100), 1) if hi52 > 0 else 0
        pct_lo = round((price - lo52) / lo52 * 100, 1)          if lo52 > 0 else 0

        def perf(n):
            if len(closes) > n:
                old = float(closes.iloc[-n])
                return round((price - old) / old * 100, 2) if old > 0 else 0
            return 0

        chg1d   = round((price - float(closes.iloc[-2])) / float(closes.iloc[-2]) * 100, 2) if len(closes) >= 2 else 0
        chg5d   = perf(5); chg10d = perf(10); chg20d = perf(20); chg60d = perf(60)
        chg250d = perf(min(250, len(closes) - 1))

        avg50v = float(volumes.tail(50).mean())
        volr   = round(volume / avg50v, 2) if avg50v > 0 else 1.0

        c_ma50  = price > ma50;  c_ma150 = ma50  > ma150; c_ma200 = ma150 > ma200
        c_trend = ma200 > ma200p; c_high  = pct_hi <= 25;  c_low   = pct_lo >= 25
        c_vol   = volr >= VOL_BREAKOUT
        sepa    = sum([c_ma50, c_ma150, c_ma200, c_trend, c_high, c_low, c_vol])
        if sepa < SEPA_MIN:
            return None

        vcp = 0
        if abs(chg5d)  < abs(chg10d):  vcp += 1
        if abs(chg10d) < abs(chg20d):  vcp += 1
        if abs(chg20d) < abs(chg60d):  vcp += 1
        if volr < 0.8:                 vcp += 1
        vcp = min(vcp, 4)

        ve  = volr - 1.0
        pvr = round(abs(chg1d) / ve, 2) if ve > 0.1 else round(abs(chg1d) * 2, 2)
        pvr = min(pvr, 9.99)

        if   sepa >= 5 and c_vol and vcp >= VCP_MIN: status = "breakout"
        elif sepa >= 4 and vcp >= VCP_MIN and pct_hi <= 15: status = "near-pivot"
        else: status = "watch"

        # ── Fundamentals (revenue growth, EPS, margin) ──────────────────────────
        sector = name = ""
        rev_growth_pct = eps_growth_pct = net_margin_pct = None
        trailing_eps_val = forward_eps_val = None
        fund_score = 0

        try:
            inf2 = t.info
            sector = inf2.get('sector', '') or inf2.get('industry', '') or ''
            name   = inf2.get('longName', ticker.replace('.AX', ''))

            rg = inf2.get('revenueGrowth')       # YoY decimal (e.g. 0.18 = +18 %)
            eg = inf2.get('earningsGrowth')       # EPS YoY
            pm = inf2.get('profitMargins')        # net margin decimal
            te = inf2.get('trailingEps')
            fe = inf2.get('forwardEps')

            if rg is not None: rev_growth_pct  = round(rg * 100, 1)
            if eg is not None: eps_growth_pct  = round(eg * 100, 1)
            if pm is not None: net_margin_pct  = round(pm * 100, 1)
            if te is not None: trailing_eps_val = round(te, 3)
            if fe is not None: forward_eps_val  = round(fe, 3)

            # Fund score: 1 pt revenue >5 %, bonus pt revenue >20 %, 1 pt positive EPS growth
            if rev_growth_pct is not None and rev_growth_pct > 5:  fund_score += 1
            if rev_growth_pct is not None and rev_growth_pct > 20: fund_score += 1
            if eps_growth_pct is not None and eps_growth_pct > 0:  fund_score += 1
            fund_score = min(fund_score, 3)
        except Exception:
            try:
                inf2 = t.info
                sector = inf2.get('sector', '') or ''
                name   = inf2.get('longName', ticker.replace('.AX', ''))
            except Exception:
                name = ticker.replace('.AX', '')

        # ── Upcoming events (earnings, ex-dividend) ──────────────────────────────
        next_earnings     = None
        next_event_label  = None
        next_ex_div       = None

        try:
            cal = t.calendar
            if isinstance(cal, dict):
                ed_list = cal.get('Earnings Date', [])
                if ed_list:
                    ed = _parse_earnings_date(ed_list[0])
                    if ed:
                        days = (ed - date.today()).days
                        if -10 <= days <= 120:
                            next_earnings = str(ed)
                            if days == 0:
                                next_event_label = "⚡ EARNINGS TODAY"
                            elif 0 < days <= 7:
                                next_event_label = f"⚡ Earnings in {days}d"
                            elif 0 < days <= 30:
                                next_event_label = f"📅 Earnings in {days}d"
                            elif days > 30:
                                next_event_label = f"📅 Earnings {ed.strftime('%d %b')}"
                            else:
                                next_event_label = f"Results {abs(days)}d ago"
                ex = cal.get('Ex-Dividend Date')
                if ex:
                    d2 = _parse_earnings_date(ex)
                    if d2:
                        next_ex_div = d2.strftime('%d %b %Y')
            elif hasattr(cal, 'columns') and 'Earnings Date' in cal.columns:
                ed = _parse_earnings_date(cal['Earnings Date'].iloc[0])
                if ed:
                    days = (ed - date.today()).days
                    if -10 <= days <= 120:
                        next_earnings = str(ed)
                        if days == 0:
                            next_event_label = "⚡ EARNINGS TODAY"
                        elif 0 < days <= 7:
                            next_event_label = f"⚡ Earnings in {days}d"
                        elif 0 < days <= 30:
                            next_event_label = f"📅 Earnings in {days}d"
                        elif days > 30:
                            next_event_label = f"📅 Earnings {ed.strftime('%d %b')}"
                        else:
                            next_event_label = f"Results {abs(days)}d ago"
        except Exception:
            pass

        # ── Short signal line ────────────────────────────────────────────────────
        sigs = []
        if c_vol:           sigs.append(f"Vol {volr}x avg")
        if chg250d > 50:    sigs.append(f"+{chg250d}% 12M")
        if vcp >= 3:        sigs.append("VCP tightening")
        if pct_hi < 5:      sigs.append("Near 52W high")
        # Inject catalyst label for near-term events
        if next_event_label and ('⚡' in next_event_label or ('📅' in next_event_label)):
            sigs.append(next_event_label)
        if not sigs:
            sigs.append(f"SEPA {sepa}/7")

        # ── Analysis text ────────────────────────────────────────────────────────
        tr    = "strongly uptrending" if chg250d > 40 else "uptrending" if chg250d > 15 else "recovering"
        mas   = "fully aligned (Price>MA50>MA150>MA200)" if (c_ma50 and c_ma150 and c_ma200) else "partially aligned"
        vls   = f"Volume is {volr}x the 50-day average" if volr >= 1.5 else f"Volume at {volr}x average"
        vcpd  = ["no base","early base","developing VCP","good VCP (volume drying up)","textbook VCP (volume at lows)"][vcp]

        fund_context = ""
        if rev_growth_pct is not None:
            if rev_growth_pct > 20:
                fund_context += f" Revenue growing strongly at +{rev_growth_pct}% YoY —"
                fund_context += " fundamental momentum aligns with technical breakout."
            elif rev_growth_pct > 5:
                fund_context += f" Revenue growing +{rev_growth_pct}% YoY."
            elif rev_growth_pct < 0:
                fund_context += f" Revenue declined {rev_growth_pct}% YoY — monitor fundamentals."
        if eps_growth_pct is not None and eps_growth_pct > 0:
            fund_context += f" EPS growth +{eps_growth_pct}% confirms profitability expansion."
        elif trailing_eps_val and trailing_eps_val > 0:
            fund_context += f" Profitable (trailing EPS ${trailing_eps_val})."

        catalyst_txt = f" CATALYST: {next_event_label}." if next_event_label else ""

        analysis = (
            f"{name} is {tr} over 12 months ({fmt_pct(chg250d)}), MAs {mas}. "
            f"Forming {vcpd}, {pct_hi}% below 52W high of ${round(hi52,2)}. "
            f"{vls}. SEPA {sepa}/7, PVR {pvr}."
            f"{fund_context}{catalyst_txt}"
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
            "checks": {"ma50":c_ma50,"ma150":c_ma150,"ma200":c_ma200,
                       "trend":c_trend,"high":c_high,"low":c_low,"vol":c_vol},
            "shortSignal": " · ".join(sigs[:3]), "analysis": analysis,
            # ── NEW: fundamentals ──
            "revGrowth":    rev_growth_pct,
            "epsGrowth":    eps_growth_pct,
            "netMargin":    net_margin_pct,
            "trailingEps":  trailing_eps_val,
            "forwardEps":   forward_eps_val,
            "fundScore":    fund_score,
            # ── NEW: upcoming events ──
            "nextEarnings":    next_earnings,
            "nextEventLabel":  next_event_label,
            "nextExDiv":       next_ex_div,
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
