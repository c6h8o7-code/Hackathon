# -*- coding: utf-8 -*-
"""
纵横填字单词游戏（完整版 · 含难度选择）
"""

import tkinter as tk
from tkinter import font as tkfont, messagebox
import random
import time

# ============================================================
# 一、中考高频 120 词
# ============================================================
WORD_BANK = [
    ("about", "关于；大约", "prep."),
    ("after", "在……之后", "prep."),
    ("again", "再一次", "adv."),
    ("always", "总是", "adv."),
    ("answer", "回答", "v."),
    ("around", "在周围", "prep."),
    ("arrive", "到达", "v."),
    ("because", "因为", "conj."),
    ("before", "在……之前", "prep."),
    ("begin", "开始", "v."),
    ("believe", "相信", "v."),
    ("between", "在……之间", "prep."),
    ("borrow", "借入", "v."),
    ("bring", "带来", "v."),
    ("build", "建造", "v."),
    ("busy", "忙碌的", "adj."),
    ("careful", "仔细的", "adj."),
    ("carry", "搬运", "v."),
    ("catch", "抓住", "v."),
    ("change", "改变", "v."),
    ("choose", "选择", "v."),
    ("clean", "干净的；打扫", "adj./v."),
    ("clear", "清楚的", "adj."),
    ("climb", "攀登", "v."),
    ("close", "关闭；近的", "v./adj."),
    ("color", "颜色", "n."),
    ("come", "来", "v."),
    ("cook", "烹饪", "v."),
    ("count", "数数", "v."),
    ("cover", "覆盖", "v."),
    ("cross", "穿过", "v."),
    ("cry", "哭", "v."),
    ("decide", "决定", "v."),
    ("develop", "发展", "v."),
    ("die", "死亡", "v."),
    ("different", "不同的", "adj."),
    ("difficult", "困难的", "adj."),
    ("discover", "发现", "v."),
    ("discuss", "讨论", "v."),
    ("draw", "画", "v."),
    ("dream", "梦想", "n./v."),
    ("dress", "穿衣；连衣裙", "v./n."),
    ("drink", "喝", "v."),
    ("drive", "驾驶", "v."),
    ("drop", "掉落", "v."),
    ("early", "早的", "adj./adv."),
    ("earth", "地球", "n."),
    ("easy", "容易的", "adj."),
    ("eat", "吃", "v."),
    ("enjoy", "享受", "v."),
    ("enough", "足够的", "adj."),
    ("enter", "进入", "v."),
    ("even", "甚至", "adv."),
    ("ever", "曾经", "adv."),
    ("every", "每个", "adj."),
    ("exam", "考试", "n."),
    ("example", "例子", "n."),
    ("excuse", "原谅；借口", "v./n."),
    ("exercise", "锻炼；练习", "n./v."),
    ("expensive", "昂贵的", "adj."),
    ("explain", "解释", "v."),
    ("face", "脸；面对", "n./v."),
    ("fact", "事实", "n."),
    ("fail", "失败", "v."),
    ("fall", "落下；秋天", "v./n."),
    ("famous", "著名的", "adj."),
    ("far", "远的", "adj."),
    ("fast", "快的", "adj./adv."),
    ("feel", "感觉", "v."),
    ("festival", "节日", "n."),
    ("few", "很少的", "adj."),
    ("fill", "填满", "v."),
    ("find", "找到", "v."),
    ("finish", "完成", "v."),
    ("fire", "火", "n."),
    ("first", "第一", "num."),
    ("fit", "适合", "v."),
    ("fix", "修理", "v."),
    ("flower", "花", "n."),
    ("fly", "飞", "v."),
    ("follow", "跟随", "v."),
    ("food", "食物", "n."),
    ("foot", "脚", "n."),
    ("forget", "忘记", "v."),
    ("free", "自由的；免费的", "adj."),
    ("fresh", "新鲜的", "adj."),
    ("friend", "朋友", "n."),
    ("front", "前面", "n."),
    ("fruit", "水果", "n."),
    ("full", "满的", "adj."),
    ("fun", "乐趣", "n."),
    ("future", "未来", "n."),
    ("game", "游戏", "n."),
    ("garden", "花园", "n."),
    ("gift", "礼物", "n."),
    ("give", "给", "v."),
    ("glad", "高兴的", "adj."),
    ("glass", "玻璃；杯子", "n."),
    ("go", "去", "v."),
    ("grow", "生长", "v."),
    ("guess", "猜测", "v."),
    ("hand", "手", "n."),
    ("happen", "发生", "v."),
    ("happy", "高兴的", "adj."),
    ("hard", "努力的；困难的", "adj."),
    ("hate", "讨厌", "v."),
    ("have", "有", "v."),
    ("head", "头", "n."),
    ("health", "健康", "n."),
    ("hear", "听到", "v."),
    ("heavy", "重的", "adj."),
    ("help", "帮助", "v."),
    ("high", "高的", "adj."),
    ("hold", "握住", "v."),
    ("holiday", "假日", "n."),
    ("home", "家", "n."),
    ("hope", "希望", "v."),
    ("hot", "热的", "adj."),
    ("hour", "小时", "n."),
    ("house", "房子", "n."),
    ("how", "怎样", "adv."),
    ("hurry", "匆忙", "v."),
    ("idea", "主意", "n."),
    ("ill", "生病的", "adj."),
    ("important", "重要的", "adj."),
    ("interest", "兴趣", "n."),
    ("job", "工作", "n."),
    ("join", "加入", "v."),
    ("joke", "笑话", "n."),
    ("keep", "保持", "v."),
    ("key", "钥匙", "n."),
    ("kind", "善良的；种类", "adj./n."),
    ("know", "知道", "v."),
    ("lake", "湖", "n."),
    ("land", "陆地", "n."),
    ("large", "大的", "adj."),
    ("last", "最后的；持续", "adj./v."),
    ("late", "迟的", "adj."),
    ("laugh", "笑", "v."),
    ("learn", "学习", "v."),
    ("leave", "离开", "v."),
]


