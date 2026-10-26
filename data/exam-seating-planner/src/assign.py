"""Stage 2 — who sits where, on the seats chosen in stage 1.

Hard rules:
  room     : named students must be in a given room
  id_apart : students next to each other in the ID-sorted roster are never "around" each other
             (around = front/back, diagonal, side, or one seat / an aisle away on the same line)
Everyone else is placed in a seeded shuffle, so the same config always gives the same chart.
check() re-verifies every rule independently of the search.
"""
import random

AROUND = ('front', 'diag', 'side', 'near')

def around(rooms, chosen):
    """{(room, desk): set of (room, desk)} — occupied seats around each occupied seat."""
    used = {}
    for ri, i in chosen:
        used.setdefault(ri, set()).add(i)
    return {(ri, i): {(ri, j) for k in AROUND for j in rooms[ri].nbr[i][k] & used[ri]} for ri, i in chosen}

def assign(rooms, chosen, people, rules, seed):
    """Return {(room, desk): person index}; raises if the rules cannot all be met."""
    rank = {p['sid']: n for n, p in enumerate(people)}            # people are sorted by ID
    by_name = {p['name']: n for n, p in enumerate(people)}
    must = {}
    for room_name, names in rules.get('room', {}).items():
        ri = next(n for n, r in enumerate(rooms) if r.name == room_name)
        for name in names:
            assert name in by_name, f'{name} is not in the roster'
            must[by_name[name]] = ri
    apart = rules.get('id_apart', False)
    near = around(rooms, chosen)
    seats = sorted(chosen, key=lambda s: (s[0], rooms[s[0]].label[s[1]]))
    order = list(range(len(people)))
    random.Random(seed).shuffle(order)
    # room head-counts must leave space for the students who are tied to a room
    for ri in range(len(rooms)):
        need = sum(1 for r in must.values() if r == ri)
        assert sum(1 for s in seats if s[0] == ri) >= need, f'{rooms[ri].name} has fewer seats than students required there'

    placed, taken = {}, set()
    def ok(seat, p):
        if p in must and must[p] != seat[0]:
            return False
        if apart:
            for other in near[seat]:
                q = placed.get(other)
                if q is not None and abs(q - p) == 1:
                    return False
        return True
    def go(k):
        if k == len(seats):
            return True
        seat = seats[k]
        # keep enough room-free students for the rooms still to fill
        for p in order:
            if p in taken or not ok(seat, p):
                continue
            rest_seats = [s for s in seats[k + 1:]]
            pending = [q for q in must if q not in taken and q != p]
            if any(sum(1 for s in rest_seats if s[0] == ri) < sum(1 for q in pending if must[q] == ri) for ri in range(len(rooms))):
                continue
            placed[seat] = p; taken.add(p)
            if go(k + 1):
                return True
            del placed[seat]; taken.discard(p)
        return False
    assert go(0), 'no seating satisfies the rules'
    return placed

def check(rooms, chosen, people, rules, placed):
    """Independent rule check. Returns a list of (rule, ok, detail)."""
    out = []
    near = around(rooms, chosen)
    out.append(('one student per seat, one seat per student', sorted(placed.values()) == list(range(len(people))) and set(placed) == set(chosen),
                f'{len(placed)} seats / {len(people)} students'))
    side = sum(1 for s in chosen for t in near[s] if s < t and t[1] in rooms[s[0]].nbr[s[1]]['side'])
    out.append(('nobody side by side', side == 0, f'{side} pairs'))
    seat_of = {p: s for s, p in placed.items()}
    by_name = {p['name']: n for n, p in enumerate(people)}
    for room_name, names in rules.get('room', {}).items():
        for name in names:
            s = seat_of[by_name[name]]
            out.append((f'{name} in room {room_name}', rooms[s[0]].name == room_name, f'{rooms[s[0]].name} {rooms[s[0]].label[s[1]]}'))
    if rules.get('id_apart'):
        bad = []
        for n in range(len(people) - 1):
            a, b = seat_of[n], seat_of[n + 1]
            if b in near[a]:
                bad.append(f'{people[n]["sid"]}/{people[n + 1]["sid"]}')
        out.append(('consecutive IDs not around each other', not bad, f'{len(bad)} pairs' + ((': ' + ', '.join(bad)) if bad else '')))
    return out
