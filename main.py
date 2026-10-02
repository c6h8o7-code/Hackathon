# -*- coding: utf-8 -*-

"""十八单词 —— 英语词汇记忆工具（第二代）

词库放在 ./dev_english/ 目录下，一个 .json 文件即一个词库，
文件名（去掉 .json）就是词库名。运行方式：

    pip install wxPython
    python 十八单词.py

主界面五个入口分别对应 spell / new_word_study / word_game_tkinter /
explain / word_note 五个模块，题目从「配置词库」里勾选的词库中抽取。
"""

import json

import A
import spell
import explain
import word_game_tkinter
import word_note
import new_word_study

try:
    import tkinter as tk
except ImportError:          # 缺少 tkinter 时主窗口仍可正常使用
    tk = None

import wx

APP_TITLE = u'十八单词'

# 路径都交给 A 处理：开发时是脚本目录，打包成 exe 后是 exe 所在目录
BASE_DIR = A.app_dir()
APP_ICON = A.resource('icon.ico')
LIB_DIR = A.ensure_lib_dir('dev_english')
LATEST = BASE_DIR / 'latest.json'
RESOURCE = BASE_DIR / "res"          # 主界面按钮图标放在 res/ 下
BANNER = A.resource('18单词第二代图标.gif')
# BUTTON ID
ACCEPT_CONFIG_BUTTON = 1
REFUSE_CONFIG_BUTTON = 2
# MENU ID
QUIT_MENU = 0
CONFIG_MENU = 1
EDIT_MENU = 2

QUIZ_SIZE = 20


# ---------------------------------------------------------------- 词库读取
# 菜单里想看到的先后顺序；不在表里的词库按名称排在后面
LIB_ORDER = ['初一', '初二', '初三',
             '必修第一册', '必修第二册', '必修第三册',
             '选择性必修第一册', '选择性必修第二册',
             '选择性必修第三册', '选择性必修第四册']


def _lib_key(path):
    stem = path.stem
    return (LIB_ORDER.index(stem) if stem in LIB_ORDER else len(LIB_ORDER), stem)


def load_libs():
    """扫描 dev_english 目录，返回 [(词库名, 文件路径, 单词总数), ...]"""
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
    """读上次勾选的词库；文件缺失或损坏时默认全选。"""
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
    """把勾选结果写回 latest.json，下次启动沿用。"""
    data = {n: 1 for n, _, _ in libs if n in selected}
    try:
        LATEST.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                          encoding='utf-8')
    except OSError as exc:
        print('保存 latest.json 失败: %s' % exc)


