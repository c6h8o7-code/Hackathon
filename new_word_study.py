# -*- coding: utf-8 -*-
"""
中考核心词 · 单词新学（优化版 v3.4）
改动：
  1. 每学完 10 个词，对 10 个词全部测验
  2. 测验后立即进入"错词重学"环节，重学后小测，直到全对或达最大轮数
  3. 错词重学顶部提示、进度明确
  4. 答错提示位置：卡片下方、按钮上方
  5. 答错时高亮正确答案
  6. 优化整体节奏与视觉反馈
"""

import tkinter as tk
import random
import threading, word_note, paths

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False


class Sound:
    def __init__(self, root):
        self.root = root
        self.muted = False

    def _beep(self, freq, dur):
        if self.muted:
            return
        if HAS_WINSOUND:
            threading.Thread(target=winsound.Beep, args=(freq, dur), daemon=True).start()

    def _bell(self):
        if self.muted:
            return
        try:
            self.root.bell()
        except Exception:
            pass

    def next_word(self):
        if HAS_WINSOUND:
            self._beep(880, 60)
        else:
            self._bell()

    def popup(self):
        if HAS_WINSOUND:
            def seq():
                if self.muted:
                    return
                winsound.Beep(660, 80)
                winsound.Beep(990, 100)
            threading.Thread(target=seq, daemon=True).start()
        else:
            self._bell()

    def finish(self):
        if HAS_WINSOUND:
            def seq():
                if self.muted:
                    return
                for f in (523, 659, 784):
                    winsound.Beep(f, 150)
            threading.Thread(target=seq, daemon=True).start()
        else:
            self._bell()

    def exit(self):
        if HAS_WINSOUND:
            self._beep(300, 180)
        else:
            self._bell()

    def replay(self):
        if HAS_WINSOUND:
            self._beep(1200, 40)
        else:
            self._bell()

    def error(self):
        if HAS_WINSOUND:
            def seq():
                if self.muted:
                    return
                winsound.Beep(400, 120)
                winsound.Beep(300, 180)
            threading.Thread(target=seq, daemon=True).start()
        else:
            self._bell()

    def correct(self):
        if HAS_WINSOUND:
            def seq():
                if self.muted:
                    return
                winsound.Beep(880, 80)
                winsound.Beep(1320, 120)
            threading.Thread(target=seq, daemon=True).start()
        else:
            self._bell()


