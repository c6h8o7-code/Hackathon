# -*- coding: utf-8 -*-
"""
中考单词练习程序
- 内置中考核心词表
- 自动生成易错干扰项（同词性 + 同语义标签优先）
- tkinter 图形界面
"""

import tkinter as tk
import random
import re

def available():
    """本机是否能用 tkinter 画界面。"""
    return tk is not None


BG="#759CE6"

# ============================================================
# 第一部分：内置词表（中考核心词，格式：单词|词性|释义）
# ============================================================
RAW_WORDS = """
abandon|v.|放弃
ability|n.|能力
accept|v.|接受
achieve|v.|实现，达到
advantage|n.|优势，好处
advice|n.|建议
afraid|adj.|害怕的
agree|v.|同意
allow|v.|允许
ancient|adj.|古代的
angry|adj.|生气的
answer|v.|回答
appear|v.|出现
arrive|v.|到达
attention|n.|注意，关注
avoid|v.|避免
balance|n.|平衡
beautiful|adj.|美丽的
believe|v.|相信
borrow|v.|借入
brave|adj.|勇敢的
bright|adj.|明亮的
busy|adj.|忙碌的
careful|adj.|仔细的
celebrate|v.|庆祝
challenge|n.|挑战
change|v.|改变
choose|v.|选择
clever|adj.|聪明的
comfortable|adj.|舒适的
communicate|v.|交流
compare|v.|比较
confident|adj.|自信的
consider|v.|考虑
continue|v.|继续
courage|n.|勇气
create|v.|创造
culture|n.|文化
dangerous|adj.|危险的
decide|v.|决定
develop|v.|发展
difficult|adj.|困难的
discover|v.|发现
discuss|v.|讨论
education|n.|教育
encourage|v.|鼓励
enjoy|v.|享受
environment|n.|环境
excited|adj.|兴奋的
experience|n.|经验，经历
famous|adj.|著名的
forget|v.|忘记
freedom|n.|自由
friendly|adj.|友好的
generous|adj.|慷慨的
happy|adj.|高兴的
happiness|n.|幸福
helpful|adj.|有帮助的
honest|adj.|诚实的
important|adj.|重要的
improve|v.|改善
independent|adj.|独立的
interest|n.|兴趣
knowledge|n.|知识
language|n.|语言
lazy|adj.|懒惰的
memory|n.|记忆
necessary|adj.|必要的
nervous|adj.|紧张的
opportunity|n.|机会
patient|adj.|耐心的
polite|adj.|礼貌的
progress|n.|进步
protect|v.|保护
proud|adj.|自豪的
quiet|adj.|安静的
realize|v.|意识到
refuse|v.|拒绝
remember|v.|记得
responsible|adj.|负责的
sad|adj.|悲伤的
safe|adj.|安全的
serious|adj.|严肃的
share|v.|分享
silent|adj.|沉默的
success|n.|成功
suggest|v.|建议
support|v.|支持
surprised|adj.|惊讶的
tradition|n.|传统
understand|v.|理解
valuable|adj.|有价值的
volunteer|n.|志愿者
wisdom|n.|智慧
worry|v.|担心
"""

# ============================================================
# 第二部分：语义标签库（用于生成"像样"的干扰项）
# ============================================================
SEMANTIC_TAGS = {
    "emotion":   ["高兴", "悲伤", "生气", "害怕", "惊讶", "喜欢", "讨厌",
                  "担心", "满意", "失望", "兴奋", "紧张", "自豪", "幸福"],
    "cognition": ["想", "认为", "知道", "理解", "记得", "忘记", "决定",
                  "希望", "相信", "怀疑", "意识到", "考虑"],
    "action":    ["接受", "获得", "达到", "放弃", "允许", "回答", "出现",
                  "到达", "避免", "借入", "改变", "选择", "交流", "比较",
                  "继续", "创造", "发展", "发现", "讨论", "鼓励", "享受",
                  "改善", "保护", "拒绝", "分享", "支持", "担心"],
    "quality":   ["美丽", "勇敢", "明亮", "忙碌", "仔细", "聪明", "舒适",
                  "自信", "危险", "困难", "著名", "友好", "慷慨", "有帮助",
                  "诚实", "重要", "独立", "懒惰", "必要", "耐心", "礼貌",
                  "安静", "负责", "安全", "严肃", "沉默", "有价值", "古老"],
    "abstract":  ["能力", "优势", "建议", "注意", "平衡", "挑战", "勇气",
                  "文化", "教育", "环境", "经验", "自由", "知识", "语言",
                  "记忆", "机会", "进步", "成功", "传统", "智慧", "兴趣"],
    "people":    ["志愿者"],
}

