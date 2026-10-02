# -*- coding: utf-8 -*-
"""十八单词 —— 拼写测试界面（tkinter 字母填空版）

玩法：随机取一个单词，挖掉其中一个字母，让玩家从若干字母里挑出正确的那一个。
      选对 -> 补全单词并显示 Correct!，稍后自动出下一题；
      选错 -> 该选项消失并提示重试，直到选对为止。

在主程序 十八单词.py 里这样调用：

    import spell, tkinter as tk
    root = tk.Tk()
    spell.WordQuizApp(root)                    # 词库取自 latest.json 的勾选
    spell.WordQuizApp(root, names=['初一'])    # 也可显式指定词库
    root.mainloop()

单独试玩本文件：python spell.py
"""

import json
import pathlib
import random

try:                      # tkinter 是标准库，但部分 Python 发行版未带
    import tkinter as tk
    from tkinter import font as tkfont
except ImportError:       # 交给主程序提示用户，而不是整个程序都起不来
    tk = None
    tkfont = None

BASE_DIR = pathlib.Path(__file__).resolve().parent
LIB_DIR = BASE_DIR / 'dev_english'
LATEST = BASE_DIR / 'latest.json'
BANNER = BASE_DIR / '18单词第二代图标.gif'

# ---------------------------------------------------------------- 外观与规则
ALPHABET = "abcdefghijklmnopqrstuvwxyz"
BG = "#759CE6"            # 背景色
BTN = "#7eb7e6"           # 选项按钮底色
BTN_HOVER = "#18aacc"     # 选项按钮悬停色
INK = "#283246"           # 单词文字色
HINT = "#A2E6BA"          # 提示文字色

MIN_LEN = 4               # 短于这个长度的词（a、it）没有填空价值，跳过
OPTION_COUNT = 5          # 每题给出几个选项
REVEAL_MS = 2000          # 答对后停留多久再出下一题（毫秒）

_ROOTS = []               # 本模块打开的测试窗口，供 clear_window() 关闭


class NoWordsError(RuntimeError):
    """勾选的词库里一条可用单词都没有时抛出。"""


# ---------------------------------------------------------------- 环境与词库
def available():
    """本机是否能用 tkinter 画界面。"""
    return tk is not None


