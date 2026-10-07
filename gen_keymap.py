#!/usr/bin/env python3
"""Generate keymap.json for keymap-drawer from the kanata chord config.

Placement is solved automatically: this script replicates keymap-drawer's
combo geometry (draw/combo.py) and greedily assigns (align, offset, slide)
so no two combo boxes on the same layer overlap, staying inside the canvas.

Geometry model (verified empirically against rendered SVG):
  key centers: cols 90..660 step 60 (x), rows 28/84/140 (y); key box 56x52
  mid    : box center = centroid of key centers (+slide between 2 farthest)
  top    : y = min(top edge) - 1 - o*56 ; bottom: y = max(bot edge) + 1 + o*56
  slide s: p = (1-s)/2*start + (1+s)/2*end, start = key farthest from centroid
  combo box 40x30; canvas 750 wide -> keep rel x in [-15, 715]
"""
import json, itertools

Q,W,E,R,T,Y,U,I,O,P = range(10)
CAPS,A,S,D,F,G,H,J,K,L,SEMI = range(10,21)
Z,X,C,V,B,N,M,COMMA,DOT,SLASH = range(21,31)

POS = {}
for i, x in enumerate(range(90, 361, 60)):  POS[i] = (x, 28)       # q w e r t
for i, x in enumerate(range(420, 661, 60)): POS[i+5] = (x, 28)     # y u i o p
POS[CAPS] = (30, 84)
for i, x in enumerate(range(90, 361, 60)):  POS[i+11] = (x, 84)    # a s d f g
for i, x in enumerate(range(420, 661, 60)): POS[i+16] = (x, 84)    # h j k l ;
for i, x in enumerate(range(90, 361, 60)):  POS[i+21] = (x, 140)   # z x c v b
for i, x in enumerate(range(420, 661, 60)): POS[i+26] = (x, 140)   # n m , . /

BW, BH = 40, 30          # combo box size (draw_config)
MIN_H = 56               # offset unit for top/bottom

def box_for(keys, align, off, slide):
    pts = [POS[k] for k in keys]
    n = len(pts)
    cx = sum(p[0] for p in pts)/n; cy = sum(p[1] for p in pts)/n
    if slide is not None:
        def dist(p): return ((p[0]-cx)**2 + (p[1]-cy)**2) ** .5
        s = sorted(pts, key=lambda p: (-dist(p), p[0], p[1]))
        a, b = s[0], s[1]
        cx = (1-slide)/2*a[0] + (1+slide)/2*b[0]
        cy = (1-slide)/2*a[1] + (1+slide)/2*b[1]
    if align == "mid":
        x, y = cx, cy
    elif align == "top":
        x = cx; y = min(p[1] for p in pts) - 26 - 1 - off*MIN_H
    elif align == "bottom":
        x = cx; y = max(p[1] for p in pts) + 26 + 1 + off*MIN_H
    else:
        raise ValueError(align)
    return (x-BW/2, y-BH/2, x+BW/2, y+BH/2)

def hits(placed, rect, margin=-1):
    """True if rect overlaps any placed box with less than 1px clearance."""
    ax0,ay0,ax1,ay1 = rect
    for (bx0,by0,bx1,by1) in placed:
        if min(ax1,bx1)-max(ax0,bx0) > margin and min(ay1,by1)-max(ay0,by0) > margin:
            return True
    return False

TOP_ROWS    = [0.3, 0.9, 1.5, 2.1, 2.7, 3.3, 3.9, 4.5]
BOT_ROWS    = [0.55, 1.15, 1.75, 2.35, 2.95, 3.55, 4.15, 4.75]
SLIDES      = [0.0] + [v for pair in [(s/10, -s/10) for s in range(1, 11)] for v in pair]

