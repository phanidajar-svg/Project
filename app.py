"""
Route Lab (Streamlit): Route Optimization & Graph Theory
อัลกอริทึม: Dijkstra (เส้นทางสั้นสุด), Prim และ Kruskal (ต้นไม้ครอบคลุมน้อยสุด)
 
ติดตั้ง (ครั้งเดียว) ใน Terminal ของ VS Code:
    pip install streamlit networkx matplotlib
 
รัน:
    streamlit run app.py
(ถ้าไม่เจอคำสั่ง streamlit ให้ใช้:  python -m streamlit run app.py)
 
เบราว์เซอร์จะเปิดหน้าเว็บที่ http://localhost:8501 อัตโนมัติ
หยุดโปรแกรมด้วย Ctrl+C ใน Terminal
 
ข้อมูลเวลาเดินทางเป็นค่าสมมติ เพื่อสาธิตอัลกอริทึมเท่านั้น
"""
import heapq
import os
import re
import random
import time
 
import matplotlib.font_manager as fm
from matplotlib.ft2font import FT2Font
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import streamlit as st
 
INF = float("inf")
plt.rcParams["axes.unicode_minus"] = False
st.set_page_config(page_title="Route Lab", page_icon="🗺️", layout="wide")
 
 
# ----------------------------------------------------------------------------
# ฟอนต์ไทย (Windows: Tahoma / Mac: Thonburi) ถ้าไม่มีจะใช้ชื่ออังกฤษ
# ----------------------------------------------------------------------------
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
 
# ----------------------------------------------------------------------------
# ข้อมูลแผนที่จำลอง
# ----------------------------------------------------------------------------
PLACES = {  # key -> (ชื่อไทย, x, y)
    "Chatuchak": ("จตุจักร", 440, 60), "Ari": ("อารีย์", 250, 100),
    "Victory Monument": ("อนุสาวรีย์", 160, 210), "Ratchathewi": ("ราชเทวี", 300, 250),
    "Siam": ("สยาม", 400, 300), "Pratunam": ("ประตูน้ำ", 500, 220),
    "Asok": ("อโศก", 600, 320), "Phrom Phong": ("พร้อมพงษ์", 690, 400),
    "Si Lom": ("สีลม", 340, 430), "Saphan Taksin": ("สะพานตากสิน", 220, 470),
    "Lat Phrao": ("ลาดพร้าว", 620, 110), "Ratchada": ("รัชดา", 700, 210),
}
ROADS = [
    ("Chatuchak", "Ari", 8), ("Chatuchak", "Lat Phrao", 10), ("Chatuchak", "Pratunam", 16),
    ("Ari", "Victory Monument", 7), ("Ari", "Ratchathewi", 12), ("Victory Monument", "Ratchathewi", 9),
    ("Ratchathewi", "Siam", 6), ("Ratchathewi", "Pratunam", 9), ("Siam", "Pratunam", 8),
    ("Siam", "Asok", 11), ("Pratunam", "Asok", 10), ("Siam", "Si Lom", 12), ("Si Lom", "Saphan Taksin", 9),
    ("Asok", "Phrom Phong", 7), ("Lat Phrao", "Ratchada", 9), ("Ratchada", "Asok", 12),
    ("Victory Monument", "Saphan Taksin", 20), ("Si Lom", "Phrom Phong", 22),
]
BKK_POS = {k: (x, -y) for k, (_, x, y) in PLACES.items()}
 
 
def label(n):
    return PLACES[n][0] if (USE_THAI and n in PLACES) else str(n)
 
 
# ----------------------------------------------------------------------------
# อัลกอริทึม (เขียนเอง)
# ----------------------------------------------------------------------------
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
 
 
# ----------------------------------------------------------------------------
# วาดกราฟ
# ----------------------------------------------------------------------------
def plain_title(t):
    """โหมดภาษาอังกฤษ: แปลคำไทยในหัวข้อกราฟเป็นอังกฤษ แล้วตัดอักษรไทยที่เหลือทิ้ง"""
    for th, en in [("ต้นไม้เส้นทางสั้นสุด", "Shortest-path tree"), ("น้ำหนักรวม", "total weight"),
                   ("ไม่พบเส้นทาง", "No path"), ("ขั้นที่", "step"), ("นาที", "min")]:
        t = t.replace(th, en)
    return re.sub(r"\s+", " ", re.sub(r"[\u0E00-\u0E7F]+", "", t)).strip()
 
 
