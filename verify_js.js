
const D=[{"status": "breakout", "vcpScore": 3, "sepaScore": 6, "price": 10.0, "change": 1.0, "volRatio": 1.5, "pvr": 2.0, "chg5d": 1.0, "chg60d": 5.0, "chg250d": 100.0, "mktcapFmt": "", "sector": "Tech", "ticker": "CBA", "name": "Commbank", "_ticker_raw": "CBA.AX", "stage": 2, "ohlcv": [], "candleSignals": ["Pocket Pivot"], "accDistRatio": 1.8, "checks": {"ma50": true, "ma150": true, "ma200": true, "trend": true, "high": true, "low": true, "vol": true}, "analysis": "Strong breakout pattern.", "fundScore": 2, "ma50": 9.0, "ma150": 8.0, "ma200": 7.0, "pctFromHigh": 5.0, "pctAboveLow": 50.0, "shortSignal": "Long", "revGrowth": 20, "revTrend": "accelerating", "revQuarters": [], "epsGrowth": 25, "netMargin": 15, "trailingEps": 2.5, "forwardEps": 3.0, "nextEarnings": "2026-05-01", "nextEventLabel": "Earnings", "nextExDiv": "2026-06-01"}];
let filt='all', stageFilt=0;
const CUR=String.fromCharCode(36);
const SCOL={1:'#5a7a9a',2:'#00d084',3:'#ff9f43',4:'#ff4757'};
const SLBL={1:'S1 Neglect',2:'S2 Advancing',3:'S3 Topping',4:'S4 Declining'};
const SDESC={
  1:'Consolidation phase. Price sideways around a flat MA200. Institutions ignoring. Avoid buying — wait for Stage 2 breakout.',
  2:'Advancing phase. Price firmly above a rising MA200, MA150>MA200, volume accumulating on up-days. This is the ONLY safe buying stage.',
  3:'Topping / distribution phase. Momentum slowing, smart money distributing to late buyers, volatility increasing. Reduce or exit positions.',
  4:'Declining phase. Full downtrend with lower highs and lower lows, price below a falling MA200. Absolutely avoid buying. Wait for Stage 1 base.'
};

function setF(f,el){
  filt=f;
  document.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('on'));
  el.classList.add('on');
  render();
}

function setStageHero(s,el){
  stageFilt = stageFilt===s ? 0 : s;
  ['tb-s1','tb-s2','tb-s3','tb-s4'].forEach(id=>{
    const b=document.getElementById(id); if(b)b.classList.remove('on');
  });
  if(stageFilt){
    const b=document.getElementById('tb-s'+s); if(b)b.classList.add('on');
  }
  document.getElementById('screener').scrollIntoView({behavior:'smooth'});
  render();
}

function setStageFilter(s,el){
  stageFilt = stageFilt===s ? 0 : s;
  document.querySelectorAll('.fbtn.s1,.fbtn.s2,.fbtn.s3,.fbtn.s4').forEach(b=>b.classList.remove('on'));
  if(stageFilt===s) el.classList.add('on');
  render();
}

function jmp(t){
  document.getElementById('screener').scrollIntoView({behavior:'smooth'});
  document.getElementById('srch').value=t;
  setTimeout(()=>{render();const r=document.querySelector('#tbody tr.main-row');if(r)r.click();},400);
}

function fmtGrowth(v,hi,med){
  hi=hi===undefined?20:hi; med=med===undefined?5:med;
  if(v===null||v===undefined)return '<span style="color:#253550">N/A</span>';
  var col=v>=hi?'#00d084':v>=med?'#ff9f43':v>=0?'#5a7a9a':'#ff4757';
  var arrow=v>0?'↑ ':v<0?'↓ ':'';
  return '<span style="color:'+col+';font-weight:700">'+arrow+(v>=0?'+':'')+v+'%</span>';
}

function revTrendChip(trend){
  if(!trend)return'';
  var map={'accelerating':['trend-chip trend-acc','↑1↑ Accelerating'],'growing':['trend-chip trend-grow','↑ Growing'],'flat':['trend-chip trend-flat','→ Flat'],'declining':['trend-chip trend-dec','↓ Declining']};
  var e=map[trend]||['',''];
  return e[0]?'<div class="'+e[0]+'">'+e[1]+'</div>':'';
}

