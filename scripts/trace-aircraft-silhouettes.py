"""Trace the silhouette sheet into one SVG per aircraft (one-off tool).

    python3 -m venv /tmp/trace && /tmp/trace/bin/pip install potracer numpy pillow
    /tmp/trace/bin/python scripts/trace-aircraft-silhouettes.py \
        assets/aircraft-icons/piradar/source-silhouettes.png assets/aircraft-icons/piradar

The sheet is two rows of black silhouettes on a transparent background, in the
order listed in ``names``. Each one is cropped, centred in a square box and
traced with potrace. Run scripts/build-aircraft-icons.py afterwards.
"""
import sys, numpy as np, potrace
from PIL import Image
src, out = sys.argv[1], sys.argv[2]
names = [["typhoon","f35","hawk","rafale","apache"],["merlin","chinook","c130","c17","a400m","osprey"]]
a = np.array(Image.open(src).convert("RGBA"))[:, :, 3] > 128
def runs(proj, gap):
    idx = np.where(proj > 0)[0]; out=[]; start=idx[0]; prev=idx[0]
    for i in idx[1:]:
        if i - prev > gap: out.append((start, prev)); start = i
        prev = i
    out.append((start, prev)); return out
rows = runs(a.sum(1), 20)
print("rows", rows)
def fmt(v): return ("%.1f" % v).rstrip("0").rstrip(".")
def to_path(curves):
    d=[]
    for c in curves:
        sp=c.start_point; d.append(f"M{fmt(sp.x)} {fmt(sp.y)}")
        for s in c.segments:
            if s.is_corner: d.append(f"L{fmt(s.c.x)} {fmt(s.c.y)}L{fmt(s.end_point.x)} {fmt(s.end_point.y)}")
            else: d.append(f"C{fmt(s.c1.x)} {fmt(s.c1.y)} {fmt(s.c2.x)} {fmt(s.c2.y)} {fmt(s.end_point.x)} {fmt(s.end_point.y)}")
        d.append("Z")
    return "".join(d)
for (y0,y1), rownames in zip(rows, names):
    band = a[y0:y1+1]
    cols = runs(band.sum(0), 3)
    print(rownames, cols)
    assert len(cols) == len(rownames), (len(cols), rownames)
    for (x0,x1), name in zip(cols, rownames):
        crop = band[:, x0:x1+1]
        ys = np.where(crop.any(1))[0]; crop = crop[ys[0]:ys[-1]+1]
        h, w = crop.shape; side = max(h, w); pad = round(side * 0.02); side += 2*pad
        canvas = np.zeros((side, side), bool)
        oy, ox = (side-h)//2, (side-w)//2
        canvas[oy:oy+h, ox:ox+w] = crop
        bm = potrace.Bitmap(~canvas)  # potrace fills dark pixels
        curves = bm.trace(turdsize=8, alphamax=1.0, opticurve=True, opttolerance=0.4)
        scale = 512/side
        path = to_path(curves)
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {side} {side}"><path fill-rule="evenodd" d="{path}"/></svg>\n'
        open(f"{out}/{name}.svg","w").write(svg)
        print(f"  {name}: {w}x{h} -> box {side}, {len(curves)} curves, {len(svg)} bytes")
