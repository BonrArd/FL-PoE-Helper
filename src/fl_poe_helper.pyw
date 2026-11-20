# -*- coding: utf-8 -*-
"""
FL PoE Helper - Assistente de campanha para Path of Exile 1
Build: Poisonous Concoction of Bouncing Pathfinder (guia do animeprincess, Mobalytics, patch 3.30)

O que faz:
  - Janela pequena, sempre por cima do jogo (use o PoE em "Janela sem bordas"/Windowed Fullscreen).
  - Lê SOMENTE o arquivo de log do jogo (Client.txt) para saber área, ato e nível.
  - Mostra o passo a passo do ato atual (checklist salva), as gemas do momento,
    avisos por área/nível e o botão para abrir a árvore de passivos certa.

O que NÃO faz:
  - Não aperta teclas, não clica, não lê memória do jogo, não altera arquivos do jogo.

Funciona no Windows e no Linux (Steam/Proton ou Lutris). No Linux, as teclas próprias (Ctrl+D/Alt+D)
precisam de X11 e do pacote pynput (já vem dentro do executável); no Wayland use Ctrl+C / Ctrl+Alt+C.
Requisitos para rodar pelo código: Python 3.9+ com tkinter.
Como rodar: dê dois cliques no arquivo, ou no terminal:  python fl_poe_helper.pyw
"""

import json
import os
import re
import shutil
import subprocess
import sys
import webbrowser

IS_WIN = os.name == "nt"
IS_LINUX = sys.platform.startswith("linux")

APP_NAME = "FL PoE Helper"
APP_VERSION = "1.0.0"
REPO_URL = "https://github.com/BonrArd/FL-PoE-Helper"
# Tudo que o programa salva fica numa pasta só: %APPDATA%\FL PoE Helper (config, caches, imagens, registros)
_HOME = os.path.expanduser("~")
DATA_DIR = os.path.join(os.environ.get("APPDATA") or _HOME, APP_NAME) if os.name == "nt" \
    else os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.join(_HOME, ".local", "share"), APP_NAME)
CACHE_DIR = os.path.join(DATA_DIR, "cache")
LOG_DIR = os.path.join(DATA_DIR, "registros")
for _d in (DATA_DIR, CACHE_DIR, LOG_DIR):
    try:
        os.makedirs(_d, exist_ok=True)
    except Exception:
        pass
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
ERROR_LOG = os.path.join(LOG_DIR, "erros.txt")

# arquivos antigos (soltos na pasta do usuário) -> nova pasta
_OLD_FILES = [
    (".pconc_helper.json", CONFIG_PATH),
    ("pconc_helper_erros.txt", ERROR_LOG),
    ("pconc_helper_debug.txt", os.path.join(LOG_DIR, "debug.txt")),
    (".pconc_tree_model.json", os.path.join(CACHE_DIR, "arvore.json")),
    (".pconc_trade_stats.json", os.path.join(CACHE_DIR, "trade_mods.json")),
    (".pconc_trade_bases.json", os.path.join(CACHE_DIR, "trade_bases.json")),
    (".pconc_helper.ico", os.path.join(DATA_DIR, "icone.ico")),
    (".pconc_tree_sprites", os.path.join(CACHE_DIR, "imagens_arvore")),
]


def migrate_old_files():
    """Move os arquivos antigos do programa para a pasta nova (uma vez só)."""
    import shutil
    moved = []
    # pasta da versão anterior (%APPDATA%\PConc Helper) -> %APPDATA%\FL PoE Helper
    old_dir = os.path.join(os.path.dirname(DATA_DIR), "PConc Helper")
    if os.name == "nt" and os.path.isdir(old_dir) and old_dir != DATA_DIR:
        for item in os.listdir(old_dir):
            src, dst = os.path.join(old_dir, item), os.path.join(DATA_DIR, item)
            try:
                if not os.path.exists(dst):
                    shutil.move(src, dst)
                elif os.path.isdir(src) and os.path.isdir(dst):
                    for sub in os.listdir(src):
                        if not os.path.exists(os.path.join(dst, sub)):
                            shutil.move(os.path.join(src, sub), os.path.join(dst, sub))
            except Exception:
                pass
        shutil.rmtree(old_dir, ignore_errors=True)
        moved.append("PConc Helper")
    for old, new in _OLD_FILES:
        src = os.path.join(_HOME, old)
        try:
            if os.path.exists(src):
                if os.path.exists(new):
                    if os.path.isdir(src):
                        shutil.rmtree(src, ignore_errors=True)
                    else:
                        os.remove(src)
                else:
                    shutil.move(src, new)
                moved.append(old)
        except Exception:
            pass
    return moved


migrate_old_files()
GUIDE_URL = "https://mobalytics.gg/poe/builds/poisonous-concoction-of-bouncing-pathfinder-animeprincess"

# ---------------------------------------------------------------------------
# Árvores de passivos (extraídas do código do Path of Building do guia)
# ---------------------------------------------------------------------------
TREE_BASE = "https://www.pathofexile.com/passive-skill-tree/"
TREES = [
    ("1) Nível 1–12", "AAAABgIDDKJAAdH0-KA4oSKklUV8xgKXBhmKr-vEogABch6gOA=="),
    ("2) Normal Lab", "AAAABgIDKX11wzqgOB1ARXzGAv4J73pA2n-WLiMi6iedYlr33a_rwuxLyejW35gXmphT_roZitN-n23EoqSVBbUB0ZcGH0Fw56CxtMW74-sUlch6fychBnAABHIeoDjzLB1AslUnnYcDcOc="),
    ("3) Cruel Lab", "AAAABgIDSH11BnCgOP4J73o_bH-WFr-fbfsJYqx2gmyMgCJQACaV993C7EvJ35j-uhmKCpsGoXDnoLFVS4w2en-1SMM6u-NFfMYC6NYaj2JanaouIyLqDHMnnfbaNj0yAR1AYeInIQEkZKbEorIZ6xS5AphTtMXTfh9BF5rPegW1AdGXBkDar-uklaQFyAyVyLTRW478xQAFch6gOIcDcOeyVSed8ywdQIXCASQ="),
    ("4) Merciless Lab", "AAAABgIDYjQ_fXUGcKA4_gnveuO-P2x_lo2_9xOfbfsJYqx2gmyMgCL_k1AAJpX33cLsS8nfmP_4_roZigqbBqFw56CxUUdWyXp_tUjB1QxzSn3HncM6Fr9JUh1ADY1FfMYC6xTo1hqPASRiWp2q6dqHdi4jH0FbjrTRsJL1GJcGjDYnnZaz9toSMHMOxKIyATY9z3ph4iLqu-NkphjvuQJA2t74mFOv69N-VUvA7xeaBbUB0bTFUdmkBaSVN0zIDLIZlcikeCch_MUACXIeoDgmG-O-3vL_-IcDcOfzLB1AhcIBJLJVJ537CJazLqLA7w=="),
    ("5) Troca p/ PConc of Bouncing", "AAAABgIDbDQ_fXUGcKA4_gm00eO-P2x_lha_9xOfbfsJYqx2gmyMgCL_k7IZJpX33cLsHF-xEd-Y__hbjv66GYodQA2NS8nIDGJaCpsGoXDnH0GgsZgjUUcXmhbCen-1SMHVtMXRb8edwzoqW0lSASRR2esUxgKMNujWGo9FfDdMnarp2od2LiNWybCS3vikBRIwz3pVSyedr-v22iLqcw674zIBXU5A2mHiuQLEomSmNj0Mc_UYGO-YU42_034nIcDvUAAFtQHRlwbvejB8pJWP8f0BlrOVyKR4Sn38xQALch6gOCYb477e8v_48ywdQIcDcOcIlhbCb97Rb4XCASSyVSedLqLA7_sIlrM="),
    ("6) Endgame", "AAAABgIDfDQ_fXUGcMgjoDiNfVuO0EzEok2S_gnveuO-P2wNjY2_9xOfbZazyAz7CRjvYqwajbTRbIwmlYAilwYOXAW1_5OyGX_7HF_33a-8wuxLyRmK35j_-NN-_rqv67ERI_ZVKQWTD6sKmwahH0Fw56CxFsJRR-ZYVsl6fxr-wdVFfBqPx53DOlHZSVIdQOsUe2HGAkkTz3owfCSLYlqdqkV-6douI4d2QNr1GLCSEjAMcyLqKlhbJvbaSn1zDn-WMgFdTheaYeL3PejWZKYN87vjN0ze-JhTNm-THxa_wO-YIypbAdG0xdFvjZKklY_x_QFQAJXIpHgnIfzFAgEQARkLch6gOCYb4771sZaz3vL_-HAGVSmHA3DnCJYWwvMsHUD9aw3zLqLA72_e0W8="),
    ("7) Explode (Beacon of Madness)", "AAAABgI3fDQ_BnCgOL3mbAjjvq-8-wlsjIAiJpWjis6oHF-btYTF_roKmwahcOdRR1bJI_bHnR1ARXzGAg3zz3o3TJ2qRX7p2rCSEjAqWFsm9tpzDgG8YeL3PWSmBZM2b5MfwO-SgCpbpJWkePzFUdl9ddBMjX2YIz9s2-cWv_cTN9SxEf-TUAB_-8LsW5kajRmKVSk-z02SDlygseZYFsJ6fxr-wdXxisM6SVIaj0Dah3YuIwOHIuqbjVuOn23e-I2_MgEki9N-7T8Mc_UYyCP669FvSRMY75hT73owfOjWXkV7YQW1H0G0xX-WjZLrFP_4_QGyGWKsD6tKfQ2NAgEZARAKch6gOCYb4771sXDn8ywdQP1rDfP7_8DvcAZVKQiWFsJv3tFv3vL_-A=="),
]


# ---------------------------------------------------------------------------
# Visualizador da árvore (desenhada a partir dos dados oficiais da GGG)
# ---------------------------------------------------------------------------
TREE_DATA_URL = "https://raw.githubusercontent.com/grindinggear/skilltree-export/master/data.json"
TREE_MODEL_PATH = os.path.join(CACHE_DIR, "arvore.json")
_ANG16 = [0, 30, 45, 60, 90, 120, 135, 150, 180, 210, 225, 240, 270, 300, 315, 330]
_ANG40 = [0, 10, 20, 30, 40, 45, 50, 60, 70, 80, 90, 100, 110, 120, 130, 135, 140, 150, 160, 170,
          180, 190, 200, 210, 220, 225, 230, 240, 250, 260, 270, 280, 290, 300, 310, 315, 320, 330, 340, 350]


def decode_tree_code(code):
    """Decodifica o código de uma URL do passive-skill-tree (versão 6)."""
    import base64
    raw = base64.urlsafe_b64decode(code + "=" * (-len(code) % 4))
    i = 4
    cls, asc, n = raw[i], raw[i + 1], raw[i + 2]
    i += 3
    nodes = [(raw[i + 2 * k] << 8) | raw[i + 2 * k + 1] for k in range(n)]
    i += 2 * n
    cn = raw[i]
    i += 1 + 2 * cn
    masteries = []
    if i < len(raw):
        mn = raw[i]
        i += 1
        for _ in range(mn):
            eff = (raw[i] << 8) | raw[i + 1]
            node = (raw[i + 2] << 8) | raw[i + 3]
            masteries.append((eff, node))
            i += 4
    return {"class": cls, "asc": asc, "nodes": nodes, "masteries": masteries}


def build_tree_model(data):
    """Converte o data.json oficial em um modelo enxuto (posições, nomes, ligações)."""
    radii = data["constants"]["orbitRadii"]
    per = data["constants"]["skillsPerOrbit"]
    groups = data["groups"]
    import math

    def angle(orbit, idx):
        s = per[orbit]
        if s == 16:
            return _ANG16[idx % 16]
        if s == 40:
            return _ANG40[idx % 40]
        return 360.0 * idx / s

    nodes, mastery_fx, asc_nodes = {}, {}, {}
    for nid, n in data["nodes"].items():
        if nid == "root" or "group" not in n:
            continue
        if n.get("isProxy"):
            continue
        g = groups.get(str(n["group"]))
        if not g:
            continue
        a = math.radians(angle(n.get("orbit", 0), n.get("orbitIndex", 0)))
        r = radii[n.get("orbit", 0)]
        x, y = g["x"] + r * math.sin(a), g["y"] - r * math.cos(a)
        if n.get("isKeystone"):
            kind = "keystone"
        elif n.get("isMastery"):
            kind = "mastery"
        elif n.get("isJewelSocket"):
            kind = "jewel"
        elif "classStartIndex" in n:
            kind = "start"
        elif n.get("isNotable"):
            kind = "notable"
        else:
            kind = "normal"
        rec = {"x": round(x, 1), "y": round(y, 1), "name": n.get("name", ""),
               "stats": n.get("stats", []), "kind": kind, "g": n["group"], "icon": n.get("icon", "")}
        for fx in n.get("masteryEffects", []) or []:
            mastery_fx[str(fx.get("effect"))] = fx.get("stats", [])
        if n.get("ascendancyName"):
            rec["asc"] = n["ascendancyName"]
            asc_nodes[nid] = rec
        else:
            nodes[nid] = rec
    edges = set()
    for nid, n in data["nodes"].items():
        if nid not in nodes:
            continue
        for o in n.get("out", []):
            if o in nodes and nodes[nid]["kind"] != "mastery" and nodes[o]["kind"] != "mastery":
                edges.add(tuple(sorted((nid, o), key=int)))
    classes = []
    for c in data.get("classes", []):
        classes.append({"name": c.get("name"),
                        "asc": [a.get("id") or a.get("name") for a in c.get("ascendancies", [])]})
    sprites = {}
    for key in ("normalActive", "normalInactive", "notableActive", "notableInactive", "keystoneActive",
                "keystoneInactive", "frame", "mastery", "jewel"):
        z = (data.get("sprites") or {}).get(key)
        if not z:
            continue
        lvl = z.get("0.5") or z[sorted(z.keys(), key=float)[-1]]
        sprites[key] = {"file": lvl["filename"],
                        "coords": {k: [c["x"], c["y"], c["w"], c["h"]] for k, c in lvl.get("coords", {}).items()}}
    return {"version": 3, "nodes": nodes, "asc_nodes": asc_nodes, "edges": sorted(edges),
            "mastery_fx": mastery_fx, "classes": classes, "sprites": sprites}


