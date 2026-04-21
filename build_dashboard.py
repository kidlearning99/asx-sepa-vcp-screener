"""
build_dashboard.py — builds the HTML dashboard from screener data
Called by screener.py
"""
from datetime import date
import json


def fmt_pct(v):
    return ("+" if v >= 0 else "") + str(round(v, 2)) + "%"


STAGE_COL = {1: "#5a7a9a", 2: "#00d084", 3: "#ff9f43", 4: "#ff4757"}
STAGE_BG  = {1: "rgba(90,122,154,.1)", 2: "rgba(0,208,132,.1)", 3: "rgba(255,159,67,.1)", 4: "rgba(255,71,87,.1)"}
STAGE_BD  = {1: "rgba(90,122,154,.3)", 2: "rgba(0,208,132,.3)", 3: "rgba(255,159,67,.3)", 4: "rgba(255,71,87,.3)"}
STAGE_LBL = {1: "S1 Neglect", 2: "S2 Advancing", 3: "S3 Topping", 4: "S4 Declining"}


def build(data, source="Yahoo Finance (live)"):
    today_str = date.today().strftime("%d %b %Y")

    def _jsafe(o):
        if hasattr(o, 'item'): return o.item()
        if hasattr(o, '__float__'): return float(o)
        raise TypeError(repr(o))

    def _clean(obj):
        if isinstance(obj, str):  return obj.encode('utf-8', errors='replace').decode('utf-8')
        if isinstance(obj, dict): return {k: _clean(v) for k, v in obj.items()}
        if isinstance(obj, list): return [_clean(v) for v in obj]
        return obj
    data = [_clean(r) for r in data]
    json_data = json.dumps(data, default=_jsafe)

    n        = len(data)
    breakouts = [r for r in data if r["status"] == "breakout"]
    pivots    = [r for r in data if r["status"] == "near-pivot"]
    watching  = [r for r in data if r["status"] == "watch"]
    stage1    = [r for r in data if r.get("stage") == 1]
    stage2    = [r for r in data if r.get("stage") == 2]
    stage3    = [r for r in data if r.get("stage") == 3]
    stage4    = [r for r in data if r.get("stage") == 4]
    sectors   = sorted(set(r["sector"] for r in data if r["sector"]))
    sector_opts = "".join(f'<option value="{s}">{s}</option>' for s in sectors)

    top = sorted(
        breakouts + [r for r in pivots if r["sepaScore"] >= 5],
        key=lambda x: (x["sepaScore"], x["vcpScore"], x["volRatio"]),
        reverse=True
    )[:10]

    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    top_html = ""
    for i, r in enumerate(top):
        sc    = r["sepaScore"]
        pips  = "".join(f'<div class="pip {"pg" if j<sc else "po"}"></div>' for j in range(7))
        vpips = "".join(f'<div class="vp {"von" if j<r["vcpScore"] else "voff"}"></div>' for j in range(4))
        col   = "#00d084" if r["status"] == "breakout" else "#3b82f6"
        p250c = "#00d084" if r["chg250d"] >= 0 else "#ff4757"
        badge_label = "BREAKOUT" if r["status"] == "breakout" else "NEAR PIVOT"
        stg   = r.get("stage", 2)
        stg_c = STAGE_COL[stg]
        stg_l = STAGE_LBL[stg]
        ev_html = ""
        nl = r.get("nextEventLabel")
        if nl:
            ev_col = "#ffd700" if "\u26a1" in nl else "#3b82f6"
            ev_bg  = "rgba(255,215,0,.1)" if "\u26a1" in nl else "rgba(59,130,246,.1)"
            ev_bd  = "rgba(255,215,0,.3)" if "\u26a1" in nl else "rgba(59,130,246,.3)"
            ev_html += (f'<div style="margin-top:5px;font-size:10px;font-weight:700;'
                        f'color:{ev_col};background:{ev_bg};border:1px solid {ev_bd};'
                        f'border-radius:4px;padding:2px 7px;display:inline-block">{nl}</div>')
        rt = r.get("revTrend")
        if rt in ("accelerating", "growing"):
            rt_col = "#00d084" if rt == "accelerating" else "#8bc34a"
            rt_lbl = "\u21911\u2191 Rev Accelerating" if rt == "accelerating" else "\u2191 Rev Growing"
            ev_html += (f'<div style="margin-top:4px;font-size:10px;font-weight:700;'
                        f'color:{rt_col};background:rgba(0,208,132,.07);border:1px solid rgba(0,208,132,.2);'
                        f'border-radius:4px;padding:2px 7px;display:inline-block">{rt_lbl}</div>')

        top_html += f'''<div class="tc" onclick="jmp('{r["ticker"]}')" >
<span class="tc-rank">{medals[i]}</span>
<div class="tc-body">
  <div class="tc-head">
    <span class="tc-ticker">{r["ticker"]}</span>
    <span class="badge-status" style="color:{col};border-color:{col}44">{badge_label}</span>
    <span class="stage-mini" style="color:{stg_c};border-color:{stg_c}44;background:{stg_c}0d">{stg_l}</span>
  </div>
  <div class="tc-name">{r["name"]}</div>
  <div style="display:flex;gap:5px;margin-bottom:6px"><div class="pips">{pips}</div><div class="vpips">{vpips}</div></div>
  <div class="tc-stats">
    <span style="color:#e8f0fe;font-weight:700">${r["price"]}</span>
    <span style="color:{p250c}">{fmt_pct(r["chg250d"])} 12M</span>
    <span style="color:{"#00d084" if r["volRatio"]>=1.5 else "#ff9f43"}">{r["volRatio"]}x vol</span>
  </div>
  <div class="tc-sig">{r["shortSignal"]}</div>
  {ev_html}
</div>
</div>'''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SEPA+VCP ASX Screener \u2014 {today_str}</title>
<meta name="description" content="Minervini SEPA + VCP ASX stock screener with stage analysis, candlestick charts, and fundamental data. Updated daily.">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
/* \u2500\u2500 Reset \u2500\u2500 */
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#080c14;--bg2:#0d1421;--bg3:#131c2e;--bg4:#1a2540;
  --border:#1e2d45;--border2:#243350;
  --text:#e8f0fe;--muted:#5a7a9a;--muted2:#3d5a78;
  --green:#00d084;--green2:#00a86b;
  --blue:#3b82f6;--cyan:#00b4d8;
  --amber:#ff9f43;--red:#ff4757;--gold:#ffd700;
  --s1:#5a7a9a;--s2:#00d084;--s3:#ff9f43;--s4:#ff4757;
}}
body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);font-size:13px;line-height:1.5}}

