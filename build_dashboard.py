import json, os, hashlib, requests
from datetime import date

NETLIFY_TOKEN   = os.environ.get("NETLIFY_TOKEN", "")
NETLIFY_SITE_ID = os.environ.get("NETLIFY_SITE_ID", "")

def fmt_cap(c):
    if not c: return "—"
    if c >= 1e12: return f"${c/1e12:.1f}T"
    if c >= 1e9:  return f"${c/1e9:.1f}B"
    if c >= 1e6:  return f"${c/1e6:.0f}M"
    return f"${c:.0f}"

def pct_color(v):
    if v is None: return "#888"
    return "#22c55e" if v >= 0 else "#ef4444"

def val_or(v, fallback="—"):
    if v is None: return fallback
    return v

def build(data):
    today = str(date.today())
    breakouts  = [r for r in data if r.get('status') == 'Breakout']
    near_pivot = [r for r in data if r.get('status') == 'NearPivot']
    watch      = [r for r in data if r.get('status') == 'Watch']

    # sort by sepa desc then vcp desc
    def sort_key(r): return (r.get('sepa',0), r.get('vcp',0), r.get('volr',0))
    breakouts  = sorted(breakouts,  key=sort_key, reverse=True)
    near_pivot = sorted(near_pivot, key=sort_key, reverse=True)
    watch      = sorted(watch,      key=sort_key, reverse=True)

    all_sectors = sorted(set(r.get('sector') or 'Unknown' for r in data))

    def check(v):
        return '<span class="ck ok">✓</span>' if v else '<span class="ck no">✗</span>'

    def pct_badge(v, label=""):
        if v is None: return f'<span class="badge grey">{label}—</span>'
        cls = "green" if v >= 0 else "red"
        return f'<span class="badge {cls}">{label}{v:+.1f}%</span>'

    def vol_bar(buy, sell):
        b = buy or 50
        s = sell or 50
        return f'''<div class="vol-bar-wrap" title="Buy {b}% / Sell {s}%">
          <div class="vol-bar-buy" style="width:{b}%"></div>
          <div class="vol-bar-sell" style="width:{s}%"></div>
        </div>
        <div class="vol-bar-labels"><span class="buy-lbl">Buy {b}%</span><span class="sell-lbl">Sell {s}%</span></div>'''

    def rsi_gauge(rsi):
        if rsi is None: return '<span class="dim">—</span>'
        cls = "overbought" if rsi > 70 else ("oversold" if rsi < 30 else "neutral")
        pct = min(max(rsi, 0), 100)
        return f'<div class="rsi-wrap"><div class="rsi-bar {cls}" style="width:{pct}%"></div><span class="rsi-val">{rsi}</span></div>'

    def bb_indicator(pos):
        if pos is None: return '<span class="dim">—</span>'
        cls = "bb-high" if pos > 80 else ("bb-low" if pos < 20 else "bb-mid")
        return f'<div class="bb-wrap"><div class="bb-fill {cls}" style="width:{min(pos,100):.0f}%"></div><span class="bb-val">{pos:.0f}%</span></div>'

    def metric_cell(label, value, suffix="", color=None, bold=False):
        style = f' style="color:{color}"' if color else ""
        bstart = "<b>" if bold else ""
        bend   = "</b>" if bold else ""
        val_str = f"{bstart}{value}{suffix}{bend}" if value not in (None, "—") else "—"
        return f'<div class="metric"><span class="metric-lbl">{label}</span><span class="metric-val"{style}>{val_str}</span></div>'

    def render_card(r):
        ticker  = r.get('ticker','')
        name    = r.get('name', ticker.replace('.AX',''))
        price   = r.get('price', 0)
        status  = r.get('status','')
        sepa    = r.get('sepa', 0)
        vcp     = r.get('vcp', 0)
        sector  = r.get('sector') or '—'
        mktcap  = r.get('mktcapFmt','—')
        chg1d   = r.get('chg1d')
        chg5d   = r.get('chg5d')
        chg20d  = r.get('chg20d')
        chg60d  = r.get('chg60d')
        chg250d = r.get('chg250d')
        volr    = r.get('volr', 1)
        vol_today = r.get('volume', 0)
        vol_avg20 = r.get('volAvg20', 0)
        dollar_vol = r.get('dollarVol')
        vol_trend  = r.get('volTrend')
        buy_pct    = r.get('buyPct', 50)
        sell_pct   = r.get('sellPct', 50)
        rsi        = r.get('rsi')
        atr_pct    = r.get('atrPct')
        bb_pos     = r.get('bbPos')
        bb_bw      = r.get('bbBw')
        pct_from_hi= r.get('pctFromHi')
        pct_from_lo= r.get('pctFromLo')
        hi52       = r.get('hi52')
        lo52       = r.get('lo52')
        ma50       = r.get('ma50')
        ma150      = r.get('ma150')
        ma200      = r.get('ma200')
        near_pivot = r.get('nearPivot', False)
        recent_hi  = r.get('recentHi')
        checks     = r.get('checks', {})
        analysis   = r.get('analysis','')
        short_sig  = r.get('shortSignal','')
        # Fundamentals
        pe         = r.get('peRatio')
        pb         = r.get('pbRatio')
        ps         = r.get('psRatio')
        peg        = r.get('pegRatio')
        roe        = r.get('roe')
        roa        = r.get('roa')
        de         = r.get('debtEquity')
        cur_r      = r.get('currentRatio')
        div_y      = r.get('divYield')
        div_r      = r.get('divRate')
        payout     = r.get('payoutRatio')
        fcf        = r.get('fcf')
        beta       = r.get('beta')
        short_rt   = r.get('shortRatio')
        pm         = r.get('profitMargin')
        gm         = r.get('grossMargin')
        om         = r.get('operatingMargin')
        rev_g      = r.get('revGrowth')
        eps_g      = r.get('epsGrowth')
        t_eps      = r.get('trailingEps')
        f_eps      = r.get('forwardEps')
        fund_score = r.get('fundScore', 0)
        # Events
        next_earn  = r.get('nextEarnings')
        next_label = r.get('nextEventLabel','')
        next_div   = r.get('nextExDiv')
        days_ev    = r.get('daysToEvent', 9999)

        status_cls = {'Breakout':'status-break','NearPivot':'status-near','Watch':'status-watch'}.get(status,'')
        status_icon = {'Breakout':'🔥','NearPivot':'👀','Watch':'📋'}.get(status,'')

        chg1d_col  = pct_color(chg1d)
        chg5d_col  = pct_color(chg5d)
        chg250d_col= pct_color(chg250d)

        event_html = ""
        if next_label and days_ev < 30:
            urgency = "event-urgent" if days_ev <= 7 else ("event-soon" if days_ev <= 14 else "event-upcoming")
            event_html = f'<div class="event-badge {urgency}">📅 {next_label}</div>'
        elif next_earn:
            event_html = f'<div class="event-badge event-upcoming">📅 Earnings {next_earn}</div>'

        if next_div:
            event_html += f'<div class="event-badge event-div">💰 Ex-Div {next_div}</div>'

        sepa_checks_html = "".join([
            f'<span class="sepa-check {"on" if checks.get(k) else "off"}" title="{lbl}">{abbr}</span>'
            for k, abbr, lbl in [
                ('ma50','50','Above MA50'),('ma150','150','Above MA150'),('ma200','200','Above MA200'),
                ('trend','T↑','MA50>150>200'),('trend200','200↑','MA200 rising'),
                ('high','52H','Within 25% of 52W high'),('low','52L','25%+ above 52W low')
            ]
        ])

        vol_trend_html = ""
        if vol_trend is not None:
            vt_col = "#22c55e" if vol_trend > 10 else ("#ef4444" if vol_trend < -10 else "#f59e0b")
            vol_trend_html = f'<span style="color:{vt_col};font-size:11px">5d avg {vol_trend:+.0f}%</span>'

        return f'''
<div class="card {status_cls}" data-ticker="{ticker}" data-sepa="{sepa}" data-vcp="{vcp}"
     data-sector="{sector}" data-mktcap="{r.get("mktcap",0)}" data-status="{status}"
     data-rsi="{rsi or 0}" data-vol="{volr}">
  <div class="card-header">
    <div class="card-title-row">
      <span class="ticker-name">{ticker.replace(".AX","")}</span>
      <span class="company-name">{name}</span>
      <span class="status-pill {status_cls}">{status_icon} {status}</span>
    </div>
    <div class="card-meta">
      <span class="sector-tag">{sector}</span>
      <span class="mktcap-tag">{mktcap}</span>
      {event_html}
    </div>
  </div>

  <div class="price-row">
    <span class="price-big">${price:.3f}</span>
    <span class="chg-badge" style="color:{chg1d_col}">{f"{chg1d:+.2f}%" if chg1d is not None else "—"}</span>
    <div class="score-pills">
      <span class="score-pill sepa-pill" title="SEPA Score">SEPA {sepa}/7</span>
      <span class="score-pill vcp-pill" title="VCP Score">VCP {vcp}/4</span>
      <span class="score-pill fund-pill" title="Fundamental Score">F {fund_score}/3</span>
    </div>
  </div>

  <!-- SEPA Checks -->
  <div class="sepa-checks-row">{sepa_checks_html}</div>

  <!-- Tab Navigation -->
  <div class="tab-nav">
    <button class="tab-btn active" onclick="switchTab(this,'price')">📈 Price</button>
    <button class="tab-btn" onclick="switchTab(this,'volume')">📊 Volume</button>
    <button class="tab-btn" onclick="switchTab(this,'technical')">🔬 Technical</button>
    <button class="tab-btn" onclick="switchTab(this,'fundamental')">💼 Fundamental</button>
    <button class="tab-btn" onclick="switchTab(this,'catalyst')">🎯 Catalyst</button>
  </div>

  <!-- Price Tab -->
  <div class="tab-panel active" data-tab="price">
    <div class="metrics-grid">
      {metric_cell("1 Day",  f'{chg1d:+.2f}%'  if chg1d  is not None else "—", color=pct_color(chg1d))}
      {metric_cell("5 Day",  f'{chg5d:+.2f}%'  if chg5d  is not None else "—", color=pct_color(chg5d))}
      {metric_cell("20 Day", f'{chg20d:+.2f}%' if chg20d is not None else "—", color=pct_color(chg20d))}
      {metric_cell("60 Day", f'{chg60d:+.2f}%' if chg60d is not None else "—", color=pct_color(chg60d))}
      {metric_cell("1 Year", f'{chg250d:+.2f}%' if chg250d is not None else "—", color=pct_color(chg250d))}
      {metric_cell("52W High", f'${hi52:.3f}' if hi52 else "—")}
      {metric_cell("52W Low",  f'${lo52:.3f}'  if lo52  else "—")}
      {metric_cell("From High", f'{pct_from_hi:+.1f}%' if pct_from_hi is not None else "—", color=pct_color(pct_from_hi))}
      {metric_cell("From Low",  f'{pct_from_lo:+.1f}%' if pct_from_lo is not None else "—", color=pct_color(pct_from_lo))}
      {metric_cell("MA 50",  f'${ma50:.3f}'  if ma50  else "—", color="#22c55e" if price > (ma50 or 0) else "#ef4444")}
      {metric_cell("MA 150", f'${ma150:.3f}' if ma150 else "—", color="#22c55e" if price > (ma150 or 0) else "#ef4444")}
      {metric_cell("MA 200", f'${ma200:.3f}' if ma200 else "—", color="#22c55e" if price > (ma200 or 0) else "#ef4444")}
    </div>
    {f'<div class="pivot-note">📍 Near Pivot: ${recent_hi:.3f}</div>' if near_pivot and recent_hi else ""}
    {f'<div class="analysis-text">{analysis}</div>' if analysis else ""}
  </div>

  <!-- Volume Tab -->
  <div class="tab-panel" data-tab="volume">
    <div class="metrics-grid">
      {metric_cell("Today Vol", f'{vol_today:,.0f}' if vol_today else "—")}
      {metric_cell("20D Avg Vol", f'{vol_avg20:,.0f}' if vol_avg20 else "—")}
      {metric_cell("Vol Ratio", f'{volr:.2f}x', color="#22c55e" if volr >= 1.5 else ("#f59e0b" if volr >= 1.0 else "#ef4444"))}
      {metric_cell("Dollar Vol", f'${dollar_vol:.1f}M' if dollar_vol else "—")}
      {metric_cell("Vol Trend 5D", f'{vol_trend:+.1f}%' if vol_trend is not None else "—", color=pct_color(vol_trend))}
    </div>
    <div class="vol-section">
      <div class="vol-label">Buy / Sell Pressure (10-day estimate)</div>
      {vol_bar(buy_pct, sell_pct)}
    </div>
    <div class="vol-note">
      Volume ratio ≥ 1.5x flags a breakout. Buy/sell split estimated from price action (close vs open per bar).
    </div>
  </div>

  <!-- Technical Tab -->
  <div class="tab-panel" data-tab="technical">
    <div class="metrics-grid">
      {metric_cell("RSI (14)", str(rsi) if rsi else "—", color="#ef4444" if (rsi or 0) > 70 else ("#22c55e" if (rsi or 0) < 30 else "#888"))}
      {metric_cell("ATR %", f'{atr_pct:.2f}%' if atr_pct else "—")}
      {metric_cell("BB Width", f'{bb_bw:.1f}%' if bb_bw else "—")}
      {metric_cell("BB Position", f'{bb_pos:.0f}%' if bb_pos else "—", color="#ef4444" if (bb_pos or 0) > 80 else ("#22c55e" if (bb_pos or 0) < 20 else "#888"))}
      {metric_cell("Beta", str(beta) if beta else "—")}
      {metric_cell("Short Ratio", str(short_rt) if short_rt else "—")}
    </div>
    <div class="rsi-section">
      <div class="indicator-label">RSI (14)</div>
      {rsi_gauge(rsi)}
    </div>
    <div class="bb-section">
      <div class="indicator-label">Bollinger Band Position</div>
      {bb_indicator(bb_pos)}
    </div>
  </div>

  <!-- Fundamental Tab -->
  <div class="tab-panel" data-tab="fundamental">
    <div class="fund-grid">
      <div class="fund-section">
        <div class="fund-section-title">Valuation</div>
        {metric_cell("P/E Ratio", str(pe) if pe else "—")}
        {metric_cell("P/B Ratio", str(pb) if pb else "—")}
        {metric_cell("P/S Ratio", str(ps) if ps else "—")}
        {metric_cell("PEG Ratio", str(peg) if peg else "—")}
        {metric_cell("Trailing EPS", f'${t_eps:.3f}' if t_eps else "—")}
        {metric_cell("Forward EPS", f'${f_eps:.3f}' if f_eps else "—")}
      </div>
      <div class="fund-section">
        <div class="fund-section-title">Growth</div>
        {metric_cell("Revenue Growth", f'{rev_g:+.1f}%' if rev_g is not None else "—", color=pct_color(rev_g))}
        {metric_cell("EPS Growth", f'{eps_g:+.1f}%' if eps_g is not None else "—", color=pct_color(eps_g))}
        {metric_cell("Gross Margin", f'{gm:.1f}%' if gm else "—")}
        {metric_cell("Operating Margin", f'{om:.1f}%' if om else "—")}
        {metric_cell("Net Margin", f'{pm:.1f}%' if pm else "—", color=pct_color(pm))}
        {metric_cell("Free Cash Flow", f'${fcf:.0f}M' if fcf else "—")}
      </div>
      <div class="fund-section">
        <div class="fund-section-title">Balance Sheet</div>
        {metric_cell("ROE", f'{roe:.1f}%' if roe else "—", color=pct_color(roe))}
        {metric_cell("ROA", f'{roa:.1f}%' if roa else "—", color=pct_color(roa))}
        {metric_cell("Debt/Equity", str(de) if de else "—", color="#ef4444" if (de or 0) > 2 else "#22c55e")}
        {metric_cell("Current Ratio", str(cur_r) if cur_r else "—", color="#22c55e" if (cur_r or 0) > 1.5 else "#f59e0b")}
        {metric_cell("Dividend Yield", f'{div_y:.1f}%' if div_y else "—")}
        {metric_cell("Payout Ratio", f'{payout:.0f}%' if payout else "—")}
      </div>
    </div>
  </div>

  <!-- Catalyst Tab -->
  <div class="tab-panel" data-tab="catalyst">
    <div class="catalyst-grid">
      <div class="catalyst-item">
        <div class="catalyst-label">📊 Next Earnings</div>
        <div class="catalyst-value">{next_earn or "Not scheduled"}</div>
        {f'<div class="catalyst-countdown {"urgent" if days_ev <= 7 else "soon"}">{days_ev} days away</div>' if next_earn and days_ev < 365 else ""}
      </div>
      <div class="catalyst-item">
        <div class="catalyst-label">💰 Ex-Dividend Date</div>
        <div class="catalyst-value">{next_div or "—"}</div>
        {f'<div class="catalyst-div-rate">Rate: ${div_r:.3f} | Yield: {div_y:.1f}%</div>' if div_r and div_y else ""}
      </div>
      <div class="catalyst-item">
        <div class="catalyst-label">📈 Revenue Trend</div>
        <div class="catalyst-value" style="color:{pct_color(rev_g)}">{f"{rev_g:+.1f}% YoY" if rev_g is not None else "—"}</div>
      </div>
      <div class="catalyst-item">
        <div class="catalyst-label">💵 EPS Trend</div>
        <div class="catalyst-value" style="color:{pct_color(eps_g)}">{f"{eps_g:+.1f}% YoY" if eps_g is not None else "—"}</div>
      </div>
    </div>
    {f'<div class="short-signal-row">🔔 {short_sig}</div>' if short_sig else ""}
  </div>
</div>'''

    # ── Build cards HTML ──────────────────────────────────────────────────────
    def section_html(title, icon, stocks, css_id):
        if not stocks:
            return f'<section id="{css_id}"><h2>{icon} {title} <span class="count">0</span></h2><p class="empty-msg">No stocks in this category today.</p></section>'
        cards = "\n".join(render_card(r) for r in stocks)
        return f'<section id="{css_id}"><h2>{icon} {title} <span class="count">{len(stocks)}</span></h2><div class="card-grid">{cards}</div></section>'

    breakout_html  = section_html("Breakouts", "🔥", breakouts, "breakouts")
    nearpivot_html = section_html("Near Pivot", "👀", near_pivot, "nearpivot")
    watch_html     = section_html("Watch List", "📋", watch, "watchlist")

    sector_options = "\n".join(f'<option value="{s}">{s}</option>' for s in all_sectors)

    total = len(data)
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ASX SEPA+VCP Screener — {today}</title>
<style>
:root {{
  --bg: #0f1117; --bg2: #1a1d27; --bg3: #22263a;
  --border: #2e3250; --text: #e2e8f0; --dim: #64748b;
  --green: #22c55e; --red: #ef4444; --yellow: #f59e0b;
  --blue: #3b82f6; --purple: #8b5cf6; --teal: #14b8a6;
  --break: #ef4444; --near: #f59e0b; --watch: #3b82f6;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 13px; line-height: 1.5; }}

/* ── Header ── */
.header {{ background: var(--bg2); border-bottom: 1px solid var(--border); padding: 16px 20px; position: sticky; top: 0; z-index: 100; }}
.header-top {{ display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }}
.logo {{ font-size: 18px; font-weight: 700; color: var(--text); }}
.logo span {{ color: var(--blue); }}
.updated {{ color: var(--dim); font-size: 11px; }}
.summary-pills {{ display: flex; gap: 8px; flex-wrap: wrap; }}
.summary-pill {{ padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }}
.pill-total  {{ background: #1e293b; border: 1px solid var(--border); }}
.pill-break  {{ background: rgba(239,68,68,.15); border: 1px solid var(--break); color: var(--break); }}
.pill-near   {{ background: rgba(245,158,11,.15); border: 1px solid var(--near); color: var(--near); }}
.pill-watch  {{ background: rgba(59,130,246,.15); border: 1px solid var(--watch); color: var(--watch); }}

/* ── Filters ── */
.filters {{ background: var(--bg2); border-bottom: 1px solid var(--border); padding: 10px 20px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }}
.filter-group {{ display: flex; align-items: center; gap: 6px; }}
.filter-group label {{ color: var(--dim); font-size: 11px; text-transform: uppercase; letter-spacing: .5px; }}
select, input[type=range] {{ background: var(--bg3); border: 1px solid var(--border); color: var(--text); border-radius: 6px; padding: 4px 8px; font-size: 12px; cursor: pointer; }}
.sort-btn {{ background: var(--bg3); border: 1px solid var(--border); color: var(--dim); padding: 4px 10px; border-radius: 6px; font-size: 11px; cursor: pointer; }}
.sort-btn.active {{ border-color: var(--blue); color: var(--blue); }}
.filter-search {{ background: var(--bg3); border: 1px solid var(--border); color: var(--text); border-radius: 6px; padding: 4px 10px; font-size: 12px; width: 160px; }}
.filter-search::placeholder {{ color: var(--dim); }}

/* ── Main layout ── */
main {{ max-width: 1600px; margin: 0 auto; padding: 20px; }}
section {{ margin-bottom: 32px; }}
section h2 {{ font-size: 16px; font-weight: 700; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }}
.count {{ background: var(--bg3); border: 1px solid var(--border); border-radius: 10px; padding: 2px 8px; font-size: 11px; color: var(--dim); }}
.empty-msg {{ color: var(--dim); font-style: italic; padding: 20px 0; }}
.card-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 14px; }}

/* ── Cards ── */
.card {{ background: var(--bg2); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; transition: transform .15s, box-shadow .15s; }}
.card:hover {{ transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,.4); }}
.card.status-break {{ border-left: 3px solid var(--break); }}
.card.status-near  {{ border-left: 3px solid var(--near); }}
.card.status-watch {{ border-left: 3px solid var(--watch); }}

.card-header {{ padding: 12px 14px 8px; }}
.card-title-row {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 4px; }}
.ticker-name {{ font-size: 16px; font-weight: 800; color: var(--text); }}
.company-name {{ font-size: 11px; color: var(--dim); flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.status-pill {{ font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 10px; }}
.status-pill.status-break {{ background: rgba(239,68,68,.15); color: var(--break); border: 1px solid var(--break); }}
.status-pill.status-near  {{ background: rgba(245,158,11,.15); color: var(--near);  border: 1px solid var(--near); }}
.status-pill.status-watch {{ background: rgba(59,130,246,.15);  color: var(--watch); border: 1px solid var(--watch); }}
.card-meta {{ display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }}
.sector-tag, .mktcap-tag {{ background: var(--bg3); border: 1px solid var(--border); border-radius: 6px; padding: 2px 6px; font-size: 10px; color: var(--dim); }}

/* Event badges */
.event-badge {{ font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 6px; }}
.event-urgent   {{ background: rgba(239,68,68,.2);  color: var(--break); border: 1px solid var(--break); }}
.event-soon     {{ background: rgba(245,158,11,.2); color: var(--yellow); border: 1px solid var(--yellow); }}
.event-upcoming {{ background: rgba(59,130,246,.2); color: var(--blue);  border: 1px solid var(--blue); }}
.event-div      {{ background: rgba(34,197,94,.2);  color: var(--green); border: 1px solid var(--green); }}

.price-row {{ display: flex; align-items: center; gap: 10px; padding: 8px 14px; background: var(--bg3); }}
.price-big {{ font-size: 20px; font-weight: 800; }}
.chg-badge {{ font-size: 13px; font-weight: 600; }}
.score-pills {{ display: flex; gap: 5px; margin-left: auto; }}
.score-pill {{ font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 8px; }}
.sepa-pill {{ background: rgba(139,92,246,.2); color: var(--purple); border: 1px solid var(--purple); }}
.vcp-pill  {{ background: rgba(20,184,166,.2);  color: var(--teal);   border: 1px solid var(--teal); }}
.fund-pill {{ background: rgba(34,197,94,.2);   color: var(--green);  border: 1px solid var(--green); }}

/* SEPA check row */
.sepa-checks-row {{ padding: 6px 14px; display: flex; gap: 4px; flex-wrap: wrap; border-bottom: 1px solid var(--border); }}
.sepa-check {{ font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; cursor: help; }}
.sepa-check.on  {{ background: rgba(34,197,94,.2);  color: var(--green); border: 1px solid rgba(34,197,94,.3); }}
.sepa-check.off {{ background: rgba(100,116,139,.1); color: var(--dim);  border: 1px solid var(--border); }}

/* Tabs */
.tab-nav {{ display: flex; gap: 2px; padding: 6px 10px 0; border-bottom: 1px solid var(--border); overflow-x: auto; scrollbar-width: none; }}
.tab-nav::-webkit-scrollbar {{ display: none; }}
.tab-btn {{ background: none; border: none; color: var(--dim); font-size: 11px; font-weight: 600; padding: 4px 10px; cursor: pointer; border-bottom: 2px solid transparent; white-space: nowrap; transition: color .15s; }}
.tab-btn.active {{ color: var(--blue); border-bottom-color: var(--blue); }}
.tab-btn:hover {{ color: var(--text); }}

.tab-panel {{ display: none; padding: 12px 14px; }}
.tab-panel.active {{ display: block; }}

/* Metrics grid */
.metrics-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }}
.metric {{ background: var(--bg3); border-radius: 6px; padding: 6px 8px; }}
.metric-lbl {{ font-size: 10px; color: var(--dim); display: block; margin-bottom: 2px; }}
.metric-val {{ font-size: 12px; font-weight: 600; }}

