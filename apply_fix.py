import sys

with open(r'c:\Claude AI\asx-sepa-vcp-screener\build_dashboard.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Fix revBars to show accurate millions
old_rev = r"var fmt=av>=1000?sign+CUR+(av/1000).toFixed(1)+'B':sign+CUR+av.toFixed(0)+'M';"
new_rev = r"""var avM = av / 1000000;
    var fmt=avM>=1000?sign+CUR+(avM/1000).toFixed(1)+'B':sign+CUR+avM.toFixed(0)+'M';"""
code = code.replace(old_rev, new_rev)

# 2. Modify VCP box and add advanced candlestick box (using double braces {{ }} for JS blocks)
old_vcpStr = r'''  var vcpAnalysisHtml = '<div style="margin-top:12px">'+
    '<div class="dh">VCP Analysis ('+r.vcpScore+'/4)</div>'+
    '<div class="abox" style="padding:9px;font-size:10px;border-left-color:var(--blue);line-height:1.5">'+
    '<strong style="color:var(--text)">'+vd+'</strong><br/>'+
    '<span style="color:#5a7a9a;display:inline-block;margin-top:4px">'+vcpPointers+'</span>'+
    '</div></div>';

  var vcpCol='<div>'+
    '<div class="dh">Catalysts &amp; Events</div>'+
    evHtml+
    vcpAnalysisHtml+
    '<div class="abox" style="margin-top:12px;padding:9px">'+
    '<div style="font-weight:700;font-size:9px;color:var(--text);margin-bottom:4px;letter-spacing:0.5px">SUMMARY</div>'+r.analysis+
    '<div class="aact '+ac+'" style="margin-top:6px">'+at+'</div></div>'+
    '</div>';'''

new_vcpStr = r'''  var vcpAnalysisHtml = '<div style="margin-top:12px">'+
    '<div class="dh">VCP Base Progression ('+r.vcpScore+'/4)</div>'+
    '<div class="abox" style="padding:12px;font-size:11px;border-left-color:var(--blue);line-height:1.6;background:var(--bg3);border:1px solid var(--border);border-left:3px solid var(--blue)">'+
    '<strong style="color:#fff;font-size:12px;letter-spacing:0.3px">'+vd+'</strong><br/>'+
    '<span style="color:#8bb4e6;display:inline-block;margin-top:4px">'+vcpPointers+'</span>'+
    '</div></div>';

  var candleSigsHTML = '<div style="margin-top:12px"><div class="dh">Advanced Price Action Analysis</div>';
  if(r.candleSignals && r.candleSignals.length > 0){{
    for(var k=0; k<r.candleSignals.length; k++){{
      var sig = r.candleSignals[k];
      var ico = sig.includes('Pivot') ? '\u26a1' : sig.includes('Squat') ? '\U0001F3CB' : sig.includes('Inside') ? '\U0001F92B' : '\U0001F504';
      var col = sig.includes('Accumulation') || sig.includes('Absorbed') || sig.includes('Pivot') ? '#00d084' : sig.includes('Distribution') ? '#ff4757' : '#ff9f43';
      var dsc = sig.includes('Pivot')?'Heavy institutional buying. Yesterdays up volume exceeds highest down volume of past 10 days.':sig.includes('Inside')?'Volume has completely dried up as price tightens. Sellers are exhausted.':sig.includes('Squat')?'Large volume prints but price made no progress. Usually masks hidden accumulation (or distribution).':'Price undercut previous lows but closed strong. Supply was aggressively absorbed.';
      candleSigsHTML += '<div style="background:var(--bg2);padding:10px;border-radius:6px;margin-bottom:6px;border:1px solid var(--border);border-left:3px solid '+col+'">'+
        '<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px"><span style="font-size:14px">'+ico+'</span><span style="font-size:12px;font-weight:700;color:'+col+'">'+sig+'</span></div>'+
        '<div style="font-size:10.5px;color:var(--muted);line-height:1.4">'+dsc+'</div></div>';
    }}
  }} else {{
    candleSigsHTML += '<div style="background:var(--bg2);padding:10px;border-radius:6px;border:1px solid var(--border);font-size:10.5px;color:var(--muted);line-height:1.4">No standout candlestick anomalies (e.g. Pocket Pivots, Squats) detected in recent trading sessions. Volume flow is normal.</div>';
  }}
  candleSigsHTML += '</div>';

  var vcpCol='<div>'+
    '<div class="dh">Upcoming Event Catalyst</div>'+
    evHtml+
    vcpAnalysisHtml+
    candleSigsHTML+
    '</div>';'''

code = code.replace(old_vcpStr, new_vcpStr)

# 3. Clean up the old candleSigsHTML block which was down at the bottom near chartCol
old_chart_candles = r'''  var candleSigsHTML='';
  if(r.candleSignals && r.candleSignals.length > 0){{
    candleSigsHTML = '<div style="margin-top:12px"><div class="dh">Recent Candlestick Patterns</div>';
    for(var k=0; k<r.candleSignals.length; k++){{
      var sig = r.candleSignals[k];
      var ico = sig.includes('Pivot') ? '\u26a1' : sig.includes('Squat') ? '\U0001F3CB' : sig.includes('Inside') ? '\U0001F92B' : '\U0001F504';
      var col = sig.includes('Accumulation') || sig.includes('Absorbed') || sig.includes('Pivot') ? '#00d084' : sig.includes('Distribution') ? '#ff4757' : '#ff9f43';
      candleSigsHTML += '<div style="display:flex;align-items:center;gap:6px;background:var(--bg2);padding:7px 10px;border-radius:6px;margin-bottom:5px;border:1px solid var(--border);border-left:3px solid '+col+'"><span style="font-size:12px">'+ico+'</span><span style="font-size:11px;font-weight:600;color:'+col+'">'+sig+'</span></div>';
    }}
    candleSigsHTML += '</div>';
  }}

  var chartCol='<div style="display:flex;flex-direction:column;height:100%">'+
    '<div class="dh">60-Day Candlestick + Volume (orange dash = MA50, bright bars = high volume)</div>'+
    drawCandles(r.ohlcv,r.ma50,r.price)+
    candleSigsHTML+
    '</div>';'''

new_chart_candles = r'''  var chartCol='<div style="display:flex;flex-direction:column;height:100%">'+
    '<div class="dh">60-Day Candlestick + Volume (orange dash = MA50, bright bars = high volume)</div>'+
    drawCandles(r.ohlcv,r.ma50,r.price)+
    '</div>';'''

code = code.replace(old_chart_candles, new_chart_candles)

with open(r'c:\Claude AI\asx-sepa-vcp-screener\build_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Applied beautifully")
