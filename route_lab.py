"""
Route Lab: Route Optimization & Graph Theory (เวอร์ชันสำหรับ VS Code)
อัลกอริทึม: Dijkstra (เส้นทางสั้นสุด), Prim และ Kruskal (ต้นไม้ครอบคลุมน้อยสุด)
 
ติดตั้งไลบรารี (ครั้งเดียว) ใน Terminal:
    pip install networkx matplotlib
 
วิธีรัน:
  1) รันทั้งไฟล์:  python route_lab.py    (กราฟจะเปิดทีละหน้าต่าง ปิดหน้าต่างเพื่อไปต่อ)
  2) รันทีละส่วนใน VS Code: กด Shift+Enter ที่เส้น "# %%" (ต้องมีส่วนขยาย Python + Jupyter)
 
ข้อมูลเวลาเดินทางเป็นค่าสมมติ เพื่อสาธิตอัลกอริทึมเท่านั้น
"""
 
# %% [1] ตั้งค่า
import heapq, os, random, re, time
 
import matplotlib.font_manager as fm
from matplotlib.ft2font import FT2Font
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.widgets import Button, Slider
 
INF = float("inf")
SAVE_FIGS = True           # True = บันทึกภาพเป็น PNG ลงโฟลเดอร์ figures/ (เอาไปใส่รายงานได้)
FIG_DIR = os.path.join(os.getcwd(), "figures")
plt.rcParams["axes.unicode_minus"] = False
 
 
THAI_FONT = None
 
 
def font_has_thai(path):
    """ฟอนต์ต้องมีอักษรไทยครบ และแต่ละตัวต้องเป็นรูปคนละแบบ (กันฟอนต์ placeholder ที่ทุกตัวเป็นกล่องเดียวกัน)"""
    try:
        cmap = FT2Font(path).get_charmap()
        chars = "กขทมสยรอาิีัุ่้์"
        if not all(ord(c) in cmap for c in chars):
            return False
        return len({cmap[ord(c)] for c in chars}) == len(chars)
    except Exception:
        return False
 
 
def setup_thai_font():
    """เลือกฟอนต์ไทยของจริง: 1) ไฟล์ฟอนต์ของ Windows  2) ชื่อฟอนต์ที่รู้จัก  3) สแกนทั้งเครื่อง"""
    global THAI_FONT
    for path in [r"C:\Windows\Fonts\tahoma.ttf", r"C:\Windows\Fonts\LeelawUI.ttf"]:
        if os.path.exists(path) and font_has_thai(path):
            fm.fontManager.addfont(path)
            THAI_FONT = FT2Font(path).family_name
            plt.rcParams["font.family"] = THAI_FONT
            return True
    preferred = ["Tahoma", "Leelawadee UI", "Leelawadee", "Thonburi", "Sarabun", "TH Sarabun New",
                 "Noto Sans Thai", "Noto Sans Thai UI", "Loma", "Garuda", "Kinnari", "Waree"]
    fonts = fm.fontManager.ttflist
    for cand in preferred:
        for f in fonts:
            if f.name == cand and font_has_thai(f.fname):
                THAI_FONT = cand
                plt.rcParams["font.family"] = cand
                return True
    for f in fonts:
        if font_has_thai(f.fname):
            THAI_FONT = f.name
            plt.rcParams["font.family"] = f.name
            return True
    return False
 
 
USE_THAI = setup_thai_font()
if USE_THAI:
    plt.rcParams["font.sans-serif"] = [THAI_FONT] + list(plt.rcParams["font.sans-serif"])
print("แสดงชื่อภาษาไทย:", USE_THAI, "| ฟอนต์:", THAI_FONT)
 