PALETTE = ["#F2B01E", "#6C9CFF", "#2ED08C", "#FF7B5C", "#C792EA", "#8EDCE6", "#F4A6C0", "#B5C99A"]
 
 
def draw_on(ax, G, pos, path_edges=(), tree_edges=(), node_color=None, extra=None, title="",
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
 
 
def show_graph(G, pos, figsize=(10, 6.4), **kw):
    fig, ax = plt.subplots(figsize=figsize)
    draw_on(ax, G, pos, **kw)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
 
 
# ----------------------------------------------------------------------------
# ชุดทดสอบความถูกต้อง
# ----------------------------------------------------------------------------
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
    return pd.DataFrame(rows)
 
 
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
 
 
# ----------------------------------------------------------------------------
# หน้าเว็บ
# ----------------------------------------------------------------------------
st.title("🗺️ Route Lab")
st.caption("ทดลองหาเส้นทางและโครงข่ายที่เหมาะสมที่สุดด้วยทฤษฎีกราฟ: Dijkstra, Prim, Kruskal "
           "(เวลาเดินทางเป็นค่าสมมติเพื่อสาธิต)")
 
# --- แถบด้านข้าง ---
st.sidebar.header("ตั้งค่า")
if USE_THAI:
    st.sidebar.caption(f"ฟอนต์กราฟ: {THAI_FONT}")
    if st.sidebar.checkbox("แสดงชื่อจุดเป็นภาษาอังกฤษ", value=False,
                           help="ใช้ถ้าตัวอักษรไทยในกราฟแสดงเป็นกล่อง"):
        USE_THAI = False
else:
    st.sidebar.info("ไม่พบฟอนต์ไทยในเครื่อง จึงแสดงชื่อจุดเป็นภาษาอังกฤษ")
src = st.sidebar.radio("แหล่งข้อมูลกราฟ", ["แผนที่กรุงเทพ (จำลอง)", "กราฟสุ่ม"])
is_bkk = src.startswith("แผนที่")
n_rand, seed = 9, 1
if not is_bkk:
    n_rand = st.sidebar.slider("จำนวนจุด", 5, 15, 9)
    seed = int(st.sidebar.number_input("seed (เปลี่ยนเพื่อสุ่มใหม่)", 0, 9999, 1))
algo = st.sidebar.radio("อัลกอริทึม", ["Dijkstra", "Prim", "Kruskal"])
 
# --- ตารางเส้นเชื่อม (แก้ไขได้) ---
if is_bkk:
    base_nodes = list(PLACES)
    df0 = pd.DataFrame(ROADS, columns=["from", "to", "minutes"])
else:
    base_nodes = list(range(n_rand))
    g0 = random_connected_graph(n_rand, seed=seed)
    df0 = pd.DataFrame([(a, b, d["weight"]) for a, b, d in g0.edges(data=True)],
                       columns=["from", "to", "minutes"])
 
with st.expander("✏️ แก้ไขกราฟ: ตารางเส้นเชื่อม (แก้ตัวเลข ลบแถว หรือเพิ่มแถวได้)", expanded=False):
    st.caption("ลองลบเส้นให้บางจุดแยกออกจากกลุ่ม เพื่อดูกรณี 'กราฟไม่เชื่อมกัน' "
               "(ชื่อจุดต้องตรงกับในตาราง แถวที่ว่างหรือเวลา ≤ 0 จะถูกข้าม)")
    edited = st.data_editor(
        df0, num_rows="dynamic", width="stretch", hide_index=True,
        key=f"edges_{src}_{n_rand}_{seed}",
        column_config={
            "from": st.column_config.TextColumn("จุด A") if is_bkk else st.column_config.NumberColumn("จุด A", step=1),
            "to": st.column_config.TextColumn("จุด B") if is_bkk else st.column_config.NumberColumn("จุด B", step=1),
            "minutes": st.column_config.NumberColumn("เวลา (นาที)", min_value=1, step=1),
        },
    )
 
G = nx.Graph()
G.add_nodes_from(base_nodes)
bad_rows = 0
for _, r in edited.iterrows():
    a, b, w = r["from"], r["to"], r["minutes"]
    if pd.isna(a) or pd.isna(b) or pd.isna(w) or w <= 0 or a == b:
        bad_rows += 1
        continue
    if not is_bkk:
        a, b = int(a), int(b)
    G.add_edge(a, b, weight=float(w) if float(w) != int(w) else int(w))
if bad_rows:
    st.warning(f"ข้ามแถวที่ใช้ไม่ได้ {bad_rows} แถว (ว่าง, เวลา ≤ 0 หรือจุดซ้ำกัน)")
 
if G.number_of_nodes() < 2:
    st.error("กราฟต้องมีอย่างน้อย 2 จุด")
    st.stop()
 
if is_bkk and all(n in BKK_POS for n in G):
    POS = BKK_POS
else:
    POS = nx.spring_layout(G, seed=42, weight=None)
 
nodes = list(G.nodes)
default_s = "Victory Monument" if is_bkk and "Victory Monument" in nodes else nodes[0]
default_t = "Phrom Phong" if is_bkk and "Phrom Phong" in nodes else nodes[-1]
start = st.sidebar.selectbox("จุดเริ่มต้น (Dijkstra / Prim)", nodes, index=nodes.index(default_s), format_func=label)
end = None
if algo == "Dijkstra":
    end = st.sidebar.selectbox("จุดปลายทาง", nodes, index=nodes.index(default_t), format_func=label)
elif algo == "Kruskal":
    st.sidebar.caption("Kruskal ไม่ต้องเลือกจุดเริ่มต้น เพราะพิจารณาทุกเส้นในกราฟ")
 
n_comp = nx.number_connected_components(G)
c1, c2, c3 = st.columns(3)
c1.metric("จำนวนจุด (V)", G.number_of_nodes())
c2.metric("จำนวนเส้น (E)", G.number_of_edges())
c3.metric("กราฟเชื่อมกันทั้งหมด", "ใช่" if n_comp == 1 else f"ไม่ ({n_comp} ส่วน)")
 
tab_res, tab_step, tab_cmp, tab_test = st.tabs(
    ["📍 ผลลัพธ์", "🪜 ดูทีละขั้น", "⚖️ เปรียบเทียบ & วัดเวลา", "✅ ทดสอบความถูกต้อง"])
 
# ---------------- ผลลัพธ์ ----------------
with tab_res:
    if algo == "Dijkstra":
        st.write("**Dijkstra:** หาเส้นทางที่ใช้เวลาน้อยที่สุดจากจุดเริ่มต้นไปปลายทาง")
        if start == end:
            st.info("จุดเริ่มต้นและปลายทางเป็นจุดเดียวกัน เลือกจุดปลายทางใหม่")
        else:
            dist, prev, _ = dijkstra(G, start, end)
            p = path_from(prev, start, end)
            if p is None:
                st.warning(f"ไปไม่ถึง {label(end)} จาก {label(start)} เพราะกราฟไม่เชื่อมกัน")
                show_graph(G, POS, title="ไม่พบเส้นทาง")
            else:
                a, b = st.columns(2)
                a.metric("เวลารวม (นาที)", path_minutes(G, p))
                b.metric("จำนวนเส้นที่ผ่าน", len(p) - 1)
                st.success(" → ".join(label(x) for x in p))
                show_graph(G, POS, path_edges=path_edges(p), title=f"Dijkstra: {path_minutes(G, p)} นาที")
    elif algo == "Prim":
        st.write("**Prim:** ต่อทุกจุดให้ถึงกันด้วยเส้นรวมถูกที่สุด โดยโตเป็นต้นไม้จากจุดเริ่มต้น")
        tree, total, cov, _ = prim(G, start)
        a, b = st.columns(2)
        a.metric("น้ำหนักรวมของต้นไม้ (MST)", total)
        b.metric("จำนวนเส้นในต้นไม้", len(tree))
        if len(cov) < G.number_of_nodes():
            st.warning(f"กราฟไม่เชื่อมกัน ได้ต้นไม้เฉพาะส่วนที่ต่อถึงจากจุดเริ่มต้น "
                       f"({len(cov)}/{G.number_of_nodes()} จุด)")
        else:
            st.success("ต่อครบทุกจุดด้วยต้นทุนรวมต่ำที่สุด")
        show_graph(G, POS, path_edges=tree, title=f"Prim (MST): น้ำหนักรวม {total}")
    else:
        st.write("**Kruskal:** เรียงเส้นจากถูกไปแพง แล้วเลือกเส้นที่ไม่ทำให้เกิดวงจร จนต่อครบทุกจุด")
        tree, total, _ = kruskal(G)
        a, b = st.columns(2)
        a.metric("น้ำหนักรวมของต้นไม้ (MST)", total)
        b.metric("จำนวนเส้นในต้นไม้", len(tree))
        if n_comp > 1:
            st.warning(f"กราฟไม่เชื่อมกัน {n_comp} ส่วน จึงได้ 'ป่า' คือหนึ่งต้นไม้ต่อหนึ่งส่วน (รวม {len(tree)} เส้น)")
        else:
            st.success("ต่อครบทุกจุดด้วยต้นทุนรวมต่ำที่สุด")
        show_graph(G, POS, path_edges=tree, title=f"Kruskal (MST): น้ำหนักรวม {total}")
 
# ---------------- ทีละขั้น ----------------
with tab_step:
    which = st.radio("เลือกอัลกอริทึมที่จะดูทีละขั้น", ["Dijkstra", "Prim", "Kruskal"], horizontal=True, key="step_algo")
    others = [n for n in nodes if n != start]
    if which == "Dijkstra":
        st.caption("เหลือง = ยืนยันแล้ว, ฟ้า = กำลังพิจารณา, เส้นน้ำเงิน = ทางที่ดีที่สุดที่รู้ ณ ตอนนี้, ตัวเลขในวงเล็บ = ระยะปัจจุบัน")
        d_def = end if (end is not None and end != start) else others[0]
        s2 = st.selectbox("จุดปลายทาง", others, index=others.index(d_def), format_func=label, key="step_end")
        _, _, steps = dijkstra(G, start, s2, record=True)
    elif which == "Prim":
        st.caption("เหลือง = จุดที่อยู่ในต้นไม้แล้ว, เส้นน้ำเงิน = เส้นที่เลือกแล้ว, เส้นส้ม = เส้นที่เพิ่งเลือก")
        _, _, _, steps = prim(G, start, record=True)
    else:
        st.caption("สีของจุด = กลุ่มที่เชื่อมกันแล้ว (จุดขาว = ยังอยู่ลำพัง), เส้นน้ำเงิน = เส้นที่เลือกแล้ว, "
                   "เส้นส้ม = เส้นที่เลือกในขั้นนี้, เส้นแดง = เส้นที่ถูกข้ามเพราะเกิดวงจร")
        _, _, steps = kruskal(G, record=True)
    i = st.slider("ขั้นที่", 1, len(steps), 1, key=f"slider_{which}") - 1
    stp = steps[i]
    st.info(f"ขั้นที่ {i + 1}/{len(steps)}: {stp['msg']}")
    if which == "Dijkstra":
        colors = {n: "#F2B01E" for n in stp["done"]}
        colors[stp["cur"]] = "#6C9CFF"
        lab = {n: ("∞" if d == INF else d) for n, d in stp["dist"].items()}
        show_graph(G, POS, tree_edges=[(v, u) for v, u in stp["prev"].items()], node_color=colors, extra=lab,
                   title=f"Dijkstra ขั้นที่ {i + 1}")
    elif which == "Prim":
        colors = {n: "#F2B01E" for n in stp["nodes"]}
        show_graph(G, POS, tree_edges=stp["tree"], node_color=colors,
                   focus=[stp["focus"]] if stp["focus"] else (), title=f"Prim ขั้นที่ {i + 1}")
    else:
        sizes = {}
        for c in stp["comp"].values():
            sizes[c] = sizes.get(c, 0) + 1
        colors = {n: PALETTE[c % len(PALETTE)] for n, c in stp["comp"].items() if sizes[c] > 1}
        fcol = "#F2B01E" if stp["ok"] else "#CF4527"
        show_graph(G, POS, tree_edges=stp["tree"], node_color=colors,
                   focus=[stp["focus"]] if stp["focus"] else (), focus_color=fcol, title=f"Kruskal ขั้นที่ {i + 1}")
    with st.expander("บันทึกทุกขั้นตอน"):
        for k, s_ in enumerate(steps, 1):
            st.text(f"{k}. {s_['msg']}")
 
# ---------------- เปรียบเทียบ ----------------
with tab_cmp:
    st.subheader("1) Prim เทียบกับ Kruskal: ได้คำตอบเท่ากันไหม")
    tp_, wp_, _, _ = prim(G, start)
    tk_, wk_, _ = kruskal(G)
    comp_start = nx.node_connected_component(G, start)
    wk_comp = sum(G[a][b]["weight"] for a, b in tk_ if a in comp_start)   # Kruskal เฉพาะส่วนของจุดเริ่มต้น
    st.dataframe(pd.DataFrame([
        {"อัลกอริทึม": "Prim (โตจากจุดเริ่มต้น)", "จำนวนเส้น": len(tp_), "น้ำหนักรวม": wp_},
        {"อัลกอริทึม": "Kruskal (ส่วนเดียวกับจุดเริ่มต้น)", "จำนวนเส้น": sum(1 for a, b in tk_ if a in comp_start),
         "น้ำหนักรวม": wk_comp},
    ]), hide_index=True, width="stretch")
    if wp_ == wk_comp:
        same = {frozenset(e) for e in tp_} == {frozenset(e) for e in tk_ if e[0] in comp_start}
        st.caption("น้ำหนักรวมเท่ากัน (MST มีน้ำหนักรวมต่ำสุดได้ค่าเดียว) " +
                   ("และเลือกเส้นชุดเดียวกัน" if same else
                    "แต่เลือกเส้นต่างชุดกัน เพราะมีเส้นน้ำหนักเท่ากันให้เลือกได้หลายแบบ"))
    else:
        st.error("น้ำหนักรวมไม่เท่ากัน: ตรวจสอบกราฟอีกครั้ง")
 
    st.divider()
    st.subheader("2) Dijkstra เทียบกับ Prim: เป้าหมายต่างกัน ผลจึงต่างกัน")
    dist_all, prev_all, _ = dijkstra(G, start)
    w_spt = spt_weight(G, prev_all)
    st.write(f"เริ่มที่ **{label(start)}**: Dijkstra สร้างต้นไม้ 'เส้นทางสั้นที่สุดไปทุกจุด' ส่วน Prim สร้างต้นไม้ "
             "'เชื่อมทุกจุดด้วยเส้นรวมถูกที่สุด'")
    a, b, c = st.columns(3)
    a.metric("น้ำหนักรวม: ต้นไม้เส้นทางสั้นสุด", w_spt)
    b.metric("น้ำหนักรวม: MST", wp_)
    c.metric("ส่วนต่าง", w_spt - wp_)
    col1, col2 = st.columns(2)
    with col1:
        show_graph(G, POS, figsize=(7, 5), path_edges=[(v, u) for v, u in prev_all.items()],
                   title=f"ต้นไม้เส้นทางสั้นสุด ({w_spt})")
    with col2:
        show_graph(G, POS, figsize=(7, 5), path_edges=tp_, title=f"MST ({wp_})")
    st.caption("ต้นไม้เส้นทางสั้นสุดทำให้ 'ทุกจุดไปถึงจากจุดเริ่มต้นได้เร็วที่สุด' แต่ใช้เส้นรวมมากกว่าหรือเท่ากับ MST เสมอ "
               "ส่วน MST ประหยัดเส้นรวมที่สุด แต่ระยะจากจุดเริ่มต้นไปบางจุดอาจอ้อมกว่า")
 
    st.divider()
    st.subheader("3) วัดเวลาการทำงานจริง")
    if st.button("▶ เริ่มวัดเวลา (ประมาณ 5-15 วินาที)"):
        with st.spinner("กำลังวัดเวลา..."):
            st.session_state["bench_fig"] = run_benchmark()
    if "bench_fig" in st.session_state:
        st.pyplot(st.session_state["bench_fig"])
        st.caption("ทั้งสามวิธีใช้เวลาเพิ่มตามขนาดกราฟแบบเกือบเส้นตรง (ความซับซ้อนประมาณ O(E log V))")
 
# ---------------- ทดสอบ ----------------
with tab_test:
    st.write("เทียบอัลกอริทึมที่เขียนเองกับ `networkx` บนกราฟสุ่ม 300 ชุด และตรวจกรณีพิเศษ")
    if st.button("▶ รันชุดทดสอบ"):
        with st.spinner("กำลังทดสอบ..."):
            bkk = nx.Graph()
            bkk.add_nodes_from(PLACES)
            bkk.add_weighted_edges_from(ROADS)
            st.session_state["test_df"] = run_tests(bkk)
    if "test_df" in st.session_state:
        df_t = st.session_state["test_df"]
        if (df_t["ผล"] == "ผ่าน").all():
            st.success(f"ผ่านครบทั้ง {len(df_t)} รายการ")
        else:
            st.error("มีรายการที่ไม่ผ่าน")
        st.dataframe(df_t, hide_index=True, width="stretch")