.pivot-note {{ margin-top: 8px; font-size: 11px; color: var(--yellow); background: rgba(245,158,11,.1); border: 1px solid rgba(245,158,11,.3); border-radius: 6px; padding: 4px 8px; }}
.analysis-text {{ margin-top: 8px; font-size: 11px; color: var(--dim); line-height: 1.5; }}

/* Volume tab */
.vol-section {{ margin-top: 10px; }}
.vol-label {{ font-size: 11px; color: var(--dim); margin-bottom: 5px; }}
.vol-bar-wrap {{ height: 12px; border-radius: 6px; overflow: hidden; display: flex; }}
.vol-bar-buy  {{ background: var(--green); height: 100%; }}
.vol-bar-sell {{ background: var(--red);   height: 100%; }}
.vol-bar-labels {{ display: flex; justify-content: space-between; margin-top: 3px; }}
.buy-lbl  {{ font-size: 10px; font-weight: 600; color: var(--green); }}
.sell-lbl {{ font-size: 10px; font-weight: 600; color: var(--red); }}
.vol-note {{ margin-top: 10px; font-size: 10px; color: var(--dim); font-style: italic; }}

/* RSI gauge */
.rsi-section, .bb-section {{ margin-top: 10px; }}
.indicator-label {{ font-size: 10px; color: var(--dim); margin-bottom: 4px; }}
.rsi-wrap {{ background: var(--bg3); border-radius: 6px; height: 14px; position: relative; overflow: hidden; }}
.rsi-bar {{ height: 100%; border-radius: 6px; transition: width .3s; }}
.rsi-bar.overbought {{ background: var(--red); }}
.rsi-bar.oversold   {{ background: var(--green); }}
.rsi-bar.neutral    {{ background: var(--blue); }}
.rsi-val {{ position: absolute; right: 6px; top: 50%; transform: translateY(-50%); font-size: 10px; font-weight: 700; }}
.bb-wrap {{ background: var(--bg3); border-radius: 6px; height: 14px; position: relative; overflow: hidden; }}
.bb-fill {{ height: 100%; border-radius: 6px; }}
.bb-fill.bb-high {{ background: var(--red); }}
.bb-fill.bb-low  {{ background: var(--green); }}
.bb-fill.bb-mid  {{ background: var(--blue); }}
.bb-val {{ position: absolute; right: 6px; top: 50%; transform: translateY(-50%); font-size: 10px; font-weight: 700; }}