# %% [2] สร้างกราฟ (แผนที่จำลอง)
# ชื่อจุด (key ในโค้ด) -> (ชื่อไทย, x, y)
PLACES = {
    "Chatuchak":        ("จตุจักร",     440, 60),
    "Ari":              ("อารีย์",       250, 100),
    "Victory Monument": ("อนุสาวรีย์",   160, 210),
    "Ratchathewi":      ("ราชเทวี",     300, 250),
    "Siam":             ("สยาม",        400, 300),
    "Pratunam":         ("ประตูน้ำ",     500, 220),
    "Asok":             ("อโศก",        600, 320),
    "Phrom Phong":      ("พร้อมพงษ์",   690, 400),
    "Si Lom":           ("สีลม",        340, 430),
    "Saphan Taksin":    ("สะพานตากสิน", 220, 470),
    "Lat Phrao":        ("ลาดพร้าว",    620, 110),
    "Ratchada":         ("รัชดา",       700, 210),
}
ROADS = [  # (จุด, จุด, เวลา นาที)
    ("Chatuchak", "Ari", 8), ("Chatuchak", "Lat Phrao", 10), ("Chatuchak", "Pratunam", 16),
    ("Ari", "Victory Monument", 7), ("Ari", "Ratchathewi", 12), ("Victory Monument", "Ratchathewi", 9),
    ("Ratchathewi", "Siam", 6), ("Ratchathewi", "Pratunam", 9), ("Siam", "Pratunam", 8),
    ("Siam", "Asok", 11), ("Pratunam", "Asok", 10), ("Siam", "Si Lom", 12), ("Si Lom", "Saphan Taksin", 9),
    ("Asok", "Phrom Phong", 7), ("Lat Phrao", "Ratchada", 9), ("Ratchada", "Asok", 12),
    ("Victory Monument", "Saphan Taksin", 20), ("Si Lom", "Phrom Phong", 22),
]
 
G = nx.Graph()
G.add_weighted_edges_from(ROADS)                         # ไม่มีทิศทาง น้ำหนัก = เวลา (นาที)
BKK_POS = {k: (x, -y) for k, (_, x, y) in PLACES.items()}    # กลับแกน y ให้เหมือนหน้าจอ
POS = BKK_POS
 
 
def label(n):
    return PLACES[n][0] if (USE_THAI and n in PLACES) else n
 
 
print(f"จุด |V| = {G.number_of_nodes()}   เส้น |E| = {G.number_of_edges()}   เชื่อมกัน = {nx.is_connected(G)}")
 
 
 
# %% [3] ฟังก์ชันวาดกราฟ
def plain_title(t):
    """โหมดภาษาอังกฤษ: แปลคำไทยในหัวข้อกราฟเป็นอังกฤษ แล้วตัดอักษรไทยที่เหลือทิ้ง"""
    for th, en in [("ต้นไม้เส้นทางสั้นสุด", "Shortest-path tree"), ("น้ำหนักรวม", "total weight"),
                   ("ไม่พบเส้นทาง", "No path"), ("ขั้นที่", "step"), ("นาที", "min")]:
        t = t.replace(th, en)
    return re.sub(r"\s+", " ", re.sub(r"[\u0E00-\u0E7F]+", "", t)).strip()
 
 
PALETTE = ["#F2B01E", "#6C9CFF", "#2ED08C", "#FF7B5C", "#C792EA", "#8EDCE6", "#F4A6C0", "#B5C99A"]
 
 
def draw_on(ax, G, pos=BKK_POS, path_edges=(), tree_edges=(), node_color=None, extra=None, title="",
            focus=(), focus_color="#F2B01E"):
    # networkx ตั้ง font_family="sans-serif" เป็นค่าเริ่มต้น (ทับ rcParams) จึงต้องส่งฟอนต์ไทยเข้าไปตรง ๆ
    ff = THAI_FONT if (USE_THAI and THAI_FONT) else "sans-serif"
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#A3B4BD", width=2)
    if tree_edges:
        nx.draw_networkx_edges(G, pos, edgelist=list(tree_edges), ax=ax, edge_color="#2D6BDB", width=4)
    if path_edges:
        nx.draw_networkx_edges(G, pos, edgelist=list(path_edges), ax=ax, edge_color="#0B9A62", width=7)
    if focus:
        nx.draw_networkx_edges(G, pos, edgelist=list(focus), ax=ax, edge_color=focus_color, width=7)
    colors = [(node_color or {}).get(n, "white") for n in G]
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=colors, edgecolors="#142A33",
                           linewidths=2.5, node_size=420)
    lp = {n: (x, y - 24 if pos is BKK_POS else y - 0.09) for n, (x, y) in pos.items()}
    names = {n: label(n) + (f"\n[{extra[n]}]" if extra and n in extra else "") for n in G}
    nx.draw_networkx_labels(G, lp, labels=names, font_size=9, ax=ax, font_family=ff)
    nx.draw_networkx_edge_labels(G, pos, edge_labels=nx.get_edge_attributes(G, "weight"),
                                 font_size=8, ax=ax, rotate=False, font_family=ff,
                                 bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="#CBD6DC"))
    ax.set_title(title if USE_THAI else plain_title(title))
    ax.axis("off")
 
 
 
