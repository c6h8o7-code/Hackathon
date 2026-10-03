# -*- coding: utf-8 -*-

"""十八单词 —— 英语词汇记忆工具（第三代 · 现代化 UI）

升级要点：
    1. 渐变背景（蓝紫渐变 + 浮动粒子动画）
    2. 毛玻璃卡片式按钮，悬停放大 + 阴影加深 + 渐变底色
    3. 点击涟漪（Ripple）动画
    4. 标题呼吸动画 + 渐变字色
    5. 平滑的按钮淡入/入场动画
    6. 现代化圆角设计、无硬边框
    7. 词库信息卡片（已选/总数/已学进度）
"""

import json
import math
import random
import time

import A
import spell
import explain
import word_game_tkinter
import word_note
import new_word_study

try:
    import tkinter as tk
except ImportError:
    tk = None

import wx

APP_TITLE = u'十八单词'

# 路径都交给 A 处理
BASE_DIR = A.app_dir()
APP_ICON = A.resource('icon.ico')
LIB_DIR = A.ensure_lib_dir('dev_english')
LATEST = BASE_DIR / 'latest.json'
RESOURCE = BASE_DIR / "res"
BANNER = A.resource('18单词第二代图标.gif')

# BUTTON ID
ACCEPT_CONFIG_BUTTON = 1
REFUSE_CONFIG_BUTTON = 2
# MENU ID
QUIT_MENU = 0
CONFIG_MENU = 1
EDIT_MENU = 2

# ---------------------------------------------------------------- 词库读取
LIB_ORDER = ['初一', '初二', '初三',
             '必修第一册', '必修第二册', '必修第三册',
             '选择性必修第一册', '选择性必修第二册',
             '选择性必修第三册', '选择性必修第四册']


def _lib_key(path):
    stem = path.stem
    return (LIB_ORDER.index(stem) if stem in LIB_ORDER else len(LIB_ORDER), stem)


def load_libs():
    libs = []
    if not LIB_DIR.is_dir():
        return libs
    for f in sorted(LIB_DIR.glob('*.json'), key=_lib_key):
        count = 0
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            if isinstance(data, dict) and isinstance(data.get('单元'), list):
                count = sum(len(u.get('单词', [])) for u in data['单元'])
            elif isinstance(data, list):
                count = len(data)
        except (OSError, ValueError) as exc:
            print('词库 %s 读取失败: %s' % (f.name, exc))
        libs.append((f.stem, f, count))
    return libs


def load_selected(libs):
    names = {n for n, _, _ in libs}
    try:
        data = json.loads(LATEST.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return names
    if isinstance(data, dict):
        picked = {k for k, v in data.items() if v}
    elif isinstance(data, list):
        picked = {str(x) for x in data}
    else:
        picked = set()
    return picked & names


def save_selected(libs, selected):
    data = {n: 1 for n, _, _ in libs if n in selected}
    try:
        LATEST.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                          encoding='utf-8')
    except OSError as exc:
        print('保存 latest.json 失败: %s' % exc)


# ---------------------------------------------------------------- 绘制适配
class _CoerceIntGC:
    """把传给 wx.GCDC 的浮点坐标自动取整。

    wx.GCDC 的绘制方法对参数类型很严格：传 float 会直接抛 TypeError
    （普通 DC 只是告警）。而界面里大量坐标是算出来的（除以 2、乘动画
    缩放系数），所以在这里统一兜一层，省得每个调用点手写 int()。
    非浮点参数（字符串、颜色、字体对象等）原样透传。
    """

    __slots__ = ('_gc',)

    def __init__(self, gc):
        object.__setattr__(self, '_gc', gc)

    def __getattr__(self, name):
        fn = getattr(object.__getattribute__(self, '_gc'), name)
        if not callable(fn):
            return fn

        def call(*args, **kwargs):
            args = tuple(int(v) if isinstance(v, float) else v for v in args)
            return fn(*args, **kwargs)

        return call


# ---------------------------------------------------------------- 自适应布局
# 大屏下的舒适尺寸
METRICS_IDEAL = {
    'pad_top': 62,        # 顶栏（EN 小标 + 配置按钮）之下、标题起始 y
    'title_size': 52,     # 主标题字号
    'sub_size': 16,       # 副标题字号
    'card_h': 80,         # 信息卡高度
    'btn_h': 72,          # 功能按钮高度
    'btn_gap': 18,        # 功能按钮之间的间距
    'g_title_card': 12,   # 副标题 → 信息卡
    'g_card_btn': 16,     # 信息卡 → 按钮区
    'ver_h': 32,          # 底部版本号 + 留白
}

# 压缩时的下限，保证再挤也还看得清、点得着
METRICS_MIN = {
    'title_size': 28,
    'sub_size': 12,
    'card_h': 50,
    'btn_h': 38,
    'btn_gap': 9,
}

TITLE_TEXT = u'十八单词'
SUBTITLE_TEXT = u'中考 · 高中英语词汇记忆工具'