def load_tree_model(download=True):
    """Carrega o modelo salvo; se não existir, baixa os dados oficiais e cria."""
    try:
        with open(TREE_MODEL_PATH, "r", encoding="utf-8") as f:
            m = json.load(f)
        if m.get("version") == 3:
            return m
    except Exception:
        pass
    if not download:
        return None
    import urllib.request
    req = urllib.request.Request(TREE_DATA_URL, headers={"User-Agent": "FLPoEHelper/1.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    model = build_tree_model(data)
    with open(TREE_MODEL_PATH, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False)
    return model


# --- ordem de alocação ---------------------------------------------------
# Peso de cada tipo de bônus para a PConc (quanto maior, mais cedo vale pegar)
NODE_WEIGHTS = [
    ("maximum life", 5), ("life flask", 4), ("flask", 3), ("poison", 4), ("projectile", 3),
    ("chaos damage", 3), ("damage over time", 3), ("suppress", 3), ("movement speed", 2),
    ("evasion", 2), ("attack speed", 2), ("resistance", 2), ("reservation", 2), ("mana", 1),
    ("accuracy", 1), ("dexterity", 1), ("intelligence", 1), ("strength", 1),
]
# Pontos de passiva por quest acumulados ao FIM de cada ato (ajudando a Alira = sem ponto de bandido)
QUEST_POINTS_END = {0: 0, 1: 2, 2: 4, 3: 6, 4: 7, 5: 9, 6: 12, 7: 15, 8: 18, 9: 20, 10: 21, 11: 23}


def estimate_points(level, act):
    """Pontos de passiva aproximados: nível - 1 + quests dos atos já concluídos."""
    return max(0, level - 1) + QUEST_POINTS_END.get(max(0, min(act, 11) - 1), 0)


def node_value(n, mastery_stats=None):
    text = " ".join(mastery_stats or n.get("stats", [])).lower()
    v = 0.5 + sum(w for k, w in NODE_WEIGHTS if k in text)
    if n["kind"] in ("notable", "keystone"):
        v *= 2.5
    elif n["kind"] == "mastery":
        v *= 2.0
    elif n["kind"] == "jewel":
        v = 3.0
    return v


def plan_allocation(model, target, allocated, masteries=None, class_name="RANGER"):
    """Ordena as passivas que faltam (target - allocated) por valor/custo, sempre por caminhos válidos."""
    nodes = model["nodes"]
    adj = {}
    for a, b in model["edges"]:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    start = next((k for k, n in nodes.items() if n["kind"] == "start" and n["name"].upper() == class_name.upper()),
                 None)
    alloc = set(allocated) | ({start} if start else set())
    remaining = {n for n in target if n in nodes} - alloc
    masteries = masteries or {}
    order = []
    while remaining:
        # BFS a partir do que já está alocado, andando só por passivas da árvore-alvo
        dist, parent, q = {}, {}, []
        for a in alloc:
            dist[a] = 0
            q.append(a)
        while q:
            cur = q.pop(0)
            for nb in adj.get(cur, ()):
                if nb in remaining and nb not in dist:
                    dist[nb] = dist[cur] + 1
                    parent[nb] = cur
                    q.append(nb)
        groups_alloc = {nodes[a].get("g") for a in alloc if a in nodes and nodes[a]["kind"] != "mastery"}
        best, best_score = None, -1
        for n in remaining:
            nd = nodes[n]
            if nd["kind"] == "mastery":
                if nd.get("g") not in groups_alloc:
                    continue
                cost = 1
            elif n in dist:
                cost = dist[n]
            else:
                continue
            score = node_value(nd, masteries.get(n)) / cost
            if score > best_score:
                best, best_score = n, score
        if best is None:
            order.extend(sorted(remaining, key=lambda x: -node_value(nodes[x])))
            break
        path = []
        cur = best
        while cur not in alloc:
            path.append(cur)
            if nodes[cur]["kind"] == "mastery":
                break
            cur = parent[cur]
        for n in reversed(path):
            order.append(n)
            alloc.add(n)
            remaining.discard(n)
    return order


SPRITE_DIR = os.path.join(CACHE_DIR, "imagens_arvore")
ASKED_PILLOW = {"v": False}


def has_pillow():
    try:
        import PIL.Image  # noqa: F401
        import PIL.ImageTk  # noqa: F401
        return True
    except Exception:
        return False


class SpriteCache:
    """Recorta e monta os ícones oficiais (ícone + moldura) das passivas. Precisa do Pillow."""
    FRAMES = {"normal": ("PSSkillFrameActive", "PSSkillFrame"),
              "notable": ("NotableFrameAllocated", "NotableFrameUnallocated"),
              "keystone": ("KeystoneFrameAllocated", "KeystoneFrameUnallocated"),
              "jewel": ("JewelFrameAllocated", "JewelFrameUnallocated")}
    SHEETS = {"normal": ("normalActive", "normalInactive"),
              "notable": ("notableActive", "notableInactive"),
              "keystone": ("keystoneActive", "keystoneInactive")}

    def __init__(self, model):
        self.model = model
        self.sprites = model.get("sprites", {})
        self.ok = has_pillow() and bool(self.sprites)
        self.ready = False
        self.sheets = {}
        self.cache = {}

    def _local(self, url):
        name = url.split("/")[-1].split("?")[0]
        tag = url.split("?")[-1] if "?" in url else ""
        return os.path.join(SPRITE_DIR, f"{tag}_{name}" if tag else name)

    def download(self):
        """Baixa as folhas de sprites (uma vez). Roda em thread."""
        if not self.ok:
            return False
        import urllib.request
        os.makedirs(SPRITE_DIR, exist_ok=True)
        for key, sp in self.sprites.items():
            path = self._local(sp["file"])
            if not os.path.isfile(path):
                req = urllib.request.Request(sp["file"], headers={"User-Agent": "Mozilla/5.0 (FLPoEHelper)"})
                with urllib.request.urlopen(req, timeout=60) as r, open(path + ".tmp", "wb") as f:
                    f.write(r.read())
                os.replace(path + ".tmp", path)
        self.ready = True
        return True

    def _sheet(self, key):
        if key not in self.sheets:
            from PIL import Image
            self.sheets[key] = Image.open(self._local(self.sprites[key]["file"])).convert("RGBA")
        return self.sheets[key]

    def _crop(self, key, name):
        sp = self.sprites.get(key)
        if not sp or name not in sp["coords"]:
            return None
        x, y, w, h = sp["coords"][name]
        return self._sheet(key).crop((x, y, x + w, y + h))

    def image(self, node, allocated, size_px):
        """PhotoImage do nó (ícone + moldura) no tamanho pedido; None se não der."""
        if not self.ready:
            return None
        kind = node["kind"]
        size_px = max(6, int(size_px) // 2 * 2)
        key = (kind, node.get("icon", ""), bool(allocated), size_px)
        if key in self.cache:
            return self.cache[key]
        try:
            from PIL import Image, ImageDraw, ImageTk, ImageEnhance
            img = None
            if kind in ("normal", "notable", "keystone"):
                sheet = self.SHEETS[kind][0 if allocated else 1]
                icon = self._crop(sheet, node.get("icon", ""))
                frame = self._crop("frame", self.FRAMES[kind][0 if allocated else 1])
                if frame is None:
                    return None
                img = Image.new("RGBA", frame.size, (0, 0, 0, 0))
                if icon is not None:
                    mask = Image.new("L", icon.size, 0)
                    ImageDraw.Draw(mask).ellipse((0, 0, icon.size[0] - 1, icon.size[1] - 1), fill=255)
                    img.paste(icon, ((frame.size[0] - icon.size[0]) // 2, (frame.size[1] - icon.size[1]) // 2), mask)
                img = Image.alpha_composite(img, frame)
            elif kind == "jewel":
                img = self._crop("frame", self.FRAMES["jewel"][0 if allocated else 1])
            elif kind == "mastery":
                img = self._crop("mastery", node.get("icon", ""))
                if img is not None and not allocated:
                    img = ImageEnhance.Brightness(img).enhance(0.45)
            if img is None:
                return None
            img = img.resize((size_px, size_px), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.cache[key] = photo
            return photo
        except Exception:
            return None


def install_pillow(done_cb):
    """Instala o Pillow com o pip do próprio Python (o usuário confirma antes)."""
    import subprocess
    import sys
    import threading

    def worker():
        if getattr(sys, "frozen", False):
            done_cb(False, "na versão .exe as imagens já vêm dentro do programa; gere o .exe de novo")
            return
        try:
            exe = sys.executable
            if exe.lower().endswith("pythonw.exe"):
                alt = exe[:-len("pythonw.exe")] + "python.exe"
                if os.path.isfile(alt):
                    exe = alt
            flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
            r = subprocess.run([exe, "-m", "pip", "install", "--user", "pillow"], capture_output=True,
                               text=True, creationflags=flags)
            done_cb(r.returncode == 0, (r.stderr or r.stdout or "")[-300:])
        except Exception as ex:
            done_cb(False, str(ex))
    threading.Thread(target=worker, daemon=True).start()


def open_tree_viewer(root, start_index, theme, ctx=None):
    """Janela que desenha a árvore de passivos da fase escolhida."""
    import threading
    import tkinter as tk

    BG, BG2, FG, MUTED, ACCENT = theme
    NEW = "#ffcc33"
    win = tk.Toplevel(root)
    win.title("Árvore de passivos – PConc Pathfinder")
    win.configure(bg=BG)
    win.geometry("900x700")
    win.attributes("-topmost", True)

    top = tk.Frame(win, bg=BG)
    top.pack(fill="x", padx=8, pady=6)
    trees = guide_trees()
    titles = [t["title"] for t in trees] or ["(sem árvore)"]
    start_index = min(max(start_index or 0, 0), len(titles) - 1)
    phase = tk.StringVar(value=titles[start_index])
    only_new = tk.BooleanVar(value=True)
    om = tk.OptionMenu(top, phase, *titles)
    om.configure(bg=BG2, fg=FG, activebackground=BG2, activeforeground=ACCENT,
                 relief="flat", highlightthickness=0)
    om["menu"].configure(bg=BG2, fg=FG)
    om.pack(side="left")
    tk.Checkbutton(top, text="Destacar novas", variable=only_new,
                   bg=BG, fg=FG, selectcolor=BG2, activebackground=BG,
                   activeforeground=ACCENT).pack(side="left", padx=6)
    plan_mode = tk.BooleanVar(value=ctx is not None)
    tk.Checkbutton(top, text="Ordem para o MEU nível", variable=plan_mode,
                   bg=BG, fg=FG, selectcolor=BG2, activebackground=BG,
                   activeforeground=ACCENT).pack(side="left", padx=6)
    lbl_count = tk.Label(top, text="", bg=BG, fg=MUTED)
    lbl_count.pack(side="right")

    info = tk.Label(win, text="Carregando...", bg=BG2, fg=FG, anchor="w", justify="left",
                    wraplength=860, padx=8, pady=4, font=("Segoe UI", 9))
    info.pack(fill="x", padx=8)

    mid = tk.Frame(win, bg=BG)
    mid.pack(fill="both", expand=True, padx=8, pady=6)
    canvas = tk.Canvas(mid, bg="#0b0c0f", highlightthickness=0, cursor="fleur")
    canvas.pack(side="left", fill="both", expand=True)
    side = tk.Text(mid, width=34, bg=BG2, fg=FG, relief="flat", wrap="word",
                   font=("Segoe UI", 9), padx=6, pady=6)
    side.pack(side="right", fill="y", padx=(6, 0))
    side.tag_configure("h", foreground=ACCENT, font=("Segoe UI", 10, "bold"))
    side.tag_configure("new", foreground=NEW)
    side.tag_configure("muted", foreground=MUTED)
    side.tag_configure("next", foreground="#4dd2ff", font=("Segoe UI", 9, "bold"))

    imgbar = tk.Frame(win, bg=WARN_BG)
    imgbar.pack(fill="x", padx=8, pady=(0, 4), after=top)
    lbl_img = tk.Label(imgbar, text="Carregando imagens...", bg=WARN_BG, fg=WARN_FG,
                       font=("Segoe UI", 10, "bold"), anchor="w", padx=8, pady=4)
    lbl_img.pack(side="left")

    def img_status(text, good=False):
        col_bg = "#1d2a1d" if good else WARN_BG
        imgbar.config(bg=col_bg)
        lbl_img.config(text=text, bg=col_bg, fg=ACCENT if good else WARN_FG)

    confirm = {"v": False}

    def ask_install():
        # confirmação dentro da própria janela (sem caixa de diálogo que trava e some atrás do jogo)
        if not confirm["v"]:
            confirm["v"] = True
            btn_inst.config(text="✔ Confirmar: instalar Pillow (~3 MB)")
            img_status("Clique de novo para confirmar a instalação do Pillow.")
            return
        img_status("Instalando o Pillow... (pode levar um minuto)")
        btn_inst.config(state="disabled")
        out = {}
        install_pillow(lambda ok, msg: out.update(ok=ok, msg=msg))

        def wait_inst():
            if "ok" not in out:
                win.after(500, wait_inst)
            elif out["ok"]:
                img_status("✅ Pillow instalado! FECHE e ABRA o programa para ver as imagens.", good=True)
            else:
                img_status("❌ Não consegui instalar. No Prompt de Comando: python -m pip install pillow  "
                           f"({out['msg'][-100:]})")
        win.after(500, wait_inst)

    btn_inst = tk.Button(imgbar, text="🖼 Ativar imagens reais (instalar Pillow)", command=ask_install,
                         bg=ACCENT, fg="#0b0c0f", relief="flat", font=("Segoe UI", 10, "bold"), padx=10)

    tk.Label(win, text="Roda do mouse: zoom • Arrastar: mover • Passe o mouse numa passiva para ver o que ela faz",
             bg=BG, fg=MUTED, font=("Segoe UI", 8)).pack(pady=(0, 6))

    st = {"model": None, "scale": 0.05, "ox": 0.0, "oy": 0.0, "items": {}, "alloc": set(),
          "new": set(), "drag": None, "order": [], "have_n": 0, "real": None, "plan_on": False}
    NEXT = "#4dd2ff"
    FUTURE = "#7a6a25"
    N_NEXT = 12

    def w2s(x, y):
        return x * st["scale"] + st["ox"], y * st["scale"] + st["oy"]

    RAD = {"normal": 26, "notable": 42, "keystone": 58, "jewel": 34, "mastery": 38, "start": 60}
    MINPX = {"normal": 2, "notable": 3.5, "keystone": 5, "jewel": 3, "mastery": 3, "start": 5}

    def redraw():
        m = st["model"]
        if not m:
            return
        canvas.delete("all")
        st["items"].clear()
        st["imgrefs"] = []
        nodes, alloc, new = m["nodes"], st["alloc"], st["new"]
        hl = only_new.get()
        plan = st["plan_on"]
        oidx = {n: i for i, n in enumerate(st["order"])}
        have_n = st["have_n"]
        cw, ch = max(canvas.winfo_width(), 200), max(canvas.winfo_height(), 200)
        sprites = st.get("sprites")
        use_img = bool(sprites and sprites.ready and RAD["normal"] * st["scale"] >= 2.5)

        def visible(x, y, pad=60):
            return -pad <= x <= cw + pad and -pad <= y <= ch + pad

        def plan_color(nid):
            if nid not in oidx:
                return ACCENT  # já tem
            i = oidx[nid]
            if i < have_n:
                return ACCENT
            if i < have_n + N_NEXT:
                return NEXT
            return FUTURE

        def status_color(nid):
            if nid not in alloc:
                return None
            if plan:
                return plan_color(nid)
            return NEW if hl and nid in new else ACCENT

        lw = max(1.5, min(6.0, 40 * st["scale"]))
        for a, b in m["edges"]:
            na, nb = nodes[a], nodes[b]
            x1, y1 = w2s(na["x"], na["y"])
            x2, y2 = w2s(nb["x"], nb["y"])
            if not (visible(x1, y1) or visible(x2, y2)) and use_img:
                continue
            if a in alloc and b in alloc:
                ca, cb = status_color(a), status_color(b)
                col = FUTURE if FUTURE in (ca, cb) else (NEXT if NEXT in (ca, cb) else
                                                         (NEW if NEW in (ca, cb) else ACCENT))
                canvas.create_line(x1, y1, x2, y2, fill=col, width=lw)
            else:
                canvas.create_line(x1, y1, x2, y2, fill="#3a3326" if use_img else "#2a2d35",
                                   width=max(1, lw * 0.6) if use_img else 1)
        for nid, n in nodes.items():
            k = n["kind"]
            x, y = w2s(n["x"], n["y"])
            r = max(MINPX[k], RAD[k] * st["scale"])
            if use_img and not visible(x, y):
                continue
            col = status_color(nid)
            if use_img:
                r = max(r, {"normal": 8, "notable": 12, "keystone": 15, "jewel": 11, "mastery": 10}.get(k, r))
            photo = sprites.image(n, nid in alloc, 2 * r) if use_img and k != "start" else None
            if photo is not None:
                it = canvas.create_image(x, y, image=photo, tags=("node",))
                st["imgrefs"].append(photo)
                if col and (plan or (hl and nid in new)):
                    canvas.create_oval(x - r - 2, y - r - 2, x + r + 2, y + r + 2, outline=col,
                                       width=max(2, r * 0.18))
            else:
                if col:
                    fill = col
                    outline = "#ffffff" if k in ("notable", "keystone") else fill
                elif k == "mastery":
                    fill, outline = "", "#3a3f4a"
                else:
                    fill = {"notable": "#5a5f6b", "keystone": "#7a6f55", "jewel": "#3d5470",
                            "start": "#6b4b8a"}.get(k, "#3f434d")
                    outline = fill
                it = canvas.create_oval(x - r, y - r, x + r, y + r, fill=fill, outline=outline,
                                        tags=("node",))
            st["items"][it] = nid
            if plan and nid in oidx and have_n <= oidx[nid] < have_n + N_NEXT:
                canvas.create_text(x, y - r - 10, text=str(oidx[nid] - have_n + 1), fill=NEXT,
                                   font=("Segoe UI", 11, "bold"))

    def describe(nid):
        m = st["model"]
        n = m["nodes"][nid]
        txt = n["name"]
        if nid in st["alloc"]:
            txt += "  ✔ pegar" + ("  (NOVA nesta fase)" if nid in st["new"] else "")
            if st["plan_on"] and nid in st["order"]:
                i = st["order"].index(nid)
                if i >= st["have_n"]:
                    txt += f"  → ordem: #{i - st['have_n'] + 1}"
        stats = list(n["stats"])
        if n["kind"] == "mastery":
            eff = st["mastery_sel"].get(nid)
            if eff:
                stats = m["mastery_fx"].get(eff, stats)
        return txt + ("\n" + " | ".join(stats) if stats else "")

    def on_enter(_e):
        cur = canvas.find_withtag("current")
        if cur and cur[0] in st["items"]:
            info.config(text=describe(st["items"][cur[0]]))

    canvas.tag_bind("node", "<Enter>", on_enter)

    def fit():
        canvas.update_idletasks()
        m = st["model"]
        focus = []
        if st["plan_on"] and st["order"]:
            focus = [n for n in st["order"][st["have_n"]:st["have_n"] + N_NEXT] if n in m["nodes"]]
        if len(focus) < 2:
            focus = [n for n in st["new"] if n in m["nodes"]] if only_new.get() else []
        pts = ([m["nodes"][n] for n in focus] if len(focus) >= 2 else
               [m["nodes"][n] for n in st["alloc"] if n in m["nodes"]]) or list(m["nodes"].values())
        xs, ys = [p["x"] for p in pts], [p["y"] for p in pts]
        w, h = max(canvas.winfo_width(), 200), max(canvas.winfo_height(), 200)
        bw, bh = (max(xs) - min(xs)) or 1, (max(ys) - min(ys)) or 1
        st["scale"] = max(min(w / (bw * 1.6), h / (bh * 1.6), 0.35), 0.22 if len(focus) >= 2 else 0)
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        st["ox"], st["oy"] = w / 2 - cx * st["scale"], h / 2 - cy * st["scale"]

    def set_phase(*_):
        m = st["model"]
        if not m:
            return
        if not trees:
            info.config(text="Este guia não tem árvore de passivas.")
            return
        idx = titles.index(phase.get())
        cur = trees[idx]
        prev = trees[idx - 1] if idx > 0 else {"nodes": []}
        if GUIDE["mode"] == "pconc" and idx == 6:  # Explode é variante do endgame: compara com a 6
            prev = trees[5]
        alloc = {str(n) for n in cur["nodes"]}
        st["alloc"] = {n for n in alloc if n in m["nodes"]}
        st["new"] = st["alloc"] - {str(n) for n in prev["nodes"]}
        st["mastery_sel"] = {str(node): str(eff) for eff, node in cur["masteries"]}
        asc = [m["asc_nodes"][n] for n in alloc if n in m["asc_nodes"]]
        removed = {str(n) for n in prev["nodes"]} - alloc
        lbl_count.config(text=f"{len(st['alloc'])} passivas  •  {len(st['new'])} novas")

        side.config(state="normal")
        side.delete("1.0", "end")
        st["plan_on"] = bool(plan_mode.get() and ctx)
        st["order"], st["have_n"] = [], 0
        if st["plan_on"]:
            c = ctx()
            mstats = {n: m["mastery_fx"].get(e, []) for n, e in st["mastery_sel"].items()}
            if st["real"] is not None:
                base = {n for n in st["real"] if n in m["nodes"]}
                st["order"] = plan_allocation(m, st["alloc"], base, mstats)
                st["have_n"] = 0
                head = f"Sua árvore real (lida do site) • nível {c['level']}"
            else:
                base = {str(n) for n in prev["nodes"] if str(n) in m["nodes"]}
                st["order"] = plan_allocation(m, st["alloc"], base, mstats)
                pts = estimate_points(c["level"], c["act"])
                st["have_n"] = max(0, min(len(st["order"]), pts - len(base)))
                head = (f"Nível {c['level']} • ~{pts} pontos (aprox.)\n"
                        f"Considerando que você completou a fase anterior.")
            side.insert("end", "▶ O QUE PEGAR AGORA\n", "h")
            side.insert("end", head + "\n", "muted")
            nxt = st["order"][st["have_n"]:st["have_n"] + N_NEXT]
            if st["have_n"]:
                side.insert("end", f"(as primeiras {st['have_n']} desta fase você já deve ter — em verde)\n", "muted")
            if not nxt:
                side.insert("end", "Fase completa! Escolha a próxima fase no menu.\n", "new")
            for k, n in enumerate(nxt, 1):
                nd = m["nodes"][n]
                stt = mstats.get(n) or nd["stats"]
                tag = "next" if nd["kind"] in ("notable", "keystone", "mastery", "jewel") else None
                side.insert("end", f"{k}. {nd['name']}", tag)
                if stt:
                    side.insert("end", " — " + "; ".join(stt)[:90], "muted")
                side.insert("end", "\n")
            left = len(st["order"]) - st["have_n"] - len(nxt)
            if left > 0:
                side.insert("end", f"... e mais {left} depois (amarelo-escuro)\n", "muted")
            if st["real"] is not None:
                extra = sorted(m["nodes"][n]["name"] for n in st["real"]
                               if n in m["nodes"] and n not in st["alloc"] and m["nodes"][n]["kind"] != "start")
                if extra:
                    side.insert("end", "\nVocê tem e o guia não usa (refund quando der):\n", "h")
                    side.insert("end", "\n".join("• " + x for x in extra[:15]) + "\n", "muted")
            side.insert("end", "\n")
        side.insert("end", "Ascendência\n", "h")
        notable_asc = [a["name"] for a in asc if a["kind"] in ("notable", "keystone")]
        side.insert("end", (", ".join(notable_asc) or "—") + "\n\n")
        side.insert("end", "Notáveis NOVAS nesta fase\n", "h")
        newn = sorted(m["nodes"][n]["name"] for n in st["new"]
                      if m["nodes"][n]["kind"] in ("notable", "keystone", "jewel"))
        side.insert("end", ("\n".join("• " + x for x in newn) or "—") + "\n\n", "new")
        side.insert("end", "Masteries escolhidas\n", "h")
        for node, eff in st["mastery_sel"].items():
            stats = m["mastery_fx"].get(eff, [])
            nm = m["nodes"].get(node, {}).get("name", "Mastery")
            side.insert("end", f"• {nm}: " + " / ".join(stats) + "\n")
        if removed:
            side.insert("end", "\nSaem da fase anterior (refund)\n", "h")
            rem = sorted(m["nodes"][n]["name"] for n in removed if n in m["nodes"])
            side.insert("end", "\n".join("• " + x for x in rem) + "\n", "muted")
        side.config(state="disabled")
        if st["plan_on"]:
            info.config(text="Azul numerado = próximos a pegar (na ordem) • Verde = já deve ter • "
                             "Amarelo-escuro = depois • Passe o mouse para detalhes")
        else:
            info.config(text="Amarelo = novo nesta fase • Verde = já tinha • Passe o mouse para detalhes")
        fit()
        redraw()

    phase.trace_add("write", set_phase)
    only_new.trace_add("write", lambda *_: redraw())
    plan_mode.trace_add("write", set_phase)

    def on_wheel(e):
        f = 1.2 if e.delta > 0 else 1 / 1.2
        st["ox"] = e.x - (e.x - st["ox"]) * f
        st["oy"] = e.y - (e.y - st["oy"]) * f
        st["scale"] *= f
        redraw()
        return "break"

    def on_press(e):
        st["drag"] = (e.x, e.y)

    def on_drag(e):
        if st["drag"]:
            dx, dy = e.x - st["drag"][0], e.y - st["drag"][1]
            canvas.move("all", dx, dy)
            st["ox"] += dx
            st["oy"] += dy
            st["drag"] = (e.x, e.y)

    canvas.bind("<MouseWheel>", on_wheel)
    canvas.bind("<Button-4>", lambda e: (setattr(e, "delta", 120), on_wheel(e)))
    canvas.bind("<Button-5>", lambda e: (setattr(e, "delta", -120), on_wheel(e)))
    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", lambda e: redraw() if st.get("sprites") and st["sprites"].ready else None)

    result = {}

    def worker():
        try:
            result["model"] = load_tree_model()
        except Exception as ex:
            result["error"] = str(ex)

    def fetch_real():
        c = ctx() if ctx else {}
        if not (c.get("account") and c.get("char")):
            return
        res2 = {}

        def w2():
            try:
                _items, passives = fetch_character(c["account"], c["char"])
                res2["h"] = {str(h) for h in (passives or {}).get("hashes", [])}
            except Exception as ex:
                res2["e"] = str(ex)
        threading.Thread(target=w2, daemon=True).start()

        def wait2():
            if "h" in res2:
                st["real"] = res2["h"]
                set_phase()
            elif "e" not in res2:
                win.after(300, wait2)
        win.after(300, wait2)

    def start_sprites():
        sc = SpriteCache(st["model"])
        st["sprites"] = sc
        if not has_pillow():
            img_status("⚠ Ícones oficiais DESLIGADOS: falta a biblioteca Pillow.")
            btn_inst.pack(side="left", padx=6, pady=3)
            return
        if not sc.sprites:
            img_status("⚠ Os dados da árvore vieram sem imagens. Feche e abra a árvore de novo.")
            return
        img_status("Baixando as imagens oficiais da árvore (só na 1ª vez)...")
        res3 = {}

        def w3():
            try:
                res3["ok"] = sc.download()
            except Exception as ex:
                res3["e"] = str(ex)
        threading.Thread(target=w3, daemon=True).start()

        def wait3():
            if "ok" in res3:
                img_status("✅ Ícones oficiais ativos. Roda do mouse = zoom.", good=True)
                redraw()
            elif "e" in res3:
                img_status(f"⚠ Não consegui baixar as imagens ({res3['e'][:80]}). Usando bolinhas.")
            else:
                win.after(300, wait3)
        win.after(300, wait3)

    def wait():
        if "model" in result:
            st["model"] = result["model"]
            set_phase()
            start_sprites()
            fetch_real()
        elif "error" in result:
            info.config(text="Não consegui baixar os dados da árvore (precisa de internet na 1ª vez).\n"
                             f"Erro: {result['error']}\nUse o botão 'Abrir no site'.")
        else:
            win.after(200, wait)

    if not os.path.isfile(TREE_MODEL_PATH):
        info.config(text="Baixando os dados oficiais da árvore (~7 MB, só na primeira vez)...")
    threading.Thread(target=worker, daemon=True).start()
    win.after(200, wait)
    return win


# ---------------------------------------------------------------------------
# Checagem antes dos chefes (lê o SEU personagem pela API pública, como o Path of Building)
# ---------------------------------------------------------------------------
# Área de entrada antes do chefe -> (chefe, nível aprox. da área, dica do guia de campanha)
BOSSES = {
    ("The Upper Prison", 1): ("Brutus", 9, "O que mais falta contra o Brutus é sustain (frascos cheios). "
                                         "Se morrer, ele não regenera toda a vida: volte e continue."),
    ("The Cavern of Anger", 1): ("Merveil", 13, "Dano de GELO forte. Fuja dos ciclones altos e mate os minions. "
                                                "Resistência a gelo ajuda muito."),
    ("The Ancient Pyramid", 2): ("Vaal Oversoul", 23, "Clique no altar e espere ele aparecer. Ataques bem avisados."),
    ("The Upper Sceptre of God", 3): ("Dominus", 33, "'A Touch of God' = se afaste. Na fase 2, quando ele "
                                                     "levantar o escudo, fique COLADO nele (evita Corrupted Blood)."),
    ("The Harvest", 4): ("Malachai", 40, "Fique atrás dele, fuja do chão marcado e dos tentáculos. "
                                         "A cada 25% de vida, mate os corações nos cantos."),
    ("The Cathedral Rooftop", 5): ("Kitava", 45, "Pode morrer e voltar sem resetar. DEPOIS dele: -30% em "
                                                 "todas as resistências."),
    ("The Brine King's Reef", 6): ("Brine King", 50, "Fique nas costas dele, não muito perto. Desvie das "
                                                     "paredes de água e dos redemoinhos brancos no chão."),
    ("The Temple of Decay Level 2", 7): ("Arakaali", 55, "Desvie dos raios roxos. Depois de 50%, cuidado com os "
                                                         "discos roxos voando: muito perigosos."),
    ("The Harbour Bridge", 8): ("Solaris e Lunaris", 60, "Elas alternam entre atacáveis e imunes. Luta tranquila."),
    ("The Rotting Core", 9): ("Depraved Trinity", 64, "Doedre, Maligaro e Shavronne separados e depois juntos."),
    ("The Feeding Trough", 10): ("Kitava", 67, "Último chefe. DEPOIS dele: mais -30% nas resistências (total -60%)."),
}

LIFE_FLASK_TIERS = ["Small", "Medium", "Large", "Greater", "Grand", "Giant", "Colossal", "Sacred",
                    "Hallowed", "Sanctified", "Divine", "Eternal"]
LIFE_FLASK_LEVEL = {"Small": 1, "Medium": 3, "Large": 6, "Greater": 12, "Grand": 18, "Giant": 24,
                    "Colossal": 30, "Sacred": 36, "Hallowed": 42, "Sanctified": 50, "Divine": 60, "Eternal": 65}

_RES_PATTERNS = [
    (re.compile(r"([+-]\d+)% to all Elemental Resistances", re.I), ("fire", "cold", "lightning")),
    (re.compile(r"([+-]\d+)% to Fire and Cold Resistances", re.I), ("fire", "cold")),
    (re.compile(r"([+-]\d+)% to Fire and Lightning Resistances", re.I), ("fire", "lightning")),
    (re.compile(r"([+-]\d+)% to Cold and Lightning Resistances", re.I), ("cold", "lightning")),
    (re.compile(r"([+-]\d+)% to Fire Resistance", re.I), ("fire",)),
    (re.compile(r"([+-]\d+)% to Cold Resistance", re.I), ("cold",)),
    (re.compile(r"([+-]\d+)% to Lightning Resistance", re.I), ("lightning",)),
    (re.compile(r"([+-]\d+)% to Chaos Resistance", re.I), ("chaos",)),
    (re.compile(r"([+-]\d+)% to Fire and Chaos Resistances", re.I), ("fire", "chaos")),
    (re.compile(r"([+-]\d+)% to Cold and Chaos Resistances", re.I), ("cold", "chaos")),
    (re.compile(r"([+-]\d+)% to Lightning and Chaos Resistances", re.I), ("lightning", "chaos")),
]
EQUIP_SLOTS = {"BodyArmour", "Helm", "Gloves", "Boots", "Ring", "Ring2", "Amulet", "Belt", "Offhand", "Weapon"}


def res_from_lines(lines, total):
    for ln in lines:
        for rx, keys in _RES_PATTERNS:
            m = rx.search(ln)
            if m:
                for k in keys:
                    total[k] += int(m.group(1))
                break


def mod_text(m):
    """Mod do site pode vir como texto ou como {'description': ...} com marcações [Chave|Texto]."""
    if isinstance(m, dict):
        m = m.get("description") or m.get("text") or ""
    if not isinstance(m, str):
        return ""
    return re.sub(r"\[(?:[^\]|]*\|)?([^\]]*)\]", r"\1", m)


def _item_lines(it):
    out = []
    for key in ("implicitMods", "explicitMods", "craftedMods", "fracturedMods", "enchantMods"):
        for m in it.get(key, []) or []:
            t = mod_text(m)
            if t:
                out += t.split("\n")
    return out


def _prop(it, name):
    for p in it.get("properties", []) or []:
        if p.get("name") == name and p.get("values"):
            return str(p["values"][0][0])
    return ""


def analyze_character(items_json, passives_json, tree_model, act, char_level, boss_level,
                      main_skill="Poisonous Concoction", flask_weapon=True, alira=True):
    """Retorna lista de (status, texto). status: 'ok' | 'warn' | 'bad' | 'info'."""
    res = []
    items = [i for i in (items_json or {}).get("items", []) if i.get("inventoryId") in EQUIP_SLOTS | {"Flask"}]
    equip = [i for i in items if i.get("inventoryId") in EQUIP_SLOTS]
    flasks = [i for i in items if i.get("inventoryId") == "Flask"]

    # nível
    gap = char_level - boss_level
    if gap >= 0:
        res.append(("ok", f"Nível {char_level} (área do chefe ~{boss_level})."))
    elif gap >= -3:
        res.append(("warn", f"Nível {char_level}, chefe ~{boss_level}: um pouco abaixo. Dá, mas vá com cuidado."))
    else:
        res.append(("bad", f"Nível {char_level}, chefe ~{boss_level}: {-gap} níveis abaixo. "
                           "Farme um pouco a área anterior antes."))

    # resistências
    total = {"fire": 0, "cold": 0, "lightning": 0, "chaos": 0}
    for it in equip:
        res_from_lines(_item_lines(it), total)
    if passives_json:
        nodes = (tree_model or {}).get("nodes", {})
        for h in passives_json.get("hashes", []) or []:
            n = nodes.get(str(h))
            if n:
                res_from_lines(n.get("stats", []), total)
        for jw in passives_json.get("items", []) or []:
            res_from_lines(_item_lines(jw), total)
    if alira and act >= 3:
        for k in ("fire", "cold", "lightning"):
            total[k] += 15  # Alira
    penalty = -60 if act >= 11 else (-30 if act >= 6 else 0)
    for k in total:
        total[k] += penalty
    target = 75 if act >= 6 else (50 if act >= 4 else 30)
    names = {"fire": "Fogo", "cold": "Gelo", "lightning": "Raio"}
    low = []
    for k in ("fire", "cold", "lightning"):
        v = min(total[k], 75)
        if v < target:
            low.append(f"{names[k]} {v}% (falta {target - v}%)")
    res_line = " | ".join(f"{names[k]} {min(total[k], 75)}%" for k in ("fire", "cold", "lightning"))
    if not low:
        res.append(("ok", f"Resistências OK: {res_line} (meta {target}%)."))
    else:
        sev = "bad" if any(min(total[k], 75) < target - 25 for k in ("fire", "cold", "lightning")) else "warn"
        res.append((sev, f"Resistências baixas (meta {target}%): " + "; ".join(low) +
                    ". Troque anéis/cinto/botas por peças com resistência."))
    if act >= 7 and total["chaos"] < -30:
        res.append(("warn", f"Caos {total['chaos']}%: atos finais têm bastante dano de caos (ex.: Arakaali)."))

    # skill principal: links e nível da gema
    found = None
    if main_skill:
        key = main_skill.replace(" Support", "").lower()
        for it in equip:
            for g in it.get("socketedItems", []) or []:
                if key in g.get("typeLine", "").lower():
                    found = (it, g)
    else:
        best_links = 0
        for it in equip:
            sockets = it.get("sockets", []) or []
            for g in it.get("socketedItems", []) or []:
                if g.get("support"):
                    continue
                si = g.get("socket", 0)
                grp = sockets[si]["group"] if si < len(sockets) else None
                n = sum(1 for s_ in sockets if s_.get("group") == grp) if grp is not None else 1
                if n > best_links:
                    best_links, found = n, (it, g)
    skill_name = (found[1].get("typeLine") if found else main_skill) or "skill principal"
    if not found:
        if main_skill and (char_level >= 12 or main_skill != "Poisonous Concoction"):
            res.append(("bad", f"Não achei a {main_skill} equipada (skill principal do guia)."))
    else:
        it, g = found
        sockets = it.get("sockets", []) or []
        si = g.get("socket", 0)
        grp = sockets[si]["group"] if si < len(sockets) else None
        links = sum(1 for s_ in sockets if s_.get("group") == grp) if grp is not None else 1
        need = 5 if act >= 6 else (4 if act >= 4 else 3)
        if links >= need:
            res.append(("ok", f"{skill_name} em {links}-link."))
        else:
            hint = (" (o guia dá 5-link grátis: mecânica da liga em Slave Pens e Twilight Strand do Ato 6)."
                    if need == 5 and flask_weapon else " (use Orb of Fusing ou procure um item com mais links).")
            res.append(("warn" if links == need - 1 else "bad",
                        f"{skill_name} em {links}-link; o ideal aqui é {need}-link" + hint))
        lvl_txt = _prop(g, "Level").split(" ")[0]
        try:
            gl = int(lvl_txt)
            if flask_weapon:
                expected = max(1, min(20, 1 + (char_level - 12) // 3))
                if gl + 2 < expected:
                    res.append(("warn", f"{skill_name} no nível {gl} (aprox. esperado {expected}+). "
                                        "Veja se não esqueceu de subir a gema."))
                else:
                    res.append(("ok", f"{skill_name} nível {gl}."))
            else:
                res.append(("info", f"{skill_name} nível {gl} (suba as gemas sempre que puder)."))
        except ValueError:
            pass

    # frasco de vida (é a arma da build)
    best, best_q = None, 0
    for f in flasks:
        base = f.get("baseType") or f.get("typeLine", "")
        for t in LIFE_FLASK_TIERS:
            if f"{t} Life Flask" in base:
                if best is None or LIFE_FLASK_TIERS.index(t) > LIFE_FLASK_TIERS.index(best):
                    best = t
                    q = _prop(f, "Quality").replace("+", "").replace("%", "")
                    best_q = int(q) if q.isdigit() else 0
    if not best:
        res.append(("bad", "Sem frasco de vida equipado!" + (" Na PConc o frasco de vida é a sua ARMA."
                                                              if flask_weapon else "")))
    else:
        avail = [t for t in LIFE_FLASK_TIERS if LIFE_FLASK_LEVEL[t] <= boss_level]
        ideal = avail[-1] if avail else "Small"
        diff = LIFE_FLASK_TIERS.index(ideal) - LIFE_FLASK_TIERS.index(best)
        qtxt = f" com {best_q}% de qualidade" if best_q else " sem qualidade"
        if diff <= 2:
            if flask_weapon:
                res.append(("ok" if best_q else "warn", f"Frasco de vida: {best} Life Flask{qtxt}."
                            + ("" if best_q else " Qualidade = mais dano (use Glassblower's Bauble).")))
            else:
                res.append(("ok", f"Frasco de vida: {best} Life Flask."))
        else:
            res.append(("warn", f"Frasco de vida {best} está velho; já existe {ideal} Life Flask. "
                                + ("Base maior = MAIS DANO na PConc. " if flask_weapon else "Cura mais. ")
                                + "Compre no vendedor."))

    # mobilidade
    if not any("Quicksilver" in (f.get("typeLine", "") + f.get("baseType", "")) for f in flasks):
        res.append(("warn" if flask_weapon else "info",
                    "Sem Quicksilver Flask" + (" (o guia usa um)." if flask_weapon else ": ajuda muito a correr.")))
    boots = next((i for i in equip if i.get("inventoryId") == "Boots"), None)
    ms = 0
    if boots:
        for ln in _item_lines(boots):
            m = re.search(r"(\d+)% increased Movement Speed", ln)
            if m:
                ms += int(m.group(1))
    if ms == 0 and act >= 2:
        res.append(("info", "Botas sem velocidade de movimento: troque assim que achar."))
    return res


def _poe_get(path, params):
    import urllib.request
    import urllib.parse
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"https://www.pathofexile.com/character-window/{path}?{q}",
                                 headers={"User-Agent": "FLPoEHelper/1.0 (leitura do proprio personagem)",
                                          "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def latest_character(account):
    """Personagem jogado por último na conta (usa quando o log ainda não mostrou o nome)."""
    last_err = None
    for acc in (account, account.replace("#", "-")):
        try:
            chars = _poe_get("get-characters", {"accountName": acc, "realm": "pc"})
            if isinstance(chars, list) and chars:
                best = max(chars, key=lambda c: c.get("lastLoginTime") or 0)
                dbg(f"personagens da conta: {[c.get('name') for c in chars]} -> uso {best.get('name')}")
                return best.get("name")
            last_err = "a conta não mostrou personagens (perfil privado?)"
        except Exception as e:
            last_err = str(e)
            dbg(f"get-characters {acc}: {e}")
    raise RuntimeError(last_err or "não achei personagens")


def fetch_character(account, character):
    """Busca itens e passivas do SEU personagem (perfil precisa estar com personagens públicos)."""
    import urllib.request
    import urllib.parse
    import urllib.error
    headers = {"User-Agent": "FLPoEHelper/1.0 (leitura do proprio personagem)"}
    last_err = None
    account = (account or "").strip()
    if not character:
        character = latest_character(account)
    for acc in (account, account.replace("#", "-")):
        try:
            q = urllib.parse.urlencode({"accountName": acc, "character": character, "realm": "pc"})
            out = []
            for ep in ("get-items", "get-passive-skills"):
                req = urllib.request.Request(f"https://www.pathofexile.com/character-window/{ep}?{q}",
                                             headers=headers)
                with urllib.request.urlopen(req, timeout=20) as r:
                    out.append(json.loads(r.read().decode("utf-8")))
            if isinstance(out[0], dict) and out[0].get("items") is not None:
                return out[0], out[1]
            last_err = "resposta sem itens"
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
            if e.code == 403:
                last_err = "HTTP 403: o site recusou a consulta do programa"
            elif e.code == 404:
                last_err = f"HTTP 404: não achei o personagem '{character}' na conta '{account}'"
        except Exception as e:
            last_err = str(e)
        dbg(f"fetch_character conta={acc!r} personagem={character!r}: {last_err}")
    raise RuntimeError(last_err or "erro desconhecido")


def suggested_tree(act, level):
    """Índice (0-based) da árvore sugerida para o ato/nível atual."""
    if act >= 11:
        return 4                      # pós-campanha: troca para Bouncing
    if level < 12:
        return 0
    if act <= 3:
        return 1                      # rumo ao Normal Lab (trials nos atos 1-3)
    if act <= 7:
        return 2                      # rumo ao Cruel Lab (trials nos atos 6-7)
    return 3                          # rumo ao Merciless Lab (trials nos atos 8-10)


# ---------------------------------------------------------------------------
# Gemas por momento (do guia)
# ---------------------------------------------------------------------------
GEMS_BOW = [
    "Caustic Arrow – Mirage Archer – Momentum",
    "Shrapnel Ballista – Pierce",
    "Sniper's Mark (1x no chefe, debuff permanente)",
    "Burning Arrow – Manaforged Arrows (opcional)",
    "Frostblink (nível baixo)",
    "Shield Charge: COMPRE já, só usa no nv 12",
]
GEMS_PCONC_A1 = [
    "PConc – Volley – Void Manipulation – Chance to Poison",
    "Shield Charge (nv 1) – Faster Attacks – Momentum",
    "Withering Step (em cima de chefes)",
    "Clarity",
    "Precision (não suba demais o nível)",
]
GEMS_A2_EXTRA = [
    "Herald of Agony",
    "Arctic Armour (pode tirar Clarity após leech de mana)",
    "Blood Rage (opcional)",
]
GEMS_A3_EXTRA = [
    "Despair (lance nos chefes)",
    "Grace OU Haste (após Charisma)",
    "Plague Bearer (+ Increased AoE se couber)",
    "Malevolence (mais tarde)",
]
GEMS_FINAL = [
    "PConc – Greater Volley – Void Manipulation – Unbound Ailments – Chance to Poison",
    "Shield Charge – Faster Attacks – Momentum",
    "Withering Step | Despair | Precision",
    "Herald of Agony | Grace/Haste | Plague Bearer",
]
GEMS_A6_EXTRA = [
    "Flesh and Stone",
    "Cast when Damage Taken – Steelskin",
]
GEMS_POST = [
    "Troque para Poisonous Concoction of Bouncing",
    "Amuleto Fury Valve só funciona com a versão Bouncing",
    "Frascos: Divine Life x2, Quicksilver, Jade, Stibnite",
    "Pantheon: Brine King (maior) + Gruthkul (menor)",
]


def gems_for(act, level):
    if act >= 11:
        return GEMS_FINAL + GEMS_A6_EXTRA + GEMS_POST
    if act == 1 and level < 12:
        return GEMS_BOW
    if act == 1:
        return GEMS_PCONC_A1
    if act == 2:
        return GEMS_PCONC_A1 + GEMS_A2_EXTRA
    if act == 3:
        return GEMS_PCONC_A1 + GEMS_A2_EXTRA + GEMS_A3_EXTRA
    if act <= 5:
        return GEMS_FINAL
    return GEMS_FINAL + GEMS_A6_EXTRA


# ---------------------------------------------------------------------------
# GUIA ATIVO: "pconc" (incluso) | "pob" (importado do Path of Building) | "none" (sem guia)
# ---------------------------------------------------------------------------
GUIDE = {"mode": "pconc"}

BANDIT_TXT = {
    "Alira": "AJUDAR a Alira (+15% res.) e MATAR Kraityn e Oak",
    "Kraityn": "AJUDAR o Kraityn e MATAR Alira e Oak",
    "Oak": "AJUDAR o Oak e MATAR Alira e Kraityn",
    "None": "MATAR os três (ponto de passiva extra)",
}


def decode_pob_code(code):
    """Código do Path of Building -> XML (texto)."""
    import base64
    import zlib
    code = code.strip().replace("\n", "").replace(" ", "")
    raw = base64.urlsafe_b64decode(code + "=" * (-len(code) % 4))
    return zlib.decompress(raw).decode("utf-8", errors="ignore")


def parse_pob_xml(xml_text):
    """Extrai do XML do PoB: classe, bandido, árvores por fase, gemas por fase e notas."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_text)
    b = root.find("Build")
    battr = b.attrib if b is not None else {}
    trees = []
    for sp in root.iter("Spec"):
        nodes = [int(x) for x in (sp.get("nodes") or "").split(",") if x.strip().isdigit()]
        mast = []
        for pair in re.findall(r"\{(\d+),(\d+)\}", sp.get("masteryEffects") or ""):
            mast.append((int(pair[1]), int(pair[0])))  # (efeito, passiva) - mesmo formato da URL
        url_el = sp.find("URL")
        url = (url_el.text or "").strip() if url_el is not None and url_el.text else ""
        trees.append({"title": sp.get("title") or f"Árvore {len(trees) + 1}", "nodes": nodes,
                      "masteries": mast, "url": url})
    skillsets = []
    sk = root.find("Skills")
    if sk is not None:
        sets = sk.findall("SkillSet") or [sk]
        for ss in sets:
            groups = []
            for skill in ss.findall("Skill"):
                if skill.get("enabled", "true") == "false":
                    continue
                gems = [g.get("nameSpec") or g.get("skillId") or "?" for g in skill.findall("Gem")
                        if g.get("enabled", "true") != "false"]
                if gems:
                    groups.append({"slot": skill.get("slot", ""), "label": skill.get("label", ""), "gems": gems})
            skillsets.append({"title": ss.get("title") or "Gemas", "groups": groups})
    notes_el = root.find("Notes")
    notes = (notes_el.text or "") if notes_el is not None else ""
    notes = re.sub(r"\^x[0-9A-Fa-f]{6}|\^\d", "", notes)[:20000]
    main = None
    if skillsets and skillsets[-1]["groups"]:
        try:
            msg = int(battr.get("mainSocketGroup", "1")) - 1
        except ValueError:
            msg = 0
        grp = skillsets[-1]["groups"][min(max(msg, 0), len(skillsets[-1]["groups"]) - 1)]
        main = grp["gems"][0]
    return {"class": battr.get("className", ""), "asc": battr.get("ascendClassName", ""),
            "bandit": battr.get("bandit", "None") or "None", "trees": trees, "skillsets": skillsets,
            "notes": notes, "main_skill": main}


def fetch_guide_text(text):
    """Aceita: código do PoB, link do Mobalytics, pobb.in ou pastebin. Retorna o código do PoB."""
    import urllib.request
    t = text.strip()
    if not t.lower().startswith("http"):
        return t
    url = t
    m = re.match(r"https?://pobb\.in/([\w-]+)", t)
    if m:
        url = f"https://pobb.in/{m.group(1)}/raw"
    m = re.match(r"https?://pastebin\.com/(?:raw/)?(\w+)", t)
    if m:
        url = f"https://pastebin.com/raw/{m.group(1)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FLPoEHelper)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8", errors="ignore").strip()
    if re.fullmatch(r"[0-9A-Za-z_\-+/=\s]+", body) and len(body) > 200:
        return body
    m = re.search(r"eN[0-9A-Za-z_\-]{300,}={0,2}", body)
    if m:
        return m.group(0)
    raise RuntimeError("não achei o código do Path of Building nessa página")


def import_guide(text):
    code = fetch_guide_text(text)
    data = parse_pob_xml(decode_pob_code(code))
    if not data["trees"]:
        raise RuntimeError("o código não tem árvore de passivas")
    data["source"] = text.strip() if text.strip().lower().startswith("http") else ""
    name = " ".join(x for x in (data["asc"] or data["class"], f"({data['main_skill']})" if data["main_skill"] else "") if x)
    data["name"] = name or "Guia importado"
    return data


def guide_trees():
    """Lista de árvores do guia ativo: [{title, nodes, masteries, url}]."""
    if GUIDE["mode"] == "pconc":
        out = []
        for title, code in TREES:
            d = decode_tree_code(code)
            out.append({"title": title, "nodes": d["nodes"], "masteries": d["masteries"], "url": TREE_BASE + code})
        return out
    if GUIDE["mode"] == "pob":
        return GUIDE.get("trees", [])
    return []


def _title_level(title):
    t = title.lower()
    m = re.search(r"(?:level|lvl|nv|nível|lv)\s*\.?\s*(\d+)\s*[-–a]+\s*(\d+)", t)
    if m:
        return int(m.group(2))
    m = re.search(r"(?:level|lvl|nv|nível|lv)\s*\.?\s*(\d+)", t)
    if m:
        return int(m.group(1))
    m = re.search(r"act\s*(\d+)|ato\s*(\d+)", t)
    if m:
        a = int(m.group(1) or m.group(2))
        return ACT_START_LEVEL.get(min(a + 1, 11), 70)
    for k, v in (("normal", 34), ("cruel", 55), ("merc", 68), ("eternal", 75), ("uber", 85),
                 ("endgame", 90), ("end game", 90), ("final", 90), ("map", 80)):
        if k in t:
            return v
    return None


def guide_suggest(act, level):
    """Índice da fase (árvore/gemas) sugerida para o momento atual."""
    if GUIDE["mode"] == "pconc":
        return suggested_tree(act, level)
    trees = guide_trees()
    if not trees:
        return None
    n = len(trees)
    marks = [_title_level(t["title"]) for t in trees]
    if any(m is not None for m in marks):
        for i, mk in enumerate(marks):
            if mk is not None and mk >= level:
                return i
        last_known = max(i for i, mk in enumerate(marks) if mk is not None)
        return min(n - 1, last_known + (1 if level > (marks[last_known] or 0) and last_known + 1 < n else 0))
    return min(n - 1, round((min(act, 11) - 1) / 10 * (n - 1)))


def guide_gems(act, level, phase_idx=None):
    if GUIDE["mode"] == "pconc":
        return gems_for(act, level)
    if GUIDE["mode"] != "pob":
        return []
    sets = GUIDE.get("skillsets", [])
    if not sets:
        return []
    idx = guide_suggest(act, level) if phase_idx is None else phase_idx
    ss = None
    trees = guide_trees()
    if idx is not None and idx < len(trees):
        title = trees[idx]["title"].strip().lower()
        ss = next((x for x in sets if x["title"].strip().lower() == title), None)
        if ss is None and len(sets) == len(trees):
            ss = sets[idx]
    if ss is None:
        ss = sets[min(idx or 0, len(sets) - 1)]
    out = []
    for g in ss["groups"]:
        line = " – ".join(g["gems"])
        if g.get("slot"):
            line += f"   [{g['slot']}]"
        out.append(line)
    return out


def guide_regexes():
    if GUIDE["mode"] == "pconc":
        return REGEXES
    return [("Vendedor: itens com links e botas com movimento", "-[rgbw]-|Runn")]


def guide_bandit():
    if GUIDE["mode"] == "pconc":
        return "Alira"
    if GUIDE["mode"] == "pob":
        return GUIDE.get("bandit", "None")
    return "None"


def guide_name():
    if GUIDE["mode"] == "pconc":
        return "Guia de exemplo: PConc of Bouncing Pathfinder"
    if GUIDE["mode"] == "pob":
        return GUIDE.get("name", "Guia importado")
    return "Sem guia (só dicas dos atos)"


# ---------------------------------------------------------------------------
# Passo a passo por ato (checklist)
# ---------------------------------------------------------------------------
# Passo a passo por ato. Cada passo: (texto, área que prova que ele foi feito)
# A área é (nome no log, ato). Quando você entra nela, o passo é marcado sozinho.
# None = só dá para marcar na mão (ex.: comprar uma gema).
STEPS_PCONC = {
    1: [
        ("Matar Hillock e entrar na cidade", ("Lioneye's Watch", 1)),
        ("Montar setup de arco (Caustic Arrow/Ballista) e comprar Frostblink", ("The Coast", 1)),
        ("Mud Flats: 3 ovos dos Rhoas → Submerged Passage", ("The Submerged Passage", 1)),
        ("Na cidade: COMPRAR Shield Charge (Força sobe se atrasar)", None),
        ("Lower Prison: fazer o TRIAL", ("The Upper Prison", 1)),
        ("Matar Brutus", ("Prisoner's Gate", 1)),
        ("Nv 12 / Cavern of Wrath: pegar Poisonous Concoction", ("The Cavern of Wrath", 1)),
        ("Trocar TUDO para PConc (sem arma) + Withering Step, Clarity, Precision", ("The Cavern of Anger", 1)),
        ("Matar Merveil", ("The Southern Forest", 2)),
    ],
    2: [
        ("Pegar Herald of Agony (e Arctic Armour se couber)", ("The Old Fields", 2)),
        ("Chamber of Sins 2: TRIAL + Fidelitas", ("The Broken Bridge", 2)),
        ("Broken Bridge: MATAR o Kraityn", ("The Fellshrine Ruins", 2)),
        ("Crypt: TRIAL + Golden Hand", ("The Riverways", 2)),
        ("Western Forest: AJUDAR A ALIRA (+15% res.)", ("The Weaver's Chambers", 2)),
        ("Wetlands: MATAR o Oak", ("The Vaal Ruins", 2)),
        ("Matar o Vaal Oversoul", ("The City of Sarn", 3)),
    ],
    3: [
        ("City of Sarn: Guard Captain + falar com a Clarissa", ("The Sarn Encampment", 3)),
        ("Crematorium: TRIAL + Piety", ("The Sewers", 3)),
        ("Sewers: 3 bustos (+1 passiva)", ("The Marketplace", 3)),
        ("Catacombs: TRIAL", ("The Battlefront", 3)),
        ("Pegar Despair, Plague Bearer e Grace/Haste", None),
        ("Library (Siosa): comprar Unbound Ailments", ("The Archives", 3)),
        ("Imperial Gardens: último TRIAL → NORMAL LAB (Nature's Reprisal)", ("The Sceptre of God", 3)),
        ("Matar Dominus", ("The Aqueduct", 4)),
    ],
    4: [
        ("Montar: PConc – Greater Volley – Void Manip – Unbound Ailments – Chance to Poison", ("The Dried Lake", 4)),
        ("Matar Voll e abrir as Minas", ("The Mines Level 1", 4)),
        ("Matar Kaom e Daresso", ("The Belly of the Beast Level 1", 4)),
        ("Melhorar o frasco de vida (é a sua arma)", None),
        ("Matar Malachai", ("The Ascent", 4)),
    ],
    5: [
        ("Slave Pens: mecânica da liga → 5-link grátis", ("Overseer's Tower", 5)),
        ("Templar Courts → Innocence", ("The Torched Courts", 5)),
        ("Ossuary e Reliquary", ("The Cathedral Rooftop", 5)),
        ("Matar Kitava (depois: -30% res → recapear)", ("Lioneye's Watch", 6)),
    ],
    6: [
        ("Twilight Strand: matar todos + mecânica da liga (2º 5-link)", ("The Coast", 6)),
        ("Lily: Flesh and Stone, CwDT + Steelskin, Unbound Ailments", None),
        ("Lower Prison: TRIAL (Cruel Lab)", ("Shavronne's Tower", 6)),
        ("Abberath e Ryslatha", ("The Southern Forest", 6)),
        ("Matar o Brine King", ("The Bridge Encampment", 7)),
    ],
    7: [
        ("Crypt: TRIAL + Maligaro's Map", ("The Chamber of Sins Level 1", 7)),
        ("Chamber of Sins 2: TRIAL → CRUEL LAB (Master Toxicist)", ("The Den", 7)),
        ("Greust e Gruthkul (pegue os 7 vaga-lumes)", ("The Causeway", 7)),
        ("Matar Arakaali", ("The Sarn Ramparts", 8)),
    ],
    8: [
        ("Matar Doedre", ("The Quay", 8)),
        ("Matar Dawn (Sun Orb)", ("The Grand Promenade", 8)),
        ("Bath House: TRIAL", ("The High Gardens", 8)),
        ("Matar Dusk (Moon Orb)", ("The Harbour Bridge", 8)),
        ("Matar Solaris e Lunaris", ("The Blood Aqueduct", 9)),
    ],
    9: [
        ("Vastiri Desert e Oasis (Shakari)", ("The Foothills", 9)),
        ("Tunnel: TRIAL", ("The Quarry", 9)),
        ("Adus e Garukhan", ("The Belly of the Beast", 9)),
        ("Matar a Depraved Trinity", ("Oriath Docks", 10)),
    ],
    10: [
        ("Control Blocks: Vilenta (+1 passiva)", ("The Ossuary", 10)),
        ("Ossuary: TRIAL → MERCILESS LAB (Nature's Adrenaline)", ("The Torched Courts", 10)),
        ("Matar Avarius", ("The Canals", 10)),
        ("Matar Kitava (depois: mais -30% res → recapear)", ("Karui Shores", 11)),
    ],
    11: [
        ("Trocar para Poisonous Concoction of Bouncing", None),
        ("Usar a árvore 5) Troca p/ PConc of Bouncing", None),
        ("Pantheon: Brine King + Gruthkul", None),
        ("Frascos: Divine Life x2, Quicksilver, Jade, Stibnite", None),
        ("Eternal Lab → Master Surgeon", None),
        ("Mapas: evitar Legion; bons: Expedition, Abyss, Essence, Strongbox, Heist", None),
    ],
}


def _bandit_line(who, bandit):
    return f"AJUDAR {'a' if who == 'Alira' else 'o'} {who}" if bandit == who else f"MATAR {'a' if who == 'Alira' else 'o'} {who}"


def make_generic_steps(bandit):
    """Passo a passo da campanha sem nada específico de build (rota + chefes + trials + bandidos)."""
    repl = {
        (1, 1): ("Pegar a 1ª gema com o Tarkleigh e ir para The Coast", ("The Coast", 1)),
        (1, 3): None,
        (1, 6): ("Chegar na Cavern of Wrath (waypoint)", ("The Cavern of Wrath", 1)),
        (1, 7): ("Atravessar a Cavern of Anger até o Merveil", ("The Cavern of Anger", 1)),
        (2, 0): ("Chegar na cidade e seguir para The Old Fields", ("The Old Fields", 2)),
        (2, 2): (f"Broken Bridge: {_bandit_line('Kraityn', bandit)}", ("The Fellshrine Ruins", 2)),
        (2, 4): (f"Western Forest: {_bandit_line('Alira', bandit)}", ("The Weaver's Chambers", 2)),
        (2, 5): (f"Wetlands: {_bandit_line('Oak', bandit)}", ("The Vaal Ruins", 2)),
        (3, 4): None,
        (3, 5): ("Library + Archives: a Siosa libera muitas gemas", ("The Archives", 3)),
        (4, 0): ("Chegar em Highgate", ("Highgate", 4)),
        (4, 3): None,
        (5, 0): ("Slave Pens → Overseer Krow", ("Overseer's Tower", 5)),
        (6, 0): ("Twilight Strand: matar todos os monstros", ("The Coast", 6)),
        (6, 1): ("Lily: libera todas as gemas — monte o setup do seu guia", None),
    }
    out = {}
    for act, lst in STEPS_PCONC.items():
        if act == 11:
            continue
        new = []
        for i, st in enumerate(lst):
            r = repl.get((act, i), st)
            if r is not None:
                new.append(r)
        out[act] = new
    out[11] = [
        ("Eternal Lab (4ª ascendência)", None),
        ("Montar o setup de endgame (gemas, árvore, itens)", None),
        ("Mapas: completar o Atlas rumo aos 4 Voidstones", None),
    ]
    return out


STEPS = STEPS_PCONC


def step_key(act, i):
    return f"{'s2' if GUIDE['mode'] == 'pconc' else 'g2'}:{act}:{i}"


# Dicas de navegação que mudam fora do guia da PConc
def _nav_generic(bandit):
    return {
        ("The Broken Bridge", 2): f"Siga o caminho (waypoint no meio) até a ponte quebrada: {_bandit_line('Kraityn', bandit)}"
                                  " e pegue o amuleto se matar.",
        ("The Western Forest", 2): "Waypoint no caminho, Captain Arteri no fim (encaixe o emblema na parede). Siga as "
                                   f"TOCHAS fora do caminho até a Alira: {_bandit_line('Alira', bandit)}. "
                                   "Weaver's Chambers no lado oposto.",
        ("The Wetlands", 2): f"Vá para o norte até o acampamento do Oak: {_bandit_line('Oak', bandit)}. "
                             "Vaal Ruins fica na parede perto do waypoint.",
        ("The Library", 3): "Ache a Siosa e o waypoint. Procure a vela solta ('Loose Candle') → Archives. "
                            "Depois a Siosa libera muitas gemas.",
        ("The Slave Pens", 5): "Fique bem à DIREITA, desça até o canto inferior direito e depois sudoeste até o "
                               "Overseer Krow.",
        ("The Twilight Strand", 6): "Mate TODOS os monstros (contador aparece com ≤5). Depois a Lily libera as gemas.",
    }


def nav_for(zone, act):
    if GUIDE["mode"] != "pconc":
        g = _nav_generic(guide_bandit()).get((zone, act))
        if g:
            return g
    return ZONE_NAV.get((zone, act), "")


# Voidstones da 3.30, na ordem recomendada de conquista (quadrante do Atlas entre parênteses).
# Atenção: Exarch e Eater dão UMA pedra só (a Eldritch), não duas.
VOIDSTONES = [
    "1ª Eldritch (canto inf. esquerdo) — matar Searing Exarch E Eater of Worlds",
    "2ª Originator (canto sup. esquerdo) — matar Incarnation of Dread",
    "3ª Decayed (canto sup. direito) — matar Shaper e Elder",
    "4ª Ceremonial (canto inf. direito) — matar The Maven",
]

# ---------------------------------------------------------------------------
# Como farmar divine em cada etapa do Atlas (liga 3.30 Covens of Umbra)
# ---------------------------------------------------------------------------
# Cada etapa: (título, resumo, [dicas]). O programa escolhe pela quantidade de
# Voidstones marcadas no checklist.
FARM_STAGES = [
    ("Etapa 0 — Sem Voidstone: juntar o primeiro capital",
     "Mapas brancos e amarelos. Aqui o objetivo não é divine, é VELOCIDADE: quanto antes chegar "
     "nas 2 primeiras pedras, antes o dinheiro começa de verdade.",
     [
         "Receita do caos é a sua base de renda agora: junte o set completo nível 60+ "
         "(arma, elmo, peito, luvas, botas, cinto, amuleto, 2 anéis) e venda. Não identificado vale mais.",
         "Árvore do Atlas: pegue primeiro os 3 nós de Essence, depois os nós de queda de mapa (para subir "
         "de tier), volte nos de Essence e termine nos de Strongbox.",
         "Corra para os mapas amarelos: mapa branco só solta Essence até Screaming; amarelo libera Shrieking, "
         "que vale bem mais.",
         "Antes de abrir o mapa, leia os mods: nada de 'no leech', 'reduced recovery' ou reflect de caos "
         "com a PConc. Um mapa ruim custa mais caro do que o tempo de rerrolar.",
         "Missões Eldritch e bônus de conclusão vêm antes de tudo. Deixe o farm bonito para depois.",
         "Venda o lixo útil no Faustus (Currency Exchange) em vez de deixar parado na aba.",
     ]),
    ("Etapa 1 — 1ª Voidstone (Eldritch): subir de tier",
     "Com a Eldritch encaixada os mapas daquele quadrante sobem de tier. Agora dá para começar a "
     "escolher uma mecânica e repetir.",
     [
         "Rota das pedras: canto inferior esquerdo (Exarch/Eater) → superior esquerdo (Incarnation) → "
         "superior direito (Shaper/Elder) → inferior direito (Maven). Essa ordem é da mais fácil para a mais difícil.",
         "Exarch e Eater não precisam de fragmento: eles abrem sozinhos conforme você corre mapas. "
         "Corra até o Envoy aparecer.",
         "Priorize 'Destructive Play' na árvore do Atlas: é o nó que invoca os chefes e acelera as pedras.",
         "Se a build ainda está fraca para mapa vermelho, rode como MÁGICO (azul) em vez de raro corrompido. "
         "Você perde o ponto de passiva, mas a missão conta e você chega nos chefes muito antes.",
         "Comece a escolher UMA mecânica para repetir. Para Pathfinder rápida: Essence, Abyss ou Expedition.",
     ]),
    ("Etapa 2 — 2 Voidstones: o dinheiro começa de verdade",
     "Esta é a virada. O que você ganha depois das duas primeiras pedras é muito maior do que tudo "
     "que veio antes. Hora de parar de 'alch and go' e montar uma estratégia.",
     [
         "Escolha uma estratégia e repita 50+ mapas antes de julgar. Trocar toda hora é o que mais faz "
         "gente ficar pobre.",
         "Harvest (reformulado na 3.30): o Sacred Grove acabou; agora você caça Sacred Flora dentro dos mapas "
         "normais e junta Lifeforce. Relatos da primeira semana colocam o alch-and-go de Harvest em T16 como "
         "uma das estratégias mais lucrativas da liga.",
         "Abyss: funciona com build meia-boca e em tier baixo. Tem relato de 50 mapas T1 rendendo alguns "
         "divines em drop puro mais uns 190 caos em itens.",
         "Expedition continua sendo renda sólida e previsível, boa para quem não quer depender de sorte.",
         "Threads of Creation: na 3.30 os Scarabs acabaram e foram trocados por Threads, que turbinam uma "
         "mecânica específica (Legion, Blight, Expedition...). Invista os Threads na SUA mecânica, não espalhe.",
         "A mecânica da liga (Covens of Umbra) solta divine nos chefes empoderados e os Remains. Vale fazer "
         "de passagem, se a sua build mata o chefe rápido. Se travar o mapa, pule.",
     ]),
    ("Etapa 3 — 3 Voidstones: escalar e investir",
     "Quase todos os mapas em T16. Agora o lucro vem de investir currency no mapa antes de abrir, "
     "não de correr mais rápido.",
     [
         "Pare de rodar mapa cru. Invista: Threads na sua mecânica, mapa bem rolado e a árvore do Atlas "
         "toda comprometida com UMA coisa.",
         "Shaped Regions garantem a mecânica que você quer dentro da região. Use isso para nunca abrir um "
         "mapa sem a sua mecânica dentro.",
         "Ritual com Mirage é uma das estratégias mais fortes da 3.30: a janela de recompensa mostra divine, "
         "ancient orb, cartas e bases boas, e você escolhe o que levar.",
         "Faça a conta: anote quantos divines você tira por hora. Se uma estratégia não paga o investimento "
         "em 10 mapas, ela não é a sua.",
         "Venda em bloco (bulk) no Currency Exchange. Vender de 1 em 1 no trade é onde o tempo evapora.",
     ]),
    ("Etapa 4 — 4 Voidstones: Atlas completo",
     "Tudo em T16. A partir daqui a renda vem de chefe, de mecânica turbinada ao máximo e de crafting.",
     [
         "Farm de chefe pinnacle: junte fragmentos e venda as carries, ou mate você mesmo. Maven e Uber "
         "são onde estão os drops caros.",
         "Nightmare Maps: cada Voidstone encaixada dá chance de o mapa T16 virar Nightmare. Com as 4, essa "
         "chance é a maior possível. Não jogue esses mapas fora.",
         "Invista pesado em uma só mecânica, com Threads, Shaped Region e a árvore inteira voltada para ela.",
         "Troque farm por crafting: com Lifeforce e essências sobrando, dá mais lucro criar o item do que "
         "vender o material.",
         "Reinvista até uns 50 divines na build. Depois disso, pense se vale subir a PConc ou começar outro "
         "personagem: o guia sugere considerar a troca nesse ponto.",
     ]),
]

# ---------------------------------------------------------------------------
# Escada de upgrades por orçamento (PConc of Bouncing Pathfinder)
# ---------------------------------------------------------------------------
# (faixa, título, o que o jogo exige nessa hora, [o que comprar, em ordem])
# Os preços mudam toda semana: use Ctrl+D em cima do item para ver o preço de hoje.
BUDGET_STAGES = [
    (0, "0 divine — primeiro arrume o básico (nada de item caro ainda)",
     "O jogo aqui não exige item caro, exige que você não morra. Resistência e vida valem mais do "
     "que qualquer unique neste momento.",
     [
         "CAPAR as 3 resistências elementais em 75%. Isso vem de raro barato, não de divine. "
         "Use o Boss? do programa para conferir antes de cada chefe.",
         "Vida: mire 3.000+ para entrar em mapas amarelos, 4.000+ para vermelhos.",
         "5-link na Poisonous Concoction já serve. 6-link pode esperar.",
         "Frascos certos: Life Flask é obrigatório (a PConc consome carga dele), Quicksilver, "
         "e um de antídoto para curse/freeze.",
         "Mark of Submission (anel): custa quase nada e dá curse automático. Compre já.",
         "Cloak of Flame (peito): barato e segura muito dano físico até você ter grana.",
     ]),
    (1, "1 divine — os dois itens que mudam o dano",
     "A build já roda. Agora o jogo começa a exigir dano para os mapas amarelos não demorarem.",
     [
         "Fury Valve (amuleto): é O item da variante Bouncing. Faz os projéteis ricochetearem. "
         "Se só der para comprar um item, compre este.",
         "Medium Cluster Jewel com Follow Through: dano grande por pouco dinheiro.",
         "Gemas de qualidade 20% e nível 20: barato e dá dano de graça.",
         "Sobrou? Jóias comuns com vida + resistência para liberar espaço na árvore.",
     ]),
    (5, "5 divines — sobrevivência para mapas vermelhos",
     "Mapa vermelho e os primeiros chefes de Atlas exigem que você aguente um hit. É aqui que a "
     "maioria empaca e fica morrendo.",
     [
         "Doppelgänger Guise (peito, modo Sane): troca do Cloak of Flame, sobe muito a defesa.",
         "Death Rush e/ou Betrayal's Sting (anéis). Use Noxious Catalyst no Betrayal's para subir o caos.",
         "Chaos Resistance positiva: a partir daqui o dano de caos começa a matar de surpresa.",
         "Botas com 30% de movimento e vida. Barato e você sente na hora.",
         "6-link na PConc, se ainda não tiver.",
     ]),
    (10, "10 divines — o salto de qualidade",
     "Com o Atlas andando, o jogo exige dano sustentado e capacidade de matar chefe de mapa sem "
     "tomar 3 minutos.",
     [
         "Watcher's Eye: escolha pelo que falta. Grace = evasão, Precision = velocidade de ataque, "
         "Malevolence = DoT multiplier (o mais caro e o melhor para veneno).",
         "Ancestral Vision (jóia): imunidade a ailment elemental. Resolve congelar e chocar de uma vez.",
         "Brutal Restraint (Asenath) com notáveis bons: dano e utilidade no mesmo slot.",
         "Eternal Lab para a 4ª ascendência (Master Surgeon), se ainda não fez. Não custa divine, "
         "custa tempo, e vale mais que item nesta faixa.",
         "Jóias com % de vida máxima + dano de caos.",
     ]),
    (25, "25 divines — luxo e conforto",
     "A build já faz todo o conteúdo normal. O que o jogo exige agora é consistência para farmar "
     "sem morrer e sem parar.",
     [
         "Progenesis (frasco): um dos maiores saltos de sobrevivência do jogo.",
         "The Tides of Time: conforto e defesa.",
         "The Light of Meaning (jóia) se você foi pela variante de dano de caos.",
         "Opcional: Beacon of Madness para o setup Explode, com troca de escudo.",
         "Enchant no elmo e corrupções boas nos uniques.",
     ]),
    (50, "50+ divines — hora de decidir",
     "A PConc já deu o que tinha que dar. A partir daqui cada divine rende pouco nela.",
     [
         "O próprio guia sugere parar por volta de 50 divines e pensar se vale continuar subindo "
         "esta build ou começar outro personagem (ex.: Viper Strike of the Mamba).",
         "Se continuar: jóias perfeitas, Watcher's Eye com 2 mods bons, itens corrompidos de alto rolo.",
         "Se trocar: guarde a currency, não venda os uniques baratos — você reusa no próximo.",
         "Uber bosses: a partir daqui dá para começar a tentar, mas confira o Boss? antes.",
     ]),
]


def budget_stage(divines):
    """Etapa da escada de upgrades para a quantidade de divines informada."""
    cur = BUDGET_STAGES[0]
    for st in BUDGET_STAGES:
        if divines >= st[0]:
            cur = st
    return cur


FARM_FOOTER = ("⚠ A economia muda toda semana. Antes de investir pesado, confira os preços no poe.ninja e "
               "o que está rendendo agora (maxroll, reddit da liga). Estas dicas são do começo da 3.30.")


def farm_stage(n_stones):
    """Dicas de farm conforme quantas Voidstones já foram marcadas (0 a 4)."""
    return FARM_STAGES[max(0, min(len(FARM_STAGES) - 1, n_stones))]

UPGRADES = [
    "Fury Valve (amuleto) — só funciona com PConc of Bouncing",
    "Medium Cluster Jewel com Follow Through",
    "Mark of Submission (anel, ótimo no começo)",
    "Death Rush e/ou Betrayal's Sting (use Noxious Catalyst no Betrayal's)",
    "Corpo: Cloak of Flame → Doppelgänger Guise (sempre no modo Sane)",
    "Watcher's Eye (Grace: evasão | Precision: attack speed | Malevolence: DoT multi)",
    "Ancestral Vision (evitar ailments elementais)",
    "The Light of Meaning (variante Chaos Damage)",
    "Brutal Restraint (Asenath) com notáveis úteis",
    "Eternal Lab → Master Surgeon",
    "Opcional: Beacon of Madness (setup Explode, com troca de escudo)",
    "Luxo: Progenesis + The Tides of Time",
    "Parar em ~50 divines e pensar em trocar (ex.: Viper Strike of the Mamba)",
]

REGEXES = [
    ("Vendedor Ato 1 (itens + todas as gemas do Ato 1)",
     '"l ba|nafo|sn.*mar|stbl|s conc|d mani|ley s|her.*ago|prec|arct.*ar|g step|od ra|desp|unb|race|'
     'ter at|h and s|ld cha|gr.*le pro|hex b|pois.*su|rce s|ge arch|-[rgbw]-|Runn|s:.+sh"'),
    ("Vendedor: só itens (links, movimento etc.)", "-[rgbw]-|Runn|s:.+sh"),
    ("Mapas: mods ruins para a build", '"!ced f|ter e|son,|from$"'),
]

HOTKEYS = {"Nenhuma": None, "F6": 0x75, "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
           "Pause": 0x13, "Scroll Lock": 0x91}

ACT_NAMES = {i: f"Ato {i}" for i in range(1, 11)}
ACT_NAMES[11] = "Pós-campanha"

# ---------------------------------------------------------------------------
# Avisos automáticos por área (aparecem na faixa amarela)
# ---------------------------------------------------------------------------
ZONE_TIPS = {
    ("The Mud Flats", 1): "Ao voltar à cidade: COMPRE Shield Charge agora!",
    ("The Cavern of Wrath", 1): "Aqui você desbloqueia Poisonous Concoction. Troque tudo no nível 12.",
    ("The Library", 3): "Fale com Siosa: compre Unbound Ailments.",
    ("The Slave Pens", 5): "Faça a mecânica da liga aqui para o 5-link grátis.",
    ("The Twilight Strand", 6): "Faça a mecânica da liga aqui para o 2º 5-link.",
    ("Lioneye's Watch", 6): "Lily: Flesh and Stone, CwDT + Steelskin, Unbound Ailments.",
    ("Oriath", 11): "Campanha concluída! Troque para PConc of Bouncing.",
    ("Karui Shores", 11): "Campanha concluída! Troque para PConc of Bouncing.",
    ("Aspirants' Plaza", 0): "Labirinto: siga a ordem Reprisal → Toxicist → Adrenaline → Surgeon.",
}

# ---------------------------------------------------------------------------
# Dicas de navegação por área (baseadas no guia de campanha do Mobalytics, por Ignatius)
# Chave: (nome da área como aparece no log, ato)
# ---------------------------------------------------------------------------
ZONE_NAV = {
    # ---------------- ATO 1 ----------------
    ("The Twilight Strand", 1): "Suba pela praia pegando arma e gemas. Mate o Hillock no fim e entre na cidade.",
    ("Lioneye's Watch", 1): "Pegue a 1ª gema com Tarkleigh. Saída para The Coast fica no lado norte.",
    ("The Coast", 1): "Pegue o waypoint e PULE Tidal Island por enquanto. Siga direto para The Mud Flats.",
    ("The Mud Flats", 1): "Pule Fetid Pool. Mate os Rhoas, pegue 3 ovos e coloque na parede do outro lado → Submerged Passage. Cuidado com a investida dos Rhoas (ande de lado).",
    ("The Submerged Passage", 1): "1ª vez: pegue o waypoint e vá à cidade, depois faça Tidal Island. 2ª vez: siga até Flooded Depths (buraco no chão) ou The Ledge.",
    ("The Tidal Island", 1): "Mate o Hailrake no fundo da área (Mercy Mission) → Quicksilver Flask.",
    ("The Flooded Depths", 1): "Procure o Dweller of the Deep e mate → +1 ponto de passiva.",
    ("The Ledge", 1): "Área linear, waypoint no meio. Depois do waypoint, 3 pedras em triângulo apontam para a saída.",
    ("The Climb", 1): "Waypoint perto do início, um pouco de lado. Porta na parede do fundo → Lower Prison.",
    ("The Lower Prison", 1): "Waypoint no início (volte e compre as gemas de nv 8). Faça o TRIAL aqui. Depois → Upper Prison.",
    ("The Upper Prison", 1): "Strongbox 'atrás da parede': ache o SWITCH num pilar perto dela para abrir (frascos). Depois procure Warden's Quarters.",
    ("The Warden's Quarters", 1): "Siga o corredor longo até o fim, volte por um corredor paralelo e suba pelas salinhas. Brutus no final.",
    ("Prisoner's Gate", 1): "Waypoint logo no início. O fim do caminho principal é falso (Piety fecha). Volte perto do início e contorne pela parede → Ship Graveyard.",
    ("The Ship Graveyard", 1): "Pegue o waypoint e procure a caverna (Ship Graveyard Cave) perto de um navio afundado no centro. Depois: Fairgraves e a entrada na parede → Cavern of Wrath.",
    ("The Ship Graveyard Cave", 1): "Siga reto para longe da entrada, mate Stranglecharm e pegue o Allflame. Saída na parede atrás dela.",
    ("The Cavern of Wrath", 1): "Waypoint no início. Área de passagem até Cavern of Anger.",
    ("The Cavern of Anger", 1): "Vá até o fundo da área: entrada na parede → Merveil (chefe de gelo). Fuja dos ciclones.",
    # ---------------- ATO 2 ----------------
    ("The Southern Forest", 2): "Siga para o norte até a entrada da cidade (Forest Encampment).",
    ("The Forest Encampment", 2): "Saia pelo NORTE (não pelo sul) → The Old Fields.",
    ("The Old Fields", 2): "Siga o caminho. The Den é opcional.",
    ("The Crossroads", 2): "Waypoint no centro. Ordem: 1) Noroeste → Chamber of Sins, 2) Nordeste → Broken Bridge, 3) Sudeste → Fellshrine Ruins.",
    ("The Chamber of Sins Level 1", 2): "Waypoint geralmente no centro. Procure a escada para o Nível 2.",
    ("The Chamber of Sins Level 2", 2): "TRIAL fica no lado oposto ao chefe: faça o trial primeiro. Fidelitas no fim de um corredor longo e estreito.",
    ("The Broken Bridge", 2): "Siga o caminho (waypoint no meio) até a ponte quebrada: MATE o Kraityn e pegue o amuleto dele.",
    ("The Fellshrine Ruins", 2): "Área enorme: NÃO saia do caminho. No fim, passe o arco e vá um pouco ao norte → The Crypt.",
    ("The Crypt Level 1", 2): "Waypoint no início e TRIAL aqui. Depois desça para o Nível 2.",
    ("The Crypt Level 2", 2): "Objetivo no lado oposto ao início: Archbishop Geofri e o altar com a Golden Hand → +1 passiva.",
    ("The Riverways", 2): "Siga o caminho principal até o waypoint (meio). Continue até Western Forest; o desvio para Wetlands você faz depois.",
    ("The Western Forest", 2): "Waypoint no caminho, Captain Arteri no fim (encaixe o emblema na parede). Siga as TOCHAS fora do caminho até a ALIRA: AJUDE A ALIRA (build). Weaver's Chambers no lado oposto.",
    ("The Weaver's Chambers", 2): "Procure a entrada do Weaver's Nest e mate a Weaver.",
    ("The Wetlands", 2): "Vá para o norte até o acampamento do Oak: MATE o Oak e pegue o amuleto. Vaal Ruins fica na parede perto do waypoint.",
    ("The Vaal Ruins", 2): "Labirinto grande: ache o selo roxo (Ancient Seal), clique e saia pela parede → Northern Forest.",
    ("The Northern Forest", 2): "Waypoint perto da entrada. Dread Thicket (hideout, só 1x) ao sul. Siga para o norte → The Caverns.",
    ("The Dread Thicket", 2): "Só se ainda não tem hideout: ache o ícone de flor-de-lis e mate Aidan e Nadia.",
    ("The Caverns", 2): "Contorne por baixo até o waypoint e a porta (precisa da Apex, recebida após resolver os 3 bandidos). Depois norte até a escada da Pirâmide.",
    ("The Ancient Pyramid", 2): "Suba as escadas a cada andar. No topo, clique no altar e espere: Vaal Oversoul.",
    # ---------------- ATO 3 ----------------
    ("The City of Sarn", 3): "OBRIGATÓRIO: mate o Guard Captain e fale com a Clarissa. Depois norte → cidade.",
    ("The Sarn Encampment", 3): "NÃO entre na Arena (PvP, norte). Saída para The Slums no nordeste da cidade.",
    ("The Slums", 3): "Note o portão trancado do esgoto (volta depois). Siga até The Crematorium.",
    ("The Crematorium", 3): "Faça o TRIAL e mate a Piety. Pegue o Tolman's Bracelet e entregue à Clarissa (chave do esgoto).",
    ("The Sewers", 3): "Abra os 3 baús ('Stash') e pegue os 3 bustos → +1 passiva. Pegue o waypoint (bloqueio perto dele). Ignore Cassia. Saída no fundo → Marketplace.",
    ("The Marketplace", 3): "Ache o beco com estátuas grandes → waypoint. Catacombs (trial) perto do waypoint. Depois norte e encoste na parede de cima para o OESTE → Battlefront.",
    ("The Catacombs", 3): "Só para o TRIAL. Volte pelo waypoint.",
    ("The Battlefront", 3): "Norte até o waypoint (centro). Baú Blackguard ao lado (geralmente sudoeste) → Ribbon Spool. Oeste e norte → Docks; depois nordeste → Solaris Temple.",
    ("The Docks", 3): "Ignore Fairgraves. Procure um píer com Supply Container → Thaumetic Sulphite.",
    ("The Solaris Temple Level 1", 3): "Área linear com waypoint no meio. Desça para o Nível 2.",
    ("The Solaris Temple Level 2", 3): "Siga o TAPETE até a Lady Dialla (perto do waypoint) → Infernal Talc. Depois volte ao esgoto e queime o bloqueio.",
    ("The Ebony Barracks", 3): "Waypoint ao norte, logo no início. Siga ao norte e mate o General Gravicius. Noroeste → Lunaris Temple; depois do waypoint → Imperial Gardens.",
    ("The Lunaris Temple Level 1", 3): "Siga os tapetes até o waypoint e a escada para o Nível 2.",
    ("The Lunaris Temple Level 2", 3): "Procure as pontes longas com escada. Nos CARRINHOS: o lado com 1 carrinho é o certo (2 = errado). Depois as jaulas e o portão dourado → Piety.",
    ("The Imperial Gardens", 3): "Fique na trilha de pedra até o waypoint. 1) Noroeste → Library, 2) Nordeste → TRIAL, 3) Leste → Sceptre of God.",
    ("The Library", 3): "Ache a Siosa e o waypoint. Procure a vela solta ('Loose Candle') → Archives. COMPRE Unbound Ailments com a Siosa.",
    ("The Archives", 3): "Pegue as 4 Golden Pages (estantes em salas sem saída, marcadas com ! no minimapa).",
    ("The Sceptre of God", 3): "3 andares: procure as escadas até o topo.",
    ("The Upper Sceptre of God", 3): "Mais 3 andares; a porta final na parede leva ao Dominus.",
    # ---------------- ATO 4 ----------------
    ("The Aqueduct", 4): "Duas pontes paralelas: quando uma fechar, passe para a outra. Highgate no fim da ponte da esquerda.",
    ("Highgate", 4): "Dried Lake fica no canto sudoeste da cidade.",
    ("The Dried Lake", 4): "Vá ao sul e oeste até o acampamento do Voll. Pegue o Deshret's Banner e use no selo ao norte da cidade.",
    ("The Mines Level 1", 4): "Siga o caminho principal até a descida. Ignore Niko.",
    ("The Mines Level 2", 4): "Siga os trilhos até o ! (Deshret's Spirit) → +1 passiva. Depois → Crystal Veins.",
    ("The Crystal Veins", 4): "Siga até o waypoint e a Lady Dialla. Kaom's Dream e Daresso's Dream ficam ao lado dela.",
    ("Kaom's Dream", 4): "No início vá toda para a DIREITA, suba a escada e volte toda para a ESQUERDA. Depois norte → Kaom's Stronghold.",
    ("Kaom's Stronghold", 4): "Waypoint no início. Encoste na parede da ESQUERDA e vá para o norte até o Kaom.",
    ("Daresso's Dream", 4): "Siga o caminho principal pelos becos. Arena do Barkhul → Grand Arena.",
    ("The Grand Arena", 4): "Waypoint no início. A saída de cada arena fica sempre ao NORTE. Daresso no Ring of Blades.",
    ("The Belly of the Beast Level 1", 4): "Faça upgrades antes. Vá para o norte-centro: entrada na parede para o Nível 2.",
    ("The Belly of the Beast Level 2", 4): "Vá para o norte e à esquerda → Piety (desvie do raio giratório).",
    ("The Harvest", 4): "Siga o túnel até o waypoint. Faça a volta matando Shavronne, Doedre e Maligaro e leve os 3 órgãos à Piety.",
    ("The Ascent", 4): "Norte (um pouco a oeste) até a ponte longa, siga o gelo até a parede, depois oeste até o ressonador → Slave Pens.",
    # ---------------- ATO 5 ----------------
    ("The Slave Pens", 5): "Fique bem à DIREITA, desça até o canto inferior direito e depois sudoeste até o Overseer Krow. (Faça a mecânica da liga para o 5-link.)",
    ("Overseer's Tower", 5): "Saída noroeste → Control Blocks.",
    ("The Control Blocks", 5): "Dá para atravessar as frestas da cerca com Shield Charge/blink. No meio: Miasmeter (+1 passiva). Casticus no fim; saída acima e à esquerda.",
    ("Oriath Square", 5): "Waypoint no início. Passe a praça e cruze a ponte a leste; procure Templar Courts.",
    ("The Templar Courts", 5): "Leste até a parede, sul até o canto inferior direito, oeste até o outro canto, depois norte → Chamber of Innocence.",
    ("The Chamber of Innocence", 5): "Volta grande no sentido ANTI-horário até o Innocence. Depois saia pela DIREITA e fale com Bannon.",
    ("The Torched Courts", 5): "Mesmo caminho das Templar Courts, mas ao contrário → Ruined Square.",
    ("The Ruined Square", 5): "1) Norte: waypoint e Ossuary, 2) Reliquary no lado oposto, 3) Cathedral Rooftop no canto oposto do mesmo lado do waypoint.",
    ("The Ossuary", 5): "Dê a volta na área (começa ~11h) e pegue o Sign of Purity na tumba.",
    ("The Reliquary", 5): "Explore os cantos: Hinekora's Hair, Tukohama's Tooth e Valako's Jaw → +1 passiva.",
    ("The Cathedral Rooftop", 5): "Vire à esquerda na entrada e vá para o noroeste extremo → Kitava. Depois: -30% resistências!",
    # ---------------- ATO 6 ----------------
    ("Lioneye's Watch", 6): "Lily (canto inferior direito) vende todas as gemas após o 1º quest. Saída norte → The Coast.",
    ("The Twilight Strand", 6): "Mate TODOS os monstros (contador aparece com ≤5). Faça a mecânica da liga para o 2º 5-link.",
    ("The Coast", 6): "Waypoint no canto nordeste. Pule Tidal Island → Mud Flats.",
    ("The Mud Flats", 6): "Vá direto para LESTE até a Dishonored Queen (barraco na parede norte). Depois noroeste → Karui Fortress.",
    ("The Karui Fortress", 6): "A área é um anel em volta do forte: procure a porta no lado de DENTRO → Tukohama (+1 passiva). Depois nordeste → The Ridge.",
    ("The Ridge", 6): "Caminho linear até a Lower Prison.",
    ("The Lower Prison", 6): "Waypoint no início. TRIAL geralmente na parte mais ao sul. Shavronne's Tower no canto oposto do mesmo lado.",
    ("Shavronne's Tower", 6): "4 andares: escada do 2º perto da entrada; 2º e 3º são semicírculos; no 4º a escada fica no centro → Brutus e Shavronne.",
    ("Prisoner's Gate", 6): "Waypoint no início. Nessa no canto leste. Valley of the Fire Drinker no lado oposto (norte). Western Forest do outro lado do vale.",
    ("The Valley of the Fire Drinker", 6): "Abberath em 2 arenas (+1 passiva). Volte para Prisoner's Gate.",
    ("The Western Forest", 6): "Siga o caminho até Riverways. Crafting altar no antigo acampamento da Alira (siga as tochas).",
    ("The Riverways", 6): "Pegue o waypoint e vá para Wetlands (2 blocos com hastes indicam). Depois norte e um desvio a leste → Southern Forest.",
    ("The Wetlands", 6): "Spawning Ground geralmente no norte, junto à montanha: quebre os 3 ovos e mate Ryslatha (+1 passiva).",
    ("The Southern Forest", 6): "Atravesse as pontes de madeira entre as ilhas. Destino: canto LESTE, waypoint na entrada da Cavern of Anger.",
    ("The Cavern of Anger", 6): "Pegue a Black Flag e siga até o fundo → The Beacon.",
    ("The Beacon", 6): "Ache o mar e siga a costa até uma ponte estreita. Fique nos 2 círculos até as colunas subirem, acenda o farol e desça até o Weylam.",
    ("The Brine King's Reef", 6): "Siga as BORDAS da área até a entrada do trono. Brine King: fique nas costas, não muito perto.",
    # ---------------- ATO 7 ----------------
    ("The Bridge Encampment", 7): "Saia pelo norte → Broken Bridge.",
    ("The Broken Bridge", 7): "Siga o caminho até Crossroads. (Opcional: Dirty Lockbox num canto → frasco.)",
    ("The Crossroads", 7): "Waypoint no caminho. 1) Leste/sul → Fellshrine Ruins, 2) Norte/oeste → Chamber of Sins.",
    ("The Fellshrine Ruins", 7): "NÃO saia do caminho. Depois do arco, um pouco ao norte pelo cemitério → The Crypt.",
    ("The Crypt", 7): "Waypoint no início e TRIAL aqui. Abra o Sarcophagus e, no lado oposto, o Container of Sins → Maligaro's Map.",
    ("The Chamber of Sins Level 1", 7): "Vá ao centro (muitos ícones no minimapa): fale com o Silk e use o mapa → Maligaro's Sanctum.",
    ("Maligaro's Sanctum", 7): "Vá logo à esquerda até uma ponte estreita, depois norte colado na parede de cima até outra ponte, depois norte → Maligaro's Workshop.",
    ("The Chamber of Sins Level 2", 7): "Faça o TRIAL. No corredor longo e estreito há uma passagem secreta (!) → The Den.",
    ("The Den", 7): "Fique à ESQUERDA até a saída na parede.",
    ("The Ashen Fields", 7): "Pegue o waypoint e siga o caminho para o sudoeste → Greust (+1 passiva). Saída norte da arena.",
    ("The Northern Forest", 7): "Dread Thicket geralmente ao norte/oeste do início. Depois siga além dela → Causeway.",
    ("The Dread Thicket", 7): "Pegue os 7 vaga-lumes (!) e mate Gruthkul no Den of Despair (+1 passiva).",
    ("The Causeway", 7): "Norte (um pouco a oeste) até o waypoint. Antes da saída: Kishara's Lockbox (+1 passiva).",
    ("The Vaal City", 7): "Norte e oeste, parte média-alta: Yeena e o waypoint (abre o templo com os 7 vaga-lumes).",
    ("The Temple of Decay Level 1", 7): "Em cada andar, a descida fica no canto OPOSTO ao início.",
    ("The Temple of Decay Level 2", 7): "Mesma regra dos opostos. Paredes roxas = perto da Arakaali.",
    # ---------------- ATO 8 ----------------
    ("The Sarn Ramparts", 8): "Vá para LESTE colado na muralha até a escada, suba e volte para OESTE por cima até a descida → cidade.",
    ("The Sarn Encampment", 8): "Saída oeste (passando a Clarissa) → Toxic Conduits.",
    ("The Toxic Conduits", 8): "Escolha qualquer direção e siga até a porta do Doedre's Cesspool. Cuidado com dano de CAOS.",
    ("Doedre's Cesspool", 8): "Siga os canos até o portão → Cauldron. Clique na válvula, mate a Doedre. Depois: nordeste → Quay; mais tarde sudoeste → Grand Promenade.",
    ("The Quay", 8): "1º) Sealed Casket (Ankh) — geralmente depois de uma ponte estreita. 2º) Resurrection Site (+1 passiva). Grain Gate fica no lado oposto da bifurcação.",
    ("The Grain Gate", 8): "Waypoint no início. No 2º pátio externo, vá a noroeste: Gemling Legionnaires (+1 passiva).",
    ("The Imperial Fields", 8): "Siga o caminho até acabar e continue na mesma direção até a borda (pátio com estátuas) → Solaris Temple.",
    ("The Solaris Temple Level 1", 8): "NÃO entre na Solaris Concourse. Siga o tapete, waypoint no meio, escada para o Nível 2.",
    ("The Solaris Temple Level 2", 8): "Portal no fim → Dawn. Pegue o Sun Orb e volte para Grand Promenade.",
    ("The Grand Promenade", 8): "Semicírculo grande no sentido anti-horário até a Bath House.",
    ("The Bath House", 8): "Norte: TRIAL (puxe todas as alavancas). Lado oposto ao trial: High Gardens (Yugul). Depois → Lunaris Concourse.",
    ("The High Gardens", 8): "Semicírculo com monstros fortes: vá rápido ao lado oposto → Yugul (+1 passiva).",
    ("The Lunaris Concourse", 8): "Waypoint no meio. Norte (um pouco a leste) → Lunaris Temple. Depois leste/sul → Harbour Bridge.",
    ("The Lunaris Temple Level 1", 8): "Fique no tapete azul; na sala grande, vá a norte e leste. Waypoint e escada para o Nível 2.",
    ("The Lunaris Temple Level 2", 8): "Área chata e cheia de becos. No fim, portal → Dusk (Moon Orb).",
    ("The Harbour Bridge", 8): "Suba direto pelo meio → Sky Shrine. Use a estátua com os 2 orbes → Solaris e Lunaris.",
    # ---------------- ATO 9 ----------------
    ("The Blood Aqueduct", 9): "Duas pontes paralelas: troque de lado quando bloquear. Highgate no fim.",
    ("Highgate", 9): "Saída nordeste → The Descent.",
    ("The Descent", 9): "3 áreas iguais: vá para LESTE (um pouco ao norte) até o Supply Hoist. Ignore as portas do Jun.",
    ("The Vastiri Desert", 9): "1) Baú Storm-Weathered (!) no centro → Storm Blade, 2) waypoint, 3) entrada bloqueada a LESTE. Portal para a cidade, pegue o Bottled Storm, abra → Oasis.",
    ("The Oasis", 9): "Só importa a Sand Pit: Shakari. Quando ela cavar, siga o rastro devagar.",
    ("The Foothills", 9): "Caminho norte até o waypoint. Siga na mesma direção → Boiling Lake. Tunnel geralmente no canto oposto do mesmo lado.",
    ("The Boiling Lake", 9): "Vá ao ponto mais ao norte (um pouco a leste) → Basilisk (Basilisk Acid).",
    ("The Tunnel", 9): "TRIAL de lado, perto da entrada. Siga até o waypoint e a Quarry.",
    ("The Quarry", 9): "Centro: waypoint e Sin. Bordas: Refinery (Adus) e Shrine of the Winds (Garukhan). Volte ao Sin no fim.",
    ("The Refinery", 9): "Siga os trilhos (comece a oeste, depois norte/oeste) até o General Adus → Trarthan Powder.",
    ("The Belly of the Beast", 9): "Vá para a parte superior-central → Rotting Core. Cuidado com Corrupted Blood.",
    ("The Rotting Core", 9): "Passagem até o Black Core: Doedre, Maligaro, Shavronne e depois o Trinity.",
    # ---------------- ATO 10 ----------------
    ("Oriath Docks", 10): "Única saída ao norte (escadas) → Cathedral Rooftop.",
    ("The Cathedral Rooftop", 10): "Cathedral Apex logo a oeste da entrada (Plaguewing). Depois vá muito para o SUDESTE → Ravaged Square.",
    ("The Ravaged Square", 10): "1) Sul → Control Blocks, 2) Ponte a leste e norte → Ossuary (TRIAL), 3) Leste/sul → Torched Courts. Pule a Reliquary.",
    ("The Control Blocks", 10): "Use as frestas da cerca. Contorne pelo fundo até a arena: Vilenta (+1 passiva).",
    ("The Ossuary", 10): "Num canto: Elixir of Allure (respec). Norte/oeste: último TRIAL do Merciless Lab.",
    ("The Torched Courts", 10): "Círculo horário: comece às 12h, saída às 6h (leste, sul até o canto, oeste, um pouco ao norte).",
    ("The Desecrated Chambers", 10): "Semicírculo anti-horário (oeste, sul, leste, um pouco norte) → Avarius. Leve o Staff of Purity ao Bannon.",
    ("The Canals", 10): "Vá para OESTE e NORTE até a ponta da área → Feeding Trough.",
    ("The Feeding Trough", 10): "Oeste e norte até a ponta, fale com o Sin → Kitava. Depois: mais -30% resistências!",
    # ---------------- EPÍLOGO ----------------
    ("Karui Shores", 11): "Pegue o crafting altar, fale com a Lani (+2 passivas) e com o Kirac (mapa). Use o mapa no device.",
}

LEVEL_TIPS = {
    12: "NÍVEL 12: troque para Poisonous Concoction (Volley, Void Manip, Chance to Poison)!",
}


_PCONC_ONLY_TIPS = {("The Mud Flats", 1), ("The Cavern of Wrath", 1), ("The Library", 3), ("The Slave Pens", 5),
                    ("The Twilight Strand", 6)}


def zone_tip(zone, act):
    if GUIDE["mode"] != "pconc":
        if (zone, act) in _PCONC_ONLY_TIPS:
            return ""
        if zone in ("Oriath", "Karui Shores"):
            return "Campanha concluída! Monte o setup de endgame do seu guia."
        if (zone, act) == ("Lioneye's Watch", 6):
            return "Lily vende todas as gemas: monte o setup do seu guia."
    return ZONE_TIPS.get((zone, act)) or ZONE_TIPS.get((zone, 0)) or ""


def level_tip(lvl):
    return LEVEL_TIPS.get(lvl, "") if GUIDE["mode"] == "pconc" else ""

# ---------------------------------------------------------------------------
# Mapa de áreas → atos (para detectar o ato automaticamente)
# ---------------------------------------------------------------------------
_ZONES_BY_ACT = {
    1: ["The Twilight Strand", "Lioneye's Watch", "The Coast", "The Tidal Island", "The Mud Flats",
        "The Fetid Pool", "The Submerged Passage", "The Flooded Depths", "The Ledge", "The Climb",
        "The Lower Prison", "The Upper Prison", "The Warden's Quarters", "Prisoner's Gate", "The Ship Graveyard",
        "The Ship Graveyard Cave", "The Cavern of Wrath", "The Cavern of Anger"],
    2: ["The Southern Forest", "The Forest Encampment", "The Old Fields", "The Den", "The Crossroads",
        "The Chamber of Sins Level 1", "The Chamber of Sins Level 2", "The Broken Bridge",
        "The Riverways", "The Fellshrine Ruins", "The Crypt Level 1", "The Crypt Level 2",
        "The Western Forest", "The Weaver's Chambers", "The Wetlands", "The Vaal Ruins",
        "The Northern Forest", "The Dread Thicket", "The Caverns", "The Ancient Pyramid"],
    3: ["The City of Sarn", "The Sarn Encampment", "The Slums", "The Crematorium", "The Sewers",
        "The Marketplace", "The Catacombs", "The Battlefront", "The Docks", "The Solaris Temple Level 1",
        "The Solaris Temple Level 2", "The Ebony Barracks", "The Lunaris Temple Level 1",
        "The Lunaris Temple Level 2", "The Imperial Gardens", "The Library", "The Archives",
        "The Sceptre of God", "The Upper Sceptre of God"],
    4: ["The Aqueduct", "Highgate", "The Dried Lake", "The Mines Level 1", "The Mines Level 2",
        "The Crystal Veins", "Kaom's Dream", "Kaom's Stronghold", "Daresso's Dream", "The Grand Arena",
        "The Belly of the Beast Level 1", "The Belly of the Beast Level 2", "The Harvest", "The Ascent"],
    5: ["The Slave Pens", "Overseer's Tower", "The Control Blocks", "Oriath Square", "The Templar Courts",
        "The Chamber of Innocence", "The Torched Courts", "The Ruined Square", "The Ossuary",
        "The Reliquary", "The Cathedral Rooftop"],
    6: ["The Twilight Strand", "Lioneye's Watch", "The Coast", "The Tidal Island", "The Mud Flats",
        "The Karui Fortress", "The Ridge", "The Lower Prison", "Shavronne's Tower", "Prisoner's Gate",
        "The Western Forest", "The Riverways", "The Wetlands", "The Southern Forest",
        "The Cavern of Anger", "The Beacon", "The Brine King's Reef", "The Valley of the Fire Drinker"],
    7: ["The Broken Bridge", "The Bridge Encampment", "The Crossroads", "The Fellshrine Ruins",
        "The Crypt", "The Chamber of Sins Level 1", "The Chamber of Sins Level 2", "The Den",
        "The Ashen Fields", "The Northern Forest", "The Dread Thicket", "The Causeway", "The Vaal City",
        "The Temple of Decay Level 1", "The Temple of Decay Level 2", "Maligaro's Sanctum"],
    8: ["The Sarn Ramparts", "The Sarn Encampment", "The Toxic Conduits", "Doedre's Cesspool",
        "The Grand Promenade", "The Bath House", "The High Gardens", "The Quay", "The Grain Gate",
        "The Imperial Fields", "The Solaris Concourse", "The Solaris Temple Level 1",
        "The Solaris Temple Level 2", "The Lunaris Concourse", "The Lunaris Temple Level 1",
        "The Lunaris Temple Level 2", "The Harbour Bridge"],
    9: ["The Blood Aqueduct", "Highgate", "The Descent", "The Vastiri Desert", "The Oasis",
        "The Foothills", "The Boiling Lake", "The Tunnel", "The Quarry", "The Refinery",
        "The Belly of the Beast", "The Rotting Core"],
    10: ["The Cathedral Rooftop", "Oriath Docks", "The Ravaged Square", "The Torched Courts",
         "The Desecrated Chambers", "The Canals", "The Feeding Trough", "The Control Blocks",
         "The Reliquary", "The Ossuary"],
    11: ["Oriath", "Karui Shores"],
}

ZONE_ACTS = {}
for _act, _zones in _ZONES_BY_ACT.items():
    for _z in _zones:
        ZONE_ACTS.setdefault(_z, set()).add(_act)


# Nível aproximado das áreas no início de cada ato
ACT_START_LEVEL = {1: 1, 2: 13, 3: 23, 4: 33, 5: 40, 6: 45, 7: 50, 8: 55, 9: 60, 10: 64, 11: 67}


def max_plausible_act(level):
    """Maior ato possível para um personagem desse nível (com folga de 8 níveis)."""
    return max(a for a, lv in ACT_START_LEVEL.items() if lv <= level + 8)


def best_act_for_level(zone, level):
    """Sem histórico confiável (personagem trocou): escolhe o ato da área que combina com o nível."""
    acts = ZONE_ACTS.get(zone)
    if not acts:
        return min(max_plausible_act(level), 11)
    fit = [a for a in acts if ACT_START_LEVEL[a] <= level + 3]
    return max(fit) if fit else min(acts)


def resolve_act(zone, current_act, level=None):
    """Descobre o ato a partir do nome da área.
    A campanha é sequencial: do ato N você só entra em áreas do ato N, N+1 ou de atos anteriores.
    Áreas repetidas (ex.: Lioneye's Watch nos atos 1 e 6) são resolvidas por isso e pelo nível."""
    acts = ZONE_ACTS.get(zone)
    if not acts:
        return current_act
    cap = max_plausible_act(level) if level else 11
    cand = [a for a in acts if a <= cap] or [min(acts)]
    if current_act in cand:
        return current_act
    if current_act + 1 in cand:
        return current_act + 1
    earlier = [a for a in cand if a < current_act]
    if earlier:
        return max(earlier)
    return min(cand)


# ---------------------------------------------------------------------------
# Leitura do Client.txt
# ---------------------------------------------------------------------------
RE_ENTER = re.compile(r"You have entered (.+?)\.\s*$")
RE_SCENE = re.compile(r"\[SCENE\] Set Source \[(.+?)\]")
RE_LEVEL = re.compile(r": (.+?) \((\w+)\) is now level (\d+)")

DEFAULT_LOG_PATHS = [
    r"C:\Program Files (x86)\Grinding Gear Games\Path of Exile\logs\Client.txt",
    r"C:\Program Files\Grinding Gear Games\Path of Exile\logs\Client.txt",
    r"C:\Program Files (x86)\Steam\steamapps\common\Path of Exile\logs\Client.txt",
    r"C:\Program Files\Steam\steamapps\common\Path of Exile\logs\Client.txt",
    r"D:\SteamLibrary\steamapps\common\Path of Exile\logs\Client.txt",
    r"E:\SteamLibrary\steamapps\common\Path of Exile\logs\Client.txt",
    r"D:\Steam\steamapps\common\Path of Exile\logs\Client.txt",
    r"D:\Grinding Gear Games\Path of Exile\logs\Client.txt",
    r"D:\Path of Exile\logs\Client.txt",
]


def linux_log_candidates():
    """Linux: Steam nativa, Steam Flatpak, bibliotecas extras da Steam e Lutris/Wine."""
    h = os.path.expanduser("~")
    rel = os.path.join("steamapps", "common", "Path of Exile", "logs", "Client.txt")
    steam_roots = [os.path.join(h, ".steam", "steam"), os.path.join(h, ".steam", "root"),
                   os.path.join(h, ".local", "share", "Steam"),
                   os.path.join(h, ".var", "app", "com.valvesoftware.Steam", ".local", "share", "Steam"),
                   os.path.join(h, ".var", "app", "com.valvesoftware.Steam", "data", "Steam")]
    cands = []
    for r in steam_roots:
        cands.append(os.path.join(r, rel))
        try:
            with open(os.path.join(r, "steamapps", "libraryfolders.vdf"), "r", encoding="utf-8",
                      errors="ignore") as f:
                for lib in re.findall(r'"path"\s+"([^"]+)"', f.read()):
                    cands.append(os.path.join(lib, rel))
        except Exception:
            pass
    ggg = os.path.join("Grinding Gear Games", "Path of Exile", "logs", "Client.txt")
    for prefix in (os.path.join(h, "Games", "path-of-exile"), os.path.join(h, "Games", "path-of-exile-1"),
                   os.path.join(h, ".wine")):
        for pf in ("Program Files (x86)", "Program Files"):
            cands.append(os.path.join(prefix, "drive_c", pf, ggg))
    return cands


def find_default_log():
    """Procura o Client.txt nos lugares comuns (Steam e site oficial) em todos os discos."""
    if not IS_WIN:
        for p in linux_log_candidates():
            if os.path.isfile(p):
                return p
        return ""
    cands = list(DEFAULT_LOG_PATHS)
    rel_steam = os.path.join("steamapps", "common", "Path of Exile", "logs", "Client.txt")
    steam_bases = [("Program Files (x86)", "Steam"), ("Program Files", "Steam"), ("Steam",), ("SteamLibrary",),
                   ("Games", "Steam"), ("Games", "SteamLibrary"), ("Jogos", "Steam")]
    ggg_bases = [("Program Files (x86)", "Grinding Gear Games", "Path of Exile"),
                 ("Program Files", "Grinding Gear Games", "Path of Exile"), ("Grinding Gear Games", "Path of Exile"),
                 ("Path of Exile",), ("Games", "Path of Exile"), ("Jogos", "Path of Exile")]
    for d in "CDEFGHIJ":
        root_ = d + ":" + os.sep
        for parts in steam_bases:
            cands.append(os.path.join(root_, *parts, rel_steam))
        for parts in ggg_bases:
            cands.append(os.path.join(root_, *parts, "logs", "Client.txt"))
    # bibliotecas extras da Steam (libraryfolders.vdf)
    for vdf in (r"C:\Program Files (x86)\Steam\steamapps\libraryfolders.vdf",
                r"C:\Program Files\Steam\steamapps\libraryfolders.vdf"):
        try:
            with open(vdf, "r", encoding="utf-8", errors="ignore") as f:
                for lib in re.findall(r'"path"\s+"([^"]+)"', f.read()):
                    cands.append(os.path.join(lib.replace("\\\\", "\\"), rel_steam))
        except Exception:
            pass
    for p in cands:
        try:
            if os.path.isfile(p):
                return p
        except Exception:
            pass
    return ""


RE_TS = re.compile(r"^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})")
RE_AREA = re.compile(r'Generating level (\d+) area "([^"]+)"')
RE_SLAIN = re.compile(r"\] : (\S+) has been slain\.")

TOWNS = {"Lioneye's Watch", "The Forest Encampment", "The Sarn Encampment", "Highgate",
         "Overseer's Tower", "The Bridge Encampment", "Oriath Docks", "Karui Shores", "Oriath"}

# Trials of Ascendancy (área, ato) por labirinto
TRIALS = [
    ("Normal Lab", [("The Lower Prison", 1), ("The Chamber of Sins Level 2", 2), ("The Crypt Level 1", 2),
                    ("The Crematorium", 3), ("The Catacombs", 3), ("The Imperial Gardens", 3)]),
    ("Cruel Lab", [("The Lower Prison", 6), ("The Crypt", 7), ("The Chamber of Sins Level 2", 7)]),
    ("Merciless Lab", [("The Bath House", 8), ("The Tunnel", 9), ("The Ossuary", 10)]),
]


def trial_key(zone, act):
    return f"{act}|{zone}"


def trial_lab(zone, act):
    for lab, lst in TRIALS:
        if (zone, act) in lst:
            return lab
    return None


def xp_multiplier(player_level, area_level):
    """Multiplicador de XP do PoE 1 (fórmula da poewiki, níveis abaixo de 95)."""
    safe = 3 + player_level // 16
    diff = max(abs(player_level - area_level) - safe, 0)
    return ((player_level + 5) / (player_level + 5 + diff ** 2.5)) ** 1.5


def parse_ts(line):
    m = RE_TS.match(line)
    return m.group(1) if m else ""


def ts_seconds(ts):
    import datetime
    try:
        return datetime.datetime.strptime(ts, "%Y/%m/%d %H:%M:%S").timestamp()
    except Exception:
        return None


def fmt_dur(sec):
    if sec is None or sec < 0:
        return "—"
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def parse_line(line):
    """Retorna ('zone', nome) | ('level', (char, classe, nivel)) | ('area', nivel) | ('slain', char) | None."""
    m = RE_LEVEL.search(line)
    if m:
        return ("level", (m.group(1), m.group(2), int(m.group(3))))
    m = RE_ENTER.search(line)
    if m:
        return ("zone", m.group(1).strip())
    m = RE_AREA.search(line)
    if m:
        return ("area", int(m.group(1)))
    m = RE_SLAIN.search(line)
    if m:
        return ("slain", m.group(1))
    m = RE_SCENE.search(line)
    if m and m.group(1) != "(null)":
        return ("zone", m.group(1).strip())
    return None


class LogState:
    """Estado do personagem montado a partir das linhas do log."""

    def __init__(self, act=1, runs=None):
        self.act = act
        self.zone = ""
        self.level = 1
        self.char = ""
        self.char_class = ""
        self.nav = ""
        self.area_level = None
        self._pending_area = None
        self.last_ts = ""
        self._pending_zones = []
        self.runs = runs if runs is not None else {}   # tempos e mortes por personagem (salvo)
        self.events = []  # avisos novos para mostrar

    # --- tempos e mortes ---
    def run(self):
        if not self.char:
            return None
        return self.runs.setdefault(self.char, {"start": "", "acts": {}, "deaths": 0, "last_death": ""})

    def _mark_act(self, ts):
        r = self.run()
        if r is not None and ts and str(self.act) not in r["acts"]:
            r["acts"][str(self.act)] = ts

    def _visit(self, zone, act):
        key = f"{act}|{zone}"
        r = self.run()
        if r is None:
            self._pending_zones.append(key)
            return
        z = r.setdefault("zones", {})
        z[key] = z.get(key, 0) + 1

    def visits(self, zone, act):
        r = self.run()
        return (r or {}).get("zones", {}).get(f"{act}|{zone}", 0)

    def step_done(self, act, i, checks):
        """Passos com área-gatilho dependem SÓ do jogo (clique não conta).
        Passos sem gatilho (ex.: comprar gema) podem ser marcados na mão."""
        steps = STEPS.get(act, [])
        if i >= len(steps):
            return False
        trig = steps[i][1]
        if trig:
            return self.visits(*trig) > 0 or self._later_progress(act, i)
        return bool(checks.get(step_key(act, i)))

    def _later_progress(self, act, i):
        """Se você já chegou num ponto mais à frente, os passos anteriores contam como feitos."""
        steps = STEPS.get(act, [])
        for j in range(i + 1, len(steps)):
            trig = steps[j][1]
            if trig and self.visits(*trig) > 0:
                return True
        return False

    def next_step(self, act, checks):
        """Próximo passo = o primeiro não feito DEPOIS do último passo feito (manual ou automático)."""
        steps = STEPS.get(act, [])
        last = -1
        for i in range(len(steps)):
            if self.step_done(act, i, checks):
                last = i
        for i in range(last + 1, len(steps)):
            if not self.step_done(act, i, checks):
                return i, steps[i][0]
        return None, None

    def xp(self):
        if self.area_level is None or self.zone in TOWNS or self.zone not in ZONE_ACTS:
            return None
        return xp_multiplier(self.level, self.area_level)

    def feed(self, line, live=True):
        ev = parse_line(line)
        if not ev:
            return
        ts = parse_ts(line)
        if ts:
            self.last_ts = ts
        kind, data = ev
        if kind == "area":
            self._pending_area = data
            return
        if kind == "slain":
            r = self.run()
            if r is not None and data == self.char and ts and ts > r.get("last_death", ""):
                r["deaths"] = r.get("deaths", 0) + 1
                r["last_death"] = ts
            return
        if kind == "zone":
            if data == self.zone:
                return
            self.zone = data
            self.area_level = self._pending_area
            self._pending_area = None
            new_act = resolve_act(data, self.act, self.level)
            if new_act != self.act and live:
                self.events.append(f"Agora: {ACT_NAMES[new_act]}!")
            self.act = new_act
            self._mark_act(ts)
            self._visit(data, self.act)
            self.nav = nav_for(data, self.act)
            if live:
                tip = zone_tip(data, self.act)
                if tip:
                    self.events.append(tip)
                lab = trial_lab(data, self.act)
                if lab:
                    self.events.append(f"⚔ Esta área tem um TRIAL do {lab}! Marque quando fizer.")
                mult = self.xp()
                if mult is not None and mult < 0.9:
                    gap = self.level - self.area_level
                    if gap > 0:
                        self.events.append(f"XP {mult:.0%}: você está {gap} níveis ACIMA da área. "
                                           "Não farme aqui, avance a campanha.")
                    else:
                        self.events.append(f"XP {mult:.0%}: você está {-gap} níveis ABAIXO da área. "
                                           "Cuidado: farme um pouco ou suba de nível.")
        elif kind == "level":
            char, cls, lvl = data
            # considera só o personagem acompanhado (o último que subiu de nível)
            if self.char and char != self.char and live:
                self.events.append(f"Acompanhando agora: {char}")
            changed = bool(self.char) and char != self.char
            new_char = char != self.char
            self.char, self.char_class, self.level = char, cls, lvl
            r = self.run()
            if new_char and r is not None and not r["start"] and ts:
                r["start"] = ts
            if r is not None and self._pending_zones:
                z = r.setdefault("zones", {})
                for key in self._pending_zones:
                    z[key] = z.get(key, 0) + 1
                self._pending_zones = []
            # personagem trocou ou o ato não combina com o nível: corrige o ato
            if changed or self.act > max_plausible_act(lvl):
                if changed:
                    self.act = best_act_for_level(self.zone, lvl) if self.zone else 1
                else:
                    self.act = resolve_act(self.zone, self.act, lvl) if self.zone else 1
                self.act = min(self.act, max_plausible_act(lvl))
                self.nav = nav_for(self.zone, self.act)
            self._mark_act(ts)
            if live and level_tip(lvl):
                self.events.append(level_tip(lvl))

    def add_active(self, sec):
        """Soma tempo em que você estava jogando de verdade (mexendo no jogo)."""
        r = self.run()
        if r is None:
            return
        a = r.setdefault("active", {})
        k = str(self.act)
        a[k] = a.get(k, 0) + sec

    def splits(self):
        """Lista [(ato, segundos jogados, em_andamento, estimado)] e tempo total da campanha.
        Conta só o tempo em que você estava mexendo no jogo; atos antigos sem esse dado usam o log (estimado)."""
        r = self.run()
        if not r:
            return [], None
        old_sp, _old_total = self._splits_log()
        old = {a: d for a, d in old_sp}
        act_sec = {int(k): v for k, v in r.get("active", {}).items()}
        out, total = [], 0.0
        for a in sorted(set(act_sec) | set(old)):
            cur = (a == self.act)
            if a in act_sec:
                d, est = act_sec[a], False
            else:
                d, est = old.get(a), True
            out.append((a, d, cur, est))
            if a <= 10 and d:
                total += d
        return out, (total if out else None)

    def _splits_log(self):
        """Tempos antigos pelo horário do log (contam o tempo parado também)."""
        r = self.run()
        if not r or not r["start"]:
            return [], None
        acts = {int(k): v for k, v in r["acts"].items()}
        acts[1] = min(acts.get(1, r["start"]), r["start"])
        out = []
        for a in sorted(acts):
            t0 = ts_seconds(acts[a])
            nxt = [b for b in sorted(acts) if b > a]
            t1 = ts_seconds(acts[nxt[0]]) if nxt else None
            out.append((a, (t1 - t0) if (t0 and t1) else None))
        total = None
        if self.last_ts:
            t_end = ts_seconds(acts.get(11, self.last_ts)) if 11 in acts else ts_seconds(self.last_ts)
            total = t_end - ts_seconds(r["start"]) if t_end else None
        return out, total


def read_tail(path, max_bytes=3_000_000):
    """Lê o final do log para recuperar o estado atual ao abrir o programa."""
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        f.seek(max(0, size - max_bytes))
        data = f.read()
    text = data.decode("utf-8", errors="ignore")
    lines = text.splitlines()
    if size > max_bytes and lines:
        lines = lines[1:]  # primeira linha pode estar cortada
    return lines, size


# ---------------------------------------------------------------------------
# Configuração salva
# ---------------------------------------------------------------------------
def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------
BG = "#14161b"
BG2 = "#1e2129"
FG = "#e6e6e6"
MUTED = "#9aa0aa"
ACCENT = "#7bd67b"     # verde veneno
WARN_BG = "#4a3b10"
WARN_FG = "#ffd866"


def set_no_activate(root, enable):
    """Windows: faz a janela NÃO roubar o foco do jogo ao ser clicada."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetParent(root.winfo_id()) or root.winfo_id()
        GWL_EXSTYLE = -20
        WS_EX_NOACTIVATE = 0x08000000
        WS_EX_TOOLWINDOW = 0x00000080
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if enable:
            style |= WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
        else:
            style &= ~(WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        # SWP_NOMOVE|SWP_NOSIZE|SWP_NOZORDER|SWP_FRAMECHANGED|SWP_NOACTIVATE
        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0004 | 0x0020 | 0x0010)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# PRICE CHECK (poe.ninja). Você copia o item no jogo com Ctrl+C; o programa só lê a área de transferência.
# ---------------------------------------------------------------------------
NINJA = "https://poe.ninja/poe1/api"
EXCHANGE_TYPES = ["Currency", "Fragment", "DivinationCard", "Essence", "Scarab", "Fossil", "Oil", "DeliriumOrb",
                  "Omen", "Tattoo", "Resonator", "Artifact", "Runegraft", "AllflameEmber"]
UNIQUE_TYPE_BY_CLASS = {
    "Rings": "UniqueAccessory", "Amulets": "UniqueAccessory", "Belts": "UniqueAccessory",
    "Body Armours": "UniqueArmour", "Helmets": "UniqueArmour", "Gloves": "UniqueArmour", "Boots": "UniqueArmour",
    "Shields": "UniqueArmour", "Quivers": "UniqueArmour",
    "Life Flasks": "UniqueFlask", "Mana Flasks": "UniqueFlask", "Hybrid Flasks": "UniqueFlask",
    "Utility Flasks": "UniqueFlask", "Jewels": "UniqueJewel", "Abyss Jewels": "UniqueJewel", "Maps": "UniqueMap",
}


def _ninja_get(path):
    import urllib.request
    req = urllib.request.Request(NINJA + path, headers={"User-Agent": "FLPoEHelper/1.0 (price check)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


class PriceDB:
    """Preços do poe.ninja com cache de 30 min."""
    TTL = 1800

    def __init__(self, league=None):
        self.league = league
        self.cache = {}

    def get_league(self):
        if not self.league:
            idx = _ninja_get("/data/index-state")
            leagues = [x["name"] for x in idx.get("economyLeagues", [])]
            self.league = leagues[0] if leagues else "Standard"
        return self.league

    def _cached(self, key, loader):
        import time
        hit = self.cache.get(key)
        if hit and time.time() - hit[0] < self.TTL:
            return hit[1]
        val = loader()
        self.cache[key] = (time.time(), val)
        return val

    def exchange(self, typ):
        """{nome: valor em chaos}"""
        import urllib.parse

        def load():
            q = urllib.parse.urlencode({"league": self.get_league(), "type": typ})
            j = _ninja_get(f"/economy/exchange/current/overview?{q}")
            names = {i["id"]: i["name"] for i in j.get("items", [])}
            out = {names.get(l["id"], l["id"]): l.get("primaryValue") for l in j.get("lines", [])}
            out.setdefault("Chaos Orb", 1.0)
            return out
        try:
            return self._cached(("ex", typ), load)
        except Exception:
            return {}

    def items(self, typ):
        import urllib.parse

        def load():
            q = urllib.parse.urlencode({"league": self.get_league(), "type": typ})
            return _ninja_get(f"/economy/stash/current/item/overview?{q}").get("lines", [])
        try:
            return self._cached(("it", typ), load)
        except Exception:
            return []

    def divine(self):
        return self.exchange("Currency").get("Divine Orb") or None

    def currency_by_id(self):
        """{'divine': 93.4, 'exalted': 0.44, ...} em chaos (ids do site de trade)."""
        import urllib.parse

        def load():
            q = urllib.parse.urlencode({"league": self.get_league(), "type": "Currency"})
            j = _ninja_get(f"/economy/exchange/current/overview?{q}")
            out = {l["id"]: l.get("primaryValue") for l in j.get("lines", [])}
            out["chaos"] = 1.0
            return out
        try:
            return self._cached(("ids", "Currency"), load)
        except Exception:
            return {"chaos": 1.0}


def parse_item_text(text):
    """Lê o texto que o PoE copia com Ctrl+C (cliente em inglês)."""
    lines = [l.strip() for l in text.replace("\r", "").split("\n")]
    if not lines or not lines[0].startswith("Item Class:"):
        return None
    it = {"class": lines[0].split(":", 1)[1].strip(), "rarity": "", "name": "", "base": "", "stack": 1,
          "ilvl": None, "level": None, "quality": 0, "corrupted": False, "links": 0, "map_tier": None}
    i = 1
    if i < len(lines) and lines[i].startswith("Rarity:"):
        it["rarity"] = lines[i].split(":", 1)[1].strip()
        i += 1
    head = []
    while i < len(lines) and lines[i] != "--------":
        if lines[i] and not lines[i].startswith("{"):
            head.append(lines[i])
        i += 1
    if head:
        it["name"] = head[0]
        it["base"] = head[1] if len(head) > 1 else head[0]
    for ln in lines[i:]:
        m = re.match(r"Stack Size: ([\d,.\s]+)/", ln)
        if m:
            it["stack"] = int(re.sub(r"[^\d]", "", m.group(1)) or 1)
        m = re.match(r"Item Level: (\d+)", ln)
        if m:
            it["ilvl"] = int(m.group(1))
        m = re.match(r"Level: (\d+)", ln)
        if m and it["level"] is None:
            it["level"] = int(m.group(1))
        m = re.match(r"Quality.*?: \+?(\d+)%", ln)
        if m:
            it["quality"] = int(m.group(1))
        m = re.match(r"Map Tier: (\d+)", ln)
        if m:
            it["map_tier"] = int(m.group(1))
        if ln == "Corrupted":
            it["corrupted"] = True
        m = re.match(r"Sockets: (.+)", ln)
        if m:
            it["links"] = max(len(g.split("-")) for g in m.group(1).split())
    return it


def price_item(db, it):
    """Retorna dict com: title, price (chaos por unidade) ou None, total, detail, trade(bool)."""
    out = {"title": it["name"], "price": None, "total": None, "detail": "", "trade": False,
           "rarity": it["rarity"]}
    rar, cls, name = it["rarity"], it["class"], it["name"]
    if rar in ("Currency", "Divination Card") or cls in ("Stackable Currency", "Map Fragments", "Divination Cards",
                                                        "Delve Stackable Socketable Currency"):
        order = ["DivinationCard"] if rar == "Divination Card" else EXCHANGE_TYPES
        for typ in order:
            p = db.exchange(typ).get(name)
            if p is not None:
                out["price"] = p
                if it["stack"] > 1:
                    out["total"] = p * it["stack"]
                return out
        out["detail"] = "Sem preço no poe.ninja (provavelmente vale pouco)."
        return out
    if rar == "Gem":
        cands = [l for l in db.items("SkillGem") if l.get("name") == name and
                 bool(l.get("corrupted")) == it["corrupted"]]
        if not cands:
            out["detail"] = "Gema sem preço listado (provavelmente vale pouco)."
            return out
        lvl, q = it["level"] or 1, it["quality"]
        fit = [l for l in cands if (l.get("gemLevel") or 1) <= lvl and (l.get("gemQuality") or 0) <= q] or cands
        best = max(fit, key=lambda l: ((l.get("gemLevel") or 1), (l.get("gemQuality") or 0)))
        out["price"] = best.get("chaosValue")
        out["detail"] = f"Referência: variante {best.get('variant', '?')} • {best.get('listingCount', 0)} à venda"
        return out
    if rar == "Unique":
        typ = UNIQUE_TYPE_BY_CLASS.get(cls, "UniqueWeapon")
        cands = [l for l in db.items(typ) if l.get("name") == name]
        if not cands:
            out["detail"] = "Único sem preço listado no poe.ninja."
            out["trade"] = True
            return out
        links = it["links"] if it["links"] >= 5 else 0
        same = [l for l in cands if (l.get("links") or 0) == links] or cands
        best = min(same, key=lambda l: l.get("chaosValue") or 0)
        out["price"] = best.get("chaosValue")
        out["detail"] = (f"{best.get('listingCount', 0)} à venda" + (f" • {links}-link" if links else "")
                         + (" • variante: " + best["variant"] if best.get("variant") else ""))
        return out
    if cls == "Maps":
        cands = [l for l in db.items("Map") if l.get("name") in (it["base"], name)]
        if cands:
            out["price"] = min(c.get("chaosValue") or 0 for c in cands)
            return out
    out["trade"] = True
    extra = []
    if it["ilvl"]:
        extra.append(f"ilvl {it['ilvl']}")
    if it["links"] >= 4:
        extra.append(f"{it['links']}-link")
    rar_pt = {"Rare": "raro", "Magic": "mágico", "Normal": "comum"}.get(rar, rar.lower() or "comum")
    out["detail"] = ("Item " + rar_pt + ": o preço depende dos mods. "
                     + (" • ".join(extra) + ". " if extra else "") + "Use o botão para abrir a busca no trade.")
    return out


def trade_url(league, it):
    import urllib.parse
    q = {"query": {"status": {"option": "online"}}}
    if it.get("rarity") == "Unique":
        q["query"]["name"] = it["name"]
        q["query"]["type"] = it["base"]
    elif it.get("base"):
        q["query"]["type"] = it["base"]
    return (f"https://www.pathofexile.com/trade/search/{urllib.parse.quote(league)}?q="
            + urllib.parse.quote(json.dumps(q)))


def fmt_chaos(c, div=None):
    if c is None:
        return "—"
    s = f"{c:,.0f} c" if c >= 10 else f"{c:,.2f} c"
    if div and c >= div * 0.5:
        s += f"  ({c / div:,.2f} div)"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------------------
# TRADE AVANÇADO (estilo Awakened PoE Trade): mods do item -> filtros -> anúncios reais do site oficial
# ---------------------------------------------------------------------------
TRADE = "https://www.pathofexile.com"
TRADE_UA = "FLPoEHelper/1.0 (ferramenta pessoal de price check)"
STATS_CACHE = os.path.join(CACHE_DIR, "trade_mods.json")
LOCAL_CLASSES = {"Body Armours", "Helmets", "Gloves", "Boots", "Shields", "Claws", "Daggers", "Wands",
                 "One Hand Swords", "Thrusting One Hand Swords", "One Hand Axes", "One Hand Maces", "Sceptres",
                 "Rune Daggers", "Staves", "Warstaves", "Two Hand Swords", "Two Hand Axes", "Two Hand Maces", "Bows"}
IMPORTANT_MOD_WORDS = ("movement speed", "suppress", "to level of", "attack speed", "critical", "damage over time",
                       "chaos damage", "poison", "projectile", "spell damage", "physical damage",
                       "elemental damage", "cast speed")
_NUM = re.compile(r"[+-]?\d+(?:\.\d+)?")


def _http_json(url, data=None, timeout=20):
    import urllib.request
    import urllib.error
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers={"User-Agent": TRADE_UA, "Content-Type": "application/json",
                                                          "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8")), dict(r.headers)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            wait = e.headers.get("Retry-After", "60")
            raise RuntimeError(f"limite de buscas do site atingido; espere {wait}s")
        if e.code == 403:
            raise RuntimeError("o site de trade bloqueou a consulta automática (403); use 'Abrir no site'")
        msg = ""
        try:
            j = json.loads(e.read().decode("utf-8", "replace"))
            msg = (j.get("error") or {}).get("message", "")
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code}" + (f" – {msg}" if msg else ""))


class StatIndex:
    """Mods oficiais do trade, indexados pelo texto com '#' no lugar dos números."""

    def __init__(self):
        self.by_type = {}

    def load(self):
        import time
        data = None
        try:
            if os.path.isfile(STATS_CACHE) and time.time() - os.path.getmtime(STATS_CACHE) < 86400:
                with open(STATS_CACHE, "r", encoding="utf-8") as f:
                    data = json.load(f)
        except Exception:
            data = None
        if data is None:
            data, _ = _http_json(TRADE + "/api/trade/data/stats")
            try:
                with open(STATS_CACHE, "w", encoding="utf-8") as f:
                    json.dump(data, f)
            except Exception:
                pass
        for grp in data.get("result", []):
            d = {}
            for e in grp.get("entries", []):
                if "\n" not in e["text"]:
                    d.setdefault(e["text"], e["id"])
            self.by_type[grp["id"]] = d
        return self

    def match(self, line, item_class):
        """Retorna (id, valor, texto) ou None para uma linha de mod do item."""
        typ = "explicit"
        for suf, t in ((" (implicit)", "implicit"), (" (crafted)", "crafted"), (" (fractured)", "fractured"),
                       (" (enchant)", "enchant")):
            if line.endswith(suf):
                line, typ = line[: -len(suf)], t
                break
        nums = [float(x) for x in _NUM.findall(line)]
        if not nums:
            return None
        # troca só os dígitos por '#': "+45 to maximum Life" -> "+# to maximum Life" (igual ao texto do trade)
        sig = re.sub(r"\d+(?:\.\d+)?", "#", line)
        table = self.by_type.get(typ, {})
        sign = 1
        cands = [sig]
        if "reduced" in sig:
            cands.append(sig.replace("reduced", "increased"))
        if "less" in sig:
            cands.append(sig.replace("less", "more"))
        for k, cand in enumerate(cands):
            if k > 0:
                sign = -1
            if item_class in LOCAL_CLASSES and cand + " (Local)" in table:
                sid = table[cand + " (Local)"]
            else:
                sid = table.get(cand)
            if sid:
                val = sum(nums) / len(nums) * sign
                return sid, val, line
        return None


def item_mod_lines(text):
    """Linhas do texto copiado que podem ser mods (depois do cabeçalho)."""
    lines = [l.strip() for l in text.replace("\r", "").split("\n")]
    out, seen_sep = [], False
    for ln in lines:
        if ln == "--------":
            seen_sep = True
            continue
        if not seen_sep or not ln or ln.startswith("{") or ":" in ln.split(" ")[0]:
            continue
        out.append(ln)
    return out


def build_trade_filters(text, it, stats):
    """Lista de filtros [{id, text, value, min, on}] com totais (vida e resistências) no estilo Awakened."""
    filters, life, strength = [], 0.0, 0.0
    res = {"fire": 0, "cold": 0, "lightning": 0, "chaos": 0}
    mods = []
    for ln in item_mod_lines(text):
        m = stats.match(ln, it["class"])
        if not m:
            continue
        sid, val, clean = m
        mods.append((sid, val, clean))
        low = clean.lower()
        if re.fullmatch(r"\+[\d.]+ to maximum life", low):
            life += val
        if "to strength" in low or "to all attributes" in low:
            strength += val
    res_from_lines([c for _, _, c in mods], res)
    total_life = life + strength // 2
    ele = res["fire"] + res["cold"] + res["lightning"]
    if total_life >= 20:
        filters.append({"id": "pseudo.pseudo_total_life", "text": f"+{total_life:.0f} vida total (pseudo)",
                        "value": total_life, "min": int(total_life * 0.85), "on": True})
    if ele >= 15:
        filters.append({"id": "pseudo.pseudo_total_elemental_resistance",
                        "text": f"+{ele}% resistência elemental total (pseudo)", "value": ele,
                        "min": int(ele * 0.85), "on": True})
    if res["chaos"] >= 10:
        filters.append({"id": "pseudo.pseudo_total_chaos_resistance", "text": f"+{res['chaos']}% resist. caos total",
                        "value": res["chaos"], "min": int(res["chaos"] * 0.85), "on": res["chaos"] >= 20})
    covered = ("maximum life", "resistance", "to strength", "to all attributes")
    for sid, val, clean in mods:
        low = clean.lower()
        is_cov = any(c in low for c in covered)
        on = (not is_cov) and not sid.startswith("crafted.") and any(w in low for w in IMPORTANT_MOD_WORDS)
        mn = int(val * 0.85) if val > 0 else int(val)
        filters.append({"id": sid, "text": clean, "value": val, "min": mn, "on": on})
    return filters


def build_trade_query(it, filters, use_base=True, min_links=None, min_ilvl=None):
    q = {"query": {"status": {"option": "online"},
                   "stats": [{"type": "and", "filters": [{"id": f["id"], "value": {"min": f["min"]}}
                                                         for f in filters if f["on"]]}],
                   "filters": {}},
         "sort": {"price": "asc"}}
    if it["rarity"] == "Unique":
        q["query"]["name"] = it["name"]
        q["query"]["type"] = it["base"]
    else:
        if use_base and it.get("base"):
            q["query"]["type"] = it.get("trade_base") or it["base"]
        q["query"]["filters"]["type_filters"] = {"filters": {"rarity": {"option": "nonunique"}}}
    if min_links:
        q["query"]["filters"]["socket_filters"] = {"filters": {"links": {"min": min_links}}}
    if min_ilvl:
        q["query"]["filters"]["misc_filters"] = {"filters": {"ilvl": {"min": min_ilvl}}}
    return q


BASES_CACHE = os.path.join(CACHE_DIR, "trade_bases.json")
_TRADE_BASES = {"set": None, "league": {}}


def trade_bases():
    """Conjunto com todos os tipos base do trade (cache de 1 dia)."""
    import time
    if _TRADE_BASES["set"] is not None:
        return _TRADE_BASES["set"]
    data = None
    try:
        if os.path.isfile(BASES_CACHE) and time.time() - os.path.getmtime(BASES_CACHE) < 86400:
            with open(BASES_CACHE, "r", encoding="utf-8") as f:
                data = json.load(f)
    except Exception:
        data = None
    if data is None:
        try:
            data, _ = _http_json(TRADE + "/api/trade/data/items")
            with open(BASES_CACHE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            data = None
    out = set()
    for grp in (data or {}).get("result", []):
        for e in grp.get("entries", []):
            if e.get("type"):
                out.add(e["type"])
    _TRADE_BASES["set"] = out
    return out


def resolve_base(it, bases=None):
    """Base real do item. Mágicos vêm com o nome cheio ('Seething Leather Belt of the Whale')."""
    b = (it.get("base") or "").strip()
    for pre in ("Superior ", "Synthesised "):
        if b.startswith(pre):
            b = b[len(pre):]
    if bases is None:
        bases = trade_bases()
    if not bases or b in bases:
        return b
    hits = [x for x in bases if x in b]
    return max(hits, key=len) if hits else b


def trade_league(ninja_league):
    """Nome da liga como o site de trade espera (pode diferir do poe.ninja)."""
    if ninja_league in _TRADE_BASES["league"]:
        return _TRADE_BASES["league"][ninja_league]
    lg = ninja_league
    try:
        j, _ = _http_json(TRADE + "/api/trade/data/leagues")
        ids = [x.get("id") for x in j.get("result", []) if x.get("realm", "pc") == "pc"]
        if ninja_league not in ids:
            low = {i.lower(): i for i in ids if i}
            if ninja_league.lower() in low:
                lg = low[ninja_league.lower()]
            else:
                main = [i for i in ids if i and i != "Standard" and "Hardcore" not in i and "SSF" not in i
                        and "Ruthless" not in i]
                if main:
                    lg = main[0]
    except Exception:
        pass
    _TRADE_BASES["league"][ninja_league] = lg
    return lg


def trade_search_safe(league, query, n=10):
    """Busca e, se o site recusar (HTTP 400), tenta de novo mais simples. Retorna (resultado, aviso)."""
    import copy
    try:
        return trade_search(league, query, n), ""
    except RuntimeError as ex:
        if "HTTP 400" not in str(ex):
            raise
        first = str(ex)
    q2 = copy.deepcopy(query)
    q2["query"].pop("type", None)
    try:
        return trade_search(league, q2, n), "busca feita sem a base (o site não aceitou a base)"
    except RuntimeError as ex:
        if "HTTP 400" not in str(ex):
            raise
    q3 = copy.deepcopy(q2)
    for grp in q3["query"].get("stats", []):
        grp["filters"] = [f for f in grp.get("filters", []) if f["id"].startswith("pseudo.")]
    try:
        return trade_search(league, q3, n), "busca feita só com vida/resistências (o site recusou algum mod)"
    except RuntimeError:
        raise RuntimeError(first)


def trade_search(league, query, n=10):
    import urllib.parse
    lg = urllib.parse.quote(league)
    j, _ = _http_json(f"{TRADE}/api/trade/search/{lg}", query)
    ids = (j.get("result") or [])[:n]
    if not ids:
        return {"total": j.get("total", 0), "id": j.get("id"), "listings": []}
    j2, _ = _http_json(f"{TRADE}/api/trade/fetch/{','.join(ids)}?query={j['id']}")
    listings = []
    for r in j2.get("result", []) or []:
        if not r:
            continue
        lst, item = r.get("listing", {}), r.get("item", {})
        listings.append({"price": lst.get("price") or {}, "indexed": lst.get("indexed", ""),
                         "ilvl": item.get("ilvl"), "name": (item.get("name") or "") + " " + item.get("typeLine", ""),
                         "mods": [mod_text(m) for m in item.get("explicitMods", [])[:4]]})
    return {"total": j.get("total", 0), "id": j.get("id"), "listings": listings}


def ago(iso):
    import datetime
    try:
        t = datetime.datetime.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=datetime.timezone.utc)
        mins = (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() / 60
    except Exception:
        return ""
    if mins < 60:
        return f"há {int(mins)} min"
    if mins < 60 * 48:
        return f"há {int(mins // 60)} h"
    return f"há {int(mins // 1440)} dias"


# ---------------------------------------------------------------------------
# COMPARAR ITEM (Ctrl+C) x ITEM EQUIPADO
# ---------------------------------------------------------------------------
SLOT_BY_CLASS = {"Body Armours": ["BodyArmour"], "Helmets": ["Helm"], "Gloves": ["Gloves"], "Boots": ["Boots"],
                 "Belts": ["Belt"], "Amulets": ["Amulet"], "Rings": ["Ring", "Ring2"], "Shields": ["Offhand"],
                 "Quivers": ["Offhand"]}
SLOT_PT = {"BodyArmour": "seu peitoral", "Helm": "seu elmo", "Gloves": "suas luvas", "Boots": "suas botas",
           "Belt": "seu cinto", "Amulet": "seu amuleto", "Ring": "seu anel esquerdo", "Ring2": "seu anel direito",
           "Offhand": "seu escudo"}
WEAPON_CLASSES = LOCAL_CLASSES - {"Body Armours", "Helmets", "Gloves", "Boots", "Shields"}
_ATTR_PATTERNS = [
    (re.compile(r"\+(\d+) to all Attributes"), ("str", "dex", "int")),
    (re.compile(r"\+(\d+) to Strength and Dexterity"), ("str", "dex")),
    (re.compile(r"\+(\d+) to Strength and Intelligence"), ("str", "int")),
    (re.compile(r"\+(\d+) to Dexterity and Intelligence"), ("dex", "int")),
    (re.compile(r"\+(\d+) to Strength$"), ("str",)),
    (re.compile(r"\+(\d+) to Dexterity$"), ("dex",)),
    (re.compile(r"\+(\d+) to Intelligence$"), ("int",)),
]


# Outros status que entram no comparativo: (chave, nome, regex do mod, peso, unidade, local_de_defesa)
# local_de_defesa=True: em peça de armadura esse mod já está somado na Armadura/Evasão/ES do item.
EXTRA_STATS = [
    ("flat_eva", "Evasão (mod)", r"\+(\d+) to Evasion Rating", 0.08, "", True),
    ("flat_arm", "Armadura (mod)", r"\+(\d+) to Armour", 0.05, "", True),
    ("flat_es", "Escudo de energia (mod)", r"\+(\d+) to maximum Energy Shield", 0.2, "", True),
    ("inc_eva", "% Evasão global", r"(\d+)% increased Evasion Rating", 0.4, "%", True),
    ("inc_ae", "% Armadura e Evasão global", r"(\d+)% increased Armour and Evasion", 0.4, "%", True),
    ("mana", "Mana", r"\+(\d+) to maximum Mana", 0.2, "", False),
    ("regen", "Regeneração de vida/s", r"Regenerate ([\d.]+) Life per second", 0.5, "", False),
    ("leech", "Roubo de vida", r"([\d.]+)% of Physical Attack Damage Leeched as Life", 4.0, "%", False),
    ("life_kill", "Vida por inimigo morto", r"Gain (\d+) Life per Enemy Killed", 0.3, "", False),
    ("life_hit", "Vida por acerto", r"Gain (\d+) Life per Enemy Hit with Attacks", 0.6, "", False),
    ("block", "Chance de bloqueio (mod)", r"\+(\d+)% Chance to Block(?: Attack Damage)?", 1.5, "%", True),
    ("aspd", "Velocidade de ataque", r"(\d+)% increased Attack Speed", 1.5, "%", False),
    ("dot", "Dano por tempo / veneno / caos", r"(\d+)% increased (?:Damage over Time|Chaos Damage|Damage with Poison|"
                                            r"Poison Duration|Projectile Damage|Damage)", 0.6, "%", False),
    ("chaos_gems", "Nível de gemas de caos", r"\+(\d+) to Level of all Chaos Skill Gems", 25.0, "", False),
    ("proj_gems", "Nível de gemas de projétil", r"\+(\d+) to Level of all Projectile Skill Gems", 20.0, "", False),
    ("crit", "Chance de crítico", r"(\d+)% increased (?:Global )?Critical Strike Chance", 0.2, "%", False),
    ("flask_used", "Menos cargas de frasco gastas", r"(\d+)% reduced Flask Charges used", 1.2, "%", False),
    ("flask_gain", "Mais cargas de frasco", r"(\d+)% increased Flask Charges gained", 1.2, "%", False),
    ("flask_eff", "Efeito de frasco", r"(\d+)% increased (?:Flask Effect Duration|Effect of Flasks)", 0.8, "%", False),
    ("flask_life", "Recuperação de vida dos frascos", r"(\d+)% increased Life Recovery from Flasks", 0.8, "%", False),
    ("acc", "Precisão", r"\+(\d+) to Accuracy Rating", 0.02, "", False),
    ("rarity", "Raridade de itens", r"(\d+)% increased Rarity of Items found|\+(\d+)% to Item Rarity", 0.15, "%", False),
    ("stun", "Recuperação de atordoamento", r"(\d+)% increased Stun and Block Recovery", 0.05, "%", False),
]
_EXTRA_RX = [(k, re.compile(rx)) for k, _, rx, _, _, _ in EXTRA_STATS]
_EXTRA_LOCAL = {k for k, *_r, loc in EXTRA_STATS if loc}


def gear_stats(mod_lines, props_text="", props=None, links=0, req_level=0):
    """Resumo do item: vida, resistências, atributos, movimento, supressão, defesas, links, nível."""
    st = {"life": 0, "fire": 0, "cold": 0, "lightning": 0, "chaos": 0, "str": 0, "dex": 0, "int": 0,
          "ms": 0, "suppress": 0, "evasion": 0, "es": 0, "armour": 0, "ward": 0, "block_base": 0,
          "links": links, "req": req_level or 0}
    for k, _rx in _EXTRA_RX:
        st[k] = 0
    res = {"fire": 0, "cold": 0, "lightning": 0, "chaos": 0}
    res_from_lines(mod_lines, res)
    st.update(res)
    for ln in mod_lines:
        ln = re.sub(r" \((implicit|crafted|fractured|enchant)\)$", "", ln.strip())
        m = re.fullmatch(r"\+(\d+) to maximum Life", ln)
        if m:
            st["life"] += int(m.group(1))
        m = re.fullmatch(r"(\d+)% increased Movement Speed", ln)
        if m:
            st["ms"] += int(m.group(1))
        m = re.fullmatch(r"\+(\d+)% chance to Suppress Spell Damage", ln)
        if m:
            st["suppress"] += int(m.group(1))
        for rx, keys in _ATTR_PATTERNS:
            m = rx.search(ln)
            if m:
                for k in keys:
                    st[k] += int(m.group(1))
                break
        for k, rx in _EXTRA_RX:
            m = rx.fullmatch(ln)
            if m:
                st[k] += float(next(g for g in m.groups() if g))
                break
    if props is not None:          # item vindo da API do site
        for p in props:
            v = str(p.get("values", [[0]])[0][0]) if p.get("values") else "0"
            v = int(re.sub(r"[^\d]", "", v) or 0)
            if p.get("name") == "Evasion Rating":
                st["evasion"] = v
            elif p.get("name") == "Energy Shield":
                st["es"] = v
            elif p.get("name") == "Armour":
                st["armour"] = v
            elif p.get("name") == "Ward":
                st["ward"] = v
            elif p.get("name") == "Chance to Block":
                st["block_base"] = v
    else:                          # item copiado com Ctrl+C
        txt = props_text.replace("\r", "")
        for key, rx in (("evasion", r"(?m)^Evasion Rating: (\d+)"), ("es", r"(?m)^Energy Shield: (\d+)"),
                        ("armour", r"(?m)^Armour: (\d+)"), ("ward", r"(?m)^Ward: (\d+)"),
                        ("block_base", r"(?m)^Chance to Block: (\d+)")):
            m = re.search(rx, txt)
            if m:
                st[key] = int(m.group(1))
    # peça de armadura: os mods locais (+evasão, % armadura e evasão...) já estão nos valores do item
    if st["evasion"] or st["armour"] or st["es"] or st["ward"]:
        for k in _EXTRA_LOCAL:
            st[k] = 0
    return st


def api_item_stats(item):
    sockets = item.get("sockets", []) or []
    groups = {}
    for s_ in sockets:
        groups[s_.get("group")] = groups.get(s_.get("group"), 0) + 1
    req = 0
    for r in item.get("requirements", []) or []:
        if r.get("name") == "Level":
            req = int(re.sub(r"[^\d]", "", str(r["values"][0][0])) or 0)
    return gear_stats(_item_lines(item), props=item.get("properties", []), links=max(groups.values() or [0]),
                      req_level=req)


def char_res_totals(items_json, passives_json, tree_model, act, alira):
    total = {"fire": 0, "cold": 0, "lightning": 0, "chaos": 0}
    for it in (items_json or {}).get("items", []):
        if it.get("inventoryId") in EQUIP_SLOTS:
            res_from_lines(_item_lines(it), total)
    if passives_json:
        nodes = (tree_model or {}).get("nodes", {})
        for h in passives_json.get("hashes", []) or []:
            n = nodes.get(str(h))
            if n:
                res_from_lines(n.get("stats", []), total)
        for jw in passives_json.get("items", []) or []:
            res_from_lines(_item_lines(jw), total)
    if alira and act >= 3:
        for k in ("fire", "cold", "lightning"):
            total[k] += 15
    pen = -60 if act >= 11 else (-30 if act >= 6 else 0)
    for k in total:
        total[k] += pen
    return total


def compare_gear(new, old, totals, slot, char_level, main_links_old=0, main_skill=None):
    """Compara dois itens do mesmo espaço. Retorna (veredito, nota, [linhas])."""
    lines, score = [], 0.0

    def add(label, diff, w, unit="", note=""):
        nonlocal score
        if diff:
            score += diff * w
            sign = "+" if diff > 0 else "−"
            lines.append(((diff > 0), f"{label}: {sign}{abs(diff):g}{unit}{note}"))

    add("Vida", new["life"] - old["life"], 1.0)
    for k, nm in (("fire", "Fogo"), ("cold", "Gelo"), ("lightning", "Raio")):
        d = new[k] - old[k]
        if not d:
            continue
        before = totals.get(k, 0)
        after = before + d
        useful = min(after, 75) - min(before, 75)          # o que conta abaixo do limite
        wasted = d - useful
        score += useful * 1.6 + wasted * 0.1
        status = "no limite ✔" if after >= 75 else f"abaixo do limite ({75 - after}% faltando)"
        lines.append((d > 0 or after >= 75, f"Res. {nm}: {'+' if d > 0 else '−'}{abs(d)}% → você fica com "
                                             f"{min(after, 75)}% ({status})"))
    d = new["chaos"] - old["chaos"]
    if d:
        score += d * 0.5
        lines.append((d > 0, f"Res. Caos: {'+' if d > 0 else '−'}{abs(d)}%"))
    add("Velocidade de movimento", new["ms"] - old["ms"], 3.0 if slot == "Boots" else 2.0, "%")
    add("Supressão de feitiço", new["suppress"] - old["suppress"], 2.5, "%")
    def defense(label, key, w):
        nonlocal score
        a, b = old.get(key, 0), new.get(key, 0)
        if a != b:
            score += (b - a) * w
            lines.append((b > a, f"{label}: {a:g} → {b:g} ({'+' if b > a else '−'}{abs(b - a):g})"))

    defense("Evasão", "evasion", 0.08)          # build de evasão: vale mais
    defense("Armadura", "armour", 0.05)
    defense("Escudo de energia", "es", 0.2)
    defense("Ward", "ward", 0.2)
    defense("Chance de bloqueio", "block_base", 1.5)
    for k, label, _rx, w, unit, _loc in EXTRA_STATS:
        d = round(new.get(k, 0) - old.get(k, 0), 2)
        add(label, d, w, unit)
    add("Força", new["str"] - old["str"], 0.35)
    add("Destreza", new["dex"] - old["dex"], 0.25)
    add("Inteligência", new["int"] - old["int"], 0.15)
    warn = []
    if main_links_old >= 4 and new["links"] < main_links_old:
        score -= 60 * (main_links_old - new["links"])
        warn.append(f"⚠ {SLOT_PT.get(slot, slot).capitalize()} atual segura a {main_skill or 'skill principal'} em "
                    f"{main_links_old}-link; este item tem só {new['links']}-link.")
    if new["req"] and new["req"] > char_level:
        warn.append(f"⚠ Precisa do nível {new['req']} (você está no {char_level}).")
    if score > 15:
        verdict = "✅ MELHOR para a sua build"
    elif score < -15:
        verdict = "❌ PIOR que o seu item atual"
    else:
        verdict = "≈ Parecido (troca lateral)"
    return verdict, score, lines, warn


def clean_advanced_text(text):
    """Texto do Ctrl+Alt+C -> igual ao do Ctrl+C: tira as linhas { ... } e as faixas tipo '45(40-49)'."""
    out = []
    for ln in text.replace("\r", "").split("\n"):
        if ln.strip().startswith("{"):
            continue
        ln = re.sub(r"(\d+(?:\.\d+)?)\([\d.]+-[\d.]+\)", r"\1", ln)
        ln = re.sub(r" — Unscalable Value", "", ln)
        out.append(ln)
    return "\n".join(out)


def apply_guide_mode(cfg):
    """Ativa o guia salvo na configuração (pconc | pob | none)."""
    global STEPS
    mode = cfg.get("guide_mode", "pconc")
    GUIDE.clear()
    if mode == "pob" and cfg.get("guide"):
        GUIDE.update(cfg["guide"])
        GUIDE["mode"] = "pob"
    elif mode == "none":
        GUIDE["mode"] = "none"
    else:
        GUIDE["mode"] = "pconc"
    STEPS = STEPS_PCONC if GUIDE["mode"] == "pconc" else make_generic_steps(guide_bandit())


def start_hotkey_thread(vk, q):
    """Windows: registra uma tecla global que só mostra/esconde o programa (não envia nada ao jogo)."""
    import threading

    def worker():
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            if not user32.RegisterHotKey(None, 1, 0x4000, vk):  # MOD_NOREPEAT
                q.append("fail")
                return
            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == 0x0312:  # WM_HOTKEY
                    q.append("toggle")
        except Exception:
            q.append("fail")
    threading.Thread(target=worker, daemon=True).start()


ACTION_KEYS = ["Desligado", "Ctrl+D", "Alt+D", "Ctrl+Q", "Alt+Q", "Alt+W", "Alt+E", "F2", "F3", "F4", "F5",
               "F6", "F7", "F8"]


def parse_combo(combo):
    """'Ctrl+D' -> (mods do RegisterHotKey, vk). None se inválido/desligado."""
    if not combo or combo == "Desligado":
        return None
    mods, vk = 0, None
    for part in combo.split("+"):
        p = part.strip().upper()
        if p == "CTRL":
            mods |= 0x2
        elif p == "ALT":
            mods |= 0x1
        elif p == "SHIFT":
            mods |= 0x4
        elif re.fullmatch(r"F([1-9]|1[0-2])", p):
            vk = 0x6F + int(p[1:])
        elif len(p) == 1 and p.isalnum():
            vk = ord(p)
    return (mods, vk) if vk else None


def has_pynput():
    try:
        import pynput.keyboard  # noqa: F401
        return True
    except Exception:
        return False


def pynput_combo(combo):
    """'Ctrl+D' -> '<ctrl>+d' (formato do pynput)."""
    if not combo or combo == "Desligado":
        return None
    out = []
    for part in combo.split("+"):
        p = part.strip().lower()
        if p in ("ctrl", "alt", "shift"):
            out.append(f"<{p}>")
        elif re.fullmatch(r"f([1-9]|1[0-2])", p):
            out.append(f"<{p}>")
        elif len(p) == 1:
            out.append(p)
    return "+".join(out) if out else None


def start_linux_hotkeys(combos, q, holder, kind="act"):
    """Linux (X11): teclas globais pelo pynput. combos {nome: 'Ctrl+D'} -> coloca (kind, nome) em q."""
    try:
        from pynput import keyboard
        mapping = {}
        for name, combo in combos.items():
            pc = pynput_combo(combo)
            if pc:
                mapping[pc] = (lambda n=name: q.append((kind, n)))
        if not mapping:
            q.append(("ready", ""))
            return
        lst = keyboard.GlobalHotKeys(mapping)
        lst.daemon = True
        lst.start()
        holder["listener"] = lst
        dbg(f"teclas (Linux) registradas: {list(mapping)}")
        q.append(("ready", ",".join(combos.values())))
    except Exception as ex:
        dbg(f"teclas (Linux) falharam: {ex}")
        q.append(("fail", "?"))


def start_action_hotkeys(combos, q, holder):
    """Windows: teclas globais de ação {nome: 'Ctrl+D'}. Ao apertar, coloca o nome em q.
    holder['tid'] guarda a thread para poder trocar as teclas sem reiniciar."""
    import threading
    if not IS_WIN:
        start_linux_hotkeys(combos, q, holder)
        return

    def worker():
        try:
            import ctypes
            from ctypes import wintypes
            user32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
            holder["tid"] = k32.GetCurrentThreadId()
            ids = {}
            for i, (name, combo) in enumerate(combos.items(), start=10):
                pc = parse_combo(combo)
                if not pc:
                    continue
                if user32.RegisterHotKey(None, i, pc[0] | 0x4000, pc[1]):
                    ids[i] = name
                else:
                    dbg(f"falhou registrar {combo}: erro {ctypes.GetLastError()}")
                    q.append(("fail", name))
            dbg(f"teclas registradas: {[combos[n] for n in ids.values()]} | pedidas: {combos}")
            q.append(("ready", ",".join(combos[n] for n in ids.values())))
            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == 0x0312 and msg.wParam in ids:
                    dbg(f"Windows avisou: tecla {ids[msg.wParam]}")
                    q.append(("act", ids[msg.wParam]))
            for i in ids:
                user32.UnregisterHotKey(None, i)
        except Exception as ex:
            dbg(f"erro na thread das teclas: {ex}")
            q.append(("fail", "?"))
    threading.Thread(target=worker, daemon=True).start()


def stop_action_hotkeys(holder):
    lst = holder.pop("listener", None)
    if lst is not None:
        try:
            lst.stop()
        except Exception:
            pass
    if not IS_WIN:
        return
    try:
        import ctypes
        if holder.get("tid"):
            ctypes.windll.user32.PostThreadMessageW(holder["tid"], 0x0012, 0, 0)  # WM_QUIT
            holder["tid"] = None
    except Exception:
        pass


def _xdotool(*args):
    if not shutil.which("xdotool"):
        return None
    try:
        r = subprocess.run(["xdotool", *args], capture_output=True, text=True, timeout=2)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def poe_is_foreground():
    """(True/False, título da janela da frente)."""
    if not IS_WIN:
        t = _xdotool("getactivewindow", "getwindowname")
        if t is None:
            return True, "(Linux: não dá para ver a janela da frente; instale o xdotool)"
        return ("Path of Exile" in t or "PathOfExile" in t), t
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        hwnd = user32.GetForegroundWindow()
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        t = buf.value or ""
        return ("Path of Exile" in t or "PathOfExile" in t), t
    except Exception as ex:
        return False, f"erro: {ex}"


def poe_running():
    """True se a janela do Path of Exile existe (aberto, mesmo minimizado). None se não der para saber."""
    if not IS_WIN:
        try:
            for pid in os.listdir("/proc"):
                if not pid.isdigit():
                    continue
                try:
                    with open(f"/proc/{pid}/cmdline", "rb") as f:
                        cmd = f.read().decode("utf-8", "ignore")
                except Exception:
                    continue
                if "PathOfExile" in cmd and "PathOfExile2" not in cmd:
                    return True
            return False
        except Exception:
            return None
    try:
        import ctypes
        user32 = ctypes.windll.user32
        if user32.FindWindowW("POEWindowClass", None):
            return True
        return bool(user32.FindWindowW(None, "Path of Exile"))
    except Exception:
        return None


def send_item_copy(advanced):
    """Uma tecla = uma cópia do item (igual ao Awakened PoE Trade): envia Ctrl+C ou Ctrl+Alt+C ao jogo.
    Não faz nenhuma ação no servidor; só copia o texto do item que está sob o mouse."""
    import time
    if not IS_WIN:
        keys = "ctrl+alt+c" if advanced else "ctrl+c"
        if shutil.which("xdotool"):
            subprocess.run(["xdotool", "key", "--clearmodifiers", keys], timeout=3)
            return
        from pynput.keyboard import Controller, Key
        kb = Controller()
        mods = [Key.ctrl, Key.alt] if advanced else [Key.ctrl]
        for m in mods:
            kb.press(m)
        time.sleep(0.03)
        kb.press("c")
        kb.release("c")
        time.sleep(0.01)
        for m in reversed(mods):
            kb.release(m)
        return
    import ctypes
    user32 = ctypes.windll.user32
    KEYUP = 0x2
    VK_CTRL, VK_ALT, VK_C = 0x11, 0x12, 0x43

    def key(vk, up=False):
        sc = user32.MapVirtualKeyW(vk, 0)
        user32.keybd_event(vk, sc, KEYUP if up else 0, 0)

    pressed = []
    for vk in ([VK_CTRL, VK_ALT] if advanced else [VK_CTRL]):
        if not (user32.GetAsyncKeyState(vk) & 0x8000):
            key(vk)
            pressed.append(vk)
    time.sleep(0.03)
    key(VK_C)
    time.sleep(0.03)
    key(VK_C, up=True)
    time.sleep(0.01)
    for vk in reversed(pressed):
        key(vk, up=True)


APP_ICON_PNG = {
    64: "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",
    32: "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAABmJLR0QA/wD/AP+gvaeTAAAID0lEQVRYhZ2XXYxdVRXHf/ucc+/caWeGaenQdvqh9FMghVJELARQgoaYKIZQaHzRGBISxVSNCTXE6IuEoCSIaAgYSHyQWuwLCCSCPqBYQPpBa2unnYLMQKfT6bRzP+bec87eey0fzrmfw5M7OTk3e++7/v/9X2uvtY6hZ6juDeNTEzcRmg2KjPSu/z/DEMzgdby0ce2bxtzju9c6xsx7P78vse7hA0fPBIeOfTzYiH3RmHybAWNMr+1PHKoKCqCoQn8pTLddNVrbtmWVL0bR7su2PvTsAgLv/2P3M8fHZ+7Z9bNXh2r1GAgwxmACk71z8E5C3ahtwCYJVUUle4MwuLifx396R+XKjSN71t30yP0tApP7d9938NjUY/c9+OKQAHFKDpqRoEnAmBaB4aISRRkL55S51LQJ5ODNt6qgqpSKGdHnfnFnZetVK36w9vOPPGt0747w1MiqqTu+tWekXEva4EHQPrkJulQY7lO+tKlEIQwAsF547WTMXGK6Tk8OnCnRJjE8WOLVZ+89t/H8x6PB1OjqGw8c+Sis1VPiVHvAA4wJCEzTDWQuCSEK2j6I8rnMXdkBgo7/d9qMU6U6n3Do2MfR1Nq12yMv6eaDR88OZH5tn7T7j7Tkv/u2UXbdu553DpwhThwApb6IB743yq/+eJo//e1MFg8KqAERIAAEjEEJAMPBo1MDN169fHPkbDJQnY+LzRPS4fMu8CBbOjI2zRtvZ/MmyhRIvOeNt9/nyNg0JsjAVQwGhSAAEZTcLplC5WpcdC4ejCRxqGjXYjPg6AE3xjA+Lazbso0d39+LiLTcsO+JnYz//qU8ThSCjAQ0bec2NbOpokjiiKyziGgOmscAHT5vPkFTIXA2zcm1b6Gzaev0mfTaXjcmmzMGzTFEFOsskdgEFZ/vMx0uoItEE9AEBu9sLz7eppggO1krX7RyhqL5RPMmqXjEJgTWJoj6fKFjU4s9HYSyx9lkQfZzNunaQ4+NXvuiHmsTAucc2vRlV4IzbZlN24gx4NJ0wZqzaUu13rWm1Y6fqAjOOYIuF9Cja4+dZUv62HX3Bs5fqC5QYGa2yq6717NsuNiN3WOsOdd0QWRdgohfuMt08eb265bx1e0j/O7lCQ6OX2zVicwa7H7qENduGOahb6zjpf0zvP7ubCY3ijbZaJuSiMe6hMBZQfLAaVnT9guUu24ZYeu6fn7422McPl3OZA46HJ4XrEPjczzw+GGu+XQfd928LKsN0E5MaAcBxVkhsC5PVgv3AHD9psVsXFngsX0TeNXsOjbzQkDPb4NT4eHnx1m/POSzGxd1G9O2eRGwDgJrBd9UQDvxlWJo2HnrEn7z5+mu28AnKNC1ZuCX+z7knpsvoRga2lq2D+hFsVaInHikVbM1L6mKUcOt24YoX76S23+8lgsfVbgwWeXcB3PMflAmTYWlawZZv30lKzYtgTAgLicktZS4ZklqlpNByC3XDvLa2+Ue+7kLxBPZjhjIgJubDLfcMEzhzqu4siiUxBCooCjiPF4hLIAzEDVPZQyNoB3QUeJY+cRb/OWtMnT0B5BnwkwBQfK6jebtlMk2l0oB54E4SQhfmeGZJ99EgRuuXU1gDPVywg07NvPc4/upVBPu/852yl+/tMvta/pN1g+gXRiighMhsk4QLxm71g1QwshgFWppSkMSqrcNYp/0FPpCBn7yGUbfr6MHLjJ+fYFwwFCfTZn68gBx0p0lU1WC0OCstoigIF6wToic9XjRVudiMl+AUeLYUU1S6pKCerx31GZiLj5xmH+/O8O6p24iTRO88xiFSqNBXAi6CMQN21K03aJlQeisJ7KWFgFUsoZBFUWoVRLqtQaVMMGo4r1Q6o9YtGWI4ePnKddj0kJAbC2pd5QbMbEP2zFghfmqQ5GeNi3IbwF5DEi7f8v0EVRCDp6oserEGaobBkAVESiVCpSvW0N6eT9171AB6zIblTgl1pBPvTjJh19bw9qTcxweq6NCqydskshugRCkVqp9IWm7hc42ivPsP95g+O//Jb0YE+47Rb2acmF2ntrT73DBeuqVhP5XJqjONEjrHvn1acLHxjjy4iR2Nmb0zWneOZEgzre741ztUoHEOqlEVvTk6LJCzaBLVQUkgEDwDhoNy+sHqnwuPM3YqiGu+eY6QIhLAclciqhSGyqweecaCkHE8sGlqHrMFf1sfmWCvx6ap9GweOc7wAVDwOilhXnrGItWnz35z+rSdT4MDf19hkaSk1DBp46xyZRiocrV8wlHrllOpT/Kru3FFFFhdnEBFhcAqJSU/mrCFScqvHfKcmrS4lOHemkpsKjPEEWG5Usit2p67K3whePoF7YOzY4uLXzx+ETSV4wM1ml+GxUTwIWGcnZO2VKusmK6hlohTYQk9mjdU6pYRqbrXH70HMMn5njjP46JaYutW1zDZb2jKov6smp4141DlaGS+dF3/zB3sFUfH9y5+umZstz78r/mh7LUnOX3qBQRLQ4pLIoISxGXLA5YPgiXFIW+POATD+U0YLoK5XnBxw5bd7h5j4sdqGKMEobwlesHKsuGgj2P7vmo/WnWHLt3rvm2E31k6qILz87aAetNEQOmGBKUIsJigOkLMIUIE5IVIQBR1INahyaCTwWJHZp6UCiEmq68tFBdsSSSIDQPPvr85HNNzAVNy44dhJuitdsF3WiMXtaqjcUwZHEYUSqGWghDojDQ0GdNlA8V58VY74lTz7x3JvWtoqBqzgWYUyfdxP4XXqDr8/x/5XEDcW6wRR4AAAAASUVORK5CYII=",
    16: "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABmJLR0QA/wD/AP+gvaeTAAAC60lEQVQ4jW2ST2icVRTFf/e9b/7FSSZpzGgWTSilttrSVq2CSq3UXS2IuhCFLlzWlTuVbiwoBQURN25dCAoaceHWfxVbxXaRYjahwZkkbdJJmsx0xvnme+9977qYVCh44WwO53LvuecKQLt5YeLSxeUPNrb6u5PEWET431IlhJhP7RpZefrZmXPjs+9uS/vahYkvv79y8fynvxwKXhFrMcaAGEYKw76+BzQSY0TznKQgnH/ruYVXTz1+3B47OPXx2x/++EIvVaJYFEvEULRw+kCZfZMJi5uBLAh5hBAhc5FLVxr1h/dUR5OVte2ZzCvG2CGsQYxw9qUHqFciANP7x/lk7hYqZscKZD5n+ebWbOLSNBFjEAxiDGIFY4XV/hgffXMNVeW1U0cwSYuYg6hBVBGjuDRNkuAzBEHMXYAYyIPn7ilj7oa8MtSoIAjBZ5jgHSJDQgREhCQx7KoKCCAwcd+QE9nRIIgIwTtMcG44Zie6WrXAy89M8e3Pjf+2+vqH67z41CS1auEebXAOk/l8J2IF4PmjVeZ+W6PTD4g1iDW0+4Gvfmpy4lD5Hm3mcxLnAqqKqvLE4Rqzbx7jzBvK1koHJTI+W6VcLdHtpZS6Ax7dWuDP+TsoinMB44OiGtEYmX2oRvrIGGu/Nriz0GJ6w9G5eoul7xYpHR2D43Wm946gMaIa8UFJMp8PPywK3X6Gb/e4XXT41Q5rD0Y2rcWVcuh0kQiDvkNjJBKHFrwPXqMSY84fv7d48nKD7ZUOlXKBpROTuC/+Jt10mM96VA7XmL/aIcYcgxJCDEmlKMuJjTgPrfU+63NN6o+NsXV/hV6jR/HgKHVbobzeZXPuJhutlJjnJAUYKUrTvnJy/HLJmtM3Nn1dVem0I/52oLadUmp2Kd5I4Xqb1fl/WF7sE1JPKYGTR0b+OrDHnhGAd16fmVhtufe7g7hXo5aTibKV0WJiStYAxCyP2nUhbA9yMTKolszSvt3lc+993mj/C8N8fJEy8nvOAAAAAElFTkSuQmCC",
}


APP_ICON_ICO = "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"
ICON_FILE = os.path.join(DATA_DIR, "icone.ico")


def linux_shortcut(cfg, here, frozen):
    """Linux: cria o lançador .desktop (menu de aplicativos e área de trabalho) com o ícone do frasco FL."""
    import base64
    try:
        icon = os.path.join(DATA_DIR, "icone.png")
        with open(icon, "wb") as f:
            f.write(base64.b64decode(APP_ICON_PNG[64]))
        exe = here if frozen else f'{sys.executable} "{here}"'
        if frozen:
            exe = f'"{here}"'
        txt = ("[Desktop Entry]\nType=Application\nName=FL PoE Helper\n"
               "Comment=Ajudante de campanha para Path of Exile 1\n"
               f"Exec={exe}\nIcon={icon}\nTerminal=false\nCategories=Game;Utility;\n")
        made = False
        for d in (os.path.join(os.path.expanduser("~"), ".local", "share", "applications"),
                  os.path.join(os.path.expanduser("~"), "Desktop"),
                  os.path.join(os.path.expanduser("~"), "Área de Trabalho")):
            if d.endswith("applications"):
                os.makedirs(d, exist_ok=True)
            if os.path.isdir(d):
                path = os.path.join(d, "fl-poe-helper.desktop")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(txt)
                os.chmod(path, 0o755)
                made = True
        if made:
            cfg["shortcut_target"] = here
        return made
    except Exception as ex:
        dbg(f"atalho Linux: {ex}")
        return False


def ensure_desktop_shortcut(cfg, force=False):
    """Cria (uma vez) o atalho 'FL PoE Helper' na área de trabalho, com o ícone do frasco FL."""
    import sys
    frozen = getattr(sys, "frozen", False)
    here = os.path.abspath(sys.argv[0] if sys.argv and sys.argv[0] else __file__)
    if cfg.get("shortcut_target") == here and not force:
        return False
    if not IS_WIN:
        return linux_shortcut(cfg, here, frozen)
    import base64
    import subprocess
    import sys
    try:
        with open(ICON_FILE, "wb") as f:
            f.write(base64.b64decode(APP_ICON_ICO))
        script = os.path.abspath(sys.argv[0] if sys.argv and sys.argv[0] else __file__)
        exe = sys.executable
        if exe.lower().endswith("python.exe") and os.path.isfile(exe[:-10] + "pythonw.exe"):
            exe = exe[:-10] + "pythonw.exe"          # abre sem janela preta
        args = "" if frozen else f'"{script}"'      # no .exe o atalho abre o próprio .exe
        q = lambda x: x.replace("'", "''")
        ps = (
            "$d=[Environment]::GetFolderPath('Desktop');"
            "Remove-Item -LiteralPath (Join-Path $d 'PConc Helper.lnk') -ErrorAction SilentlyContinue;"
            "$s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'FL PoE Helper.lnk'));"
            f"$s.TargetPath='{q(exe)}';"
            f"$s.Arguments='{q(args)}';"
            f"$s.WorkingDirectory='{q(os.path.dirname(script))}';"
            f"$s.IconLocation='{q(ICON_FILE)},0';"
            "$s.Description='FL PoE Helper - ajudante de Path of Exile';"
            "$s.Save()"
        )
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                           capture_output=True, text=True, timeout=30, creationflags=0x08000000)
        dbg(f"atalho: código {r.returncode} {(r.stderr or '').strip()[:200]}")
        if r.returncode == 0:
            cfg["shortcut_target"] = here
            return True
    except Exception as ex:
        dbg(f"atalho: erro {ex}")
    return False


# O Tk do Linux pode travar (segfault) ao desenhar emoji colorido. No Windows mostramos o emoji;
# fora dele trocamos por um texto equivalente, para o programa não fechar sozinho.
UI_EMOJI_FALLBACK = {
    "💰": "$", "🤖": "IA", "🏠": "", "🧪": "", "💡": "", "🎮": "", "🌳": "", "📘": "",
    "⚙": "", "⚔": "", "⚖": "", "📍": "", "⚠": "!", "✅": "OK", "❌": "X", "▶": ">",
    "▸": ">", "①": "1)", "②": "2)",
}


def ui_text(s):
    """Texto seguro para botão/rótulo: fora do Windows, troca o emoji que pode travar o Tk."""
    if IS_WIN or not isinstance(s, str) or not s:
        return s
    out = s
    for emo, alt in UI_EMOJI_FALLBACK.items():
        if emo in out:
            out = out.replace(emo, alt)
    out = " ".join(out.split())
    return out or s


def dark_titlebar(win, color="#0f1115"):
    """Barra de título escura (Windows 10/11), da mesma cor do programa, no lugar da barra branca."""
    if os.name != "nt":
        return
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()
        on = ctypes.c_int(1)
        for attr in (20, 19):                      # DWMWA_USE_IMMERSIVE_DARK_MODE (novo / antigo)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(on), 4) == 0:
                break
        c = color.lstrip("#")
        bgr = ctypes.c_int(int(c[4:6] + c[2:4] + c[0:2], 16))    # COLORREF = 0x00BBGGRR
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(bgr), 4)   # cor da barra (Win11)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(bgr), 4)   # cor da borda (Win11)
    except Exception:
        pass


def set_app_icon(root):
    """Ícone do app (frasco FL) na janela, nas janelas filhas e na barra de tarefas."""
    import tkinter as tk
    try:
        imgs = [tk.PhotoImage(master=root, data=APP_ICON_PNG[n]) for n in (64, 32, 16)]
        root.iconphoto(True, *imgs)
        root._app_icons = imgs          # guarda a referência (senão o Tk apaga a imagem)
    except Exception as ex:
        dbg(f"ícone: {ex}")


DEBUG_LOG = os.path.join(LOG_DIR, "debug.txt")


def dbg(msg):
    """Registro passo a passo dos atalhos (para achar onde trava)."""
    import time
    try:
        if os.path.isfile(DEBUG_LOG) and os.path.getsize(DEBUG_LOG) > 300_000:
            os.remove(DEBUG_LOG)
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%H:%M:%S ") + str(msg) + "\n")
    except Exception:
        pass


def clip_seq():
    """Número que o Windows aumenta a cada cópia (mesmo se o texto for igual)."""
    try:
        import ctypes
        return ctypes.windll.user32.GetClipboardSequenceNumber()
    except Exception:
        return None


def clip_text():
    """Lê o texto da área de transferência direto do Windows."""
    import ctypes
    from ctypes import wintypes
    user32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
    user32.GetClipboardData.restype = wintypes.HANDLE
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    k32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    for _ in range(5):
        if user32.OpenClipboard(None):
            break
        import time
        time.sleep(0.02)
    else:
        return None
    try:
        h = user32.GetClipboardData(13)  # CF_UNICODETEXT
        if not h:
            return None
        ptr = k32.GlobalLock(h)
        if not ptr:
            return None
        try:
            return ctypes.wstring_at(ptr)
        finally:
            k32.GlobalUnlock(h)
    finally:
        user32.CloseClipboard()



# ---------------------------------------------------------------------------
# Perguntar ao Claude (assistente da build)
# ---------------------------------------------------------------------------
CLAUDE_MODEL = "claude-sonnet-5-5"
CLAUDE_SYSTEM = (
    "Você é um professor experiente de Path of Exile 1 (liga 3.30). Responda sempre em português do Brasil, "
    "de forma curta, direta e prática, como quem está ajudando alguém no meio do jogo. Use listas curtas. "
    "Baseie-se nos dados do personagem que vierem junto (nível, ato, equipamento, gemas, resistências). "
    "Se faltar informação para responder com certeza, diga o que falta em uma linha."
)
QUICK_QUESTIONS = [
    "O que devo melhorar primeiro agora?",
    "Estou pronto para o próximo chefe?",
    "Meus itens estão bons? O que trocar?",
    "Minhas gemas e links estão certos?",
    "Que passivos pegar nos próximos níveis?",
]


def build_context_text(state, items=None, passives=None, model=None):
    """Resumo da build em texto (vai junto com a pergunta)."""
    L = []
    L.append(f"Build/guia: {guide_name()}")
    L.append(f"Personagem: {state.char or '?'} ({state.char_class or '?'}), nível {state.level}")
    L.append(f"Momento: {'pós-campanha (mapas)' if state.act >= 11 else 'Ato ' + str(state.act)}"
             + (f", zona: {state.zone}" if state.zone else "")
             + (f" (nível da área {state.area_level})" if getattr(state, "area_level", 0) else ""))
    b = guide_bandit()
    if b:
        L.append(f"Bandido: {b}")
    if items:
        try:
            alira = (GUIDE["mode"] == "pconc") or b == "Alira"
            tot = char_res_totals(items, passives or {}, model, state.act, alira)
            L.append("Resistências (com penalidade do ato): " + ", ".join(
                f"{n} {tot.get(k, 0)}%" for k, n in (("fire", "fogo"), ("cold", "gelo"),
                                                       ("lightning", "raio"), ("chaos", "caos"))))
        except Exception:
            pass
        L.append("Equipamento:")
        for it in items.get("items", []):
            slot = it.get("inventoryId", "")
            if slot in ("MainInventory", "ExpandedMainInventory"):
                continue
            name = " ".join(x for x in (it.get("name"), it.get("typeLine") or it.get("baseType")) if x).strip()
            mods = [m for m in _item_lines(it)][:8]
            socks = it.get("sockets") or []
            groups = {}
            for sk in socks:
                groups[sk.get("group", 0)] = groups.get(sk.get("group", 0), 0) + 1
            link = f" [{max(groups.values())}L]" if groups and max(groups.values()) > 1 else ""
            L.append(f"- {slot}: {name} ({it.get('rarity', '')}){link}" + (": " + "; ".join(mods) if mods else ""))
            gems = [g.get("typeLine", "") for g in it.get("socketedItems", []) or []]
            if gems:
                L.append(f"    gemas: {' + '.join(gems)}")
    if passives and passives.get("hashes") is not None:
        L.append(f"Pontos de passiva usados: {len(passives.get('hashes', []))}")
    return "\n".join(L)


def ask_claude_api(key, question, context, history=None):
    """Pergunta pela API da Anthropic (só quando o usuário coloca a própria chave)."""
    import urllib.request
    import urllib.error
    msgs = list(history or [])
    msgs.append({"role": "user", "content": f"Dados do meu personagem agora:\n{context}\n\nPergunta: {question}"})
    body = json.dumps({"model": CLAUDE_MODEL, "max_tokens": 1200, "system": CLAUDE_SYSTEM,
                       "messages": msgs}).encode("utf-8")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST",
                                 headers={"x-api-key": key.strip(), "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            j = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        msg = ""
        try:
            msg = json.loads(e.read().decode("utf-8", "replace")).get("error", {}).get("message", "")
        except Exception:
            pass
        if e.code == 401:
            raise RuntimeError("a chave não foi aceita. Confira se colou a chave inteira (começa com sk-ant-).")
        if "credit" in msg.lower():
            raise RuntimeError("a chave está sem crédito. Coloque crédito no console.anthropic.com.")
        if e.code == 429:
            raise RuntimeError("muitas perguntas seguidas. Espere alguns segundos e tente de novo.")
        raise RuntimeError(f"HTTP {e.code}" + (f" – {msg}" if msg else ""))
    txt = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
    msgs.append({"role": "assistant", "content": txt})
    return txt, msgs[-6:]       # guarda só as últimas trocas para continuar a conversa


def run_app():
    import threading
    import tkinter as tk
    from tkinter import filedialog

    cfg = load_config()
    cfg.setdefault("checks", {})
    cfg.setdefault("alpha", 0.92)
    cfg.setdefault("follow", True)
    cfg.setdefault("compact", False)
    cfg.setdefault("act", 1)
    cfg.setdefault("no_focus", True)
    if not cfg.get("log_path") or not os.path.isfile(cfg.get("log_path", "")):
        cfg["log_path"] = find_default_log()

    if not cfg.get("checks_v3"):
        cfg["checks"] = {k: v for k, v in cfg.get("checks", {}).items() if not k.startswith("s2:")}
        cfg["checks_v3"] = True
    cfg.setdefault("runs", {})
    cfg.setdefault("trials", {})
    cfg.setdefault("hotkey", "F9")
    apply_guide_mode(cfg)
    state = LogState(act=cfg["act"], runs=cfg["runs"])
    active_now = {"on": False, "n": 0}
    tail = {"pos": 0, "path": ""}

    if os.name == "nt":
        try:   # faz o Windows mostrar o ícone do app na barra de tarefas (e não o do Python)
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("BonrArd.FLPoEHelper")
        except Exception:
            pass
    root = tk.Tk()
    set_app_icon(root)
    if os.environ.get("FLPOE_SMOKE"):
        root.after(int(os.environ.get("FLPOE_SMOKE_MS", "9000")), lambda: (print("SMOKE_OK", flush=True),
                                                                          root.destroy()))
    _darked = set()

    def _on_map(e):
        w_ = e.widget
        if isinstance(w_, (tk.Tk, tk.Toplevel)) and str(w_) not in _darked:
            _darked.add(str(w_))
            w_.after(10, lambda: dark_titlebar(w_, BG))
    root.bind_class("Toplevel", "<Map>", _on_map, add="+")
    root.bind("<Map>", _on_map, add="+")
    root.title(APP_NAME)

    smoke_err = []

    def report_error(exc, val, tb):
        import traceback
        txt = "".join(traceback.format_exception(exc, val, tb))
        if os.environ.get("FLPOE_SMOKE"):
            print("SMOKE_ERROR\n" + txt, file=sys.stderr, flush=True)
            smoke_err.append(txt)
        try:
            with open(ERROR_LOG, "a", encoding="utf-8") as f:
                f.write(txt + "\n")
        except Exception:
            pass
        try:
            show_warning(f"Erro: {val}. Detalhes em {ERROR_LOG}")
        except Exception:
            pass
    root.report_callback_exception = report_error
    root.configure(bg=BG)
    root.attributes("-topmost", True)
    try:
        root.attributes("-alpha", cfg["alpha"])
    except Exception:
        pass
    root.geometry(cfg.get("geometry", "400x640+40+80"))
    root.minsize(320, 160)

    view_act = tk.IntVar(value=cfg["act"])
    follow = tk.BooleanVar(value=cfg["follow"])
    tree_choice = tk.StringVar(value="")

    font = ("Segoe UI", 10)
    font_b = ("Segoe UI", 10, "bold")
    font_h = ("Segoe UI", 12, "bold")
    font_s = ("Segoe UI", 9)

    # --- topo: status ---
    top = tk.Frame(root, bg=BG)
    top.pack(fill="x", padx=8, pady=(8, 4))
    lbl_status = tk.Label(top, text="", bg=BG, fg=MUTED, font=font_s, anchor="w", justify="left")
    lbl_status.pack(fill="x")

    nav = tk.Frame(root, bg=BG)
    nav.pack(fill="x", padx=8)
    btn_prev = tk.Button(nav, text="◀", width=3, bg=BG2, fg=FG, relief="flat",
                         activebackground=BG2, activeforeground=ACCENT)
    btn_prev.pack(side="left")
    lbl_act = tk.Label(nav, text="", bg=BG, fg=ACCENT, font=font_h)
    lbl_act.pack(side="left", expand=True)
    btn_next = tk.Button(nav, text="▶", width=3, bg=BG2, fg=FG, relief="flat",
                         activebackground=BG2, activeforeground=ACCENT)
    btn_next.pack(side="right")

    chk_follow = tk.Checkbutton(root, text="Seguir o jogo automaticamente", variable=follow,
                                bg=BG, fg=MUTED, selectcolor=BG2, activebackground=BG,
                                activeforeground=FG, font=font_s, anchor="w")
    chk_follow.pack(fill="x", padx=6)

    no_focus = tk.BooleanVar(value=cfg["no_focus"])

    def apply_no_focus():
        cfg["no_focus"] = no_focus.get()
        save_config(cfg)
        set_no_activate(root, no_focus.get())

    chk_focus = tk.Checkbutton(root, text="Não tirar o foco do jogo (desmarque para arrastar a janela)",
                               variable=no_focus, command=apply_no_focus,
                               bg=BG, fg=MUTED, selectcolor=BG2, activebackground=BG,
                               activeforeground=FG, font=font_s, anchor="w")
    chk_focus.pack(fill="x", padx=6)

    # --- faixa de aviso ---
    warn = tk.Label(root, text="", bg=WARN_BG, fg=WARN_FG, font=font_b, wraplength=370,
                    justify="left", anchor="w", padx=8, pady=6)

    # --- corpo rolável ---
    body_wrap = tk.Frame(root, bg=BG)
    body_wrap.pack(fill="both", expand=True, padx=8, pady=4)
    canvas = tk.Canvas(body_wrap, bg=BG, highlightthickness=0)
    sb = tk.Scrollbar(body_wrap, orient="vertical", command=canvas.yview)
    body = tk.Frame(canvas, bg=BG)
    body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    win_id = canvas.create_window((0, 0), window=body, anchor="nw")
    canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win_id, width=e.width))
    canvas.configure(yscrollcommand=sb.set)
    canvas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    def _wheel(e):
        canvas.yview_scroll(int(-e.delta / 120), "units")
    canvas.bind_all("<MouseWheel>", _wheel)

    # --- rodapé: árvore e botões ---
    foot = tk.Frame(root, bg=BG)
    foot.pack(fill="x", padx=8, pady=(4, 8))

    # menus organizados em grupos, na ordem de uso
    def section(title):
        title = ui_text(title)
        f = tk.Frame(foot, bg=BG)
        f.pack(fill="x", pady=(6, 0))
        tk.Label(f, text=title, bg=BG, fg=ACCENT, font=font_b, anchor="w").pack(fill="x")
        return f

    def subrow(parent):
        r_ = tk.Frame(parent, bg=BG)
        r_.pack(fill="x")
        return r_

    sec_game = section("🎮 Durante o jogo")
    row_game = subrow(sec_game)
    sec_tree = section("🌳 Árvore de passivos")
    tree_menu = tk.OptionMenu(sec_tree, tree_choice, "")
    tree_menu.configure(bg=BG2, fg=FG, activebackground=BG2, activeforeground=ACCENT,
                        relief="flat", highlightthickness=0, font=font_s)
    tree_menu["menu"].configure(bg=BG2, fg=FG, font=font_s)
    tree_menu.pack(fill="x", pady=(2, 2))
    row_tree = subrow(sec_tree)
    sec_guide = section("📘 Guia e personagem")
    row_guide = subrow(sec_guide)
    sec_cfg = section("⚙ Configurações")
    cfg_a = subrow(sec_cfg)
    row = row_tree
    BTN = {}

    def mk_btn(parent, text, cmd):
        b = tk.Button(parent, text=ui_text(text), command=cmd, bg=BG2, fg=FG, relief="flat",
                      activebackground="#2a2f3a", activeforeground=ACCENT, font=font_s, padx=6)
        b.pack(side="left", padx=(0, 4), pady=2)
        BTN[text] = b
        return b

    def rebuild_tree_menu():
        menu = tree_menu["menu"]
        menu.delete(0, "end")
        titles = [t["title"] for t in guide_trees()]
        for t in titles or ["(este modo não tem árvore)"]:
            menu.add_command(label=t, command=lambda v=t: tree_choice.set(v))
        tree_choice.set(titles[0] if titles else "(este modo não tem árvore)")
        cfg["tree_manual"] = False

    def open_tree():
        name = tree_choice.get()
        for t in guide_trees():
            if t["title"] == name:
                url = t.get("url") or ""
                if url:
                    webbrowser.open(url)
                else:
                    show_warning("Esta árvore não tem link do site; use 'Ver árvore aqui'.")
                return

    tree_win = {"w": None}

    def view_tree():
        # o botão abre e FECHA a árvore
        if tree_win["w"] is not None:
            try:
                if tree_win["w"].winfo_exists():
                    tree_win["w"].destroy()
                    tree_win["w"] = None
                    return
            except Exception:
                pass
            tree_win["w"] = None
        titles = [t["title"] for t in guide_trees()]
        if not titles:
            show_warning("Sem guia não há árvore. Importe um guia no 🏠 Home.")
            return
        idx = titles.index(tree_choice.get()) if tree_choice.get() in titles else 0
        w = open_tree_viewer(root, idx, (BG, BG2, FG, MUTED, ACCENT),
                             ctx=lambda: {"act": state.act, "level": state.level,
                                          "account": cfg.get("account"), "char": state.char})
        tree_win["w"] = w
        try:
            w.lift()
            w.attributes("-topmost", True)
        except Exception:
            pass

        def on_close_tree():
            tree_win["w"] = None
            w.destroy()
        w.protocol("WM_DELETE_WINDOW", on_close_tree)
        if cfg.get("no_focus", True):
            w.after(300, lambda: set_no_activate(w, True))

    mk_btn(row, "Ver/fechar árvore", view_tree)
    mk_btn(row, "Site", open_tree)
    def open_guide():
        if GUIDE["mode"] == "pconc":
            webbrowser.open(GUIDE_URL)
        elif GUIDE.get("source"):
            webbrowser.open(GUIDE["source"])
        else:
            show_warning("Este guia não tem link. Veja as notas no 🏠 Home.")

    mk_btn(row_guide, "Abrir guia", open_guide)

    def choose_log():
        p = filedialog.askopenfilename(
            title="Selecione o Client.txt (pasta 'logs' do Path of Exile)",
            filetypes=[("Client.txt", "Client.txt"), ("Texto", "*.txt"), ("Todos", "*.*")])
        if p:
            cfg["log_path"] = p
            save_config(cfg)
            start_log()

    mk_btn(cfg_a, "Client.txt", choose_log)

    def toggle_compact():
        cfg["compact"] = not cfg["compact"]
        apply_compact()
        save_config(cfg)

    btn_compact = mk_btn(cfg_a, "Compacto", toggle_compact)

    def make_shortcut():
        def worker():
            ok = ensure_desktop_shortcut(cfg, force=True)
            res_sc["ok"] = ok
        res_sc = {}
        threading.Thread(target=worker, daemon=True).start()

        def wait():
            if "ok" in res_sc:
                save_config(cfg)
                show_warning("Atalho 'FL PoE Helper' criado na área de trabalho." if res_sc["ok"]
                             else "Não consegui criar o atalho (veja registros\\debug.txt na pasta de dados).")
            else:
                root.after(300, wait)
        root.after(300, wait)
    mk_btn(cfg_a, "Atalho na área de trabalho", make_shortcut)

    def open_data_dir():
        try:
            if IS_WIN:
                os.startfile(DATA_DIR)
            else:
                subprocess.Popen(["xdg-open", DATA_DIR])
        except Exception as ex:
            show_warning(f"Pasta de dados: {DATA_DIR} ({ex})")
    mk_btn(cfg_a, "Pasta de dados", open_data_dir)
    _here = os.path.abspath(__import__("sys").argv[0] or __file__)
    if cfg.get("shortcut_target") != _here:
        root.after(2000, make_shortcut)       # cria/atualiza o atalho quando o programa muda de lugar

    row2 = tk.Frame(sec_cfg, bg=BG)
    row2.pack(fill="x")

    def change_alpha(delta):
        cfg["alpha"] = min(1.0, max(0.4, round(cfg["alpha"] + delta, 2)))
        for w in (root, bar):
            try:
                w.attributes("-alpha", cfg["alpha"])
            except Exception:
                pass
        save_config(cfg)

    mk_btn(row2, "Transparência −", lambda: change_alpha(-0.08))
    mk_btn(row2, "Transparência +", lambda: change_alpha(+0.08))

    def reset_checks():
        cfg["checks"] = {}
        save_config(cfg)
        render()

    mk_btn(row_guide, "Zerar checklist", reset_checks)

    def new_character():
        state.act, state.level, state.char, state.char_class = 1, 1, "", ""
        state.nav = nav_for(state.zone, 1)
        cfg["act"] = 1
        cfg["checks"] = {}
        cfg["tree_manual"] = False
        save_config(cfg)
        view_act.set(1)
        follow.set(True)
        update_status()
        render()
        show_warning("Novo personagem: voltei para o Ato 1 e zerei o checklist.")

    row3 = row_guide
    row3.pack(fill="x")
    mk_btn(row_guide, "Novo personagem", new_character)

    regex_pop = {"w": None}

    def toggle_regex(anchor=None):
        if regex_pop["w"] is not None:
            regex_pop["w"].destroy()
            regex_pop["w"] = None
            return
        pop = tk.Toplevel(root)
        pop.overrideredirect(True)
        pop.attributes("-topmost", True)
        pop.configure(bg=BG2, highlightthickness=1, highlightbackground="#3a3f4a")
        tk.Label(pop, text="Clique para COPIAR e cole com Ctrl+V na busca do vendedor/stash",
                 bg=BG2, fg=ACCENT, font=font_s).pack(fill="x", padx=8, pady=(6, 4))

        def copy(txt, label):
            root.clipboard_clear()
            root.clipboard_append(txt)
            root.update()
            show_warning(f"Copiado: {label}. Cole com Ctrl+V na busca.")
            toggle_regex()
        for label, txt in guide_regexes():
            tk.Button(pop, text=label, command=lambda t=txt, l=label: copy(t, l), bg=BG, fg=FG,
                      relief="flat", activebackground="#2a2f3a", activeforeground=ACCENT,
                      font=font_s, anchor="w").pack(fill="x", padx=8, pady=1)
        tk.Button(pop, text="Fechar", command=toggle_regex, bg=BG, fg=MUTED, relief="flat",
                  font=("Segoe UI", 8)).pack(pady=(4, 6))
        pop.update_idletasks()
        ref = anchor or root
        x = ref.winfo_x() + 10
        y = ref.winfo_y() - pop.winfo_reqheight() - 4 if anchor else ref.winfo_y() + 40
        pop.geometry(f"+{max(0, x)}+{max(0, y)}")
        regex_pop["w"] = pop
        if cfg.get("no_focus", True):
            pop.after(100, lambda: set_no_activate(pop, True))

    mk_btn(row_game, "Regex", lambda: toggle_regex())

    row4 = tk.Frame(sec_cfg, bg=BG)
    row4.pack(fill="x", pady=(2, 0))
    tk.Label(row4, text="Tecla mostrar/esconder:", bg=BG, fg=MUTED, font=font_s).pack(side="left")
    hk_var = tk.StringVar(value=cfg["hotkey"] if cfg["hotkey"] in HOTKEYS else "F9")
    hk_menu = tk.OptionMenu(row4, hk_var, *HOTKEYS.keys())
    hk_menu.configure(bg=BG2, fg=FG, activebackground=BG2, activeforeground=ACCENT,
                      relief="flat", highlightthickness=0, font=font_s)
    hk_menu.pack(side="left", padx=4)

    def on_hk(*_):
        cfg["hotkey"] = hk_var.get()
        save_config(cfg)
        show_warning("Tecla alterada. Feche e abra o programa para valer.")
    hk_var.trace_add("write", on_hk)

    # --- 💰 dicas de farm de divine (por Voidstone) ---
    farm_win = {"w": None}

    def open_farm_tips():
        if farm_win["w"] is not None and farm_win["w"].winfo_exists():
            farm_win["w"].destroy()
            farm_win["w"] = None
            return
        w = tk.Toplevel(root)
        farm_win["w"] = w
        w.title("Como farmar divine")
        w.configure(bg=BG)
        w.attributes("-topmost", True)
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        hh = min(760, sh - 60)
        w.geometry(f"620x{hh}+{(sw - 620) // 2}+{max(10, (sh - hh) // 2)}")
        tk.Label(w, text=ui_text("💰 Divines: como ganhar e onde gastar"), bg=BG, fg=ACCENT,
                 font=("Segoe UI", 15, "bold")).pack(pady=(12, 0))
        n_vs = sum(1 for i in range(len(VOIDSTONES)) if cfg["checks"].get(f"vs:{i}"))

        # troca de aba: GANHAR (por Voidstone) / GASTAR (por orçamento)
        tabs = tk.Frame(w, bg=BG)
        tabs.pack(pady=(6, 0))
        tab = {"cur": cfg.get("farm_tab", "ganhar")}
        tab_btns = {}

        def set_tab(name):
            tab["cur"] = name
            cfg["farm_tab"] = name
            save_config(cfg)
            for k, b in tab_btns.items():
                b.config(bg=ACCENT if k == name else BG2, fg="#0b0c0f" if k == name else FG)
            draw_tab()

        for key, label in (("ganhar", ui_text("① GANHAR divine")), ("gastar", ui_text("② GASTAR divine"))):
            b = tk.Button(tabs, text=label, relief="flat", font=font_b, padx=14, pady=4,
                          command=lambda k=key: set_tab(k))
            b.pack(side="left", padx=4)
            tab_btns[key] = b

        wrap = tk.Frame(w, bg=BG)
        wrap.pack(fill="both", expand=True, padx=12, pady=8)
        cv = tk.Canvas(wrap, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(wrap, orient="vertical", command=cv.yview)
        inner = tk.Frame(cv, bg=BG)
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0, 0), window=inner, anchor="nw", width=560)
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        cv.bind_all("<MouseWheel>", lambda e: cv.yview_scroll(int(-e.delta / 120), "units"))

        def etapa_box(title, resumo, dicas, agora):
            box = tk.Frame(inner, bg=BG2 if agora else BG, padx=10, pady=8,
                           highlightthickness=2 if agora else 0, highlightbackground=ACCENT)
            box.pack(fill="x", pady=4)
            tk.Label(box, text=ui_text(("▶ VOCÊ ESTÁ AQUI — " if agora else "") + title),
                     bg=box["bg"], fg=ACCENT if agora else FG, font=font_b, anchor="w",
                     justify="left", wraplength=520).pack(fill="x")
            tk.Label(box, text=resumo, bg=box["bg"], fg=MUTED, font=font_s, anchor="w",
                     justify="left", wraplength=520).pack(fill="x", pady=(2, 6))
            for d in dicas:
                tk.Label(box, text="•  " + d, bg=box["bg"], fg=FG, font=font_s, anchor="w",
                         justify="left", wraplength=505).pack(fill="x", pady=1)

        def draw_tab():
            for ch in inner.winfo_children():
                ch.destroy()
            cv.yview_moveto(0)
            if tab["cur"] == "ganhar":
                tk.Label(inner, text=f"Você marcou {n_vs} de {len(VOIDSTONES)} Voidstones. "
                                     "As dicas mudam conforme você marca.",
                         bg=BG, fg=MUTED, font=font_s, anchor="w", justify="left",
                         wraplength=540).pack(fill="x", pady=(0, 6))
                atual = max(0, min(len(FARM_STAGES) - 1, n_vs))
                for i, (title, resumo, dicas) in enumerate(FARM_STAGES):
                    etapa_box(title, resumo, dicas, i == atual)
            else:
                top = tk.Frame(inner, bg=BG)
                top.pack(fill="x", pady=(0, 6))
                tk.Label(top, text="Quantos divines você tem?", bg=BG, fg=FG,
                         font=font_b).pack(side="left")
                ent = tk.Entry(top, width=6, bg=BG2, fg=FG, insertbackground=FG, relief="flat",
                               font=font_b, justify="center")
                ent.insert(0, str(cfg.get("divines", 0)))
                ent.pack(side="left", padx=6, ipady=3)

                def salvar_div():
                    try:
                        cfg["divines"] = max(0, int(float(ent.get().replace(",", "."))))
                    except Exception:
                        cfg["divines"] = 0
                        ent.delete(0, "end")
                        ent.insert(0, "0")
                    save_config(cfg)
                    draw_tab()
                tk.Button(top, text="Atualizar", command=salvar_div, bg=ACCENT, fg="#0b0c0f",
                          relief="flat", font=font_b, padx=10).pack(side="left")
                ent.bind("<Return>", lambda e: salvar_div())
                tk.Label(inner, text="Compre de cima para baixo. Cada item só depois que o de cima "
                                     "estiver resolvido — pular etapa é o que mais trava build.",
                         bg=BG, fg=MUTED, font=font_s, anchor="w", justify="left",
                         wraplength=540).pack(fill="x", pady=(0, 6))
                atual = budget_stage(cfg.get("divines", 0))
                for st in BUDGET_STAGES:
                    etapa_box(st[1], st[2], st[3], st is atual)
                tk.Label(inner, text=ui_text("💡 Os preços mudam toda semana. Passe o mouse no item "
                                             "dentro do jogo e aperte a tecla de preço (Ctrl+D) para ver "
                                             "quanto custa hoje."),
                         bg=BG, fg=WARN_FG, font=font_s, anchor="w", justify="left",
                         wraplength=540).pack(fill="x", pady=(8, 0))

            tk.Label(inner, text=ui_text(FARM_FOOTER), bg=BG, fg=WARN_FG, font=font_s, anchor="w",
                     justify="left", wraplength=540).pack(fill="x", pady=(10, 4))
            links = tk.Frame(inner, bg=BG)
            links.pack(fill="x", pady=(0, 10))
            for txt, url in (("poe.ninja (preços)", "https://poe.ninja/"),
                             ("maxroll (estratégias)", "https://maxroll.gg/poe/category/currency-farming"),
                             ("Perguntar à IA", None)):
                tk.Button(links, text=txt, bg=BG2, fg=FG, relief="flat", font=font_s, padx=8,
                          command=(open_ask if url is None else (lambda u=url: webbrowser.open(u)))
                          ).pack(side="left", padx=(0, 6))

        set_tab(tab["cur"])

    # --- render ---
    check_vars = {}

    def render():
        for w in body.winfo_children():
            w.destroy()
        check_vars.clear()
        act = view_act.get()
        lbl_act.config(text=ACT_NAMES.get(act, f"Ato {act}"))

        nav_txt = state.nav
        if act == state.act and state.zone in TOWNS and state.visits(state.zone, state.act) > 1:
            _ni, nt = state.next_step(act, cfg["checks"])
            nav_txt = ("Próximo objetivo: " + nt) if nt else "Ato concluído: siga para o próximo ato."
        if act == state.act and nav_txt:
            box = tk.Frame(body, bg="#1d2a1d", padx=8, pady=6)
            box.pack(fill="x", pady=(2, 8))
            tk.Label(box, text="📍 " + state.zone, bg="#1d2a1d", fg=ACCENT, font=font_b,
                     anchor="w").pack(fill="x")
            tk.Label(box, text=nav_txt, bg="#1d2a1d", fg=FG, font=font, anchor="w",
                     justify="left", wraplength=340).pack(fill="x")

        tk.Label(body, text="Passo a passo", bg=BG, fg=ACCENT, font=font_b,
                 anchor="w").pack(fill="x", pady=(2, 2))
        nxt_i, _ = state.next_step(act, cfg["checks"])
        for i, (step, trig) in enumerate(STEPS.get(act, [])):
            key = step_key(act, i)
            done = state.step_done(act, i, cfg["checks"])
            prefix = "▶ " if i == nxt_i else ""
            if trig:
                # passo automático: só o jogo marca (não dá para clicar sem querer)
                tk.Label(body, text=f"{prefix}{'☑' if done else '☐'} {step}" + ("" if done else f"   ⟶ marca ao entrar em {trig[0]}"),
                         bg=BG, fg=(MUTED if done else (WARN_FG if prefix else FG)),
                         font=(font[0], font[1], "overstrike") if done else font,
                         anchor="w", justify="left", wraplength=340).pack(fill="x", anchor="w")
                continue
            var = tk.BooleanVar(value=done)

            def on_toggle(k=key, v=var):
                cfg["checks"][k] = v.get()
                save_config(cfg)
                render()

            cb = tk.Checkbutton(body, text=prefix + step + "  (marque você)", variable=var, command=on_toggle,
                                bg=BG, fg=(MUTED if done else FG), selectcolor=BG2,
                                activebackground=BG, activeforeground=ACCENT,
                                font=(font[0], font[1], "overstrike") if done else font,
                                anchor="w", justify="left", wraplength=340)
            cb.pack(fill="x", anchor="w")
            check_vars[key] = var

        lvl = state.level if act == state.act else (12 if act > 1 else 1)
        tk.Label(body, text="Gemas agora", bg=BG, fg=ACCENT, font=font_b,
                 anchor="w").pack(fill="x", pady=(10, 2))
        for g in guide_gems(act, lvl):
            tk.Label(body, text="• " + g, bg=BG, fg=FG, font=font, anchor="w",
                     justify="left", wraplength=350).pack(fill="x", anchor="w")

        tk.Label(body, text="Equipamento: vida, resistências, evasão (+ accuracy se faltar).\n"
                            "O frasco de vida é a sua arma: melhore sempre.",
                 bg=BG, fg=MUTED, font=font_s, anchor="w", justify="left",
                 wraplength=350).pack(fill="x", pady=(10, 0))

        def check_row(store, key, text, highlight=False):
            var = tk.BooleanVar(value=store.get(key, False))

            def toggle(k=key, v=var):
                store[k] = v.get()
                save_config(cfg)
                render()
            done = var.get()
            tk.Checkbutton(body, text=text, variable=var, command=toggle,
                           bg=BG, fg=(MUTED if done else (WARN_FG if highlight else FG)),
                           selectcolor=BG2, activebackground=BG, activeforeground=ACCENT,
                           font=(font_s[0], font_s[1], "overstrike") if done else font_s,
                           anchor="w", justify="left", wraplength=340).pack(fill="x", anchor="w")

        if act == 11:
            tk.Label(body, text="Voidstones (endgame)", bg=BG, fg=ACCENT, font=font_b,
                     anchor="w").pack(fill="x", pady=(10, 2))
            for i, v in enumerate(VOIDSTONES):
                check_row(cfg["checks"], f"vs:{i}", v)

            # Dicas de farm conforme as Voidstones já conquistadas
            n_vs = sum(1 for i in range(len(VOIDSTONES)) if cfg["checks"].get(f"vs:{i}"))
            title, resumo, dicas = farm_stage(n_vs)
            fbox = tk.Frame(body, bg=BG2, padx=8, pady=6)
            fbox.pack(fill="x", pady=(8, 2))
            tk.Label(fbox, text=ui_text("💰 Como farmar divine agora"), bg=BG2, fg=ACCENT, font=font_b,
                     anchor="w").pack(fill="x")
            tk.Label(fbox, text=title, bg=BG2, fg=FG, font=font_s, anchor="w", justify="left",
                     wraplength=330).pack(fill="x")
            tk.Label(fbox, text=resumo, bg=BG2, fg=MUTED, font=font_s, anchor="w", justify="left",
                     wraplength=330).pack(fill="x", pady=(2, 4))
            for d in dicas[:2]:
                tk.Label(fbox, text="• " + d, bg=BG2, fg=FG, font=font_s, anchor="w", justify="left",
                         wraplength=330).pack(fill="x")
            bst = budget_stage(cfg.get("divines", 0))
            tk.Label(fbox, text="— Com " + str(cfg.get("divines", 0)) + " divine(s), compre: —",
                     bg=BG2, fg=ACCENT, font=font_s, anchor="w").pack(fill="x", pady=(6, 0))
            for d in bst[3][:2]:
                tk.Label(fbox, text="• " + d, bg=BG2, fg=FG, font=font_s, anchor="w", justify="left",
                         wraplength=330).pack(fill="x")
            tk.Button(fbox, text=ui_text("Abrir o guia de divines ▸"), command=open_farm_tips,
                      bg=ACCENT, fg="#0b0c0f", relief="flat", activebackground="#a8f0a8",
                      font=font_b, padx=8).pack(anchor="w", pady=(6, 0))
            for i, u in enumerate(UPGRADES if GUIDE["mode"] == "pconc" else []):
                if i == 0:
                    tk.Label(body, text="Upgrades da build (ordem do guia)", bg=BG, fg=ACCENT, font=font_b,
                             anchor="w").pack(fill="x", pady=(10, 2))
                check_row(cfg["checks"], f"up:{i}", u)

        # Trials do Labirinto
        tk.Label(body, text="Trials do Labirinto", bg=BG, fg=ACCENT, font=font_b,
                 anchor="w").pack(fill="x", pady=(10, 2))
        for lab, lst in TRIALS:
            done_n = sum(1 for z, a in lst if cfg["trials"].get(trial_key(z, a)))
            tk.Label(body, text=f"{lab}: {done_n}/{len(lst)}" + ("  ✔ pronto para o lab!" if done_n == len(lst) else ""),
                     bg=BG, fg=(ACCENT if done_n == len(lst) else MUTED), font=font_s,
                     anchor="w").pack(fill="x")
            for z, a in lst:
                here = (z == state.zone and a == state.act)
                check_row(cfg["trials"], trial_key(z, a), f"{'⚔ ' if here else ''}Ato {a} – {z}", highlight=here)

        # Tempos e mortes
        sp, total = state.splits()
        r = state.run()
        tk.Label(body, text="Tempos e mortes", bg=BG, fg=ACCENT, font=font_b,
                 anchor="w").pack(fill="x", pady=(10, 2))
        if sp:
            for a, dur, cur, est in sp:
                txt = f"{ACT_NAMES.get(a, a)}: {fmt_dur(dur)}"
                if cur:
                    txt += " (em andamento" + (", pausado ⏸" if not active_now["on"] else "") + ")"
                elif est:
                    txt += " (estimado pelo log)"
                tk.Label(body, text=txt, bg=BG, fg=FG, font=font_s, anchor="w").pack(fill="x")
            tk.Label(body, text="Só conta enquanto você mexe no jogo; parado ou fora do PoE, pausa.",
                     bg=BG, fg=MUTED, font=font_s, anchor="w").pack(fill="x")
            tk.Label(body, text=f"Total: {fmt_dur(total)}   •   Mortes: {(r or {}).get('deaths', 0)}",
                     bg=BG, fg=FG, font=font_b, anchor="w").pack(fill="x")
        else:
            tk.Label(body, text="Começa a contar quando o personagem subir de nível.",
                     bg=BG, fg=MUTED, font=font_s, anchor="w").pack(fill="x")

        sugg = guide_suggest(act, lvl)
        trees_now = guide_trees()
        if sugg is not None and trees_now and not cfg.get("tree_manual"):
            tree_choice.set(trees_now[sugg]["title"])

    def apply_compact():
        if cfg["compact"]:
            body_wrap.pack_forget()
            btn_compact.config(text="Expandir")
        else:
            body_wrap.pack(fill="both", expand=True, padx=8, pady=4, before=foot)
            btn_compact.config(text="Compacto")

    def update_status():
        who = f"{state.char} ({state.char_class})" if state.char else "personagem ainda não detectado"
        zone = state.zone or "—"
        logp = cfg.get("log_path") or "Client.txt NÃO encontrado – clique em 'Client.txt'"
        mult = state.xp()
        xp_txt = f" • Área nv {state.area_level} • XP {mult:.0%}" if mult is not None else ""
        lbl_status.config(text=f"{who} • Nível {state.level}{xp_txt}\nÁrea: {zone} ({ACT_NAMES.get(state.act)})\n"
                               f"Guia: {guide_name()}"
                               + ("" if cfg.get("log_path") else "\nClient.txt NÃO encontrado – clique em 'Client.txt'"))

    warn_job = {"id": None}

    def show_warning(msg):
        warn.config(text=msg)
        warn.pack(fill="x", padx=8, pady=(4, 0), after=chk_follow)
        if warn_job["id"]:
            root.after_cancel(warn_job["id"])
        warn_job["id"] = root.after(12000, lambda: warn.pack_forget())

    def go(delta):
        follow.set(False)
        view_act.set(min(11, max(1, view_act.get() + delta)))
        render()

    btn_prev.config(command=lambda: go(-1))
    btn_next.config(command=lambda: go(+1))

    def on_tree_pick(*_):
        # se o usuário escolheu manualmente uma árvore diferente da sugerida, respeita
        trees_now = guide_trees()
        si = guide_suggest(view_act.get(), state.level)
        sugg = trees_now[si]["title"] if trees_now and si is not None else ""
        cfg["tree_manual"] = tree_choice.get() != sugg

    tree_choice.trace_add("write", on_tree_pick)

    # --- modo barra (faixa fina perto da barra de XP) ---
    bar = tk.Toplevel(root)
    bar.withdraw()
    bar.overrideredirect(True)
    bar.attributes("-topmost", True)
    try:
        bar.attributes("-alpha", cfg["alpha"])
    except Exception:
        pass
    bar.configure(bg=BG, highlightthickness=1, highlightbackground="#3a3f4a")

    grip = tk.Label(bar, text="⠿", bg=BG2, fg=MUTED, font=("Segoe UI", 14), cursor="fleur", padx=4)
    grip.pack(side="left", fill="y")
    bar_btns = tk.Frame(bar, bg=BG)
    bar_btns.pack(side="right", fill="y", padx=(4, 4))
    bar_mid = tk.Frame(bar, bg=BG)
    bar_mid.pack(side="left", fill="both", expand=True, padx=6, pady=2)

    bar_top = tk.Frame(bar_mid, bg=BG)
    bar_top.pack(fill="x")
    lbl_bar_head = tk.Label(bar_top, text="", bg=BG, fg=ACCENT, font=("Segoe UI", 9, "bold"), anchor="w")
    lbl_bar_head.pack(side="left")
    lbl_bar_next = tk.Label(bar_mid, text="", bg=BG, fg=WARN_FG, font=("Segoe UI", 10, "bold"), anchor="w",
                            justify="left")
    lbl_bar_next.pack(fill="x")
    lbl_bar_nav = tk.Label(bar_mid, text="", bg=BG, fg=FG, font=("Segoe UI", 9), anchor="w",
                           justify="left")
    lbl_bar_nav.pack(fill="x")

    BAR = {}

    def bar_btn(text, cmd, tip_fg=FG):
        b = tk.Button(bar_btns, text=ui_text(text), command=cmd, bg=BG2, fg=tip_fg, relief="flat",
                      activebackground="#2a2f3a", activeforeground=ACCENT,
                      font=("Segoe UI", 8), padx=5, pady=0)
        b.pack(side="left", padx=1, pady=4, fill="y")
        BAR[text] = b
        return b

    gems_pop = {"w": None}

    def toggle_gems():
        if gems_pop["w"] is not None:
            gems_pop["w"].destroy()
            gems_pop["w"] = None
            return
        act = state.act if follow.get() else view_act.get()
        lvl = state.level if act == state.act else (12 if act > 1 else 1)
        pop = tk.Toplevel(root)
        pop.overrideredirect(True)
        pop.attributes("-topmost", True)
        pop.configure(bg=BG2, highlightthickness=1, highlightbackground="#3a3f4a")
        tk.Label(pop, text="Gemas agora", bg=BG2, fg=ACCENT, font=font_b, anchor="w").pack(
            fill="x", padx=8, pady=(6, 2))
        for g in guide_gems(act, lvl):
            tk.Label(pop, text="• " + g, bg=BG2, fg=FG, font=font_s, anchor="w",
                     justify="left").pack(fill="x", padx=8)
        tk.Label(pop, text="(clique em 'Gemas' de novo para fechar)", bg=BG2, fg=MUTED,
                 font=("Segoe UI", 8)).pack(padx=8, pady=(4, 6))
        pop.update_idletasks()
        x = bar.winfo_x() + bar.winfo_width() - pop.winfo_reqwidth()
        y = bar.winfo_y() - pop.winfo_reqheight() - 4
        pop.geometry(f"+{max(0, x)}+{max(0, y)}")
        gems_pop["w"] = pop
        if cfg.get("no_focus", True):
            pop.after(100, lambda: set_no_activate(pop, True))

    def mark_next():
        act = state.act if follow.get() else view_act.get()
        i, _ = state.next_step(act, cfg["checks"])
        if i is None:
            return
        trig = STEPS[act][i][1]
        if trig:
            show_warning(f"Este passo é marcado SOZINHO quando você entrar em {trig[0]}.")
            return
        cfg["checks"][step_key(act, i)] = True
        save_config(cfg)
        render()

    # (o texto do próximo passo não é mais clicável, para não marcar sem querer)

    bar_first = bar_btn("✓", mark_next)
    bar_btn("Gemas", toggle_gems)
    bar_btn("Regex", lambda: toggle_regex(bar))
    bar_btn("Árvore", lambda: view_tree())
    bar_btn("⤢", lambda: exit_bar())
    bar_btn("✕", lambda: on_close(), tip_fg="#ff7b7b")

    bar_warn = {"msg": "", "job": None}

    def render_bar():
        act = state.act if follow.get() else view_act.get()
        zone = state.zone if act == state.act and state.zone else ""
        head = "PÓS" if act >= 11 else f"A{act}"
        if zone:
            head += f" • {zone}"
        head += f" • Você nv {state.level}"
        mult = state.xp() if act == state.act else None
        if mult is not None:
            if mult >= 0.999:
                head += f" • Área nv {state.area_level} (XP cheio)"
            else:
                quem = "acima" if state.level > state.area_level else "abaixo"
                head += f" • Área nv {state.area_level} • {quem}: XP só {mult:.0%}"
            lbl_bar_head.config(fg=ACCENT if mult >= 0.9 else (WARN_FG if mult >= 0.6 else "#ff7b7b"))
        else:
            lbl_bar_head.config(fg=ACCENT)
        _sp, total = state.splits()
        r = state.run()
        if total is not None:
            head += f" • Tempo {fmt_dur(total)}" + ("" if active_now["on"] else " ⏸")
        if r:
            head += f" • Mortes {r.get('deaths', 0)}"
        lbl_bar_head.config(text=head)
        _i, nxt = state.next_step(act, cfg["checks"])
        lbl_bar_next.config(text=("▶ " + nxt) if nxt else "✔ Passo a passo deste ato concluído")
        if bar_warn["msg"]:
            lbl_bar_nav.config(text="⚠ " + bar_warn["msg"], bg=WARN_BG, fg=WARN_FG)
        else:
            nav = state.nav if act == state.act else ""
            if act == state.act and state.zone in TOWNS and state.visits(state.zone, state.act) > 1:
                _ni, nt = state.next_step(act, cfg["checks"])
                nav = ("Próximo objetivo: " + nt) if nt else "Ato concluído: siga para o próximo ato."
            lab = trial_lab(state.zone, state.act) if act == state.act else None
            if lab and not cfg["trials"].get(trial_key(state.zone, state.act)):
                nav = f"⚔ TRIAL do {lab} aqui! " + nav
            lbl_bar_nav.config(text=("📍 " + nav) if nav else "📍 Sem dica para esta área.",
                               bg=BG, fg=FG)
        w = bar.winfo_width() if bar.winfo_width() > 50 else cfg.get("bar_w", 820)
        lbl_bar_nav.config(wraplength=max(200, w - 230))
        lbl_bar_next.config(wraplength=max(200, w - 230))

    def bar_warning(msg):
        bar_warn["msg"] = msg
        if bar_warn["job"]:
            root.after_cancel(bar_warn["job"])

        def clear():
            bar_warn["msg"] = ""
            render_bar()
        bar_warn["job"] = root.after(12000, clear)
        render_bar()

    def place_bar(reset=False):
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        w = cfg.get("bar_w") or int(sw * 0.42)
        h = 84
        if reset or "bar_x" not in cfg:
            cfg["bar_x"] = (sw - w) // 2
            cfg["bar_y"] = sh - h - 26   # logo acima da barra de XP
        cfg["bar_w"] = w
        bar.geometry(f"{w}x{h}+{cfg['bar_x']}+{cfg['bar_y']}")

    drag = {"dx": 0, "dy": 0}

    def grip_press(e):
        drag["dx"], drag["dy"] = e.x_root - bar.winfo_x(), e.y_root - bar.winfo_y()

    def grip_move(e):
        cfg["bar_x"], cfg["bar_y"] = e.x_root - drag["dx"], e.y_root - drag["dy"]
        bar.geometry(f"+{cfg['bar_x']}+{cfg['bar_y']}")

    def grip_release(_e):
        save_config(cfg)

    def grip_wheel(e):
        cfg["bar_w"] = max(420, min(root.winfo_screenwidth(), cfg.get("bar_w", 820) + (40 if e.delta > 0 else -40)))
        place_bar()
        render_bar()
        save_config(cfg)
        return "break"

    def grip_reset(_e):
        cfg.pop("bar_w", None)
        place_bar(reset=True)
        render_bar()
        save_config(cfg)

    grip.bind("<ButtonPress-1>", grip_press)
    grip.bind("<B1-Motion>", grip_move)
    grip.bind("<ButtonRelease-1>", grip_release)
    grip.bind("<MouseWheel>", grip_wheel)
    grip.bind("<Double-Button-1>", grip_reset)

    def enter_bar():
        cfg["mode"] = "bar"
        save_config(cfg)
        root.withdraw()
        place_bar()
        bar.deiconify()
        render_bar()
        if cfg.get("no_focus", True):
            bar.after(150, lambda: set_no_activate(bar, True))

    def exit_bar():
        cfg["mode"] = "full"
        save_config(cfg)
        if gems_pop["w"] is not None:
            gems_pop["w"].destroy()
            gems_pop["w"] = None
        bar.withdraw()
        root.deiconify()
        if cfg.get("no_focus", True):
            root.after(150, lambda: set_no_activate(root, True))

    mk_btn(row_game, "Modo barra (perto da XP)", enter_bar)

    # --- transparência automática: some quando o mouse não está em cima ---
    cfg.setdefault("auto_fade", True)
    cfg.setdefault("fade_alpha", 0.3)
    fade = {"cur": {}, "warn_until": 0.0}
    FADE_OPTS = {"Quase invisível (15%)": 0.15, "Bem transparente (30%)": 0.3, "Meio transparente (50%)": 0.5}
    row5 = tk.Frame(sec_cfg, bg=BG)
    row5.pack(fill="x", pady=(2, 0))
    fade_var = tk.BooleanVar(value=cfg["auto_fade"])

    def on_fade_toggle():
        cfg["auto_fade"] = fade_var.get()
        save_config(cfg)

    cwg_var = tk.BooleanVar(value=cfg.get("close_with_game", True))

    def on_cwg():
        cfg["close_with_game"] = cwg_var.get()
        save_config(cfg)
    row_cwg = tk.Frame(sec_cfg, bg=BG)
    row_cwg.pack(fill="x", pady=(2, 0))
    tk.Checkbutton(row_cwg, text="Fechar o FL PoE Helper quando eu fechar o jogo", variable=cwg_var,
                   command=on_cwg, bg=BG, fg=MUTED, selectcolor=BG2, activebackground=BG,
                   activeforeground=FG, font=font_s).pack(side="left")

    tk.Checkbutton(row5, text="Transparente quando não estiver usando:", variable=fade_var,
                   command=on_fade_toggle, bg=BG, fg=MUTED, selectcolor=BG2, activebackground=BG,
                   activeforeground=FG, font=font_s).pack(side="left")
    fade_lvl = tk.StringVar(value=next((k for k, v in FADE_OPTS.items() if abs(v - cfg["fade_alpha"]) < 0.01),
                                       "Bem transparente (30%)"))
    fm = tk.OptionMenu(row5, fade_lvl, *FADE_OPTS.keys())
    fm.configure(bg=BG2, fg=FG, activebackground=BG2, activeforeground=ACCENT, relief="flat",
                 highlightthickness=0, font=font_s)
    fm["menu"].configure(bg=BG2, fg=FG, font=font_s)
    fm.pack(side="left", padx=4)

    def on_fade_lvl(*_):
        cfg["fade_alpha"] = FADE_OPTS.get(fade_lvl.get(), 0.3)
        save_config(cfg)
    fade_lvl.trace_add("write", on_fade_lvl)

    def fade_loop():
        import time
        try:
            win = bar if cfg.get("mode") == "bar" else root
            if win.winfo_viewable():
                full = cfg.get("alpha", 0.92)
                target = full
                if cfg.get("auto_fade", True):
                    px, py = root.winfo_pointerxy()
                    x, y = win.winfo_rootx(), win.winfo_rooty()
                    w_, h_ = win.winfo_width(), win.winfo_height()
                    inside = x - 8 <= px <= x + w_ + 8 and y - 8 <= py <= y + h_ + 8
                    busy = time.time() < fade["warn_until"]
                    if not inside and not busy:
                        target = min(full, cfg.get("fade_alpha", 0.3))
                cur = fade["cur"].get(str(win), full)
                if abs(cur - target) > 0.01:
                    # rápido para aparecer, suave para sumir
                    step = 0.6 if target > cur else 0.18
                    cur = cur + (target - cur) * step
                    if abs(cur - target) < 0.02:
                        cur = target
                    win.attributes("-alpha", cur)
                    fade["cur"][str(win)] = cur
        except Exception:
            pass
        root.after(100, fade_loop)

    root.after(1500, fade_loop)

    # o render/aviso/status da janela grande também atualizam a barra
    _render_full, _warn_full, _status_full = render, show_warning, update_status

    def render():
        _render_full()
        render_bar()

    def show_warning(msg):
        import time
        fade["warn_until"] = time.time() + 12  # aviso aparece com a janela visível
        _warn_full(msg)
        bar_warning(msg)

    def update_status():
        _status_full()
        render_bar()

    # --- checagem antes dos chefes ---
    boss_pop = {"w": None, "job": None}

    def ask_account():
        from tkinter import simpledialog
        acc = simpledialog.askstring(
            "Conta do Path of Exile",
            "Nome da sua conta como aparece no site (ex.: Gabriel#1234).\n"
            "No site: Perfil > Privacy Settings > deixe os PERSONAGENS públicos.",
            initialvalue=cfg.get("account", ""), parent=root)
        if acc:
            cfg["account"] = acc.strip()
            save_config(cfg)
            show_warning("Conta salva. Use 'Boss?' para testar.")

    def boss_opts():
        if GUIDE["mode"] == "pconc":
            return {}
        return {"main_skill": GUIDE.get("main_skill") if GUIDE["mode"] == "pob" else None,
                "flask_weapon": False, "alira": guide_bandit() == "Alira"}

    def boss_for_now():
        b = BOSSES.get((state.zone, state.act))
        if b:
            return b
        same = [v for (z, a), v in BOSSES.items() if a == state.act]
        return same[-1] if same else None

    def close_boss_pop():
        if boss_pop["w"] is not None:
            boss_pop["w"].destroy()
            boss_pop["w"] = None

    def show_boss_check(auto=False):
        close_boss_pop()
        boss = boss_for_now()
        if not boss:
            show_warning("Não há chefe de ato cadastrado para esta parte.")
            return
        name, default_lvl, tip = boss
        boss_level = (state.area_level + 1) if (state.area_level and BOSSES.get((state.zone, state.act))) else default_lvl
        pop = tk.Toplevel(root)
        pop.overrideredirect(True)
        pop.attributes("-topmost", True)
        pop.configure(bg=BG2, highlightthickness=2, highlightbackground=ACCENT)
        tk.Label(pop, text=f"⚔ Próximo chefe: {name}", bg=BG2, fg=ACCENT,
                 font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x", padx=10, pady=(8, 2))
        verdict = tk.Label(pop, text="Checando seu personagem...", bg=BG2, fg=FG,
                           font=("Segoe UI", 11, "bold"), anchor="w")
        verdict.pack(fill="x", padx=10)
        body_f = tk.Frame(pop, bg=BG2)
        body_f.pack(fill="x", padx=10, pady=4)
        tk.Label(pop, text="💡 " + tip, bg=BG2, fg=MUTED, font=font_s, anchor="w", justify="left",
                 wraplength=460).pack(fill="x", padx=10, pady=(2, 4))
        tk.Button(pop, text="Fechar", command=close_boss_pop, bg=BG, fg=FG, relief="flat",
                  activebackground="#2a2f3a", activeforeground=ACCENT, font=font_s).pack(pady=(0, 8))

        def place():
            pop.update_idletasks()
            sw = root.winfo_screenwidth()
            x = (sw - pop.winfo_reqwidth()) // 2
            y = 80
            pop.geometry(f"+{x}+{y}")
        place()
        boss_pop["w"] = pop
        if cfg.get("no_focus", True):
            pop.after(100, lambda: set_no_activate(pop, True))
        icons = {"ok": ("✅", ACCENT), "warn": ("⚠", WARN_FG), "bad": ("❌", "#ff7b7b"), "info": ("ℹ", MUTED)}

        def fill(results, note=""):
            if boss_pop["w"] is not pop:
                return
            for w in body_f.winfo_children():
                w.destroy()
            bad = sum(1 for st_, _ in results if st_ == "bad")
            warn_n = sum(1 for st_, _ in results if st_ == "warn")
            if bad:
                verdict.config(text="❌ Ainda não está pronto — veja o que falta:", fg="#ff7b7b")
            elif warn_n:
                verdict.config(text="⚠ Dá para ir, mas dá para melhorar:", fg=WARN_FG)
            else:
                verdict.config(text="✅ Pronto! Pode ir.", fg=ACCENT)
            for st_, txt in results:
                ic, col = icons.get(st_, ("•", FG))
                tk.Label(body_f, text=f"{ic} {txt}", bg=BG2, fg=col if st_ != "ok" else FG, font=font_s,
                         anchor="w", justify="left", wraplength=460).pack(fill="x", anchor="w")
            if note:
                tk.Label(body_f, text=note, bg=BG2, fg=MUTED, font=("Segoe UI", 8), anchor="w",
                         justify="left", wraplength=460).pack(fill="x", anchor="w", pady=(4, 0))
            place()

        # resultado básico (só pelo log) enquanto busca o resto
        basic = analyze_character(None, None, None, state.act, state.level, boss_level, **boss_opts())[:1]
        if not cfg.get("account"):
            why = "Configure sua conta (botão 'Conta PoE') para checar resistências, links e frascos."
            fill(basic, why)
            return
        fill(basic, "Buscando resistências, links e frascos no site...")
        result = {}

        def worker():
            try:
                items, passives = fetch_character(cfg["account"], state.char)
                model = None
                try:
                    model = load_tree_model(download=True)
                except Exception:
                    pass
                result["r"] = analyze_character(items, passives, model, state.act, state.level, boss_level,
                                               **boss_opts())
                if model is None:
                    result["note"] = "Resistências da árvore não contadas (sem dados da árvore)."
            except Exception as ex:
                result["err"] = str(ex)
        threading.Thread(target=worker, daemon=True).start()

        def wait():
            if "r" in result:
                fill(result["r"], result.get("note", "Resist. = itens + árvore + Alira − penalidade do ato. "
                                                      "Não conta auras/buffs."))
            elif "err" in result:
                fill(basic, f"Não consegui ler o personagem ({result['err']}). Confira o nome da conta e se "
                            "os personagens estão públicos no perfil do site.")
            else:
                root.after(300, wait)
        root.after(300, wait)
        if auto:
            if boss_pop["job"]:
                root.after_cancel(boss_pop["job"])
            boss_pop["job"] = root.after(45000, close_boss_pop)

    mk_btn(cfg_a, "Conta PoE", ask_account)
    mk_btn(row_game, "Checar chefe", lambda: show_boss_check())

    # --- HOME: escolher o guia ---
    home = {"w": None}

    def on_mode_changed(msg=None):
        apply_guide_mode(cfg)
        save_config(cfg)
        state.nav = nav_for(state.zone, state.act)
        rebuild_tree_menu()
        render()
        update_status()
        show_warning(msg or f"Guia ativo: {guide_name()}")

    def show_notes():
        notes = GUIDE.get("notes", "") if GUIDE["mode"] == "pob" else ""
        if not notes.strip():
            show_warning("Este guia não tem notas.")
            return
        w = tk.Toplevel(root)
        w.title("Notas do guia")
        w.attributes("-topmost", True)
        w.geometry("640x560")
        t = tk.Text(w, bg=BG2, fg=FG, wrap="word", font=font_s, padx=10, pady=10, relief="flat")
        t.insert("1.0", notes)
        t.config(state="disabled")
        t.pack(fill="both", expand=True)

    def open_home():
        if home["w"] is not None:
            try:
                home["w"].destroy()
            except Exception:
                pass
        w = tk.Toplevel(root)
        home["w"] = w
        w.title("Início – escolha o seu guia")
        w.configure(bg=BG)
        w.attributes("-topmost", True)
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        hh = min(800, sh - 60)
        w.geometry(f"580x{hh}+{(sw - 580) // 2}+{max(10, (sh - hh) // 2)}")
        tk.Label(w, text=ui_text("🏠 Início"), bg=BG, fg=ACCENT, font=("Segoe UI", 16, "bold")).pack(pady=(12, 0))
        lbl_cur = tk.Label(w, text="", bg=BG, fg=MUTED, font=font_s)
        lbl_cur.pack(pady=(0, 6))

        # aviso de "deu tudo certo" (aparece embaixo por alguns segundos)
        ok_bar = tk.Label(w, text="", bg="#1f6b34", fg="#eaffea", font=font_b, padx=10, pady=8,
                          wraplength=520, justify="center")
        ok_job = {"id": None}

        def show_ok(msg, good=True):
            ok_bar.config(text=msg, bg="#1f6b34" if good else "#7a2424",
                          fg="#eaffea" if good else "#ffecec")
            ok_bar.pack(side="bottom", fill="x", padx=16, pady=(0, 12))
            if ok_job["id"]:
                w.after_cancel(ok_job["id"])
            ok_job["id"] = w.after(6000, ok_bar.pack_forget)

        def refresh_cur():
            lbl_cur.config(text=f"Guia atual: {guide_name()}")

        refresh_cur()

        def card(title, desc, btn_text=None, cmd=None):
            title, btn_text = ui_text(title), ui_text(btn_text)
            f = tk.Frame(w, bg=BG2, padx=12, pady=10)
            f.pack(fill="x", padx=16, pady=5)
            tk.Label(f, text=title, bg=BG2, fg=FG, font=font_b, anchor="w").pack(fill="x")
            d = tk.Label(f, text=desc, bg=BG2, fg=MUTED, font=font_s, anchor="w", justify="left",
                         wraplength=520)
            d.pack(fill="x", pady=(2, 6))
            row_ = tk.Frame(f, bg=BG2)
            row_.pack(fill="x")
            if btn_text:
                tk.Button(row_, text=btn_text, command=cmd, bg=ACCENT, fg="#0b0c0f", relief="flat",
                          activebackground="#a8f0a8", font=font_b, padx=10).pack(side="left")
            return f, row_, d

        def use_pconc():
            cfg["guide_mode"] = "pconc"
            on_mode_changed()
            refresh_cur()
            show_ok("✅ Tudo certo! Guia de exemplo ativado. Pode fechar esta janela e jogar.")

        def use_none():
            cfg["guide_mode"] = "none"
            on_mode_changed()
            refresh_cur()
            show_ok("✅ Tudo certo! Modo sem guia ativado: você recebe as dicas de cada ato.")

        card("1) Guia de exemplo (vem junto)",
             "Um guia pronto para testar o programa: PConc of Bouncing Pathfinder (build de animeprincess, 3.30), "
             "com passo a passo, gemas por fase, 7 árvores, regex e upgrades.", "Usar o guia de exemplo", use_pconc)

        f2, r2, _d2 = card("2) Importar o MEU guia",
                           "Copie o LINK do guia (Mobalytics, pobb.in ou pastebin) ou o CÓDIGO do Path of Building "
                           "(botão 'Copy Code' do guia) e clique abaixo. O programa pega as árvores, as gemas de "
                           "cada fase, o bandido e as notas do guia.", "Colar e importar", lambda: do_import())
        status = tk.Label(f2, text="", bg=BG2, fg=FG, font=font_s, anchor="w", justify="left", wraplength=520)
        status.pack(fill="x", pady=(6, 0))
        tk.Button(r2, text="Digitar link...", command=lambda: do_import(ask=True), bg=BG, fg=FG,
                  relief="flat", font=font_s, padx=8).pack(side="left", padx=6)
        tk.Button(r2, text="Ver notas do guia", command=show_notes, bg=BG, fg=FG,
                  relief="flat", font=font_s, padx=8).pack(side="left")

        def do_import(ask=False):
            text = ""
            if ask:
                from tkinter import simpledialog
                text = simpledialog.askstring("Importar guia", "Cole o link do guia ou o código do PoB:",
                                              parent=w) or ""
            else:
                try:
                    text = root.clipboard_get()
                except Exception:
                    text = ""
            text = (text or "").strip()
            if not text:
                status.config(text="A área de transferência está vazia. Copie o link ou o código primeiro.",
                              fg="#ff7b7b")
                show_ok("❌ Nada para importar: copie o link ou o código do guia primeiro.", good=False)
                return
            status.config(text="Importando...", fg=FG)
            res = {}

            def worker():
                try:
                    res["d"] = import_guide(text)
                except Exception as ex:
                    res["e"] = str(ex)
            threading.Thread(target=worker, daemon=True).start()

            def wait():
                if "d" in res:
                    d = res["d"]
                    cfg["guide"] = d
                    cfg["guide_mode"] = "pob"
                    on_mode_changed(f"Guia importado: {d['name']}")
                    refresh_cur()
                    status.config(text=f"Importado: {d['name']} • {len(d['trees'])} árvores • "
                                       f"{len(d['skillsets'])} setups de gemas • bandido: {d['bandit']}",
                                  fg=ACCENT)
                    show_ok(f"✅ Tudo certo! Guia \"{d['name']}\" importado e ativado.")
                elif "e" in res:
                    status.config(text=f"Não consegui importar ({res['e']}). Se for um link, tente copiar o "
                                       "código do Path of Building no próprio guia ('Copy Code').", fg="#ff7b7b")
                    show_ok("❌ Não deu para importar esse guia. Veja a mensagem no quadro 2.", good=False)
                else:
                    w.after(300, wait)
            w.after(300, wait)

        card("3) Não tenho guia",
             "Só as dicas da campanha: rota de cada área, chefes, trials, bandidos (matar os 3), "
             "aviso de XP, tempos e checagem de resistências antes dos chefes.", "Usar sem guia", use_none)

        # 4) Configurar: conta do PoE (login) e Client.txt
        f4, r4, d4 = card("⚙ Configurar", "")

        def cfg_status():
            acc = cfg.get("account") or ""
            logp = cfg.get("log_path") or ""
            ok_log = bool(logp) and os.path.isfile(logp)
            d4.config(text=("Conta do PoE: " + (f"✅ {acc}" if acc else "⚠ não configurada (opcional: libera checagem "
                                                                      "de chefes, comparador e IA com seus itens)")
                            + "\nClient.txt do jogo: " + ("✅ encontrado" if ok_log else "⚠ não encontrado")))
        cfg_status()
        tk.Label(r4, text="Conta (ex.: Nome#1234):", bg=BG2, fg=FG, font=font_s).pack(side="left")
        acc_e = tk.Entry(r4, width=22, bg=BG, fg=FG, insertbackground=FG, relief="flat", font=font_s)
        acc_e.insert(0, cfg.get("account", ""))
        acc_e.pack(side="left", padx=6, ipady=3)

        def save_acc():
            acc = acc_e.get().strip()
            if not acc:
                show_ok("❌ Digite o nome da conta, como aparece no site (ex.: Nome#1234).", good=False)
                return
            if "#" not in acc:
                show_ok("⚠ Faltou o #número no fim (ex.: Nome#1234). Veja no canto do site do PoE.", good=False)
                return
            cfg["account"] = acc
            save_config(cfg)
            cfg_status()
            show_ok(f"✅ Tudo certo! Conta {acc} salva. Deixe os personagens públicos no site do PoE.")

        tk.Button(r4, text="Salvar conta", command=save_acc, bg=ACCENT, fg="#0b0c0f", relief="flat",
                  activebackground="#a8f0a8", font=font_b, padx=10).pack(side="left")
        acc_e.bind("<Return>", lambda e: save_acc())
        r4b = tk.Frame(f4, bg=BG2)
        r4b.pack(fill="x", pady=(6, 0))

        def pick_log():
            p_ = filedialog.askopenfilename(
                parent=w, title="Selecione o Client.txt (pasta 'logs' do Path of Exile)",
                filetypes=[("Client.txt", "Client.txt"), ("Texto", "*.txt"), ("Todos", "*.*")])
            if p_:
                cfg["log_path"] = p_
                save_config(cfg)
                start_log()
                cfg_status()
                show_ok("✅ Tudo certo! Client.txt configurado: o programa já está lendo o jogo.")

        tk.Button(r4b, text="Escolher Client.txt", command=pick_log, bg=BG, fg=FG, relief="flat",
                  font=font_s, padx=8).pack(side="left")
        tk.Button(r4b, text="Abrir privacidade no site do PoE",
                  command=lambda: webbrowser.open(
                      "https://www.pathofexile.com/account/view-profile/"
                      + (cfg.get("account") or "").replace("#", "-") + "/privacy"
                      if cfg.get("account") else "https://www.pathofexile.com/my-account"),
                  bg=BG, fg=FG, relief="flat", font=font_s, padx=8).pack(side="left", padx=6)

        show_start = tk.BooleanVar(value=cfg.get("home_on_start", True))

        def on_show_start():
            cfg["home_on_start"] = show_start.get()
            save_config(cfg)
        tk.Checkbutton(w, text="Mostrar esta tela sempre que abrir o programa", variable=show_start,
                       command=on_show_start, bg=BG, fg=MUTED, selectcolor=BG2, activebackground=BG,
                       activeforeground=FG, font=font_s).pack(pady=(6, 4))
        try:
            w.lift()
            w.focus_force()
        except Exception:
            pass

    mk_btn(row_guide, "🏠 Início", open_home)
    hb = bar_btn("🏠 Início", open_home)
    hb.pack_configure(before=bar_first)
    tk.Button(nav, text="🏠 Início", command=open_home, bg=BG2, fg=FG, relief="flat",
              activebackground=BG2, activeforeground=ACCENT, font=font_s).pack(side="left", padx=(0, 6),
                                                                              before=btn_prev)
    rebuild_tree_menu()
    bar_btn("Boss?", lambda: show_boss_check())

    # --- PRICE CHECK: Ctrl+C no item dentro do jogo ---
    cfg.setdefault("price_check", True)
    pdb = PriceDB(cfg.get("league"))
    pc = {"last": None, "pop": None, "job": None}
    pc_var = tk.BooleanVar(value=cfg["price_check"])

    def on_pc_toggle():
        cfg["price_check"] = pc_var.get()
        save_config(cfg)
        show_warning("Price check " + ("LIGADO: passe o mouse no item e aperte Ctrl+C." if pc_var.get()
                                       else "desligado."))

    cfg.setdefault("compare_on", True)
    cmp_var = tk.BooleanVar(value=cfg["compare_on"])

    def on_cmp_toggle():
        cfg["compare_on"] = cmp_var.get()
        save_config(cfg)

    # Seletor de atalhos. O jogo só copia itens com Ctrl+C (normal) ou Ctrl+Alt+C (avançado);
    # o programa não aperta teclas no jogo, então a escolha é o que cada cópia abre.
    SHORTCUT_MODES = [
        ("padrao", "Ctrl+C = preço  •  Ctrl+Alt+C = comparar"),
        ("invertido", "Ctrl+C = comparar  •  Ctrl+Alt+C = preço"),
        ("juntos", "Ctrl+C = preço + comparar juntos"),
        ("so_preco", "Só preço (Ctrl+C ou Ctrl+Alt+C)"),
        ("so_comparar", "Só comparar (Ctrl+C ou Ctrl+Alt+C)"),
        ("off", "Desligado (não abre nada ao copiar)"),
    ]
    if "shortcut_mode" not in cfg:
        p_on, c_on = cfg.get("price_check", True), cfg.get("compare_on", True)
        cfg["shortcut_mode"] = ("padrao" if p_on and c_on else "so_preco" if p_on
                                else "so_comparar" if c_on else "off")
    label_by_mode = dict(SHORTCUT_MODES)
    mode_by_label = {v: k for k, v in SHORTCUT_MODES}
    sc_var = tk.StringVar(value=label_by_mode.get(cfg["shortcut_mode"], SHORTCUT_MODES[0][1]))

    def on_shortcut(choice):
        cfg["shortcut_mode"] = mode_by_label.get(choice, "padrao")
        save_config(cfg)
        show_warning("Atalhos: " + choice)

    sc_row = tk.Frame(sec_cfg, bg=BG)
    sc_row.pack(fill="x", pady=(2, 0))
    tk.Label(sc_row, text="⌨ Atalhos (mouse no item):", bg=BG, fg=MUTED, font=font_s).pack(side="left")
    sc_menu = tk.OptionMenu(sc_row, sc_var, *[lbl for _, lbl in SHORTCUT_MODES], command=on_shortcut)
    sc_menu.config(bg=BG2, fg=FG, activebackground=BG2, activeforeground=ACCENT, relief="flat",
                   highlightthickness=0, font=font_s)
    sc_menu["menu"].config(bg=BG2, fg=FG, activebackground=ACCENT, activeforeground="#0b0c0f", font=font_s)
    sc_menu.pack(side="left", padx=(6, 0), fill="x", expand=True)

    # mesmo seletor no modo barra: botão "⌨" abre a lista de opções
    bar_sc_menu = tk.Menu(root, tearoff=0, bg=BG2, fg=FG, activebackground=ACCENT, activeforeground="#0b0c0f",
                          font=font_s)
    bar_sc_menu.add_command(label="Atalhos (mouse no item no jogo):", state="disabled")
    for _k, _lbl in SHORTCUT_MODES:
        bar_sc_menu.add_radiobutton(label=_lbl, value=_lbl, variable=sc_var,
                                    command=lambda l=_lbl: on_shortcut(l))
    bar_sc_menu.add_separator()
    bar_sc_menu.add_command(label="Teclas próprias (o programa copia o item para você):", state="disabled")

    def open_bar_shortcuts():
        b = BAR.get("Atalhos")
        try:
            x, y = b.winfo_rootx(), b.winfo_rooty()
            h = bar_sc_menu.yposition("end") + 30
            bar_sc_menu.tk_popup(x, max(0, y - h))   # abre para cima (a barra fica embaixo da tela)
        finally:
            bar_sc_menu.grab_release()
    bar_btn("Atalhos", open_bar_shortcuts)

    def close_price():
        if pc["pop"] is not None:
            try:
                pc["pop"].destroy()
            except Exception:
                pass
            pc["pop"] = None

    RARITY_COLORS = {"Unique": "#af6025", "Rare": "#ffff77", "Magic": "#8888ff", "Gem": "#1ba29b",
                     "Currency": "#aa9e82", "Divination Card": "#c8dcff", "Normal": "#c8c8c8"}

    def show_price(it):
        close_price()
        pop = tk.Toplevel(root)
        pop.overrideredirect(True)
        pop.attributes("-topmost", True)
        pop.configure(bg=BG2, highlightthickness=2, highlightbackground="#3a3f4a")
        col = RARITY_COLORS.get(it["rarity"], FG)
        title = it["name"] + (f" ×{it['stack']}" if it["stack"] > 1 else "")
        tk.Label(pop, text=title, bg=BG2, fg=col, font=("Segoe UI", 11, "bold"), anchor="w").pack(
            fill="x", padx=10, pady=(8, 0))
        if it["rarity"] in ("Unique", "Rare") and it["base"] != it["name"]:
            tk.Label(pop, text=it["base"], bg=BG2, fg=MUTED, font=font_s, anchor="w").pack(fill="x", padx=10)
        lbl_p = tk.Label(pop, text="Consultando o poe.ninja...", bg=BG2, fg=FG, font=("Segoe UI", 14, "bold"),
                         anchor="w")
        lbl_p.pack(fill="x", padx=10, pady=(4, 0))
        lbl_d = tk.Label(pop, text="", bg=BG2, fg=MUTED, font=font_s, anchor="w", justify="left", wraplength=340)
        lbl_d.pack(fill="x", padx=10)

        btns = tk.Frame(pop, bg=BG2)
        btns.pack(fill="x", padx=10, pady=(6, 8))
        tk.Button(btns, text="Fechar", command=close_price, bg=BG, fg=FG, relief="flat", font=font_s).pack(
            side="right")
        pc["pop"] = pop

        def place():
            pop.update_idletasks()
            try:
                mx, my = root.winfo_pointerxy()
            except Exception:
                mx, my = 200, 200
            sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
            w_, h_ = pop.winfo_reqwidth(), pop.winfo_reqheight()
            x = min(max(0, mx + 24), sw - w_ - 4)
            y = min(max(0, my - h_ // 2), sh - h_ - 40)
            pop.geometry(f"+{x}+{y}")
        place()
        if cfg.get("no_focus", True):
            pop.after(80, lambda: set_no_activate(pop, True))
        res = {}

        def worker():
            try:
                r = price_item(pdb, it)
                r["div"] = pdb.divine()
                r["league"] = pdb.get_league()
                res["r"] = r
            except Exception as ex:
                res["e"] = str(ex)
        threading.Thread(target=worker, daemon=True).start()

        def wait():
            if pc["pop"] is not pop:
                return
            if "r" in res:
                r = res["r"]
                if r["price"] is not None:
                    lbl_p.config(text="≈ " + fmt_chaos(r["price"], r["div"]) + (" cada" if r["total"] else ""),
                                 fg=ACCENT)
                    det = []
                    if r["total"]:
                        det.append(f"Total da pilha: {fmt_chaos(r['total'], r['div'])}")
                    if r["detail"]:
                        det.append(r["detail"])
                    det.append(f"poe.ninja • liga {r['league']}")
                    lbl_d.config(text="\n".join(det))
                else:
                    lbl_p.config(text="Sem preço direto", fg=WARN_FG)
                    lbl_d.config(text=r["detail"] + f"\npoe.ninja • liga {r['league']}")
                if it["rarity"] == "Unique":
                    tk.Button(btns, text="Ver anúncios", bg=ACCENT, fg="#0b0c0f", relief="flat", font=font_s,
                              command=lambda: (close_price(), open_advanced(it, pc.get("text", "")))).pack(side="left")
                elif r["trade"] or r["price"] is not None:
                    tk.Button(btns, text="Abrir no trade", bg=ACCENT, fg="#0b0c0f", relief="flat", font=font_s,
                              command=lambda: webbrowser.open(trade_url(r["league"], it))).pack(side="left")
                place()
                if pc["job"]:
                    root.after_cancel(pc["job"])
                pc["job"] = root.after(12000, close_price)
            elif "e" in res:
                lbl_p.config(text="Não consegui consultar", fg="#ff7b7b")
                lbl_d.config(text=f"Sem internet ou poe.ninja fora do ar ({res['e'][:80]}).")
                place()
            else:
                root.after(200, wait)
        root.after(200, wait)

    equip_cache = {"t": 0.0, "data": None, "char": None}

    def fill_compare(frame, it, text, wnd):
        """Preenche um quadro com a comparação item copiado x item equipado (roda a busca em thread)."""
        import time
        for c in frame.winfo_children():
            c.destroy()
        cls = it["class"]
        if GUIDE["mode"] == "pconc" and cls in WEAPON_CLASSES and not (cls == "Bows" and state.level < 12):
            tk.Label(frame, text="⚖ A PConc não usa arma (só escudo). Este item não serve para você.",
                     bg=BG2, fg=WARN_FG, font=font_b, anchor="w", wraplength=440, justify="left").pack(fill="x")
            return
        slots = SLOT_BY_CLASS.get(cls)
        if not slots:
            return
        if not cfg.get("account"):
            tk.Label(frame, text="⚖ Para comparar com o seu item equipado, configure a conta (botão 'Conta PoE').",
                     bg=BG2, fg=MUTED, font=font_s, anchor="w", wraplength=440, justify="left").pack(fill="x")
            return
        lbl = tk.Label(frame, text="⚖ Comparando com o seu item equipado...", bg=BG2, fg=MUTED, font=font_s,
                       anchor="w")
        lbl.pack(fill="x")
        res = {}

        def worker():
            try:
                fresh = (time.time() - equip_cache["t"] < 60 and equip_cache["char"] == state.char)
                if not fresh:
                    equip_cache["data"] = fetch_character(cfg["account"], state.char)
                    equip_cache["t"], equip_cache["char"] = time.time(), state.char
                items, passives = equip_cache["data"]
                try:
                    model = load_tree_model(download=False)
                except Exception:
                    model = None
                res["d"] = (items, passives, model)
            except Exception as ex:
                res["e"] = str(ex)
        threading.Thread(target=worker, daemon=True).start()

        def done():
            if not frame.winfo_exists():
                return
            if "e" in res:
                lbl.config(text=f"⚖ Não consegui ler seu item equipado ({res['e'][:70]}).", fg="#ff7b7b")
                return
            if "d" not in res:
                wnd.after(250, done)
                return
            items, passives, model = res["d"]
            alira = (GUIDE["mode"] == "pconc") or guide_bandit() == "Alira"
            totals = char_res_totals(items, passives, model, state.act, alira)
            eq = {i.get("inventoryId"): i for i in items.get("items", [])}
            main = "Poisonous Concoction" if GUIDE["mode"] == "pconc" else GUIDE.get("main_skill")
            m_links = re.search(r"Sockets: (.+)", text)
            new_links = max((len(g.split("-")) for g in m_links.group(1).split()), default=0) if m_links else 0
            new = gear_stats(item_mod_lines(text), props_text=text, links=new_links, req_level=it["level"] or 0)
            best = None
            for slot in slots:
                old_item = eq.get(slot)
                old = api_item_stats(old_item) if old_item else gear_stats([], props=[])
                ml = 0
                if old_item and main:
                    for g in old_item.get("socketedItems", []) or []:
                        if main.lower() in g.get("typeLine", "").lower():
                            ml = old["links"]
                tot_wo = dict(totals)
                for k in ("fire", "cold", "lightning", "chaos"):
                    tot_wo[k] = totals[k]  # comparação é diferença; totals já inclui o item antigo
                r = compare_gear(new, old, tot_wo, slot, state.level, ml, main)
                name = (old_item.get("name") or old_item.get("typeLine", "")) if old_item else "(vazio)"
                if best is None or r[1] > best[0][1]:
                    best = (r, slot, name)
            (verdict, score, lines, warns), slot, name = best
            lbl.destroy()
            col = ACCENT if verdict.startswith("✅") else ("#ff7b7b" if verdict.startswith("❌") else WARN_FG)
            tk.Label(frame, text=verdict, bg=BG2, fg=col, font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x")
            tk.Label(frame, text=f"comparado com {SLOT_PT.get(slot, slot)}: {name}", bg=BG2, fg=MUTED,
                     font=("Segoe UI", 8), anchor="w").pack(fill="x")
            for wtxt in warns:
                tk.Label(frame, text=wtxt, bg=BG2, fg=WARN_FG, font=font_s, anchor="w", wraplength=440,
                         justify="left").pack(fill="x")
            if not lines:
                tk.Label(frame, text="Sem diferença nos atributos que a build usa.", bg=BG2, fg=MUTED,
                         font=font_s, anchor="w").pack(fill="x")
            for good, txt in lines[:9]:
                tk.Label(frame, text=("▲ " if good else "▼ ") + txt, bg=BG2, fg=ACCENT if good else "#ff7b7b",
                         font=font_s, anchor="w", wraplength=440, justify="left").pack(fill="x")
        wnd.after(250, done)

    cmpw = {"w": None, "job": None}

    def close_compare():
        if cmpw["w"] is not None:
            try:
                cmpw["w"].destroy()
            except Exception:
                pass
            cmpw["w"] = None

    def open_compare(it, text):
        """Janelinha só de comparação (Ctrl+Alt+C no item)."""
        close_compare()
        pop = tk.Toplevel(root)
        pop.overrideredirect(True)
        pop.attributes("-topmost", True)
        pop.configure(bg=BG2, highlightthickness=2, highlightbackground="#3a3f4a")
        cmpw["w"] = pop
        col = RARITY_COLORS.get(it["rarity"], FG)
        tk.Label(pop, text="⚖ " + it["name"], bg=BG2, fg=col, font=("Segoe UI", 11, "bold"), anchor="w").pack(
            fill="x", padx=10, pady=(8, 0))
        if it["base"] != it["name"]:
            tk.Label(pop, text=it["base"], bg=BG2, fg=MUTED, font=font_s, anchor="w").pack(fill="x", padx=10)
        body_c = tk.Frame(pop, bg=BG2, padx=10, pady=4)
        body_c.pack(fill="x")
        if it["class"] in SLOT_BY_CLASS or it["class"] in WEAPON_CLASSES:
            fill_compare(body_c, it, text, pop)
        else:
            tk.Label(body_c, text="Este tipo de item não tem o que comparar (não é equipamento).", bg=BG2, fg=MUTED,
                     font=font_s, anchor="w").pack(fill="x")
        b_ = tk.Frame(pop, bg=BG2)
        b_.pack(fill="x", padx=10, pady=(4, 8))

        def to_price():
            close_compare()
            if it["rarity"] in ("Rare", "Magic"):
                open_advanced(it, text)
            else:
                show_price(it)
        tk.Button(b_, text="Ver preço", command=to_price, bg=ACCENT, fg="#0b0c0f", relief="flat",
                  font=font_s).pack(side="left")
        tk.Button(b_, text="Fechar", command=close_compare, bg=BG, fg=FG, relief="flat", font=font_s).pack(
            side="right")

        anchor = {"xy": None}

        def place():
            try:
                pop.update_idletasks()
                if anchor["xy"] is None:
                    anchor["xy"] = root.winfo_pointerxy()
                mx, my = anchor["xy"]
                sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
                w_, h_ = max(pop.winfo_reqwidth(), 360), pop.winfo_reqheight()
                pop.geometry(f"+{min(max(0, mx + 24), sw - w_ - 4)}+{min(max(0, my - h_ // 2), sh - h_ - 40)}")
            except Exception:
                pass
        place()
        pop.after(700, place)      # reposiciona quando a comparação terminar de carregar
        pop.after(1800, place)
        if cfg.get("no_focus", True):
            pop.after(80, lambda: set_no_activate(pop, True))
        if cmpw["job"]:
            root.after_cancel(cmpw["job"])
        cmpw["job"] = root.after(30000, close_compare)

    adv = {"w": None, "stats": None}

    def open_advanced(it, text):
        """Janela estilo Awakened PoE Trade: filtros dos mods + anúncios reais."""
        if adv["w"] is not None:
            try:
                adv["w"].destroy()
            except Exception:
                pass
        w = tk.Toplevel(root)
        adv["w"] = w
        w.title("Price check – trade")
        w.configure(bg=BG)
        w.attributes("-topmost", True)
        try:
            mx, my = root.winfo_pointerxy()
        except Exception:
            mx, my = 300, 200
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        W, H = 470, 640
        w.geometry(f"{W}x{H}+{min(max(0, mx + 30), sw - W - 10)}+{min(max(0, my - H // 2), sh - H - 50)}")
        col = RARITY_COLORS.get(it["rarity"], FG)
        tk.Label(w, text=it["name"], bg=BG, fg=col, font=("Segoe UI", 12, "bold"), anchor="w").pack(
            fill="x", padx=10, pady=(8, 0))
        sub = [it["base"]] if it["base"] != it["name"] else []
        if it["ilvl"]:
            sub.append(f"ilvl {it['ilvl']}")
        if it["links"] >= 2:
            sub.append(f"{it['links']}-link")
        tk.Label(w, text=" • ".join(sub), bg=BG, fg=MUTED, font=font_s, anchor="w").pack(fill="x", padx=10)

        opts = tk.Frame(w, bg=BG)
        opts.pack(fill="x", padx=10, pady=(6, 0))
        use_base = tk.BooleanVar(value=True)
        tk.Checkbutton(opts, text=f"Mesma base ({it['base']})", variable=use_base, bg=BG, fg=FG, selectcolor=BG2,
                       activebackground=BG, activeforeground=ACCENT, font=font_s).pack(side="left")
        use_links = tk.BooleanVar(value=it["links"] >= 5)
        if it["links"] >= 5:
            tk.Checkbutton(opts, text=f"{it['links']}-link", variable=use_links, bg=BG, fg=FG, selectcolor=BG2,
                           activebackground=BG, activeforeground=ACCENT, font=font_s).pack(side="left", padx=8)

        tk.Label(w, text="Filtros (marque o que importa; ajuste o mínimo):", bg=BG, fg=ACCENT, font=font_b,
                 anchor="w").pack(fill="x", padx=10, pady=(8, 2))
        fbox = tk.Frame(w, bg=BG2)
        fbox.pack(fill="x", padx=10)
        status = tk.Label(w, text="Lendo os mods do item...", bg=BG, fg=MUTED, font=font_s, anchor="w",
                          justify="left", wraplength=440)
        status.pack(fill="x", padx=10, pady=(6, 0))
        btns = tk.Frame(w, bg=BG)
        btns.pack(fill="x", padx=10, pady=6)
        results = tk.Frame(w, bg=BG)
        results.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        rows = []
        state_ = {"filters": [], "league": None, "busy": False}

        def current_filters():
            out = []
            for f, var, ent in rows:
                f = dict(f)
                f["on"] = var.get()
                try:
                    f["min"] = float(ent.get().replace(",", "."))
                except ValueError:
                    pass
                out.append(f)
            return out

        def query():
            return build_trade_query(it, current_filters(), use_base=use_base.get(),
                                     min_links=it["links"] if use_links.get() else None)

        def open_site():
            import urllib.parse
            lg = state_["league"] or trade_league(pdb.get_league())
            if state_.get("last_id"):
                # abre exatamente a última busca feita aqui (mesmo resultado da janela)
                webbrowser.open(f"{TRADE}/trade/search/{urllib.parse.quote(lg)}/{state_['last_id']}")
            else:
                webbrowser.open(f"{TRADE}/trade/search/{urllib.parse.quote(lg)}?q=" +
                                urllib.parse.quote(json.dumps(query())))

        def show_results(r, rates):
            for c in results.winfo_children():
                c.destroy()
            ls = r["listings"]
            if not ls and not state_.get("relaxed") and rows:
                # 1ª busca sem resultado: afrouxa (só totais + velocidade) e tenta de novo
                state_["relaxed"] = True
                for f, var, ent in rows:
                    keep = f["id"].startswith("pseudo.") or "movement speed" in f["text"].lower()
                    var.set(bool(var.get() and keep))
                    if keep:
                        try:
                            v = float(ent.get().replace(",", "."))
                            ent.delete(0, "end")
                            ent.insert(0, f"{int(v * 0.8):g}")
                        except ValueError:
                            pass
                status.config(text="Nenhum anúncio igual; afrouxei os filtros e busquei de novo...", fg=WARN_FG)
                w.after(1500, do_search)
                return
            if not ls:
                status.config(text=f"Nenhum anúncio com esses filtros ({r['total']} no total). "
                                   "Desmarque alguns filtros ou baixe os mínimos e busque de novo.", fg=WARN_FG)
                return
            vals = []
            for l in ls:
                p = l["price"]
                c = rates.get(p.get("currency", ""), None)
                if c is not None and p.get("amount") is not None:
                    vals.append(p["amount"] * c)
            vals.sort()
            div = rates.get("divine")
            if vals:
                med = vals[len(vals) // 2]
                status.config(text=f"Mais barato: {fmt_chaos(vals[0], div)}   •   mediana dos {len(vals)}: "
                                   f"{fmt_chaos(med, div)}   •   {r['total']} anúncios no total", fg=ACCENT)
            else:
                status.config(text=f"{r['total']} anúncios", fg=ACCENT)
            for l in ls:
                p = l["price"]
                line = tk.Frame(results, bg=BG2)
                line.pack(fill="x", pady=1)
                ptxt = f"{p.get('amount', '?')} {p.get('currency', '')}"
                tk.Label(line, text=ptxt, width=11, bg=BG2, fg=WARN_FG, font=font_b, anchor="w").pack(side="left")
                tk.Label(line, text=f"ilvl {l['ilvl']} • {ago(l['indexed'])}", bg=BG2, fg=MUTED, font=font_s,
                         anchor="w").pack(side="left")

        def do_search():
            if state_["busy"]:
                return
            state_["busy"] = True
            status.config(text="Buscando no site oficial de trade...", fg=FG)
            res = {}
            q = query()

            def worker():
                try:
                    lg = trade_league(pdb.get_league())
                    state_["league"] = lg
                    res["r"], res["warn"] = trade_search_safe(lg, q)
                    res["rates"] = pdb.currency_by_id()
                except Exception as ex:
                    res["e"] = str(ex)
            threading.Thread(target=worker, daemon=True).start()

            def wait():
                if "r" in res:
                    state_["busy"] = False
                    state_["last_id"] = res["r"].get("id")
                    show_results(res["r"], res["rates"])
                    if res.get("warn"):
                        status.config(text=status.cget("text") + f"  ({res['warn']})")
                elif "e" in res:
                    state_["busy"] = False
                    status.config(text=f"Não consegui buscar: {res['e']}.", fg="#ff7b7b")
                else:
                    w.after(250, wait)
            w.after(250, wait)

        for txt, cmd, bg_ in (("🔎 Buscar", do_search, ACCENT), ("Abrir no site", open_site, BG2),
                              ("Fechar", w.destroy, BG2)):
            tk.Button(btns, text=txt, command=cmd, bg=bg_, fg="#0b0c0f" if bg_ == ACCENT else FG, relief="flat",
                      font=font_b if bg_ == ACCENT else font_s, padx=10).pack(side="left", padx=(0, 6))

        def build(stats):
            fl = build_trade_filters(text, it, stats)
            if it["rarity"] == "Unique":
                for f in fl:
                    f["on"] = False  # único: busca pelo nome; marque mods só se quiser um roll específico
            state_["filters"] = fl
            if not fl:
                tk.Label(fbox, text="Não reconheci mods neste item (busca só pela base).", bg=BG2, fg=MUTED,
                         font=font_s).pack(anchor="w", padx=6, pady=4)
            for f in fl:
                r_ = tk.Frame(fbox, bg=BG2)
                r_.pack(fill="x", pady=1)
                var = tk.BooleanVar(value=f["on"])
                tk.Checkbutton(r_, variable=var, bg=BG2, selectcolor=BG, activebackground=BG2).pack(side="left")
                ent = tk.Entry(r_, width=6, bg=BG, fg=FG, insertbackground=FG, relief="flat", font=font_s)
                ent.insert(0, f"{f['min']:g}")
                ent.pack(side="left", padx=(0, 6))
                tk.Label(r_, text=f["text"], bg=BG2, fg=FG if "pseudo" not in f["id"] else ACCENT, font=font_s,
                         anchor="w", justify="left", wraplength=360).pack(side="left", fill="x")
                rows.append((f, var, ent))
            do_search()

        res0 = {}

        def load_stats():
            try:
                if adv["stats"] is None:
                    adv["stats"] = StatIndex().load()
                try:
                    it["trade_base"] = resolve_base(it)
                except Exception:
                    pass
                res0["s"] = adv["stats"]
            except Exception as ex:
                res0["e"] = str(ex)
        threading.Thread(target=load_stats, daemon=True).start()

        def wait0():
            if "s" in res0:
                build(res0["s"])
            elif "e" in res0:
                status.config(text=f"Não consegui carregar a lista de mods do trade ({res0['e']}). "
                                   "Use 'Abrir no site'.", fg="#ff7b7b")
            else:
                w.after(200, wait0)
        w.after(200, wait0)

    def check_clipboard():
        fresh = False
        if os.name == "nt" and clip_seq() is not None:
            seq = clip_seq()
            if pc.get("seq") is None:
                pc["seq"], pc["last"] = seq, ""   # ignora o que já estava copiado ao abrir o programa
                return
            if seq == pc["seq"]:
                return
            pc["seq"] = seq
            try:
                txt = clip_text()
            except Exception as ex:
                dbg(f"erro lendo a cópia: {ex}")
                txt = None
            fresh = bool(txt)
            dbg(f"cópia nova (seq {seq}): " + (repr(txt[:40]) if txt else "sem texto"))
        else:
            try:
                txt = root.clipboard_get()
            except Exception:
                txt = None
            if pc["last"] is None:
                pc["last"] = txt or ""
                return
            fresh = bool(txt) and txt != pc["last"]
        if fresh:
            pc["last"] = txt
            if txt.startswith("Item Class:"):
                advanced = bool(re.search(r"^\{ .*(Modifier|Implicit)", txt, re.M))
                clean = clean_advanced_text(txt) if advanced else txt
                it = parse_item_text(clean)
                dbg(f"item: {it and it.get('name')} | {it and it.get('rarity')} | avançado={advanced}")
                if it and it["name"]:
                    pc["text"] = clean
                    mode = cfg.get("shortcut_mode", "padrao")
                    want_price = {"padrao": not advanced, "invertido": advanced, "juntos": True,
                                  "so_preco": True}.get(mode, False)
                    want_cmp = {"padrao": advanced, "invertido": not advanced, "juntos": True,
                                "so_comparar": True}.get(mode, False)
                    import time as _t
                    force = pc.get("force")
                    if force and _t.time() - force[1] < 3:
                        want_price, want_cmp = force[0] == "price", force[0] == "compare"
                    pc["force"] = None
                    if want_price:
                        if it["rarity"] in ("Rare", "Magic") and it["class"] not in ("Maps", "Stackable Currency"):
                            open_advanced(it, clean)
                        else:
                            show_price(it)
                    dbg(f"abrir: preço={want_price} comparar={want_cmp} (modo {mode})")
                    is_gear = it["class"] in SLOT_BY_CLASS or it["class"] in WEAPON_CLASSES
                    if want_cmp and (is_gear or not want_price):
                        open_compare(it, clean)

    def poll_clipboard():
        try:
            check_clipboard()
        except Exception:
            import sys as _s
            report_error(*_s.exc_info())
        finally:
            root.after(400, poll_clipboard)

    root.after(1000, poll_clipboard)

    # --- TEMPO JOGADO: conta enquanto você joga; para depois de 1 minuto sem mexer mouse/teclado
    #     (ou 1 minuto fora do jogo). Voltou a mexer no jogo, volta a contar na hora. ---
    IDLE_LIMIT = 60
    last_fg = {"t": 0.0}

    linux_input = {"t": None}

    def _linux_idle_watch():
        """Linux sem xprintidle: marca a hora do último mouse/teclado pelo pynput."""
        try:
            import time as _t
            from pynput import keyboard, mouse
            linux_input["t"] = _t.time()

            def touch(*_a):
                linux_input["t"] = _t.time()
            for L in (keyboard.Listener(on_press=touch), mouse.Listener(on_move=touch, on_click=touch,
                                                                         on_scroll=touch)):
                L.daemon = True
                L.start()
        except Exception:
            linux_input["t"] = None

    if not IS_WIN and not shutil.which("xprintidle") and has_pynput():
        _linux_idle_watch()

    def idle_seconds():
        if not IS_WIN:
            import time as _t
            out = None
            if shutil.which("xprintidle"):
                try:
                    out = subprocess.run(["xprintidle"], capture_output=True, text=True, timeout=2).stdout
                    return int(out.strip()) / 1000.0
                except Exception:
                    pass
            if linux_input["t"] is not None:
                return _t.time() - linux_input["t"]
            return 0.0
        try:
            import ctypes

            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
            li = LASTINPUTINFO()
            li.cbSize = ctypes.sizeof(li)
            ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li))
            now = ctypes.windll.kernel32.GetTickCount() & 0xFFFFFFFF
            return ((now - li.dwTime) & 0xFFFFFFFF) / 1000.0
        except Exception:
            return 0.0

    def tick_active():
        try:
            on = False
            if state.char:
                import time as _t
                fg, _title = poe_is_foreground()
                if fg:
                    last_fg["t"] = _t.time()
                on = (_t.time() - last_fg["t"] < IDLE_LIMIT) and idle_seconds() < IDLE_LIMIT
            if on:
                state.add_active(1)
            changed = on != active_now["on"]
            active_now["on"] = on
            active_now["n"] += 1
            if active_now["n"] % 30 == 0:
                save_config(cfg)
            if changed or on:
                update_status()
        finally:
            root.after(1000, tick_active)
    root.after(1000, tick_active)

    # --- TECLAS PRÓPRIAS: uma para preço/comprar, outra para comparar ---
    cfg.setdefault("hk_price", "Ctrl+D")
    cfg.setdefault("hk_compare", "Alt+D")
    act_q, act_holder = [], {}

    def restart_action_keys():
        dbg(f"--- iniciando teclas (sistema {os.name}) preço={cfg.get('hk_price')} comparar={cfg.get('hk_compare')}")
        if not IS_WIN and not has_pynput():
            show_warning("Linux: as teclas próprias (Ctrl+D/Alt+D) precisam do pynput e de X11. "
                         "Use Ctrl+C (preço) e Ctrl+Alt+C (comparar) no jogo.")
            return
        stop_action_hotkeys(act_holder)
        root.after(150, lambda: start_action_hotkeys({"price": cfg["hk_price"], "compare": cfg["hk_compare"]},
                                                     act_q, act_holder))

    def on_action(kind):
        ok, title = poe_is_foreground()
        dbg(f"tecla {kind} apertada | janela da frente: {title!r} | é o PoE: {ok}")
        if not ok:
            show_warning(f"Tecla recebida, mas a janela da frente não é o PoE ({title or 'sem título'}). "
                         "Clique no jogo e tente de novo.")
            return
        import time as _t
        pc["force"] = (kind, _t.time())
        if os.name != "nt" or clip_seq() is None:
            pc["last"] = ""
        try:
            send_item_copy(advanced=(kind == "compare"))
            dbg("Ctrl+C enviado ao jogo" + (" (com Alt)" if kind == "compare" else ""))
        except Exception as ex:
            dbg(f"erro ao enviar a cópia: {ex}")
            show_warning(f"Não consegui copiar o item: {ex}")
            return
        for ms in (120, 300, 600):
            root.after(ms, check_clipboard)

        def no_copy():
            if pc.get("force") and pc["force"][1] == t0:
                pc["force"] = None
                dbg("o jogo não copiou nada em 1,2 s")
                show_warning("Tecla recebida, mas o jogo não copiou nada. Deixe o mouse EM CIMA do item "
                             "(inventário ou chão). Se o PoE estiver como administrador, abra o programa "
                             "também como administrador.")
        t0 = pc["force"][1]
        root.after(1200, no_copy)

    def poll_actions():
        while act_q:
            ev, name = act_q.pop(0)
            if ev == "act":
                on_action(name)
            elif ev == "ready":
                if name:
                    show_warning(f"Teclas ativas: {cfg['hk_price']} = preço/comprar • {cfg['hk_compare']} = comparar")
            else:
                nome = {"price": "preço/comprar", "compare": "comparar"}.get(name, name)
                show_warning(f"Não consegui usar a tecla de {nome} (outro programa usa?). Escolha outra em Atalhos.")
        root.after(50, poll_actions)

    restart_action_keys()
    root.after(50, poll_actions)

    def set_action_key(which, combo):
        other = "hk_compare" if which == "hk_price" else "hk_price"
        if combo != "Desligado" and cfg.get(other) == combo:
            show_warning("Essa tecla já está na outra ação. Escolha uma diferente.")
            kvars[which].set(cfg[which])
            return
        cfg[which] = combo
        save_config(cfg)
        restart_action_keys()
        show_warning(("Preço/comprar" if which == "hk_price" else "Comparar") + f": tecla {combo}")

    kvars = {"hk_price": tk.StringVar(value=cfg["hk_price"]), "hk_compare": tk.StringVar(value=cfg["hk_compare"])}
    key_rows = []
    for which, label in (("hk_price", "💰 Tecla preço/comprar:"), ("hk_compare", "⚖ Tecla comparar:")):
        r_ = tk.Frame(sec_cfg, bg=BG)
        key_rows.append(r_)
        r_.pack(fill="x", pady=(2, 0))
        tk.Label(r_, text=label, bg=BG, fg=MUTED, font=font_s).pack(side="left")
        om = tk.OptionMenu(r_, kvars[which], *ACTION_KEYS, command=lambda c, w_=which: set_action_key(w_, c))
        om.config(bg=BG2, fg=FG, activebackground=BG2, activeforeground=ACCENT, relief="flat",
                  highlightthickness=0, font=font_s)
        om["menu"].config(bg=BG2, fg=FG, activebackground=ACCENT, activeforeground="#0b0c0f", font=font_s)
        om.pack(side="left", padx=(6, 0))
    for which, label in (("hk_price", "💰 Tecla preço/comprar"), ("hk_compare", "⚖ Tecla comparar")):
        sub = tk.Menu(bar_sc_menu, tearoff=0, bg=BG2, fg=FG, activebackground=ACCENT,
                      activeforeground="#0b0c0f", font=font_s)
        for k in ACTION_KEYS:
            sub.add_radiobutton(label=k, value=k, variable=kvars[which],
                                command=lambda k_=k, w_=which: set_action_key(w_, k_))
        bar_sc_menu.add_cascade(label=label, menu=sub)

    # --- log ---
    def start_log():
        path = cfg.get("log_path", "")
        tail["path"] = path
        tail["pos"] = 0
        if not path or not os.path.isfile(path):
            update_status()
            show_warning("Não achei o Client.txt. Clique em 'Client.txt' e selecione o arquivo "
                         "na pasta logs do Path of Exile.")
            return
        lines, size = read_tail(path)
        for ln in lines:
            state.feed(ln, live=False)
        tail["pos"] = size
        if follow.get():
            view_act.set(state.act)
        update_status()
        render()

    def poll():
        path = tail["path"]
        try:
            if path and os.path.isfile(path):
                size = os.path.getsize(path)
                if size < tail["pos"]:
                    tail["pos"] = 0  # log foi recriado
                if size > tail["pos"]:
                    with open(path, "rb") as f:
                        f.seek(tail["pos"])
                        chunk = f.read()
                    tail["pos"] = size
                    prev_act, prev_lvl, prev_zone = state.act, state.level, state.zone
                    for ln in chunk.decode("utf-8", errors="ignore").splitlines():
                        state.feed(ln, live=True)
                    if state.act != prev_act:
                        cfg["tree_manual"] = False  # novo ato: volta a sugerir a árvore
                    if state.zone != prev_zone and (state.zone, state.act) in BOSSES:
                        show_boss_check(auto=True)
                    for msg in state.events:
                        show_warning(msg)
                    state.events.clear()
                    save_config(cfg)  # guarda tempos/mortes
                    if follow.get() and (state.act != view_act.get() or state.level != prev_lvl):
                        view_act.set(state.act)
                        render()
                    elif state.act != prev_act or state.zone != prev_zone:
                        render()
                    update_status()
        except Exception:
            pass
        root.after(700, poll)

    def on_close():
        if cfg.get("mode") != "bar":
            cfg["geometry"] = root.geometry()
        cfg["act"] = state.act
        cfg["follow"] = follow.get()
        save_config(cfg)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    # --- fechar junto com o jogo (configurável) ---
    game_watch = {"seen": False, "gone": 0}

    def watch_game():
        try:
            run = poe_running()
            if run:
                game_watch["seen"], game_watch["gone"] = True, 0
            elif run is False and game_watch["seen"] and cfg.get("close_with_game", True):
                game_watch["gone"] += 1
                if game_watch["gone"] >= 3:          # ~9 s sem o jogo (evita fechar numa troca de resolução)
                    dbg("jogo fechado: fechando o FL PoE Helper junto")
                    on_close()
                    return
        except Exception:
            pass
        root.after(3000, watch_game)
    root.after(3000, watch_game)

    apply_compact()
    start_log()
    render()
    update_status()
    root.after(700, poll)
    root.after(300, lambda: set_no_activate(root, no_focus.get()))
    if cfg.get("mode") == "bar":
        root.after(400, enter_bar)
    if "guide_mode" not in cfg or cfg.get("home_on_start", True):
        root.after(700, open_home)

    # tecla global para mostrar/esconder (Windows)
    hk_q = []
    hidden = {"v": False}

    def toggle_visible():
        win = bar if cfg.get("mode") == "bar" else root
        if hidden["v"]:
            win.deiconify()
            hidden["v"] = False
            if cfg.get("no_focus", True):
                win.after(100, lambda: set_no_activate(win, True))
        else:
            for p in (gems_pop, regex_pop):
                if p["w"] is not None:
                    p["w"].destroy()
                    p["w"] = None
            win.withdraw()
            hidden["v"] = True

    def poll_hotkey():
        while hk_q:
            ev = hk_q.pop(0)
            if ev == "toggle":
                toggle_visible()
            elif ev == "fail":
                show_warning(f"Não consegui registrar a tecla {cfg['hotkey']} (outro programa usa?). "
                             "Escolha outra em 'Tecla mostrar/esconder'.")
        root.after(100, poll_hotkey)

    vk = HOTKEYS.get(cfg.get("hotkey"))
    if vk and IS_WIN:
        start_hotkey_thread(vk, hk_q)
    elif not IS_WIN and has_pynput() and cfg.get("hotkey"):
        class _HkQ:
            def append(self, item):
                if item[0] == "act":
                    hk_q.append("toggle")
                elif item[0] == "fail":
                    hk_q.append("fail")
        start_linux_hotkeys({"toggle": cfg["hotkey"]}, _HkQ(), {})
    root.after(100, poll_hotkey)

    # --- ordem final dos botões (do mais usado para o menos usado) ---

    # --- 🤖 PERGUNTAR AO CLAUDE ---
    ask_win = {"w": None, "hist": []}

    def get_char_data(cb):
        """Busca itens/passivas (se a conta estiver configurada) e chama cb(items, passives, model)."""
        import time
        if not cfg.get("account"):
            cb(None, None, None)
            return
        res = {}

        def worker():
            try:
                fresh = (time.time() - equip_cache["t"] < 60 and equip_cache["char"] == state.char)
                if not fresh:
                    equip_cache["data"] = fetch_character(cfg["account"], state.char)
                    equip_cache["t"], equip_cache["char"] = time.time(), state.char
                try:
                    model = load_tree_model(download=False)
                except Exception:
                    model = None
                res["d"] = (*equip_cache["data"], model)
            except Exception as ex:
                res["e"] = str(ex)
        threading.Thread(target=worker, daemon=True).start()

        def wait():
            if "d" in res:
                cb(*res["d"])
            elif "e" in res:
                dbg(f"perguntar: não li o personagem ({res['e']})")
                cb(None, None, None)
            else:
                root.after(200, wait)
        root.after(200, wait)

    def set_claude_key():
        w = tk.Toplevel(root)
        w.title("Chave do Claude (opcional)")
        w.configure(bg=BG)
        w.attributes("-topmost", True)
        tk.Label(w, text="Resposta dentro do programa (opcional)", bg=BG, fg=ACCENT, font=font_b).pack(
            anchor="w", padx=12, pady=(10, 2))
        tk.Label(w, bg=BG, fg=FG, font=font_s, justify="left", wraplength=420, text=(
            "Sem chave o botão IA já funciona: ele abre o Claude no navegador com a sua pergunta "
            "e os dados da build prontos (é só colar com Ctrl+V).\n\n"
            "Se quiser a resposta aqui dentro, sem sair do jogo, cole uma chave de API da Anthropic "
            "(console.anthropic.com → API Keys). A API é cobrada à parte, por uso. "
            "A chave fica salva só neste computador.")).pack(anchor="w", padx=12)
        e = tk.Entry(w, width=56, show="•", bg=BG2, fg=FG, insertbackground=FG, relief="flat")
        e.insert(0, cfg.get("claude_key", ""))
        e.pack(padx=12, pady=8, fill="x")
        row = tk.Frame(w, bg=BG)
        row.pack(fill="x", padx=12, pady=(0, 10))

        def save():
            cfg["claude_key"] = e.get().strip()
            save_config(cfg)
            w.destroy()
            show_warning("Chave salva: as respostas vão aparecer dentro do programa." if cfg["claude_key"]
                         else "Sem chave: o botão IA vai abrir o Claude no navegador.")

        def clear():
            e.delete(0, "end")
            save()
        tk.Button(row, text="Salvar", command=save, bg=ACCENT, fg="#0b0c0f", relief="flat", font=font_b,
                  padx=10).pack(side="left")
        tk.Button(row, text="Remover chave", command=clear, bg=BG2, fg=FG, relief="flat", font=font_s,
                  padx=8).pack(side="left", padx=6)
        tk.Button(row, text="Abrir console.anthropic.com",
                  command=lambda: webbrowser.open("https://console.anthropic.com/settings/keys"),
                  bg=BG2, fg=FG, relief="flat", font=font_s, padx=8).pack(side="left")

    def open_ask():
        if ask_win["w"] is not None and ask_win["w"].winfo_exists():
            ask_win["w"].destroy()
            ask_win["w"] = None
            return
        w = tk.Toplevel(root)
        ask_win["w"] = w
        w.title("Perguntar à IA (Claude)")
        w.configure(bg=BG)
        w.attributes("-topmost", True)
        w.geometry("520x560")
        has_key = bool(cfg.get("claude_key"))
        tk.Label(w, text=ui_text("Pergunte à IA sobre a sua build"), bg=BG, fg=ACCENT, font=font_b).pack(
            anchor="w", padx=10, pady=(8, 0))
        mode_txt = ("Modo: resposta aqui dentro (chave configurada)" if has_key else
                    "Modo: abre o Claude no navegador com tudo pronto (é só colar com Ctrl+V)")
        tk.Label(w, text=mode_txt, bg=BG, fg=MUTED, font=font_s).pack(anchor="w", padx=10)

        qf = tk.Frame(w, bg=BG)
        qf.pack(fill="x", padx=10, pady=(6, 2))
        tk.Label(qf, text="Perguntas rápidas:", bg=BG, fg=MUTED, font=font_s).pack(anchor="w")
        txt = tk.Text(w, height=3, wrap="word", bg=BG2, fg=FG, insertbackground=FG, relief="flat", font=font_s)
        for q in QUICK_QUESTIONS:
            tk.Button(qf, text=q, anchor="w", bg=BG2, fg=FG, relief="flat", font=font_s, padx=6,
                      activebackground="#2a2f3a", activeforeground=ACCENT,
                      command=lambda q_=q: (txt.delete("1.0", "end"), txt.insert("1.0", q_), send())
                      ).pack(fill="x", pady=1)
        tk.Label(w, text="Ou escreva a sua pergunta:", bg=BG, fg=MUTED, font=font_s).pack(anchor="w", padx=10,
                                                                                         pady=(6, 0))
        txt.pack(fill="x", padx=10)
        inc = tk.BooleanVar(value=True)
        opt = tk.Frame(w, bg=BG)
        opt.pack(fill="x", padx=10, pady=4)
        tk.Checkbutton(opt, text="Mandar junto os dados do meu personagem", variable=inc, bg=BG, fg=FG,
                       selectcolor=BG2, activebackground=BG, font=font_s).pack(side="left")
        btn = tk.Button(opt, text="Perguntar ➤", bg=ACCENT, fg="#0b0c0f", relief="flat", font=font_b, padx=10)
        btn.pack(side="right")
        out = tk.Text(w, wrap="word", bg="#0b0c0f", fg=FG, relief="flat", font=font_s, padx=8, pady=6)
        out.pack(fill="both", expand=True, padx=10, pady=(4, 4))
        bottom = tk.Frame(w, bg=BG)
        bottom.pack(fill="x", padx=10, pady=(0, 8))
        tk.Button(bottom, text=ui_text("⚙ Chave (opcional)"), command=set_claude_key, bg=BG2, fg=MUTED, relief="flat",
                  font=font_s).pack(side="left")
        tk.Button(bottom, text="Nova conversa", bg=BG2, fg=MUTED, relief="flat", font=font_s,
                  command=lambda: (ask_win.__setitem__("hist", []), out.delete("1.0", "end"))).pack(side="left",
                                                                                                   padx=6)

        def show(t, color=FG):
            out.config(state="normal")
            out.insert("end", t + "\n\n")
            out.see("end")

        if not has_key:
            show("Como funciona: escolha uma pergunta rápida ou escreva a sua e clique em Perguntar.\n"
                 "O programa copia a pergunta + os dados da sua build e abre o Claude no navegador. "
                 "Lá, aperte Ctrl+V e Enter.")

        def send():
            q = txt.get("1.0", "end").strip()
            if not q:
                show("Escreva uma pergunta ou clique numa pergunta rápida.")
                return
            btn.config(state="disabled", text="Pensando...")

            def go(items, passives, model):
                ctx = build_context_text(state, items, passives, model) if inc.get() else "(não enviado)"
                if inc.get() and items is None:
                    ctx += ("\n(Itens não incluídos: configure a 'Conta PoE' e deixe os personagens públicos "
                            "para eu ver seu equipamento.)")
                if cfg.get("claude_key"):
                    res = {}

                    def worker():
                        try:
                            res["a"], ask_win["hist"] = ask_claude_api(cfg["claude_key"], q, ctx, ask_win["hist"])
                        except Exception as ex:
                            res["e"] = str(ex)
                    threading.Thread(target=worker, daemon=True).start()
                    show("Você: " + q)

                    def wait():
                        if not w.winfo_exists():
                            return
                        if "a" in res or "e" in res:
                            btn.config(state="normal", text="Perguntar ➤")
                            show(("Claude: " + res["a"]) if "a" in res else ("⚠ Não deu certo: " + res["e"]))
                            txt.delete("1.0", "end")
                        else:
                            w.after(300, wait)
                    w.after(300, wait)
                else:
                    prompt = (f"{CLAUDE_SYSTEM}\n\nDados do meu personagem agora:\n{ctx}\n\nPergunta: {q}")
                    try:
                        root.clipboard_clear()
                        root.clipboard_append(prompt)
                        root.update()
                    except Exception:
                        pass
                    webbrowser.open("https://claude.ai/new")
                    btn.config(state="normal", text="Perguntar ➤")
                    show("✅ Pergunta copiada e Claude aberto no navegador.\n"
                         "Lá, clique na caixa de mensagem, aperte Ctrl+V e depois Enter.")
            get_char_data(go)
        btn.config(command=send)
        txt.bind("<Return>", lambda e: (send(), "break")[1])
        txt.focus_set()

    mk_btn(row_game, "Perguntar à IA", open_ask)
    bar_btn("IA", open_ask)
    mk_btn(row_game, "💰 Divines", open_farm_tips)
    bar_btn("💰", open_farm_tips)
    mk_btn(cfg_a, "Chave do Claude", set_claude_key)

    def arrange(reg, order, **pk):
        for name in order:
            b = reg.get(name)
            if b is not None:
                b.pack_forget()
                b.pack(**pk)

    # ===== ORDEM DOS MENUS =====
    # Regra: do que se usa a cada minuto jogando -> o que se usa uma vez por sessão -> configurações.
    # Ações que apagam coisas ficam por último no grupo. Controles da janela (⤢ ✕) sempre na ponta direita.
    arrange(BTN, ["Modo barra (perto da XP)", "Checar chefe", "Perguntar à IA", "💰 Divines", "Regex"],
            side="left", padx=(0, 4), pady=2)
    arrange(BTN, ["Ver/fechar árvore", "Site"], side="left", padx=(0, 4), pady=2)
    arrange(BTN, ["🏠 Início", "Abrir guia", "Novo personagem", "Zerar checklist"], side="left", padx=(0, 4), pady=2)

    # Configurações em 4 grupos: Conta -> Teclas -> Janela -> Sistema
    def cfg_group(title):
        g = tk.Frame(cfg_a, bg=BG)
        g.pack(fill="x", pady=(4, 0))
        tk.Label(g, text=title, bg=BG, fg=MUTED, font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x")
        r_ = tk.Frame(g, bg=BG)
        r_.pack(fill="x")
        return g, r_

    g_acc, r_acc = cfg_group("CONTA E JOGO")
    for name in ("Conta PoE", "Client.txt", "Chave do Claude"):
        if BTN.get(name):
            BTN[name].pack_forget()
            BTN[name].pack(in_=r_acc, side="left", padx=(0, 4), pady=2)
    g_keys, _r = cfg_group("TECLAS")
    for fr in [sc_row] + key_rows + [row4]:
        fr.pack_forget()
        fr.pack(in_=g_keys, fill="x", pady=(2, 0))
    g_win, r_win = cfg_group("JANELA")
    if BTN.get("Compacto"):
        BTN["Compacto"].pack_forget()
        BTN["Compacto"].pack(in_=r_win, side="left", padx=(0, 4), pady=2)
    for fr in (row2, row5, row_cwg):
        fr.pack_forget()
        fr.pack(in_=g_win, fill="x", pady=(2, 0))
    g_sys, r_sys = cfg_group("SISTEMA")
    for name in ("Atalho na área de trabalho", "Pasta de dados"):
        if BTN.get(name):
            BTN[name].pack_forget()
            BTN[name].pack(in_=r_sys, side="left", padx=(0, 4), pady=2)

    # Barra: passo atual -> jogo (árvore, gemas, chefe, regex, IA) -> | -> Início e Atalhos -> ⤢ ✕
    if BAR.get("IA") is not None:
        sep = tk.Frame(BAR["IA"].master, bg="#3a3f4b", width=1)
        BAR["|"] = sep
    arrange(BAR, ["✓", "Árvore", "Gemas", "Boss?", "Regex", "IA", "💰", "|", "🏠 Início", "Atalhos", "⤢", "✕"],
            side="left", padx=1, pady=4, fill="y")
    if BAR.get("|") is not None:
        BAR["|"].pack_configure(padx=4, pady=8)
    if os.environ.get("FLPOE_SMOKE"):
        # Teste automático: abre uma janela por vez, cada uma no seu próprio tique do Tk.
        # Nada de root.update() aninhado nem destroy() manual: isso trava o Tk no Linux.
        def _smoke_step(i):
            steps = [("pos-campanha", None), ("farm", open_farm_tips), ("home", open_home),
                     ("ask", open_ask)]
            if i >= len(steps):
                print("SMOKE_WINDOWS_DONE", flush=True)
                return
            name, fn = steps[i]
            print("SMOKE_TRY " + name, flush=True)
            try:
                if fn is None:
                    cfg.setdefault("checks", {})
                    for k in range(2):
                        cfg["checks"][f"vs:{k}"] = True       # finge 2 Voidstones
                    view_act.set(11)                          # a aba já redesenha sozinha
                else:
                    fn()
                print("SMOKE_WIN_OK " + name, flush=True)
            except Exception as ex:
                import traceback
                smoke_err.append(f"{name}: {ex}")
                print(f"SMOKE_ERROR janela {name}\n" + traceback.format_exc(), file=sys.stderr,
                      flush=True)
            root.after(400, lambda: _smoke_step(i + 1))
        root.after(1500, lambda: _smoke_step(0))

    if os.environ.get("FLPOE_SMOKE"):
        print("SMOKE_BUILT", flush=True)
    root.mainloop()
    if os.environ.get("FLPOE_SMOKE") and smoke_err:
        sys.exit(1)


if __name__ == "__main__":
    run_app()