def draw(G, fname=None, title="", figsize=(11, 7), **kw):
    fig, ax = plt.subplots(figsize=figsize)
    draw_on(ax, G, title=title, **kw)
    fig.tight_layout()
    if SAVE_FIGS and fname:
        os.makedirs(FIG_DIR, exist_ok=True)
        fig.savefig(os.path.join(FIG_DIR, fname + ".png"), dpi=150)
    plt.show()
 
 
draw(G, "00_map", title="แผนที่จำลอง (น้ำหนักเส้น = เวลา นาที)" if USE_THAI else "Map (edge weight = minutes)")
 
 
# %% [4] อัลกอริทึม (เขียนเอง): Dijkstra, Prim, Kruskal
def dijkstra(G, s, t=None, record=False):
    """เส้นทางสั้นที่สุดจาก s  คืน (dist, prev, steps)"""
    dist = {n: INF for n in G}
    dist[s] = 0
    prev, done, steps = {}, set(), []
    pq = [(0, str(s), s)]
 
    def snap(msg, cur):
        if record:
            steps.append(dict(msg=msg, cur=cur, done=set(done), dist=dict(dist), prev=dict(prev)))
 
    snap(f"เริ่มที่ {label(s)} ระยะ 0 ส่วนจุดอื่นเป็น ∞", s)
    while pq:
        d, _, u = heapq.heappop(pq)
        if u in done:
            continue
        done.add(u)
        snap(f"ล็อก {label(u)} (ระยะ {d} นาที)", u)
        if u == t:
            break
        for v, data in G[u].items():
            nd = d + data["weight"]
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, str(v), v))
                snap(f"ผ่าน {label(u)} ไป {label(v)} ได้ {nd} นาที ดีกว่าเดิม -> อัปเดต", u)
    return dist, prev, steps
 
 
def path_from(prev, s, t):
    if t != s and t not in prev:
        return None
    p = [t]
    while p[-1] != s:
        p.append(prev[p[-1]])
    return p[::-1]
 
 
def path_edges(p):
    return list(zip(p, p[1:]))
 
 
def path_minutes(G, p):
    return sum(G[a][b]["weight"] for a, b in path_edges(p))
 
 
def spt_weight(G, prev):
    """น้ำหนักรวมของ 'ต้นไม้เส้นทางสั้นที่สุด' ที่ Dijkstra สร้าง (เส้น prev ทั้งหมด)"""
    return sum(G[v][u]["weight"] for v, u in prev.items())
 
 
def prim(G, s, record=False):
    """MST โดยโตจากจุด s  คืน (เส้นในต้นไม้, น้ำหนักรวม, เซตจุดที่ต่อถึง, steps)"""
    in_tree, tree, total, steps = {s}, [], 0, []
 
    def snap(msg, focus=None):
        if record:
            steps.append(dict(msg=msg, tree=list(tree), nodes=set(in_tree), focus=focus))
 
    snap(f"เริ่มต้นต้นไม้ที่ {label(s)}")
    pq = [(d["weight"], str(s), s, v) for v, d in G[s].items()]
    heapq.heapify(pq)
    while pq:
        w, _, u, v = heapq.heappop(pq)
        if v in in_tree:
            continue
        in_tree.add(v)
        tree.append((u, v))
        total += w
        snap(f"เลือกเส้นที่ถูกที่สุดที่ออกจากต้นไม้: {label(u)}–{label(v)} ({w}) ต้นทุนรวม {total}", (u, v))
        for x, d in G[v].items():
            if x not in in_tree:
                heapq.heappush(pq, (d["weight"], str(v), v, x))
    return tree, total, in_tree, steps
 
 
class DSU:
    """Union-Find: ใช้ตรวจว่าสองจุดอยู่ในกลุ่มเดียวกันแล้วหรือยัง"""
 
    def __init__(self, items):
        self.p = {x: x for x in items}
        self.r = {x: 0 for x in items}
 
    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x
 
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.r[ra] < self.r[rb]:
            ra, rb = rb, ra
        self.p[rb] = ra
        if self.r[ra] == self.r[rb]:
            self.r[ra] += 1
        return True
 
 
