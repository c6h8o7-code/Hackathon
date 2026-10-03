# -*- coding: utf-8 -*-
"""打开词书 —— 表格形式浏览各词库的词条，支持按中文/英文搜索。

主程序调用：
    word_book.run(banner=...)

左侧挑词库，右侧看「单元 / 单词 / 词性 / 释义 / 音标」表格，
底部可以一键打开词库文件夹（方便自己往里加 .json 词库）。

说明：本模块原先叫 word_note，现在 word_note 是「单词笔记」（艾宾浩斯复习）
程序，词书浏览改名为 word_book，两个功能各自独立。
"""

import json
import os
import pathlib
import subprocess
import sys

# 软导入：个别精简版 Python 没带 tkinter，缺了也不该让主程序起不来
try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:          # pragma: no cover
    tk = None
    ttk = None

import spell


def available():
    """tkinter 是否可用"""
    return spell.available()


# ---------------------------------------------------------------- 数据读取
def read_lib(path):
    """读一个词库文件，返回 [(单元, 单词, 词性, 释义, 音标), ...]"""
    rows = []
    try:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print("词库 %s 读取失败: %s" % (pathlib.Path(path).name, exc))
        return rows

    units = data.get("单元", []) if isinstance(data, dict) else []
    if not units and isinstance(data, list):        # 兼容纯列表格式的词库
        for item in data:
            if isinstance(item, dict):
                rows.append(("", (item.get("单词") or "").strip(),
                             (item.get("词性") or "").strip(),
                             (item.get("中文释义") or item.get("释义") or "").strip(),
                             (item.get("音标") or "").strip()))
        return rows

    for u in units:
        unit_name = (u.get("单元名称") or u.get("单元") or "").strip()
        for w in u.get("单词", []):
            rows.append((unit_name,
                         (w.get("单词") or "").strip(),
                         (w.get("词性") or "").strip(),
                         (w.get("中文释义") or w.get("释义") or "").strip(),
                         (w.get("音标") or "").strip()))
    return rows


def open_folder(path):
    """在系统文件管理器里打开词库目录"""
    path = str(path)
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)                       # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as exc:
        print("打开文件夹失败: %s" % exc)


