"""Generic controls. No question IDs, answers, references or scores as inputs."""
from collections import defaultdict
import copy
import json
import v20_adapter_v1 as old

VERSION = 'DIRECT-ASSEMBLY-CONTROLS-v1'

def page_index(units):
    index = defaultdict(list)
    for uid, unit in units.items():
        assert len(unit['pdf_pages']) == 1, 'Requires frozen page-bounded units'
        index[unit['pdf_pages'][0]].append(uid)
    for page in index:
        index[page].sort(key=lambda uid: (min(units[uid]['fragment_ids']), uid))
    return index

def signature(table):
    # Preserve null positions and column count: no inferred/filled headers.
    return tuple(None if cell is None else ''.join(cell.split()) for cell in table['cells'][0])

def table_index(tables, units):
    fragment_owner = {}
    for uid, unit in units.items():
        if unit['kind'] == 'table':
            for fid in unit['fragment_ids']:
                assert fid not in fragment_owner
                fragment_owner[fid] = uid
    by_unit = {}; by_page = defaultdict(list)
    for table in tables:
        owners = {fragment_owner.get(fid) for fid in table['row_fragment_ids']}
        assert len(owners) == 1 and None not in owners
        uid = owners.pop()
        assert uid not in by_unit
        by_unit[uid] = table
        by_page[table['pdf_page']].append(uid)
    return by_unit, by_page

def same_scope(a, b):
    return all(a[key] == b[key] for key in ('source_document', 'source_sha256', 'revision', 'sections'))

def table_members(uid, units, tmap, tpages):
    if uid not in tmap:
        return [uid], 'non_table'
    anchor = tmap[uid]; page = anchor['pdf_page']; sig = signature(anchor)
    if anchor.get('native_text_missing_characters', 0):
        return [uid], 'anchor_character_loss'
    peers = [u for u in tpages[page] if signature(tmap[u]) == sig and same_scope(units[uid], units[u])]
    if len(peers) != 1:
        return [uid], 'ambiguous_anchor_table'
    members = [uid]
    for neighbor in (page - 1, page + 1):
        possible = [u for u in tpages.get(neighbor, [])
                    if signature(tmap[u]) == sig and same_scope(units[uid], units[u])]
        if len(possible) == 1 and not tmap[possible[0]].get('native_text_missing_characters', 0):
            members.append(possible[0])
    members.sort(key=lambda u: (units[u]['pdf_pages'], u))
    return members, 'one_hop_header_tables' if len(members) > 1 else 'no_unique_compatible_neighbor'

def bundles(hits, chunks, units, pages, tmap, tpages, mode, decisions):
    assert mode in ('B1', 'B1A', 'BT')
    seen = set()
    for hit in hits:
        cid = hit['chunk_id']; uid = chunks[cid]['unit_id']
        if uid in seen:
            continue
        seen.add(uid)
        if mode == 'BT':
            members, reason = table_members(uid, units, tmap, tpages)
        else:
            page = units[uid]['pdf_pages'][0]
            members = list(dict.fromkeys([uid] + pages.get(page - 1, []) + pages.get(page + 1, [])))
            reason = 'fixed_one_page_each_side'
        decisions.append(dict(trigger_chunk=cid, parent=uid, members=members, reason=reason))
        entries = [old.entry_for(units[m], cid) for m in members]
        if mode == 'B1':
            for entry in entries:
                yield [entry], []
        else:
            yield entries, []

