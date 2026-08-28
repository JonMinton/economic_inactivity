#!/usr/bin/env python3
"""Build ifoa_life_reference.pptx (pandoc-compatible) from the pristine IFoA template.

Why this exists — three things about the IFoA template trip pandoc up:
1. Layout names: pandoc looks for fixed names ("Title and Content", "Two Content",
   "Section Header", ...). We rename six IFoA layouts (XML only; design unchanged).
2. Missing placeholders: the IFoA Title Slide layout has only a `title` placeholder,
   pandoc writes `ctrTitle` + `subTitle`; the colour section-divider layout has no title
   placeholder at all. We retype/add placeholders so title and section slides render.
3. Three slide masters: pandoc carries only slideMaster1 but copies layout and
   presentation relationships that point at slideMaster2/3, customXml, authors.xml,
   handoutMaster, changesInfo — none of which exist in the output. That is what makes
   PowerPoint demand a "repair" on open. We consolidate to ONE master (the content
   master, originally slideMaster2), re-point every layout at it, and drop the dangling
   parts from the package.

Usage:  python3 build_reference.py   (reads ifoa_life_template.pptx, writes ifoa_life_reference.pptx)
"""
import re
import zipfile

SRC = 'ifoa_life_template.pptx'
DST = 'ifoa_life_reference.pptx'

RENAMES = {
    'slideLayout2.xml': ('Single column', 'Title and Content'),
    'slideLayout5.xml': ('1_Two Columns', 'Two Content'),
    'slideLayout11.xml': ('Two columns - in 3rds', 'Comparison'),
    'slideLayout12.xml': ('Single column + image', 'Content with Caption'),
    'slideLayout18.xml': ('Blank with footer - Colour', 'Section Header'),
    'slideLayout17.xml': ('Blank with footer - White', 'Blank'),
}
# parts to drop entirely (prefix match)
DROP_PREFIXES = (
    'customXml/', 'ppt/authors.xml', 'ppt/changesInfos/', 'ppt/handoutMasters/',
    'ppt/slideMasters/slideMaster3.xml', 'ppt/slideMasters/_rels/slideMaster3.xml.rels',
    'ppt/theme/theme3.xml',
)
SP_RE = re.compile(r'<p:sp>.*?</p:sp>', re.S)


def patch_title_layout(x):
    sp = [m.group(0) for m in SP_RE.finditer(x) if 'type="title"' in m.group(0)][0]
    old_xfrm = re.search(r'<a:off[^/]*/><a:ext[^/]*/>', sp).group(0)
    title = (sp.replace('type="title"', 'type="ctrTitle"').replace('sz="7000"', 'sz="4000"')
             .replace(old_xfrm, '<a:off x="2500000" y="3200000"/><a:ext cx="11256000" cy="2000000"/>'))
    sub = (sp.replace('type="title" hasCustomPrompt="1"', 'type="subTitle" idx="1"')
           .replace('sz="7000" b="1"', 'sz="1800" b="0"')
           .replace(old_xfrm, '<a:off x="2500000" y="5300000"/><a:ext cx="11256000" cy="2400000"/>'))
    sub = re.sub(r'<p:cNvPr id="\d+" name="[^"]*"', '<p:cNvPr id="70" name="Subtitle 2"', sub, count=1)
    sub = re.sub(r'<a:p>.*</a:p>', '<a:p><a:r><a:rPr lang="en-GB"/><a:t>Subtitle</a:t></a:r></a:p>', sub, flags=re.S)
    return x.replace(sp, title + sub)


def inject_section_title(x, content_layout_xml):
    if 'type="title"' in x:
        return x
    tsp = [m.group(0) for m in SP_RE.finditer(content_layout_xml) if 'type="title"' in m.group(0)][0]
    tsp = re.sub(r'<a:off x="\d+" y="\d+"/><a:ext cx="\d+" cy="\d+"/>',
                 '<a:off x="1500000" y="3400000"/><a:ext cx="13256000" cy="2200000"/>', tsp, count=1)
    tsp = re.sub(r'<p:cNvPr id="\d+"', '<p:cNvPr id="97"', tsp, count=1)
    return x.replace('</p:spTree>', tsp + '</p:spTree>', 1)


