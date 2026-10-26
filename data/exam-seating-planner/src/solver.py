"""Stage 1 — which seats get used.

Hard rule: nobody sits side by side. Then, exactly optimised in this order:
  1. as few diagonal pairs as possible (a desk diagonally ahead is in view; the one straight ahead is blocked by its owner)
  2. as close to the podium as possible (rows nearer the front), then 3. nearer the podium in a straight line
Front/back pairs are allowed. Each room group (block / side of a fan) is a chain of rows, so a row-by-row DP is exact.
"""

def depth(room, i):
    """Distance from the podium measured straight back along the desk's own depth axis."""
    _, (vx, vy) = room.frame(i)
    d, p = room.desks[i], room.podium
    return (d['cx'] - p['cx']) * vx + (d['cy'] - p['cy']) * vy

def add(a, b):
    return tuple(x + y for x, y in zip(a, b))

def stage1(rooms, n_students, fixed=None, counts=None):
    """rooms: list of Room. fixed: {(room_idx, desk): True/False}. counts: {room_idx: head-count} (optional).
    Returns the set of (room_idx, desk) to use."""
    fixed = fixed or {}
    per_room = []
    for ri, room in enumerate(rooms):
        far, far2 = max(depth(room, i) for i in room.seats), max(room.dist(i) for i in room.seats)
        near = {i: (depth(room, i) / far, room.dist(i) / far2) for i in room.seats}   # 0 = at the podium, 1 = back wall
        table = {0: ((0, 0.0, 0.0), frozenset())}
        for g in room.groups:
            table = combine(table, solve_group(room, ri, g, near, fixed))
        if counts and ri in counts:
            assert counts[ri] in table, f'{room.name}: cannot seat {counts[ri]} without side-by-side neighbours'
            table = {counts[ri]: table[counts[ri]]}
        per_room.append(table)
    total = {0: ((0, 0.0, 0.0), frozenset())}
    for table in per_room:
        total = combine(total, table)
    assert n_students in total, f'only {max(total)} seats are possible without side-by-side neighbours'
    return set(total[n_students][1])

def combine(a, b):
    out = {}
    for n1, (c1, p1) in a.items():
        for n2, (c2, p2) in b.items():
            n, c = n1 + n2, add(c1, c2)
            if n not in out or c < out[n][0]:
                out[n] = (c, p1 | p2)
    return out

def subsets(room, ri, row, fixed):
    """Seat choices for one row: nobody side by side, fixed seats respected."""
    seats = [i for i in row if i in set(room.seats)]
    out = []
    for mask in range(1 << len(seats)):
        sub = frozenset(i for b, i in enumerate(seats) if mask >> b & 1)
        if all(not room.nbr[i]['side'] & sub for i in sub) and all(fixed.get((ri, i), i in sub) == (i in sub) for i in seats):
            out.append(sub)
    return out

def solve_group(room, ri, group, near, fixed):
    """Row-by-row DP over one group: for every head-count, the best (diagonal pairs, depth, distance) and its seats."""
    table = {frozenset(): {0: ((0, 0.0, 0.0), frozenset())}}
    for q in group:
        nxt = {}
        for cur in subsets(room, ri, room.rows[q], fixed):
            own = (sum(near[i][0] for i in cur), sum(near[i][1] for i in cur))
            for prev, by_n in table.items():
                step = (sum(len(room.nbr[i]['diag'] & prev) for i in cur), *own)
                slot = nxt.setdefault(cur, {})
                for n, (c, picked) in by_n.items():
                    m, c2 = n + len(cur), add(c, step)
                    if m not in slot or c2 < slot[m][0]:
                        slot[m] = (c2, picked | {(ri, i) for i in cur})
        table = nxt
    best = {}
    for by_n in table.values():
        for n, v in by_n.items():
            if n not in best or v[0] < best[n][0]:
                best[n] = v
    return best

def pairs(rooms, chosen, kind):
    return sum(len(rooms[ri].nbr[i][kind] & {j for rj, j in chosen if rj == ri}) for ri, i in chosen) // 2
