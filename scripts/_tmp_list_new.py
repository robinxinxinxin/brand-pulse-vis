import json, sys
sys.stdout.reconfigure(encoding='utf-8')
base = r'D:\robin-skills\trae solo\brand-pulse-vis\products'
c = json.load(open(base + r'\ks-candidates.json', encoding='utf-8'))['candidates']
r = json.load(open(base + r'\ks-recent.json', encoding='utf-8'))['products']
old = {p['id'] for p in r}
new = [x for x in c if x['id'] not in old]
for i, x in enumerate(new):
    k = x.get('ksData', {}) or {}
    parts = [
        str(i), x['id'], str(x.get('brand')), str(x.get('category')),
        str(x.get('title')), (x.get('desc') or '')[:120],
        'bk=%s' % k.get('backersCount'),
        'pct=%s' % round(k.get('percentFunded') or 0),
        str(k.get('state')),
    ]
    print('|'.join(parts))