WORDS = [
    ("about", "/əˈbaʊt/", "prep.", "关于；大约"),
    ("after", "/ˈɑːftə(r)/", "prep./conj.", "在……之后"),
    ("again", "/əˈɡen/", "adv.", "再一次；又"),
    ("all", "/ɔːl/", "adj./pron.", "所有的；全部"),
    ("also", "/ˈɔːlsəʊ/", "adv.", "也；同样"),
    ("always", "/ˈɔːlweɪz/", "adv.", "总是；一直"),
    ("animal", "/ˈænɪml/", "n.", "动物"),
    ("answer", "/ˈɑːnsə(r)/", "n./v.", "回答；答案"),
    ("any", "/ˈeni/", "adj./pron.", "任何的；一些"),
    ("apple", "/ˈæpl/", "n.", "苹果"),
    ("ask", "/ɑːsk/", "v.", "问；请求"),
    ("back", "/bæk/", "adv./n.", "回；后面"),
    ("bad", "/bæd/", "adj.", "坏的；差的"),
    ("bag", "/bæɡ/", "n.", "包；袋子"),
    ("ball", "/bɔːl/", "n.", "球"),
    ("beautiful", "/ˈbjuːtɪfl/", "adj.", "美丽的"),
    ("because", "/bɪˈkɒz/", "conj.", "因为"),
    ("become", "/bɪˈkʌm/", "v.", "变成；成为"),
    ("before", "/bɪˈfɔː(r)/", "prep./conj.", "在……之前"),
    ("begin", "/bɪˈɡɪn/", "v.", "开始"),
    ("best", "/best/", "adj./adv.", "最好的；最好地"),
    ("better", "/ˈbetə(r)/", "adj./adv.", "更好的；更好地"),
    ("big", "/bɪɡ/", "adj.", "大的"),
    ("bird", "/bɜːd/", "n.", "鸟"),
    ("black", "/blæk/", "adj./n.", "黑色的；黑色"),
    ("blue", "/bluː/", "adj./n.", "蓝色的；蓝色"),
    ("book", "/bʊk/", "n./v.", "书；预订"),
    ("boy", "/bɔɪ/", "n.", "男孩"),
    ("bring", "/brɪŋ/", "v.", "带来"),
    ("brother", "/ˈbrʌðə(r)/", "n.", "兄弟"),
    ("build", "/bɪld/", "v.", "建造"),
    ("busy", "/ˈbɪzi/", "adj.", "忙碌的"),
    ("buy", "/baɪ/", "v.", "买"),
    ("call", "/kɔːl/", "v./n.", "打电话；称呼"),
    ("can", "/kæn/", "modal v.", "能；会"),
    ("car", "/kɑː(r)/", "n.", "小汽车"),
    ("care", "/keə(r)/", "v./n.", "关心；照顾"),
    ("carry", "/ˈkæri/", "v.", "携带；搬运"),
    ("catch", "/kætʃ/", "v.", "抓住；赶上"),
    ("change", "/tʃeɪndʒ/", "v./n.", "改变；零钱"),
    ("child", "/tʃaɪld/", "n.", "孩子"),
    ("choose", "/tʃuːz/", "v.", "选择"),
    ("city", "/ˈsɪti/", "n.", "城市"),
    ("class", "/klɑːs/", "n.", "班级；课"),
    ("clean", "/kliːn/", "adj./v.", "干净的；打扫"),
    ("clear", "/klɪə(r)/", "adj.", "清楚的；晴朗的"),
    ("climb", "/klaɪm/", "v.", "攀登；爬"),
    ("close", "/kləʊz/", "v./adj.", "关闭；近的"),
    ("come", "/kʌm/", "v.", "来"),
    ("cook", "/kʊk/", "v./n.", "烹饪；厨师"),
    ("cool", "/kuːl/", "adj.", "凉爽的；酷的"),
    ("country", "/ˈkʌntri/", "n.", "国家；乡村"),
    ("cut", "/kʌt/", "v.", "切；剪"),
    ("day", "/deɪ/", "n.", "天；白天"),
    ("decide", "/dɪˈsaɪd/", "v.", "决定"),
    ("different", "/ˈdɪfrənt/", "adj.", "不同的"),
    ("difficult", "/ˈdɪfɪkəlt/", "adj.", "困难的"),
    ("do", "/duː/", "v.", "做"),
    ("draw", "/drɔː/", "v.", "画；拉"),
    ("dream", "/driːm/", "n./v.", "梦想；做梦"),
    ("drink", "/drɪŋk/", "v./n.", "喝；饮料"),
    ("drive", "/draɪv/", "v.", "驾驶"),
    ("each", "/iːtʃ/", "adj./pron.", "每个"),
    ("early", "/ˈɜːli/", "adj./adv.", "早的；早地"),
    ("earth", "/ɜːθ/", "n.", "地球；泥土"),
    ("easy", "/ˈiːzi/", "adj.", "容易的"),
    ("eat", "/iːt/", "v.", "吃"),
    ("end", "/end/", "n./v.", "结束；末端"),
    ("enjoy", "/ɪnˈdʒɔɪ/", "v.", "享受；喜欢"),
    ("enough", "/ɪˈnʌf/", "adj./adv.", "足够的；足够地"),
    ("even", "/ˈiːvn/", "adv.", "甚至"),
    ("every", "/ˈevri/", "adj.", "每一个"),
    ("example", "/ɪɡˈzɑːmpl/", "n.", "例子"),
    ("exercise", "/ˈeksəsaɪz/", "n./v.", "锻炼；练习"),
    ("eye", "/aɪ/", "n.", "眼睛"),
    ("face", "/feɪs/", "n./v.", "脸；面对"),
    ("fact", "/fækt/", "n.", "事实"),
    ("fall", "/fɔːl/", "v./n.", "落下；秋天"),
    ("family", "/ˈfæməli/", "n.", "家庭"),
    ("far", "/fɑː(r)/", "adj./adv.", "远的；远地"),
    ("fast", "/fɑːst/", "adj./adv.", "快的；快地"),
    ("father", "/ˈfɑːðə(r)/", "n.", "父亲"),
    ("feel", "/fiːl/", "v.", "感觉"),
    ("few", "/fjuː/", "adj.", "很少的"),
    ("find", "/faɪnd/", "v.", "找到；发现"),
    ("finish", "/ˈfɪnɪʃ/", "v.", "完成"),
    ("fire", "/ˈfaɪə(r)/", "n.", "火"),
    ("first", "/fɜːst/", "adj./adv.", "第一的；首先"),
    ("fish", "/fɪʃ/", "n./v.", "鱼；钓鱼"),
    ("fly", "/flaɪ/", "v./n.", "飞；苍蝇"),
    ("follow", "/ˈfɒləʊ/", "v.", "跟随"),
    ("food", "/fuːd/", "n.", "食物"),
    ("foot", "/fʊt/", "n.", "脚"),
    ("forget", "/fəˈɡet/", "v.", "忘记"),
    ("free", "/friː/", "adj.", "自由的；免费的"),
    ("friend", "/frend/", "n.", "朋友"),
    ("full", "/fʊl/", "adj.", "满的；饱的"),
    ("game", "/ɡeɪm/", "n.", "游戏；比赛"),
    ("get", "/ɡet/", "v.", "得到；变得"),
    ("girl", "/ɡɜːl/", "n.", "女孩"),
    ("give", "/ɡɪv/", "v.", "给"),
    ("go", "/ɡəʊ/", "v.", "去"),
    ("good", "/ɡʊd/", "adj.", "好的"),
    ("great", "/ɡreɪt/", "adj.", "伟大的；很好的"),
    ("green", "/ɡriːn/", "adj./n.", "绿色的；绿色"),
    ("grow", "/ɡrəʊ/", "v.", "生长；种植"),
    ("hand", "/hænd/", "n./v.", "手；递"),
    ("happy", "/ˈhæpi/", "adj.", "快乐的"),
    ("hard", "/hɑːd/", "adj./adv.", "困难的；努力地"),
    ("have", "/hæv/", "v.", "有"),
    ("head", "/hed/", "n.", "头"),
    ("hear", "/hɪə(r)/", "v.", "听见"),
    ("help", "/help/", "v./n.", "帮助"),
    ("high", "/haɪ/", "adj./adv.", "高的；高地"),
    ("hold", "/həʊld/", "v.", "握住；举行"),
    ("home", "/həʊm/", "n./adv.", "家；在家"),
    ("hope", "/həʊp/", "v./n.", "希望"),
    ("hot", "/hɒt/", "adj.", "热的"),
    ("hour", "/ˈaʊə(r)/", "n.", "小时"),
    ("house", "/haʊs/", "n.", "房子"),
    ("how", "/haʊ/", "adv.", "怎样；多么"),
    ("idea", "/aɪˈdɪə/", "n.", "主意；想法"),
    ("important", "/ɪmˈpɔːtnt/", "adj.", "重要的"),
    ("interest", "/ˈɪntrəst/", "n./v.", "兴趣；使感兴趣"),
    ("job", "/dʒɒb/", "n.", "工作"),
    ("join", "/dʒɔɪn/", "v.", "参加；加入"),
    ("just", "/dʒʌst/", "adv.", "仅仅；刚刚"),
    ("keep", "/kiːp/", "v.", "保持；保存"),
    ("kind", "/kaɪnd/", "adj./n.", "友善的；种类"),
    ("know", "/nəʊ/", "v.", "知道"),
    ("land", "/lænd/", "n./v.", "陆地；降落"),
    ("large", "/lɑːdʒ/", "adj.", "大的"),
    ("last", "/lɑːst/", "adj./v.", "最后的；持续"),
    ("late", "/leɪt/", "adj./adv.", "迟的；晚地"),
    ("laugh", "/lɑːf/", "v./n.", "笑"),
    ("learn", "/lɜːn/", "v.", "学习"),
    ("leave", "/liːv/", "v.", "离开；留下"),
    ("left", "/left/", "adj./n.", "左边的；左边"),
    ("lesson", "/ˈlesn/", "n.", "课"),
    ("let", "/let/", "v.", "让"),
    ("life", "/laɪf/", "n.", "生活；生命"),
    ("light", "/laɪt/", "n./adj.", "光；轻的"),
    ("like", "/laɪk/", "v./prep.", "喜欢；像"),
    ("listen", "/ˈlɪsn/", "v.", "听"),
    ("little", "/ˈlɪtl/", "adj.", "小的；少的"),
    ("live", "/lɪv/", "v.", "居住；生活"),
    ("long", "/lɒŋ/", "adj.", "长的"),
    ("look", "/lʊk/", "v.", "看"),
    ("lose", "/luːz/", "v.", "丢失；输"),
    ("love", "/lʌv/", "v./n.", "爱"),
    ("make", "/meɪk/", "v.", "制作；使"),
    ("man", "/mæn/", "n.", "男人"),
    ("many", "/ˈmeni/", "adj.", "许多的"),
    ("matter", "/ˈmætə(r)/", "n./v.", "事情；要紧"),
    ("may", "/meɪ/", "modal v.", "可以；可能"),
    ("meet", "/miːt/", "v.", "遇见；满足"),
    ("mind", "/maɪnd/", "n./v.", "头脑；介意"),
    ("minute", "/ˈmɪnɪt/", "n.", "分钟"),
    ("money", "/ˈmʌni/", "n.", "钱"),
    ("month", "/mʌnθ/", "n.", "月"),
    ("more", "/mɔː(r)/", "adj./adv.", "更多的；更"),
    ("morning", "/ˈmɔːnɪŋ/", "n.", "早晨"),
    ("most", "/məʊst/", "adj./adv.", "最多的；最"),
    ("mother", "/ˈmʌðə(r)/", "n.", "母亲"),
    ("move", "/muːv/", "v.", "移动；搬家"),
    ("music", "/ˈmjuːzɪk/", "n.", "音乐"),
    ("must", "/mʌst/", "modal v.", "必须"),
    ("name", "/neɪm/", "n./v.", "名字；命名"),
    ("near", "/nɪə(r)/", "adj./prep.", "近的；靠近"),
    ("need", "/niːd/", "v./n.", "需要"),
    ("never", "/ˈnevə(r)/", "adv.", "从不"),
    ("new", "/njuː/", "adj.", "新的"),
    ("next", "/nekst/", "adj./adv.", "下一个；接下来"),
    ("night", "/naɪt/", "n.", "夜晚"),
    ("no", "/nəʊ/", "adv./adj.", "不；没有"),
    ("not", "/nɒt/", "adv.", "不"),
    ("nothing", "/ˈnʌθɪŋ/", "pron.", "没有什么"),
    ("now", "/naʊ/", "adv.", "现在"),
    ("number", "/ˈnʌmbə(r)/", "n.", "数字；号码"),
    ("old", "/əʊld/", "adj.", "老的；旧的"),
    ("open", "/ˈəʊpən/", "v./adj.", "打开；开着的"),
    ("other", "/ˈʌðə(r)/", "adj./pron.", "其他的"),
    ("over", "/ˈəʊvə(r)/", "prep./adv.", "在……上方；结束"),
    ("page", "/peɪdʒ/", "n.", "页"),
    ("paper", "/ˈpeɪpə(r)/", "n.", "纸；论文"),
    ("part", "/pɑːt/", "n.", "部分"),
    ("people", "/ˈpiːpl/", "n.", "人们"),
    ("place", "/pleɪs/", "n./v.", "地方；放置"),
    ("plan", "/plæn/", "n./v.", "计划"),
    ("play", "/pleɪ/", "v./n.", "玩；戏剧"),
    ("point", "/pɔɪnt/", "n./v.", "点；指"),
    ("possible", "/ˈpɒsəbl/", "adj.", "可能的"),
    ("problem", "/ˈprɒbləm/", "n.", "问题"),
    ("put", "/pʊt/", "v.", "放"),
    ("question", "/ˈkwestʃən/", "n.", "问题"),
    ("quick", "/kwɪk/", "adj.", "快的"),
    ("quiet", "/ˈkwaɪət/", "adj.", "安静的"),
    ("read", "/riːd/", "v.", "读"),
    ("ready", "/ˈredi/", "adj.", "准备好的"),
    ("real", "/rɪəl/", "adj.", "真实的"),
    ("remember", "/rɪˈmembə(r)/", "v.", "记得"),
    ("right", "/raɪt/", "adj./n.", "正确的；右边"),
    ("room", "/ruːm/", "n.", "房间"),
    ("run", "/rʌn/", "v.", "跑"),
    ("say", "/seɪ/", "v.", "说"),
    ("school", "/skuːl/", "n.", "学校"),
    ("see", "/siː/", "v.", "看见"),
    ("seem", "/siːm/", "v.", "似乎"),
    ("show", "/ʃəʊ/", "v./n.", "展示；表演"),
    ("small", "/smɔːl/", "adj.", "小的"),
    ("some", "/sʌm/", "adj./pron.", "一些"),
    ("speak", "/spiːk/", "v.", "说话"),
    ("start", "/stɑːt/", "v./n.", "开始"),
    ("stay", "/steɪ/", "v.", "停留"),
    ("stop", "/stɒp/", "v./n.", "停止；车站"),
    ("story", "/ˈstɔːri/", "n.", "故事"),
    ("study", "/ˈstʌdi/", "v./n.", "学习"),
    ("such", "/sʌtʃ/", "adj.", "这样的"),
    ("take", "/teɪk/", "v.", "拿；花费"),
    ("talk", "/tɔːk/", "v./n.", "谈话"),
    ("tell", "/tel/", "v.", "告诉"),
    ("than", "/ðæn/", "conj.", "比"),
    ("thank", "/θæŋk/", "v.", "感谢"),
    ("thing", "/θɪŋ/", "n.", "事情；东西"),
    ("think", "/θɪŋk/", "v.", "想；认为"),
    ("time", "/taɪm/", "n.", "时间；次数"),
    ("today", "/təˈdeɪ/", "adv./n.", "今天"),
    ("together", "/təˈɡeðə(r)/", "adv.", "一起"),
    ("tomorrow", "/təˈmɒrəʊ/", "adv./n.", "明天"),
    ("too", "/tuː/", "adv.", "也；太"),
    ("town", "/taʊn/", "n.", "城镇"),
    ("tree", "/triː/", "n.", "树"),
    ("try", "/traɪ/", "v.", "尝试"),
    ("turn", "/tɜːn/", "v./n.", "转；轮流"),
    ("under", "/ˈʌndə(r)/", "prep.", "在……下面"),
    ("understand", "/ˌʌndəˈstænd/", "v.", "理解"),
    ("use", "/juːz/", "v./n.", "使用；用途"),
    ("very", "/ˈveri/", "adv.", "非常"),
    ("visit", "/ˈvɪzɪt/", "v./n.", "参观；拜访"),
    ("wait", "/weɪt/", "v.", "等待"),
    ("walk", "/wɔːk/", "v./n.", "走；散步"),
    ("want", "/wɒnt/", "v.", "想要"),
    ("watch", "/wɒtʃ/", "v./n.", "观看；手表"),
    ("water", "/ˈwɔːtə(r)/", "n.", "水"),
    ("way", "/weɪ/", "n.", "路；方法"),
    ("wear", "/weə(r)/", "v.", "穿"),
    ("week", "/wiːk/", "n.", "星期"),
    ("well", "/wel/", "adv./adj.", "好地；健康的"),
    ("what", "/wɒt/", "pron.", "什么"),
    ("when", "/wen/", "adv./conj.", "什么时候；当……时"),
    ("where", "/weə(r)/", "adv.", "在哪里"),
    ("which", "/wɪtʃ/", "pron./adj.", "哪一个"),
    ("white", "/waɪt/", "adj./n.", "白色的；白色"),
    ("who", "/huː/", "pron.", "谁"),
    ("why", "/waɪ/", "adv.", "为什么"),
    ("will", "/wɪl/", "modal v.", "将；会"),
    ("with", "/wɪð/", "prep.", "和……一起"),
    ("word", "/wɜːd/", "n.", "单词"),
    ("work", "/wɜːk/", "v./n.", "工作"),
    ("world", "/wɜːld/", "n.", "世界"),
    ("write", "/raɪt/", "v.", "写"),
    ("year", "/jɪə(r)/", "n.", "年"),
    ("young", "/jʌŋ/", "adj.", "年轻的"),
    ("your", "/jɔː(r)/", "pron.", "你的"),
]

