import json

d = json.load(open('data/wc2026_real_results.json', encoding='utf-8'))
matches = d['matches']
gs = [m for m in matches if 'score' in m and m.get('group')]
print(f'Total group-stage matches with scores: {len(gs)}')
print(f'Total matches in file: {len(matches)}')
# Show groups C D E F only
for m in gs:
    g = m.get('group','')
    if any(x in g for x in ['C','D','E','F']):
        sc = m['score']['ft']
        print(f"  {m['date']} {g}: {m['team1']} {sc[0]}-{sc[1]} {m['team2']}")