def kruskal(G, record=False):
    """MST โดยเรียงเส้นจากถูกไปแพง แล้วเลือกเส้นที่ไม่ทำให้เกิดวงจร
    ถ้ากราฟไม่เชื่อมกันจะได้ 'ป่า' (หนึ่งต้นไม้ต่อหนึ่งส่วนที่เชื่อมกัน)
    คืน (เส้นในต้นไม้, น้ำหนักรวม, steps)"""
    edges = sorted((d["weight"], str(u), str(v), u, v) for u, v, d in G.edges(data=True))
    dsu = DSU(G.nodes)
    tree, total, steps = [], 0, []
 
    def comp_map():
        roots = {}
        return {n: roots.setdefault(dsu.find(n), len(roots)) for n in G}
 
    if record:
        steps.append(dict(msg=f"เรียงเส้นจากถูกไปแพง ทั้งหมด {len(edges)} เส้น เริ่มต้นทุกจุดเป็นกลุ่มของตัวเอง",
                          tree=[], focus=None, ok=None, comp=comp_map()))
    for w, _, _, u, v in edges:
        ok = dsu.union(u, v)
        if ok:
            tree.append((u, v))
            total += w
        if record:
            msg = (f"เลือกเส้น {label(u)}–{label(v)} ({w}) เพราะเชื่อมสองกลุ่มที่ยังแยกกัน ต้นทุนรวม {total}" if ok
                   else f"ข้ามเส้น {label(u)}–{label(v)} ({w}) เพราะสองจุดนี้อยู่กลุ่มเดียวกันแล้ว (จะเกิดวงจร)")
            steps.append(dict(msg=msg, tree=list(tree), focus=(u, v), ok=ok, comp=comp_map()))
    return tree, total, steps
 
 
def random_connected_graph(n, extra=None, wmax=20, seed=None):
    rng = random.Random(seed)
    g = nx.Graph()
    g.add_nodes_from(range(n))
    for v in range(1, n):
        g.add_edge(v, rng.randrange(v), weight=rng.randint(1, wmax))
    for _ in range(extra if extra is not None else n):
        a, b = rng.sample(range(n), 2)
        if not g.has_edge(a, b):
            g.add_edge(a, b, weight=rng.randint(1, wmax))
    return g
 
 
 
 
# %% [5] Dijkstra: เส้นทางที่ใช้เวลาน้อยที่สุด  เวลา O((V+E) log V)
S, T = "Victory Monument", "Phrom Phong"
dist, prev, _ = dijkstra(G, S, T)
p_dij = path_from(prev, S, T)
print("Dijkstra:", " -> ".join(p_dij), f"| {dist[T]} นาที ({len(p_dij) - 1} เส้น)")
draw(G, "01_dijkstra", path_edges=path_edges(p_dij), title=f"Dijkstra: {dist[T]} นาที")
 
# %% [6] Prim: ต้นไม้ครอบคลุมน้อยที่สุด (โตจากจุดเริ่มต้น)  เวลา O(E log V)
tree_p, total_p, covered, _ = prim(G, "Siam")
print(f"Prim: ใช้ {len(tree_p)} เส้น น้ำหนักรวม {total_p} นาที (ครอบคลุม {len(covered)}/{G.number_of_nodes()} จุด)")
draw(G, "02_prim_mst", path_edges=tree_p, title=f"Prim (MST): น้ำหนักรวม {total_p}")
 
# %% [7] Kruskal: เรียงเส้นจากถูกไปแพง เลือกเส้นที่ไม่เกิดวงจร  เวลา O(E log E)
tree_k, total_k, steps_k = kruskal(G, record=True)
print(f"Kruskal: ใช้ {len(tree_k)} เส้น น้ำหนักรวม {total_k} นาที")
for i, st in enumerate(steps_k, 1):
    print(f"  {i:2d}. {st['msg']}")
draw(G, "03_kruskal_mst", path_edges=tree_k, title=f"Kruskal (MST): น้ำหนักรวม {total_k}")
 