# ---------------------------------------------------------------- 窗口
class WordBook:
    """词书窗口：左选词库，右看词条，顶部可搜索"""

    def __init__(self, root, libs):
        self.root = root
        self.libs = list(libs)
        self.rows = []                  # 当前词库的全部词条
        self.shown = []                 # 过滤后实际显示的词条

        root.title(u"十八单词 · 词书")
        root.geometry("960x620")
        root.configure(bg=spell.BG)
        spell.attach_window(root)

        cn = spell.pick_family(spell.CN_FONTS)
        self.f_text = (cn, 11)
        self.f_small = (cn, 10)

        body = tk.Frame(root, bg=spell.BG)
        body.pack(fill="both", expand=True, padx=14, pady=(8, 12))

        # ---------------- 左侧：词库列表 ----------------
        left = tk.Frame(body, bg=spell.BG)
        left.pack(side="left", fill="y")
        tk.Label(left, text=u"词库", font=self.f_small, bg=spell.BG,
                 fg=spell.TXT_GREY).pack(anchor="w")
        self.listbox = tk.Listbox(left, font=self.f_text, width=22,
                                  activestyle="none",
                                  selectbackground=spell.BTN_ACTIVE,
                                  selectforeground=spell.TXT_MAIN,
                                  highlightthickness=0, bd=0)
        self.listbox.pack(side="left", fill="y", pady=(4, 0))
        sb = tk.Scrollbar(left, command=self.listbox.yview)
        sb.pack(side="left", fill="y", pady=(4, 0))
        self.listbox.config(yscrollcommand=sb.set)
        self.listbox.bind("<<ListboxSelect>>", self.on_pick)

        for name, _path, count in self.libs:
            self.listbox.insert("end", u"%s（%d）" % (name, count))

        # ---------------- 右侧：搜索 + 表格 ----------------
        right = tk.Frame(body, bg=spell.BG)
        right.pack(side="left", fill="both", expand=True, padx=(14, 0))

        bar = tk.Frame(right, bg=spell.BG)
        bar.pack(fill="x")
        tk.Label(bar, text=u"搜索：", font=self.f_text, bg=spell.BG,
                 fg="#333333").pack(side="left")
        self.keyword = tk.StringVar()
        entry = tk.Entry(bar, textvariable=self.keyword, font=self.f_text,
                         width=28)
        entry.pack(side="left", padx=(2, 8))
        entry.bind("<KeyRelease>", lambda e: self.apply_filter())
        tk.Label(bar, text=u"（英文单词或中文释义都可以）", font=self.f_small,
                 bg=spell.BG, fg=spell.TXT_LIGHT).pack(side="left")

        self.status = tk.Label(bar, text=u"", font=self.f_small, bg=spell.BG,
                               fg=spell.TXT_GREY)
        self.status.pack(side="right")

        cols = ("unit", "word", "pos", "meaning", "phonetic")
        heads = ("单元", "单词", "词性", "释义", "音标")
        widths = (150, 130, 60, 300, 150)
        wrap = tk.Frame(right, bg=spell.BG)
        wrap.pack(fill="both", expand=True, pady=(6, 0))
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings",
                                 selectmode="browse")
        for col, head, w in zip(cols, heads, widths):
            self.tree.heading(col, text=head)
            self.tree.column(col, width=w, anchor="w",
                             stretch=(col == "meaning"))
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")
        self.tree.tag_configure("odd", background="#eaf4ff")
        self.tree.tag_configure("even", background="#ffffff")

        # ---------------- 底部 ----------------
        foot = tk.Frame(root, bg=spell.BG)
        foot.pack(fill="x", padx=14, pady=(0, 12))
        self.open_btn = tk.Button(foot, text=u"打开词库文件夹", font=self.f_text,
                                  bg="#ffffff", fg=spell.TXT_MAIN,
                                  activebackground=spell.BTN_ACTIVE,
                                  relief="ridge", bd=2, padx=16, pady=5,
                                  cursor="hand2", command=self.on_open_dir)
        self.open_btn.pack(side="left")
        tk.Label(foot, text=u"词库目录：%s" % spell.LIB_DIR, font=self.f_small,
                 bg=spell.BG, fg=spell.TXT_LIGHT).pack(side="left", padx=12)

        if self.libs:
            self.listbox.selection_set(0)
            self.show_lib(0)
        else:
            self.status.config(text=u"没有找到词库")

    # ---------------- 交互 ----------------
    def on_pick(self, _event=None):
        sel = self.listbox.curselection()
        if sel:
            self.show_lib(sel[0])

    def show_lib(self, index):
        name, path, _count = self.libs[index]
        self.rows = read_lib(path)
        self.keyword.set("")
        self.apply_filter()

    def apply_filter(self):
        kw = self.keyword.get().strip().lower()
        if kw:
            self.shown = [r for r in self.rows
                          if kw in r[1].lower() or kw in r[3].lower()]
        else:
            self.shown = list(self.rows)

        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(self.shown):
            self.tree.insert("", "end", values=row,
                             tags=("odd" if i % 2 else "even",))
        total = len(self.rows)
        if kw:
            self.status.config(text=u"%d / %d 条" % (len(self.shown), total))
        else:
            self.status.config(text=u"共 %d 条" % total)

    def on_open_dir(self):
        open_folder(spell.LIB_DIR)


# ---------------------------------------------------------------- 入口
def run(libs=None, banner=None):
    """打开词书窗口（阻塞到关窗为止）。

    libs   : [(名称, 路径, 词数), ...]；省略则扫描 dev_english 目录
    banner : 窗口顶部图标，省略则用默认图标
    """
    if libs is None:
        libs = spell.list_libs()
    spell.open_window(lambda root: WordBook(root, libs),
                      banner or spell.default_banner())


if __name__ == "__main__":
    run()