def _compute_metrics(dc, h, n_buttons):
    """按窗口可用高度算出整套纵向布局尺寸。

    高度充裕就用「舒适值」；不够时依次压缩 按钮高度 → 按钮间距 → 卡片高度
    → 标题字号 → 副标题字号，保证 5 个按钮和底部信息始终完整落在窗口内，
    不会被挤出画面（之前的固定尺寸就是少了这一步）。

    dc 只要支持 SetFont / GetTextExtent 即可（ClientDC、MemoryDC、GCDC
    都能传），用它实测文字的真实像素高度，避免我凭字号猜高度猜错。
    """
    m = dict(METRICS_IDEAL)
    cache = {}

    def text_h(size, bold, text):
        key = (size, bold)
        if key not in cache:
            font = wx.Font(size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                           wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL,
                           faceName='Microsoft YaHei UI')
            dc.SetFont(font)
            cache[key] = dc.GetTextExtent(text)[1]
        return cache[key]

    def total(mm):
        th = text_h(mm['title_size'], True, TITLE_TEXT)
        sh = text_h(mm['sub_size'], False, SUBTITLE_TEXT)
        return (mm['pad_top'] + th + 10 + sh + mm['g_title_card'] + mm['card_h']
                + mm['g_card_btn'] + n_buttons * mm['btn_h']
                + (n_buttons - 1) * mm['btn_gap'] + mm['ver_h'])

    # 逐级压缩直到装得下（每轮只动一个量，压缩顺序决定视觉优先级的取舍）
    while total(m) > h:
        if m['btn_h'] > 52:
            m['btn_h'] -= 1
        elif m['btn_gap'] > METRICS_MIN['btn_gap']:
            m['btn_gap'] -= 1
        elif m['card_h'] > METRICS_MIN['card_h']:
            m['card_h'] -= 1
        elif m['title_size'] > METRICS_MIN['title_size']:
            m['title_size'] -= 1
        elif m['sub_size'] > METRICS_MIN['sub_size']:
            m['sub_size'] -= 1
        elif m['btn_h'] > METRICS_MIN['btn_h']:
            m['btn_h'] -= 1
        else:
            break

    m['title_h'] = text_h(m['title_size'], True, TITLE_TEXT)
    m['sub_h'] = text_h(m['sub_size'], False, SUBTITLE_TEXT)
    m['content_h'] = total(m)
    m['btn_w'] = 480          # 按钮宽度固定，窗口最小宽度已保证放得下
    return m


# ---------------------------------------------------------------- 现代化配色
class Theme:
    """现代化配色：蓝紫渐变系，毛玻璃风格"""
    # 背景渐变（蓝紫 → 浅蓝）
    BG_TOP = (30, 58, 138)         # 深蓝紫
    BG_BOTTOM = (147, 197, 253)    # 浅天蓝

    # 卡片背景（毛玻璃白，带透明度）
    CARD_BG = (255, 255, 255, 230)
    CARD_SHADOW = (0, 0, 0, 40)

    # 主色调
    PRIMARY = (99, 102, 241)       # 靛蓝 #6366f1
    PRIMARY_LIGHT = (129, 140, 248)
    PRIMARY_DARK = (79, 70, 229)

    # 强调色
    ACCENT = (244, 114, 182)       # 粉
    ACCENT2 = (52, 211, 153)       # 翠绿
    ACCENT3 = (251, 191, 36)       # 金黄
    ACCENT4 = (239, 68, 68)        # 红
    ACCENT5 = (14, 165, 233)       # 天蓝

    # 文字色
    TEXT_DARK = (30, 41, 59)
    TEXT_MID = (71, 85, 105)
    TEXT_LIGHT = (148, 163, 184)
    TEXT_WHITE = (255, 255, 255)

    # 按钮颜色（每个按钮专属渐变色）
    BTN_COLORS = {
        'spell':   ((99, 102, 241), (139, 92, 246)),   # 靛蓝 → 紫
        'study':   ((52, 211, 153), (16, 185, 129)),   # 翠绿
        'game':    ((251, 146, 60), (239, 68, 68)),     # 橙 → 红
        'explain': ((14, 165, 233), (59, 130, 246)),   # 天蓝 → 蓝
        'note':    ((244, 114, 182), (236, 72, 153)),  # 粉
    }

    BTN_ICONS = {
        'spell': '✍',
        'study': '📖',
        'game': '🎮',
        'explain': '🔤',
        'note': '📝',
    }


# ---------------------------------------------------------------- 粒子系统
class Particle:
    """背景浮动粒子"""
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.reset()
        self.y = random.uniform(0, h)  # 初始随机分布

    def reset(self):
        self.x = random.uniform(0, self.w)
        self.y = self.h + random.uniform(10, 50)
        self.r = random.uniform(2, 6)
        self.speed = random.uniform(0.3, 1.2)
        self.drift = random.uniform(-0.3, 0.3)
        self.alpha = random.uniform(60, 140)
        self.pulse = random.uniform(0, math.pi * 2)
        self.pulse_speed = random.uniform(0.02, 0.05)

    def update(self):
        self.y -= self.speed
        self.x += self.drift + math.sin(self.pulse) * 0.2
        self.pulse += self.pulse_speed
        if self.y < -10 or self.x < -20 or self.x > self.w + 20:
            self.reset()


# ---------------------------------------------------------------- 涟漪效果
class Ripple:
    """点击涟漪动画"""
    def __init__(self, x, y, max_r=120):
        self.x = x
        self.y = y
        self.r = 0
        self.max_r = max_r
        self.alpha = 180
        self.done = False

    def update(self):
        self.r += 6
        self.alpha = max(0, int(180 * (1 - self.r / self.max_r)))
        if self.r >= self.max_r:
            self.done = True


