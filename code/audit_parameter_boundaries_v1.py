"""Exact boundary helpers extracted from the recorded source; legacy archive CLI omitted."""
import re
from collections import Counter

START=re.compile(r'^[Pr]\d{4}(?:\[[0-9.]+\]|\.[0-9.]+)?$')

def norm(s):return re.sub(r'\s+','',s or '')

def signature(t):return [norm(v) for v in t['cells'][0] if v is not None]

def is_parameter(t):return signature(t)[:2]==['参数','功能']

def partition(tables):
    counts=Counter(t['pdf_page'] for t in tables if is_parameter(t))
    result=[];orphan=[];current=None;previous=None
    for t in sorted(tables,key=lambda t:(t['pdf_page'],t['bbox'][1])):
        if not is_parameter(t) or counts[t['pdf_page']]!=1:
            if current:current['closure']='ambiguous_table';current=None
            orphan.extend(t['row_fragment_ids'][1:]);previous=None;continue
        continuous=previous is not None and t['pdf_page']==previous['pdf_page']+1 and signature(t)==signature(previous)
        if current and not continuous:current['closure']='unobserved_or_incompatible_next_page';current=None
        for i,values in enumerate(t['cells'][1:],1):
            label=norm(values[0])
            fid=t['row_fragment_ids'][i]
            if START.fullmatch(label):
                if current:current['closure']='next_parameter_observed';current['next_parameter']=label
                current=dict(parameter=label,closure='right_boundary_unobserved',body_fragments=[],table_ids=[],headers={})
                result.append(current)
            if current:
                current['body_fragments'].append(fid)
                if t['table_id'] not in current['table_ids']:current['table_ids'].append(t['table_id'])
                current['headers'][t['table_id']]=t['row_fragment_ids'][0]
            else:orphan.append(fid)
        previous=t
    return result,orphan

def tests():
    def table(page,labels,header=None):return dict(table_id=f't{page}',pdf_page=page,bbox=[0,0,1,1],
        cells=[header or ['参数','功能']]+[[x,'引用P9999，不是新起点'] for x in labels],
        row_fragment_ids=[f'p{page}r{i}' for i in range(len(labels)+1)])
    cases=[]
    def check(name,ok):assert ok,name;cases.append(dict(name=name,passed=True,synthetic=True))
    p,o=partition([table(1,['P0001','说明：','P0002'])]);check('notes_retained',len(p[0]['body_fragments'])==2)
    check('next_start_closes',p[0]['closure']=='next_parameter_observed')
    check('last_not_assumed_complete',p[-1]['closure']=='right_boundary_unobserved')
    p,o=partition([table(1,['P0001']),table(2,['注意：','P0002'])]);check('adjacent_continuation',len(p[0]['body_fragments'])==2)
    p,o=partition([table(1,['P0001']),table(3,['注意：','P0002'])]);check('gap_not_joined',len(o)==1)
    p,o=partition([table(1,['P0001']),table(2,['注意：','P0002'],['参数','功能','不同列'])]);check('header_change_not_joined',len(o)==1)
    p,o=partition([table(1,['注意：','P0001'])]);check('leading_orphan_retained',len(o)==1)
    p,o=partition([table(1,['P0001[0...2]','r0002.0...15','说明：'])]);check('index_and_bit_ids',len(p)==2)
    p,o=partition([table(1,['P0001','说明：P9999','P0002'])]);check('mentioned_parameter_not_start',len(p)==2 and len(p[0]['body_fragments'])==2)
    p,o=partition([table(1,['P0001']),table(1,['P0002'])]);check('multiple_tables_fail_closed',not p and len(o)==2)
    p,o=partition([table(1,['P0001']),table(2,['说明：','P0002'],['参数','功能',None])]);check('null_column_header_preserved_not_rewritten',len(p[0]['body_fragments'])==2)
    return cases
