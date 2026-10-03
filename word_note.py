# -*- coding: utf-8 -*-
"""单词笔记 —— 难词/错词本，基于艾宾浩斯遗忘曲线的复习系统。

主程序调用：
    word_note.run(banner=...)

数据文件：A.app_dir() / "review_data.json"

这份数据是全局共用的：拼写测试 / 填单词游戏 / 单词翻译测试里「连错多次单词爆炸」
会自动把那个单词加进来（标为重点复习），学习单词界面点「⭐ 加入笔记」也会加进来。
所以打开这个窗口就能看到它们，并按 1 / 2 / 4 / 7 / 15 天的间隔复习。

窗口结构（相对上传版的改动，其余逻辑一字未改）：
    - tkinter 改成软导入：精简版 Python 缺 tkinter 时主程序仍能启动
    - 页面建在 self.body 上，不再清空 root 的所有子控件（否则顶部图标会被抹掉）
    - 左上角有「退出」按钮，和其余练习窗口一致
    - run() 走 spell 的统一开窗入口：顶部图标 + 单窗口管理一致
"""

import json
from datetime import datetime, timedelta

# tkinter 是标准库，但个别精简版 Python 没带。做成软导入：缺了也不让主程序起不来。
try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except ImportError:          # pragma: no cover
    tk = None
    ttk = None
    messagebox = None

import A

# ─── 常量 ─────────────────────────────────────────────────

DATA_FILE = A.app_dir() / "review_data.json"
REVIEW_INTERVALS = [1, 2, 4, 7, 15]  # 艾宾浩斯复习间隔（天）
MAX_CORRECT = 3  # 累计正确次数达标则完成

WINDOW_TITLE = "十八单词 · 单词笔记"


def available():
    """tkinter 是否可用（主程序据此决定要不要弹提示）"""
    return tk is not None


# ─── 数据管理 ─────────────────────────────────────────────

def load_data():
    """从文件加载单词数据"""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def save_data(words):
    """保存单词数据到文件"""
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(words, f, ensure_ascii=False, indent=2)
        return True
    except OSError as exc:
        print("保存单词笔记失败: %s" % exc)
        return False


def make_word(english: str, chinese: str, note: str = "", priority: bool = False) -> dict:
    """创建新单词记录"""
    return {
        "english": english,
        "chinese": chinese,
        "note": note,
        "created_at": datetime.now().isoformat(),
        "review_stage": 0,       # 当前复习阶段索引 (0-4 对应 1/2/4/7/15天)
        "correct_count": 0,      # 累计正确次数
        "next_review": (datetime.now() + timedelta(days=1)).isoformat(),  # 首次复习: 1天后
        "priority": bool(priority),  # 是否重点复习（错词自动 True）
        "completed": False,      # 是否完成全部复习
    }


# ─── 对外 API（供其他练习模块调用：加错词 / 手动加 / 查询 / 计数） ─

def note_path():
    """笔记数据文件路径（便于其他模块校验）"""
    return DATA_FILE


def _normalize(english: str) -> str:
    """统一大小写/两端空白，避免 'Apple' 和 'apple' 被当成两个单词"""
    return (english or "").strip().lower()


def _find(words, english: str):
    key = _normalize(english)
    for idx, w in enumerate(words):
        if _normalize(w.get("english", "")) == key:
            return idx, w
    return -1, None


def contains(english: str) -> bool:
    """某个单词是否已经在笔记里（忽略大小写/两端空白）"""
    _, w = _find(load_data(), english)
    return w is not None


def count() -> int:
    """笔记里已有多少个单词"""
    return len(load_data())


def _add(english: str, chinese: str, note: str = "", priority: bool = False):
    """底层加词：已存在则仅按需升级 priority；不存在则新增并写入文件。
    返回 (是否新增, 单词记录)。"""
    english = (english or "").strip()
    chinese = (chinese or "").strip()
    if not english or not chinese:
        return False, None

    words = load_data()
    idx, existing = _find(words, english)
    if existing is not None:
        # 已存在：若中文释义比已有长（更详细）则更新；若这次要求重点复习则升级 priority
        changed = False
        if priority and not existing.get("priority", False):
            existing["priority"] = True
            changed = True
        if note and not existing.get("note"):
            existing["note"] = note
            changed = True
        if len(chinese) > len(existing.get("chinese", "")):
            existing["chinese"] = chinese
            changed = True
        if changed:
            save_data(words)
        return False, existing

    record = make_word(english, chinese, note=note, priority=priority)
    words.append(record)
    save_data(words)
    return True, record