function revBars(quarters){
  if(!quarters||!Array.isArray(quarters)||!quarters.length)return'<div style="color:#253550;font-size:10px">No quarterly data</div>';
  var vals=quarters.slice(0,5);
  var maxV=1;
  for(var k=0;k<vals.length;k++){if(Math.abs(vals[k][1])>maxV)maxV=Math.abs(vals[k][1]);}
  var out='';
  for(var k=0;k<vals.length;k++){
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
  }
  return '<div class="rev-bars">'+out+'</div>';
}

function drawCandles(ohlcv,ma50v,price){
  if(!ohlcv||!ohlcv.length)return'<div style="color:#253550;font-size:11px;text-align:center;padding:24px 0">No price history available</div>';
  var W=520,H=188,VH=46,PAD={t:6,r:42,b:18,l:46};
  var cW=W-PAD.l-PAD.r,cH=H-PAD.t-PAD.b;
  var n=ohlcv.length;
  var pMin=Infinity,pMax=-Infinity,vMax=1,avgVol=0;
  for(var i=0;i<n;i++){
    if(ohlcv[i][2]<pMin)pMin=ohlcv[i][2];
    if(ohlcv[i][1]>pMax)pMax=ohlcv[i][1];
    if(ohlcv[i][4]>vMax)vMax=ohlcv[i][4];
    avgVol+=ohlcv[i][4];
  }
  pMin*=0.998; pMax*=1.002;
  avgVol/=n;
  var pRange=pMax-pMin;
  var bW=Math.max(1.5,(cW/n)*0.72);
  function px(i){return PAD.l+(i+0.5)*(cW/n);}
  function py(p){return PAD.t+cH-(p-pMin)/pRange*cH;}
  var s='<svg viewBox="0 0 '+W+' '+(H+VH+6)+'" xmlns="http://www.w3.org/2000/svg" style="display:block;width:100%">';
  s+='<defs><linearGradient id="gU" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#00d084" stop-opacity="0.9"/><stop offset="100%" stop-color="#00d084" stop-opacity="0.3"/></linearGradient>';
  s+='<linearGradient id="gD" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#ff4757" stop-opacity="0.9"/><stop offset="100%" stop-color="#ff4757" stop-opacity="0.3"/></linearGradient></defs>';
  s+='<rect x="'+PAD.l+'" y="'+PAD.t+'" width="'+cW+'" height="'+cH+'" fill="#050810" rx="3"/>';
  for(var g=1;g<=3;g++){
    var gy=PAD.t+cH*g/4;
    var gp=pMax-pRange*g/4;
    s+='<line x1="'+PAD.l+'" y1="'+gy+'" x2="'+(PAD.l+cW)+'" y2="'+gy+'" stroke="#1a2540" stroke-width="0.5"/>';
    s+='<text x="'+(PAD.l-3)+'" y="'+(gy+3)+'" text-anchor="end" fill="#3d5a78" font-size="8" font-family="monospace">'+gp.toFixed(2)+'</text>';
  }
  s+='<text x="'+(PAD.l-3)+'" y="'+(PAD.t+5)+'" text-anchor="end" fill="#3d5a78" font-size="8" font-family="monospace">'+pMax.toFixed(2)+'</text>';
  s+='<text x="'+(PAD.l-3)+'" y="'+(PAD.t+cH)+'" text-anchor="end" fill="#3d5a78" font-size="8" font-family="monospace">'+pMin.toFixed(2)+'</text>';
  if(ma50v>=pMin&&ma50v<=pMax){
    var my=py(ma50v);
    s+='<line x1="'+PAD.l+'" y1="'+my+'" x2="'+(PAD.l+cW)+'" y2="'+my+'" stroke="#ff9f43" stroke-width="1" stroke-dasharray="3,2" opacity="0.75"/>';
    s+='<text x="'+(PAD.l+cW+2)+'" y="'+(my+3)+'" fill="#ff9f43" font-size="7">MA50</text>';
  }
  for(var i=0;i<n;i++){
    var op=ohlcv[i][0],hi=ohlcv[i][1],lo=ohlcv[i][2],cl=ohlcv[i][3];
    var up=cl>=op;
    var col=up?'#00d084':'#ff4757';
    var x=px(i);
    var bTop=py(Math.max(op,cl));
    var bBot=py(Math.min(op,cl));
    var bH=Math.max(1,bBot-bTop);
    s+='<line x1="'+x+'" y1="'+py(hi)+'" x2="'+x+'" y2="'+py(lo)+'" stroke="'+col+'" stroke-width="0.8" opacity="0.45"/>';
    s+='<rect x="'+(x-bW/2)+'" y="'+bTop+'" width="'+bW+'" height="'+bH+'" fill="'+col+'" opacity="'+(up?'0.82':'0.92')+'"/>';
  }
  var cpy=py(price);
  if(cpy>=PAD.t&&cpy<=PAD.t+cH){
    s+='<line x1="'+PAD.l+'" y1="'+cpy+'" x2="'+(PAD.l+cW)+'" y2="'+cpy+'" stroke="#e8f0fe" stroke-width="0.6" stroke-dasharray="4,3" opacity="0.3"/>';
    s+='<text x="'+(PAD.l+cW+2)+'" y="'+(cpy+3)+'" fill="#5a7a9a" font-size="7">'+price+'</text>';
  }
  var li=[0,Math.floor(n/2),n-1];
  for(var k=0;k<li.length;k++){
    var daysAgo=n-1-li[k];
    s+='<text x="'+px(li[k])+'" y="'+(PAD.t+cH+14)+'" text-anchor="middle" fill="#2a3d55" font-size="7">'+(daysAgo===0?'today':daysAgo+'d ago')+'</text>';
  }
  var vTop=H+2;
  s+='<rect x="'+PAD.l+'" y="'+vTop+'" width="'+cW+'" height="'+VH+'" fill="#040710" rx="3"/>';
  s+='<text x="'+(PAD.l-3)+'" y="'+(vTop+9)+'" text-anchor="end" fill="#2a3d55" font-size="7">Vol</text>';
  for(var i=0;i<n;i++){
    var op=ohlcv[i][0],cl=ohlcv[i][3],vol=ohlcv[i][4];
    var up=cl>=op;
    var x=px(i);
    var vH2=Math.max(1,(vol/vMax)*(VH-4));
    var isHigh=vol>avgVol*1.4;
    s+='<rect x="'+(x-bW/2)+'" y="'+(vTop+VH-2-vH2)+'" width="'+bW+'" height="'+vH2+'" fill="'+(up?'url(#gU)':'url(#gD)')+'" opacity="'+(isHigh?'1':'0.5')+'"/>';
  }
  var avgH=(avgVol/vMax)*(VH-4);
  s+='<line x1="'+PAD.l+'" y1="'+(vTop+VH-2-avgH)+'" x2="'+(PAD.l+cW)+'" y2="'+(vTop+VH-2-avgH)+'" stroke="#ff9f43" stroke-width="0.5" stroke-dasharray="2,2" opacity="0.4"/>';
  s+='<text x="'+(PAD.l+cW/2)+'" y="'+(vTop+VH)+'" text-anchor="middle" fill="#1e2d45" font-size="7">VOLUME — bright bars = above-average (buying pressure)</text>';
  s+='</svg>';
  return s;
}