def solve(combo_defs):
    """combo_defs: list of (key_positions, key_spec, layers, preferred_aligns)."""
    placed = {}      # frozenset(layers) not usable across; use per-layer lists
    layer_placed = {}
    out = []
    for keys, key, layers, prefs in combo_defs:
        cands = []
        for align in prefs:
            if align == "mid":
                cands += [("mid", None, s) for s in SLIDES]
            elif align == "top":
                cands += [("top", o, s) for o in TOP_ROWS for s in SLIDES]
            else:
                cands += [("bottom", o, s) for o in BOT_ROWS for s in SLIDES]
        chosen = None
        for align, off, s in cands:
            rect = box_for(keys, align, off, s)
            if not (-15 <= rect[0] and rect[2] <= 715):
                continue
            if any(hits(layer_placed.get(ln, []), rect) for ln in layers):
                continue
            chosen = (align, off, s, rect); break
        if chosen is None:
            raise RuntimeError(f"no placement for {keys} {key}")
        align, off, s, rect = chosen
        for ln in layers:
            layer_placed.setdefault(ln, []).append(rect)
        d = {"p": keys, "k": key, "l": layers, "a": align}
        if off is not None: d["o"] = off
        if s is not None: d["s"] = s
        out.append(d)
    return out

def k(t, h=None, type=None):
    d = {"t": t}
    if h is not None: d["h"] = h
    if type is not None: d["type"] = type
    return d

def tr(ch): return {"t": ch, "type": "trans"}

CAP = k("Esc", "Shift")
CAP_TR = k("Esc", "Shift", "trans")
one = lambda name: k(name, "1-shot")

# ---------------------------------------------------------------- layers
alpha = [ "q","w","e","r", tr("t"), tr("y"), "u","i","o","p",
    CAP, k("a","Nav R"), "s","d","f","g",
    "h","j","k","l", k(";","Nav L"),
    "z","x","c","v", tr("b"), tr("n"), "m",",",".","/" ]

letters = "qwertyuiopasdfghjkl;zxcvbnm,./"
plain = [tr(c) for c in letters[:10]] + [CAP] + [tr(c) for c in letters[10:]]

nav_r = [ "Nav L","Alt","Tab", k("PgUp","Meta"), tr("t"), tr("y"),
          "Tab","↑","Bksp","Alpha",
    CAP_TR, "Alpha","Ctrl","Esc", k("PgDn","Shift"), "",
    "C-z","←","↓","→", k("Enter","Shift"),
    tr("z"),tr("x"),"C-c","C-v",tr("b"), tr("n"),"Del","",tr("."),tr("/") ]

nav_l = [ "Alpha","Bksp","↑","Tab", tr("t"), tr("y"),
          k("PgUp","Meta"),"Tab","Alt","Nav R",
    CAP_TR, k("Enter","Shift"),"←","↓","→","C-z",
    "", k("PgDn","Shift"),"Esc","Ctrl","Alpha",
    tr("z"),tr("x"),"","Del",tr("b"), tr("n"),"C-v","C-c",tr("."),tr("/") ]

nums = [ ",","0","8","6", tr("t"), tr("y"), "6","8","0",",",
    CAP_TR, "'","5","3","1","`",
    "`","1","3","5","'",
    tr("z"),tr("x"),"?","~",tr("b"), tr("n"),"?", "~",tr("."),tr("/") ]

ff = [ "F12","F10","F8","F6", tr("t"), tr("y"), "F6","F8","F10","F12",
    CAP_TR, "F11","F5","F3","F1","",
    "","F1","F3","F5","F11",
    tr("z"),tr("x"),"","",tr("b"), tr("n"),"","",tr("."),tr("/") ]

media = [ "Bri +","⏮","Vol +","Mute", tr("t"), tr("y"), "Mute","Vol +","⏮","Bri +",
    CAP_TR, "Bri -","⏭","Vol -","⏯","↻ kanata",
    "↻ kanata","⏯","Vol -","⏭","Bri -",
    tr("z"),tr("x"),"","",tr("b"), tr("n"),"","",tr("."),tr("/") ]

go = [ "A-1","A-`","C-PgUp","C-S-t", tr("t"), tr("y"),
       "C-S-t","C-PgUp","A-`","A-1",
    CAP_TR, "A-9","C-Tab","C-PgDn","C-w","M-A-i",
    "M-A-i","C-w","C-PgDn","C-Tab","A-9",
    tr("z"),tr("x"),"","",tr("b"), tr("n"),"","",tr("."),tr("/") ]

chars = [ tr("q"),"é",tr("e"),tr("r"),tr("t"),tr("y"),"ú","í","ó",tr("p"),
    CAP_TR, "á",tr("s"),"ü",tr("f"),tr("g"),
    tr("h"),tr("j"),tr("k"),tr("l"),tr(";"),
    tr("z"),tr("x"),tr("c"),tr("v"),tr("b"), "ñ",tr("m"),tr(","),tr("."),tr("/") ]