# ============================================================
# 二、自动生成交叉关卡
# ============================================================
class CrosswordGenerator:
    def __init__(self, words, grid_size=15):
        self.words = words
        self.grid_size = grid_size

    def generate(self, word_count=5, max_attempts=80):
        best = None
        for _ in range(max_attempts):
            pool = random.sample(self.words, min(len(self.words), word_count * 6))
            pool.sort(key=lambda x: -len(x[0]))
            result = self._try_build(pool, word_count)
            if result and (best is None or len(result["words"]) > len(best["words"])):
                best = result
            if best and len(best["words"]) >= word_count:
                break
        return best

    def _try_build(self, pool, target_count):
        grid = {}
        placed = []
        first = pool[0]
        w0 = first[0]
        r0 = self.grid_size // 2
        c0 = (self.grid_size - len(w0)) // 2
        if not self._place(grid, placed, first, r0, c0, "H"):
            return None
        for word_tuple in pool[1:]:
            if len(placed) >= target_count:
                break
            self._try_place_word(grid, placed, word_tuple)
        if len(placed) < 3:
            return None
        placed, grid = self._trim(placed, grid)
        prefilled = self._pick_prefilled(placed, grid)
        return {"words": placed, "prefilled": prefilled}

    def _try_place_word(self, grid, placed, word_tuple):
        word = word_tuple[0].lower()
        candidates = []
        for (r, c), letter in list(grid.items()):
            for i, ch in enumerate(word):
                if ch != letter:
                    continue
                r2, c2 = r, c - i
                if self._can_place(grid, word, r2, c2, "H"):
                    candidates.append((self._score(grid, word, r2, c2, "H"), r2, c2, "H"))
                r2, c2 = r - i, c
                if self._can_place(grid, word, r2, c2, "V"):
                    candidates.append((self._score(grid, word, r2, c2, "V"), r2, c2, "V"))
        if not candidates:
            return False
        candidates.sort(key=lambda x: -x[0])
        _, r, c, d = candidates[0]
        self._place(grid, placed, word_tuple, r, c, d)
        return True

    def _can_place(self, grid, word, r, c, d):
        dr, dc = (0, 1) if d == "H" else (1, 0)
        end_r = r + dr * (len(word) - 1)
        end_c = c + dc * (len(word) - 1)
        if r < 0 or c < 0 or end_r >= self.grid_size or end_c >= self.grid_size:
            return False
        if (r - dr, c - dc) in grid or (end_r + dr, end_c + dc) in grid:
            return False
        for i, ch in enumerate(word):
            rr = r + dr * i
            cc = c + dc * i
            if (rr, cc) in grid:
                if grid[(rr, cc)] != ch:
                    return False
            else:
                for pr, pc in [(rr + dc, cc + dr), (rr - dc, cc - dr)]:
                    if (pr, pc) in grid:
                        return False
        return True

    def _score(self, grid, word, r, c, d):
        dr, dc = (0, 1) if d == "H" else (1, 0)
        return sum(1 for i in range(len(word)) if (r + dr * i, c + dc * i) in grid)

    def _place(self, grid, placed, word_tuple, r, c, d):
        word = word_tuple[0].lower()
        dr, dc = (0, 1) if d == "H" else (1, 0)
        for i, ch in enumerate(word):
            grid[(r + dr * i, c + dc * i)] = ch
        placed.append((word, word_tuple[1], r, c, d))
        return True

    def _trim(self, placed, grid):
        min_r = min(r for (r, c) in grid)
        min_c = min(c for (r, c) in grid)
        new_placed = [(w, m, r - min_r, c - min_c, d) for w, m, r, c, d in placed]
        new_grid = {(r - min_r, c - min_c): ch for (r, c), ch in grid.items()}
        return new_placed, new_grid

    def _pick_prefilled(self, placed, grid):
        usage = {}
        for word, _, r, c, d in placed:
            dr, dc = (0, 1) if d == "H" else (1, 0)
            for i in range(len(word)):
                key = (r + dr * i, c + dc * i)
                usage[key] = usage.get(key, 0) + 1
        cells = list(grid.keys())
        random.shuffle(cells)
        cells.sort(key=lambda k: -usage[k])
        target = max(3, int(len(cells) * random.uniform(0.25, 0.4)))
        prefilled = {}
        used_words = set()
        for key in cells:
            if len(prefilled) >= target:
                break
            for w_idx, (word, _, r, c, d) in enumerate(placed):
                dr, dc = (0, 1) if d == "H" else (1, 0)
                for i in range(len(word)):
                    if (r + dr * i, c + dc * i) == key:
                        if w_idx in used_words and usage[key] == 1:
                            continue
                        prefilled[key] = grid[key]
                        used_words.add(w_idx)
                        break
                else:
                    continue
                break
        return prefilled