function render(){
  var srt=document.getElementById('srt').value,
      q=document.getElementById('srch').value.toLowerCase(),
      sec=document.getElementById('sec').value;
  var d=D.filter(function(r){
    if(filt!=='all'&&r.status!==filt)return false;
    if(stageFilt&&r.stage!==stageFilt)return false;
    if(sec&&r.sector!==sec)return false;
    if(q&&!r.ticker.toLowerCase().includes(q)&&!r.name.toLowerCase().includes(q))return false;
    return true;
  });
  d.sort(function(a,b){
    if(srt==='sepa') return(b.sepaScore*10+b.vcpScore)-(a.sepaScore*10+a.vcpScore);
    if(srt==='vcp')  return b.vcpScore-a.vcpScore;
    if(srt==='vol')  return b.volRatio-a.volRatio;
    if(srt==='pvr')  return b.pvr-a.pvr;
    if(srt==='fund') return(b.fundScore||0)-(a.fundScore||0);
    if(srt==='p250') return b.chg250d-a.chg250d;
    if(srt==='mc')   return b.mktcap-a.mktcap;
    if(srt==='stage')return(a.stage||1)-(b.stage||1);
    return 0;
  });
  document.getElementById('cnt').textContent=d.length+' shown';
  if(!d.length){document.getElementById('tbody').innerHTML='<tr><td colspan="16"><div class="empty">No stocks match these filters</div></td></tr>';return;}
  document.getElementById('tbody').innerHTML=d.map(function(r,i){return row(r,i);}).join('');
}