/* Fundamentals */
.fund-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }}
.fund-section {{ }}
.fund-section-title {{ font-size: 11px; font-weight: 700; color: var(--blue); margin-bottom: 6px; text-transform: uppercase; letter-spacing: .5px; }}

/* Catalyst */
.catalyst-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }}
.catalyst-item {{ background: var(--bg3); border-radius: 8px; padding: 10px; }}
.catalyst-label {{ font-size: 10px; color: var(--dim); margin-bottom: 4px; }}
.catalyst-value {{ font-size: 13px; font-weight: 600; }}
.catalyst-countdown {{ margin-top: 3px; font-size: 10px; font-weight: 700; }}
.catalyst-countdown.urgent {{ color: var(--break); }}
.catalyst-countdown.soon   {{ color: var(--yellow); }}
.catalyst-div-rate {{ margin-top: 3px; font-size: 10px; color: var(--dim); }}
.short-signal-row {{ margin-top: 10px; font-size: 11px; color: var(--yellow); background: rgba(245,158,11,.1); border: 1px solid rgba(245,158,11,.2); border-radius: 6px; padding: 6px 10px; }}

.dim {{ color: var(--dim); }}

@media (max-width: 600px) {{
  .fund-grid {{ grid-template-columns: 1fr; }}
  .catalyst-grid {{ grid-template-columns: 1fr; }}
  .metrics-grid {{ grid-template-columns: repeat(2, 1fr); }}
}}
</style>
</head>
<body>

