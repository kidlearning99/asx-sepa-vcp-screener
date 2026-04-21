import sys
import re

with open(r'c:\Claude AI\asx-sepa-vcp-screener\build_dashboard.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Redefine det(r) with the correct layout and nuances.
det_body = r'''function det(r){{
  var c=r.checks;
  var stg=r.stage||1;
  var sc2=SCOL[stg];
  var crows=[[c.ma50,CUR+r.price+' > MA50 ('+CUR+(r.ma50?r.ma50.toFixed(2):'0')+')'],[c.ma150,'MA50 > MA150 ('+CUR+(r.ma150?r.ma150.toFixed(2):'0')+')'],[c.ma200,'MA150 > MA200 ('+CUR+(r.ma200?r.ma200.toFixed(2):'0')+')'],[c.trend,'200-day MA trending up (12M: '+(r.chg250d>=0?'+':'')+r.chg250d+'%)'],[c.high,'Within 25% of 52W high ('+r.pctFromHigh+'% below)'],[c.low,'25%+ above 52W low ('+r.pctAboveLow+'% above)'],[c.vol,'Volume breakout >=1.5x ('+r.volRatio+'x), PVR '+r.pvr]].map(function(p){{return '<div class="cr '+(p[0]?'ok':'no')+'"><span class="ci">'+(p[0]?'\u2713':'\u2717')+'</span>'+p[1]+'</div>';}}).join('');
  
  var vd=['No contraction','Weak (1/4)','Moderate (2/4)','Good (3/4) \u2014 VCP forming','Ideal (4/4) \u2014 textbook base'][r.vcpScore];
  var ac=r.status==='breakout'?'abuy':r.status==='near-pivot'?'awch':'ahld';
  var at=r.status==='breakout'?'\u2192 BUY ZONE: Consider entry. Stop-loss below MA50. Risk 1-2%.':r.status==='near-pivot'?'\u2192 WATCHLIST: Alert at pivot high. Enter on breakout with vol >1.5x.':'\u2192 MONITOR: Wait for VCP to tighten and volume to dry up.';
  var rg=r.revGrowth,eg=r.epsGrowth,nm=r.netMargin,te=r.trailingEps,fe=r.forwardEps,fs=r.fundScore||0;
  var fp2='';for(var j=0;j<3;j++)fp2+='<div class="fpip" style="display:inline-block;width:9px;height:9px;border-radius:2px;background:'+(j<fs?'#ff9f43':'#1a2540')+';border:1px solid '+(j<fs?'#ff9f43':'#1e2d45')+'"></div>&nbsp;';

  var fundCol='<div style="min-width:0">'+
    '<div class="dh">Net Revenue &nbsp;'+fp2+'</div>'+
    revTrendChip(r.revTrend)+
    revBars(r.revQuarters)+
    '<table class="mat">'+
    '<tr><td class="mlb">Rev YoY</td><td class="mbar"></td><td class="mgv">'+fmtGrowth(rg)+'</td></tr>'+
    '<tr><td class="mlb">EPS Grw</td><td class="mbar"></td><td class="mgv">'+fmtGrowth(eg,10,0)+'</td></tr>'+
    '</table>'+
    '</div>';
    
  var evHtml='<div class="ev-none">No upcoming events</div>';
  var evLines=[];
  if(r.nextEventLabel){{
    var hot=r.nextEventLabel.includes('\u26a1');
    evLines.push('<div class="'+(hot?'ev-hot':'ev-soon')+'">'+r.nextEventLabel+'</div>');
  }}
  if(r.nextExDiv)evLines.push('<div class="ev-div">\u1F4B0 Ex-Div: '+r.nextExDiv+'</div>');
  if(evLines.length)evHtml=evLines.join('');
  
  var entry=r.price,stop=r.ma50||(r.price*0.93),risk=entry-stop;
  var target=risk>0?(entry+2*risk).toFixed(2):null;
  var tlBox='<div class="tl-box" style="padding:10px 8px;margin-bottom:8px">'+
    '<div class="tl-title" style="font-size:9px;margin-bottom:6px">\u26A1 TRADE LEVELS</div>'+
    '<div style="display:flex;flex-direction:column;gap:5px">'+
    '<div style="background:#081a0f;border:1px solid rgba(0,208,132,.25);border-radius:4px;padding:4px;text-align:center"><div style="font-size:7px;color:#5a7a9a;margin-bottom:2px">BUY ABOVE</div><div style="font-size:11px;font-weight:700;color:#00d084">'+CUR+entry.toFixed(2)+'</div></div>'+
    '<div style="background:#1a0809;border:1px solid rgba(255,71,87,.25);border-radius:4px;padding:4px;text-align:center"><div style="font-size:7px;color:#5a7a9a;margin-bottom:2px">STOP LOSS</div><div style="font-size:11px;font-weight:700;color:#ff4757">'+CUR+stop.toFixed(2)+'</div></div>'+
    '</div></div>';

  var vcpPointers = ['Base is loose or trending down. Wait for a constructive base to form.', 'Early signs of contraction. Still too loose to buy.', 'Base is forming. Watch for tightening spreads on the right side.', 'Good VCP forming. Volume is drying up. Stalk entry near pivot high.', 'Textbook VCP. Extreme volatility contraction. Prime entry setup on volume breakout.'][r.vcpScore];

  var adr = (r.accDistRatio !== undefined) ? r.accDistRatio : 1.0;
  var adrCol = adr >= 1.5 ? '#00d084' : adr >= 1.0 ? '#8bc34a' : '#ff4757';
  var adrTxt = adr >= 1.5 ? 'Strong Institutional Accumulation' : adr >= 1.2 ? 'Healthy Buying Bias' : 'Check distribution signals';
  
  var smartMoneyHtml = '<div>'+
    '<div class="dh">Smart Money Indicators</div>'+
    '<div class="abox" style="padding:10px;font-size:11px;border-left-color:'+adrCol+';line-height:1.6;background:var(--bg3);border:1px solid var(--border);border-left:3.5px solid '+adrCol+'">'+
    '<div style="font-size:12px;font-weight:800;color:#fff;margin-bottom:5px">60D Acc/Dist: <span style="color:'+adrCol+'">'+adr.toFixed(2)+'x</span></div>'+
    '<div style="font-size:10px;color:var(--muted);margin-bottom:8px">'+adrTxt+'</div>'+
    '<div style="display:flex;justify-content:space-between;border-top:1px solid var(--border);padding-top:6px"><span style="color:var(--muted)">Price/Vol (PVR):</span><strong style="color:'+(r.pvr>1.1?'#00d084':'#ff9f43')+'">'+(r.pvr||0)+'</strong></div>'+
    '<div style="display:flex;justify-content:space-between"><span style="color:var(--muted)">Vol vs 50D:</span><strong style="color:'+(r.volRatio>=1.5?'#00d084':'#ff9f43')+'">'+(r.volRatio||0).toFixed(1)+'x</strong></div>'+
    '</div></div>';

  var candleSigsHTML = '<div style="margin-top:12px"><div class="dh" style="color:var(--gold)">Advanced Price Action Highlights</div>';
  if(r.candleSignals && r.candleSignals.length > 0){{
    for(var k=0; k<r.candleSignals.length; k++){{
      var sig = r.candleSignals[k];
      var ico = sig.includes('Pivot') ? '\u26a1' : sig.includes('Squat') ? '\U0001F3CB' : sig.includes('Inside') ? '\U0001F92B' : '\U0001F504';
      var col = sig.includes('Accumulation') || sig.includes('Absorbed') || sig.includes('Pivot') ? '#00d084' : sig.includes('Distribution') ? '#ff4757' : '#ff9f43';
      var dsc = sig.includes('Pivot')?'Heavy institutional buying. Yesterdays up volume exceeds highest down volume of past 10 days.':sig.includes('Inside')?'Volume has dried up as price tightens. Sellers are exhausted.':sig.includes('Squat')?'Large volume prints but price made no progress. Usually masks hidden accumulation (or distribution).':'Price undercut previous lows but closed strong. Supply was aggressively absorbed.';
      candleSigsHTML += '<div style="background:var(--bg2);padding:9px;border-radius:6px;margin-bottom:6px;border:1px solid var(--border);border-left:3px solid '+col+'">'+
        '<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px"><span style="font-size:14px">'+ico+'</span><span style="font-size:11px;font-weight:700;color:'+col+'">'+sig+'</span></div>'+
        '<div style="font-size:10px;color:var(--muted);line-height:1.3">'+dsc+'</div></div>';
    }}
  }} else {{
    candleSigsHTML += '<div style="background:var(--bg2);padding:9px;border-radius:6px;border:1px solid var(--border);font-size:10px;color:var(--muted);line-height:1.3">No standout anomalies (e.g. Squats) detected in last 5 days. Volume flow remains characteristic of '+(r.accDistRatio>1.1?'accumulation':'consolidation')+'.</div>';
  }}
  candleSigsHTML += '</div>';

  var nuances = [];
  if(stg===2) nuances.push('Confirmed Stage 2 Uptrend. Institutions are in control.');
  if(r.vcpScore>=3) nuances.push('Aggressive VCP contraction ('+r.vcpScore+'/4). Price is coiling for a major move.');
  if(r.accDistRatio>1.5) nuances.push('Extreme institutional footprint; buying pressure is out-pacing supply by 50%+.');
  if(r.pctFromHigh<5) nuances.push('Stock is stalking 52W Highs; Relative Strength is elite vs the broader ASX.');
  if(r.volRatio<0.7) nuances.push('Volume dry-up (VDU) detected. Supply exhaustion near pivot point.');
  if(r.candleSignals.some(s=>s.includes('Pivot'))) nuances.push('Actionable Pocket Pivot occurred; signals internal strength entering the base.');
  if(nuances.length===0) nuances.push('Stock is currently consolidating. Wait for technical triggers or volume dry-up.');
  
  var nuanceHTML = '<div style="height:100%"><div class="dh">Aggressive Strategy Sentiment</div>'+
    '<div class="abox" style="padding:12px;font-size:11.5px;border-left-color:var(--gold);background:rgba(212,175,55,.05);line-height:1.6">'+
    '<strong style="color:var(--gold);display:block;margin-bottom:6px;font-size:10.5px">STOCK VERDICT</strong>'+
    nuances.slice(0,3).join('<br/><br/>')+
    '<div style="margin-top:12px;padding-top:10px;border-top:1px solid rgba(212,175,55,.2);color:var(--text);font-style:italic;font-size:10.5px">"The biggest moves happen when the setup looks quietest."</div>'+
    '</div></div>';

  var chartCol='<div style="display:flex;flex-direction:column;gap:12px">'+
    '<div><div class="dh">60-Day Candlestick + Volume (orange dash = MA50)</div>'+
    drawCandles(r.ohlcv,r.ma50,r.price)+'</div>'+
    candleSigsHTML+
    '</div>';

  var sepaCol='<div>'+
    '<div class="dh">SEPA Checklist \u2014 '+r.sepaScore+'/7</div>'+
    stageBox+
    '<div class="cl">'+crows+'</div>'+
    '<div class="pi" style="margin-top:12px"><span class="pk">5D Chg</span><span class="'+(r.chg5d>=0?'gn':'rd')+'">'+(r.chg5d>=0?'+':'')+r.chg5d+'%</span></div>'+
    '<div class="pi"><span class="pk">60D Chg</span><span class="'+(r.chg60d>=0?'gn':'rd')+'">'+(r.chg60d>=0?'+':'')+r.chg60d+'%</span></div>'+
    '<div class="pi"><span class="pk">12M Chg</span><span class="'+(r.chg250d>=0?'gn':'rd')+'">'+(r.chg250d>=0?'+':'')+r.chg250d+'%</span></div>'+
    '</div>';

  var vcpCol='<div>'+
    '<div class="dh">Catalysts & VCP Base</div>'+
    evHtml+
    '<div><div class="dh" style="margin-top:12px;margin-bottom:5px">Base Progression</div>'+
    '<div class="abox" style="padding:10px;font-size:11px;border-left-color:var(--blue);line-height:1.4;background:var(--bg3)">'+
    '<strong style="color:#fff">'+vd+'</strong><br/><span style="color:var(--muted)">'+vcpPointers+'</span></div></div>'+
    smartMoneyHtml+
    '</div>';
    
  var tradeCol='<div>'+
    tlBox+
    '<div class="abox" style="margin-top:6px;padding:10px;line-height:1.6">'+
    '<div style="font-weight:800;font-size:9px;color:var(--text);margin-bottom:6px;letter-spacing:0.5px">SUMMARY</div>'+(r.analysis || 'Awaiting breakout confirmation.')+
    '<div class="aact '+ac+'" style="margin-top:8px">'+at+'</div></div>'+
    '</div>';

  return '<div class="dpanel">'+chartCol+sepaCol+fundCol+vcpCol+tradeCol+nuanceHTML+'</div>';
}'''

# Find the start of function det(r) and the end of its first brace match
pattern = re.compile(r'function det\(r\)\{\{.*?return \'<div class="dpanel">\'.*?</div>\';\n\}\}', re.DOTALL)
new_code = pattern.sub(lambda m: det_body.replace('\\', '\\\\'), code)

with open(r'c:\Claude AI\asx-sepa-vcp-screener\build_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(new_code)

print("Restructured dashboard logic: Candlestick signals moved to chartCol, added Aggressive Nuances, and reinforced Smart Money.")
