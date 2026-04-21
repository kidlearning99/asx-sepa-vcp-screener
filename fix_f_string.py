import sys

with open(r'c:\Claude AI\asx-sepa-vcp-screener\build_dashboard.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Fix the single brackets I accidentally inserted into the javascript which is inside an f-string
bad_block = r'''  var candleSigsHTML = '<div style="margin-top:12px"><div class="dh">Advanced Price Action Analysis</div>';
  if(r.candleSignals && r.candleSignals.length > 0){
    for(var k=0; k<r.candleSignals.length; k++){
      var sig = r.candleSignals[k];
      var ico = sig.includes('Pivot') ? '\u26a1' : sig.includes('Squat') ? '\U0001F3CB' : sig.includes('Inside') ? '\U0001F92B' : '\U0001F504';
      var col = sig.includes('Accumulation') || sig.includes('Absorbed') || sig.includes('Pivot') ? '#00d084' : sig.includes('Distribution') ? '#ff4757' : '#ff9f43';
      var dsc = sig.includes('Pivot')?'Heavy institutional buying. Yesterdays up volume exceeds highest down volume of past 10 days.':sig.includes('Inside')?'Volume has completely dried up as price tightens. Sellers are exhausted.':sig.includes('Squat')?'Large volume prints but price made no progress. Usually masks hidden accumulation (or distribution).':'Price undercut previous lows but closed strong. Supply was aggressively absorbed.';
      candleSigsHTML += '<div style="background:var(--bg2);padding:10px;border-radius:6px;margin-bottom:6px;border:1px solid var(--border);border-left:3px solid '+col+'">'+
        '<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px"><span style="font-size:14px">'+ico+'</span><span style="font-size:12px;font-weight:700;color:'+col+'">'+sig+'</span></div>'+
        '<div style="font-size:10.5px;color:var(--muted);line-height:1.4">'+dsc+'</div></div>';
    }
  } else {
    candleSigsHTML += '<div style="background:var(--bg2);padding:10px;border-radius:6px;border:1px solid var(--border);font-size:10.5px;color:var(--muted);line-height:1.4">No standout candlestick anomalies (e.g. Pocket Pivots, Squats) detected in recent trading sessions. Volume flow is normal.</div>';
  }
  candleSigsHTML += '</div>';'''

fixed_block = r'''  var candleSigsHTML = '<div style="margin-top:12px"><div class="dh">Advanced Price Action Analysis</div>';
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
  candleSigsHTML += '</div>';'''

code = code.replace(bad_block, fixed_block)

with open(r'c:\Claude AI\asx-sepa-vcp-screener\build_dashboard.py', 'w', encoding='utf-8') as f: f.write(code)
print("Fix applied")
