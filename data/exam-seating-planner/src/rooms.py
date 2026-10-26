"""A room = desks + podium + who sits next to whom, loaded from rooms/<name>.json.

Two config types end up in the same shape (every desk is a rectangle with a centre, size and angle):
  "grid": rows x blocks of columns, aisles between blocks, blocked cells (pillars), podium above or below a block
  "pptx": desks read straight from a slide, e.g. a fan-shaped lecture room

Neighbours are then found from geometry alone, so both types follow the same rules:
  row   : desks touching end to end (along the desk's width) form one row
  side  : touching desks in the same row
  front : in the next row back, the desk(s) right behind
  diag  : in the next row back, the desk(s) just beside the one right behind
  near  : same line, one desk or an aisle away (not touching, but close enough to see)
Rows that link front-to-back form a group (a block, one side of a fan); a group is a chain of rows from the podium back.
"""
import json, math, os
import pptx_desks

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOM_DIR = os.path.join(ROOT, 'rooms')

# grid geometry (pt) — only proportions matter, the renderer scales to the slide
DW, DH, GAP, AISLE, POD_H = 90, 50, 6, 34, 40

class Room:
    def __init__(self, name, desks, podium, stretch_x=1.0):
        """desks: dict(cx, cy, w, h, rot[, blocked=label]); a blocked desk (pillar) shapes the rows but is never seated."""
        self.name, self.desks, self.podium = name, desks, podium
        self.stretch_x = stretch_x                    # renderer may widen the room to use the slide
        self.seats = [i for i, d in enumerate(desks) if 'blocked' not in d]
        self._link()

    # --- geometry helpers ---
    def frame(self, i):
        """Unit vectors along the desk's width (u) and depth pointing away from the podium (v)."""
        d = self.desks[i]
        a = math.radians(d['rot'])
        u, v = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
        away = (d['cx'] - self.podium['cx'], d['cy'] - self.podium['cy'])
        if v[0] * away[0] + v[1] * away[1] < 0:
            v = (-v[0], -v[1])
        return u, v

    def offset(self, i, j):
        """Position of desk j seen from desk i: (along the row, away from the podium, straight-line distance)."""
        (ux, uy), (vx, vy) = self.frame(i)
        dx, dy = self.desks[j]['cx'] - self.desks[i]['cx'], self.desks[j]['cy'] - self.desks[i]['cy']
        return dx * ux + dy * uy, dx * vx + dy * vy, math.hypot(dx, dy)

    def dist(self, i):
        d, p = self.desks[i], self.podium
        return math.hypot(d['cx'] - p['cx'], d['cy'] - p['cy'])

    # --- neighbours ---
    def _link(self):
        n = len(self.desks)
        self.nbr = [{'side': set(), 'front': set(), 'diag': set(), 'near': set()} for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                du, dv, _ = self.offset(i, j)
                if abs(dv) < 0.5 * self.desks[i]['h']:
                    kind = 'side' if abs(du) < 1.25 * self.desks[i]['w'] else 'near' if abs(du) < 2.3 * self.desks[i]['w'] else None
                    if kind:                          # 'near' here = across an aisle on the same line
                        self.nbr[i][kind].add(j); self.nbr[j][kind].add(i)
        for i in range(n):                            # one desk away along the row, however the row curves
            for k in self.nbr[i]['side']:
                for j in self.nbr[k]['side'] - self.nbr[i]['side'] - {i}:
                    self.nbr[i]['near'].add(j); self.nbr[j]['near'].add(i)
        # rows = chains of side-by-side desks
        self.row_of, self.rows = [None] * n, []
        for i in range(n):
            if self.row_of[i] is None:
                stack, row = [i], []
                self.row_of[i] = len(self.rows)
                while stack:
                    k = stack.pop(); row.append(k)
                    for m in self.nbr[k]['side']:
                        if self.row_of[m] is None:
                            self.row_of[m] = len(self.rows); stack.append(m)
                self.rows.append(row)
        # front / diagonal: look into the nearest row behind (and ahead, for front)
        reach = [min(self.dist(i) for i in row) for row in self.rows]   # how far each row starts from the podium
        def nearest_row(i, sign):
            r, h = self.row_of[i], self.desks[i]['h']
            cands = [j for j in range(n) if self.row_of[j] != r
                     and sign * self.offset(i, j)[1] > 0.5 * h                       # behind (or ahead) this desk
                     and sign * (reach[self.row_of[j]] - reach[r]) > 0.25 * h]      # a row further back, not one alongside
            if not cands:
                return [], 0
            row = self.rows[self.row_of[min(cands, key=lambda j: self.offset(i, j)[2])]]
            return row, min(self.offset(i, j)[2] for j in row)
        found = {}
        for i in range(n):
            w = self.desks[i]['w']
            row, near = nearest_row(i, +1)
            for j in row:
                d = self.offset(i, j)[2]
                kind = 'front' if d < near + 0.3 * w else 'diag' if d < near + 0.9 * w else None
                key = frozenset((i, j))
                if kind and found.get(key) != 'front':
                    found[key] = kind
            row, near = nearest_row(i, -1)                # seen from the row ahead, the closest desk is also front
            for j in row:
                if self.offset(i, j)[2] < near + 0.3 * w:
                    found[frozenset((i, j))] = 'front'
        for key, kind in found.items():
            i, j = tuple(key)
            self.nbr[i][kind].add(j); self.nbr[j][kind].add(i)
        self._group()
        blocked = {i for i, d in enumerate(self.desks) if 'blocked' in d}
        for i, nb in enumerate(self.nbr):             # nobody sits at a pillar
            for kind in nb:
                nb[kind] = set() if i in blocked else nb[kind] - blocked

    def _group(self):
        """Groups of rows linked front-to-back, each ordered from the podium outward, with seat labels."""
        link = {r: set() for r in range(len(self.rows))}
        for i, nb in enumerate(self.nbr):
            for j in nb['front'] | nb['diag']:
                link[self.row_of[i]].add(self.row_of[j])
        seen, groups = set(), []
        for r in range(len(self.rows)):
            if r in seen:
                continue
            stack, g = [r], []
            seen.add(r)
            while stack:
                q = stack.pop(); g.append(q)
                for p in link[q] - seen:
                    seen.add(p); stack.append(p)
            groups.append(sorted(g, key=lambda q: min(self.dist(i) for i in self.rows[q])))
        cx = lambda g: sum(self.desks[i]['cx'] for q in g for i in self.rows[q]) / sum(len(self.rows[q]) for q in g)
        self.groups = sorted(groups, key=cx)
        for g in self.groups:                         # the solver needs each row to touch only the rows before/after it
            for a, q in enumerate(g):
                assert link[q] <= set(g[max(0, a - 1):a + 2]), f'{self.name}: rows are not a front-to-back chain'
        # label = group letter + row number + seat number (left to right as drawn)
        self.label = [None] * len(self.desks)
        for gi, g in enumerate(self.groups):
            for ri, q in enumerate(g):
                (ux, uy), _ = self.frame(self.rows[q][0])
                along = sorted(self.rows[q], key=lambda i: self.desks[i]['cx'] * ux + self.desks[i]['cy'] * uy)
                if ux < 0:
                    along.reverse()
                for si, i in enumerate(along):
                    self.label[i] = f'{chr(65 + gi)}{ri + 1}-{si + 1}'
        self.index = {lab: i for i, lab in enumerate(self.label)}

def grid(cfg):
    rows, blocks = cfg['rows'], cfg['blocks']
    blocked = {(r - 1, c - 1) for r, c in cfg.get('blocked', [])}
    xs, x = [], 0.0
    for bi, ncol in enumerate(blocks):
        for c in range(ncol):
            xs.append((bi, x + DW / 2)); x += DW + GAP
        x += AISLE - GAP
    desks = []
    for r in range(rows):
        for c, (bi, cx) in enumerate(xs):
            rect = dict(cx=cx, cy=r * (DH + GAP) + DH / 2, w=DW, h=DH, rot=0.0)
            if (r, c) in blocked:
                rect['blocked'] = cfg.get('blocked_label', '')
            desks.append(rect)
    pod = cfg['podium']
    first = sum(blocks[:pod['block'] - 1])
    left = xs[first][1] - DW / 2
    right = xs[first + blocks[pod['block'] - 1] - 1][1] + DW / 2
    top = pod.get('side', 'top') == 'top'
    cy = -8 - POD_H / 2 if top else rows * (DH + GAP) - GAP + 8 + POD_H / 2
    podium = dict(cx=(left + right) / 2, cy=cy, w=right - left, h=POD_H, rot=0.0)
    return Room(cfg['name'], desks, podium)

def from_pptx(cfg, base):
    podium, desks = pptx_desks.load(os.path.join(base, cfg['file']), cfg.get('slide', 1), cfg.get('podium_text', 'Podium'))
    return Room(cfg['name'], desks, podium, stretch_x=cfg.get('stretch_x', 1.0))

def load(name):
    path = os.path.join(ROOM_DIR, f'{name}.json')
    cfg = json.load(open(path, encoding='utf-8'))
    if cfg['type'] == 'grid':
        return grid(cfg)
    if cfg['type'] == 'pptx':
        return from_pptx(cfg, os.path.dirname(path))
    raise ValueError(f'{path}: unknown type {cfg["type"]}')