ALPHABET = "abcdefghijklmnopqrstuvwxyz"
import json


class WordLearningApp:
    BG_TOP = "#1e3a8a"
    BG_BOTTOM = "#7c3aed"
    CARD_BG = "#ffffff"
    CARD_BORDER = "#e0e7ff"
    WORD_COLOR = "#1e293b"
    PHONETIC_COLOR = "#64748b"
    POS_COLOR = "#0d9488"
    CN_COLOR = "#334155"

    DELAY_MS = 2180
    REREAD_DELAY_MS = 1200     # 错词重学时的轻锁时间
    MAX_REVIEW_ROUNDS = 3      # 错词最多重学几轮

    def __init__(self, root, T, name):
        self.root = root
        self.Name = name
        self.root.title("中考核心词 · 单词新学")
        self.root.configure(bg=self.BG_TOP)
        self.root.geometry("1200x800")
        self.root.minsize(900, 620)
        
            
        self.queue = T.copy()
        self.T = T.copy()
        self.index = 0

        with open(paths.app_dir() / "study_word_data.json", "a+", encoding="utf-8") as f:
            try:
                f.seek(0)
                content = f.read().strip()
                if content:
                    data = json.loads(content)
                else:
                    data = {}
            except Exception:
                data = {}
            
            self.queue = data.get(name, self.queue)
            self.index = data.get("index_"+name, 0)
        self.learned_count = 0
        self.delay_ms = self.DELAY_MS
        self.after_id = None
        self.paused = False
        self.locked = False
        self.unlock_after_id = None

        # 窗口一销毁就取消挂起的定时器。只靠 protocol('WM_DELETE_WINDOW')
        # 不够：直接 destroy()、被父窗口回收、进程退出这些路径都不会走它，
        # 而定时器到点后回调已被销毁的部件，Tcl 会抛
        # "invalid command name ..._unlock_next"，打包后会被写进 debug.txt。
        self.root.bind('<Destroy>', self._on_window_destroy)

        # 统计
        self.quiz_count = 0
        self.quiz_correct = 0
        self.first_pass_correct = 0     # 首次测验正确数（用于最终统计）
        self.first_pass_total = 0
        self.wrong_words = []           # 全局错题本（最终未攻克的）

        # 测验状态
        self.quiz_batch = []
        self.quiz_order = []
        self.quiz_pos = 0
        self.quiz_data = None
        self.quiz_buttons = []
        self.quiz_frame = None

        # 错词重学状态
        self.review_words = []          # 本轮需要重学的错词
        self.review_index = 0
        self.review_round = 0

        self.state = "learn"

        self.sound = Sound(root)
        # ★ 先画背景，再建 UI
        self._draw_gradient_bg()
        self._build_ui()
        self._bind_keys()

        self.show_word()

    # ============================================================
    # 渐变背景
    # ============================================================
    def _draw_gradient_bg(self):
        self.bg_canvas = tk.Canvas(self.root, highlightthickness=0, bd=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)

        def draw(_event=None):
            self.bg_canvas.delete("grad")
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            if w <= 1 or h <= 1:
                return
            steps = 60
            r1, g1, b1 = self.root.winfo_rgb(self.BG_TOP)
            r2, g2, b2 = self.root.winfo_rgb(self.BG_BOTTOM)
            for i in range(steps):
                r = max(0, min(255, int(r1 + (r2 - r1) * i / steps) >> 8))
                g = max(0, min(255, int(g1 + (g2 - g1) * i / steps) >> 8))
                b = max(0, min(255, int(b1 + (b2 - b1) * i / steps) >> 8))
                color = f"#{r:02x}{g:02x}{b:02x}"
                y1 = int(h * i / steps)
                y2 = int(h * (i + 1) / steps) + 1
                self.bg_canvas.create_rectangle(
                    0, y1, w, y2, fill=color, outline=color, tags="grad"
                )

        self.root.bind("<Configure>", draw)
        self.root.after(50, draw)

    # ============================================================
    # 界面
    # ============================================================
    def _build_ui(self):
        self.lbl_progress = tk.Label(
            self.root, text="",
            font=("Microsoft YaHei", 14, "bold"),
            bg=self.BG_TOP, fg="#fbbf24"
        )
        self.lbl_progress.place(relx=0.5, rely=0.045, anchor="center")

        self.card = tk.Frame(
            self.root, bg=self.CARD_BG,
            bd=0, highlightthickness=2,
            highlightbackground=self.CARD_BORDER
        )
        self.card.place(relx=0.5, rely=0.45, anchor="center",
                        relwidth=0.75, relheight=0.56)

        inner = tk.Frame(self.card, bg=self.CARD_BG)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        self.lbl_word = tk.Label(
            inner, text="", font=("Helvetica", 68, "bold"),
            bg=self.CARD_BG, fg=self.WORD_COLOR
        )
        self.lbl_phonetic = tk.Label(
            inner, text="", font=("Helvetica", 24),
            bg=self.CARD_BG, fg=self.PHONETIC_COLOR
        )
        self.lbl_pos = tk.Label(
            inner, text="", font=("Helvetica", 22, "italic"),
            bg=self.CARD_BG, fg=self.POS_COLOR
        )
        self.lbl_cn = tk.Label(
            inner, text="", font=("Microsoft YaHei", 32),
            bg=self.CARD_BG, fg=self.CN_COLOR
        )
        self.lbl_word.pack(pady=(0, 6))
        self.lbl_phonetic.pack(pady=(0, 4))
        self.lbl_pos.pack(pady=(0, 4))
        self.lbl_cn.pack(pady=(0, 6))

        # 状态提示：卡片下方、按钮上方
        self.lbl_status = tk.Label(
            self.root, text="",
            font=("Microsoft YaHei", 16, "bold"),
            bg=self.BG_BOTTOM, fg="#fef08a"
        )
        self.lbl_status.place(relx=0.5, rely=0.775, anchor="center")

        # 选项按钮行
        self.quiz_row = tk.Frame(self.root, bg=self.BG_BOTTOM)
        self.quiz_row.place(relx=0.5, rely=0.86, anchor="center")

        self.lbl_help = tk.Label(
            self.root,
            text="空格/→/Enter：继续   ← ：上一个   F5：重听   "
                 "P：暂停/继续   M：静音   Esc：退出",
            font=("Microsoft YaHei", 12),
            bg=self.BG_BOTTOM, fg="#e0e7ff"
        )
        self.lbl_help.place(relx=0.5, rely=0.97, anchor="s")

        self.btn_continue = None
        self.btn_exit = None
        self.btn_review = None
        self.quiz_frame = self.quiz_row

    # ============================================================
    # 快捷键
    # ============================================================
    def _bind_keys(self):
        self.root.bind("<KeyPress-space>", self._on_next_key)
        self.root.bind("<Right>", self._on_next_key)
        self.root.bind("<Return>", self._on_next_key)
        self.root.bind("<Left>", lambda e: self.prev_word())
        self.root.bind("<KeyPress-Escape>", lambda e: self.quit_app())
        self.root.bind("<KeyPress-F5>", lambda e: self.replay())
        self.root.bind("<KeyPress-p>", lambda e: self.toggle_pause())
        self.root.bind("<KeyPress-P>", lambda e: self.toggle_pause())
        self.root.bind("<KeyPress-m>", lambda e: self.toggle_mute())
        self.root.bind("<KeyPress-M>", lambda e: self.toggle_mute())
        # Tk 里 "+" 不是合法 keysym，必须写 "plus"，否则窗口一建就抛 TclError
        self.root.bind("<KeyPress-plus>", lambda e: self.addtolist())
        
    def addtolist(self):
        if self.state == "quiz" or self.state == "finish": return
        
        t = word_note.load_data()
        t.append(word_note.make_word(self.lbl_word.cget("text"), self.lbl_cn.cget("text"), ""))
        self.next_word(t)

    def _on_next_key(self, event=None):
        if self.state == "quiz":
            return
        if self.state == "finish":
            return
        
        self.next_word()

    # ============================================================
    # 学习流程
    # ============================================================
    def show_word(self):
        self._remove_action_buttons()
        self._clear_quiz_widgets()

        if self.index >= len(self.queue):
            self._show_finish()
            return

        self.state = "learn"
        word, phonetic, pos, cn = self.queue[self.index]
        self.lbl_word.config(text=word, fg=self.WORD_COLOR,
                             font=("Helvetica", 68, "bold"))
        self.lbl_phonetic.config(text=phonetic, fg=self.PHONETIC_COLOR,
                                 font=("Helvetica", 24))
        self.lbl_pos.config(text=pos, fg=self.POS_COLOR,
                            font=("Helvetica", 22, "italic"))
        self.lbl_cn.config(text=cn, fg=self.CN_COLOR,
                           font=("Microsoft YaHei", 32))
        self.lbl_status.config(text="")
        self._update_progress()

        first_seen = self.index >= self.learned_count
        if first_seen and not self.paused:
            self.locked = True
            self.lbl_help.config(
                text="请先阅读单词，2.18 秒后即可继续…",
                fg="#fbbf24"
            )
            if self.unlock_after_id is not None:
                self.root.after_cancel(self.unlock_after_id)
            self.unlock_after_id = self.root.after(
                self.delay_ms, self._unlock_next
            )
            if self.after_id is not None:
                self.root.after_cancel(self.after_id)
            self.after_id = self.root.after(
                self.delay_ms, self._popup_buttons
            )
        else:
            self.locked = False
            self.lbl_help.config(
                text="空格/→/Enter：继续   ← ：上一个   F5：重听   "
                     "P：暂停/继续   M：静音   Esc：退出  +：加入单词笔记",
                fg="#e0e7ff"
            )

    def _unlock_next(self):
        self.unlock_after_id = None
        self.locked = False
        self.lbl_help.config(
            text="空格/→/Enter：继续   ← ：上一个   F5：重听   "
                 "P：暂停/继续   M：静音   Esc：退出  +：加入单词笔记",
            fg="#e0e7ff"
        )

    def _popup_buttons(self):
        self.after_id = None
        if self.state != "learn":
            return
        self.sound.popup()

        if self.btn_continue is None:
            self.btn_continue = tk.Button(
                self.root, text="继续学习  (空格)",
                font=("Microsoft YaHei", 18, "bold"),
                bg="#22c55e", fg="white",
                activebackground="#16a34a", activeforeground="white",
                bd=0, padx=32, pady=12, cursor="hand2",
                command=self.next_word
            )
            self.btn_continue.place(relx=0.03, rely=0.94, anchor="sw")

        if self.btn_exit is None:
            self.btn_exit = tk.Button(
                self.root, text="退出  (Esc)",
                font=("Microsoft YaHei", 18, "bold"),
                bg="#ef4444", fg="white",
                activebackground="#dc2626", activeforeground="white",
                bd=0, padx=32, pady=12, cursor="hand2",
                command=self.quit_app
            )
            self.btn_exit.place(relx=0.97, rely=0.94, anchor="se")

    def _remove_action_buttons(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        if self.unlock_after_id is not None:
            self.root.after_cancel(self.unlock_after_id)
            self.unlock_after_id = None
        if self.btn_continue is not None:
            self.btn_continue.destroy()
            self.btn_continue = None
        if self.btn_exit is not None:
            self.btn_exit.destroy()
            self.btn_exit = None
        if self.btn_review is not None:
            self.btn_review.destroy()
            self.btn_review = None

    def _update_progress(self):
        total = len(self.queue)
        done = min(self.index, total)
        pct = done / total if total else 0
        bar_len = 24
        filled = int(bar_len * pct)
        bar = "█" * filled + "░" * (bar_len - filled)
        pause = "   ⏸ 已暂停" if self.paused else ""
        mute = "   🔇" if self.sound.muted else ""
        self.lbl_progress.config(
            text=f"第 {done + 1 if done < total else total} / {total} 个  "
                 f"[{bar}]  {pct*100:.0f}%{pause}{mute}"
        )

    def next_word(self, t=None):
        if self.state == "quiz":
            return
        if self.state == "finish":
            return
        if self.index >= len(self.queue):
            return

        if self.locked:
            self.lbl_status.config(
                text=f"⏳ 请先阅读 {self.delay_ms/1000:.2f} 秒…",
                fg="#fbbf24"
            )

            return
        if t:
            word_note.save_data(t)
        self.sound.next_word()
        self.index += 1
        self.learned_count += 1

        # 每学完 10 个触发整批测验
        if (self.learned_count % 10 == 0
                and self.index < len(self.queue)
                and self.index >= 10):
            batch = self.queue[self.index - 10: self.index]
            self._start_quiz(batch)
            return

        self.show_word()

    def prev_word(self):
        if self.state == "quiz" or self.state == "finish":
            return
        if self.index <= 0:
            return
        self.sound.next_word()
        self.index -= 1
        if self.learned_count > 0:
            self.learned_count -= 1
        self.show_word()

    def replay(self):
        self.sound.replay()
        self.lbl_status.config(text="🔊 重听提示音", fg="#fbbf24")
        self.root.after(800, lambda: self.lbl_status.config(text=""))

    def toggle_pause(self):
        if self.state == "quiz" or self.state == "finish":
            return
        self.paused = not self.paused
        if self.paused:
            if self.after_id is not None:
                self.root.after_cancel(self.after_id)
                self.after_id = None
            if self.unlock_after_id is not None:
                self.root.after_cancel(self.unlock_after_id)
                self.unlock_after_id = None
            self.locked = False
            self.lbl_help.config(
                text="⏸ 已暂停，按 P 继续   Esc：退出", fg="#fbbf24"
            )
        else:
            if self.index < len(self.queue) and self.index >= self.learned_count:
                self.locked = True
                self.unlock_after_id = self.root.after(
                    self.delay_ms, self._unlock_next
                )
                self.after_id = self.root.after(
                    self.delay_ms, self._popup_buttons
                )
            self.lbl_help.config(
                text="空格/→/Enter：继续   ← ：上一个   F5：重听   "
                     "P：暂停/继续   M：静音   Esc：退出",
                fg="#e0e7ff"
            )
        self._update_progress()
        self.sound.replay()

    def toggle_mute(self):
        self.sound.muted = not self.sound.muted
        self._update_progress()
        if self.sound.muted:
            self.lbl_status.config(text="🔇 已静音", fg="#fbbf24")
        else:
            self.lbl_status.config(text="🔊 已开启音效", fg="#22c55e")
        self.root.after(1000, lambda: self.lbl_status.config(text=""))

    # ============================================================
    # 测验：整批 10 个词全部测
    # ============================================================
    def _clear_quiz_widgets(self):
        for b in self.quiz_buttons:
            try:
                b.destroy()
            except Exception:
                pass
        self.quiz_buttons = []
        self.quiz_data = None

    def _start_quiz(self, batch):
        """启动一批 10 个词的测验"""
        if not batch:
            self.show_word()
            return

        self.state = "quiz"
        self._remove_action_buttons()
        self._clear_quiz_widgets()

        self.quiz_batch = list(batch)
        self.quiz_order = list(batch)
        random.shuffle(self.quiz_order)
        self.quiz_pos = 0

        # 记录本轮首次测验的错词
        self._round_wrong_words = []
        self.first_pass_total += len(self.quiz_order)

        self._next_quiz_question()

    def _next_quiz_question(self):
        """显示下一题；如果本批已测完，进入错词重学或返回学习"""
        if self.quiz_pos >= len(self.quiz_order):
            self._finish_quiz_batch()
            return

        target = self.quiz_order[self.quiz_pos]
        # 交替出题
        quiz_type = "spelling" if self.quiz_pos % 2 == 0 else "meaning"
        if quiz_type == "spelling" and len(target[0]) < 3:
            quiz_type = "meaning"

        if quiz_type == "spelling":
            self._start_spelling_quiz(target)
        else:
            self._start_meaning_quiz(target, self.quiz_batch)

    def _start_spelling_quiz(self, target):
        word, phonetic, pos, cn = target
        n_blank = 2 if len(word) <= 5 else 3
        blank_idx = sorted(random.sample(range(len(word)), n_blank))
        correct = "".join(word[i].lower() for i in blank_idx)

        wrongs = set()
        tries = 0
        while len(wrongs) < 2 and tries < 200:
            tries += 1
            cand = "".join(random.choice(ALPHABET) for _ in range(n_blank))
            if cand != correct:
                wrongs.add(cand)
        options = list(wrongs) + [correct]
        random.shuffle(options)

        self.quiz_data = {
            "type": "spelling",
            "target": target,
            "correct": correct,
            "options": options,
        }

        self.lbl_word.config(text="✏️ 拼写测验", fg="#7c3aed",
                             font=("Microsoft YaHei", 30, "bold"))
        display = "   ".join(
            "_" if i in blank_idx else ch.upper()
            for i, ch in enumerate(word)
        )
        self.lbl_phonetic.config(text=display,
                                 font=("Helvetica", 38, "bold"),
                                 fg="#1e293b")
        self.lbl_pos.config(text=cn, font=("Microsoft YaHei", 20),
                            fg="#64748b")
        self.lbl_cn.config(text="请选择缺失的字母组合：",
                           font=("Microsoft YaHei", 16),
                           fg="#7c3aed")
        self.lbl_status.config(text="")
        self.lbl_progress.config(
            text=f"🎯 测验 {self.quiz_pos + 1} / {len(self.quiz_order)}"
        )

        self._make_option_buttons(options)

    def _start_meaning_quiz(self, target, batch):
        word, phonetic, pos, cn = target

        same_pos = [w for w in self.T if w[2] == pos and w[3] != cn]
        other = [w for w in self.T if w[3] != cn and w not in same_pos]
        pool = same_pos if len(same_pos) >= 3 else other
        if len(pool) < 3:
            pool = [w for w in self.T if w[3] != cn]

        wrongs = random.sample(pool, 3)
        options = [w[3] for w in wrongs] + [cn]
        random.shuffle(options)

        self.quiz_data = {
            "type": "meaning",
            "target": target,
            "correct": cn,
            "options": options,
        }

        self.lbl_word.config(text=word, fg="#7c3aed",
                             font=("Helvetica", 58, "bold"))
        self.lbl_phonetic.config(text="🎯 释义测验",
                                 font=("Microsoft YaHei", 20, "bold"),
                                 fg="#7c3aed")
        self.lbl_pos.config(text=pos, font=("Helvetica", 22, "italic"),
                            fg="#0d9488")
        self.lbl_cn.config(text="请选择正确的释义：",
                           font=("Microsoft YaHei", 16),
                           fg="#64748b")
        self.lbl_status.config(text="")
        self.lbl_progress.config(
            text=f"🎯 测验 {self.quiz_pos + 1} / {len(self.quiz_order)}"
        )

        self._make_option_buttons(options)

    def _make_option_buttons(self, options):
        for b in self.quiz_buttons:
            try:
                b.destroy()
            except Exception:
                pass
        self.quiz_buttons = []

        for opt in options:
            b = tk.Button(
                self.quiz_row, text=opt,
                font=("Microsoft YaHei", 18, "bold"),
                bg="#ffffff", fg="#1e293b",
                activebackground="#dbeafe",
                relief="flat", bd=0,
                padx=26, pady=12, cursor="hand2",
                command=lambda o=opt: self._on_quiz_answer(o)
            )
            b.pack(side="left", padx=10)
            self.quiz_buttons.append(b)

    def _on_quiz_answer(self, selected):
        if self.quiz_data is None:
            return
        correct = self.quiz_data["correct"]
        target = self.quiz_data["target"]

        for b in self.quiz_buttons:
            try:
                b.config(state="disabled")
            except Exception:
                pass

        self.quiz_count += 1
        is_review = getattr(self, "_in_review_quiz", False)

        if selected == correct:
            self.quiz_correct += 1
            if not is_review:
                self.first_pass_correct += 1
            self.sound.correct()
            self.lbl_status.config(text="✓ 回答正确！", fg="#22c55e")
            self.root.after(700, self._after_quiz_one)
        else:
            self.sound.error()
            # 答错提示：卡片下方、按钮上方
            self.lbl_status.config(
                text=f"✗ 答错了，正确答案：{correct}",
                fg="#ef4444"
            )
            # 高亮正确答案 + 用户选项
            for b in self.quiz_buttons:
                try:
                    if b.cget("text") == correct:
                        b.config(bg="#22c55e", fg="white")
                    elif b.cget("text") == selected:
                        b.config(bg="#ef4444", fg="white")
                except Exception:
                    pass

            # 记录错词（首次测验中的错词，用于本轮重学）
            if not is_review:
                if target not in self._round_wrong_words:
                    self._round_wrong_words.append(target)
            else:
                # 重学小测中还错 → 留在 review 队列
                if target not in self._review_wrong_words:
                    self._review_wrong_words.append(target)

            self.root.after(1400, self._after_quiz_one)

    def _after_quiz_one(self):
        """一题测完，进入下一题"""
        self._clear_quiz_widgets()
        self.quiz_pos += 1
        self._next_quiz_question()

    def _finish_quiz_batch(self):
        """本批 10 题测完，检查是否有错词要重学"""
        self._clear_quiz_widgets()
        self.quiz_batch = []
        self.quiz_order = []
        self.quiz_pos = 0

        if self._round_wrong_words:
            # ★ 立刻进入错词重学
            self.review_words = list(self._round_wrong_words)
            self.review_index = 0
            self.review_round = 1
            self._start_review_learn()
        else:
            self.state = "learn"
            self.lbl_status.config(
                text="✅ 本组全对！继续学习下一个 10 词", fg="#22c55e"
            )
            self.root.after(900, self.show_word)

    # ============================================================
    # 错词重学：先逐个显示重学，再针对错词小测
    # ============================================================
    def _start_review_learn(self):
        """开始一轮错词重学（逐个显示单词）"""
        if not self.review_words:
            self._after_review_finished()
            return

        self.state = "review_learn"
        self._remove_action_buttons()
        self._clear_quiz_widgets()

        word, phonetic, pos, cn = self.review_words[self.review_index]
        self.lbl_word.config(text=word, fg="#dc2626",
                             font=("Helvetica", 68, "bold"))
        self.lbl_phonetic.config(text=phonetic, fg=self.PHONETIC_COLOR,
                                 font=("Helvetica", 24))
        self.lbl_pos.config(text=pos, fg=self.POS_COLOR,
                            font=("Helvetica", 22, "italic"))
        self.lbl_cn.config(text=cn, fg=self.CN_COLOR,
                           font=("Microsoft YaHei", 32))
        self.lbl_progress.config(
            text=f"🔁 错词重学 第 {self.review_round} 轮  "
                 f"({self.review_index + 1} / {len(self.review_words)})"
        )
        self.lbl_status.config(text="看 1.2 秒后继续…", fg="#fbbf24")
        self.lbl_help.config(
            text="错词重学中，请认真看一遍", fg="#fbbf24"
        )

        # 轻锁 1.2 秒
        self.locked = True
        if self.unlock_after_id is not None:
            self.root.after_cancel(self.unlock_after_id)
        self.unlock_after_id = self.root.after(
            self.REREAD_DELAY_MS, self._unlock_review_next
        )

    def _unlock_review_next(self):
        self.unlock_after_id = None
        self.locked = False
        self.lbl_status.config(text="按 空格/→ 继续看下一个", fg="#22c55e")
        self.lbl_help.config(
            text="空格/→/Enter：下一个错词   Esc：退出", fg="#e0e7ff"
        )

    def _next_review_word(self):
        if self.locked:
            return
        self.review_index += 1
        if self.review_index >= len(self.review_words):
            # 重学完一轮，进入错词小测
            self._start_review_quiz()
        else:
            self._start_review_learn()

    def _start_review_quiz(self):
        """对错词进行小测（只测错词）"""
        self.state = "review_quiz"
        self._in_review_quiz = True
        self._review_wrong_words = []
        self.quiz_order = list(self.review_words)
        random.shuffle(self.quiz_order)
        self.quiz_pos = 0
        self._next_review_quiz_question()

    def _next_review_quiz_question(self):
        if self.quiz_pos >= len(self.quiz_order):
            self._in_review_quiz = False
            # 检查本轮还错哪些
            if self._review_wrong_words:
                if self.review_round >= self.MAX_REVIEW_ROUNDS:
                    # 达到最大轮数，剩下的进"最终错题本"
                    for w in self._review_wrong_words:
                        if w not in self.wrong_words:
                            self.wrong_words.append(w)
                    self.state = "learn"
                    self.lbl_status.config(
                        text=f"本轮仍有 {len(self._review_wrong_words)} 个未掌握，已加入错题本",
                        fg="#f59e0b"
                    )
                    self.root.after(1500, self.show_word)
                else:
                    # 进入下一轮重学
                    self.review_words = list(self._review_wrong_words)
                    self.review_index = 0
                    self.review_round += 1
                    self._start_review_learn()
            else:
                self.state = "learn"
                self.lbl_status.config(
                    text="🎉 错词全部掌握！继续学习", fg="#22c55e"
                )
                self.root.after(1000, self.show_word)
            return

        target = self.quiz_order[self.quiz_pos]
        # 错词小测：交替 拼写/释义
        quiz_type = "meaning" if self.quiz_pos % 2 == 0 else "spelling"
        if quiz_type == "spelling" and len(target[0]) < 3:
            quiz_type = "meaning"

        if quiz_type == "spelling":
            self._start_spelling_quiz(target)
        else:
            self._start_meaning_quiz(target, self.review_words)

    def _after_review_finished(self):
        """兜底：没有错词可重学"""
        self.state = "learn"
        self.show_word()

    # ============================================================
    # 完成 / 退出
    # ============================================================
    def _show_finish(self):
        self.state = "finish"
        self._remove_action_buttons()
        self._clear_quiz_widgets()

        acc = (self.first_pass_correct / self.first_pass_total * 100) \
            if self.first_pass_total else 0
        self.lbl_word.config(text="🎉 全部学完！", fg="#22c55e",
                             font=("Microsoft YaHei", 44, "bold"))
        self.lbl_phonetic.config(text="")
        self.lbl_pos.config(text="")
        self.lbl_cn.config(
            text=f"共学 {len(self.T)} 词  |  首次测验正确率 {acc:.0f}%  |  "
                 f"错题本 {len(self.wrong_words)} 词",
            font=("Microsoft YaHei", 18),
            fg="#334155"
        )
        self.lbl_status.config(text="")
        self.lbl_progress.config(text="")
        self.lbl_help.config(
            text="Esc：退出   空格/→/Enter：无效",
            fg="#e0e7ff"
        )
        self.sound.finish()

        if self.wrong_words:
            self.btn_review = tk.Button(
                self.root,
                text=f"复习错题本 ({len(self.wrong_words)})",
                font=("Microsoft YaHei", 18, "bold"),
                bg="#f59e0b", fg="white",
                activebackground="#d97706", activeforeground="white",
                bd=0, padx=32, pady=12, cursor="hand2",
                command=self._review_wrong_words
            )
            self.btn_review.place(relx=0.5, rely=0.86, anchor="center")

        if self.btn_exit is None:
            self.btn_exit = tk.Button(
                self.root, text="退出  (Esc)",
                font=("Microsoft YaHei", 18, "bold"),
                bg="#ef4444", fg="white",
                activebackground="#dc2626", activeforeground="white",
                bd=0, padx=32, pady=12, cursor="hand2",
                command=self.quit_app
            )
            self.btn_exit.place(relx=0.97, rely=0.94, anchor="se")

    def _review_wrong_words(self):
        if not self.wrong_words:
            return
        self.queue = self.wrong_words.copy()
        random.shuffle(self.queue)

        self.wrong_words = []
        self.index = 0
        self.learned_count = 0
        self.quiz_count = 0
        self.quiz_correct = 0
        self.first_pass_correct = 0
        self.first_pass_total = 0
        self.state = "learn"
        self._remove_action_buttons()
        self.lbl_help.config(
            text="空格/→/Enter：继续   ← ：上一个   F5：重听   "
                 "P：暂停/继续   M：静音   Esc：退出",
            fg="#e0e7ff"
        )
        self.show_word()

    def _cancel_timers(self):
        """取消所有挂起的定时器（幂等，可重复调用）。"""
        for attr in ('unlock_after_id', 'after_id'):
            tid = getattr(self, attr, None)
            if tid is not None:
                try:
                    self.root.after_cancel(tid)
                except Exception:
                    pass
                setattr(self, attr, None)

    def _on_window_destroy(self, event=None):
        # <Destroy> 会为每个子控件都触发一次，只在根窗口那次才清理
        if event is not None and getattr(event, 'widget', None) is not self.root:
            return
        self._cancel_timers()

    def quit_app(self):
        # 先取消挂起的定时器：窗口销毁后它们再触发，Tcl 会抛
        # "invalid command name ..._unlock_next"，打包后这类报错会被写进
        # debug.txt，看起来像程序出错。
        self._cancel_timers()
        self.sound.exit()
        
        # 正确读取→修改→写入，避免w+清空后读取空文件
        data_file = paths.app_dir() / "study_word_data.json"
        try:
            # 先读取已有数据
            if data_file.exists():
                with open(data_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        t = json.loads(content)
                    else:
                        t = {}
            else:
                t = {}
        except Exception:
            t = {}
        
        # 更新进度数据
        t["index_"+self.Name] = self.index
        t[self.Name] = self.T[self.index-1:]
        
        # 最后写入文件
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(t, f, ensure_ascii=False, indent=2)
            
        self.root.after(180, self.root.destroy)


# ============================================================
# 入口
# ============================================================
def run(T, name):
    root = tk.Tk()
    app = WordLearningApp(root, T, name)
    # 点右上角 X 也要走清理流程，否则挂起的定时器会在销毁后触发报错
    root.protocol('WM_DELETE_WINDOW', app.quit_app)
    root.mainloop()
if __name__ == "__main__":
    run(WORDS, name="default")