def tests():
    records = []
    def check(name, ok):
        assert ok, name
        records.append(dict(name=name, passed=True, synthetic=True))
    def unit(uid, page, kind='text', fragment=None):
        return dict(unit_id=uid, kind=kind, pdf_pages=[page], printed_pages=[page],
                    source_document='D', source_sha256='h', revision='v', document_date='d',
                    sections=['S'], fragment_ids=[fragment or uid], packet_fragment_ids=[fragment or uid],
                    packet_text=uid, flags=['original'])
    units = {'a':unit('a',1), 'b':unit('b',2,fragment='p2F002'),
             'c':unit('c',2,fragment='p2F001'), 'd':unit('d',3), 'f':unit('f',5)}
    chunks = {k:{'unit_id':k} for k in units}
    def window(mode, ids):
        return list(bundles([{'chunk_id':i} for i in ids], chunks, units, page_index(units), {}, {}, mode, []))
    ids = lambda groups:[e['chunk_id'] for group,_ in groups for e in group]
    check('first_page_and_source_order', ids(window('B1',['a'])) == ['a','c','b'])
    check('last_page_no_wrap', ids(window('B1',['f'])) == ['f'])
    check('missing_page_not_skipped', ids(window('B1',['d'])) == ['d','c','b'])
    check('repeated_trigger_parent_once', ids(window('B1',['a','a'])) == ['a','c','b'])
    check('neighbor_sequence_equal_atomic', ids(window('B1',['b'])) == ids(window('B1A',['b'])))
    check('anchor_page_other_unit_not_added', ids(window('B1',['b'])) == ['b','a','d'])
    units['a']['sections']=['other']
    check('generic_window_no_semantic_filter', 'a' in ids(window('B1',['b'])))
    def table(uid, page, header=None, loss=0):
        return dict(table_id=uid, pdf_page=page, cells=[header or ['code',None,'value'],['x',None,'y']],
                    row_fragment_ids=[uid], native_text_missing_characters=loss)
    tus={str(i):unit(str(i),i,'table') for i in range(1,5)}
    ts=[table(str(i),i) for i in range(1,5)]
    tm,tp=table_index(ts,tus)
    check('generic_two_sided_tables',table_members('2',tus,tm,tp)[0]==['1','2','3'])
    check('no_recursive_chaining', '4' not in table_members('2',tus,tm,tp)[0])
    tm['3']['cells'][0]=['code','value',None]
    check('null_column_position_matters',table_members('2',tus,tm,tp)[0]==['1','2'])
    tm['3']['cells'][0]=['code',None,'value'];tus['3']['sections']=['other']
    check('different_section_not_joined',table_members('2',tus,tm,tp)[0]==['1','2'])
    tus['3']['sections']=['S'];tus['3']['revision']='different'
    check('different_revision_not_joined',table_members('2',tus,tm,tp)[0]==['1','2'])
    tus['3']['revision']='v';tm['3']['native_text_missing_characters']=1
    check('neighbor_character_loss_not_joined',table_members('2',tus,tm,tp)[0]==['1','2'])
    tm['2']['native_text_missing_characters']=1
    check('anchor_character_loss_fallback',table_members('2',tus,tm,tp)[0]==['2'])
    tm['2']['native_text_missing_characters']=0;tm['3']['native_text_missing_characters']=0
    tus['3x']=unit('3x',3,'table');tm['3x']=table('3x',3);tp[3].append('3x')
    check('multiple_compatible_neighbors_fail_closed',table_members('2',tus,tm,tp)[0]==['1','2'])
    tus['2x']=unit('2x',2,'table');tm['2x']=table('2x',2);tp[2].append('2x')
    check('ambiguous_anchor_fallback',table_members('2',tus,tm,tp)[0]==['2'])
    check('non_table_fallback',table_members('a',units,tm,tp)[0]==['a'])
    count=lambda msg:1+sum(len(e['text']) for e in json.loads(msg[1]['content'])['evidence'])
    g=window('B1',['a']);snap=copy.deepcopy(g)
    check('sequential_first_overflow_keeps_anchor',len(old.fit('q',iter(g),'s',count,2)[1])==1)
    check('atomic_window_overflow_empty',len(old.fit('q',iter(window('B1A',['a'])),'s',count,2)[1])==0)
    check('exact_fit',len(old.fit('q',iter(g),'s',count,4)[1])==3)
    check('fit_does_not_mutate_groups',g==snap)
    r=old.fit('q',iter(g+g),'s',count,4)
    check('selected_ids_deduplicated',len(r[1])==3)
    prior=[([old.entry_for(units['a'],'prior')],[])]
    r=old.fit('q',iter(prior+window('B1A',['a'])),'s',count,2)
    check('prior_partial_not_rolled_back',[e['chunk_id'] for e in r[1]]==['a'])
    try: old.fit('q',iter(g),'s',count,0)
    except ValueError: check('base_budget_rejected',True)
    else: check('base_budget_rejected',False)
    return records
