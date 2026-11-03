"""V20 adaptation-only parser and query-independent context assembly. No API calls."""
from collections import Counter, defaultdict
import hashlib
import json
import re

VERSION = 'V20-ADAPTER-CANDIDATE-v1-20261010'
PARSER = dict(header_bottom=80, footer_band=55, wrap_gap=2.0, wrap_indent=3.0,
              note_gap=24, max_chars=380, overlap=40, tables='whole_detected_table',
              null_cells='preserve_no_forward_fill', cross_page_join=False,
              images='geometry_only_not_OCR', both_arms_same_parents=True)
RULES = dict(max_gap_points=24, max_indent_points=30, max_list_items=20,
             max_group_characters=2400, reference_distance_points=180,
             same_page_only=True, same_section_only=True, transitive_expansion=False,
             reject_nested_colon_items=True, reject_table_introductions=True,
             does_not_assert_global_list_completeness=True)


def sha_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def norm(text):
    return re.sub(r'\s+', '', text)


def box_union(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def inside(a, b):
    x, y = (a[0] + a[2]) / 2, (a[1] + a[3]) / 2
    return b[0] - 1 <= x <= b[2] + 1 and b[1] - 1 <= y <= b[3] + 1


def bullet(text):
    return bool(re.search(r'(?m)^\s*[•●▪]\s*$', text))


def split(text):
    start = 0
    while start < len(text):
        end = min(start + PARSER['max_chars'], len(text))
        if end < len(text):
            cut = text.rfind('\n', start + PARSER['max_chars'] // 2, end)
            if cut > start:
                end = cut + 1
        yield start, end, text[start:end]
        if end == len(text):
            break
        start = end - PARSER['overlap']


def render_fragment(f):
    if 'cells' in f:
        # JSON null distinguishes merged/absent slots from an actual empty string.
        text = json.dumps(f['cells'], ensure_ascii=False, separators=(',', ':'))
    else:
        text = f['text']
    return f"[PDF {f['pdf_page']} / {f['fragment_id']}]\n{text}"


def reconstruct(unit, fragments):
    return '\n'.join(render_fragment(fragments[f]) for f in unit['packet_fragment_ids'])


def parse(fixture, authorized_pages):
    pages = fixture['pages']
    if [p['pdf_page'] for p in pages] != sorted(set(authorized_pages)):
        raise ValueError('Fixture pages differ from authorized adaptation boundary')
    source = fixture['source']
    fragments, units, tables, inventory = [], [], [], []
    fmap = {}
    for page in pages:
        pn = page['pdf_page']
        fs = 0

        def frag(kind, text, bbox, **extra):
            nonlocal fs
            fs += 1
            record = dict(fragment_id=f'V20-p{pn:03}-F{fs:03}', pdf_page=pn,
                          kind=kind, text=text, bbox=bbox, **extra)
            fragments.append(record)
            fmap[record['fragment_id']] = record
            return record['fragment_id']

        all_lines, elements = [], []
        for bi, block in enumerate(page['blocks']):
            if block.get('type') == 1:
                elements.append(dict(kind='image', bbox=block['bbox'], text='', block_id=bi))
                continue
            retained = []
            for li, line in enumerate(block.get('lines', [])):
                text = ''.join(span['text'] for span in line['spans']).strip()
                if not text:
                    continue
                spans = [s for s in line['spans'] if s['text'].strip()]
                item = dict(text=text, bbox=line['bbox'], line_id=f'b{bi}-l{li}',
                            size=max(s['size'] for s in spans),
                            bold=all(bool(s['flags'] & 16) for s in spans))
                all_lines.append(item)
                # Large chapter titles are body text even if they enter the header band.
                if (line['bbox'][1] >= PARSER['header_bottom'] or item['size'] >= 18) and line['bbox'][3] < page['height'] - PARSER['footer_band']:
                    retained.append(item)
            outside = [l for l in retained if not any(inside(l['bbox'], t['bbox']) for t in page['tables'])]
            if outside:
                text = '\n'.join(l['text'] for l in outside)
                is_note = text.strip() in ('说明', '注意', '警告', '危险', '小心')
                is_heading = (not is_note and len(text) < 90 and
                              ((all(l['bold'] for l in outside) and not text.endswith(('。', '：', ':')))
                               or bool(re.match(r'^\d+(?:\.\d+)+\s*\n', text))))
                elements.append(dict(kind='note_label' if is_note else 'heading' if is_heading else 'prose',
                                     text=text, bbox=box_union([l['bbox'] for l in outside]),
                                     native_line_ids=[l['line_id'] for l in outside], block_id=bi))
        body_lines = [l for l in all_lines if (l['bbox'][1] >= PARSER['header_bottom'] or l['size'] >= 18)
                      and l['bbox'][3] < page['height'] - PARSER['footer_band']]
        printed_candidates = [l['text'] for l in all_lines if l['bbox'][1] >= page['height'] - PARSER['footer_band'] and l['text'].isdigit()]
        printed = int(printed_candidates[0]) if len(printed_candidates) == 1 else None
        header = [l['text'] for l in all_lines if l['bbox'][3] < PARSER['header_bottom'] and re.match(r'^\d+(?:\.\d+)+\s', l['text'])]
        previous_section = page['sections'][-1]
        section = (previous_section['title'] if previous_section['start_pdf_page'] < pn
                   else header[-1] if header else previous_section['title'])
        for ti, table in enumerate(page['tables'], 1):
            tid = f'V20-p{pn:03}-T{ti:02}'
            native = [l for l in body_lines if inside(l['bbox'], table['bbox'])]
            elements.append(dict(kind='table', text='', bbox=table['bbox'], table_id=tid,
                                 raw=table, native=native))
        elements.sort(key=lambda e: (e['bbox'][1], e['bbox'][0]))
        # Rejoin only wrapped lines, not separate paragraphs/list entries.
        merged = []
        for e in elements:
            if merged and e['kind'] == merged[-1]['kind'] == 'prose':
                prev = merged[-1]
                gap = e['bbox'][1] - prev['bbox'][3]
                if (-0.5 <= gap <= PARSER['wrap_gap'] and abs(e['bbox'][0] - prev['bbox'][0]) <= PARSER['wrap_indent']
                        and not bullet(e['text']) and not re.match(r'^\d+[.)]\s', e['text'])):
                    prev['text'] += '\n' + e['text']
                    prev['bbox'] = box_union([prev['bbox'], e['bbox']])
                    prev['native_line_ids'] += e['native_line_ids']
                    continue
            merged.append(e.copy())
        # Keep an adjacent note label + paragraph together, not a free-floating "说明".
        combined, i = [], 0
        while i < len(merged):
            e = merged[i]
            if e['kind'] == 'note_label' and i + 1 < len(merged):
                nxt = merged[i + 1]
                if nxt['kind'] == 'prose' and 0 <= nxt['bbox'][1] - e['bbox'][3] <= 6:
                    e = dict(e, kind='note', text=e['text'] + '\n' + nxt['text'],
                             bbox=box_union([e['bbox'], nxt['bbox']]),
                             native_line_ids=e['native_line_ids'] + nxt['native_line_ids'])
                    i += 1
            combined.append(e)
            i += 1
        headings, local_title, local_id = [], '', ''
        page_units, barriers = [], []
        for ei, e in enumerate(combined):
            kind = e['kind']
            if kind == 'heading':
                fid = frag('heading', e['text'], e['bbox'], native_line_ids=e['native_line_ids'])
                title = ' '.join(e['text'].split())
                if re.match(r'^\d+(?:\.\d+)+\s', title):
                    section = title
                    headings, local_title, local_id = [fid], '', ''
                else:
                    headings = [h for h in headings if fmap[h].get('numbered_heading')]
                    local_title, local_id = title, fid
                    headings.append(fid)
                fmap[fid]['numbered_heading'] = bool(re.match(r'^\d+(?:\.\d+)+\s', title))
                barriers.append(dict(kind=kind, bbox=e['bbox']))
                continue
            if kind == 'image':
                frag('image_region', '', e['bbox'], native_block_id=e['block_id'], text_decoded=False)
                barriers.append(dict(kind=kind, bbox=e['bbox']))
                continue
            fids, flags = [], []
            context = list(headings)
            if kind == 'table':
                t = e['raw']
                for ri, row in enumerate(t['cells']):
                    fids.append(frag('table_row', '\n'.join(c for c in row if c), t['row_bboxes'][ri],
                                     cells=row, cell_bboxes=t['cell_bboxes'][ri], row_index=ri, table_id=e['table_id']))
                missing = Counter(norm('\n'.join(l['text'] for l in e['native']))) - Counter(norm('\n'.join(fmap[f]['text'] for f in fids)))
                if missing:
                    fids.append(frag('table_native_fallback', '\n'.join(l['text'] for l in e['native']), e['bbox'],
                                     native_line_ids=[l['line_id'] for l in e['native']]))
                    flags.append('table_native_fallback_not_reconstructed_cells')
                # Same-page preceding paragraph provides a table's explicit introduction, common to both arms.
                if page_units and ei > 0 and combined[ei-1]['kind'] == 'prose':
                    prev = page_units[-1]
                    if prev['sections'] == [section, local_title] and 0 <= e['bbox'][1] - prev['bbox'][3] <= 36:
                        context += prev['fragment_ids']
                flags += ['table_preserved_whole', 'merged_cells_not_forward_filled']
                if any(inside(b['bbox'], e['bbox']) for b in combined if b['kind'] == 'image'):
                    flags.append('table_contains_untranscribed_image')
                tables.append(dict(table_id=e['table_id'], pdf_page=pn, bbox=e['bbox'],
                                   cells=t['cells'], cell_bboxes=t['cell_bboxes'], row_fragment_ids=fids[:len(t['cells'])],
                                   native_text_missing_characters=sum(missing.values()), header_inference=False))
                barriers.append(dict(kind=kind, bbox=e['bbox']))
            else:
                fids = [frag(kind, e['text'], e['bbox'], native_line_ids=e['native_line_ids'])]
                if kind in ('note', 'note_label'):
                    barriers.append(dict(kind=kind, bbox=e['bbox']))
            if not headings:
                flags.append('leading_page_context_not_joined')
            if any(b['kind'] == 'image' for b in combined):
                flags.append('page_has_untranscribed_images')
            if re.search(r'下[图表]|见图|如图|以下.*(?:对话框|窗口)|按照以下步骤', e.get('text', '')):
                flags.append('visual_or_following_material_reference')
            if re.search(r'\(页\s*\d+\)', e.get('text', '')):
                flags.append('page_reference_not_auto_followed')
            u = dict(unit_id=f'V20-018-p{pn:03}-U{len(page_units)+1:03}', kind=kind,
                     fragment_ids=fids, context_fragment_ids=context, note_fragment_ids=[], bbox=e['bbox'],
                     sections=[section, local_title], local_scope_id=local_id, flags=flags,
                     source_document=source['document_id'], source_sha256=source['sha256'],
                     document_date=source['edition'], revision='018', pdf_pages=[pn], printed_pages=[printed],
                     source_element_index=ei)
            if kind == 'note' and page_units:
                prev = page_units[-1]
                if (prev['sections'] == u['sections'] and prev['kind'] in ('prose', 'table')
                        and 0 <= e['bbox'][1] - prev['bbox'][3] <= PARSER['note_gap']
                        and ei > 0 and combined[ei-1]['kind'] in ('prose', 'table')):
                    prev['note_fragment_ids'] += fids
            page_units.append(u)
        # Keep headings available even when a page has no ordinary prose after them.
        for u in page_units:
            u['packet_fragment_ids'] = list(dict.fromkeys(u['context_fragment_ids'] + u['fragment_ids'] + u['note_fragment_ids']))
            u['packet_text'] = reconstruct(u, fmap)
            u['flags'] = sorted(set(u['flags']))
        native_chars = Counter(norm('\n'.join(l['text'] for l in body_lines)))
        extracted_chars = Counter(norm('\n'.join(f['text'] for f in fragments if f['pdf_page'] == pn and f['kind'] != 'image_region')))
        missing = native_chars - extracted_chars
        if missing:
            raise ValueError(f'Unaccounted native characters on PDF {pn}: {dict(missing)}')
        inventory.append(dict(pdf_page=pn, printed_page=printed, sections=sorted(set(u['sections'][0] for u in page_units)),
                              body_lines=len(body_lines), tables=len(page['tables']),
                              image_regions=sum(e['kind']=='image' for e in combined),
                              barriers=barriers, native_characters_unaccounted=0,
                              cross_page_joined=False, cross_page_completeness_asserted=False))
        units += page_units
    chunks = []
    for u in units:
        for i, (start, end, text) in enumerate(split(u['packet_text']), 1):
            chunks.append(dict(chunk_id=f"{u['unit_id']}-C{i:03}", unit_id=u['unit_id'], text=text,
                               start=start, end=end, source_sha256=source['sha256'], text_sha256=sha_text(text),
                               pdf_pages=u['pdf_pages'], must_expand_parent=True))
    return dict(fragments=fragments, evidence_units=units, chunks=chunks, tables=tables, page_inventory=inventory)


def discover(units, fragments, inventory):
    pages = defaultdict(list)
    for u in units.values():
        if u['kind'] != 'prose' or len(u['fragment_ids']) != 1:
            continue
        f = fragments[u['fragment_ids'][0]]
        pages[f['pdf_page']].append(dict(uid=u['unit_id'], page=f['pdf_page'], bbox=f['bbox'], text=f['text'], sections=u['sections']))
    barriers = {p['pdf_page']: p['barriers'] for p in inventory}

    def compatible(left, right, distance=RULES['max_gap_points']):
        gap = right['bbox'][1] - left['bbox'][3]
        blocked = any(left['bbox'][3] <= b['bbox'][1] <= right['bbox'][1] for b in barriers.get(left['page'], []))
        return (left['page'] == right['page'] and left['sections'] == right['sections'] and not blocked
                and 0 <= gap <= distance and abs(left['bbox'][0]-right['bbox'][0]) <= RULES['max_indent_points'])

    relations = []
    for page, items in sorted(pages.items()):
        items.sort(key=lambda x: (x['bbox'][1], x['bbox'][0]))
        for i, intro in enumerate(items):
            if not intro['text'].rstrip().endswith(('：', ':')) or bullet(intro['text']) or '下表' in intro['text']:
                continue
            group = [intro]
            for item in items[i+1:]:
                if not compatible(group[-1], item) or not bullet(item['text']):
                    break
                group.append(item)
            if not 2 <= len(group) <= RULES['max_list_items'] + 1:
                continue
            if any(re.sub(r'[•●▪\s]', '', x['text']).endswith(('：', ':')) for x in group[1:]):
                continue
            if sum(len(x['text']) for x in group) > RULES['max_group_characters']:
                continue
            relations.append(dict(type='list_intro_items', page=page, members=[x['uid'] for x in group],
                                  triggers=[x['uid'] for x in group], verbatim_texts=[x['text'] for x in group],
                                  basis='colon_intro_contiguous_bullets_same_page_section_column_no_barrier'))
        for source in items:
            body = norm('\n'.join(source['text'].splitlines()[1:]))
            matches = []
            for target in items:
                heading = target['text'].splitlines()[0].strip()
                if (re.fullmatch(r'[\u4e00-\u9fffA-Za-z0-9 ]{2,18}模式', heading)
                        and source['uid'] != target['uid'] and compatible(target, source, RULES['reference_distance_points'])
                        and re.search(r'(?:采用|使用|按照|按|切换到|切换至)' + re.escape(norm(heading)), body)):
                    matches.append(target)
            if len(matches) == 1:
                target = matches[0]
                relations.append(dict(type='explicit_mode_back_reference', page=page,
                                      members=[target['uid'], source['uid']], triggers=[source['uid']],
                                      verbatim_texts=[target['text'], source['text']], basis='exact_preceding_named_mode_reference'))
    for i, r in enumerate(relations, 1):
        r['relation_id'] = f'V20-v1-R{i:04}'
    return relations


def entry_for(unit, trigger):
    return dict(chunk_id=unit['unit_id'], retrieved_chunk_id=trigger, document_number=unit['source_document'],
                revision=unit['revision'], document_date=unit['document_date'], pdf_pages=unit['pdf_pages'],
                printed_pages=unit['printed_pages'], sections=unit['sections'], kind=unit['kind'],
                source_fragment_ids=unit['packet_fragment_ids'], flags=unit['flags'], text=unit['packet_text'])


def bundles(hits, chunks, units, relations, arm):
    if arm not in ('baseline', 'structure'):
        raise ValueError(arm)
    index, seen = defaultdict(list), set()
    if arm == 'structure':
        for r in relations:
            for uid in r['triggers']:
                index[uid].append(r)
    for hit in hits:
        cid = hit['chunk_id']
        uid = chunks[cid]['unit_id']
        if uid in seen:
            continue
        seen.add(uid)
        linked = index.get(uid, [])
        ids = list(dict.fromkeys([m for r in linked for m in r['members']] + [uid]))
        yield [entry_for(units[m], cid) for m in ids], [r['relation_id'] for r in linked]


def messages(question, entries, system):
    return [dict(role='system', content=system), dict(role='user', content=json.dumps(
        dict(question=question, images_provided=False, evidence=entries), ensure_ascii=False, separators=(',', ':')))]


def fit(question, groups, system, count, limit):
    selected, seen, trace = [], set(), []
    if count(messages(question, [], system)) > limit:
        raise ValueError('Base prompt exceeds input cap')
    for entries, relations in groups:
        new = [e for e in entries if e['chunk_id'] not in seen]
        if not new:
            continue
        if count(messages(question, selected + new, system)) > limit:
            trace.append(dict(status='first_overflow_stop', units=[e['chunk_id'] for e in new], relations=relations))
            break
        selected += new
        seen.update(e['chunk_id'] for e in new)
        trace.append(dict(status='included', units=[e['chunk_id'] for e in new], relations=relations))
    msg = messages(question, selected, system)
    return msg, selected, dict(input_cap=limit, estimated_input_tokens=count(msg), dispatchable=bool(selected)), trace
