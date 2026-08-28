#!/usr/bin/env python3
"""Post-render fix for pandoc + IFoA template.

Pandoc writes body/content placeholders without <a:xfrm>, relying on the slide
layout for position. PowerPoint does not resolve that inheritance for the IFoA
layouts (custom idx values), so text lands at the slide origin, unwrapped, over
the title. This script copies the geometry from the matching layout placeholder
into each slide shape explicitly, and forces wrapping + shrink-to-fit.

Usage: python3 fix_pptx.py <deck.pptx>   (rewrites in place)
Wired in via _quarto.yml post-render.
"""
import re
import sys
import zipfile
import shutil
import os

PH_RE = re.compile(r'<p:ph\b([^>]*?)/?>')
SP_RE = re.compile(r'<p:sp>.*?</p:sp>', re.S)
XFRM_RE = re.compile(r'<a:xfrm[^>]*>.*?</a:xfrm>', re.S)


def ph_attrs(sp):
    m = PH_RE.search(sp)
    if not m:
        return None
    a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
    return a.get('type', 'obj'), a.get('idx')


def layout_geometry(layout_xml):
    geo = {}
    for sp in SP_RE.findall(layout_xml):
        key = ph_attrs(sp)
        x = XFRM_RE.search(sp)
        if key and x:
            geo[key] = x.group(0)
            # also index by idx alone and type alone for looser matching
            geo.setdefault(('*', key[1]), x.group(0))
            geo.setdefault((key[0], '*'), x.group(0))
    return geo


def fix_slide(slide_xml, geo):
    def repl(m):
        sp = m.group(0)
        key = ph_attrs(sp)
        if not key or XFRM_RE.search(sp):
            return sp
        x = geo.get(key) or geo.get(('*', key[1])) or geo.get((key[0], '*'))
        if not x:
            return sp
        # insert xfrm into spPr
        if '<p:spPr/>' in sp:
            sp = sp.replace('<p:spPr/>', f'<p:spPr>{x}</p:spPr>', 1)
        elif '<p:spPr>' in sp:
            sp = sp.replace('<p:spPr>', f'<p:spPr>{x}', 1)
        else:
            sp = sp.replace('</p:nvSpPr>', f'</p:nvSpPr><p:spPr>{x}</p:spPr>', 1)
        # wrap + shrink text on overflow
        sp = re.sub(r'<a:bodyPr\s*/>',
                    '<a:bodyPr wrap="square" rtlCol="0"><a:normAutofit/></a:bodyPr>', sp, 1)
        sp = re.sub(r'<a:bodyPr([^/>]*)/>',
                    r'<a:bodyPr\1 wrap="square"><a:normAutofit/></a:bodyPr>', sp, 1)
        return sp
    return SP_RE.sub(repl, slide_xml)


def main(path):
    tmp = path + '.tmp'
    zin = zipfile.ZipFile(path)
    names = zin.namelist()
    layouts = {n: layout_geometry(zin.read(n).decode('utf8'))
               for n in names if n.startswith('ppt/slideLayouts/slideLayout')}
    zout = zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED)
    fixed = 0
    for it in zin.infolist():
        data = zin.read(it.filename)
        m = re.match(r'ppt/slides/(slide\d+)\.xml$', it.filename)
        if m:
            rels = zin.read(f'ppt/slides/_rels/{m.group(1)}.xml.rels').decode('utf8')
            lay = re.search(r'slideLayouts/(slideLayout\d+\.xml)', rels)
            if lay:
                geo = layouts.get('ppt/slideLayouts/' + lay.group(1), {})
                new = fix_slide(data.decode('utf8'), geo)
                if new != data.decode('utf8'):
                    fixed += 1
                data = new.encode('utf8')
        zout.writestr(it, data)
    zout.close()
    zin.close()
    shutil.move(tmp, path)
    print(f'fix_pptx: {fixed} slides patched in {os.path.basename(path)}')


if __name__ == '__main__':
    main(sys.argv[1])
