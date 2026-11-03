"""Conservative, query/gold-free parameter assembly on frozen source rows."""
from collections import Counter, defaultdict
import copy
import re
import json
import v20_adapter_v1 as old
from audit_parameter_boundaries_v1 import partition, is_parameter

VERSION = 'PARAM-PACKET-DEV-v1.1'


def render(fids, fragments):
    return old.reconstruct(dict(packet_fragment_ids=fids), fragments)


def build(tables, units, fragments):
    packets, orphans = partition(tables)
    tmap = {t['table_id']: t for t in tables}
    parents = {}
    for t in tables:
        matches = [u for u in units.values() if set(t['row_fragment_ids']) <= set(u['fragment_ids'])]
        parents[t['table_id']] = matches[0] if len(matches) == 1 else None
    by_fragment = {}
    catalog = []
    for p in packets:
        reasons = []
        ts = [tmap[tid] for tid in p['table_ids']]
        us = [parents[tid] for tid in p['table_ids']]
        if p['closure'] != 'next_parameter_observed':
            reasons.append('open_boundary')
        if any(u is None for u in us):
            reasons.append('ambiguous_parent')
        else:
            if any(u['kind'] != 'table' or set(u['packet_fragment_ids']) != set(t['row_fragment_ids']) for t, u in zip(ts, us)):
                reasons.append('extra_or_missing_parent_context')
            if any('image' in flag for u in us for flag in u['flags']):
                reasons.append('untranscribed_image_on_parent_page')
            if any(f['kind'] == 'image_region' and f['pdf_page'] in {t['pdf_page'] for t in ts} for f in fragments.values()):
                reasons.append('image_region_on_parent_page')
            if any(u['sections'] != us[0]['sections'] or not any('8.2 参数列表' in s for s in u['sections']) for u in us):
                reasons.append('section_not_verified')
            for key in ('source_document', 'source_sha256', 'revision', 'document_date'):
                if any(u[key] != us[0][key] for u in us):
                    reasons.append('source_identity_mismatch')
        if any(t.get('native_text_missing_characters', 1) != 0 for t in ts):
            reasons.append('missing_native_characters')
        fids = []
        for t in ts:
            fids += [p['headers'][t['table_id']]] + [f for f in p['body_fragments'] if f in t['row_fragment_ids']]
        fids = list(dict.fromkeys(fids))
        uid = 'V20-PARAM-v1-' + p['body_fragments'][0]
        entry = None
        if not reasons:
            entry = dict(chunk_id=uid, retrieved_chunk_id=None, document_number=us[0]['source_document'],
                         revision=us[0]['revision'], document_date=us[0]['document_date'],
                         pdf_pages=sorted({fragments[f]['pdf_page'] for f in fids}),
                         printed_pages=sorted({n for u in us for n in u['printed_pages']}),
                         sections=us[0]['sections'], kind='parameter_entry', source_fragment_ids=fids,
                         parent_unit_ids=list(dict.fromkeys(u['unit_id'] for u in us)),
                         flags=['parameter_entry_local_text_closed', 'source_rows_verbatim',
                                'null_cells_preserved', 'reference_dependencies_unresolved',
                                'semantic_completeness_not_verified'], text=render(fids, fragments))
        row = dict(**p, entry_id=uid, eligible=not reasons, fallback_reasons=sorted(set(reasons)),
                   source_fragment_ids=fids, parent_unit_ids=[u['unit_id'] for u in us if u], entry=entry)
        catalog.append(row)
        for f in p['body_fragments']:
            assert f not in by_fragment
            by_fragment[f] = row
    return catalog, by_fragment, orphans


def touched_fragments(chunk, unit, fragments):
    fids = unit['packet_fragment_ids']
    if render(fids, fragments) != unit['packet_text']:
        return None
    start, end = chunk['start'], chunk['end']
    if not 0 <= start < end <= len(unit['packet_text']) or unit['packet_text'][start:end] != chunk['text']:
        return None
    touched = []
    offset = 0
    for i, fid in enumerate(fids):
        piece = render([fid], fragments)
        stop = offset + len(piece) + (1 if i + 1 < len(fids) else 0)
        if start < stop and end > offset:
            touched.append(fid)
        offset = stop
    return touched


def select(chunk, unit, fragments, by_fragment):
    touched = touched_fragments(chunk, unit, fragments)
    if not touched:
        return None, 'offset_or_render_mismatch'
    chosen = []
    for fid in touched:
        p = by_fragment.get(fid)
        if p is None:
            return None, 'header_or_unassigned_fragment'
        if not p['eligible']:
            return None, '|'.join(p['fallback_reasons'])
        if p['entry_id'] not in {x['chunk_id'] for x in chosen}:
            entry = copy.deepcopy(p['entry'])
            entry['retrieved_chunk_id'] = chunk['chunk_id']
            chosen.append(entry)
    return chosen, 'parameter_packet'