# %% [8] เปรียบเทียบผลลัพธ์
print()
print("1) Prim เทียบกับ Kruskal")
print(f"   Prim = {total_p}, Kruskal = {total_k}  ->  {'เท่ากัน' if total_p == total_k else 'ไม่เท่ากัน (ตรวจสอบโค้ด)'}")
same = {frozenset(e) for e in tree_p} == {frozenset(e) for e in tree_k}
print("   เลือกเส้นชุดเดียวกัน:", same, "(ถ้าเป็น False แปลว่ามีเส้นน้ำหนักเท่ากันให้เลือกได้หลายแบบ)")
 
print("2) Dijkstra เทียบกับ Prim (เริ่มที่ Siam)")
_, prev_all, _ = dijkstra(G, "Siam")
w_spt = spt_weight(G, prev_all)
print(f"   ต้นไม้เส้นทางสั้นสุด (Dijkstra) น้ำหนักรวม = {w_spt}")
print(f"   ต้นไม้ครอบคลุมน้อยสุด (Prim)    น้ำหนักรวม = {total_p}")
print(f"   ส่วนต่าง = {w_spt - total_p}  (ต้นไม้เส้นทางสั้นสุดหนักกว่าหรือเท่ากับ MST เสมอ)")
fig, ax = plt.subplots(1, 2, figsize=(15, 6))
draw_on(ax[0], G, path_edges=[(v, u) for v, u in prev_all.items()], title=f"ต้นไม้เส้นทางสั้นสุด ({w_spt})")
draw_on(ax[1], G, path_edges=tree_p, title=f"MST ({total_p})")
fig.tight_layout()
if SAVE_FIGS:
    os.makedirs(FIG_DIR, exist_ok=True)
    fig.savefig(os.path.join(FIG_DIR, "04_spt_vs_mst.png"), dpi=150)
plt.show()
 
 
# %% [9] ดู Dijkstra ทีละขั้น (หน้าต่างโต้ตอบ: เลื่อนแถบด้านล่าง)
# %% [9] ดู Dijkstra แบบ Animation
# %% [9] Animation เส้นทางสั้นที่สุด
# %% [9] Dijkstra Animation: เส้นทางค่อย ๆ วิ่งทีละจุด