# ============================================================
# 三、游戏界面
# ============================================================
class CrosswordGame:
    CANVAS_W = 1350
    CANVAS_H = 850
    CELL_FONT_SIZE = 18
    TITLE_FONT_SIZE = 22
    SPLASH_MS = 7799

    def __init__(self, root):
        self.root = root
        self.root.attributes("-fullscreen", True)
        self.root.title("纵横填字 · 中考高频词")
        self.root.geometry(f"{self.CANVAS_W}x{self.CANVAS_H}")
        self.root.configure(bg="#f8fafc")
        self.root.resizable(False, False)

        self.cells = {}
        self.state = {}
        self.words_info = []
        self.selected = None
        self.current_dir = "H"
        self.locked = False
        self.game_started = False
        self.splash = None

        self.start_time = None
        self.timer_running = False
        self.elapsed = 0
        self.using=0
        self.word_count = 6   # 默认难度：5 词

        self.generator = CrosswordGenerator(WORD_BANK, grid_size=15)

        self._build_ui()
        self._build_game()
        self._show_splash()

    # ---------------- 开场遮罩 ----------------
    def _show_splash(self):
        self.splash = tk.Frame(self.root, bg="#1e3a8a")
        self.splash.place(x=0, y=0, relwidth=1, relheight=1)

        wrap = tk.Frame(self.splash, bg="#1e3a8a")
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            wrap, text="📖 玩法说明",
            font=("微软雅黑", 34, "bold"),
            bg="#1e3a8a", fg="#ffffff"
        ).pack(pady=(0, 28))

        rules = (
            "① 点击白色空格选中它（同格再点一次可切换横/竖方向）\n\n"
            "② 用键盘直接输入字母，或点击右侧字母按钮填入\n\n"
            "③ 按 Backspace 删除当前格字母；Tab / 回车跳到下一格\n\n"
            "④ 方向键可在网格中移动光标\n\n"
            "⑤ 填完全部格子后点击【检查答案】，正确变绿、错误变红\n\n"
            "⑥ 遇到困难可用【提示一格】揭示一个字母"
        )
        tk.Label(
            wrap, text=rules,
            font=("微软雅黑", 18),
            bg="#1e3a8a", fg="#e0e7ff",
            justify="left", anchor="w"
        ).pack(pady=(0, 30))

        self.countdown_label = tk.Label(
            wrap, text="准备开始…",
            font=("微软雅黑", 18, "bold"),
            bg="#1e3a8a", fg="#fbbf24"
        )
        self.countdown_label.pack()

        self._update_countdown(7)
        self.root.after(self.SPLASH_MS, self._end_splash)

    def _update_countdown(self, seconds):
        if seconds <= 0 or self.splash is None:
            return
        self.countdown_label.config(text=f"{seconds} 秒后开始…")
        self.root.after(1000, lambda: self._update_countdown(seconds - 1))

    def _end_splash(self):
        if self.splash is not None:
            self.splash.destroy()
            self.splash = None
        self.game_started = True
        self._start_timer()
        self.root.focus_set()
        self.status_label.config(
            text="点击格子，用键盘输入字母，方向键切换单词",
            fg="#64748b"
        )

    # ---------------- UI ----------------
    def _build_ui(self):
        top = tk.Frame(self.root, bg="#f8fafc")
        top.pack(fill="x", padx=20, pady=(12, 6))

        tk.Label(
            top, text="纵横填字 · 中考高频词",
            font=("微软雅黑", self.TITLE_FONT_SIZE, "bold"),
            bg="#f8fafc", fg="#1e3a8a"
        ).pack(side="right")

        self.timer_label = tk.Label(
            top, text="⏱ 00:00", font=("Consolas", 16, "bold"),
            bg="#f8fafc", fg="#0f766e"
        )
        self.timer_label.pack(side="right")

        main_frame = tk.Frame(self.root, bg="#f8fafc")
        main_frame.pack(fill="both", expand=True, padx=20, pady=6)

        board_container = tk.Frame(main_frame, bg="#ffffff",
                                   bd=2, relief="solid", highlightthickness=0)
        board_container.pack(side="left", fill="both", expand=True)

        self.board_frame = tk.Frame(board_container, bg="#ffffff")
        self.board_frame.pack(expand=True)

        right_panel = tk.Frame(main_frame, bg="#f8fafc", width=300)
        right_panel.pack(side="right", fill="y", padx=(15, 0))
        right_panel.pack_propagate(False)

        # 提示
        self.hint_frame = tk.Frame(right_panel, bg="#ffffff",
                                   bd=1, relief="solid", highlightthickness=0)
        self.hint_frame.pack(fill="x", pady=(0, 10))

        tk.Label(
            self.hint_frame, text="📋 单词提示",
            font=("微软雅黑", 11, "bold"),
            bg="#ffffff", fg="#334155"
        ).pack(anchor="w", padx=10, pady=(8, 4))

        self.hint_label = tk.Label(
            self.hint_frame, text="",
            font=("微软雅黑", 10),
            bg="#ffffff", fg="#475569",
            justify="left", anchor="nw", wraplength=280
        )
        self.hint_label.pack(anchor="w", padx=10, pady=(0, 8))

        # 字母按钮
        letters_container = tk.Frame(right_panel, bg="#ffffff",
                                     bd=1, relief="solid", highlightthickness=0)
        letters_container.pack(fill="x", pady=(0, 10))

        tk.Label(
            letters_container, text="🔤 字母按钮",
            font=("微软雅黑", 11, "bold"),
            bg="#ffffff", fg="#334155"
        ).pack(anchor="w", padx=10, pady=(8, 4))

        self.letters_frame = tk.Frame(letters_container, bg="#ffffff")
        self.letters_frame.pack(padx=10, pady=(0, 10))

        # 操作按钮
        action = tk.Frame(right_panel, bg="#f8fafc")
        action.pack(fill="x", pady=(0, 10))

        self._mk_btn(action, "✓ 检查答案", "#16a34a", self.check_all).pack(fill="x", pady=2)
        self.idea=self._mk_btn(action, "💡 提示一格", "#f59e0b", self.hint_one)
        self.idea.pack(fill="x", pady=2)
        self._mk_btn(action, "🗑 清空", "#ef4444", self.clear_input).pack(fill="x", pady=2)
        self._mk_btn(action, "🔄 换一题", "#3b82f6", self.new_puzzle).pack(fill="x", pady=2)

        # 难度按钮
        self.diff_btn = self._mk_btn(
            action, f"🎯 难度：{self.word_count} 词",
            "#8b5cf6", self.choose_difficulty
        )
        self.diff_btn.pack(fill="x", pady=2)

        self.status_label = tk.Label(
            right_panel, text="等待开始…",
            font=("微软雅黑", 10),
            bg="#f8fafc", fg="#64748b",
            wraplength=280, justify="left"
        )
        self.status_label.pack(fill="x", pady=(5, 0))

        # 底部规则
        self.rules_frame = tk.Frame(
            self.root, bg="#f0f9ff",
            bd=1, relief="solid", highlightthickness=0
        )
        self.rules_frame.pack(fill="x", padx=20, pady=(6, 12))

        tk.Label(
            self.rules_frame, text="📖 玩法说明",
            font=("微软雅黑", 11, "bold"),
            bg="#f0f9ff", fg="#0369a1"
        ).pack(anchor="w", padx=12, pady=(8, 3))

        RULES_TEXT = (
            "① 点击白色空格选中它（同格再点一次可切换横/竖方向）；   "
            "② 用键盘直接输入字母，或点击右侧字母按钮填入；   "
            "③ 按 Backspace 删除当前格字母；Tab / 回车跳到下一格；   "
            "④ 方向键可在网格中移动光标；   "
            "⑤ 填完全部格子后点击【检查答案】，正确变绿、错误变红；   "
            "⑥ 遇到困难可用【提示一格】揭示一个字母。"
        )
        tk.Label(
            self.rules_frame, text=RULES_TEXT,
            font=("微软雅黑", 10),
            bg="#f0f9ff", fg="#334155",
            justify="left", anchor="w",
            wraplength=self.CANVAS_W - 60
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # 退出按钮
        self.quit_btn = tk.Button(
            self.root, text="退出", font=("微软雅黑", 11),
            bg="#e74c3c", fg="white", activebackground="#c0392b",
            relief="flat", padx=18, pady=5, cursor="hand2",
            command=self.root.destroy
        )
        self.quit_btn.place(relx=0.0, rely=0.0, anchor="nw", x=20, y=18)

        self.root.bind("<Key>", self.on_key)

    def _mk_btn(self, parent, text, color, cmd):
        return tk.Button(
            parent, text=text, font=("微软雅黑", 11),
            bg=color, fg="white", activebackground=color,
            relief="flat", padx=10, pady=6, cursor="hand2",
            command=cmd
        )

    # ---------------- 计时 ----------------
    def _start_timer(self):
        self.elapsed = 0
        self.start_time = time.time()
        self.timer_running = True
        self._update_timer()

    def _update_timer(self):
        if not self.timer_running:
            return
        self.elapsed = int(time.time() - self.start_time)
        m, s = divmod(self.elapsed, 60)
        self.timer_label.config(text=f"⏱ {m:02d}:{s:02d}")
        self.root.after(1000, self._update_timer)

    # ---------------- 难度选择 ----------------
    def choose_difficulty(self):
        if not self.game_started:
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("选择难度")
        dlg.configure(bg="#f8fafc")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        self.root.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 360) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 280) // 2
        dlg.geometry(f"360x280+{x}+{y}")

        tk.Label(
            dlg, text="请选择每关单词数量",
            font=("微软雅黑", 16, "bold"),
            bg="#f8fafc", fg="#1e3a8a"
        ).pack(pady=(20, 6))

        tk.Label(
            dlg, text="数字越大，交叉越复杂",
            font=("微软雅黑", 10),
            bg="#f8fafc", fg="#64748b"
        ).pack(pady=(0, 16))

        btn_frame = tk.Frame(dlg, bg="#f8fafc")
        btn_frame.pack(pady=6)

        def pick(n):
            self.word_count = n
            self.diff_btn.config(text=f"🎯 难度：{n} 词")
            dlg.destroy()
            self.new_puzzle()

        for n, color in [(5, "#22c55e"), (6, "#f59e0b"), (7, "#ef4444"), (8, "#f52323"), (9, "#ff0000")]:
            tk.Button(
                btn_frame, text=f"{n} 词", font=("微软雅黑", 14, "bold"),
                bg=color, fg="white", activebackground=color,
                relief="flat", width=6, pady=14, cursor="hand2",
                command=lambda x=n: pick(x)
            ).pack(side="left", padx=6)

        tk.Button(
            dlg, text="取消", font=("微软雅黑", 11),
            bg="#cbd5e1", fg="#1e293b", activebackground="#94a3b8",
            relief="flat", padx=20, pady=5, cursor="hand2",
            command=dlg.destroy
        ).pack(pady=(16, 0))

    # ---------------- 生成题目 ----------------
    def _build_game(self):
        puzzle = self.generator.generate(word_count=self.word_count)
        if not puzzle:
            messagebox.showerror("错误", "关卡生成失败，请再试一次")
            return
        self.using=0
        self.idea.config(state=tk.NORMAL)
        self.words_info = puzzle["words"]
        prefilled = puzzle["prefilled"]

        max_r = max(r + (len(w) if d == "V" else 0)
                    for w, _, r, c, d in self.words_info)
        max_c = max(c + (len(w) if d == "H" else 0)
                    for w, _, r, c, d in self.words_info)

        solution = {}
        cell_words = {}
        for idx, (w, m, r, c, d) in enumerate(self.words_info):
            dr, dc = (0, 1) if d == "H" else (1, 0)
            for i, ch in enumerate(w):
                key = (r + dr * i, c + dc * i)
                solution[key] = ch
                cell_words.setdefault(key, []).append((idx, d))

        for widget in self.board_frame.winfo_children():
            widget.destroy()
        self.cells.clear()
        self.state.clear()
        self.selected = None
        self.current_dir = "H"
        self.locked = False

        f = tkfont.Font(family="Arial", size=self.CELL_FONT_SIZE, weight="bold")
        small_f = tkfont.Font(family="Arial", size=8)

        for r in range(max_r):
            for c in range(max_c):
                key = (r, c)
                if key not in solution:
                    tk.Label(self.board_frame, text="", width=3, height=1,
                             bg="#ffffff").grid(row=r, column=c, padx=1, pady=1)
                    continue

                prefilled_letter = prefilled.get(key, "")
                is_prefilled = key in prefilled

                holder = tk.Frame(self.board_frame, bg="#ffffff")
                holder.grid(row=r, column=c, padx=1, pady=1)

                lbl = tk.Label(
                    holder, text=prefilled_letter,
                    font=f, width=3, height=1,
                    bg="#dbeafe" if is_prefilled else "#ffffff",
                    fg="#1e3a8a" if is_prefilled else "#0f172a",
                    relief="solid", bd=2, cursor="hand2"
                )
                lbl.pack()

                start_idx = None
                for idx, (w, m, rr, cc, d) in enumerate(self.words_info):
                    if (rr, cc) == key:
                        start_idx = idx + 1
                        break
                if start_idx:
                    num = tk.Label(
                        holder, text=str(start_idx),
                        font=small_f, bg="#ffffff", fg="#64748b"
                    )
                    num.place(x=2, y=1)

                lbl.bind("<Button-1>", lambda e, k=key: self.on_cell_click(k))

                self.cells[key] = lbl
                self.state[key] = {
                    "letter": prefilled_letter,
                    "prefilled": is_prefilled,
                    "solution": solution[key],
                    "words": cell_words[key],
                }

        self._build_letter_buttons(solution)

        lines = []
        for idx, (w, m, r, c, d) in enumerate(self.words_info):
            arrow = "→" if d == "H" else "↓"
            lines.append(f"{idx+1}. {arrow} {m}（{len(w)} 字母）")
        self.hint_label.config(text="\n".join(lines))

    def _build_letter_buttons(self, solution):
        for w in self.letters_frame.winfo_children():
            w.destroy()

        needed = sorted(set(solution.values()))
        alphabet = list("abcdefghijklmnopqrstuvwxyz")
        extra = [ch for ch in alphabet if ch not in needed]
        random.shuffle(extra)

        letters = list(needed) + extra[:max(4, 8 - len(needed))]
        random.shuffle(letters)

        cols = 6
        for i, ch in enumerate(letters):
            b = tk.Button(
                self.letters_frame, text=ch.upper(),
                font=("Arial", 13, "bold"),
                width=2, height=1,
                bg="#ffffff", fg="#1e3a8a",
                activebackground="#bfdbfe",
                relief="ridge", bd=2, cursor="hand2",
                command=lambda x=ch: self.fill_letter(x)
            )
            b.grid(row=i // cols, column=i % cols, padx=3, pady=3)

    # ---------------- 交互 ----------------
    def on_cell_click(self, key):
        if not self.game_started:
            return
        if key not in self.state or self.state[key]["prefilled"]:
            return
        if self.selected == key:
            self.current_dir = "V" if self.current_dir == "H" else "H"
        self.selected = key
        self._refresh_highlight()

    def _refresh_highlight(self):
        for k, lbl in self.cells.items():
            st = self.state[k]
            base = "#dbeafe" if st["prefilled"] else "#ffffff"
            lbl.config(bg=base, fg="#1e3a8a" if st["prefilled"] else "#0f172a")

        if self.selected is None:
            return

        cur_word = None
        for idx, d in self.state[self.selected]["words"]:
            if d == self.current_dir:
                cur_word = idx
                break
        if cur_word is None:
            cur_word = self.state[self.selected]["words"][0][0]
            self.current_dir = self.state[self.selected]["words"][0][1]

        w, m, r, c, d = self.words_info[cur_word]
        dr, dc = (0, 1) if d == "H" else (1, 0)
        for i in range(len(w)):
            k = (r + dr * i, c + dc * i)
            if k in self.cells:
                self.cells[k].config(bg="#fef08a")

        self.cells[self.selected].config(bg="#fbbf24")

        arrow = "→" if d == "H" else "↓"
        self.status_label.config(
            text=f"{arrow} {m}（{len(w)} 个字母）",
            fg="#1e3a8a"
        )

    def fill_letter(self, ch):
        if not self.game_started or self.locked:
            return
        if self.selected is None:
            self.status_label.config(text="请先点击一个空格", fg="#f59e0b")
            return
        st = self.state[self.selected]
        if st["prefilled"]:
            return
        st["letter"] = ch
        self.cells[self.selected].config(text=ch, fg="#0f172a")
        self._refresh_highlight()

    def on_key(self, event):
        if not self.game_started or self.locked or self.selected is None:
            return
        ch = event.char
        key = event.keysym

        if ch and ch.isalpha() and len(ch) == 1:
            self.fill_letter(ch.lower())
        elif key == "BackSpace":
            st = self.state[self.selected]
            if not st["prefilled"]:
                st["letter"] = ""
                self.cells[self.selected].config(text="")
        elif key in ("Left", "Right", "Up", "Down"):
            self._move_arrow(key)
        elif key in ("Tab", "Return"):
            self._move_next()

    def _move_next(self):
        keys = sorted(self.cells.keys())
        if self.selected not in keys:
            return
        idx = keys.index(self.selected)
        for k in keys[idx+1:]:
            if not self.state[k]["prefilled"]:
                self.selected = k
                self._refresh_highlight()
                return

    def _move_arrow(self, key):
        dr, dc = {"Up": (-1, 0), "Down": (1, 0),
                  "Left": (0, -1), "Right": (0, 1)}[key]
        r, c = self.selected
        for step in range(1, 25):
            nr, nc = r + dr * step, c + dc * step
            if (nr, nc) in self.cells and not self.state[(nr, nc)]["prefilled"]:
                self.selected = (nr, nc)
                self._refresh_highlight()
                return

    # ---------------- 检查 ----------------
    def check_all(self):
        if not self.game_started:
            return
        all_filled = True
        all_correct = True
        for k, st in self.state.items():
            if st["prefilled"]:
                continue
            if not st["letter"]:
                all_filled = False
                continue
            if st["letter"].lower() != st["solution"].lower():
                all_correct = False
                self.cells[k].config(bg="#fecaca", fg="#b91c1c")
            else:
                self.cells[k].config(bg="#bbf7d0", fg="#166534")

        if not all_filled:
            self.status_label.config(text="还有空格没填", fg="#f59e0b")
            return

        if all_correct:
            self.timer_running = False
            m, s = divmod(self.elapsed, 60)
            self.status_label.config(
                text=f"🎉 全部正确！用时 {m:02d}:{s:02d}",
                fg="#16a34a"
            )
            self.locked = True
        else:
            self.status_label.config(text="有错误，红色格子需要修改", fg="#ef4444")

    MAX_HINTS = 2      # 每关最多提示次数（用户要求：填字只能两次提示）

    def hint_one(self):
        if not self.game_started:
            return
        if self.using >= self.MAX_HINTS:
            self.status_label.config(
                text=f"提示次数已用完（{self.MAX_HINTS}/{self.MAX_HINTS}）",
                fg="#ef4444")
            self.idea.config(state=tk.DISABLED)
            return
        empties = [k for k, st in self.state.items()
                   if not st["prefilled"] and not st["letter"]]
        if not empties:
            empties = [k for k, st in self.state.items()
                       if not st["prefilled"] and st["letter"] != st["solution"]]
        if not empties:
            self.status_label.config(text="已经全部填对啦", fg="#16a34a")
            return
        k = random.choice(empties)
        st = self.state[k]
        st["letter"] = st["solution"]
        self.cells[k].config(text=st["solution"], fg="#f59e0b")
        self.using += 1
        remain = self.MAX_HINTS - self.using
        if remain > 0:
            self.status_label.config(
                text=f"已揭示一个字母（还剩 {remain} 次提示）", fg="#f59e0b")
        else:
            self.status_label.config(
                text=f"已揭示一个字母（提示次数已用完）", fg="#ef4444")
            self.idea.config(state=tk.DISABLED)

    def clear_input(self):
        if not self.game_started:
            return
        for k, st in self.state.items():
            if st["prefilled"]:
                continue
            st["letter"] = ""
            self.cells[k].config(text="", bg="#ffffff", fg="#0f172a")
        self.status_label.config(text="已清空", fg="#64748b")
        self.locked = False

    def new_puzzle(self):
        if not self.game_started:
            return
        self._build_game()
        self._start_timer()
        self.status_label.config(
            text="点击格子，用键盘输入字母，方向键切换单词",
            fg="#64748b"
        )


# ============================================================
# 四、主函数
# ============================================================
def run():
    random.seed()
    try:
        root = tk.Tk()
        game = CrosswordGame(root)
        root.mainloop()
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("程序出错，按回车退出…")
if __name__ == "__main__":
    run()