# ============================================================
# 第三部分：工具函数
# ============================================================

def parse_raw_words(raw_text):
    """解析内置词表，返回 [(word, pos, meaning), ...]"""
    entries = []
    for line in raw_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) != 3:
            continue
        w, pos, m = parts[0].strip(), parts[1].strip(), parts[2].strip()
        if w and m:
            entries.append((w, pos, m))
    return entries


def get_tags(meaning):
    """返回释义命中的语义标签集合"""
    tags = set()
    for tag, keywords in SEMANTIC_TAGS.items():
        for kw in keywords:
            if kw in meaning:
                tags.add(tag)
                break
    return tags or {"other"}


def build_index(entries):
    """构建词性索引、标签索引、释义索引"""
    pos_map = {e[0]: e[1] for e in entries}
    tag_map = {e[0]: get_tags(e[2]) for e in entries}
    meaning_map = {e[0]: e[2] for e in entries}
    return pos_map, tag_map, meaning_map


def generate_distractors(target, entries, pos_map, tag_map, meaning_map,
                         n=3, length_tolerance=2):
    """
    为 target=(word, pos, meaning) 生成 n 个干扰释义。
    优先级：同词性+同标签 > 同词性 > 任意
    """
    t_word, t_pos, t_meaning = target
    t_tags = tag_map.get(t_word, {"other"})
    t_len = len(t_meaning)

    def collect(same_pos, same_tag):
        pool = []
        for w, p, m in entries:
            if w == t_word or m == t_meaning:
                continue
            if same_pos and p != t_pos:
                continue
            if same_tag and not (tag_map.get(w, set()) & t_tags):
                continue
            pool.append(m)
        return list(set(pool))

    # 按优先级累积候选
    candidates = collect(True, True)
    if len(candidates) < n * 4:
        candidates += collect(True, False)
    if len(candidates) < n * 4:
        candidates += collect(False, False)
    candidates = list(set(candidates))

    # 长度过滤：优先选与正确答案长度接近的
    close = [c for c in candidates if abs(len(c) - t_len) <= length_tolerance]
    pool = close if len(close) >= n else candidates

    # 打乱后抽取
    random.shuffle(pool)

    # 校验：去重、不包含正确答案
    result = []
    for c in pool:
        if c == t_meaning or c in result:
            continue
        if t_meaning in c or c in t_meaning:
            continue
        result.append(c)
        if len(result) == n:
            break

    # 兜底：如果仍不足 n 个，从全部释义里随机补
    if len(result) < n:
        all_meanings = [m for _, _, m in entries if m != t_meaning and m not in result]
        random.shuffle(all_meanings)
        for m in all_meanings:
            if m not in result and t_meaning not in m and m not in t_meaning:
                result.append(m)
            if len(result) == n:
                break

    return result[:n]


def build_word_bank(entries):
    """生成完整题库：[(word, correct, [wrong1, wrong2, wrong3]), ...]"""
    pos_map, tag_map, meaning_map = build_index(entries)
    bank = []
    for e in entries:
        wrongs = generate_distractors(e, entries, pos_map, tag_map, meaning_map, n=3)
        if len(wrongs) >= 3:
            bank.append((e[0], e[2], wrongs[:3]))
    return bank


# ============================================================
# 第四部分：图形界面
# ============================================================