def step_viewer(G, s, t):

    # ---------------------------------------------------------
    # หาเส้นทางสั้นที่สุดด้วย Dijkstra
    # ---------------------------------------------------------
    dist, prev, steps = dijkstra(G, s, t, record=True)

    p = path_from(prev, s, t)

    if p is None:
        print("ไม่พบเส้นทาง")
        return

    # เส้นทาง เช่น
    # [Victory Monument, Ratchathewi, Siam, Asok, Phrom Phong]
    edges = path_edges(p)

    # ---------------------------------------------------------
    # สร้างหน้าต่าง
    # ---------------------------------------------------------
    fig, ax = plt.subplots(figsize=(11, 7.6))

    fig.subplots_adjust(bottom=0.25)

    # ---------------------------------------------------------
    # ตัวแปรควบคุม Animation
    # ---------------------------------------------------------
    current_edge = [0]
    progress = [0.0]
    playing = [False]
    timer = [None]

    # ---------------------------------------------------------
    # Slider เลือกจุด
    # ---------------------------------------------------------
    ax_slider = fig.add_axes([0.20, 0.12, 0.60, 0.035])

    slider = Slider(
        ax_slider,
        "จุด",
        1,
        len(edges) + 1,
        valinit=1,
        valstep=1
    )

    # ---------------------------------------------------------
    # Slider ความเร็ว
    # ---------------------------------------------------------
    ax_speed = fig.add_axes([0.20, 0.18, 0.60, 0.025])

    speed = Slider(
        ax_speed,
        "ความเร็ว",
        1,
        10,
        valinit=5,
        valstep=1
    )

    # ---------------------------------------------------------
    # ปุ่ม
    # ---------------------------------------------------------
    ax_play = fig.add_axes([0.20, 0.04, 0.12, 0.055])
    ax_next = fig.add_axes([0.34, 0.04, 0.12, 0.055])
    ax_back = fig.add_axes([0.48, 0.04, 0.12, 0.055])
    ax_reset = fig.add_axes([0.62, 0.04, 0.12, 0.055])

    btn_play = Button(ax_play, "▶ เล่น")
    btn_next = Button(ax_next, "ถัดไป")
    btn_back = Button(ax_back, "ย้อน")
    btn_reset = Button(ax_reset, "รีเซ็ต")

    # ---------------------------------------------------------
    # ฟังก์ชันวาดภาพแต่ละ Frame
    # ---------------------------------------------------------
    def draw_frame():

        ax.clear()

        # -----------------------------------------------------
        # เส้นที่วาดเสร็จแล้ว
        # -----------------------------------------------------
        completed_edges = edges[:current_edge[0]]

        # -----------------------------------------------------
        # สีของจุด
        # -----------------------------------------------------
        node_colors = {
            n: "white"
            for n in G.nodes
        }

        # จุดที่ผ่านไปแล้ว
        for n in p[:current_edge[0] + 1]:
            node_colors[n] = "#F2B01E"

        # จุดปัจจุบัน
        if current_edge[0] < len(edges):

            u, v = edges[current_edge[0]]

            node_colors[u] = "#F2B01E"
            node_colors[v] = "#6C9CFF"

        # -----------------------------------------------------
        # วาดกราฟ
        # -----------------------------------------------------
        draw_on(
            ax,
            G,

            # เส้นทางที่วาดเสร็จแล้ว
            path_edges=completed_edges,

            node_color=node_colors,

            title=(
                f"Dijkstra: {label(s)} → {label(t)}\n"
                f"เวลารวม {dist[t]} นาที"
            )
        )

        # -----------------------------------------------------
        # วาด "เส้นที่กำลังวิ่ง"
        # -----------------------------------------------------
        if current_edge[0] < len(edges):

            u, v = edges[current_edge[0]]

            x1, y1 = BKK_POS[u]
            x2, y2 = BKK_POS[v]

            # ตำแหน่งปลายเส้นในขณะนี้
            x = x1 + (x2 - x1) * progress[0]
            y = y1 + (y2 - y1) * progress[0]

            ax.plot(
                [x1, x],
                [y1, y],
                color="#0B9A62",
                linewidth=7,
                solid_capstyle="round",
                zorder=10
            )

            # -------------------------------------------------
            # แสดงว่าเส้นไหนกำลังวิ่ง
            # -------------------------------------------------
            ax.text(
                0.5,
                1.02,
                f"{label(u)} → {label(v)}",
                transform=ax.transAxes,
                ha="center",
                va="bottom",
                fontsize=13,
                fontweight="bold"
            )

        else:

            ax.text(
                0.5,
                1.02,
                "✓ ถึงจุดหมายแล้ว",
                transform=ax.transAxes,
                ha="center",
                va="bottom",
                fontsize=13,
                fontweight="bold"
            )

        fig.canvas.draw_idle()

    # ---------------------------------------------------------
    # หยุด Animation
    # ---------------------------------------------------------
    def stop_animation():

        playing[0] = False

        if timer[0] is not None:

            timer[0].stop()
            timer[0] = None

        btn_play.label.set_text("▶ เล่น")

        fig.canvas.draw_idle()

    # ---------------------------------------------------------
    # Animation
    # ---------------------------------------------------------
    def animation_tick():

        if not playing[0]:
            return

        # ความเร็ว
        progress[0] += 0.025 * speed.val

        # -----------------------------------------------------
        # ยังวาดเส้นไม่ถึงปลายทาง
        # -----------------------------------------------------
        if progress[0] < 1.0:

            draw_frame()

        # -----------------------------------------------------
        # วาดเส้นนี้เสร็จแล้ว
        # -----------------------------------------------------
        else:

            progress[0] = 0.0

            current_edge[0] += 1

            # -------------------------------------------------
            # ถึงปลายทาง
            # -------------------------------------------------
            if current_edge[0] >= len(edges):

                current_edge[0] = len(edges)

                draw_frame()

                stop_animation()

                return

            draw_frame()

    # ---------------------------------------------------------
    # ปุ่ม ▶ เล่น
    # ---------------------------------------------------------
    def play(event):

        if playing[0]:

            stop_animation()
            return

        # ถ้าจบแล้ว ให้เริ่มใหม่
        if current_edge[0] >= len(edges):

            current_edge[0] = 0
            progress[0] = 0.0

        playing[0] = True

        btn_play.label.set_text("⏸ หยุด")

        timer[0] = fig.canvas.new_timer(
            interval=40
        )

        timer[0].add_callback(animation_tick)

        timer[0].start()

    # ---------------------------------------------------------
    # ปุ่ม ถัดไป
    # ---------------------------------------------------------
    def next_step(event):

        stop_animation()

        if current_edge[0] < len(edges):

            current_edge[0] += 1
            progress[0] = 0.0

            slider.eventson = False
            slider.set_val(current_edge[0] + 1)
            slider.eventson = True

            draw_frame()

    # ---------------------------------------------------------
    # ปุ่ม ย้อน
    # ---------------------------------------------------------
    def back_step(event):

        stop_animation()

        if current_edge[0] > 0:

            current_edge[0] -= 1
            progress[0] = 0.0

            slider.eventson = False
            slider.set_val(current_edge[0] + 1)
            slider.eventson = True

            draw_frame()

    # ---------------------------------------------------------
    # ปุ่ม รีเซ็ต
    # ---------------------------------------------------------
    def reset(event):

        stop_animation()

        current_edge[0] = 0
        progress[0] = 0.0

        slider.eventson = False
        slider.set_val(1)
        slider.eventson = True

        draw_frame()

    # ---------------------------------------------------------
    # Slider จุด
    # ---------------------------------------------------------
    def slider_change(val):

        stop_animation()

        current_edge[0] = int(val) - 1
        progress[0] = 0.0

        draw_frame()

    # ---------------------------------------------------------
    # เชื่อมปุ่ม
    # ---------------------------------------------------------
    btn_play.on_clicked(play)
    btn_next.on_clicked(next_step)
    btn_back.on_clicked(back_step)
    btn_reset.on_clicked(reset)

    slider.on_changed(slider_change)

    # ---------------------------------------------------------
    # เริ่มต้น
    # ---------------------------------------------------------
    draw_frame()

    plt.show()