def main():
    zin = zipfile.ZipFile(SRC)
    parts = {i.filename: zin.read(i.filename) for i in zin.infolist()}
    txt = lambda n: parts[n].decode('utf8')

    # --- 1 & 2: layout renames and placeholder patches
    for base, (old, new) in RENAMES.items():
        n = 'ppt/slideLayouts/' + base
        x = txt(n)
        assert f'<p:cSld name="{old}"' in x, base
        parts[n] = x.replace(f'<p:cSld name="{old}"', f'<p:cSld name="{new}"', 1).encode()
    parts['ppt/slideLayouts/slideLayout1.xml'] = patch_title_layout(txt('ppt/slideLayouts/slideLayout1.xml')).encode()
    parts['ppt/slideLayouts/slideLayout18.xml'] = inject_section_title(
        txt('ppt/slideLayouts/slideLayout18.xml'), txt('ppt/slideLayouts/slideLayout2.xml')).encode()

    # --- 3: consolidate to a single master = old slideMaster2 (content master), renamed slideMaster1
    m2, m2rels = txt('ppt/slideMasters/slideMaster2.xml'), txt('ppt/slideMasters/_rels/slideMaster2.xml.rels')
    # add layouts that lived on masters 1 and 3
    extra = ['slideLayout1.xml', 'slideLayout16.xml', 'slideLayout17.xml', 'slideLayout18.xml', 'slideLayout19.xml']
    next_rid = max(int(i) for i in re.findall(r'Id="rId(\d+)"', m2rels)) + 1
    next_id = max(int(i) for i in re.findall(r'<p:sldLayoutId id="(\d+)"', m2)) + 1
    new_rels, new_ids = '', ''
    for lay in extra:
        new_rels += (f'<Relationship Id="rId{next_rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                     f'relationships/slideLayout" Target="../slideLayouts/{lay}"/>')
        new_ids += f'<p:sldLayoutId id="{next_id}" r:id="rId{next_rid}"/>'
        next_rid += 1; next_id += 1
    m2rels = m2rels.replace('</Relationships>', new_rels + '</Relationships>')
    m2 = m2.replace('</p:sldLayoutIdLst>', new_ids + '</p:sldLayoutIdLst>')
    parts['ppt/slideMasters/slideMaster1.xml'] = m2.encode()
    parts['ppt/slideMasters/_rels/slideMaster1.xml.rels'] = m2rels.encode()
    del parts['ppt/slideMasters/slideMaster2.xml'], parts['ppt/slideMasters/_rels/slideMaster2.xml.rels']
    # every layout -> slideMaster1
    for n in list(parts):
        if n.startswith('ppt/slideLayouts/_rels/'):
            parts[n] = re.sub(r'slideMaster\d+\.xml', 'slideMaster1.xml', txt(n)).encode()

    # presentation.xml.rels: keep only one slideMaster rel, drop dangling part types
    prels = txt('ppt/_rels/presentation.xml.rels')
    keep_master_rid = re.search(r'Id="(rId\d+)"[^>]*Target="slideMasters/slideMaster1\.xml"', prels).group(1)
    def drop_rel(m):
        r = m.group(0)
        if 'slideMasters/slideMaster' in r and keep_master_rid not in r:
            return ''
        if any(k in r for k in ('customXml', 'authors.xml', 'changesInfo', 'handoutMaster')):
            return ''
        return r
    prels = re.sub(r'<Relationship [^>]*/>', drop_rel, prels)
    parts['ppt/_rels/presentation.xml.rels'] = prels.encode()
    pres = txt('ppt/presentation.xml')
    pres = re.sub(r'<p:sldMasterIdLst>.*?</p:sldMasterIdLst>',
                  lambda m: '<p:sldMasterIdLst>' + ''.join(e for e in re.findall(r'<p:sldMasterId [^>]*/>', m.group(0))
                                                           if keep_master_rid in e) + '</p:sldMasterIdLst>', pres, flags=re.S)
    pres = re.sub(r'<p:handoutMasterIdLst>.*?</p:handoutMasterIdLst>', '', pres, flags=re.S)
    parts['ppt/presentation.xml'] = pres.encode()

    # drop dangling parts and their content-type overrides
    for n in list(parts):
        if n.startswith(DROP_PREFIXES):
            del parts[n]
    ct = txt('[Content_Types].xml')
    ct = re.sub(r'<Override [^>]*/>', lambda m: '' if not any(
        m.group(0).find(f'PartName="/{p}"') >= 0 for p in parts) else m.group(0), ct)
    parts['[Content_Types].xml'] = ct.encode()
    # package-level rels (docProps etc.) — drop anything pointing at a removed part
    top = txt('_rels/.rels')
    top = re.sub(r'<Relationship [^>]*/>', lambda m: m.group(0) if re.search(
        r'Target="/?([^"]+)"', m.group(0)).group(1) in parts else '', top)
    parts['_rels/.rels'] = top.encode()

    # sanity: no dangling relationship targets remain
    import posixpath
    missing = []
    for n, d in parts.items():
        if not n.endswith('.rels'):
            continue
        base = posixpath.dirname(posixpath.dirname(n))
        for t, mode in re.findall(r'Target="([^"]+)"(?: TargetMode="(\w+)")?', d.decode()):
            if mode == 'External':
                continue
            p = t.lstrip('/') if t.startswith('/') else posixpath.normpath(posixpath.join(base, t))
            if p not in parts:
                missing.append((n, t))
    assert not missing, missing

    with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zout:
        # [Content_Types].xml first, as PowerPoint prefers
        zout.writestr('[Content_Types].xml', parts.pop('[Content_Types].xml'))
        for n, d in parts.items():
            zout.writestr(n, d)
    print(f'wrote {DST}: 1 master, {sum(1 for n in parts if re.match(r"ppt/slideLayouts/slideLayout\d+\.xml$", n))} layouts, no dangling rels')


if __name__ == '__main__':
    main()