/* \u2500\u2500 Nav \u2500\u2500 */
nav{{
  background:rgba(8,12,20,.96);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);
  border-bottom:1px solid var(--border);padding:10px 24px;
  display:flex;align-items:center;justify-content:space-between;
  position:sticky;top:0;z-index:100;gap:12px;flex-wrap:wrap
}}
.nlogo{{font-weight:800;font-size:15px;color:#fff;display:flex;align-items:center;gap:8px;letter-spacing:-.3px}}
.ndot{{width:8px;height:8px;background:var(--green);border-radius:50%;animation:pulse 2s infinite;box-shadow:0 0 8px var(--green)}}
@keyframes pulse{{0%,100%{{opacity:1;transform:scale(1)}}50%{{opacity:.35;transform:scale(.75)}}}}
.nlinks{{display:flex;gap:18px}}.nlinks a{{color:var(--muted);font-size:12px;text-decoration:none;transition:color .15s}}.nlinks a:hover{{color:var(--text)}}
.nbadge{{background:rgba(0,208,132,.1);color:var(--green);border:1px solid rgba(0,208,132,.25);border-radius:20px;padding:3px 11px;font-size:11px;font-weight:600;white-space:nowrap}}

/* \u2500\u2500 Hero \u2500\u2500 */
.hero{{
  background:linear-gradient(160deg,#070a12 0%,#0c1628 55%,#070a12 100%);
  padding:52px 24px 36px;text-align:center;border-bottom:1px solid var(--border);
  position:relative;overflow:hidden
}}
.hero::before{{
  content:'';position:absolute;top:-30%;left:50%;transform:translateX(-50%);
  width:700px;height:400px;
  background:radial-gradient(ellipse,rgba(0,208,132,.07) 0%,transparent 65%);
  pointer-events:none
}}
.hero h1{{font-size:36px;font-weight:800;color:#fff;letter-spacing:-1.5px;line-height:1.1;margin-bottom:10px}}
.hero h1 span{{background:linear-gradient(90deg,var(--green),var(--cyan));-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.hero p{{font-size:14px;color:var(--muted);margin:0 auto;max-width:560px;line-height:1.7}}
.hero-stats{{
  display:flex;justify-content:center;gap:0;margin-top:28px;flex-wrap:wrap;
  border:1px solid var(--border);border-radius:12px;overflow:hidden;
  max-width:580px;margin-left:auto;margin-right:auto;background:var(--bg2)
}}
.hs{{text-align:center;padding:15px 22px;flex:1;border-right:1px solid var(--border)}}
.hs:last-child{{border-right:none}}
.hs-n{{font-size:28px;font-weight:800;font-family:'JetBrains Mono'}}
.hs-l{{font-size:9px;color:var(--muted);margin-top:2px;text-transform:uppercase;letter-spacing:.7px}}
.stage-row{{display:flex;justify-content:center;gap:8px;margin-top:16px;flex-wrap:wrap}}
.stage-pill{{
  display:flex;align-items:center;gap:5px;padding:5px 13px;border-radius:20px;
  font-size:11px;font-weight:700;border:1px solid;cursor:pointer;transition:all .15s;user-select:none
}}
.stage-pill:hover{{filter:brightness(1.15);transform:translateY(-1px)}}

/* \u2500\u2500 Top picks \u2500\u2500 */
.section{{padding:40px 24px;border-bottom:1px solid var(--border)}}
.stitle{{font-size:20px;font-weight:800;color:#fff;margin-bottom:4px;letter-spacing:-.3px}}
.ssub{{font-size:13px;color:var(--muted);margin-bottom:22px}}
.picks-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(225px,1fr));gap:10px}}
.tc{{
  background:var(--bg2);border:1px solid var(--border);border-radius:12px;
  padding:13px;cursor:pointer;transition:all .18s;display:flex;gap:9px;
  position:relative;overflow:hidden
}}
.tc::after{{
  content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,var(--green),var(--cyan));
  opacity:0;transition:opacity .18s
}}
.tc:hover{{border-color:rgba(0,208,132,.28);transform:translateY(-2px);box-shadow:0 6px 24px rgba(0,208,132,.07)}}
.tc:hover::after{{opacity:1}}
.tc-rank{{font-size:18px;flex-shrink:0;margin-top:1px}}
.tc-body{{flex:1;min-width:0}}
.tc-head{{display:flex;align-items:center;gap:5px;margin-bottom:2px;flex-wrap:wrap}}
.tc-ticker{{font-weight:800;font-size:14px;font-family:'JetBrains Mono';color:#fff;letter-spacing:.5px}}
.badge-status{{padding:1px 6px;border-radius:4px;font-size:9px;font-weight:700;letter-spacing:.5px;border:1px solid;background:transparent}}
.stage-mini{{padding:1px 5px;border-radius:3px;font-size:8px;font-weight:700;letter-spacing:.3px;border:1px solid}}
.tc-name{{font-size:10px;color:var(--muted);margin-bottom:5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.tc-stats{{display:flex;gap:7px;font-size:11px;font-family:'JetBrains Mono';flex-wrap:wrap}}
.tc-sig{{font-size:10px;color:var(--muted2);margin-top:3px;line-height:1.4}}

/* \u2500\u2500 Pips \u2500\u2500 */
.pips,.vpips{{display:flex;gap:2px}}
.pip{{width:8px;height:8px;border-radius:2px}}
.pg{{background:var(--green)}}.pa{{background:var(--amber)}}.pr{{background:var(--red)}}
.po{{background:var(--bg4);border:1px solid var(--border)}}
.vp{{width:9px;height:9px;border-radius:2px}}.von{{background:var(--blue)}}.voff{{background:var(--bg4);border:1px solid var(--border)}}
.fpip{{width:9px;height:9px;border-radius:2px}}.fon{{background:var(--amber)}}.foff{{background:var(--bg4);border:1px solid var(--border)}}

/* \u2500\u2500 Toolbar \u2500\u2500 */
.toolbar{{
  padding:8px 24px;display:flex;gap:6px;align-items:center;flex-wrap:wrap;
  background:rgba(8,12,20,.94);backdrop-filter:blur(10px);
  border-bottom:1px solid var(--border);position:sticky;top:49px;z-index:90
}}
.fbtn{{
  padding:4px 10px;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer;
  border:1px solid var(--border);background:var(--bg3);color:var(--muted);
  transition:all .12s;white-space:nowrap;user-select:none
}}
.fbtn.on{{border-color:var(--green);background:rgba(0,208,132,.1);color:var(--green)}}
.fbtn:hover:not(.on){{border-color:var(--muted2);color:var(--text)}}
.fbtn.s1.on{{border-color:var(--s1);background:rgba(90,122,154,.1);color:var(--s1)}}
.fbtn.s2.on{{border-color:var(--s2);background:rgba(0,208,132,.1);color:var(--s2)}}
.fbtn.s3.on{{border-color:var(--s3);background:rgba(255,159,67,.1);color:var(--s3)}}
.fbtn.s4.on{{border-color:var(--s4);background:rgba(255,71,87,.1);color:var(--s4)}}
.tsep{{width:1px;height:20px;background:var(--border);margin:0 2px;flex-shrink:0}}
input.srch,select{{
  background:var(--bg3);border:1px solid var(--border);color:var(--text);
  border-radius:6px;padding:5px 9px;font-size:11px;outline:none;font-family:'Inter'
}}
input.srch{{width:150px}}input.srch::placeholder{{color:var(--muted)}}
input.srch:focus,select:focus{{border-color:var(--green)}}
.cnt{{font-size:11px;color:var(--muted);margin-left:auto;white-space:nowrap}}

/* \u2500\u2500 Table \u2500\u2500 */
.twrap{{margin:0 24px 28px;border:1px solid var(--border);border-radius:12px;overflow:hidden;overflow-x:auto}}
table{{width:100%;border-collapse:collapse;min-width:1060px}}
thead th{{
  background:var(--bg2);padding:9px 10px;text-align:left;
  font-size:9px;font-weight:700;color:var(--muted);text-transform:uppercase;
  letter-spacing:.7px;border-bottom:1px solid var(--border);white-space:nowrap
}}
tbody tr.main-row{{border-bottom:1px solid rgba(30,45,69,.5);cursor:pointer;transition:background .08s}}
tbody tr.main-row:hover{{background:rgba(13,20,33,.85)}}
tbody tr.main-row.expanded{{background:var(--bg2);border-bottom:none}}
tbody td{{padding:8px 10px;vertical-align:middle}}
.tkr{{font-weight:800;font-size:13px;font-family:'JetBrains Mono';color:#fff;letter-spacing:.3px}}
.co{{font-size:10px;color:var(--muted);margin-top:1px;max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.badge{{display:inline-flex;padding:2px 7px;border-radius:4px;font-size:9px;font-weight:700;letter-spacing:.4px}}
.bb{{background:rgba(0,208,132,.1);color:var(--green);border:1px solid rgba(0,208,132,.3)}}
.bp{{background:rgba(59,130,246,.1);color:var(--blue);border:1px solid rgba(59,130,246,.3)}}
.bw{{background:rgba(255,159,67,.1);color:var(--amber);border:1px solid rgba(255,159,67,.3)}}
.bb-pulse{{animation:bdgpulse 2.5s infinite}}
@keyframes bdgpulse{{0%,100%{{box-shadow:0 0 0 0 rgba(0,208,132,.5)}}50%{{box-shadow:0 0 0 5px rgba(0,208,132,0)}}}}
.stage-badge{{display:inline-flex;padding:2px 7px;border-radius:4px;font-size:9px;font-weight:700;letter-spacing:.3px;white-space:nowrap}}
.pv{{font-family:'JetBrains Mono';font-size:12px;font-weight:600}}
.gn{{color:var(--green)}}.rd{{color:var(--red)}}.gy{{color:var(--muted)}}
.vhigh{{color:var(--green);font-weight:700}}.vmed{{color:var(--amber);font-weight:600}}.vlow{{color:var(--muted)}}
.pvg{{color:var(--green);font-weight:600}}.pvo{{color:var(--amber)}}.pvw{{color:var(--muted)}}
.sec{{font-size:10px;color:#4a6a8a;max-width:90px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.mc{{font-family:'JetBrains Mono';font-size:11px;color:#4a6a8a}}
.vol-wrap{{display:flex;align-items:center;gap:5px}}
.vol-track{{width:32px;height:4px;background:var(--bg4);border-radius:2px;overflow:hidden}}
.vol-fill{{height:100%;border-radius:2px}}

/* \u2500\u2500 Detail panel \u2500\u2500 */
.drow td{{padding:0;background:#050810}}
.dpanel{{
  padding:18px 18px 20px 48px;
  display:grid;
  grid-template-columns:minmax(310px,2.6fr) minmax(150px,1.2fr) minmax(170px,1.2fr) minmax(170px,1.3fr) minmax(140px,1fr);
  gap:16px;border-top:1px solid var(--border)
}}
.dh{{font-size:9px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.8px;margin-bottom:9px}}
.cl{{display:flex;flex-direction:column;gap:3px}}
.cr{{display:flex;align-items:flex-start;gap:5px;font-size:11px;line-height:1.5}}
.cr.ok{{color:var(--green)}}.cr.no{{color:#253550}}
.ci{{width:12px;flex-shrink:0;font-size:10px;margin-top:1px}}
.mat{{width:100%;border-collapse:collapse;font-size:11px;table-layout:fixed}}
.mat td{{padding:3px 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.mlb{{color:var(--muted);width:48px}}.mbar{{padding:2px 6px;width:88px}}
.mbw{{height:5px;background:var(--bg4);border-radius:3px;overflow:hidden}}
.mbi{{height:100%;border-radius:3px}}.mvl{{font-family:'JetBrains Mono';color:#4a6a8a;text-align:right;width:54px}}
.mgv{{font-family:'JetBrains Mono';font-size:11px;font-weight:700;text-align:right}}
.rev-bars{{display:flex;align-items:flex-end;gap:3px;height:48px;margin:6px 0}}
.rev-bar-wrap{{display:flex;flex-direction:column;align-items:center;gap:2px;flex:0 0 24px}}
.rev-bar{{width:16px;border-radius:2px 2px 0 0;min-height:2px}}
.rev-bar-lbl{{font-size:8px;color:var(--muted)}}
.abox{{background:var(--bg2);border-radius:8px;padding:11px;border-left:3px solid var(--border);font-size:11px;color:#4a6a8a;line-height:1.8}}
.aact{{margin-top:8px;font-weight:700;font-size:11px;padding:6px 10px;border-radius:6px}}
.abuy{{color:var(--green);background:rgba(0,208,132,.06);border:1px solid rgba(0,208,132,.2)}}
.awch{{color:var(--blue);background:rgba(59,130,246,.06);border:1px solid rgba(59,130,246,.2)}}
.ahld{{color:var(--amber);background:rgba(255,159,67,.06);border:1px solid rgba(255,159,67,.2)}}
.pg2{{display:flex;flex-direction:column;gap:0;font-size:10px;margin-top:8px}}
.pi{{display:flex;justify-content:space-between;align-items:center;padding:3px 0;border-bottom:1px solid var(--border)}}
.pi:last-child{{border:none}}.pk{{color:var(--muted);flex-shrink:0;margin-right:5px}}
.pv2{{font-family:'JetBrains Mono';font-size:10px;font-weight:600;text-align:right}}
.ev-hot{{display:inline-block;padding:4px 9px;border-radius:5px;font-size:11px;font-weight:800;background:rgba(255,215,0,.1);color:var(--gold);border:1px solid rgba(255,215,0,.3);margin-top:6px}}
.ev-soon{{display:inline-block;padding:4px 9px;border-radius:5px;font-size:11px;font-weight:700;background:rgba(59,130,246,.1);color:var(--blue);border:1px solid rgba(59,130,246,.3);margin-top:6px}}
.ev-div{{font-size:10px;color:var(--amber);margin-top:5px}}
.ev-none{{font-size:10px;color:#253550;margin-top:6px}}
.trend-chip{{display:inline-block;font-size:10px;font-weight:700;padding:2px 7px;border-radius:4px;margin-bottom:7px}}
.trend-acc{{background:rgba(0,208,132,.1);color:var(--green);border:1px solid rgba(0,208,132,.25)}}
.trend-grow{{background:rgba(139,195,74,.08);color:#8bc34a;border:1px solid rgba(139,195,74,.2)}}
.trend-flat{{background:rgba(255,159,67,.08);color:var(--amber);border:1px solid rgba(255,159,67,.2)}}
.trend-dec{{background:rgba(255,71,87,.08);color:var(--red);border:1px solid rgba(255,71,87,.2)}}
.fpips{{display:flex;gap:2px}}
.tl-box{{background:var(--bg2);border:1.5px solid rgba(0,208,132,.35);border-radius:8px;padding:10px 12px;margin-bottom:9px}}
.tl-title{{font-size:10px;font-weight:700;color:var(--text);letter-spacing:.06em;margin-bottom:8px}}
.tl-grid{{display:grid;grid-template-columns:1fr 1fr;gap:6px}}
.tl-cell{{border-radius:5px;padding:6px 8px;text-align:center}}
.tl-lbl{{font-size:8px;color:var(--muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:3px}}
.tl-val{{font-size:14px;font-weight:700;font-family:'JetBrains Mono'}}
.stage-info-box{{border-radius:7px;padding:9px 11px;font-size:11px;line-height:1.6;margin-bottom:10px;border:1px solid}}
.empty{{text-align:center;padding:50px;color:var(--muted)}}
footer{{background:#040710;border-top:1px solid var(--border);padding:18px 24px;text-align:center;font-size:11px;color:var(--muted)}}
@media(max-width:1100px){{.dpanel{{grid-template-columns:1.5fr 1fr 1fr!important}}}}
@media(max-width:800px){{.dpanel{{grid-template-columns:1fr 1fr!important}}}}
@media(max-width:550px){{.dpanel{{grid-template-columns:1fr!important}}.hero h1{{font-size:26px}}}}
</style>
</head>
<body>
<nav>
  <div class="nlogo"><div class="ndot"></div>SEPA+VCP ASX Screener</div>
  <div class="nlinks"><a href="#picks">Top Picks</a><a href="#screener">Screener</a></div>
  <span class="nbadge">&#x25cf; Live &mdash; {today_str}</span>
</nav>

<div class="hero">
  <h1>ASX Stock Screener<br><span>SEPA &middot; VCP &middot; Minervini Stages</span></h1>
  <p>Minervini's Stage 2 Trend Template with VCP analysis, net revenue trend, EPS growth, Minervini lifecycle stage classification (1&ndash;4), and 60-day candlestick charts &mdash; applied to every ASX stock over $100M market cap.</p>
  <div class="hero-stats">
    <div class="hs"><div class="hs-n" style="color:var(--green)">{len(breakouts)}</div><div class="hs-l">Breakouts</div></div>
    <div class="hs"><div class="hs-n" style="color:var(--blue)">{len(pivots)}</div><div class="hs-l">Near Pivot</div></div>
    <div class="hs"><div class="hs-n" style="color:var(--amber)">{len(watching)}</div><div class="hs-l">On Watch</div></div>
    <div class="hs"><div class="hs-n" style="color:var(--text)">{n}</div><div class="hs-l">Screened</div></div>
  </div>
  <div class="stage-row">
    <div class="stage-pill" style="color:var(--s1);border-color:rgba(90,122,154,.3);background:rgba(90,122,154,.08)" onclick="setStageHero(1,this)">
      &#x25cf; S1 Neglect <strong>&nbsp;{len(stage1)}</strong>
    </div>
    <div class="stage-pill" style="color:var(--s2);border-color:rgba(0,208,132,.3);background:rgba(0,208,132,.08)" onclick="setStageHero(2,this)">
      &#x25cf; S2 Advancing <strong>&nbsp;{len(stage2)}</strong>
    </div>
    <div class="stage-pill" style="color:var(--s3);border-color:rgba(255,159,67,.3);background:rgba(255,159,67,.08)" onclick="setStageHero(3,this)">
      &#x25cf; S3 Topping <strong>&nbsp;{len(stage3)}</strong>
    </div>
    <div class="stage-pill" style="color:var(--s4);border-color:rgba(255,71,87,.3);background:rgba(255,71,87,.08)" onclick="setStageHero(4,this)">
      &#x25cf; S4 Declining <strong>&nbsp;{len(stage4)}</strong>
    </div>
  </div>
</div>

<div class="section" id="picks">
  <div class="stitle">&#x1F3C6; Top 10 ASX Picks Today</div>
  <div class="ssub">Highest-conviction SEPA + VCP + Stage 2 setups &mdash; ranked by combined score. Click any card to jump to full analysis with 60-day candlestick chart.</div>
  <div class="picks-grid">{top_html}</div>
  <p style="font-size:11px;color:var(--muted);margin-top:16px;line-height:1.7">
    <strong style="color:#c9d1d9">How to read:</strong> Green pips = SEPA score (7 max). Blue pips = VCP score (4 max).
    <strong style="color:var(--green)">S2 Advancing</strong> = the only safe buying stage.
    Breakouts: enter at market, stop below MA50. Near Pivot: set alert at pivot high, enter on breakout with vol &gt;1.5x. Always risk 1&ndash;2% max per trade.
  </p>
</div>

<div id="screener">
<div class="toolbar">
  <button class="fbtn on" id="btn-all" onclick="setF('all',this)">All ({n})</button>
  <button class="fbtn" onclick="setF('breakout',this)">&#x1F7E2; Breakout ({len(breakouts)})</button>
  <button class="fbtn" onclick="setF('near-pivot',this)">&#x1F535; Near Pivot ({len(pivots)})</button>
  <button class="fbtn" onclick="setF('watch',this)">&#x1F7E1; Watch ({len(watching)})</button>
  <div class="tsep"></div>
  <button class="fbtn s2" id="tb-s2" onclick="setStageFilter(2,this)">S2 Advancing ({len(stage2)})</button>
  <button class="fbtn s1" id="tb-s1" onclick="setStageFilter(1,this)">S1 Neglect ({len(stage1)})</button>
  <button class="fbtn s3" id="tb-s3" onclick="setStageFilter(3,this)">S3 Topping ({len(stage3)})</button>
  <button class="fbtn s4" id="tb-s4" onclick="setStageFilter(4,this)">S4 Declining ({len(stage4)})</button>
  <div class="tsep"></div>
  <input class="srch" id="srch" placeholder="&#x1F50D; Ticker or name..." oninput="render()">
  <select id="srt" onchange="render()">
    <option value="sepa">&#x2193; SEPA Score</option>
    <option value="vcp">&#x2193; VCP Score</option>
    <option value="vol">&#x2193; Volume Ratio</option>
    <option value="pvr">&#x2193; PVR</option>
    <option value="fund">&#x2193; Fund Score</option>
    <option value="p250">&#x2193; 12M Perf</option>
    <option value="mc">&#x2193; Mkt Cap</option>
    <option value="stage">&#x2191; Stage (1 first)</option>
  </select>
  <select id="sec" onchange="render()"><option value="">All Sectors</option>{sector_opts}</select>
  <span class="cnt" id="cnt"></span>
</div>
<div class="twrap"><table>
  <thead><tr>
    <th>#</th><th>Ticker</th><th>Stage</th><th>Signal</th>
    <th>SEPA /7</th><th>VCP /4</th>
    <th>Price</th><th>Today</th><th>Rel.Vol</th><th>PVR</th>
    <th>Fund /3</th><th>Net Revenue</th><th>Catalyst</th>
    <th>12M</th><th>Mkt Cap</th><th>Sector</th>
  </tr></thead>
  <tbody id="tbody"></tbody>
</table></div>
</div>

<footer>
  <strong>SEPA + VCP ASX Screener</strong> &middot; Data: Yahoo Finance &middot; Generated {today_str}<br>
  <span style="font-size:10px;opacity:.55">&#x26A0;&#xFE0F; For educational and research purposes only. Not financial advice. Always conduct your own due diligence and consult a licensed financial adviser before making investment decisions. All prices in AUD.</span>
</footer>

<script>
const D={json_data};
let filt='all', stageFilt=0;
const CUR=String.fromCharCode(36);
const SCOL={{1:'#5a7a9a',2:'#00d084',3:'#ff9f43',4:'#ff4757'}};
const SLBL={{1:'S1 Neglect',2:'S2 Advancing',3:'S3 Topping',4:'S4 Declining'}};
const SDESC={{
  1:'Consolidation phase. Price sideways around a flat MA200. Institutions ignoring. Avoid buying \u2014 wait for Stage 2 breakout.',
  2:'Advancing phase. Price firmly above a rising MA200, MA150>MA200, volume accumulating on up-days. This is the ONLY safe buying stage.',
  3:'Topping / distribution phase. Momentum slowing, smart money distributing to late buyers, volatility increasing. Reduce or exit positions.',
  4:'Declining phase. Full downtrend with lower highs and lower lows, price below a falling MA200. Absolutely avoid buying. Wait for Stage 1 base.'
}};

function setF(f,el){{
  filt=f;
  document.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('on'));
  el.classList.add('on');
  render();
}}

function setStageHero(s,el){{
  stageFilt = stageFilt===s ? 0 : s;
  ['tb-s1','tb-s2','tb-s3','tb-s4'].forEach(id=>{{
    const b=document.getElementById(id); if(b)b.classList.remove('on');
  }});
  if(stageFilt){{
    const b=document.getElementById('tb-s'+s); if(b)b.classList.add('on');
  }}
  document.getElementById('screener').scrollIntoView({{behavior:'smooth'}});
  render();
}}

function setStageFilter(s,el){{
  stageFilt = stageFilt===s ? 0 : s;
  document.querySelectorAll('.fbtn.s1,.fbtn.s2,.fbtn.s3,.fbtn.s4').forEach(b=>b.classList.remove('on'));
  if(stageFilt===s) el.classList.add('on');
  render();
}}

function jmp(t){{
  document.getElementById('screener').scrollIntoView({{behavior:'smooth'}});
  document.getElementById('srch').value=t;
  setTimeout(()=>{{render();const r=document.querySelector('#tbody tr.main-row');if(r)r.click();}},400);
}}

function fmtGrowth(v,hi,med){{
  hi=hi===undefined?20:hi; med=med===undefined?5:med;
  if(v===null||v===undefined)return '<span style="color:#253550">N/A</span>';
  var col=v>=hi?'#00d084':v>=med?'#ff9f43':v>=0?'#5a7a9a':'#ff4757';
  var arrow=v>0?'\u2191 ':v<0?'\u2193 ':'';
  return '<span style="color:'+col+';font-weight:700">'+arrow+(v>=0?'+':'')+v+'%</span>';
}}

function revTrendChip(trend){{
  if(!trend)return'';
  var map={{'accelerating':['trend-chip trend-acc','\u21911\u2191 Accelerating'],'growing':['trend-chip trend-grow','\u2191 Growing'],'flat':['trend-chip trend-flat','\u2192 Flat'],'declining':['trend-chip trend-dec','\u2193 Declining']}};
  var e=map[trend]||['',''];
  return e[0]?'<div class="'+e[0]+'">'+e[1]+'</div>':'';
}}

function revBars(quarters){{
  if(!quarters||!Array.isArray(quarters)||!quarters.length)return'<div style="color:#253550;font-size:10px">No quarterly data</div>';
  var vals=quarters.slice(0,5);
  var maxV=1;
  for(var k=0;k<vals.length;k++){{if(Math.abs(vals[k][1])>maxV)maxV=Math.abs(vals[k][1]);}}
  var out='';
  for(var k=0;k<vals.length;k++){{
    var lbl=vals[k][0],val=vals[k][1];
    var col=val>=0?'#00d084':'#ff4757';
    var h=Math.max(Math.round(Math.abs(val)/maxV*40),2);
    var av=Math.abs(val);
    var sign=val<0?'-':'';
    var avM = av / 1000000;
    var fmt=avM>=1000?sign+CUR+(avM/1000).toFixed(1)+'B':sign+CUR+avM.toFixed(0)+'M';
    out+='<div class="rev-bar-wrap">';
    out+='<div class="rev-bar" style="height:'+h+'px;background:'+col+'"></div>';
    out+='<div class="rev-bar-lbl">'+lbl+'</div>';
    out+='<div style="font-size:7px;color:#3d5a78">'+fmt+'</div>';
    out+='</div>';
  }}
  return '<div class="rev-bars">'+out+'</div>';
}}

function drawCandles(ohlcv,ma50v,price){{
  if(!ohlcv||!ohlcv.length)return'<div style="color:#253550;font-size:11px;text-align:center;padding:24px 0">No price history available</div>';
  var W=520,H=188,VH=46,PAD={{t:6,r:42,b:18,l:46}};
  var cW=W-PAD.l-PAD.r,cH=H-PAD.t-PAD.b;
  var n=ohlcv.length;
  var pMin=Infinity,pMax=-Infinity,vMax=1,avgVol=0;
  for(var i=0;i<n;i++){{
    if(ohlcv[i][2]<pMin)pMin=ohlcv[i][2];
    if(ohlcv[i][1]>pMax)pMax=ohlcv[i][1];
    if(ohlcv[i][4]>vMax)vMax=ohlcv[i][4];
    avgVol+=ohlcv[i][4];
  }}
  pMin*=0.998; pMax*=1.002;
  avgVol/=n;
  var pRange=pMax-pMin;
  var bW=Math.max(1.5,(cW/n)*0.72);
  function px(i){{return PAD.l+(i+0.5)*(cW/n);}}
  function py(p){{return PAD.t+cH-(p-pMin)/pRange*cH;}}
  var s='<svg viewBox="0 0 '+W+' '+(H+VH+6)+'" xmlns="http://www.w3.org/2000/svg" style="display:block;width:100%">';
  s+='<defs><linearGradient id="gU" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#00d084" stop-opacity="0.9"/><stop offset="100%" stop-color="#00d084" stop-opacity="0.3"/></linearGradient>';
  s+='<linearGradient id="gD" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#ff4757" stop-opacity="0.9"/><stop offset="100%" stop-color="#ff4757" stop-opacity="0.3"/></linearGradient></defs>';
  s+='<rect x="'+PAD.l+'" y="'+PAD.t+'" width="'+cW+'" height="'+cH+'" fill="#050810" rx="3"/>';
  for(var g=1;g<=3;g++){{
    var gy=PAD.t+cH*g/4;
    var gp=pMax-pRange*g/4;
    s+='<line x1="'+PAD.l+'" y1="'+gy+'" x2="'+(PAD.l+cW)+'" y2="'+gy+'" stroke="#1a2540" stroke-width="0.5"/>';
    s+='<text x="'+(PAD.l-3)+'" y="'+(gy+3)+'" text-anchor="end" fill="#3d5a78" font-size="8" font-family="monospace">'+gp.toFixed(2)+'</text>';
  }}
  s+='<text x="'+(PAD.l-3)+'" y="'+(PAD.t+5)+'" text-anchor="end" fill="#3d5a78" font-size="8" font-family="monospace">'+pMax.toFixed(2)+'</text>';
  s+='<text x="'+(PAD.l-3)+'" y="'+(PAD.t+cH)+'" text-anchor="end" fill="#3d5a78" font-size="8" font-family="monospace">'+pMin.toFixed(2)+'</text>';
  if(ma50v>=pMin&&ma50v<=pMax){{
    var my=py(ma50v);
    s+='<line x1="'+PAD.l+'" y1="'+my+'" x2="'+(PAD.l+cW)+'" y2="'+my+'" stroke="#ff9f43" stroke-width="1" stroke-dasharray="3,2" opacity="0.75"/>';
    s+='<text x="'+(PAD.l+cW+2)+'" y="'+(my+3)+'" fill="#ff9f43" font-size="7">MA50</text>';
  }}
  for(var i=0;i<n;i++){{
    var op=ohlcv[i][0],hi=ohlcv[i][1],lo=ohlcv[i][2],cl=ohlcv[i][3];
    var up=cl>=op;
    var col=up?'#00d084':'#ff4757';
    var x=px(i);
    var bTop=py(Math.max(op,cl));
    var bBot=py(Math.min(op,cl));
    var bH=Math.max(1,bBot-bTop);
    s+='<line x1="'+x+'" y1="'+py(hi)+'" x2="'+x+'" y2="'+py(lo)+'" stroke="'+col+'" stroke-width="0.8" opacity="0.45"/>';
    s+='<rect x="'+(x-bW/2)+'" y="'+bTop+'" width="'+bW+'" height="'+bH+'" fill="'+col+'" opacity="'+(up?'0.82':'0.92')+'"/>';
  }}
  var cpy=py(price);
  if(cpy>=PAD.t&&cpy<=PAD.t+cH){{
    s+='<line x1="'+PAD.l+'" y1="'+cpy+'" x2="'+(PAD.l+cW)+'" y2="'+cpy+'" stroke="#e8f0fe" stroke-width="0.6" stroke-dasharray="4,3" opacity="0.3"/>';
    s+='<text x="'+(PAD.l+cW+2)+'" y="'+(cpy+3)+'" fill="#5a7a9a" font-size="7">'+price+'</text>';
  }}
  var li=[0,Math.floor(n/2),n-1];
  for(var k=0;k<li.length;k++){{
    var daysAgo=n-1-li[k];
    s+='<text x="'+px(li[k])+'" y="'+(PAD.t+cH+14)+'" text-anchor="middle" fill="#2a3d55" font-size="7">'+(daysAgo===0?'today':daysAgo+'d ago')+'</text>';
  }}
  var vTop=H+2;
  s+='<rect x="'+PAD.l+'" y="'+vTop+'" width="'+cW+'" height="'+VH+'" fill="#040710" rx="3"/>';
  s+='<text x="'+(PAD.l-3)+'" y="'+(vTop+9)+'" text-anchor="end" fill="#2a3d55" font-size="7">Vol</text>';
  for(var i=0;i<n;i++){{
    var op=ohlcv[i][0],cl=ohlcv[i][3],vol=ohlcv[i][4];
    var up=cl>=op;
    var x=px(i);
    var vH2=Math.max(1,(vol/vMax)*(VH-4));
    var isHigh=vol>avgVol*1.4;
    s+='<rect x="'+(x-bW/2)+'" y="'+(vTop+VH-2-vH2)+'" width="'+bW+'" height="'+vH2+'" fill="'+(up?'url(#gU)':'url(#gD)')+'" opacity="'+(isHigh?'1':'0.5')+'"/>';
  }}
  var avgH=(avgVol/vMax)*(VH-4);
  s+='<line x1="'+PAD.l+'" y1="'+(vTop+VH-2-avgH)+'" x2="'+(PAD.l+cW)+'" y2="'+(vTop+VH-2-avgH)+'" stroke="#ff9f43" stroke-width="0.5" stroke-dasharray="2,2" opacity="0.4"/>';
  s+='<text x="'+(PAD.l+cW/2)+'" y="'+(vTop+VH)+'" text-anchor="middle" fill="#1e2d45" font-size="7">VOLUME \u2014 bright bars = above-average (buying pressure)</text>';
  s+='</svg>';
  return s;
}}

function render(){{
  var srt=document.getElementById('srt').value,
      q=document.getElementById('srch').value.toLowerCase(),
      sec=document.getElementById('sec').value;
  var d=D.filter(function(r){{
    if(filt!=='all'&&r.status!==filt)return false;
    if(stageFilt&&r.stage!==stageFilt)return false;
    if(sec&&r.sector!==sec)return false;
    if(q&&!r.ticker.toLowerCase().includes(q)&&!r.name.toLowerCase().includes(q))return false;
    return true;
  }});
  d.sort(function(a,b){{
    if(srt==='sepa') return(b.sepaScore*10+b.vcpScore)-(a.sepaScore*10+a.vcpScore);
    if(srt==='vcp')  return b.vcpScore-a.vcpScore;
    if(srt==='vol')  return b.volRatio-a.volRatio;
    if(srt==='pvr')  return b.pvr-a.pvr;
    if(srt==='fund') return(b.fundScore||0)-(a.fundScore||0);
    if(srt==='p250') return b.chg250d-a.chg250d;
    if(srt==='mc')   return b.mktcap-a.mktcap;
    if(srt==='stage')return(a.stage||1)-(b.stage||1);
    return 0;
  }});
  document.getElementById('cnt').textContent=d.length+' shown';
  if(!d.length){{document.getElementById('tbody').innerHTML='<tr><td colspan="16"><div class="empty">No stocks match these filters</div></td></tr>';return;}}
  document.getElementById('tbody').innerHTML=d.map(function(r,i){{return row(r,i);}}).join('');
}}

function row(r,i){{
  var sc=r.sepaScore,pc=sc>=6?'pg':sc>=4?'pa':'pr';
  var ps='';for(var j=0;j<7;j++)ps+='<div class="pip '+(j<sc?pc:'po')+'"></div>';
  var vs='';for(var j=0;j<4;j++)vs+='<div class="vp '+(j<r.vcpScore?'von':'voff')+'"></div>';
  var fs=r.fundScore||0;
  var fps='';for(var j=0;j<3;j++)fps+='<div class="fpip '+(j<fs?'fon':'foff')+'"></div>';
  var bdg=r.status==='breakout'?'<span class="badge bb bb-pulse">BREAKOUT</span>':r.status==='near-pivot'?'<span class="badge bp">NEAR PIVOT</span>':'<span class="badge bw">WATCH</span>';
  var cc=r.change>0?'gn':r.change<0?'rd':'gy';
  var vc=r.volRatio>=2?'vhigh':r.volRatio>=1.5?'vmed':'vlow';
  var p2=r.pvr>=1.5?'pvg':r.pvr>=1?'pvo':'pvw';
  var q2=r.chg250d>=0?'gn':'rd';
  var stg=r.stage||1;
  var sc2=SCOL[stg];
  var stageBdg='<span class="stage-badge" style="color:'+sc2+';background:'+sc2+'18;border:1px solid '+sc2+'40">'+SLBL[stg]+'</span>';
  var vPct=Math.min(100,r.volRatio/3*100);
  var vBc=r.volRatio>=2?'var(--green)':r.volRatio>=1.5?'var(--amber)':'#3d5a78';
  var volCell='<div class="vol-wrap"><span class="'+vc+'">'+r.volRatio+'x</span><div class="vol-track"><div class="vol-fill" style="width:'+vPct+'%;background:'+vBc+'"></div></div></div>';
  var revCell='<span style="color:#253550;font-size:10px">N/A</span>';
  if(r.revGrowth!==null&&r.revGrowth!==undefined){{
    var tIco={{'accelerating':'\u21911\u2191','growing':'\u2191','flat':'\u2192','declining':'\u2193'}};
    var tCol={{'accelerating':'#00d084','growing':'#8bc34a','flat':'#ff9f43','declining':'#ff4757'}};
    var icon=tIco[r.revTrend]||'';
    var col2=tCol[r.revTrend]||(r.revGrowth>=0?'#5a7a9a':'#ff4757');
    revCell='<span style="color:'+col2+';font-weight:700;font-size:11px">'+icon+' '+(r.revGrowth>=0?'+':'')+r.revGrowth+'%</span>';
  }}
  var evCell='<span style="color:#253550;font-size:10px">&mdash;</span>';
  if(r.nextEventLabel){{
    var hot=r.nextEventLabel.includes('\u26a1');
    evCell='<span style="color:'+(hot?'var(--gold)':'var(--blue)')+';font-size:10px;font-weight:700">'+r.nextEventLabel+'</span>';
  }}
  return '<tr class="main-row" onclick="tog('+i+')" id="mr'+i+'">'+
    '<td style="color:#253550;font-size:10px">'+(i+1)+'</td>'+
    '<td><div class="tkr">'+r.ticker+'</div><div class="co" title="'+r.name+'">'+r.name+'</div></td>'+
    '<td>'+stageBdg+'</td>'+
    '<td>'+bdg+'</td>'+
    '<td><div style="display:flex;align-items:center;gap:3px"><div class="pips">'+ps+'</div><span style="font-size:10px;color:var(--muted)">'+sc+'</span></div></td>'+
    '<td><div class="vpips">'+vs+'</div></td>'+
    '<td><span class="pv">'+CUR+r.price+'</span></td>'+
    '<td><span class="'+cc+'">'+(r.change>0?'+':'')+r.change+'%</span></td>'+
    '<td>'+volCell+'</td>'+
    '<td><span class="'+p2+'">'+r.pvr+'</span></td>'+
    '<td><div class="fpips" style="display:flex;gap:2px">'+fps+'</div><span style="font-size:9px;color:var(--muted);margin-left:3px">'+fs+'/3</span></td>'+
    '<td style="white-space:nowrap">'+revCell+'</td>'+
    '<td style="white-space:nowrap">'+evCell+'</td>'+
    '<td><span class="'+q2+'">'+(r.chg250d>=0?'+':'')+r.chg250d+'%</span></td>'+
    '<td class="mc">'+r.mktcapFmt+'</td>'+
    '<td class="sec" title="'+r.sector+'">'+r.sector+'</td>'+
    '</tr>'+
    '<tr class="drow" id="d'+i+'" style="display:none"><td colspan="16">'+det(r)+'</td></tr>';
}}

function det(r){{
  var c=r.checks;
  var stg=r.stage||1;
  var sc2=SCOL[stg];
  var crows=[[c.ma50,CUR+r.price+' > MA50 ('+CUR+r.ma50+')'],[c.ma150,'MA50 > MA150 ('+CUR+r.ma150+')'],[c.ma200,'MA150 > MA200 ('+CUR+r.ma200+')'],[c.trend,'200-day MA trending up (12M: '+(r.chg250d>=0?'+':'')+r.chg250d+'%)'],[c.high,'Within 25% of 52W high ('+r.pctFromHigh+'% below)'],[c.low,'25%+ above 52W low ('+r.pctAboveLow+'% above)'],[c.vol,'Volume breakout >=1.5x ('+r.volRatio+'x), PVR '+r.pvr]].map(function(p){{return '<div class="cr '+(p[0]?'ok':'no')+'"><span class="ci">'+(p[0]?'\u2713':'\u2717')+'</span>'+p[1]+'</div>';}}).join('');
  var mx=Math.max(r.price,r.ma50,r.ma150,r.ma200);
  function mb(lb,v,col){{return '<tr><td class="mlb">'+lb+'</td><td class="mbar"><div class="mbw"><div class="mbi" style="width:'+Math.round(v/mx*100)+'%;background:'+col+'"></div></div></td><td class="mvl">'+CUR+v+'</td></tr>';}}
  var vd=['No contraction','Weak (1/4)','Moderate (2/4)','Good (3/4) \u2014 VCP forming','Ideal (4/4) \u2014 textbook base'][r.vcpScore];
  var ac=r.status==='breakout'?'abuy':r.status==='near-pivot'?'awch':'ahld';
  var at=r.status==='breakout'?'\u2192 BUY ZONE: Consider entry. Stop-loss below MA50. Risk 1-2%.':r.status==='near-pivot'?'\u2192 WATCHLIST: Alert at pivot high. Enter on breakout with vol >1.5x.':'\u2192 MONITOR: Wait for VCP to tighten and volume to dry up.';
  var rg=r.revGrowth,eg=r.epsGrowth,nm=r.netMargin,te=r.trailingEps,fe=r.forwardEps,fs=r.fundScore||0;
  var fp2='';for(var j=0;j<3;j++)fp2+='<div class="fpip" style="display:inline-block;width:9px;height:9px;border-radius:2px;background:'+(j<fs?'#ff9f43':'#1a2540')+';border:1px solid '+(j<fs?'#ff9f43':'#1e2d45')+'"></div>&nbsp;';
  var epsRows='';
  if(te!==null&&te!==undefined){{var ec=te>0?'#00d084':'#ff4757';epsRows+='<div class="pi"><span class="pk">Trail EPS</span><span class="pv2" style="color:'+ec+'">'+te+'</span></div>';}}
  if(fe!==null&&fe!==undefined){{var ec=fe>0?'#00d084':'#ff4757';epsRows+='<div class="pi"><span class="pk">Fwd EPS</span><span class="pv2" style="color:'+ec+'">'+fe+'</span></div>';}}
  var nmRow='';
  if(nm!==null&&nm!==undefined){{var mc=nm>=15?'#00d084':nm>0?'#ff9f43':'#ff4757';nmRow='<div class="pi"><span class="pk">Net Margin</span><span class="pv2" style="color:'+mc+'">'+nm+'%</span></div>';}}
  var fundCol='<div>'+
    '<div class="dh">Net Revenue &nbsp;'+fp2+'</div>'+
    revTrendChip(r.revTrend)+
    revBars(r.revQuarters)+
    '<table class="mat">'+
    '<tr><td class="mlb">Rev YoY</td><td class="mbar"></td><td class="mgv">'+fmtGrowth(rg)+'</td></tr>'+
    '<tr><td class="mlb">EPS Grw</td><td class="mbar"></td><td class="mgv">'+fmtGrowth(eg,10,0)+'</td></tr>'+
    '</table>'+
    '<div class="pg2" style="margin-top:8px">'+nmRow+epsRows+'</div>'+
    '</div>';
  var evHtml='<div class="ev-none">No upcoming events</div>';
  var evLines=[];
  if(r.nextEventLabel){{
    var hot=r.nextEventLabel.includes('\u26a1');
    evLines.push('<div class="'+(hot?'ev-hot':'ev-soon')+'">'+r.nextEventLabel+'</div>');
    if(r.nextEarnings)evLines.push('<div style="font-size:10px;color:#253550;margin-top:3px">📆 '+r.nextEarnings+'</div>');
  }}
  if(r.nextExDiv)evLines.push('<div class="ev-div">💰 Ex-Div: '+r.nextExDiv+'</div>');
  if(evLines.length)evHtml=evLines.join('');
  var entry=r.price,stop=r.ma50,risk=entry-stop;
  var target=risk>0?(entry+2*risk).toFixed(2):null;
  var tlBox='<div class="tl-box" style="padding:10px 8px;margin-bottom:8px">'+
    '<div class="tl-title" style="font-size:9px;margin-bottom:6px">\u26A1 TRADE LEVELS</div>'+
    '<div style="display:flex;flex-direction:column;gap:5px">'+
    '<div style="background:#081a0f;border:1px solid rgba(0,208,132,.25);border-radius:4px;padding:4px;text-align:center"><div style="font-size:7px;color:#5a7a9a;margin-bottom:2px">BUY ABOVE</div><div style="font-size:11px;font-weight:700;color:#00d084">'+CUR+entry+'</div></div>'+
    '<div style="background:#1a0809;border:1px solid rgba(255,71,87,.25);border-radius:4px;padding:4px;text-align:center"><div style="font-size:7px;color:#5a7a9a;margin-bottom:2px">STOP LOSS</div><div style="font-size:11px;font-weight:700;color:#ff4757">'+CUR+stop+'</div></div>'+
    (target?'<div style="background:#08101a;border:1px solid rgba(59,130,246,.25);border-radius:4px;padding:4px;text-align:center;margin-top:2px"><div style="font-size:7px;color:#5a7a9a;margin-bottom:2px">TARGET (2R)</div><div style="font-size:11px;font-weight:700;color:#3b82f6">'+CUR+target+'</div></div>':'')+
    '</div></div>';

  var vcpPointers = ['Base is loose or trending down. Wait for a constructive base to form.', 'Early signs of contraction. Still too loose to buy.', 'Base is forming. Watch for tightening spreads on the right side.', 'Good VCP forming. Volume is drying up. Stalk entry near pivot high.', 'Textbook VCP. Extreme volatility contraction. Prime entry setup on volume breakout.'][r.vcpScore];

  var vcpAnalysisHtml = '<div style="margin-top:12px">'+
    '<div class="dh">VCP Analysis ('+r.vcpScore+'/4)</div>'+
    '<div class="abox" style="padding:9px;font-size:10px;border-left-color:var(--blue);line-height:1.5">'+
    '<strong style="color:var(--text)">'+vd+'</strong><br/>'+
    '<span style="color:#5a7a9a;display:inline-block;margin-top:4px">'+vcpPointers+'</span>'+
    '</div></div>';

  var vcpCol='<div>'+
    '<div class="dh">Catalysts &amp; Events</div>'+
    evHtml+
    vcpAnalysisHtml+
    '</div>';

  var tradeCol='<div>'+
    tlBox+
    '<div class="abox" style="margin-top:6px;padding:10px;line-height:1.6">'+
    '<div style="font-weight:800;font-size:9px;color:var(--text);margin-bottom:6px;letter-spacing:0.5px">SUMMARY</div>'+r.analysis+
    '<div class="aact '+ac+'" style="margin-top:8px">'+at+'</div></div>'+
    '</div>';

  var stageBox='<div class="stage-info-box" style="color:'+sc2+';background:'+sc2+'0d;border-color:'+sc2+'33">'+
    '<strong>'+SLBL[stg]+'</strong> \u2014 '+SDESC[stg]+
    '</div>';

  var adr = r.accDistRatio || 1.0;
  var adrCol = adr >= 1.5 ? '#00d084' : adr >= 1.0 ? '#8bc34a' : '#ff4757';
  var adrTxt = adr >= 1.5 ? 'Strong Accumulation (Inst. Buying)' : adr >= 1.0 ? 'Mild Accumulation' : 'Distribution (Selling Pressure)';
  
  var smartMoneyHtml = '<div style="margin-top:12px">'+
    '<div class="dh">Smart Money Indicators</div>'+
    '<div class="abox" style="padding:9px;font-size:10px;border-left-color:'+adrCol+';line-height:1.5">'+
    '<strong style="color:var(--text)">60-Day Acc/Dist Ratio: <span style="color:'+adrCol+'">'+adr+'x</span></strong><br/>'+
    '<span style="color:#5a7a9a;display:inline-block;margin-top:2px">'+adrTxt+'</span><br/>'+
    '<div style="display:flex;justify-content:space-between;margin-top:6px;padding-top:6px;border-top:1px solid rgba(30,45,69,.5)"><span style="color:#5a7a9a">Price/Vol Ratio (PVR):</span><strong style="color:'+(r.pvr>1.2?'#00d084':r.pvr>0.8?'#ff9f43':'#ff4757')+'">'+r.pvr+'</strong></div>'+
    '<div style="display:flex;justify-content:space-between;margin-top:4px"><span style="color:#5a7a9a">Today Vol vs 50d Avg:</span><strong style="color:'+(r.volRatio>=1.5?'#00d084':r.volRatio>=1?'#ff9f43':'#ff4757')+'">'+r.volRatio+'x</strong></div>'+
    '</div></div>';

  var sepaCol='<div>'+
    '<div class="dh">SEPA Checklist \u2014 '+r.sepaScore+'/7</div>'+
    stageBox+
    '<div class="cl">'+crows+'</div>'+
    smartMoneyHtml+
    '<div class="pg2" style="margin-top:12px">'+
    '<div class="pi"><span class="pk">5D</span><span class="'+(r.chg5d>=0?'gn':'rd')+'">'+(r.chg5d>=0?'+':'')+r.chg5d+'%</span></div>'+
    '<div class="pi"><span class="pk">60D</span><span class="'+(r.chg60d>=0?'gn':'rd')+'">'+(r.chg60d>=0?'+':'')+r.chg60d+'%</span></div>'+
    '<div class="pi"><span class="pk">12M</span><span class="'+(r.chg250d>=0?'gn':'rd')+'">'+(r.chg250d>=0?'+':'')+r.chg250d+'%</span></div>'+
    '<div class="pi"><span class="pk">Cap</span><span style="color:#4a6a8a">'+r.mktcapFmt+'</span></div>'+
    '</div></div>';
  var chartCol='<div style="display:flex;flex-direction:column;height:100%">'+
    '<div class="dh">60-Day Candlestick + Volume (orange dash = MA50, bright bars = high volume)</div>'+
    drawCandles(r.ohlcv,r.ma50,r.price)+
    '</div>';
  return '<div class="dpanel">'+chartCol+sepaCol+fundCol+vcpCol+tradeCol+'</div>';
}}

function tog(i){{
  var el=document.getElementById('d'+i);
  var mr=document.getElementById('mr'+i);
  var showing=el.style.display!=='none';
  el.style.display=showing?'none':'table-row';
  if(mr)mr.classList.toggle('expanded',!showing);
}}
render();
</script>
</body>
</html>"""
