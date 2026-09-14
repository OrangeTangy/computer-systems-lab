"""Dependency-free SVG scientific plots with explicit min/max whiskers."""
import math,html,pathlib
def plot(path,title,xlabel,ylabel,series,logx=False,notes='',vlines=(),subtitle='Measured Windows results | medians; whiskers = trial min-max, not confidence intervals'):
 # Series: (label, [(x,median,min,max), ...]); order is preserved for parametric curves.
 allp=[p for _,ps in series for p in ps];tx=lambda x:math.log2(x) if logx else x
 lo=min(tx(p[0]) for p in allp);hi=max(tx(p[0]) for p in allp);hi=hi if hi>lo else lo+1
 ymax=max(p[3] for p in allp)*1.12 or 1
 X=lambda x:90+690*(tx(x)-lo)/(hi-lo);Y=lambda y:440-330*y/ymax
 parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1040" height="570">','<rect width="1040" height="570" fill="#fff"/>','<g font-family="Arial,sans-serif" fill="#172033">',f'<text x="40" y="35" font-size="23">{html.escape(title)}</text>',f'<text x="40" y="65" font-size="13">{html.escape(subtitle)}</text>',f'<text x="90" y="95" font-size="13">{html.escape(ylabel)}</text>']
 for i in range(6):
  y=i*ymax/5;parts += [f'<path d="M90 {Y(y)} H780" stroke="#e2e8f0"/>',f'<text x="78" y="{Y(y)+4}" text-anchor="end" font-size="12">{y:.3g}</text>']
 ticks=sorted(set(p[0] for p in allp))
 if not logx:ticks=[lo+(hi-lo)*i/5 for i in range(6)]
 elif len(ticks)>9:ticks=[ticks[round(i*(len(ticks)-1)/7)] for i in range(8)]
 for x in ticks:parts.append(f'<text x="{X(x)}" y="463" font-size="12" text-anchor="middle">{x:.3g}</text>')
 for x,label in vlines:
  if lo<=tx(x)<=hi:parts.extend([f'<path d="M{X(x)} 110 V440" stroke="#64748b" stroke-dasharray="4 4"/>',f'<text x="{X(x)+4}" y="126" font-size="11">{html.escape(label)}</text>'])
 colors=['#2563eb','#dc2626','#059669','#9333ea','#ea580c','#0891b2']
 for j,(label,ps) in enumerate(series):
  color=colors[j%len(colors)];points=' '.join(f'{X(p[0])},{Y(p[1])}' for p in ps)
  parts.append(f'<polyline points="{points}" stroke="{color}" fill="none" stroke-width="2"/>')
  for x,mn,l,h in ps:parts.extend([f'<path d="M{X(x)} {Y(l)} V{Y(h)} M{X(x)-3} {Y(l)} H{X(x)+3} M{X(x)-3} {Y(h)} H{X(x)+3}" stroke="{color}"/>',f'<circle cx="{X(x)}" cy="{Y(mn)}" r="3" fill="{color}"/>'])
  parts.append(f'<text x="800" y="{115+j*23}" font-size="12" fill="{color}">{html.escape(label)}</text>')
 parts.extend([f'<text x="435" y="500" text-anchor="middle" font-size="14">{html.escape(xlabel)}</text>',f'<text x="40" y="540" font-size="12">{html.escape(notes)}</text>','</g></svg>'])
 path=pathlib.Path(path);path.parent.mkdir(exist_ok=True,parents=True);path.write_text('\n'.join(parts))
