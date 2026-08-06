import json, sys, statistics
sys.stdout.reconfigure(encoding='utf-8')
base = r'D:\robin-skills\trae solo\brand-pulse-vis\products'
r = json.load(open(base + r'\ks-recent.json', encoding='utf-8'))['products']
s = sorted(p['score'] for p in r)
print('n', len(s), 'min', s[0], 'max', s[-1], 'median', statistics.median(s))
print('p10', s[int(len(s)*0.1)], 'p25', s[int(len(s)*0.25)], 'p75', s[int(len(s)*0.75)], 'p90', s[int(len(s)*0.9)])
print('--- top5 ---')
for p in sorted(r, key=lambda x: -x['score'])[:5]:
    print(p['score'], p['brand'], '|', p['title'][:60], '|', p['visBreakdown'])
print('--- bottom3 ---')
for p in sorted(r, key=lambda x: x['score'])[:3]:
    print(p['score'], p['brand'], '|', p['title'][:60], '|', p['visBreakdown'])
print('--- sample charging ---')
for p in r:
    if 'power bank' in p['title'].lower() or 'Power Bank' in p['title']:
        print(p['score'], p['brand'], '|', p['title'][:55], '|', p['visBreakdown'])