def add_wrong(word: str, pos: str = "", meaning: str = "", ipa: str = ""):
    """爆炸触发时调用：把错词加进笔记，自动标为重点复习。
    参数顺序兼容之前 spell/explain 的调用：(word, pos, meaning, ipa)。"""
    parts = []
    if pos != "":
        parts.append(pos)
    if meaning != "":
        parts.append(meaning)
    chinese = " ".join(parts) if parts != [] else (meaning or "")
    note_parts = []
    if ipa != "":
        note_parts.append("音标: %s" % ipa)
    note_parts.append("来自：错题自动加入")
    note = "  ".join(note_parts)
    return _add(word, chinese, note=note, priority=True)


def add_manual(word: str, pos: str = "", meaning: str = "", ipa: str = ""):
    """学习界面点「⭐ 加入笔记」调用：加进笔记但不标重点。"""
    parts = []
    if pos:
        parts.append(pos)
    if meaning:
        parts.append(meaning)
    chinese = " ".join(parts) if parts else (meaning or "")
    note_parts = []
    if ipa:
        note_parts.append("音标: %s" % ipa)
    note_parts.append("来自：手动加入")
    note = "  ".join(note_parts)
    return _add(word, chinese, note=note, priority=False)


# ─── 主应用 ───────────────────────────────────────────────

