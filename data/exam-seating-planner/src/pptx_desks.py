"""Read desks drawn in a PowerPoint slide (rectangles, possibly inside nested, rotated groups) as absolute rectangles in pt."""
import math
import numpy as np
from pptx import Presentation
from pptx.oxml.ns import qn

E = 12700

def T(x, y): return np.array([[1, 0, x], [0, 1, y], [0, 0, 1]], float)
def S(x, y): return np.array([[x, 0, 0], [0, y, 0], [0, 0, 1]], float)
def R(deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)

def place(xfrm):
    """Matrix that rotates/flips a box about its own centre, in parent coordinates."""
    off, ext = xfrm.find(qn('a:off')), xfrm.find(qn('a:ext'))
    x, y, w, h = (int(off.get('x')) / E, int(off.get('y')) / E, int(ext.get('cx')) / E, int(ext.get('cy')) / E)
    cx, cy = x + w / 2, y + h / 2
    F = S(-1 if xfrm.get('flipH') == '1' else 1, -1 if xfrm.get('flipV') == '1' else 1)
    return T(cx, cy) @ R(int(xfrm.get('rot', 0)) / 60000) @ F @ T(-cx, -cy), (x, y, w, h)

def load(path, slide=1, podium_text='Podium'):
    """Return (podium, desks) from the given slide (1-based); each is dict(cx, cy, w, h, rot) in pt.
    The podium is the shape whose text is podium_text; every other shape is a desk."""
    shapes = []
    def walk(el, M):
        for ch in el:
            tag = ch.tag.split('}')[1]
            if tag == 'grpSp':
                xf = ch.find(qn('p:grpSpPr')).find(qn('a:xfrm'))
                P, (x, y, w, h) = place(xf)
                co, ce = xf.find(qn('a:chOff')), xf.find(qn('a:chExt'))
                cox, coy = int(co.get('x')) / E, int(co.get('y')) / E
                cew, ceh = int(ce.get('cx')) / E, int(ce.get('cy')) / E
                walk(ch, M @ P @ T(x, y) @ S(w / cew, h / ceh) @ T(-cox, -coy))
            elif tag == 'sp':
                xf = ch.find(qn('p:spPr')).find(qn('a:xfrm'))
                if xf is None:
                    continue
                P, (x, y, w, h) = place(xf)
                A = M @ P
                c = A @ [x + w / 2, y + h / 2, 1]
                vx, vy = A[:2, :2] @ [w, 0], A[:2, :2] @ [0, h]
                txt = ''.join(t.text or '' for t in ch.iter(qn('a:t'))).strip()
                shapes.append(dict(cx=float(c[0]), cy=float(c[1]), w=float(np.hypot(*vx)), h=float(np.hypot(*vy)),
                                   rot=math.degrees(math.atan2(vx[1], vx[0])) % 360, txt=txt))
    prs = Presentation(path)
    walk(prs.slides[slide - 1].shapes._spTree, np.eye(3))
    podium = next(s for s in shapes if s['txt'] == podium_text)
    desks = [s for s in shapes if s is not podium and not s['txt']]
    return podium, desks