# ---------------------------------------------------------------- 词库选择对话框
class ConfigDialog(wx.Dialog):
    """勾选需要加载的词库"""

    def __init__(self, parent, libs, selected):
        super().__init__(parent, title=u'选择词库', size=(420, 380))

        panel = wx.Panel(self)
        outer = wx.BoxSizer(wx.VERTICAL)

        outer.Add(wx.StaticText(panel, label=u'请勾选要学习的词库：'),
                  0, wx.ALL, 10)

        # 词库多时用滚动窗口，避免勾选框被挤出可视区
        scrolled = wx.ScrolledWindow(panel, style=wx.VSCROLL | wx.BORDER_SIMPLE)
        scrolled.SetScrollRate(0, 20)
        inner = wx.BoxSizer(wx.VERTICAL)

        self.checkboxes = []
        for name, path, count in libs:
            cb = wx.CheckBox(scrolled, label=u'%s（%d 词）' % (name, count))
            cb.SetValue(name in selected)
            inner.Add(cb, 0, wx.ALL, 6)
            self.checkboxes.append((cb, name))
        scrolled.SetSizer(inner)

        outer.Add(scrolled, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # 确定 / 取消
        btns = wx.BoxSizer(wx.HORIZONTAL)
        self.accept = wx.Button(panel, ACCEPT_CONFIG_BUTTON, u'确定')
        self.refuse = wx.Button(panel, REFUSE_CONFIG_BUTTON, u'取消')
        btns.AddStretchSpacer()
        btns.Add(self.accept, 0, wx.RIGHT, 10)
        btns.Add(self.refuse, 0, wx.RIGHT, 10)
        outer.Add(btns, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(outer)
        self.Bind(wx.EVT_BUTTON, self.onButton)

    def onButton(self, evt):
        # 确定：把选中的词库名回传给主窗口；取消：什么也不改
        if evt.GetId() == ACCEPT_CONFIG_BUTTON:
            self.EndModal(wx.ID_OK)
        elif evt.GetId() == REFUSE_CONFIG_BUTTON:
            self.EndModal(wx.ID_CANCEL)

    def get_selected(self):
        return {name for cb, name in self.checkboxes if cb.GetValue()}


def flatten(lst):
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


# ---------------------------------------------------------------- 主窗口
class mainFrame(wx.Frame):
    '''程序主窗口类，继承自 wx.Frame'''

    # 主界面按钮：键、文案、图标文件、处理方法（顺序 = 界面上的先后顺序）
    BUTTONS = (
        ('spell',   u'开始拼写测试',                'wordspell.png', 'start'),
        ('study',   u'开始学习单词',                'wordstudy.png', 'start3'),
        ('game',    u'开始填单词游戏',              'game.gif',      'start2'),
        ('explain', u'开始单词翻译测试（固定100词）', 'explain.gif',   'start1'),
        ('note',    u'打开单词笔记',                    'wordnote.gif',  'start4'),
    )
    ICON_SIZE = 32              # 按钮上图标显示尺寸
    BTN_SIZE = (400, 52)        # 所有按钮统一尺寸，排列才整齐
    BTN_GAP = 16                # 按钮之间统一的垂直间距

    def __init__(self):

        '''构造函数'''
        wx.Frame.__init__(self, None, -1, APP_TITLE,
                          style=wx.DEFAULT_FRAME_STYLE & (~(wx.RESIZE_BORDER)) & (~wx.MAXIMIZE_BOX))
        self.SetBackgroundColour(wx.Colour(179, 224, 255))
        self.SetSize((800, 620))
        self.SetMinSize((800, 620))
        self.Center()
        self.t=0
        self.eX=0
        self.eY=0
        if APP_ICON.is_file():
            self.SetIcon(wx.Icon(str(APP_ICON), wx.BITMAP_TYPE_ICO))

        self.libs = load_libs()
        self.selected = load_selected(self.libs)
        self.setWidgets()
        self.Bind(wx.EVT_MENU, self.menuHandler)

    def setWidgets(self):
        '''设置控件'''
        # ---------------- 菜单栏 ----------------
        self.menubar = wx.MenuBar()
        self.menuFile = wx.Menu()
        self.menuEdit = wx.Menu()
        self.menuEdit.Append(CONFIG_MENU, u'配置词库')
        self.menuFile.AppendSubMenu(self.menuEdit, u'编辑')
        self.menuFile.Append(QUIT_MENU, u'退出(Alt+F4)')
        self.menubar.Append(self.menuFile, u'文件')
        self.SetMenuBar(self.menubar)

        # ---------------- 正文 ----------------
        # 全部交给 Sizer 排版：不再用 pos= 绝对定位（绝对定位和 Sizer 混用会错位）
        panel = wx.Panel(self)
        panel.Bind(wx.EVT_BUTTON, self.activeWave)
        panel.SetBackgroundColour(self.GetBackgroundColour())
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel = panel
        self.sizer = sizer

        # 大标题（StaticText 居中显示；RichTextPlainText 是只读编辑控件，
        # 自带白底、边框和滚动条，拿来做标题反而不整齐）
        self.ttle = wx.StaticText(panel, label=u'18单词',
                                  style=wx.ALIGN_CENTER_HORIZONTAL)
        fonth = self.ttle.GetFont()
        fonth.SetPointSize(fonth.GetPointSize() + 18)
        fonth.SetWeight(wx.FONTWEIGHT_BOLD)
        self.ttle.SetFont(fonth)
        self.ttle.SetForegroundColour(wx.Colour(30, 58, 138))

        # 固定标语（一直显示）
        self.slogan = wx.StaticText(panel, label=u'中考 · 高中英语词汇记忆工具',
                                    style=wx.ALIGN_CENTER_HORIZONTAL)
        f_slogan = self.slogan.GetFont()
        f_slogan.SetPointSize(f_slogan.GetPointSize() + 3)
        self.slogan.SetFont(f_slogan)
        self.slogan.SetForegroundColour(wx.Colour(95, 125, 155))

        # 信息栏：显示当前已选词库与合计词数（refreshInfo 会改写它）
        self.subtitle = wx.StaticText(panel, label=u'',
                                      style=wx.ALIGN_CENTER_HORIZONTAL)
        font = self.subtitle.GetFont()
        font.SetPointSize(font.GetPointSize() + 3)
        self.subtitle.SetFont(font)
        self.subtitle.SetForegroundColour(wx.Colour(60, 85, 105))
        self.Bind(wx.EVT_PAINT, self.onDraw)
        sizer.AddStretchSpacer(1)          # 上方留白：与下方对称，内容整体居中
        sizer.Add(self.ttle, 0, wx.ALIGN_CENTER_HORIZONTAL)
        sizer.Add(self.slogan, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 6)
        sizer.Add(self.subtitle, 0,
                  wx.ALIGN_CENTER_HORIZONTAL | wx.TOP | wx.BOTTOM, 20)

        # 按钮组：尺寸一致、间距一致、图标 + 文字。
        # 用 BitmapButton 承载自绘位图，而不是 wx.Button.SetBitmap ——
        # wx.Button 设了 SetBitmap 后在某些平台不渲染带文字的位图；
        # 另外 wx.Image.Rescale() 返回的是 Image，直接塞给 SetBitmap 会报错。
        self.buttons = {}
        for key, label, icon_file, handler in self.BUTTONS:
            normal = self.make_button_bitmap(label, icon_file, 'normal')
            btn = wx.BitmapButton(panel, bitmap=normal, size=self.BTN_SIZE,
                                  style=wx.BORDER_NONE)
            hover = self.make_button_bitmap(label, icon_file, 'hover')
            btn.SetBitmapPressed(self.make_button_bitmap(label, icon_file, 'press'))
            btn.SetBitmapDisabled(
                self.make_button_bitmap(label, icon_file, 'disabled'))
            # 悬停效果手动切换，比 SetBitmapHover 的平台兼容性更好
            btn.Bind(wx.EVT_ENTER_WINDOW, lambda e, b=btn, m=hover: b.SetBitmap(m))
            btn.Bind(wx.EVT_LEAVE_WINDOW, lambda e, b=btn, m=normal: b.SetBitmap(m))
            btn.Bind(wx.EVT_BUTTON, getattr(self, handler))
            btn.SetToolTip(label)
            sizer.Add(btn, 0,
                      wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, self.BTN_GAP)
            self.buttons[key] = btn

        sizer.AddStretchSpacer(1)          # 下方留白，与上方对称
        panel.SetSizer(sizer)

        # 保留原来的控件名，外部按旧名字引用也不会断
        for key, attr in (('spell', 'startspell'), ('study', 'startstudy'),
                          ('game', 'startgame'), ('explain', 'startexplain'),
                          ('note', 'startnote')):
            setattr(self, attr, self.buttons[key])

        self.refreshInfo()
    def activeWave(self, event: wx.MouseEvent ):
        self.t = 0
        self.eX=event.GetX()
        self.eY=event.GetY()
        print(self.eX, self.eY)
    def onDraw(self, event):
        print(self.t)
        if self.t<10: 
            self.t+=0.3
            dc = wx.PaintDC(self)
            dc.SetPen(wx.Pen('#00f4ff'))
            dc.SetBrush(wx.Brush('b3e0ff'))
            dc.DrawCircle(self.eX, self.eY, self.t)

    # 按钮自绘配色：(底色, 边框色, 文字色, 图标是否置灰)
    BUTTON_STYLES = {
        'normal':   (wx.Colour(255, 255, 255), wx.Colour(185, 214, 238),
                     wx.Colour(30, 58, 138), False),
        'hover':    (wx.Colour(232, 243, 255), wx.Colour(90, 150, 220),
                     wx.Colour(20, 48, 120), False),
        'press':    (wx.Colour(207, 230, 251), wx.Colour(74, 134, 204),
                     wx.Colour(15, 40, 105), False),
        'disabled': (wx.Colour(242, 244, 246), wx.Colour(214, 220, 226),
                     wx.Colour(166, 173, 181), True),
    }

    def make_button_bitmap(self, text, icon_file, state='normal'):
        """把「图标 + 文字」画成一张按钮位图（圆角、悬停、置灰都由这里控制）。

        之所以自己画：wx.Button 设置 SetBitmap 后，在 GTK 等平台不会把图标
        画到按钮上，而 BitmapButton + 自绘位图各平台表现一致。
        """
        w, h = self.BTN_SIZE
        bmp = wx.Bitmap(w, h, 32)
        dc = wx.MemoryDC(bmp)
        dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        dc.Clear()

        fill, edge, text_col, grey = self.BUTTON_STYLES[state]
        dc.SetBrush(wx.Brush(fill))
        dc.SetPen(wx.Pen(edge, 2))
        dc.DrawRoundedRectangle(1, 1, w - 2, h - 2, 9)

        font = self.subtitle.GetFont()
        font.SetPointSize(font.GetPointSize() + 1)
        dc.SetFont(font)
        dc.SetTextForeground(text_col)

        icon = self.make_icon(icon_file, grey)
        icon_w = icon.GetWidth() if icon.IsOk() else 0
        icon_h = icon.GetHeight() if icon.IsOk() else 0
        text_w, text_h = dc.GetTextExtent(text)
        gap = 12 if icon_w else 0

        # 图标 + 文字作为一个整体水平居中
        x = (w - (icon_w + gap + text_w)) // 2
        if icon_w:
            dc.DrawBitmap(icon, x, (h - icon_h) // 2, True)
            x += icon_w + gap
        dc.DrawText(text, x, (h - text_h) // 2)

        dc.SelectObject(wx.NullBitmap)
        return bmp

    def make_icon(self, filename, grey=False):
        """加载并缩放按钮图标：按扩展名判断格式（.gif 不是 png！），
        文件缺失或格式不对时返回空位图 —— 少个图标不该让程序起不来。"""
        path = RESOURCE / filename
        if not path.is_file():
            print('图标文件不存在: %s' % path)
            return wx.NullBitmap
        kind = wx.BITMAP_TYPE_PNG
        try:
            image = wx.Image(str(path), kind)
            if not image.IsOk():
                print('图标无法识别: %s' % path)
                return wx.NullBitmap
            if grey:                       # 按钮置灰时图标也变灰
                image = image.ConvertToGreyscale()
            return image.Rescale(self.ICON_SIZE, self.ICON_SIZE,
                                 wx.IMAGE_QUALITY_HIGH).ConvertToBitmap()
        except Exception as exc:
            print('图标加载失败 %s: %s' % (path, exc))
            return wx.NullBitmap

    def refreshInfo(self):
        total = sum(c for n, _, c in self.libs if n in self.selected)
        picked = [n for n, _, _ in self.libs if n in self.selected]

        if not self.libs:
            self.subtitle.SetLabel(u'未找到词库，请把词库（*.json）放到：\n%s' % LIB_DIR)
            self.subtitle.SetToolTip(u'')
        elif not picked:
            self.subtitle.SetLabel(u'当前未选择任何词库\n请从「文件 - 编辑 - 配置词库」中选择')
            self.subtitle.SetToolTip(u'')
        else:
            # 词库名太多会把信息栏撑得很宽，这里只列前 3 个，完整列表放进提示
            if len(picked) <= 3:
                head = u'已选词库：%s' % u'、'.join(picked)
            else:
                head = u'已选词库：%s 等 %d 个' % (u'、'.join(picked[:3]), len(picked))
            self.subtitle.SetLabel(u'%s\n共 %d 词' % (head, total))
            self.subtitle.SetToolTip(u'已选词库（%d 个）：%s'
                                     % (len(picked), u'、'.join(picked)))

        # 没有可用词库时把练习按钮置灰（Enable 是方法，不能直接赋值）；
        # 「打开词书」在没勾词库时也应该能点，方便去看目录里到底有什么
        ready = bool(self.libs and self.selected)
        for key, btn in self.buttons.items():
            btn.Enable(True if key == 'note' or key == 'game' or key == 'explain' else ready)

        # 文字行数变化后让 Sizer 重新排版，避免压住按钮
        self.panel.Layout()
        save_selected(self.libs, self.selected)

    # ------------------------------------------------------------ 五个入口
    def start(self, event):
        """拼写测试：看中文释义，手打英文单词（题目从勾选的词库随机抽取）

        注意：这里走 spell.run('spell')，也就是「看中文写英文」的拼写界面。
        你原来的写法是 spell.WordQuizApp(...)，那是「英文选中文释义」的界面，
        和「开始单词翻译测试」是同一个，两个按钮会打开一模一样的窗口。
        """
        self.launch(spell.run, u'拼写测试',
                    names=sorted(self.selected))

    def start1(self, event):
        """单词翻译测试：固定 100 词，英文选中文"""
        self.launch(explain.run, u'单词翻译测试')

    def start2(self, event):
        """填单词游戏：挖空选字母"""
        self.launch(word_game_tkinter.run, u'填单词游戏')

    def start3(self, event):
        """学习单词：卡片式浏览"""
        self.launch(new_word_study.run, u'学习单词',
                    T=spell.load_words2(sorted(self.selected)))

    def start4(self, event):
        """打开词书：表格浏览各词库词条"""
        self.launch(word_note.run, u'单词笔记')

    def launch(self, func, what, **kwargs):
        """统一打开练习窗口：都走 spell.open_window，行为一致"""
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
        except Exception as exc:        # 兜底：任何异常都弹窗，不让主程序崩掉
            wx.MessageBox(u'打开「%s」失败：\n%s' % (what, exc),
                          u'出错了', wx.ICON_ERROR, self)

    def warn_tk(self, what):
        wx.MessageBox(u'「%s」需要标准库 tkinter，\n'
                      u'当前 Python 没有装，请先安装后再试。' % what,
                      u'无法开始', wx.ICON_WARNING, self)

    def menuHandler(self, evt: wx.Event):
        if evt.GetId() == QUIT_MENU:
            self.Close()
        elif evt.GetId() == CONFIG_MENU:
            dlg = ConfigDialog(self, self.libs, self.selected)
            if dlg.ShowModal() == wx.ID_OK:
                self.selected = dlg.get_selected()
                self.refreshInfo()
            dlg.Destroy()


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
