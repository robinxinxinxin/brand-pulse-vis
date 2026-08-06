# -*- coding: utf-8 -*-
import json, sys, datetime, collections
sys.stdout.reconfigure(encoding='utf-8')

base = r'D:\robin-skills\trae solo\brand-pulse-vis\products'
cand = json.load(open(base + r'\ks-candidates.json', encoding='utf-8'))
recent = json.load(open(base + r'\ks-recent.json', encoding='utf-8'))
cands = cand['candidates']
olds = {p['id']: p for p in recent['products']}

# category style detection (keep file convention)
styles = collections.Counter('slash' if '/' in p.get('category', '') else 'underscore'
                             for p in recent['products'])
use_slash = styles['slash'] >= styles['underscore']
print('category style ->', 'slash' if use_slash else 'underscore', dict(styles))

# index -> (rec, para, cmf, trans, diff) for the 81 new candidates (order = _tmp_list_new.py output)
S = {
 0:(6.0,6.0,5.0,5.0,5.5),   1:(6.5,5.0,5.0,5.0,5.5),   2:(7.0,6.5,5.0,5.5,6.0),
 3:(7.0,6.0,5.5,6.5,7.0),   4:(6.0,5.5,5.0,5.0,5.5),   5:(5.5,5.5,6.5,6.0,6.5),
 6:(6.5,6.0,5.0,6.0,6.0),   7:(8.0,8.0,6.5,6.0,6.5),   8:(7.5,5.5,8.0,7.0,7.0),
 9:(5.0,5.0,5.0,5.0,5.2),  10:(6.0,6.0,5.0,5.0,5.5),  11:(6.0,5.5,5.0,5.5,5.8),
 12:(7.5,7.0,6.0,6.0,6.5), 13:(5.0,5.0,5.0,5.0,5.2), 14:(7.5,5.5,7.5,7.0,7.0),
 15:(6.5,6.5,5.0,5.0,5.5), 16:(6.5,5.5,6.0,6.5,6.5), 17:(5.5,5.0,5.0,5.5,5.5),
 18:(8.0,5.5,8.0,7.5,7.0), 19:(6.5,7.0,5.0,6.0,6.0), 20:(6.0,5.5,5.0,5.5,6.0),
 21:(5.0,5.0,5.0,5.0,5.2), 22:(5.5,6.0,5.0,6.0,5.8), 23:(5.0,5.0,5.0,5.0,5.2),
 24:(5.0,5.0,5.0,5.0,5.5), 25:(5.5,5.0,5.0,5.0,5.2), 26:(6.5,7.0,5.0,5.5,5.5),
 27:(5.5,5.0,5.0,5.5,5.5), 28:(5.5,5.0,5.0,5.0,5.2), 29:(5.0,5.5,5.0,5.0,5.5),
 30:(7.0,5.5,6.0,6.5,6.5), 31:(7.0,7.0,6.0,6.5,6.5), 32:(5.5,5.0,5.0,5.0,5.5),
 33:(6.5,5.5,6.0,5.5,5.5), 34:(5.5,5.5,5.0,5.0,5.2), 35:(6.5,8.0,8.5,8.0,7.5),
 36:(6.5,7.5,5.0,6.0,6.0), 37:(7.0,7.0,5.0,6.5,6.5), 38:(5.0,5.0,5.0,5.0,5.2),
 39:(5.5,5.5,5.0,5.0,5.2), 40:(5.0,5.0,5.0,5.0,5.2), 41:(8.0,7.5,6.0,6.5,6.5),
 42:(5.0,5.0,5.0,5.0,5.2), 43:(5.5,6.0,6.5,6.5,7.0), 44:(5.5,5.0,5.0,5.0,5.2),
 45:(7.5,7.5,6.0,8.0,7.0), 46:(5.0,5.0,5.0,5.0,5.2), 47:(7.0,6.5,6.5,6.5,6.5),
 48:(5.0,5.0,5.0,5.0,5.2), 49:(6.5,7.0,5.5,6.0,6.0), 50:(6.0,6.0,5.0,5.5,5.8),
 51:(5.5,5.5,5.5,5.0,5.5), 52:(6.5,5.5,5.5,5.5,5.5), 53:(5.0,5.0,5.0,5.0,5.0),
 54:(6.5,6.5,5.5,6.5,6.0), 55:(5.5,5.0,5.0,5.0,5.5), 56:(5.5,5.5,5.0,5.5,5.5),
 57:(5.0,5.0,5.0,5.0,5.2), 58:(6.5,8.0,5.0,6.5,6.5), 59:(6.5,7.0,5.5,6.0,6.5),
 60:(7.5,7.0,7.5,6.5,6.5), 61:(5.5,5.5,5.5,5.5,5.5), 62:(7.5,7.5,6.0,7.0,7.0),
 63:(5.0,5.0,5.0,5.0,5.2), 64:(6.0,5.5,5.0,5.0,5.5), 65:(8.5,7.0,8.0,8.0,7.0),
 66:(6.0,5.5,5.5,5.0,5.2), 67:(8.5,7.5,5.5,6.5,6.5), 68:(8.0,7.0,7.5,7.5,6.0),
 69:(6.0,5.0,5.0,5.5,5.0), 70:(5.5,5.0,5.5,5.0,5.0), 71:(7.5,7.0,5.5,7.0,6.5),
 72:(7.5,7.5,5.5,6.0,6.5), 73:(5.0,5.0,5.0,5.0,5.2), 74:(5.5,5.0,5.0,5.0,5.5),
 75:(9.0,7.0,8.0,7.0,6.5), 76:(6.5,6.5,5.5,6.5,6.0), 77:(7.0,7.0,5.5,6.0,6.0),
 78:(8.0,7.5,6.5,6.5,6.5), 79:(6.5,6.0,5.0,5.5,5.8), 80:(7.5,5.5,7.5,7.5,7.0),
}