mods = [ "", k("Alt","1-shot"),"Tab", k("Sup","1-shot"), tr("t"), tr("y"),
         k("Sup","1-shot"),"Tab", k("Alt","1-shot"),"",
    CAP_TR, "", k("Ctrl","1-shot"),"Esc", k("Shift","1-shot"),"",
    "", k("Shift","1-shot"),"Esc", k("Ctrl","1-shot"),"",
    "","","","",tr("b"), tr("n"),"","","","" ]

AL, PL, NR, NL, NU, FFl, ME, GO, CH, MO = ("Alpha (base)","Plain (gaming)",
    "Nav R (hold a)","Nav L (hold ;)","Nums (1-shot)","FF (1-shot)",
    "Media (1-shot)","Go (1-shot)","Chars (1-shot)","Mods (unreachable)")

TB = ["top", "bottom"]     # band-only preference
MTB = ["mid", "top", "bottom"]

combo_defs = [
    # ==================== ALPHA ====================
    ([S,D,F], "SPC", [AL], MTB),
    ([J,K,L], "SPC", [AL], MTB),
    ([S,E,R], "Enter", [AL], TB),
    ([U,I,L], "Enter", [AL], TB),
    ([W,D,F], "Bksp", [AL], MTB),
    ([J,K,O], "Bksp", [AL], MTB),
    ([W,E,R], one("GO"), [AL], TB),
    ([U,I,O], one("GO"), [AL], TB),
    ([Q,W,E], one("FF"), [AL], TB),
    ([I,O,P], one("FF"), [AL], TB),
    ([W,E,F], one("NUMS"), [AL], TB),
    ([J,I,O], one("NUMS"), [AL], TB),
    ([S,E,F], one("MEDIA"), [AL], TB),
    ([J,I,L], one("MEDIA"), [AL], TB),
    ([A,S,D], "CAPS\nWORD", [AL], TB),
    ([K,L,SEMI], "CAPS\nWORD", [AL], TB),
    ([G,H], k("⇄ Plain"), [AL], TB),
    ([G,H], k("⇄ Alpha"), [PL], TB),
    ([C,S], one("CHARS"), [AL], MTB),
    ([COMMA,L], one("CHARS"), [AL], MTB),
    ([V,S], one("Ctrl"), [AL], MTB),
    ([M,L], one("Ctrl"), [AL], MTB),
    ([V,C], one("Sup"), [AL], MTB),
    ([M,COMMA], one("Sup"), [AL], MTB),
    ([V,D], one("Shift"), [AL], MTB),
    ([M,K], one("Shift"), [AL], MTB),
    ([V,A], one("Alt"), [AL], MTB),
    ([M,SEMI], one("Alt"), [AL], MTB),
    ([V,D,S], one("Meh"), [AL], MTB),
    ([M,K,L], one("Meh"), [AL], MTB),

    # ==================== NAV ====================
    ([J,K,L], "SPC", [NR], MTB),
    ([S,D,F], "SPC", [NL], MTB),
    ([U,I,O], "Esc", [NR], TB),
    ([W,E,R], "Esc", [NL], TB),
    ([U,O], "Home", [NR], TB),
    ([W,R], "Home", [NL], TB),
    ([I,O], "PgUp", [NR], TB),
    ([E,R], "PgUp", [NL], TB),
    ([J,L], "End", [NR], TB),
    ([S,F], "End", [NL], TB),
    ([K,O], "PgDn", [NR], MTB),
    ([D,R], "PgDn", [NL], MTB),

    # ==================== NUMS ====================
    ([F,D], "2", [NU], MTB),
    ([J,K], "2", [NU], MTB),
    ([D,S], "4", [NU], MTB),
    ([K,L], "4", [NU], MTB),
    ([R,E], "7", [NU], MTB),
    ([U,I], "7", [NU], MTB),
    ([E,W], "9", [NU], MTB),
    ([I,O], "9", [NU], MTB),
    ([Q,W], "^", [NU], MTB),
    ([P,O], "^", [NU], MTB),
    ([A,S], "\\", [NU], MTB),
    ([SEMI,L], "\\", [NU], MTB),
    ([F,E], "/", [NU], MTB),
    ([J,I], "/", [NU], MTB),
    ([S,E], ".", [NU], MTB),
    ([L,I], ".", [NU], MTB),
    ([C,S], "=", [NU], MTB),
    ([COMMA,L], "=", [NU], MTB),
    ([W,D,F], "&", [NU], MTB),
    ([O,K,J], "&", [NU], MTB),
    ([S,E,R], "|", [NU], MTB),
    ([L,I,U], "|", [NU], MTB),
    ([S,F], "<", [NU], MTB),
    ([L,J], ">", [NU], MTB),
    ([W,F], "(", [NU], MTB),
    ([O,J], ")", [NU], MTB),
    ([A,F], "[", [NU], MTB),
    ([SEMI,J], "]", [NU], MTB),
    ([Q,F], "{", [NU], MTB),
    ([P,J], "}", [NU], MTB),
    ([D,V], "\"", [NU], MTB),
    ([K,M], "\"", [NU], MTB),
    ([S,V], "-", [NU], MTB),
    ([L,M], "-", [NU], MTB),
    ([A,V], "*", [NU], MTB),
    ([SEMI,M], "*", [NU], MTB),
    ([C,V], "#", [NU], MTB),
    ([COMMA,M], "#", [NU], MTB),
    ([W,D], "_", [NU], MTB),
    ([O,K], "_", [NU], MTB),
    ([G,W], "+", [NU], MTB),
    ([H,O], "+", [NU], MTB),
    ([G,S], "!", [NU], MTB),
    ([H,L], "!", [NU], MTB),
    ([G,A], "@", [NU], MTB),
    ([H,SEMI], "@", [NU], MTB),
    ([S,E,F], ";", [NU], TB),
    ([L,I,J], ";", [NU], TB),
    ([W,E,F], ":", [NU], TB),
    ([O,I,J], ":", [NU], TB),
    ([S,D,V], "%", [NU], MTB),
    ([L,K,M], "%", [NU], MTB),
    ([S,C,V], "$", [NU], MTB),
    ([L,COMMA,M], "$", [NU], MTB),
    ([S,D,F], "SPC", [NU], TB),
    ([L,K,J], "SPC", [NU], TB),

    # ==================== FF ====================
    ([F,D], "F2", [FFl], MTB),
    ([J,K], "F2", [FFl], MTB),
    ([D,S], "F4", [FFl], MTB),
    ([K,L], "F4", [FFl], MTB),
    ([R,E], "F7", [FFl], MTB),
    ([U,I], "F7", [FFl], MTB),
    ([E,W], "F9", [FFl], MTB),
    ([I,O], "F9", [FFl], MTB),

    # ==================== MODS ====================
    ([F,S], k("Ctrl+Shift","1-shot"), [MO], TB),
    ([J,L], k("Ctrl+Shift","1-shot"), [MO], TB),
    ([R,W], k("Sup+Alt","1-shot"), [MO], TB),
    ([U,O], k("Sup+Alt","1-shot"), [MO], TB),
    ([F,W], k("Alt+Shift","1-shot"), [MO], MTB),
    ([J,O], k("Alt+Shift","1-shot"), [MO], MTB),
    ([R,S], k("Sup+Ctrl","1-shot"), [MO], MTB),
    ([U,K], k("Sup+Ctrl","1-shot"), [MO], MTB),
    ([F,D,S], k("Meh","1-shot"), [MO], TB),
    ([J,K,L], k("Meh","1-shot"), [MO], TB),
]

combos = solve(combo_defs)

keymap = {
    "layout": {"cols_thumbs_notation": "133333 33333"},
    "draw_config": {"combo_w": 40, "combo_h": 30},
    "layers": {AL: alpha, PL: plain, NR: nav_r, NL: nav_l, NU: nums, FFl: ff,
               ME: media, GO: go, CH: chars, MO: mods},
    "combos": combos,
}

with open("/tmp/keymap.json", "w") as f:
    json.dump(keymap, f, indent=1, ensure_ascii=False)
print(f"wrote /tmp/keymap.json: {len(combos)} combos, {len(keymap['layers'])} layers")
for name, layer in keymap["layers"].items():
    assert len(layer) == 31, f"{name}: {len(layer)}"
print("ok: all layers 31 keys")