step_viewer(G, S, T)
 
 
# %% [10] ทดสอบความถูกต้อง: เทียบกับ networkx และกรณีพิเศษ
def forest_weight(g):
    return nx.minimum_spanning_tree(g).size(weight="weight")     # กราฟไม่เชื่อมกัน networkx คืนป่า
 
 
def run_tests(G_bkk):
    rows = []
 
    def add(name, ok):
        rows.append({"รายการทดสอบ": name, "ผล": "ผ่าน" if ok else "ไม่ผ่าน"})
 
    ok_d = ok_p = ok_k = ok_pk = ok_spt = True
    for trial in range(300):
        n = random.randint(3, 25)
        g = random_connected_graph(n, seed=trial)
        s, t = random.sample(list(g), 2)
        d, pv, _ = dijkstra(g, s, t)
        ok_d &= d[t] == nx.dijkstra_path_length(g, s, t)
        ref = forest_weight(g)
        pt = prim(g, s)[1]
        kt = kruskal(g)[1]
        ok_p &= pt == ref
        ok_k &= kt == ref
        ok_pk &= pt == kt
        _, pv_all, _ = dijkstra(g, s)
        ok_spt &= spt_weight(g, pv_all) >= ref
    add("กราฟสุ่ม 300 ชุด: Dijkstra ตรงกับ networkx", ok_d)
    add("กราฟสุ่ม 300 ชุด: Prim ตรงกับ networkx (MST)", ok_p)
    add("กราฟสุ่ม 300 ชุด: Kruskal ตรงกับ networkx (MST)", ok_k)
    add("กราฟสุ่ม 300 ชุด: Prim และ Kruskal ได้น้ำหนักรวมเท่ากัน", ok_pk)
    add("กราฟสุ่ม 300 ชุด: ต้นไม้เส้นทางสั้นสุด (Dijkstra) หนักกว่าหรือเท่ากับ MST", ok_spt)
 
    ok_same = True
    for k in range(100):                       # น้ำหนักไม่ซ้ำกัน -> MST มีได้ชุดเดียว
        g = random_connected_graph(12, extra=15, seed=5000 + k)
        ws = random.sample(range(1, 1000), g.number_of_edges())
        for (a, b), w in zip(list(g.edges), ws):
            g[a][b]["weight"] = w
        te = {frozenset(e) for e in prim(g, 0)[0]}
        ke = {frozenset(e) for e in kruskal(g)[0]}
        ok_same &= te == ke
    add("น้ำหนักเส้นไม่ซ้ำกัน: Prim และ Kruskal ได้ต้นไม้ชุดเดียวกัน (100 กราฟ)", ok_same)
 
    H = G_bkk.copy()
    H.remove_edges_from([("Chatuchak", "Lat Phrao"), ("Chatuchak", "Pratunam"), ("Ratchada", "Asok")])
    d, pv, _ = dijkstra(H, "Chatuchak", "Ratchada")
    add("กราฟไม่เชื่อมกัน: Dijkstra ไปไม่ถึง (ระยะ ∞)",
        d["Ratchada"] == INF and path_from(pv, "Chatuchak", "Ratchada") is None)
    comp = nx.node_connected_component(H, "Chatuchak")
    _, tot_p, cov, _ = prim(H, "Chatuchak")
    add("กราฟไม่เชื่อมกัน: Prim ครอบคลุมเฉพาะส่วนที่ต่อถึง และน้ำหนักถูกต้อง",
        cov == comp and tot_p == forest_weight(H.subgraph(comp)))
    tree_k, tot_k, _ = kruskal(H)
    add("กราฟไม่เชื่อมกัน: Kruskal ได้ป่า (จำนวนเส้น = V - จำนวนส่วนที่เชื่อมกัน)",
        len(tree_k) == H.number_of_nodes() - nx.number_connected_components(H) and tot_k == forest_weight(H))
 
    d, pv, _ = dijkstra(G_bkk, "Siam", "Siam")
    add("จุดเริ่ม = จุดปลาย: ระยะ 0 และมีจุดเดียว", d["Siam"] == 0 and path_from(pv, "Siam", "Siam") == ["Siam"])
 
    I = G_bkk.copy()
    I.add_node("Island")
    add("จุดโดดเดี่ยว: Dijkstra ไปไม่ถึง", dijkstra(I, "Siam", "Island")[0]["Island"] == INF)
    add("จุดโดดเดี่ยว: Prim จากจุดนั้นได้ต้นไม้ว่าง (0 เส้น)", prim(I, "Island")[0] == [])
 
    E = nx.Graph()
    E.add_weighted_edges_from([(u, v, 4) for u, v in nx.petersen_graph().edges])
    add("น้ำหนักเท่ากันหมด: MST หนัก (V-1)×น้ำหนัก ทั้ง Prim และ Kruskal",
        prim(E, 0)[1] == 4 * 9 and kruskal(E)[1] == 4 * 9)
 
    Ln = nx.path_graph(6)
    nx.set_edge_attributes(Ln, 3, "weight")
    add("กราฟเส้นตรง: Prim และ Kruskal ได้ทุกเส้น และ Dijkstra ได้ทางตรง",
        prim(Ln, 0)[1] == 15 and kruskal(Ln)[1] == 15 and path_from(dijkstra(Ln, 0, 5)[1], 0, 5) == [0, 1, 2, 3, 4, 5])
    return rows
 
 