def calc(v):
    r, p, c, t, d = v
    return round((r*0.30 + p*0.25 + c*0.20 + t*0.15 + d*0.10) * 10, 1)

def mk_reason(k):
    bits = []
    if k.get('backersCount'):
        bits.append('%d人支持' % k['backersCount'])
    if k.get('percentFunded'):
        bits.append('达成%dx' % round(k['percentFunded'] / 100))
    if k.get('state'):
        bits.append(str(k['state']))
    return ' · '.join(bits)

new_items = [x for x in cands if x['id'] not in olds]
assert len(new_items) == len(S), (len(new_items), len(S))

out = []
for i, x in enumerate(new_items):
    v = S[i]
    k = x.get('ksData', {}) or {}
    cat = x.get('category', '')
    if use_slash:
        cat = cat.replace('_', '/', 1) if '_' in cat else cat
        if x.get('tags'):
            cat = x['tags'][0]
    item = {
        'id': x['id'], 'brand': x.get('brand'), 'category': cat,
        'title': x.get('title'), 'desc': x.get('desc'), 'time': x.get('time'),
        'score': calc(v),
        'visBreakdown': {'recognition': v[0], 'paradigmShift': v[1], 'cmfInnovation': v[2],
                         'transferability': v[3], 'diffusionPotential': v[4]},
        'source': 'kickstarter', 'sourceName': 'Kickstarter',
        'url': x.get('url'), 'tags': x.get('tags', []), 'image': x.get('image'),
        'reason': mk_reason(k), 'ksData': k,
        'personalRelevanceTier': x.get('personalRelevanceTier'),
        'personalRelevanceReason': x.get('personalRelevanceReason'),
    }
    out.append(item)

# keep previously scored items that are still in the candidate pool, plus all new
cand_ids = {x['id'] for x in cands}
kept = [olds[i] for i in olds if i in cand_ids]
dropped = [p for p in recent['products'] if p['id'] not in cand_ids]
merged = kept + dropped + out
merged.sort(key=lambda p: (-p['score'], p.get('time') or ''))
merged = merged[:200]

today = datetime.date.today().isoformat()
json.dump({'lastUpdated': today, 'products': merged},
          open(base + r'\ks-recent.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)

print('new scored: %d | kept-from-pool: %d | carried: %d | final: %d' %
      (len(out), len(kept), len(dropped), len(merged)))
print('new items entering top200: %d' % sum(1 for p in merged if p['id'] in {o['id'] for o in out}))
print('--- top 12 ---')
for p in merged[:12]:
    print(p['score'], '|', p['brand'], '|', p['title'][:58])