def bundles(hits, chunks, units, relations, arm, fragments, by_fragment, decisions):
    if arm not in ('baseline', 'structure'):
        raise ValueError(arm)
    index = defaultdict(list)
    if arm == 'structure':
        for r in relations:
            for uid in r['triggers']:
                index[uid].append(r)
    seen = set()
    for hit in hits:
        cid = hit['chunk_id']; chunk = chunks[cid]; uid = chunk['unit_id']; unit = units[uid]
        linked = index.get(uid, [])
        if uid in seen:
            continue
        entries = None
        reason = 'non_parameter_parent'
        if linked:
            reason = 'structure_relation_preserved'
        elif unit['kind'] == 'table':
            entries, reason = select(chunk, unit, fragments, by_fragment)
        if entries is None:
            seen.add(uid)
            ids = list(dict.fromkeys([m for r in linked for m in r['members']] + [uid]))
            entries = [old.entry_for(units[m], cid) for m in ids]
        # A later whole-parent fallback may overlap earlier entries; record, do not silently change fit.
        decisions.append(dict(chunk_id=cid, parent_unit_id=uid, reason=reason,
                              output_ids=[e['chunk_id'] for e in entries]))
        yield entries, [r['relation_id'] for r in linked]


def tests():
    from audit_parameter_boundaries_v1 import tests as boundary_tests
    results = boundary_tests()
    def check(name, condition):
        assert condition, name
        results.append(dict(name=name, passed=True, synthetic=True))
    fs = {f'f{i}': dict(fragment_id=f'f{i}', pdf_page=1, kind='table_row', text=s, cells=[s,None,'value']) for i, s in enumerate(['header', 'P0001', 'note', 'P0002', 'last'])}
    check('real_schema_null_cells_preserved',json.loads(render(['f1'],fs).split('\n',1)[1])==['P0001',None,'value'])
    u = dict(unit_id='u', packet_fragment_ids=list(fs), packet_text=render(list(fs), fs), kind='table')
    def chunk(fid):
        s = u['packet_text'].index(render([fid], fs))
        return dict(chunk_id='c'+fid, unit_id='u', start=s, end=s+len(render([fid], fs)), text=render([fid], fs))
    packet = dict(eligible=True, entry_id='new', entry=dict(chunk_id='new', text=render(['f0','f1','f2'],fs)), fallback_reasons=[])
    bm = dict(f1=packet, f2=packet, f3=dict(eligible=False, fallback_reasons=['open_boundary']))
    check('exact_offsets', touched_fragments(chunk('f2'),u,fs)==['f2'])
    check('header_fallback',select(chunk('f0'),u,fs,bm)[0] is None)
    check('complete_entry_for_note',select(chunk('f2'),u,fs,bm)[0][0]['text']==packet['entry']['text'])
    check('open_fallback',select(chunk('f3'),u,fs,bm)[0] is None)
    bad=chunk('f1');bad['end']+=1
    check('invalid_offsets_fallback',select(bad,u,fs,bm)[0] is None)
    span=chunk('f2');span['end']=chunk('f3')['end'];span['text']=u['packet_text'][span['start']:span['end']]
    check('mixed_safe_unsafe_fallback',select(span,u,fs,bm)[0] is None)
    bm['f3']=dict(packet,entry_id='new2',entry=dict(chunk_id='new2',text='next'))
    check('multiple_entries_atomic',len(select(span,u,fs,bm)[0])==2)
    check('input_entry_unmodified',packet['entry'].get('retrieved_chunk_id') is None)
    # Full catalog eligibility/metadata fixture.
    t=dict(table_id='t',pdf_page=1,bbox=[0,0,10,10],cells=[['参数','功能'],['P0001','x'],['','说明'],['P0002','y'],['','end']],row_fragment_ids=list(fs),native_text_missing_characters=0)
    full=dict(u,fragment_ids=list(fs),flags=[],sections=['8.2 参数列表',''],source_document='doc',source_sha256='hash',revision='1',document_date='date',printed_pages=[1])
    cat,_,_=build([t],{'u':full},fs)
    check('new_identity_no_whole_flag',cat[0]['eligible'] and cat[0]['entry_id']!='u' and 'table_preserved_whole' not in cat[0]['entry']['flags'])
    check('closed_entry_full_rows',cat[0]['source_fragment_ids']==['f0','f1','f2'])
    for flag in ['table_contains_untranscribed_image','page_has_untranscribed_images']:
        c,_,_=build([t],{'u':dict(full,flags=[flag])},fs)
        check(flag+'_fallback',not c[0]['eligible'])
    c,_,_=build([dict(t,native_text_missing_characters=1)],{'u':full},fs)
    check('missing_chars_fallback',not c[0]['eligible'])
    c,_,_=build([t],{'u':dict(full,sections=['other'])},fs)
    check('other_section_fallback',not c[0]['eligible'])
    return results