class WordNotesApp:
    def __init__(self, root):  # root: tk.Tk（字符串化以兼容 tkinter 缺失时的导入）
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry("900x760")
        self.root.minsize(820, 600)
        self.root.configure(bg="#ffffff")

        # 让主程序的单窗口管理 / 顶部退出按钮能管到这个窗口
        try:
            import spell
            self._spell = spell
            spell.attach_window(root)
        except Exception:
            self._spell = None

        self.words: list = load_data()
        self.ROW_HEIGHT = 42
        self._mode = "simple"  # simple | scroll

        # 页面都建在这个 body 里：清页面时不会把窗口顶部的图标连带抹掉
        self.body = tk.Frame(root, bg="#ffffff")
        self.body.pack(fill=tk.BOTH, expand=True)

        self._build_main_page()
        self._refresh_list()

    # ─── 退出 ─────────────────────────────────────────────
    def _quit(self):
        """退出：走统一的关窗入口，没装 spell 时直接销毁本窗口"""
        spell = getattr(self, "_spell", None)
        if spell is not None:
            try:
                spell.clear_window()
                return
            except Exception:
                pass
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    # ═══════════════════════════════════════════════════════
    #  主页面 UI
    # ═══════════════════════════════════════════════════════

    def _build_main_page(self):
        # 清除旧内容（只清 body，保留窗口顶部的图标）
        for w in self.body.winfo_children():
            w.destroy()

        # ── 顶部栏 ──
        top = tk.Frame(self.body, bg="#ffffff", height=64)
        top.pack(fill=tk.X, padx=20, pady=(16, 0))
        top.pack_propagate(False)

        # 左上：退出（和其他练习窗口一致的位置）
        tk.Button(
            top, text="退出", font=("Microsoft YaHei", 11),
            bg="#e74c3c", fg="white", activebackground="#c0392b",
            relief=tk.FLAT, padx=14, pady=6, cursor="hand2",
            command=self._quit,
        ).pack(side=tk.LEFT)

        # 左上：添加单词
        tk.Button(
            top, text="＋ 添加单词", font=("Microsoft YaHei", 12, "bold"),
            bg="#4f46e5", fg="white", activebackground="#4338ca",
            relief=tk.FLAT, padx=16, pady=8, cursor="hand2",
            command=self._add_word,
        ).pack(side=tk.LEFT, padx=(10, 0))

        # 中间：标题
        tk.Label(
            top, text="单词笔记", font=("Microsoft YaHei", 24, "bold"),
            bg="#ffffff", fg="#1f2937",
        ).pack(expand=True)

        # 右上：复习巩固
        tk.Button(
            top, text="复习巩固", font=("Microsoft YaHei", 12, "bold"),
            bg="#7c3aed", fg="white", activebackground="#6d28d9",
            relief=tk.FLAT, padx=16, pady=8, cursor="hand2",
            command=self._open_review,
        ).pack(side=tk.RIGHT)

        # ── 列表区域 ──
        list_frame = tk.Frame(self.body, bg="#ffffff")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(12, 16))

        # 表头
        header = tk.Frame(list_frame, bg="#f3f4f6", height=40)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        for text, width in [("序号", 6), ("英文", 20), ("中文", 20), ("备注", 22), ("", 6)]:
            tk.Label(
                header, text=text, font=("Microsoft YaHei", 11, "bold"),
                bg="#f3f4f6", fg="#6b7280", width=width, anchor="w",
            ).pack(side=tk.LEFT, padx=6, pady=8)

        tk.Frame(list_frame, bg="#e5e7eb", height=1).pack(fill=tk.X)

        # 内容容器
        self.container = tk.Frame(list_frame, bg="#ffffff")
        self.container.pack(fill=tk.BOTH, expand=True)

        self._show_empty()

    # ─── 空状态 ───────────────────────────────────────────

    def _show_empty(self):
        for w in self.container.winfo_children():
            w.destroy()
        self._mode = "simple"
        tk.Label(
            self.container, text="暂无单词，点击「添加单词」开始吧 ✨",
            font=("Microsoft YaHei", 13), bg="#ffffff", fg="#9ca3af", pady=80,
        ).pack(fill=tk.X)

    # ─── 刷新列表 ─────────────────────────────────────────

    def _refresh_list(self):
        # 上一次若是滚动模式，先解绑全局按键、拆掉旧 canvas。
        # 否则下面的 destroy 会把 scroll_frame 一起销毁，而 self._mode 仍是
        # "scroll"，_create_row 就会往一个已经销毁的窗口里塞控件，
        # 抛 TclError 之后列表整片空白 —— 看起来就像"删掉一个词，全都没了"。
        if self._mode == "scroll":
            try:
                self._teardown_scroll()
            except Exception:
                pass

        for w in self.container.winfo_children():
            w.destroy()

        # 容器内容已清空，滚动状态一并复位，下面重新判定
        self._mode = "simple"
        self.scroll_frame = None
        self.canvas = None

        if not self.words:
            self._show_empty()
            return

        self.root.update_idletasks()
        available = self.container.winfo_height()
        need_scroll = len(self.words) * self.ROW_HEIGHT > available and available > 0

        if need_scroll:
            self._setup_scroll()

        target = self.scroll_frame if self._mode == "scroll" else self.container
        for idx, word in enumerate(self.words, start=1):
            self._create_row(target, idx, word)

    def _setup_scroll(self):
        """切换到可滚动模式（带右侧滚动条 + 鼠标滚轮 + 键盘翻页）"""
        for w in self.container.winfo_children():
            w.destroy()

        # 右侧可见滚动条
        scrollbar = tk.Scrollbar(self.container, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 画布
        self.canvas = tk.Canvas(self.container, bg="#ffffff", highlightthickness=0,
                                yscrollcommand=scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.canvas.yview)

        self.scroll_frame = tk.Frame(self.canvas, bg="#ffffff")
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw", tags="inner")

        # 画布宽度跟随窗口变化
        def _on_configure(event):
            self.canvas.itemconfig("inner", width=event.width)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.bind("<Configure>", _on_configure)

        # 内容变化时更新滚动区域
        def _on_frame_configure(event=None):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.scroll_frame.bind("<Configure>", _on_frame_configure)

        # 鼠标滚轮支持（Windows/macOS 用 <MouseWheel>，Linux 用 <Button-4>/<Button-5>）
        def _on_mousewheel(event):
            if event.delta:
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                if event.num == 4:
                    self.canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.canvas.yview_scroll(1, "units")

        # 只在鼠标进入画布区域时生效，避免抢占其他控件的滚轮事件
        def _bind_wheel(event=None):
            self._wheel_bind_ids = [
                self.canvas.bind_all("<MouseWheel>", _on_mousewheel, add="+"),
                self.canvas.bind_all("<Button-4>", _on_mousewheel, add="+"),
                self.canvas.bind_all("<Button-5>", _on_mousewheel, add="+"),
            ]
        def _unbind_wheel(event=None):
            for bid in self._wheel_bind_ids:
                try:
                    self.canvas.unbind_all("<MouseWheel>", bid)
                    self.canvas.unbind_all("<Button-4>", bid)
                    self.canvas.unbind_all("<Button-5>", bid)
                except Exception:
                    pass
            self._wheel_bind_ids = []

        self._wheel_bind_ids = []
        self.canvas.bind("<Enter>", _bind_wheel)
        self.canvas.bind("<Leave>", _unbind_wheel)
        _bind_wheel()  # 初始绑定一次

        # 键盘翻页（仅当焦点在本窗口时生效）
        self._key_bind_ids = [
            self.root.bind("<Up>", lambda e: self.canvas.yview_scroll(-1, "units")),
            self.root.bind("<Down>", lambda e: self.canvas.yview_scroll(1, "units")),
            self.root.bind("<Prior>", lambda e: self.canvas.yview_scroll(-5, "units")),
            self.root.bind("<Next>", lambda e: self.canvas.yview_scroll(5, "units")),
        ]

        self._mode = "scroll"

    def _teardown_scroll(self):
        """切换回简单模式，解绑所有事件避免残留"""
        # 解绑滚轮事件
        if hasattr(self, '_wheel_bind_ids') and self._wheel_bind_ids:
            for bid in self._wheel_bind_ids:
                try:
                    self.root.unbind_all("<MouseWheel>", bid)
                    self.root.unbind_all("<Button-4>", bid)
                    self.root.unbind_all("<Button-5>", bid)
                except Exception:
                    pass
            self._wheel_bind_ids = []
        # 解绑键盘事件
        if hasattr(self, '_key_bind_ids') and self._key_bind_ids:
            keys = ["<Up>", "<Down>", "<Prior>", "<Next>"]
            for seq, bid in zip(keys, self._key_bind_ids):
                try:
                    self.root.unbind(seq, bid)
                except Exception:
                    pass
            self._key_bind_ids = []
        for w in self.container.winfo_children():
            w.destroy()
        self._mode = "simple"


    # ─── 创建行 ───────────────────────────────────────────

    def _create_row(self, parent, index, word):
        row_bg = "#ffffff" if index % 2 == 1 else "#f9fafb"
        row = tk.Frame(parent, bg=row_bg, height=self.ROW_HEIGHT)
        row.pack(fill=tk.X)
        row.pack_propagate(False)

        tk.Frame(row, bg="#f3f4f6", height=1).pack(fill=tk.X, side=tk.BOTTOM)

        tk.Label(row, text=str(index), font=("Microsoft YaHei", 11),
                 bg=row_bg, fg="#9ca3af", width=6, anchor="w").pack(side=tk.LEFT, padx=6)

        tk.Label(row, text=word.get("english", ""), font=("Microsoft YaHei", 11, "bold"),
                 bg=row_bg, fg="#4f46e5", anchor="w", width=20).pack(side=tk.LEFT, padx=6)

        tk.Label(row, text=word.get("chinese", ""), font=("Microsoft YaHei", 11),
                 bg=row_bg, fg="#1f2937", anchor="w", width=20).pack(side=tk.LEFT, padx=6)

        # 备注 + 复习次数
        count = word.get("correct_count", 0)
        note = word.get("note", "")
        if note:
            note_text = f"{note}（已复习{count}次）"
            note_color = "#7c3aed"
        else:
            note_text = "点击添加备注…" if count == 0 else f"点击添加备注…（已复习{count}次）"
            note_color = "#9ca3af"
        note_lbl = tk.Label(row, text=note_text, font=("Microsoft YaHei", 10),
                            bg=row_bg, fg=note_color, anchor="w", width=26, cursor="hand2")
        note_lbl.pack(side=tk.LEFT, padx=6)
        note_lbl.bind("<Button-1>", lambda e, w=word: self._edit_note(w))

        # 重点复习标记（爆炸加进来的错词会带上）
        if word.get("priority"):
            tk.Label(row, text="重点", font=("Microsoft YaHei", 9),
                     bg=row_bg, fg="#f59e0b", anchor="w").pack(side=tk.LEFT)

        tk.Button(row, text="删除", font=("Microsoft YaHei", 9),
                  bg=row_bg, fg="#ef4444", activebackground="#fef2f2",
                  activeforeground="#dc2626", relief=tk.FLAT, cursor="hand2", width=4,
                  command=lambda w=word: self._delete_word(w)).pack(side=tk.RIGHT, padx=8)

    # ═══════════════════════════════════════════════════════
    #  添加 / 编辑 / 删除
    # ═══════════════════════════════════════════════════════

    def _add_word(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("添加单词")
        dialog.geometry("440x340")
        dialog.configure(bg="#ffffff")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        self._center_dialog(dialog, 440, 340)

        tk.Label(dialog, text="添加新单词", font=("Microsoft YaHei", 15, "bold"),
                 bg="#ffffff", fg="#1f2937").pack(pady=(24, 20))

        # 英文
        tk.Label(dialog, text="英文 *", font=("Microsoft YaHei", 11),
                 bg="#ffffff", fg="#6b7280").pack(anchor="w", padx=40)
        en_entry = tk.Entry(dialog, font=("Microsoft YaHei", 12), bg="#f9fafb",
                            fg="#1f2937", insertbackground="#1f2937",
                            relief=tk.SOLID, bd=1, highlightcolor="#4f46e5",
                            highlightbackground="#d1d5db")
        en_entry.pack(fill=tk.X, padx=40, pady=(4, 12), ipady=6)
        en_entry.focus_set()

        # 中文
        tk.Label(dialog, text="中文 *", font=("Microsoft YaHei", 11),
                 bg="#ffffff", fg="#6b7280").pack(anchor="w", padx=40)
        cn_entry = tk.Entry(dialog, font=("Microsoft YaHei", 12), bg="#f9fafb",
                            fg="#1f2937", insertbackground="#1f2937",
                            relief=tk.SOLID, bd=1, highlightcolor="#4f46e5",
                            highlightbackground="#d1d5db")
        cn_entry.pack(fill=tk.X, padx=40, pady=(4, 12), ipady=6)

        # 备注（可选）
        tk.Label(dialog, text="备注（可选）", font=("Microsoft YaHei", 11),
                 bg="#ffffff", fg="#6b7280").pack(anchor="w", padx=40)
        note_entry = tk.Entry(dialog, font=("Microsoft YaHei", 12), bg="#f9fafb",
                              fg="#1f2937", insertbackground="#1f2937",
                              relief=tk.SOLID, bd=1, highlightcolor="#7c3aed",
                              highlightbackground="#d1d5db")
        note_entry.pack(fill=tk.X, padx=40, pady=(4, 20), ipady=6)

        en_entry.bind("<Return>", lambda e: cn_entry.focus_set())
        cn_entry.bind("<Return>", lambda e: note_entry.focus_set())

        def confirm():
            en = en_entry.get().strip()
            cn = cn_entry.get().strip()
            note = note_entry.get().strip()
            if not en or not cn:
                messagebox.showwarning("提示", "英文和中文为必填项！", parent=dialog)
                return
            self.words.append(make_word(en, cn, note))
            save_data(self.words)
            self._refresh_list()
            dialog.destroy()

        note_entry.bind("<Return>", lambda e: confirm())

        bf = tk.Frame(dialog, bg="#ffffff")
        bf.pack(pady=4)
        tk.Button(bf, text="取消", font=("Microsoft YaHei", 10),
                  bg="#f3f4f6", fg="#374151", relief=tk.FLAT, padx=24, pady=6,
                  cursor="hand2", command=dialog.destroy).pack(side=tk.LEFT, padx=10)
        tk.Button(bf, text="添加", font=("Microsoft YaHei", 10, "bold"),
                  bg="#4f46e5", fg="white", relief=tk.FLAT, padx=24, pady=6,
                  cursor="hand2", command=confirm).pack(side=tk.LEFT, padx=10)

    def _edit_note(self, word):
        dialog = tk.Toplevel(self.root)
        dialog.title("编辑备注")
        dialog.geometry("420x220")
        dialog.configure(bg="#ffffff")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        self._center_dialog(dialog, 420, 220)

        tk.Label(dialog, text=f"备注 — {word.get('english', '')}",
                 font=("Microsoft YaHei", 14, "bold"),
                 bg="#ffffff", fg="#1f2937").pack(pady=(20, 16))

        entry = tk.Entry(dialog, font=("Microsoft YaHei", 12), bg="#f9fafb",
                         fg="#1f2937", insertbackground="#1f2937",
                         relief=tk.SOLID, bd=1, highlightcolor="#7c3aed",
                         highlightbackground="#d1d5db")
        entry.pack(fill=tk.X, padx=40, pady=(0, 24), ipady=8)
        entry.insert(0, word.get("note", ""))
        entry.focus_set()
        entry.select_range(0, tk.END)

        def save():
            word["note"] = entry.get().strip()
            save_data(self.words)
            self._refresh_list()
            dialog.destroy()

        entry.bind("<Return>", lambda e: save())
        tk.Button(dialog, text="保存", font=("Microsoft YaHei", 10, "bold"),
                  bg="#4f46e5", fg="white", relief=tk.FLAT, padx=28, pady=6,
                  cursor="hand2", command=save).pack()

    def _delete_word(self, word):
        if messagebox.askyesno(
                "确认删除",
                f"确定删除「{word.get('english', '')} - {word.get('chinese', '')}」？"):
            self.words.remove(word)
            save_data(self.words)
            self._refresh_list()

    # ═══════════════════════════════════════════════════════
    #  复习巩固页面
    # ═══════════════════════════════════════════════════════

    def _open_review(self):
        """打开复习巩固页面"""
        # 筛选需要复习的单词
        today = datetime.now().date()
        review_words = []
        for w in self.words:
            if w.get("completed"):
                continue
            try:
                next_r = datetime.fromisoformat(w["next_review"]).date()
            except (KeyError, ValueError):
                next_r = today
            if today >= next_r:
                review_words.append(w)

        # 排序：重点复习的排前面，然后按阶段升序
        review_words.sort(key=lambda w: (not w.get("priority"), w.get("review_stage", 0)))

        # 切换到复习页面
        for wid in self.body.winfo_children():
            wid.destroy()

        # ── 顶部栏 ──
        top = tk.Frame(self.body, bg="#ffffff", height=64)
        top.pack(fill=tk.X, padx=20, pady=(16, 0))
        top.pack_propagate(False)

        # 左上：退出（位置和其他练习窗口一致）
        tk.Button(
            top, text="退出", font=("Microsoft YaHei", 11),
            bg="#e74c3c", fg="white", activebackground="#c0392b",
            relief=tk.FLAT, padx=14, pady=6, cursor="hand2",
            command=self._quit,
        ).pack(side=tk.LEFT)

        tk.Button(
            top, text="← 返回", font=("Microsoft YaHei", 12, "bold"),
            bg="#6b7280", fg="white", activebackground="#4b5563",
            relief=tk.FLAT, padx=16, pady=8, cursor="hand2",
            command=self._back_to_main,
        ).pack(side=tk.LEFT, padx=(10, 0))

        tk.Label(
            top, text="复习巩固，助力长期记忆",
            font=("Microsoft YaHei", 22, "bold"),
            bg="#ffffff", fg="#7c3aed",
        ).pack(expand=True)

        tk.Label(top, text="", bg="#ffffff", width=14).pack(side=tk.RIGHT)

        # ── 复习内容区 ──
        if not review_words:
            tk.Label(
                self.body, text="🎉 暂无需要复习的单词，继续保持！",
                font=("Microsoft YaHei", 16), bg="#ffffff", fg="#6b7280",
            ).pack(expand=True)
            return

        # 复习状态
        self._review_queue = review_words
        self._review_idx = 0
        self._review_correct = 0
        self._review_wrong = 0
        self._attempts = 0  # 当前单词已用次数
        self._show_note = tk.BooleanVar(value=True)  # 是否显示备注提示

        # 复习卡片区域
        self.review_frame = tk.Frame(self.body, bg="#ffffff")
        self.review_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=20)

        # 备注提示开关
        note_toggle_frame = tk.Frame(self.review_frame, bg="#ffffff")
        note_toggle_frame.pack(pady=(0, 4))
        tk.Checkbutton(
            note_toggle_frame, text="显示备注提示", variable=self._show_note,
            font=("Microsoft YaHei", 10), bg="#ffffff", fg="#6b7280",
            activebackground="#ffffff", selectcolor="#ffffff",
            command=self._toggle_note_hint,
        ).pack(side=tk.LEFT)

        # 进度条
        self.progress_label = tk.Label(
            self.review_frame, text="",
            font=("Microsoft YaHei", 11), bg="#ffffff", fg="#9ca3af",
        )
        self.progress_label.pack(pady=(0, 12))

        # 中文提示
        self.chinese_label = tk.Label(
            self.review_frame, text="",
            font=("Microsoft YaHei", 28, "bold"), bg="#ffffff", fg="#1f2937",
        )
        self.chinese_label.pack(pady=(20, 8))

        # 备注提示
        self.note_hint = tk.Label(
            self.review_frame, text="",
            font=("Microsoft YaHei", 11), bg="#ffffff", fg="#9ca3af",
        )
        self.note_hint.pack(pady=(0, 24))

        # 输入框
        self.answer_entry = tk.Entry(
            self.review_frame, font=("Microsoft YaHei", 16),
            bg="#f9fafb", fg="#1f2937", insertbackground="#1f2937",
            relief=tk.SOLID, bd=2, highlightcolor="#7c3aed",
            highlightbackground="#d1d5db", justify="center",
        )
        self.answer_entry.pack(fill=tk.X, padx=60, ipady=10)
        self.answer_entry.focus_set()
        self.answer_entry.bind("<Return>", lambda e: self._check_answer())

        # 提示文字
        self.hint_label = tk.Label(
            self.review_frame, text="输入英文后按回车提交",
            font=("Microsoft YaHei", 10), bg="#ffffff", fg="#9ca3af",
        )
        self.hint_label.pack(pady=(12, 0))

        # 反馈文字
        self.feedback_label = tk.Label(
            self.review_frame, text="",
            font=("Microsoft YaHei", 14, "bold"), bg="#ffffff",
        )
        self.feedback_label.pack(pady=(16, 0))

        # 统计
        self.stats_label = tk.Label(
            self.review_frame, text="",
            font=("Microsoft YaHei", 10), bg="#ffffff", fg="#9ca3af",
        )
        self.stats_label.pack(side=tk.BOTTOM, pady=(0, 8))

        self._show_current_word()

    def _show_current_word(self):
        """显示当前复习的单词"""
        if self._review_idx >= len(self._review_queue):
            self._finish_review()
            return

        word = self._review_queue[self._review_idx]
        self._attempts = 0

        self.progress_label.config(
            text=f"第 {self._review_idx + 1} / {len(self._review_queue)} 个单词"
        )
        self.chinese_label.config(text=word.get("chinese", ""))
        # 根据开关决定是否显示备注
        if self._show_note.get() and word.get("note"):
            self.note_hint.config(text=f"备注：{word['note']}")
        else:
            self.note_hint.config(text="")
        self.answer_entry.delete(0, tk.END)
        self.hint_label.config(text="输入英文后按回车提交", fg="#9ca3af")
        self.feedback_label.config(text="")
        self.stats_label.config(
            text=f"✅ 正确 {self._review_correct}  ❌ 错误 {self._review_wrong}"
        )
        self.answer_entry.focus_set()

    def _toggle_note_hint(self):
        """切换备注提示显示"""
        if self._review_idx >= len(self._review_queue):
            return
        word = self._review_queue[self._review_idx]
        if self._show_note.get() and word.get("note"):
            self.note_hint.config(text=f"备注：{word['note']}")
        else:
            self.note_hint.config(text="")

    def _check_answer(self):
        """检查答案"""
        if self._review_idx >= len(self._review_queue):
            return

        word = self._review_queue[self._review_idx]
        answer = self.answer_entry.get().strip().lower()
        correct = str(word.get("english", "")).strip().lower()

        if not answer:
            return

        self._attempts += 1

        if answer == correct:
            # 回答正确
            self._review_correct += 1
            word["correct_count"] = word.get("correct_count", 0) + 1
            word["priority"] = False

            # 判断是否完成
            if (word["correct_count"] >= MAX_CORRECT
                    or word.get("review_stage", 0) >= len(REVIEW_INTERVALS) - 1):
                word["completed"] = True
                self.feedback_label.config(text="✅ 正确！该单词已完成全部复习！", fg="#059669")
            else:
                # 进入下一阶段
                word["review_stage"] = word.get("review_stage", 0) + 1
                next_days = REVIEW_INTERVALS[word["review_stage"]]
                word["next_review"] = (datetime.now() + timedelta(days=next_days)).isoformat()
                self.feedback_label.config(
                    text=f"✅ 正确！下次复习：{next_days}天后", fg="#059669"
                )

            save_data(self.words)
            self._review_idx += 1
            self.root.after(1200, self._show_current_word)

        elif self._attempts >= 2:
            # 两次都用完，答错
            self._review_wrong += 1
            word["priority"] = True  # 标记重点复习
            save_data(self.words)
            self.feedback_label.config(
                text=f"❌ 正确答案是：{word.get('english', '')}，已标记为重点复习", fg="#dc2626"
            )
            self._review_idx += 1
            self.root.after(1800, self._show_current_word)

        else:
            # 第一次答错，还有机会
            self.feedback_label.config(
                text=f"❌ 再试一次！（还剩 {2 - self._attempts} 次机会）", fg="#f59e0b"
            )
            self.hint_label.config(text=f"提示：首字母是「{correct[0]}」", fg="#f59e0b")
            self.answer_entry.delete(0, tk.END)
            self.answer_entry.focus_set()

    def _finish_review(self):
        """复习结束"""
        for w in self.review_frame.winfo_children():
            w.destroy()

        tk.Label(
            self.review_frame, text="🎉 本轮复习完成！",
            font=("Microsoft YaHei", 24, "bold"), bg="#ffffff", fg="#7c3aed",
        ).pack(pady=(40, 16))

        tk.Label(
            self.review_frame,
            text=f"✅ 正确 {self._review_correct} 个    ❌ 错误 {self._review_wrong} 个",
            font=("Microsoft YaHei", 14), bg="#ffffff", fg="#6b7280",
        ).pack(pady=(0, 30))

        # 统计剩余
        today = datetime.now().date()
        remaining = 0
        for w in self.words:
            if w.get("completed"):
                continue
            try:
                if datetime.fromisoformat(w["next_review"]).date() <= today:
                    remaining += 1
            except (KeyError, ValueError):
                remaining += 1

        if remaining > 0:
            tk.Label(
                self.review_frame,
                text=f"还有 {remaining} 个单词等待复习",
                font=("Microsoft YaHei", 12), bg="#ffffff", fg="#9ca3af",
            ).pack(pady=(0, 20))
        else:
            tk.Label(
                self.review_frame,
                text="所有单词复习完毕，太棒了！",
                font=("Microsoft YaHei", 12), bg="#ffffff", fg="#059669",
            ).pack(pady=(0, 20))

        tk.Button(
            self.review_frame, text="返回主页", font=("Microsoft YaHei", 12, "bold"),
            bg="#4f46e5", fg="white", activebackground="#4338ca",
            relief=tk.FLAT, padx=32, pady=10, cursor="hand2",
            command=self._back_to_main,
        ).pack(pady=(20, 0))

    def _back_to_main(self):
        """返回主页面"""
        self._build_main_page()
        self._refresh_list()

    # ═══════════════════════════════════════════════════════
    #  工具方法
    # ═══════════════════════════════════════════════════════

    def _center_dialog(self, dialog, w, h):
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        dialog.geometry(f"+{x}+{y}")


# ─── 启动 ─────────────────────────────────────────────────

# ─── 单窗口管理（供主程序与其它模块统一调用）────────────────
_OWN_ROOT = None


def _set_root(root):
    global _OWN_ROOT
    _OWN_ROOT = root


def has_window():
    """当前是否已经开着单词笔记窗口。"""
    r = _OWN_ROOT
    if r is None:
        return False
    try:
        return bool(r.winfo_exists())
    except Exception:
        return False


def focus_window():
    """把已经开着的单词笔记窗口提到最前。"""
    r = _OWN_ROOT
    if r is None:
        return
    try:
        r.deiconify()
        r.lift()
        r.focus_force()
    except Exception:
        pass


def clear_window():
    """关闭单词笔记窗口。"""
    global _OWN_ROOT
    r, _OWN_ROOT = _OWN_ROOT, None
    if r is None:
        return
    try:
        r.destroy()
    except Exception:
        pass


def run(banner=None):
    """打开单词笔记窗口（阻塞到关窗为止）。

    banner : 窗口顶部图标；主程序会用统一入口把默认图标传进来
    """
    if not available():
        raise RuntimeError("本机 Python 缺少 tkinter，无法打开单词笔记")

    try:
        import spell
    except Exception:                    # 独立运行时没有 spell 也能开窗
        spell = None

    if spell is None:
        root = tk.Tk()
        WordNotesApp(root)
        root.mainloop()
        return

    if has_window() or spell.has_window():
        focus_window()
        try:
            spell.focus_window()
        except Exception:
            pass
        return

    def _factory(root):
        _set_root(root)
        return WordNotesApp(root)

    # 本窗口自己带左上角「退出」按钮（放在页面顶部栏里），所以不要框架再加一个
    spell.open_window(_factory,
                      banner or spell.default_banner(),
                      with_quit=False)
    _set_root(None)


if __name__ == "__main__":
    run()
