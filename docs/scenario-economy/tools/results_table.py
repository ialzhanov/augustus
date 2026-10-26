import json,sys
B=json.load(open('base.json')); W={r['map']:r for r in json.load(open('worst.json'))}
def nm(m): return m.replace('___The_City_to_',' ').replace('_SAVE',' (save)').replace('_',' ')
print('| Map | Pop / prosp / culture / peace / favor goal | Max house level | Surplus/yr (base) | Tax : exports : imports | Workers used / available | Lowest tax that balances | Surplus with no trade | Worst case | Build-up: lowest treasury | Rule caps and requirements |')
print('|'+'---|'*11)
for r in B:
    g=r['goal']; w=W.get(r['map'],{})
    bu=r.get('buildup') or {}
    blocked=[f"{int(s['share']*100)}%" for s in bu.get('stages',[]) if s['surplus'] is None]
    req='; '.join(r.get('requirements',[]))[:160]
    mons=[x['monument'] for x in (r.get('monuments') or [])]
    if mons: req=(req+'; ' if req else '')+'needs '+', '.join(mons)
    sur=f"{r['surplus']:.0f}" if r['surplus'] is not None else 'none'
    ws=f"{w['surplus']:.0f}" if w.get('surplus') is not None else 'INFEASIBLE '+str(w.get('blockers'))
    print(f"| {nm(r['map'])} | {g['pop']} / {g['prosperity']} / {g['culture']} / {g['peace']} / {g['favor']} | {r['max_level']} | {sur} | {r['tax_income'] or 0:.0f} : {r['export_income'] or 0:.0f} : {r['import_cost'] or 0:.0f} | {r['workers'] or 0:.0f} / {r['workers_available'] or 0:.0f} | {r['min_tax']}% | {'none (trade required)' if r['no_trade'] is None else round(r['no_trade'])} | {ws} | {bu.get('lowest_treasury')} at y{bu.get('lowest_at_year')}{' BLOCKED '+','.join(blocked) if blocked else ''} | {req} |")