def load_selected_names():
    """读 latest.json，返回被勾选的词库名列表；读不到就返回空表。"""
    try:
        data = json.loads(LATEST.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []
    if isinstance(data, dict):
        return [k for k, v in data.items() if v]
    if isinstance(data, list):
        return [str(x) for x in data]
    return []


def load_words(names=None):
    """把若干词库摊平成一个单词列表（只取「单词」这一列）。

    names 为空时用 latest.json 的勾选结果；仍为空则用 dev_english 下全部词库。
    """
    if not names:
        names = load_selected_names()
    if not names:
        names = [p.stem for p in sorted(LIB_DIR.glob('*.json'))]

    words = []
    for name in names:
        path = LIB_DIR / ('%s.json' % name)
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        units = data.get('单元') if isinstance(data, dict) else data
        if not isinstance(units, list):
            continue
        for unit in units:
            if not isinstance(unit, dict):
                continue
            for item in unit.get('单词', []):
                text = str(item.get('单词', '') if isinstance(item, dict)
                           else item).strip()
                if text:
                    words.append(text)
    return words


def make_pool(wordbank):
    """把原始词条整理成可出题的单词表：去空白、转小写、去重、剔掉短词和非纯字母。"""
    pool = []
    for raw in wordbank:
        word = str(raw).strip().lower()
        if len(word) >= MIN_LEN and word.isalpha() and word not in pool:
            pool.append(word)
    return pool


# ---------------------------------------------------------------- 窗口控制
def clear_window():
    """关闭本模块打开的所有测试窗口（主程序把它绑在“退出”按钮上）。"""
    closing, _ROOTS[:] = list(_ROOTS), []
    for root in closing:
        try:
            root.destroy()
        except Exception:
            pass


def has_window():
    """当前是否已有测试窗口开着。"""
    return bool(_ROOTS)


def focus_window():
    """把已经开着的测试窗口提到最前。"""
    for root in _ROOTS:
        try:
            root.deiconify()
            root.lift()
            root.focus_force()
        except Exception:
            pass


# ---------------------------------------------------------------- 测试窗口
class WordQuizApp:
    """字母填空小游戏：单词缺一个字母，从选项中挑出正确的那一个。"""

    def __init__(self, root, wordbank=None, names=None,
                 title=u'十八中考单词拼写', geometry='1500x1000'):
        if tk is None:
            raise NoWordsError(u'本机 Python 缺少 tkinter，无法进行拼写测试')

        self.root = root
        if wordbank is None:
            wordbank = load_words(names)

        self.WORD_BANK = make_pool(wordbank)
        if not self.WORD_BANK:
            raise NoWordsError(u'勾选的词库里没有找到可用单词，\n'
                               u'请先在「文件 - 编辑 - 配置词库」里勾选词库。')

        self.root.title(title)
        # self.root.overrideredirect(True)
        self.root.attributes("-fullscreen", True)
        self.root.geometry(geometry)
        self.root.configure(bg=BG)

        self.word_font = tkfont.Font(family="Arial", size=48, weight="bold")
        self.hint_font = tkfont.Font(family="Arial", size=16)
        self.btn_font = tkfont.Font(family="Arial", size=28, weight="bold")
        self.fb_font = tkfont.Font(family="Arial", size=18)
        tk.Label(root, text=u"请选择正确的字母填到下划线处：",
                 font=self.hint_font, fg=HINT, bg=BG).pack(pady=(70, 10))

        self.word_label = tk.Label(root, text="", font=self.word_font,
                                   fg=INK, bg=BG)
        self.word_label.pack(pady=10)

        self.fb_label = tk.Label(root, text="", font=self.fb_font, bg=BG)
        self.fb_label.pack(pady=10)

        self.btn_frame = tk.Frame(root, bg=BG)
        self.btn_frame.pack(pady=50)

        self.word = ""
        self.blank_idx = 0
        self.buttons = []
        self.locked = False
        self.alive = True

        _ROOTS.append(root)
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.next_round()

    # ------------------------------------------------------------ 出题
    def next_round(self):
        if not self.alive or not self._window_alive():
            self.alive = False
            return

        self.word = random.choice(self.WORD_BANK)
        self.blank_idx = random.randrange(len(self.word))
        correct = self.word[self.blank_idx]
        wrong = random.sample([c for c in ALPHABET if c != correct],
                              min(OPTION_COUNT - 1, len(ALPHABET) - 1))
        options = wrong + [correct]
        random.shuffle(options)

        self.fb_label.config(text="", fg="#7B75C3")
        self.render_word()
        self.build_buttons(options)
        self.locked = False

    def render_word(self, show_full=False):
        chars = []
        for i, ch in enumerate(self.word):
            if i == self.blank_idx and not show_full:
                chars.append("_")
            else:
                chars.append(ch.upper())
        self.word_label.config(text="   ".join(chars))

    def build_buttons(self, options):
        for b in self.buttons:
            b.destroy()
        self.buttons = []
        for letter in options:
            b = tk.Button(self.btn_frame, text=letter.upper(),
                          font=self.btn_font, width=3, height=2,
                          bg=BTN, fg="white", relief="flat",
                          activebackground=BTN_HOVER, activeforeground="white",
                          cursor="hand2", bd=0,
                          command=lambda l=letter: self.on_click(l))
            b.pack(side=tk.LEFT, padx=25)
            self.buttons.append(b)

    # ------------------------------------------------------------ 答题
    def on_click(self, letter):
        if self.locked or not self.alive or not self._window_alive():
            return
        if letter == self.word[self.blank_idx]:
            self.locked = True
            for b in self.buttons:
                b.destroy()
            self.buttons = []
            self.render_word(show_full=True)
            self.fb_label.config(text="Correct! ", fg="#28a05a")
            self.root.after(REVEAL_MS, self.next_round)
        else:
            for b in self.buttons:
                if b.cget("text") == letter.upper():
                    b.destroy()
                    self.buttons.remove(b)
                    break
            self.fb_label.config(text=u"Noops,try again:(", fg="#c84646")

    # ------------------------------------------------------------ 收尾
    def _window_alive(self):
        try:
            return bool(self.root.winfo_exists())
        except Exception:
            return False

    def close(self):
        self.alive = False
        if self.root in _ROOTS:
            _ROOTS.remove(self.root)
        try:
            self.root.destroy()
        except Exception:
            pass


def run(names=None):
    """单独运行本文件时的入口：带图标和退出按钮。"""
    if tk is None:
        raise SystemExit(u'本机 Python 缺少 tkinter，装好后再试')

    root = tk.Tk()
    root.configure(bg=BG)

    top = tk.Frame(root, bg=BG)
    top.pack(fill='x')
    holder = {}
    if BANNER.is_file():
        try:
            holder['img'] = tk.PhotoImage(file=str(BANNER))
            tk.Label(top, image=holder['img'], bg=BG).pack(pady=(8, 4))
        except tk.TclError as exc:
            print(u'图标加载失败: %s' % exc)
    tk.Button(top, text=u'退出', command=clear_window).pack(pady=(0, 6))

    try:
        WordQuizApp(root, names=names)
    except NoWordsError as exc:
        print(exc)
        root.destroy()
        return
    root.mainloop()


if __name__ == '__main__':
    run()
