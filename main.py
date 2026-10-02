# -*- coding: gbk -*-

"""十八单词 —— 英语词汇记忆工具（第二代）

词库放在 ./dev_english/ 目录下，一个 .json 文件即一个词库，
文件名（去掉 .json）就是词库名。运行方式：

    pip install wxPython
    python 十八单词.py

点“开始拼写测试(20词)”会打开一个 tkinter 窗口做拼写测验，
题目从「配置词库」里勾选的词库中随机抽取。
"""
import json, A, spell, explain, word_game_tkinter, word_note, new_word_study

try:
    import tkinter as tk
except ImportError:          # 缺少 tkinter 时主窗口仍可正常使用
    tk = None

import wx

APP_TITLE = u'十八单词'

# 路径都相对本脚本所在目录，从任何位置运行都没问题
BASE_DIR = A.app_dir()
APP_ICON = BASE_DIR / 'icon.ico'
LIB_DIR = BASE_DIR / 'dev_english'
LATEST = BASE_DIR / 'latest.json'
RESOURCE = BASE_DIR / 'res'
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

    def __init__(self):
        '''构造函数'''
        wx.Frame.__init__(self, None, -1, APP_TITLE,
                          style=wx.DEFAULT_FRAME_STYLE & (~(wx.RESIZE_BORDER)) & (~wx.MAXIMIZE_BOX))
        self.SetBackgroundColour(wx.Colour(179, 224, 255))
        self.SetSize((800, 600))
        self.Center()

        if APP_ICON.is_file():
            self.SetIcon(wx.Icon(str(APP_ICON), wx.BITMAP_TYPE_ICO))

        self.libs = load_libs()
        self.selected = load_selected(self.libs)
        self._banner = None            # 防止 tk 图片被回收

        self.setWidgets()
        self.Bind(wx.EVT_MENU, self.menuHandler)

    def setWidgets(self):
        '''设置控件'''
        # 菜单栏
        self.menubar = wx.MenuBar()
        self.menuFile = wx.Menu()
        self.menuEdit = wx.Menu()
        self.menuEdit.Append(CONFIG_MENU, u'配置词库')
        self.menuFile.AppendSubMenu(self.menuEdit, u'编辑')
        self.menuFile.Append(QUIT_MENU, u'退出(Alt+F4)')
        self.menubar.Append(self.menuFile, u'文件')
        self.SetMenuBar(self.menubar)

        # 正文：显示当前已选词库 + 开始测试
        panel = wx.Panel(self)
        panel.SetBackgroundColour(self.GetBackgroundColour())
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel=panel
        self.sizer=sizer
        self.info = wx.StaticText(panel, label=u'', style=wx.ALIGN_CENTRE_HORIZONTAL)
        font = self.info.GetFont()
        font.SetPointSize(font.GetPointSize() + 4)
        self.info.SetFont(font)

        self.ttle = wx.StaticText(panel, label=u'18单词', size = (100, 40), pos = (350, 0), style=wx.ALIGN_CENTRE_HORIZONTAL)
        fonth = self.info.GetFont()
        fonth.SetPointSize(font.GetPointSize()+12)
        self.ttle.SetFont(fonth)


        self.startspell = wx.Button(panel, label=u'开始拼写测试', size = (400, 60), pos = (200, 250))
        self.startspell.SetFont(font)
        self.startspell.SetBitmap(wx.Image(str(RESOURCE / 'wordspell.png'), wx.BITMAP_TYPE_PNG).Rescale(50, 50))
        self.startspell.Bind(wx.EVT_BUTTON, self.start)
        
        self.startexplain = wx.Button(panel, label=u'开始单词翻译测试（固定100词）', size = (400, 60), pos = (200, 100))
        self.startexplain.SetFont(font)
        self.startexplain.SetBitmap(wx.Image(str(RESOURCE / 'explain.gif'), wx.BITMAP_TYPE_PNG).Rescale(50, 50))
        self.startexplain.Bind(wx.EVT_BUTTON, self.start1)

        self.startgame = wx.Button(panel, label = u'开始填单词游戏', size = (400, 60), pos = (200, 150))
        self.startgame.SetFont(font)
        self.startgame.SetBitmap(wx.Image(str(RESOURCE / 'game.gif'), wx.BITMAP_TYPE_PNG).Rescale(50, 50))
        self.startgame.Bind(wx.EVT_BUTTON, self.start2)

        self.startstudy = wx.Button(panel, label = u'开始学习单词', size = (400, 60), pos = (200, 350))
        self.startstudy.SetFont(font)
        self.startstudy.SetBitmap(wx.Image(str(RESOURCE / 'wordstudy.png'), wx.BITMAP_TYPE_PNG).Rescale(50, 50))
        self.startstudy.Bind(wx.EVT_BUTTON, self.start3)

        self.startnote = wx.Button(panel, label = u'打开词书', size = (400, 60))
        self.startnote.SetFont(font)
        self.startnote.SetBitmap(wx.Image(str(RESOURCE / 'wordnote.gif'), wx.BITMAP_TYPE_PNG).Rescale(50, 50))
        self.startnote.Bind(wx.EVT_BUTTON, self.start4)

        sizer.AddStretchSpacer()
        # sizer.Add(self.info, 0, wx.EXPAND | wx.ALL, 30)
        sizer.Add(self.startspell, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 16)
        sizer.Add(self.startstudy, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 19)
        sizer.Add(self.startgame, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 13)
        sizer.Add(self.startexplain, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 10)
        sizer.Add(self.startnote, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 7)
        
        sizer.AddStretchSpacer()
        panel.SetSizer(sizer)

        self.refreshInfo()

    def refreshInfo(self):
        total = sum(c for n, _, c in self.libs if n in self.selected)
        if not self.libs:
            self.info.SetLabel(u'未找到词库，请检查 dev_english 目录')
        elif not self.selected:
            self.info.SetLabel(u'当前未选择任何词库\n请从「文件 - 编辑 - 配置词库」中选择')
        else:
            names = u'、'.join(n for n, _, _ in self.libs if n in self.selected)
            self.info.SetLabel(u'已选词库：%s\n共 %d 词' % (names, total))
        # 没有可选词库时禁用开始按钮（Enable 是方法，不能直接赋值）
        self.startspell.Enable(bool(self.libs and self.selected))
        self.startstudy.Enable(bool(self.libs and self.selected))
        save_selected(self.libs, self.selected)

    # ------------------------------------------------------------ 拼写测试
    def start(self, event):
        if not spell.available() or tk is None:
            wx.MessageBox(u'拼写需要标准库 tkinter，\n'
                          u'当前 Python 没有装，请先安装后再试。',
                          u'无法开始测试', wx.ICON_WARNING, self)
            return
        if spell.has_window():          # 已经开着一个就别再开一个
            spell.focus_window()
            return

        root = tk.Tk()
        root.title(u'十八单词 · 拼写测试')
        root.configure(bg=spell.BG)

        # 顶部：第二代图标 + 退出按钮
        top = tk.Frame(root, bg=spell.BG)
        top.pack(fill='x')
        tk.Button(top, text=u'退出', command=spell.clear_window).pack(pady=(0, 6))

        try:
            spell.WordQuizApp(root, names=sorted(self.selected))
        except spell.NoWordsError as exc:
            wx.MessageBox(str(exc), u'没有可用词库', wx.ICON_WARNING, self)
            root.destroy()
            return
        root.mainloop()

    def start1(self, event):
        if not explain.available() or tk is None:
            wx.MessageBox(u'单词翻译需要标准库 tkinter，\n'
                          u'当前 Python 没有装，请先安装后再试。',
                          u'无法开始测试', wx.ICON_WARNING, self)
            return
        explain.run()
    def start2(self, event):
        if not spell.available() or tk is None:
            wx.MessageBox(u'单词游戏需要标准库 tkinter，\n'
                          u'当前 Python 没有装，请先安装后再试。',
                          u'无法开始测试', wx.ICON_WARNING, self)
            return
        word_game_tkinter.run()
    def start3(self, event):
        if not spell.available() or tk is None:
            wx.MessageBox(u'学习词语需要标准库 tkinter，\n'
                          u'当前 Python 没有装，请先安装后再试。',
                          u'无法开始测试', wx.ICON_WARNING, self)
            return
        new_word_study.run(spell.load_words2(sorted(self.selected)))
    def start4(self, event):
        if not spell.available() or tk is None:
            wx.MessageBox(u'词书需要标准库 tkinter，\n'
                          u'当前 Python 没有装，请先安装后再试。',
                          u'无法开始测试', wx.ICON_WARNING, self)
            return
        word_note.run()
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
