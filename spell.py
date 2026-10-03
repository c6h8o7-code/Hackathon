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
import A
import random, word_note
import word_explosion

try:                      # tkinter 是标准库，但部分 Python 发行版未带
    import tkinter as tk
    from tkinter import font as tkfont
except ImportError:       # 交给主程序提示用户，而不是整个程序都起不来
    tk = None
    tkfont = None

BASE_DIR = A.app_dir()
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

def load_words2(names=None):
    """把若干词库摊平成一个单词列表（但不只取「单词」这一列）。

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
                yb = str(item.get('音标', '') if isinstance(item, dict)
                           else item).strip()
                cx = str(item.get('词性', '') if isinstance(item, dict)
                           else item).strip()
                sy = str(item.get('释义', '') if isinstance(item, dict)
                           else item).strip()
                
                if text:
                    words.append((text, yb, cx, sy))
    return words


def make_pool(wordbank):
    """把原始词条整理成可出题的单词表：去空白、转小写、去重、剔掉短词和非纯字母。"""
    # print(wordbank)
    pool = []
    for raw, k in wordbank:
        word = str(raw).strip().lower()
        if len(word) >= MIN_LEN and word.isalpha() and word not in pool:
            pool.append((word, k))
    return pool

def default_banner():
    """练习窗口顶部默认用的那张图标；找不到就返回 None"""
    p = BANNER
    return str(p) if p.is_file() else None

# ---------------------------------------------------------------- 窗口控制
def clear_window():
    """关闭本模块打开的所有测试窗口（主程序把它绑在“退出”按钮上）。"""
    closing, _ROOTS[:] = list(_ROOTS), []
    for root in closing:
        try:
            root.destroy()
        except Exception:
            pass


def attach_window(root):
    """把外部自己创建的窗口登记进来，之后 clear_window()/has_window() 就能管到它。

    单词笔记（word_note）因为页面顶部自带退出按钮，是自己建 root 的，
    建好后调用本函数登记，主程序「已经开着一个就不再开第二个」才生效。
    """
    if root not in _ROOTS:
        _ROOTS.append(root)
    return root


def _alive_roots():
    """返回还活着的窗口，并顺手把已销毁的引用清掉。

    用户点窗口右上角的 X 关闭时，root 被销毁但引用还留在 _ROOTS 里；
    之前 has_window() 只看列表是否非空，于是窗口明明关掉了却仍返回 True，
    再点「开始」按钮就会走 focus_window() 分支——去 focus 一个已经不存在的
    窗口，结果就是「点了没反应，窗口再也打不开」。
    """
    alive = []
    for root in _ROOTS:
        try:
            if root.winfo_exists():
                alive.append(root)
        except Exception:
            pass
    _ROOTS[:] = alive
    return alive


def has_window():
    """当前是否已有测试窗口开着。"""
    return bool(_alive_roots())


def focus_window():
    """把已经开着的测试窗口提到最前。"""
    for root in _alive_roots():
        try:
            root.deiconify()
            root.lift()
            root.focus_force()
        except Exception:
            pass

def _new_root(banner=None, with_quit=True):
    """建一个 tk 窗口：左上角退出按钮 + 顶部图标。

    with_quit=False 时不再往窗口上贴退出按钮 —— 给「单词笔记」这种
    自己在页面顶部栏里带退出键的界面用，免得两个按钮叠在一起。
    """
    root = tk.Tk()
    root.configure(bg=BG)

    if with_quit:
        # 左上角退出按钮（place 定位，避免与顶部图标布局相互干扰）
        quit_btn = tk.Button(root, text=u"退出", font=("", 11), bg="#e74c3c",
                             fg="white", activebackground="#c0392b",
                             activeforeground="white", relief="flat", bd=0,
                             padx=18, pady=4, cursor="hand2",
                             command=clear_window)
        quit_btn.place(relx=0.0, rely=0.0, anchor="nw", x=18, y=14)

    top = tk.Frame(root, bg=BG)
    top.pack(fill="x", pady=(10, 0))

    imgs = []
    if banner:
        p = pathlib.Path(str(banner))
        if p.is_file():
            try:
                img = tk.PhotoImage(file=str(p))
                lbl = tk.Label(top, image=img, bg=BG)
                lbl.image = img              # 保住引用，否则图片会变空白
                lbl.pack()
                imgs.append(img)
            except tk.TclError as exc:
                print("图标加载失败: %s" % exc)

    root._banner_images = imgs           # 防止图片被回收变空白
    return root

def open_window(factory, banner=None, with_quit=True):
    """建窗口 + 打开练习界面，阻塞到关窗为止。

    factory  : 接收 root，在窗口里搭好界面，如 lambda r: SpellingApp(r, pool)
    with_quit: 是否在窗口左上角自动加「退出」按钮（单词笔记自带给，传 False）
    已经开着一个窗口时不再重复打开，只把它提到最前。
    """
    if not available():
        raise NoWordsError("当前 Python 没有 tkinter，无法打开练习窗口。")
    if has_window():                     # 已经开着一个就别再开一个
        focus_window()
        return

    root = _new_root(banner, with_quit)
    # 统一在这里登记：各练习界面自己也会登记，但那样一旦漏掉某个界面，
    # 「已经开着就别再开」的判断就会失效，集中做一次最稳。
    attach_window(root)
    try:
        factory(root)
    except Exception:
        root.destroy()
        raise
    root.mainloop()
# ---------------------------------------------------------------- 测试窗口
class WordQuizApp:
    """字母填空小游戏：单词缺一个字母，从选项中挑出正确的那一个。"""

    def __init__(self, root, wordbank=None, names=None,
                 title=u'十八中考单词拼写', geometry='1500x1000'):
        if tk is None:
            raise NoWordsError(u'本机 Python 缺少 tkinter，无法进行拼写测试')

        self.root = root
        if wordbank is None:
            wordbank = list(map(lambda x: (x[0], x[3]), load_words2(names)))

        self.WORD_BANK = make_pool(wordbank)
        if not self.WORD_BANK:
            raise NoWordsError(u'勾选的词库里没有找到可用单词，\n'
                               u'请先在「文件 - 编辑 - 配置词库」里勾选词库。')

        self.root.title(title)
        # self.root.overrideredirect(True)
        # self.root.attributes("-fullscreen", True)
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
        self.wrong_streak = 0           # 同一题的连续错误次数
        self.fail_threshold = 3         # 连续错几次触发爆炸

        attach_window(root)             # 登记窗口（重复登记会自动去重）
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.next_round()

    # ------------------------------------------------------------ 出题
    def next_round(self):
        if not self.alive or not self._window_alive():
            self.alive = False
            return
        i = random.randint(0, len(self.WORD_BANK)-1)
        self.word = self.WORD_BANK[i][0]
        self.Cword= self.WORD_BANK[i][1]
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
            self.wrong_streak = 0
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
            self.wrong_streak += 1
            remain = max(0, self.fail_threshold - self.wrong_streak)
            if remain > 0:
                self.fb_label.config(
                    text=u"Noops,try again:(（再错 %d 次单词就炸了！）" % remain,
                    fg="#c84646")
            else:
                # 达到阈值：触发爆炸
                self.fb_label.config(
                    text=u"连续错 %d 次！单词炸啦！💥" % self.fail_threshold,
                    fg="#e74c3c")
                self._trigger_explosion()
                
    def _trigger_explosion(self):
        """连续答错 → 单词从天而降砸地炸开，结束后进入下一题。"""
        self.locked = True
        # 把题面区域隐藏起来，让爆炸更显眼
        try:
            self.word_label.config(text="")
        except Exception:
            pass
        for b in self.buttons:
            try:
                b.destroy()
            except Exception:
                pass
        self.buttons = []
        
        # 加入错词本
        if word_note is not None:
            try:
                word_note.add_wrong(self.word, "", self.Cword, "")
            except Exception as exc:
                print("加入错词本失败:", exc)
        def _after():
            self.wrong_streak = 0
            if self.alive and self._window_alive():
                self.next_round()

        try:
            word_explosion.trigger(
                self.root, self.word,
                duration_ms=2600,
                bg=BG,
                word_color="#ffffff",
                letter_color="#ff6b6b",
                letter_outline="#7b1d1d",
                flash_color="#ffd04a",
                smoke_color="#b0c4de",
                font_size=84,
                on_done=_after,
            )
        except Exception as exc:
            print("word_explosion 触发失败: %s" % exc)
            self.root.after(500, _after)

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
    if has_window():
        focus_window()

    else:
        open_window(lambda r: WordQuizApp(r, names=names), default_banner())

if __name__ == '__main__':
    run()