def timeit(f, repeat=3):
    best = INF
    for _ in range(repeat):
        t0 = time.perf_counter()
        f()
        best = min(best, time.perf_counter() - t0)
    return best
 
 
def run_benchmark():
    sizes = [200, 400, 800, 1600, 3200]
    td, tp, tk = [], [], []
    for n in sizes:
        g = random_connected_graph(n, extra=2 * n, seed=n)
        td.append(timeit(lambda: dijkstra(g, 0)))
        tp.append(timeit(lambda: prim(g, 0)))
        tk.append(timeit(lambda: kruskal(g)))
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(sizes, td, "o-", label="Dijkstra")
    ax.plot(sizes, tp, "s-", label="Prim")
    ax.plot(sizes, tk, "^-", label="Kruskal")
    ax.set_xlabel("V (nodes), E = 3V")
    ax.set_ylabel("seconds")
    ax.legend()
    ax.grid(alpha=.3)
    ax.set_title("Runtime vs graph size")
    fig.tight_layout()
    return fig
 
 
 
 
results = run_tests(G)
for r in results:
    print(("ผ่าน  " if r["ผล"] == "ผ่าน" else "ไม่ผ่าน  ") + r["รายการทดสอบ"])
assert all(r["ผล"] == "ผ่าน" for r in results), "มีรายการที่ไม่ผ่าน"
print(f"ผ่านครบทั้ง {len(results)} รายการ")
 
# %% [11] วัดความเร็วจริง
fig = run_benchmark()
if SAVE_FIGS:
    os.makedirs(FIG_DIR, exist_ok=True)
    fig.savefig(os.path.join(FIG_DIR, "05_runtime.png"), dpi=150)
plt.show()
print("เสร็จสิ้น")