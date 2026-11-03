"""Numerical checks only; no model, network, or automatic semantic grading."""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
def read(name): return json.loads((ROOT / 'data' / name).read_text('utf-8'))

def calculate():
    rows=read('ratings.json'); grouped=defaultdict(list)
    assert len(rows)==293
    for r in rows:
        assert r['correctness'] in (0,1,2) and r['support'] in (0,1,2)
        if 'endpoint' in r:
            passed=r['correctness']==r['support']==2
            if r['endpoint']!='historical_joint': passed=passed and r['core_label_original']=='是'
            assert passed==r['passed'], (r['cohort'],r['question'],r['arm'])
        grouped[r['cohort'],r['arm'],r.get('cap'),r.get('repeat')].append(r)
    summaries=[]
    for (cohort,arm,cap,repeat),rs in sorted(grouped.items()):
        s=dict(cohort=cohort,arm=arm,cap=cap,repeat=repeat,logical_positions=len(rs),
               correctness_2=sum(r['correctness']==2 for r in rs),support_2_as_recorded=sum(r['support']==2 for r in rs))
        if 'passed' in rs[0]: s['passes']=sum(r['passed'] for r in rs)
        if 'delivery' in rs[0]: s['delivery_complete']=sum(r['delivery'] for r in rs)
        if rs[0]['core_semantics']=='completion': s['core_complete']=sum(r['core_label_original']=='是' for r in rs)
        if 'input_tokens_api' in rs[0]: s['mean_input_tokens_api']=sum(r['input_tokens_api'] for r in rs)/len(rs)
        summaries.append(s)
    expected_initial={('acs_initial18','bm25'):(18,18),('acs_initial18','dense'):(17,18),('acs_initial18','hybrid'):(17,18),
        ('atv_initial12','bm25'):(9,9),('atv_initial12','dense'):(7,8),('atv_initial12','hybrid'):(9,10)}
    for s in summaries:
        k=s['cohort'],s['arm']
        if k in expected_initial: assert (s['correctness_2'],s['support_2_as_recorded'])==expected_initial[k],s
    assert sum(r['passed'] for r in rows if r['cohort']=='v20_pilot')==35
    assert {(s['arm'],s['repeat']):s['passes'] for s in summaries if s['cohort']=='v20_pilot'}=={('B1',1):5,('B1',2):6,('B1A',1):6,('B1A',2):6,('B2',1):6,('B2',2):6}
    assert sum(r['passed'] for r in rows if r['cohort']=='v20_diagnostic')==12
    assert {(s['arm'],s['cap']):s['passes'] for s in summaries if s['cohort']=='v90_final'}=={('B1',4000):4,('B2',4000):5,('B1',12000):6,('B2',12000):5}
    assert {s['arm']:s['passes'] for s in summaries if s['cohort']=='v20_original24'}=={'baseline':20,'structure':20}
    for cohort,expected in [('v20_crosspage3',{'original':2,'crosspage':3}),('v20_risk8',{'original':7,'crosspage':8}),('v20_new3',{'original':2,'crosspage':3})]:
        assert {s['arm']:s['passes'] for s in summaries if s['cohort']==cohort}==expected
    ds=read('v20_delivery.json'); refs=read('listed_packages.json'); groups=defaultdict(list)
    assert len(ds)==675
    keyed={(r['question'],r['arm'],r['cap']):r for r in ds}; assert len(keyed)==675
    for r in ds:
        q=refs[r['question']]; ids=set(r['selected_unit_ids'])
        assert len(ids)==len(r['selected_unit_ids'])
        complete=all(u in ids for u in q['parent_unit_ids']) if 'parent_unit_ids' in q else all(any(set(a)<=ids for a in f['alternatives']) for f in q['facts'])
        assert complete==r['complete']
        assert r['input_tokens_estimated']<=r['cap']
        base=set(keyed[r['question'],'B0',r['cap']]['selected_unit_ids'])
        assert r['added_count']==len(ids-base) and r['lost_count']==len(base-ids)
        groups[r['cohort'],r['cap'],r['arm']].append(r)
    grid=[]
    for (cohort,cap,arm),rs in sorted(groups.items()):
        grid.append(dict(cohort=cohort,cap=cap,arm=arm,n=len(rs),complete=sum(r['complete'] for r in rs),
            missing_questions=[r['question'] for r in rs if not r['complete']],empty=sum(not r['selected_unit_ids'] for r in rs),
            mean_local_tokens=sum(r['input_tokens_estimated'] for r in rs)/len(rs),
            added_occurrences=sum(r['added_count'] for r in rs),lost_occurrences=sum(r['lost_count'] for r in rs)))
    arms=['B0','B1','B1A','BT','B2']
    expected={4000:[18,15,14,17,19],8000:[20,20,19,19,20],12000:[21,23,23,20,21],16000:[22,23,23,21,23],20000:[23,23,23,23,24]}
    for cap,counts in expected.items():
        assert [next(x['complete'] for x in grid if (x['cohort'],x['cap'],x['arm'])==('Q24',cap,a)) for a in arms]==counts
    assert {x['arm']:x['missing_questions'] for x in grid if x['cohort']=='Q24' and x['cap']==20000}=={
        'B0':['V20-Q24'],'B1':['V20-Q04'],'B1A':['V20-Q04'],'BT':['V20-Q04'],'B2':[]}
    q04_added=set(keyed['V20-Q04','B0',20000]['selected_unit_ids'])-set(keyed['V20-Q04','B0',16000]['selected_unit_ids'])
    assert {'V20-018-p359-U001','V20-018-p111-U002'}<=q04_added
    pairs=read('original24_pair_identity.json'); subsets=[]
    for same in (True,False):
        rs=[r for r in pairs if r['identical_request']==same]
        subsets.append(dict(identical_request=same,n=len(rs),baseline_pass=sum(r['baseline_pass'] for r in rs),
            structure_pass=sum(r['structure_pass'] for r in rs),discordant=sum(r['baseline_pass']!=r['structure_pass'] for r in rs)))
    assert [(r['n'],r['baseline_pass'],r['structure_pass'],r['discordant']) for r in subsets]==[(8,6,6,0),(16,14,14,2)]
    flagged=[r for r in rows if r.get('support_application_flag')]
    assert len(flagged)==4 and all(not r['passed'] for r in flagged)
    # These are supplied, dated human corrections, not machine-assigned grades.
    assert all(r['support']==1 and r['support_revision']['original_support']==2 and r['support_revision']['final_review_date']=='2026-10-21' for r in flagged)
    assert sum(r['support']==2 for r in rows if r['cohort']=='v20_diagnostic')==14
    # Correctness/completion already failed, so both joint endpoints stay unchanged.
    assert all(not (r['core_label_original']=='是' and r['correctness']==2 and s==2) for r in flagged for s in (0,1,2))
    pilot_usage={a:round(sum(r['input_tokens_api'] for r in rows if r['cohort']=='v20_pilot' and r['arm']==a)/12,1) for a in ('B1','B1A','B2')}
    assert pilot_usage=={'B1':15739.3,'B1A':14853.0,'B2':15139.2}
    return dict(score_summaries=summaries,delivery_grid=grid,original24_partitions=subsets,
        table6_mean_API_input_tokens=pilot_usage,
        diagnostic_corrected_support_rows=4,pilot_confirmed_support_rows=36,pilot_corrected_support_rows=1,pilot_support_2_final=35,pilot_supported_completion_final=35,diagnostic_support_2_final=14,diagnostic_support_1_final=4,diagnostic_positions=18,corrected_rows_endpoints_unchanged=True,
        scope='Recorded-score arithmetic and listed-ID delivery only; not independent semantic validation')

if __name__=='__main__': print(json.dumps(calculate(),ensure_ascii=False,indent=2))