class WordQuizApp:
    def __init__(self, root, word_bank):
        self.root = root
        self.root.title("中考单词练习")
        self.root.geometry("760x520")
        self.root.configure(bg="#f0f8ff")
        self.root.attributes("-fullscreen", True)
        self.root.resizable(False, False)

        self.all_words = word_bank
        self.remaining = word_bank.copy()
        self.total = len(word_bank)

        self.current = None
        self.correct = None
        self.buttons = []
        self.timer_id = None
        self.locked = False

        self._build_ui()

        if self.total == 0:
            self.word_label.config(text="题库为空", fg="#e74c3c")
        else:
            self.next_question()

    def _build_ui(self):
        # 进度
        self.progress_label = tk.Label(
            self.root, text="", font=("微软雅黑", 11),
            bg="#f0f8ff", fg="#888888"
        )
        self.progress_label.pack(pady=(15, 0))

        # 提示
        self.tip_label = tk.Label(
            self.root, text="请选择正确的释义：",
            font=("微软雅黑", 14), bg="#f0f8ff", fg="#333333"
        )
        self.tip_label.pack(pady=(5, 5))

        # 单词
        self.word_label = tk.Label(
            self.root, text="", font=("Arial", 42, "bold"),
            bg="#f0f8ff", fg="#1e3a8a"
        )
        self.word_label.pack(pady=10)

        # 选项区
        self.options_frame = tk.Frame(self.root, bg="#f0f8ff")
        self.options_frame.pack(pady=30, fill="x", padx=40)

        # 状态
        self.status_label = tk.Label(
            self.root, text="", font=("微软雅黑", 12),
            bg="#f0f8ff", fg="#666666"
        )
        self.status_label.pack(pady=5)

        # 退出按钮
        self.quit_btn = tk.Button(
            self.root, text="退出", font=("微软雅黑", 12),
            bg="#e74c3c", fg="white", activebackground="#c0392b",
            relief="flat", padx=20, pady=5, cursor="hand2",
            command=self.quit_app
        )
        self.quit_btn.place(relx=1.0, rely=1.0, anchor="se", x=-15, y=-15)

    def next_question(self):
        self.clear_buttons()
        self.locked = False
        self.status_label.config(text="")

        if not self.remaining:
            self.word_label.config(text="全部完成！", fg="#27ae60",
                                   font=("Arial", 30, "bold"))
            self.tip_label.config(text="恭喜你完成了所有单词！")
            self.progress_label.config(text="")
            return

        done = self.total - len(self.remaining)
        self.progress_label.config(text=f"进度：{done} / {self.total}")

        self.current, self.correct, wrongs = random.choice(self.remaining)

        self.word_label.config(text=self.current, fg="#1e3a8a",
                               font=("Arial", 42, "bold"))
        self.tip_label.config(text="请选择正确的释义：")

        options = wrongs[:3] + [self.correct]
        random.shuffle(options)

        for opt in options:
            btn = tk.Button(
                self.options_frame,
                text=opt,
                font=("微软雅黑", 15),
                bg="#ffffff", fg="#333333",
                activebackground="#dbeafe",
                relief="ridge", bd=2,
                width=10, pady=12,
                cursor="hand2",
            )
            btn.config(command=lambda o=opt, b=btn: self.check_answer(o, b))
            btn.pack(side="left", expand=True, padx=8)
            self.buttons.append(btn)

    def check_answer(self, selected, btn):
        if self.locked:
            return

        if selected == self.correct:
            self.locked = True
            btn.config(bg="#27ae60", fg="white")
            self.status_label.config(text="✓ 回答正确！", fg="#27ae60")
            self.clear_buttons()

            self.word_label.config(
                text=f"{self.current}\n{self.correct}",
                fg="#27ae60", font=("Arial", 28, "bold")
            )
            self.tip_label.config(text="记住这个单词！")

            for item in self.remaining:
                if item[0] == self.current:
                    self.remaining.remove(item)
                    break

            self.timer_id = self.root.after(2000, self.next_question)
        else:
            btn.config(bg="#e74c3c", fg="white", state="disabled")
            self.status_label.config(text="✗ 错误，再试试！", fg="#e74c3c")
            self.root.after(300, lambda: self.remove_button(btn))

    def remove_button(self, btn):
        if btn in self.buttons:
            self.buttons.remove(btn)
            btn.destroy()

    def clear_buttons(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        for btn in self.buttons:
            btn.destroy()
        self.buttons = []

    def quit_app(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        self.root.destroy()


# ============================================================
# 第五部分：主入口
# ============================================================

def run():
    random.seed()  # 随机种子

    # 1. 解析内置词表
    entries = parse_raw_words(RAW_WORDS)
    print(f"解析到 {len(entries)} 个单词")

    # 2. 生成题库（含自动干扰项）
    bank = build_word_bank(entries)
    print(f"生成 {len(bank)} 道题目")

    # 4. 启动界面
    root = tk.Tk()
    app = WordQuizApp(root, bank)
    root.mainloop()
if __name__ == "__main__":
    run()