<header class="header">
  <div class="header-top">
    <div class="logo">ASX <span>SEPA+VCP</span> Screener</div>
    <div class="updated">Updated: {today} · {total} stocks screened</div>
    <div class="summary-pills">
      <span class="summary-pill pill-total">📊 {total} Total</span>
      <span class="summary-pill pill-break">🔥 {len(breakouts)} Breakouts</span>
      <span class="summary-pill pill-near">👀 {len(near_pivot)} Near Pivot</span>
      <span class="summary-pill pill-watch">📋 {len(watch)} Watch</span>
    </div>
  </div>
</header>

<div class="filters">
  <input type="text" class="filter-search" placeholder="🔍 Search ticker or name..." onkeyup="applyFilters()">
  <div class="filter-group">
    <label>Sector</label>
    <select onchange="applyFilters()">
      <option value="">All Sectors</option>
      {sector_options}
    </select>
  </div>
  <div class="filter-group">
    <label>SEPA ≥</label>
    <select id="f-sepa" onchange="applyFilters()">
      <option value="0">Any</option>
      <option value="3">3+</option>
      <option value="4">4+</option>
      <option value="5">5+</option>
      <option value="6">6+</option>
    </select>
  </div>
  <div class="filter-group">
    <label>VCP ≥</label>
    <select id="f-vcp" onchange="applyFilters()">
      <option value="0">Any</option>
      <option value="2">2+</option>
      <option value="3">3+</option>
      <option value="4">4</option>
    </select>
  </div>
  <div class="filter-group">
    <label>Status</label>
    <select id="f-status" onchange="applyFilters()">
      <option value="">All</option>
      <option value="Breakout">Breakout</option>
      <option value="NearPivot">Near Pivot</option>
      <option value="Watch">Watch</option>
    </select>
  </div>
  <div class="filter-group">
    <label>Vol ≥</label>
    <select id="f-vol" onchange="applyFilters()">
      <option value="0">Any</option>
      <option value="1.5">1.5x</option>
      <option value="2">2x</option>
      <option value="3">3x</option>
    </select>
  </div>
  <div class="filter-group">
    <label>Sort</label>
    <select id="f-sort" onchange="applyFilters()">
      <option value="sepa">SEPA Score</option>
      <option value="vcp">VCP Score</option>
      <option value="vol">Volume Ratio</option>
      <option value="chg1d">1D Change</option>
      <option value="chg250d">1Y Change</option>
      <option value="mktcap">Market Cap</option>
    </select>
  </div>
