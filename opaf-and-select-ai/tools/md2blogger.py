import re, sys, markdown
def convert(md):
    html = markdown.markdown(md, extensions=['tables','fenced_code','md_in_html'], output_format='html')
    html = re.sub(r'<h1>.*?</h1>\s*', '', html, count=1, flags=re.S)
    html = re.sub(r'\s+style="[^"]*"', '', html)
    html = re.sub(r'<p>\s*(<img [^>]*>)\s*</p>', r'\1', html)
    # external reference links open in a new tab (requested for the 'Useful links' section)
    k = html.find('<h2>Useful links and documentation</h2>')
    if k >= 0:
        head, tail = html[:k], html[k:]
        tail = re.sub(r'<a href="(https?://[^"]+)">', r'<a href="\1" target="_blank" rel="noopener">', tail)
        html = head + tail
    m = re.match(r'\s*(<img [^>]*>)\s*(.*?)(?=<h2>)(.*)', html, re.S)
    feat, intro, body = m.group(1), m.group(2).strip(), m.group(3).strip()
    out = ('<article class="zv-blog-post">\n\n' + feat + '\n\n<div class="post-intro">\n' + intro +
           '\n</div>\n\n<!--more-->\n\n' + body + '\n\n</article>\n')
    return out
def check(h):
    errs=[]
    if h.count('<article class="zv-blog-post">')!=1 or h.count('<article')!=1: errs.append('article')
    if h.count('<!--more-->')!=1: errs.append('more')
    for bad in ['<style','style="','<h1','<html','<head','<body','DOCTYPE','<link','<script','data:image']:
        if bad in h: errs.append(bad)
    i=h.find('post-intro'); j=h.find('<!--more-->'); k=h.find('<h2>')
    if not (h.find('<img')<i<j<k): errs.append('order')
    intro=re.search(r'<div class="post-intro">(.*?)</div>',h,re.S).group(1)
    w=len(re.sub('<[^>]+>','',intro).split())
    if not 60<=w<=180: errs.append(f'intro words {w}')
    if h.count('<img', 0, j)!=1: errs.append('imgs before more')
    for lbl in ['Hero','Series,','Posts,']:
        pass
    return errs, w
for f in sys.argv[1:]:
    h=convert(open(f).read()); out=f[:-3]+'.html'; open(out,'w').write(h)
    e,w=check(h); print(out, 'intro words', w, 'ERRORS' if e else 'OK', e)