# ---------------------------------------------------------------- 配置对话框（现代化）
class ConfigDialog(wx.Dialog):
    def __init__(self, parent, libs, selected):
        super().__init__(parent, title=u'选择词库', size=(460, 480))
        self.SetBackgroundColour(wx.Colour(248, 250, 252))

        panel = wx.Panel(self)
        panel.SetBackgroundColour(wx.Colour(248, 250, 252))
        outer = wx.BoxSizer(wx.VERTICAL)

        # 标题区
        title = wx.StaticText(panel, label=u'📚 选择词库')
        f = title.GetFont()
        f.SetPointSize(f.GetPointSize() + 8)
        f.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(f)
        title.SetForegroundColour(wx.Colour(*Theme.TEXT_DARK))
        outer.Add(title, 0, wx.ALL, 20)

        sub = wx.StaticText(panel, label=u'勾选你想学习的词库，题目将从所选词库中抽取')
        f2 = sub.GetFont()
        f2.SetPointSize(f2.GetPointSize() + 1)
        sub.SetFont(f2)
        sub.SetForegroundColour(wx.Colour(*Theme.TEXT_LIGHT))
        outer.Add(sub, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 20)

        # 滚动区
        scrolled = wx.ScrolledWindow(panel, style=wx.VSCROLL)
        scrolled.SetScrollRate(0, 20)
        scrolled.SetBackgroundColour(wx.Colour(255, 255, 255))
        inner = wx.BoxSizer(wx.VERTICAL)

        self.checkboxes = []
        for i, (name, path, count) in enumerate(libs):
            row = wx.Panel(scrolled)
            row.SetBackgroundColour(wx.Colour(255, 255, 255))
            rs = wx.BoxSizer(wx.HORIZONTAL)

            cb = wx.CheckBox(row, label=u'')
            cb.SetValue(name in selected)
            rs.Add(cb, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 12)

            # 词库名
            lbl = wx.StaticText(row, label=name)
            fl = lbl.GetFont()
            fl.SetPointSize(fl.GetPointSize() + 2)
            lbl.SetFont(fl)
            lbl.SetForegroundColour(wx.Colour(*Theme.TEXT_DARK))
            rs.Add(lbl, 1, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

            # 词数徽章
            badge = wx.StaticText(row, label=u'%d 词' % count)
            fb = badge.GetFont()
            fb.SetPointSize(fb.GetPointSize())
            badge.SetFont(fb)
            badge.SetForegroundColour(wx.Colour(*Theme.PRIMARY))
            badge.SetBackgroundColour(wx.Colour(238, 242, 255))
            rs.Add(badge, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)

            row.SetSizer(rs)
            inner.Add(row, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 4)
            self.checkboxes.append((cb, name))

            # 分隔线
            if i < len(libs) - 1:
                line = wx.Panel(scrolled, size=(-1, 1))
                line.SetBackgroundColour(wx.Colour(241, 245, 249))
                inner.Add(line, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        scrolled.SetSizer(inner)
        outer.Add(scrolled, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 20)

        # 按钮区
        btns = wx.BoxSizer(wx.HORIZONTAL)
        self.refuse = wx.Button(panel, REFUSE_CONFIG_BUTTON, u'取消')
        self.refuse.SetBackgroundColour(wx.Colour(241, 245, 249))
        self.refuse.SetForegroundColour(wx.Colour(*Theme.TEXT_DARK))
        btns.Add(self.refuse, 0, wx.RIGHT, 10)

        self.accept = wx.Button(panel, ACCEPT_CONFIG_BUTTON, u'开始学习')
        self.accept.SetBackgroundColour(wx.Colour(*Theme.PRIMARY))
        self.accept.SetForegroundColour(wx.Colour(255, 255, 255))
        btns.Add(self.accept, 0)
        outer.Add(btns, 0, wx.ALIGN_RIGHT | wx.ALL, 20)

        panel.SetSizer(outer)
        self.Bind(wx.EVT_BUTTON, self.onButton)
        self.CenterOnParent()

    def onButton(self, evt):
        if evt.GetId() == ACCEPT_CONFIG_BUTTON:
            self.EndModal(wx.ID_OK)
        elif evt.GetId() == REFUSE_CONFIG_BUTTON:
            self.EndModal(wx.ID_CANCEL)

    def get_selected(self):
        return {name for cb, name in self.checkboxes if cb.GetValue()}


# ---------------------------------------------------------------- 主窗口（现代化UI）
class mainFrame(wx.Frame):
    BUTTONS = (
        ('spell',   u'拼写测试',       'wordspell.png', 'start',   '看中文写英文，即时判分'),
        ('study',   u'单词学习',       'wordstudy.png', 'start3',  '卡片式浏览，边学边记'),
        ('game',    u'填字游戏',       'game.gif',      'start2',  '挖空选字母，爆炸特效'),
        ('explain', u'词义选择',       'explain.gif',   'start1',  '英文选中文释义'),
        ('note',    u'单词笔记',       'wordnote.gif',  'start4',  '艾宾浩斯复习计划'),
    )
    BTN_SIZE = (480, 72)
    BTN_RADIUS = 16
    BTN_GAP = 18

    def __init__(self):
        # 布局会随窗口高度自适应（见 _compute_metrics），所以放开尺寸限制：
        # 屏幕小的机器可以自己拉大或最大化，不会再有内容被裁在画面外。
        wx.Frame.__init__(self, None, -1, APP_TITLE, style=wx.DEFAULT_FRAME_STYLE)
        self.SetSize((900, 720))
        self.SetMinSize((740, 560))
        self.Center()

        # 自适应布局缓存（窗口尺寸不变就不重算）
        self._m = None
        self._m_key = None

        if APP_ICON.is_file():
            self.SetIcon(wx.Icon(str(APP_ICON), wx.BITMAP_TYPE_ICO))

        self.libs = load_libs()
        self.selected = load_selected(self.libs)

        # 动画状态
        self.particles = []
        self.ripples = []
        self.title_phase = 0.0
        self.btn_hover = None       # 当前悬停的按钮 key
        self.btn_pressed = None
        self.btn_alpha = {key: 0.0 for key, *_ in self.BUTTONS}  # 入场动画透明度
        self.btn_y_offset = {key: 30.0 for key, *_ in self.BUTTONS}
        self.enter_start = time.time()
        self.animating = True

        # 绘制面板（全自绘）
        self.canvas = wx.Panel(self, size=self.GetClientSize())
        self.canvas.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.canvas.Bind(wx.EVT_PAINT, self.on_paint)
        self.canvas.Bind(wx.EVT_SIZE, self.on_size)
        self.canvas.Bind(wx.EVT_MOTION, self.on_motion)
        self.canvas.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.canvas.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.canvas.Bind(wx.EVT_LEAVE_WINDOW, lambda e: self.set_hover(None))

        # 让画布自动铺满窗口：拉大/最大化时画布跟着变，布局随之重排
        _sizer = wx.BoxSizer(wx.VERTICAL)
        _sizer.Add(self.canvas, 1, wx.EXPAND)
        self.SetSizer(_sizer)

        # 菜单栏（隐藏默认，画自定义菜单按钮）
        self.menubar = wx.MenuBar()
        self.menuFile = wx.Menu()
        self.menuEdit = wx.Menu()
        self.menuEdit.Append(CONFIG_MENU, u'配置词库')
        self.menuFile.AppendSubMenu(self.menuEdit, u'编辑')
        self.menuFile.Append(QUIT_MENU, u'退出')
        self.menubar.Append(self.menuFile, u'文件')
        self.SetMenuBar(self.menubar)
        self.Bind(wx.EVT_MENU, self.menuHandler)

        # 初始化粒子
        w, h = self.GetClientSize()
        self.particles = [Particle(w, h) for _ in range(40)]

        # 定时器：60fps 动画
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_tick, self.timer)
        self.timer.Start(16)  # ~60fps

        # 按内容把窗口调到合适大小（不再写死 720 把底部按钮裁掉）
        self._fit_window()
        self.refreshInfo()

    # ---------------- 窗口尺寸自适应 ----------------
    def _content_height(self):
        """理想尺寸下，内容一共需要多高（用于决定窗口默认高度）。"""
        try:
            dc = wx.ClientDC(self.canvas)
            return _compute_metrics(dc, 10 ** 6, len(self.BUTTONS))['content_h']
        except Exception:
            return 760

    def _fit_window(self):
        """把窗口调到刚好放下全部内容，同时不超出屏幕可用区域。

        之前固定 900x720：客户区只有约 695px，而标题+副标题+3 张卡片+
        5 个 72px 按钮+版本号需要约 785px，于是最后一个按钮和版本号被裁掉。
        这里改为「按内容算高度」，装不下时 _compute_metrics 还会继续压缩。
        """
        want = self._content_height()
        size = self.GetSize()
        client = self.GetClientSize()
        chrome = max(0, size.height - client.height)   # 菜单栏 + 标题栏

        area = wx.Display().GetClientArea()
        max_h = max(480, area.height - 40)
        min_h = 560
        h = int(min(max(want + chrome + 8, min_h), max_h))

        w = 900
        if area.width - 60 < w:
            w = max(740, area.width - 60)
        self.SetSize((w, h))
        self.SetMinSize((min(740, w), min(560, h)))
        self.Center()

    def on_size(self, event):
        # canvas 由 sizer 自动铺满窗口，这里只同步粒子并重绘；
        # 布局尺寸在 on_paint 里按当前高度重算（_m_key 变化即重算）
        w, h = self.canvas.GetClientSize()
        for p in self.particles:
            p.w, p.h = w, h
        if len(self.particles) < 40 and w > 0:
            for _ in range(40 - len(self.particles)):
                self.particles.append(Particle(w, h))
        self.Refresh()
        event.Skip()

    def on_tick(self, event):
        # 入场动画
        t = time.time() - self.enter_start
        for i, (key, *_rest) in enumerate(self.BUTTONS):
            delay = i * 0.08
            progress = max(0.0, min(1.0, (t - delay) / 0.5))
            # ease-out cubic
            eased = 1 - (1 - progress) ** 3
            self.btn_alpha[key] = eased
            self.btn_y_offset[key] = 30 * (1 - eased)

        # 标题呼吸
        self.title_phase += 0.03

        # 粒子更新
        w, h = self.GetClientSize()
        for p in self.particles:
            p.w, p.h = w, h
            p.update()

        # 涟漪更新
        alive = []
        for r in self.ripples:
            r.update()
            if not r.done:
                alive.append(r)
        self.ripples = alive

        self.Refresh()

    # ---------------- 绘制 ----------------
    def _lerp_color(self, c1, c2, t):
        return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

    def _draw_gradient_bg(self, gc, w, h):
        """绘制蓝紫渐变背景"""
        ctx = gc.GetGraphicsContext() if hasattr(gc, 'GetGraphicsContext') else None
        if ctx:
            # 用 GDI+ 画真正的渐变
            brush = ctx.CreateLinearGradientBrush(0, 0, 0, h,
                                                  wx.Colour(*Theme.BG_TOP),
                                                  wx.Colour(*Theme.BG_BOTTOM))
            ctx.SetBrush(brush)
            ctx.DrawRectangle(0, 0, w, h)
        else:
            # 退化方案：分段填充
            steps = 64
            for i in range(steps):
                t = i / steps
                c = self._lerp_color(Theme.BG_TOP, Theme.BG_BOTTOM, t)
                gc.SetBrush(wx.Brush(wx.Colour(*c)))
                gc.SetPen(wx.TRANSPARENT_PEN)
                gc.DrawRectangle(0, int(h * i / steps), w, int(h / steps) + 2)

    def _draw_particles(self, gc, w, h):
        ctx = gc.GetGraphicsContext() if hasattr(gc, 'GetGraphicsContext') else None
        for p in self.particles:
            r = p.r * (0.8 + 0.2 * math.sin(p.pulse))
            a = int(p.alpha * (0.7 + 0.3 * math.sin(p.pulse)))
            color = wx.Colour(255, 255, 255, a)
            if ctx:
                ctx.SetBrush(ctx.CreateBrush(wx.Brush(color)))
                ctx.DrawEllipse(p.x - r, p.y - r, r * 2, r * 2)
            else:
                gc.SetBrush(wx.Brush(wx.Colour(255, 255, 255)))
                gc.DrawCircle(int(p.x), int(p.y), int(r))

    def _draw_title(self, gc, w):
        """大标题：18单词，呼吸动画 + 渐变字"""
        ctx = gc.GetGraphicsContext() if hasattr(gc, 'GetGraphicsContext') else None

        m = self._m
        # 标题：字号带呼吸动画，但排版按固定高度 title_h 算，
        # 否则字号每帧变化会把下面的卡片和按钮一起推得上下抖
        title = TITLE_TEXT
        ty = m['pad_top']
        font_size = m['title_size'] + int(2 * math.sin(self.title_phase))
        font = wx.Font(font_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                       wx.FONTWEIGHT_BOLD, faceName='Microsoft YaHei UI')
        gc.SetFont(font)
        tw, th = gc.GetTextExtent(title)
        tx = (w - tw) / 2
        ty_text = ty + (m['title_h'] - th) / 2

        # 标题阴影
        gc.SetTextForeground(wx.Colour(0, 0, 0, 40))
        gc.DrawText(title, tx + 2, ty_text + 3)

        # 标题主色（白）
        gc.SetTextForeground(wx.Colour(255, 255, 255, 250))
        gc.DrawText(title, tx, ty_text)

        # 副标题
        sub_font = wx.Font(m['sub_size'], wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                           wx.FONTWEIGHT_NORMAL, faceName='Microsoft YaHei UI')
        gc.SetFont(sub_font)
        gc.SetTextForeground(wx.Colour(255, 255, 255, 200))
        sub_y = ty + m['title_h'] + 10
        sw, sh = gc.GetTextExtent(SUBTITLE_TEXT)
        gc.DrawText(SUBTITLE_TEXT, (w - sw) / 2, sub_y)

        return sub_y + sh + m['g_title_card']   # 返回标题区底部 y

    def _draw_info_card(self, gc, w, top_y):
        """顶部信息卡：已选词库/总词数/笔记数"""
        total = sum(c for n, _, c in self.libs if n in self.selected)
        picked_count = len(self.selected)
        note_count = self._get_note_count()

        cards = [
            (u'已选词库', str(picked_count), u'个', Theme.ACCENT5),
            (u'单词总数', str(total), u'词', Theme.PRIMARY),
            (u'我的笔记', str(note_count), u'词', Theme.ACCENT),
        ]

        m = self._m
        card_w = 140
        card_h = m['card_h']          # 高度随窗口自适应，宽度固定
        gap = 20
        radius = max(8, int(card_h * 0.15))
        # 字号随卡片高度等比缩放，卡片被压矮时文字不会溢出卡片
        num_size = max(18, int(card_h * 0.33))
        unit_size = max(9, int(card_h * 0.15))
        lbl_size = max(9, int(card_h * 0.14))
        total_w = card_w * 3 + gap * 2
        start_x = (w - total_w) / 2
        cy = top_y

        for i, (label, num, unit, color) in enumerate(cards):
            cx = start_x + i * (card_w + gap)

            # 卡片阴影
            ctx = gc.GetGraphicsContext() if hasattr(gc, 'GetGraphicsContext') else None
            if ctx:
                shadow = wx.Colour(0, 0, 0, 25)
                ctx.SetBrush(ctx.CreateBrush(wx.Brush(shadow)))
                ctx.DrawRoundedRectangle(cx + 3, cy + 5, card_w, card_h, radius)
                # 卡片本体（半透明白）
                bg = wx.Colour(255, 255, 255, 210)
                ctx.SetBrush(ctx.CreateBrush(wx.Brush(bg)))
                ctx.SetPen(wx.TRANSPARENT_PEN)
                ctx.DrawRoundedRectangle(cx, cy, card_w, card_h, radius)
                # 左侧色条
                bar = wx.Colour(*color, 255)
                ctx.SetBrush(ctx.CreateBrush(wx.Brush(bar)))
                ctx.DrawRoundedRectangle(cx, cy, 4, card_h, 2)
            else:
                gc.SetBrush(wx.Brush(wx.Colour(255, 255, 255)))
                gc.DrawRoundedRectangle(int(cx), int(cy), card_w, card_h, radius)

            # 数字
            num_font = wx.Font(num_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                               wx.FONTWEIGHT_BOLD, faceName='Microsoft YaHei UI')
            gc.SetFont(num_font)
            gc.SetTextForeground(wx.Colour(*color))
            nw, nh = gc.GetTextExtent(num)
            num_y = cy + max(6, int(card_h * 0.15))
            gc.DrawText(num, cx + 20, num_y)
            # 单位
            unit_font = wx.Font(unit_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                wx.FONTWEIGHT_NORMAL, faceName='Microsoft YaHei UI')
            gc.SetFont(unit_font)
            gc.SetTextForeground(wx.Colour(*Theme.TEXT_LIGHT))
            gc.DrawText(unit, cx + 20 + nw + 4, num_y + int(card_h * 0.2))

            # 标签（贴着卡片底部排，卡片变矮也不会跑出去）
            lbl_font = wx.Font(lbl_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                               wx.FONTWEIGHT_NORMAL, faceName='Microsoft YaHei UI')
            gc.SetFont(lbl_font)
            gc.SetTextForeground(wx.Colour(*Theme.TEXT_MID))
            gc.DrawText(label, cx + 20, cy + card_h - lbl_size - 10)

        return cy + card_h + m['g_card_btn']

    def _get_note_count(self):
        try:
            import word_note
            data = word_note.load_data()
            return len(data)
        except Exception:
            return 0

    def _draw_buttons(self, gc, w, top_y):
        """绘制毛玻璃卡片按钮"""
        m = self._m
        ctx = gc.GetGraphicsContext() if hasattr(gc, 'GetGraphicsContext') else None
        btn_w, btn_h = m['btn_w'], m['btn_h']   # 高度与间距随窗口自适应
        gap = m['btn_gap']
        radius = max(10, int(btn_h * 0.22))
        # 图标与两行文字按按钮高度等比缩放，按钮被压矮时不会溢出按钮
        icon_size = max(18, int(btn_h * 0.42))
        title_size = max(13, int(btn_h * 0.24))
        desc_size = max(9, int(btn_h * 0.15))
        text_x = max(56, int(btn_w * 0.19))
        start_y = top_y
        btn_rects = {}

        for i, (key, label, icon_file, handler, desc) in enumerate(self.BUTTONS):
            bx = (w - btn_w) / 2
            by = start_y + i * (btn_h + gap) + self.btn_y_offset[key]
            alpha = self.btn_alpha[key]

            is_hover = (self.btn_hover == key)
            is_press = (self.btn_pressed == key)
            ready = self._is_btn_ready(key)

            c1, c2 = Theme.BTN_COLORS[key]
            if not ready:
                c1 = (180, 180, 180)
                c2 = (150, 150, 150)

            # 放大效果（悬停时）
            scale = 1.03 if is_hover else 1.0
            scale = 0.98 if is_press else scale
            extra_w = btn_w * (scale - 1) / 2
            extra_h = btn_h * (scale - 1) / 2
            rx = bx - extra_w
            ry = by - extra_h
            rw = btn_w + extra_w * 2
            rh = btn_h + extra_h * 2

            if alpha < 0.01:
                btn_rects[key] = (int(bx), int(by), btn_w, btn_h, ready, handler)
                continue

            # 整体透明度
            gc_cut = None
            if alpha < 1.0 and ctx:
                pass  # wx 对全局透明度支持有限，用颜色逼近

            # 阴影（悬停时更深更大）
            shadow_alpha = 30 + (25 if is_hover else 0)
            shadow_offset = 4 + (3 if is_hover else 0)
            if ctx:
                sh = wx.Colour(0, 0, 0, int(shadow_alpha * alpha))
                ctx.SetBrush(ctx.CreateBrush(wx.Brush(sh)))
                ctx.SetPen(wx.TRANSPARENT_PEN)
                ctx.DrawRoundedRectangle(rx + 2, ry + shadow_offset, rw, rh, radius)

            # 按钮渐变
            if ctx:
                # 渐变底色
                if is_hover or is_press:
                    c1b = self._lerp_color(c1, (255, 255, 255), 0.15 if not is_press else -0.1)
                    c2b = self._lerp_color(c2, (255, 255, 255), 0.15 if not is_press else -0.1)
                else:
                    c1b = c1
                    c2b = c2
                brush = ctx.CreateLinearGradientBrush(rx, ry, rx, ry + rh,
                                                      wx.Colour(*c1b),
                                                      wx.Colour(*c2b))
                ctx.SetBrush(brush)
                ctx.SetPen(wx.TRANSPARENT_PEN)
                ctx.DrawRoundedRectangle(rx, ry, rw, rh, radius)

                # 高光（顶部一条亮边）
                hi = wx.Colour(255, 255, 255, 60 if is_hover else 40)
                ctx.SetBrush(ctx.CreateBrush(wx.Brush(hi)))
                ctx.DrawRoundedRectangle(rx + 2, ry + 1, rw - 4, rh / 2, radius - 2)
            else:
                gc.SetBrush(wx.Brush(wx.Colour(*c1)))
                gc.DrawRoundedRectangle(int(rx), int(ry), int(rw), int(rh), radius)

            # 涟漪
            for ripple in self.ripples:
                if hasattr(ripple, 'btn_key') and ripple.btn_key == key:
                    ra = int(ripple.alpha * alpha)
                    ripple_color = wx.Colour(255, 255, 255, ra)
                    if ctx:
                        ctx.SetBrush(ctx.CreateBrush(wx.Brush(ripple_color)))
                        ctx.DrawEllipse(rx + ripple.x - ripple.r,
                                        ry + ripple.y - ripple.r,
                                        ripple.r * 2, ripple.r * 2)

            # 图标（emoji 字符）
            icon_char = Theme.BTN_ICONS.get(key, '●')
            icon_font = wx.Font(icon_size + (2 if is_hover else 0),
                                wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                wx.FONTWEIGHT_NORMAL)
            gc.SetFont(icon_font)
            gc.SetTextForeground(wx.Colour(255, 255, 255))
            iw, ih = gc.GetTextExtent(icon_char)
            ix = rx + max(18, int(rw * 0.06))
            iy = ry + (rh - ih) / 2
            gc.DrawText(icon_char, int(ix), int(iy))

            # 标题
            title_font = wx.Font(title_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                 wx.FONTWEIGHT_BOLD, faceName='Microsoft YaHei UI')
            gc.SetFont(title_font)
            gc.SetTextForeground(wx.Colour(255, 255, 255))
            tw, th = gc.GetTextExtent(label)
            tx = rx + text_x
            ty = ry + (rh - th) / 2 - th * 0.45
            gc.DrawText(label, int(tx), int(ty))

            # 描述
            desc_font = wx.Font(desc_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                wx.FONTWEIGHT_NORMAL, faceName='Microsoft YaHei UI')
            gc.SetFont(desc_font)
            gc.SetTextForeground(wx.Colour(255, 255, 255, 200))
            gc.DrawText(desc, int(tx), int(ty + th + max(2, int(rh * 0.08))))

            btn_rects[key] = (int(bx), int(by), btn_w, btn_h, ready, handler)

        # 底部小字：紧跟在最后一个按钮下面
        ver = u'v3.0 · 现代化界面'
        vfont = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                        wx.FONTWEIGHT_NORMAL)
        gc.SetFont(vfont)
        gc.SetTextForeground(wx.Colour(255, 255, 255, 120))
        vw, vh = gc.GetTextExtent(ver)
        ver_y = start_y + len(self.BUTTONS) * btn_h + (len(self.BUTTONS) - 1) * gap + 10
        gc.DrawText(ver, int((w - vw) / 2), int(ver_y))

        self.btn_rects = btn_rects
        return ver_y + vh

    def _draw_top_bar(self, gc, w):
        """右上角：配置词库按钮"""
        ctx = gc.GetGraphicsContext() if hasattr(gc, 'GetGraphicsContext') else None
        btn_text = u'⚙ 配置词库'
        btn_w, btn_h = 120, 36
        bx = w - btn_w - 20
        by = 20
        # 半透明白色按钮
        if ctx:
            bg = wx.Colour(255, 255, 255, 50 if self._cfg_hover else 80)
            ctx.SetBrush(ctx.CreateBrush(wx.Brush(bg)))
            ctx.SetPen(wx.Pen(wx.Colour(255, 255, 255, 80), 1))
            ctx.DrawRoundedRectangle(bx, by, btn_w, btn_h, 18)
        else:
            gc.SetBrush(wx.Brush(wx.Colour(255, 255, 255)))
            gc.DrawRoundedRectangle(bx, by, btn_w, btn_h, 18)
        font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                       wx.FONTWEIGHT_NORMAL, faceName='Microsoft YaHei UI')
        gc.SetFont(font)
        gc.SetTextForeground(wx.Colour(255, 255, 255))
        tw, th = gc.GetTextExtent(btn_text)
        gc.DrawText(btn_text, int(bx + (btn_w - tw) / 2), int(by + (btn_h - th) / 2 - 1))

        # 左上角标题小标
        logo = u'EN'
        lfont = wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                        wx.FONTWEIGHT_BOLD)
        gc.SetFont(lfont)
        gc.SetTextForeground(wx.Colour(255, 255, 255, 180))
        gc.DrawText(logo, 24, 24)

        self.cfg_btn_rect = (int(bx), int(by), btn_w, btn_h)

    _cfg_hover = False

    def on_paint(self, event):
        w, h = self.canvas.GetClientSize()
        if w <= 0 or h <= 0:
            return

        # 全部图层先画到离屏位图，再一次性贴到窗口（自己做了双缓冲，不闪）。
        # 关键：wx.GCDC 只接受 wx.DC 家族的“真实” DC（MemoryDC / PaintDC ...），
        # 传 AutoBufferedPaintDC 会抛 TypeError，所以这里用 MemoryDC 包 GCDC。
        buf = wx.Bitmap(w, h)
        mdc = wx.MemoryDC(buf)
        try:
            try:
                gc = _CoerceIntGC(wx.GCDC(mdc))
            except Exception:
                gc = _CoerceIntGC(mdc)       # 极老的 wx 没有 GCDC，降级
            # 先按当前窗口高度算出整套布局尺寸；窗口尺寸没变就直接复用缓存
            if self._m_key != (w, h):
                self._m = _compute_metrics(gc, h, len(self.BUTTONS))
                self._m_key = (w, h)
            self._paint_all(gc, w, h)
        finally:
            mdc.SelectObject(wx.NullBitmap)

        dc = wx.PaintDC(self.canvas)
        dc.DrawBitmap(buf, 0, 0, False)

    def _paint_all(self, gc, w, h):
        """所有图层依次画到 gc 上。

        每层单独兜住异常：某一层画崩了（不同 wx / 显卡驱动对 GDI+ 的支持
        有差异），其余图层照常显示，不会因为一个图元把整个界面弄成空白。
        """
        def safe(fn, *a):
            try:
                return fn(*a)
            except Exception as exc:
                print('绘制图层 %s 失败: %s' % (getattr(fn, '__name__', fn), exc))
                return None

        if self._m is None:
            self._m = _compute_metrics(gc, h, len(self.BUTTONS))

        safe(self._draw_gradient_bg, gc, w, h)                 # 背景渐变
        safe(self._draw_particles, gc, w, h)                   # 粒子
        safe(self._draw_top_bar, gc, w)                        # 顶栏

        # 各区块自上而下依次排列，每个 _draw_* 返回自己区块的底部 y，
        # 间距全部来自 _m，所以窗口多高都能刚好铺满、不留大块空白也不溢出。
        bottom = safe(self._draw_title, gc, w) or 120          # 标题 + 副标题
        bottom = safe(self._draw_info_card, gc, w, bottom) or (bottom + 90)
        safe(self._draw_buttons, gc, w, bottom)                # 功能按钮 + 版本号

    # ---------------- 交互 ----------------
    def _is_btn_ready(self, key):
        ready = bool(self.libs and self.selected)
        if key in ('note', 'game', 'explain'):
            return True
        return ready

    def _hit_test(self, x, y):
        """命中测试：返回 key 或 'config' 或 None"""
        if hasattr(self, 'cfg_btn_rect'):
            bx, by, bw, bh = self.cfg_btn_rect
            if bx <= x <= bx + bw and by <= y <= by + bh:
                return 'config'
        if hasattr(self, 'btn_rects'):
            for key, (bx, by, bw, bh, ready, handler) in self.btn_rects.items():
                if bx <= x <= bx + bw and by <= y <= by + bh:
                    return key
        return None

    def set_hover(self, key):
        if self.btn_hover != key:
            self.btn_hover = key
            self.canvas.SetCursor(wx.Cursor(wx.CURSOR_HAND) if key else wx.NullCursor)
            self.Refresh()

    def on_motion(self, event):
        x, y = event.GetX(), event.GetY()
        hit = self._hit_test(x, y)

        self._cfg_hover = (hit == 'config')

        if hit and hit not in ('config',):
            self.set_hover(hit)
        else:
            self.set_hover(None)
        # 配置按钮悬停也刷新
        self.Refresh()
        event.Skip()

    def on_left_down(self, event):
        x, y = event.GetX(), event.GetY()
        hit = self._hit_test(x, y)
        if hit == 'config':
            self.btn_pressed = 'config'
        elif hit and hit not in ('config',):
            self.btn_pressed = hit
            bx, by, bw, bh, ready, handler = self.btn_rects[hit]
            # 创建涟漪
            r = Ripple(x - bx, y - by, max_r=max(bw, bh) * 0.8)
            r.btn_key = hit
            self.ripples.append(r)
        self.Refresh()
        event.Skip()

    def on_left_up(self, event):
        x, y = event.GetX(), event.GetY()
        hit = self._hit_test(x, y)
        pressed = self.btn_pressed
        self.btn_pressed = None

        if hit == 'config' and pressed == 'config':
            self.open_config()
        elif hit and hit not in ('config',) and pressed == hit:
            bx, by, bw, bh, ready, handler = self.btn_rects[hit]
            if ready and hasattr(self, handler):
                getattr(self, handler)(None)
        self.Refresh()
        event.Skip()

    def open_config(self):
        dlg = ConfigDialog(self, self.libs, self.selected)
        if dlg.ShowModal() == wx.ID_OK:
            self.selected = dlg.get_selected()
            self.refreshInfo()
        dlg.Destroy()

    def refreshInfo(self):
        # 没词库/没选词库时按钮置灰由 _is_btn_ready 动态计算
        if hasattr(self, 'canvas'):
            self.canvas.Refresh()
        save_selected(self.libs, self.selected)

    # ---------------- 五个入口 ----------------
    def start(self, event):
        self.launch(spell.run, u'拼写测试', names=sorted(self.selected))

    def start1(self, event):
        self.launch(explain.run, u'单词翻译测试')

    def start2(self, event):
        self.launch(word_game_tkinter.run, u'填单词游戏')

    def start3(self, event):
        self.launch(new_word_study.run, u'学习单词', T=spell.load_words2(sorted(self.selected)))

    def start4(self, event):
        self.launch(word_note.run, u'单词笔记')

    def launch(self, func, what, **kwargs):
        if tk is None or not spell.available():
            self.warn_tk(what)
            return
        if spell.has_window():
            spell.focus_window()
            return
        try:
            func(**kwargs)
        except spell.NoWordsError as exc:
            wx.MessageBox(str(exc), u'没有可用词库', wx.ICON_WARNING, self)
        except Exception as exc:
            wx.MessageBox(u'打开「%s」失败：\n%s' % (what, exc),
                          u'出错了', wx.ICON_ERROR, self)

    def warn_tk(self, what):
        wx.MessageBox(u'「%s」需要标准库 tkinter，\n当前 Python 没有装，请先安装后再试。' % what,
                      u'无法开始', wx.ICON_WARNING, self)

    def menuHandler(self, evt):
        if evt.GetId() == QUIT_MENU:
            self.Close()
        elif evt.GetId() == CONFIG_MENU:
            self.open_config()


class mainApp(wx.App):
    def OnInit(self):
        self.SetAppName(APP_TITLE)
        self.Frame = mainFrame()
        self.Frame.Show()
        return True


if __name__ == '__main__':
    with open(BASE_DIR / 'debug.txt', 'w+', encoding='utf-8'):
        pass
    app = mainApp(redirect=True, filename=str(BASE_DIR / 'debug.txt'))
    app.MainLoop()