function row(r,i){
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
  if(r.revGrowth!==null&&r.revGrowth!==undefined){
    var tIco={'accelerating':'↑1↑','growing':'↑','flat':'→','declining':'↓'};
    var tCol={'accelerating':'#00d084','growing':'#8bc34a','flat':'#ff9f43','declining':'#ff4757'};
    var icon=tIco[r.revTrend]||'';
    var col2=tCol[r.revTrend]||(r.revGrowth>=0?'#5a7a9a':'#ff4757');
    revCell='<span style="color:'+col2+';font-weight:700;font-size:11px">'+icon+' '+(r.revGrowth>=0?'+':'')+r.revGrowth+'%</span>';
  }
  var evCell='<span style="color:#253550;font-size:10px">&mdash;</span>';
  if(r.nextEventLabel){
    var hot=r.nextEventLabel.includes('⚡');
    evCell='<span style="color:'+(hot?'var(--gold)':'var(--blue)')+';font-size:10px;font-weight:700">'+r.nextEventLabel+'</span>';
  }
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
}

function det(r){
  var c=r.checks;
  var stg=r.stage||1;
  var sc2=SCOL[stg];
  var crows=[[c.ma50,CUR+r.price+' > MA50 ('+CUR+(r.ma50?r.ma50.toFixed(2):'0')+')'],[c.ma150,'MA50 > MA150 ('+CUR+(r.ma150?r.ma150.toFixed(2):'0')+')'],[c.ma200,'MA150 > MA200 ('+CUR+(r.ma200?r.ma200.toFixed(2):'0')+')'],[c.trend,'200-day MA trending up (12M: '+(r.chg250d>=0?'+':'')+r.chg250d+'%)'],[c.high,'Within 25% of 52W high ('+r.pctFromHigh+'% below)'],[c.low,'25%+ above 52W low ('+r.pctAboveLow+'% above)'],[c.vol,'Volume breakout >=1.5x ('+r.volRatio+'x), PVR '+r.pvr]].map(function(p){return '<div class="cr '+(p[0]?'ok':'no')+'"><span class="ci">'+(p[0]?'\u2713':'\u2717')+'</span>'+p[1]+'</div>';}).join('');
  
  var vd=['No contraction','Weak (1/4)','Moderate (2/4)','Good (3/4) \u2014 VCP forming','Ideal (4/4) \u2014 textbook base'][r.vcpScore];
  var ac=r.status==='breakout'?'abuy':r.status==='near-pivot'?'awch':'ahld';
  var at=r.status==='breakout'?'\u2192 BUY ZONE: Consider entry. Stop-loss below MA50. Risk 1-2%.':r.status==='near-pivot'?'\u2192 WATCHLIST: Alert at pivot high. Enter on breakout with vol >1.5x.':'\u2192 MONITOR: Wait for VCP to tighten and volume to dry up.';
  var rg=r.revGrowth,eg=r.epsGrowth,nm=r.netMargin,te=r.trailingEps,fe=r.forwardEps,fs=r.fundScore||0;
  var fp2='';for(var j=0;j<3;j++)fp2+='<div class="fpip" style="display:inline-block;width:9px;height:9px;border-radius:2px;background:'+(j<fs?'#ff9f43':'#1a2540')+';border:1px solid '+(j<fs?'#ff9f43':'#1e2d45')+'"></div>&nbsp;';
  var epsRows='';
  if(te!==null&&te!==undefined){var ec=te>0?'#00d084':'#ff4757';epsRows+='<div class="pi"><span class="pk">Trail EPS</span><span class="pv2" style="color:'+ec+'">'+te+'</span></div>';}
  if(fe!==null&&fe!==undefined){var ec=fe>0?'#00d084':'#ff4757';epsRows+='<div class="pi"><span class="pk">Fwd EPS</span><span class="pv2" style="color:'+ec+'">'+fe+'</span></div>';}
  var nmRow='';
  if(nm!==null&&nm!==undefined){var mc=nm>=15?'#00d084':nm>0?'#ff9f43':'#ff4757';nmRow='<div class="pi"><span class="pk">Net Margin</span><span class="pv2" style="color:'+mc+'">'+nm+'%</span></div>';}
  
  var fundCol='<div style="min-width:0">'+
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
  if(r.nextEventLabel){
    var hot=r.nextEventLabel.includes('\u26a1');
    evLines.push('<div class="'+(hot?'ev-hot':'ev-soon')+'">'+r.nextEventLabel+'</div>');
    if(r.nextEarnings)evLines.push('<div style="font-size:10px;color:#253550;margin-top:3px">\u1F4C6 '+r.nextEarnings+'</div>');
  }
  if(r.nextExDiv)evLines.push('<div class="ev-div">\u1F4B0 Ex-Div: '+r.nextExDiv+'</div>');
  if(evLines.length)evHtml=evLines.join('');
  
  var entry=r.price,stop=r.ma50||(r.price*0.93),risk=entry-stop;
  var target=risk>0?(entry+2*risk).toFixed(2):null;
  var tlBox='<div class="tl-box" style="padding:10px 8px;margin-bottom:8px">'+
    '<div class="tl-title" style="font-size:9px;margin-bottom:6px">\u26A1 TRADE LEVELS</div>'+
    '<div style="display:flex;flex-direction:column;gap:5px">'+
    '<div style="background:#081a0f;border:1px solid rgba(0,208,132,.25);border-radius:4px;padding:4px;text-align:center"><div style="font-size:7px;color:#5a7a9a;margin-bottom:2px">BUY ABOVE</div><div style="font-size:11px;font-weight:700;color:#00d084">'+CUR+entry.toFixed(2)+'</div></div>'+
    '<div style="background:#1a0809;border:1px solid rgba(255,71,87,.25);border-radius:4px;padding:4px;text-align:center"><div style="font-size:7px;color:#5a7a9a;margin-bottom:2px">STOP LOSS</div><div style="font-size:11px;font-weight:700;color:#ff4757">'+CUR+stop.toFixed(2)+'</div></div>'+
    (target?'<div style="background:#08101a;border:1px solid rgba(59,130,246,.25);border-radius:4px;padding:4px;text-align:center;margin-top:2px"><div style="font-size:7px;color:#5a7a9a;margin-bottom:2px">TARGET (2R)</div><div style="font-size:11px;font-weight:700;color:#3b82f6">'+CUR+target+'</div></div>':'')+
    '</div></div>';

  var vcpPointers = ['Base is loose or trending down. Wait for a constructive base to form.', 'Early signs of contraction. Still too loose to buy.', 'Base is forming. Watch for tightening spreads on the right side.', 'Good VCP forming. Volume is drying up. Stalk entry near pivot high.', 'Textbook VCP. Extreme volatility contraction. Prime entry setup on volume breakout.'][r.vcpScore];

  var vcpAnalysisHtml = '<div style="margin-top:12px">'+
    '<div class="dh">VCP Base Progression ('+r.vcpScore+'/4)</div>'+
    '<div class="abox" style="padding:12px;font-size:11px;border-left-color:var(--blue);line-height:1.6;background:var(--bg3);border:1px solid var(--border);border-left:3px solid var(--blue)">'+
    '<strong style="color:#fff;font-size:12px;letter-spacing:0.3px">'+vd+'</strong><br/>'+
    '<span style="color:#8bb4e6;display:inline-block;margin-top:4px">'+vcpPointers+'</span>'+
    '</div></div>';

  var candleSigsHTML = '<div style="margin-top:12px"><div class="dh">Advanced Price Action Analysis</div>';
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
  candleSigsHTML += '</div>';

  var vcpCol='<div>'+
    '<div class="dh">Upcoming Event Catalyst</div>'+
    evHtml+
    vcpAnalysisHtml+
    candleSigsHTML+
    '</div>';

  var tradeCol='<div>'+
    tlBox+
    '<div class="abox" style="margin-top:6px;padding:10px;line-height:1.6">'+
    '<div style="font-weight:800;font-size:9px;color:var(--text);margin-bottom:6px;letter-spacing:0.5px">SUMMARY</div>'+(r.analysis || 'Awaiting deeper technical analysis.')+
    '<div class="aact '+ac+'" style="margin-top:8px">'+at+'</div></div>'+
    '</div>';

  var stageBox='<div class="stage-info-box" style="color:'+sc2+';background:'+sc2+'0d;border-color:'+sc2+'33">'+
    '<strong>'+SLBL[stg]+'</strong> \u2014 '+SDESC[stg]+
    '</div>';

  var adr = (r.accDistRatio !== undefined) ? r.accDistRatio : 1.0;
  var adrCol = adr >= 1.5 ? '#00d084' : adr >= 1.0 ? '#8bc34a' : '#ff4757';
  var adrTxt = adr >= 1.5 ? 'Strong Accumulation (Inst. Buying)' : adr >= 1.0 ? 'Mild Accumulation' : 'Distribution (Selling Pressure)';
  
  var smartMoneyHtml = '<div style="margin-top:12px">'+
    '<div class="dh">Smart Money Indicators</div>'+
    '<div class="abox" style="padding:9px;font-size:10px;border-left-color:'+adrCol+';line-height:1.5">'+
    '<strong style="color:var(--text)">60-Day Acc/Dist Ratio: <span style="color:'+adrCol+'">'+adr.toFixed(2)+'x</span></strong><br/>'+
    '<span style="color:#5a7a9a;display:inline-block;margin-top:2px">'+adrTxt+'</span><br/>'+
    '<div style="display:flex;justify-content:space-between;margin-top:6px;padding-top:6px;border-top:1px solid rgba(30,45,69,.5)"><span style="color:#5a7a9a">Price/Vol Ratio (PVR):</span><strong style="color:'+(r.pvr>1.2?'#00d084':r.pvr>0.8?'#ff9f43':'#ff4757')+'">'+(r.pvr||0)+'</strong></div>'+
    '<div style="display:flex;justify-content:space-between;margin-top:4px"><span style="color:#5a7a9a">Today Vol vs 50d Avg:</span><strong style="color:'+(r.volRatio>=1.5?'#00d084':r.volRatio>=1?'#ff9f43':'#ff4757')+'">'+(r.volRatio||0).toFixed(1)+'x</strong></div>'+
    '</div></div>';

  var stratNotesHtml = '<div style="height:100%"><div class="dh">Strategy Nuances & Pro Tips</div>'+
    '<div style="display:flex;flex-direction:column;gap:8px">'+
    '<div class="abox" style="padding:8px;font-size:10.5px;border-left-color:var(--gold)">'+
    '<strong style="color:var(--gold);font-size:9px">PRO TIP: THE CHEAT</strong><br/>Consolidation halfway up a base. Low-risk early entry point below the primary pivot.</div>'+
    '<div class="abox" style="padding:8px;font-size:10.5px;border-left-color:var(--green)">'+
    '<strong style="color:var(--green);font-size:9px">PRO TIP: TENNIS BALL</strong><br/>High-RS stocks bounce first when market dips. Look for speed of recovery.</div>'+
    '<div class="abox" style="padding:8px;font-size:10.5px;border-left-color:var(--blue)">'+
    '<strong style="color:var(--blue);font-size:9px">PRO TIP: VDU</strong><br/>Volume dry-up reveals supply exhaustion. The best buy points are often silent.</div>'+
    '<div class="abox" style="padding:8px;font-size:10.5px;border-left-color:var(--muted)">'+
    '<strong style="color:var(--muted);font-size:9px">RULE: THE SEVEN PERCENT</strong><br/>Never let a loss exceed 7-8%. Survival is the first stage of success.</div>'+
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
    '<div class="dh">60-Day Candlestick + Volume (orange dash = MA50)</div>'+
    drawCandles(r.ohlcv,r.ma50,r.price)+
    '</div>';
    
  return '<div class="dpanel">'+chartCol+sepaCol+fundCol+vcpCol+tradeCol+stratNotesHtml+'</div>';
}

function tog(i){
  var el=document.getElementById('d'+i);
  var mr=document.getElementById('mr'+i);
  var showing=el.style.display!=='none';
  el.style.display=showing?'none':'table-row';
  if(mr)mr.classList.toggle('expanded',!showing);
}
render();
