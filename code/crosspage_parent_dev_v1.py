"""Full original-parent atomic grouping; no question IDs or gold in selection."""
from collections import defaultdict
import parameter_packet_dev_v1_1 as params
import v20_adapter_v1 as old

VERSION='CROSSPAGE-PARENT-DEV-v1'
IMAGE_ONLY={'image_region_on_parent_page','untranscribed_image_on_parent_page'}

def build(tables,units,fragments):
    catalog,by_fragment,orphans=params.build(tables,units,fragments)
    headers={t['row_fragment_ids'][0] for t in tables}
    for p in catalog:
        p['crosspage_eligible']=len(p['table_ids'])>1 and not (set(p['fallback_reasons'])-IMAGE_ONLY)
        p['crosspage_group_id']='V20-XPAGE-v1-'+p['body_fragments'][0]
        p['images_delivered']=False
        p['crosspage_semantic_approval']=None
    return catalog,by_fragment,headers,orphans

def match(chunk,unit,fragments,by_fragment,headers):
    touched=params.touched_fragments(chunk,unit,fragments)
    if not touched:return [],'offset_mismatch'
    body=[f for f in touched if f not in headers]
    if not body:return [],'header_only'
    ps=[]
    for f in body:
        p=by_fragment.get(f)
        if p is None:return [],'unassigned_row'
        if len(p['table_ids'])>1 and not p['crosspage_eligible']:
            return [],'ineligible_crosspage_boundary'
        if p['crosspage_eligible'] and p['crosspage_group_id'] not in {x['crosspage_group_id'] for x in ps}:
            ps.append(p)
    return ps,'crosspage_group' if ps else 'no_crosspage_in_hit'

def bundles(hits,chunks,units,relations,arm,fragments,by_fragment,headers,decisions):
    if arm not in ('baseline','structure'):raise ValueError(arm)
    index=defaultdict(list);seen=set()
    if arm=='structure':
        for r in relations:
            for uid in r['triggers']:index[uid].append(r)
    for hit in hits:
        cid=hit['chunk_id'];chunk=chunks[cid];uid=chunk['unit_id']
        if uid in seen:continue
        seen.add(uid);unit=units[uid];linked=index.get(uid,[])
        ps,reason=match(chunk,unit,fragments,by_fragment,headers) if unit['kind']=='table' else ([], 'non_table')
        baseids=list(dict.fromkeys([m for r in linked for m in r['members']]+[uid]))
        xids=sorted({m for p in ps for m in p['parent_unit_ids']},key=lambda x:(units[x]['pdf_pages'],x))
        ids=list(dict.fromkeys([m for m in baseids if m!=uid]+xids+[uid])) if ps else baseids
        gids=[p['crosspage_group_id'] for p in ps]
        decisions.append(dict(trigger_chunk=cid,parent=uid,reason=reason,group_ids=gids,
                              groups=[dict(id=p['crosspage_group_id'],parameter=p['parameter'],members=p['parent_unit_ids']) for p in ps],members=ids))
        yield [old.entry_for(units[m],cid) for m in ids],[r['relation_id'] for r in linked]+gids

def tests():
    records=params.tests()
    def check(n,v):
        assert v,n
        records.append(dict(name=n,passed=True,synthetic=True))
    fs={};ts=[];us={}
    for page,labels in [(1,['P0001','说明：']),(2,['注意：','P0002'])]:
        fids=[];cells=[['参数','功能']]+[[x,'原文'] for x in labels]
        for i,c in enumerate(cells):
            fid=f'p{page}f{i}';fids.append(fid)
            fs[fid]=dict(fragment_id=fid,pdf_page=page,kind='table_row',text=' '.join(c),cells=c)
        ts.append(dict(table_id=f't{page}',pdf_page=page,bbox=[0,0,1,1],row_fragment_ids=fids,cells=cells,native_text_missing_characters=0))
        us[f'u{page}']=dict(unit_id=f'u{page}',kind='table',fragment_ids=fids,packet_fragment_ids=fids,
            packet_text=params.render(fids,fs),flags=['table_preserved_whole','table_contains_untranscribed_image'],
            sections=['8.2 参数列表',''],source_document='D',source_sha256='hash',revision='R',document_date='date',pdf_pages=[page],printed_pages=[page])
    cat,bm,hs,_=build(ts,us,fs)
    p=cat[0]
    check('image_allowed_only_with_full_parents',p['crosspage_eligible'] and not p['eligible'])
    check('two_parent_members',p['parent_unit_ids']==['u1','u2'])
    def chunk(fid):
        uid='u'+fid[1];t=us[uid]['packet_text'];s=t.index(params.render([fid],fs));e=s+len(params.render([fid],fs))
        return dict(chunk_id='c'+fid,unit_id=uid,start=s,end=e,text=t[s:e])
    c=chunk('p2f1');check('continuation_to_identity',match(c,us['u2'],fs,bm,hs)[0][0]['parameter']=='P0001')
    c=chunk('p1f1');c['start']=0;c['text']=us['u1']['packet_text'][:c['end']]
    check('header_plus_body_allowed',len(match(c,us['u1'],fs,bm,hs)[0])==1)
    check('header_only_no_guess',match(chunk('p1f0'),us['u1'],fs,bm,hs)[1]=='header_only')
    p['crosspage_eligible']=False
    check('ambiguous_crosspage_no_join',not match(chunk('p2f1'),us['u2'],fs,bm,hs)[0]);p['crosspage_eligible']=True
    c=chunk('p2f1');dec=[]
    groups=list(bundles([{'chunk_id':c['chunk_id']}],{c['chunk_id']:c},us,[],'baseline',fs,bm,hs,dec))
    check('source_order_from_continuation_hit',[e['chunk_id'] for e in groups[0][0]]==['u1','u2'])
    check('whole_source_and_flags_preserved',all(e['text']==us[e['chunk_id']]['packet_text'] and e['flags']==us[e['chunk_id']]['flags'] for e in groups[0][0]))
    count=lambda messages:sum(len(e['text']) for e in __import__('json').loads(messages[1]['content'])['evidence'])+1
    total=count(old.messages('q',groups[0][0],'s'))
    result=old.fit('q',iter(groups),'s',count,total-1)
    check('atomic_overflow_no_partial_new_member',result[1]==[])
    result=old.fit('q',iter(groups),'s',count,total)
    check('atomic_exact_fit',len(result[1])==2)
    prior=([old.entry_for(us['u1'],'prior')],[])
    result=old.fit('q',iter([prior]+groups),'s',count,total-1)
    check('previous_partial_not_misrepresented',[e['chunk_id'] for e in result[1]]==['u1'] and result[3][-1]['status']=='first_overflow_stop')
    ts[1]['native_text_missing_characters']=1
    cc,_,_,_=build(ts,us,fs)
    check('missing_chars_not_relaxed_for_images',not cc[0]['crosspage_eligible'])
    return records