</div>

<main>
  {breakout_html}
  {nearpivot_html}
  {watch_html}
</main>

<script>
function switchTab(btn, tabName) {{
  const card = btn.closest('.card');
  card.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  card.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  card.querySelector(`[data-tab="${{tabName}}"]`).classList.add('active');
}}

function applyFilters() {{
  const search = document.querySelector('.filter-search').value.toLowerCase();
  const sector = document.querySelector('select').value;
  const sepa   = parseFloat(document.getElementById('f-sepa').value) || 0;
  const vcp    = parseFloat(document.getElementById('f-vcp').value) || 0;
  const status = document.getElementById('f-status').value;
  const vol    = parseFloat(document.getElementById('f-vol').value) || 0;
  const sort   = document.getElementById('f-sort').value;

  let cards = Array.from(document.querySelectorAll('.card'));

  cards.forEach(c => {{
    const ticker  = (c.dataset.ticker || '').toLowerCase();
    const cname   = (c.querySelector('.company-name')?.textContent || '').toLowerCase();
    const csector = c.dataset.sector || '';
    const csepa   = parseInt(c.dataset.sepa) || 0;
    const cvcp    = parseInt(c.dataset.vcp) || 0;
    const cstatus = c.dataset.status || '';
    const cvol    = parseFloat(c.dataset.vol) || 0;
    const matchSearch = !search || ticker.includes(search) || cname.includes(search);
    const matchSector = !sector || csector === sector;
    const matchSepa   = csepa >= sepa;
    const matchVcp    = cvcp  >= vcp;
    const matchStatus = !status || cstatus === status;
    const matchVol    = cvol  >= vol;
    c.style.display = (matchSearch && matchSector && matchSepa && matchVcp && matchStatus && matchVol) ? '' : 'none';
  }});

  // Re-sort visible cards within each grid
  document.querySelectorAll('.card-grid').forEach(grid => {{
    const visible = Array.from(grid.querySelectorAll('.card')).filter(c => c.style.display !== 'none');
    visible.sort((a,b) => {{
      const getVal = (c) => {{
        if (sort === 'sepa')    return parseInt(c.dataset.sepa) || 0;
        if (sort === 'vcp')     return parseInt(c.dataset.vcp) || 0;
        if (sort === 'vol')     return parseFloat(c.dataset.vol) || 0;
        if (sort === 'mktcap')  return parseInt(c.dataset.mktcap) || 0;
        return 0;
      }};
      return getVal(b) - getVal(a);
    }});
    visible.forEach(c => grid.appendChild(c));
  }});
}}
</script>
</body>
</html>'''
    return html

def publish(path):
    if not NETLIFY_TOKEN or not NETLIFY_SITE_ID:
        print("No Netlify credentials — skipping deploy")
        return
    print("Publishing to Netlify...")
    try:
        with open(path, 'rb') as f:
            content = f.read()
        sha = hashlib.sha1(content).hexdigest()
        deploy_url = f"https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_ID}/deploys"
        headers_json = {"Authorization": f"Bearer {NETLIFY_TOKEN}", "Content-Type": "application/json"}
        r = requests.post(deploy_url, headers=headers_json, json={"files": {"/index.html": sha}})
        try: deploy = r.json()
        except Exception as e: print(f"Netlify gave non-JSON response: {r.text[:200]}"); return
        did = deploy.get("id")
        if not did: return
        r2 = requests.put(f"https://api.netlify.com/api/v1/deploys/{did}/files/index.html",
                         headers={"Authorization": f"Bearer {NETLIFY_TOKEN}", "Content-Type": "application/octet-stream"},
                         data=content)
        if r2.status_code == 200: print(f"Published: https://{NETLIFY_SITE_ID}.netlify.app")
        else: print(f"Netlify Upload Failed: {r2.status_code} {r2.text[:200]}")
    except Exception as err:
        print(f"Deployment failure: {err}")
