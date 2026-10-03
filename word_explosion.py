# -*- coding: utf-8 -*-
"""word_explosion —— 单词爆炸物理动画（第一版实现 · 纯 Canvas · 带爆炸音效）

按「第一版」的做法重写：全部用 tkinter Canvas 原生图元绘制，**不引入 Pillow、
不做贴图、不做旋转**，因此：

    * 不会出现贴图透明角落导致的「字母周围黑框」；
    * 打包成 exe 不会多出 PIL 依赖。

动画流程：
    单词从天上带重力落下 → 砸到地面（金色闪光 + 碎片迸射 + 整屏震动）
    → 每个字母变成独立刚体四散飞开 → 落地反弹 + 摩擦减速 → 淡出 → on_done

在「第一版」基础上保留的两项功能：
    * 爆炸音效：炸开瞬间播放 res/boom.wav。Windows 用内置 winsound，
      macOS 用 afplay，Linux 用 paplay/aplay/ffplay/mpg123，都不依赖第三方库；
      没有音效文件或没有播放器时退回系统提示音，任何异常都不会影响动画。
    * 屏幕震动：正弦衰减 + 随机扰动，字母砸地会追加二次震动；
      只施加增量位移，震动结束精确归零，画面不会跑偏。

外观：不画任何投影、不给字母描深色边框（此前出现过「字母周围黑框」）。

对外接口：

    trigger(parent, word, duration_ms=None, on_done=None, **style)
    play_sound(parent=None, sound_file=None)
    set_sound_enabled(flag) / sound_enabled()
    is_active()

典型用法：

    from word_explosion import trigger
    trigger(self.root, self.current, on_done=self.next_round)
"""

import math
import os
import random
import shutil
import subprocess
import sys
import time

try:
    import tkinter as tk
except ImportError:                      # 无 tkinter 时模块仍可被 import
    tk = None


# ================================================================ 音效
SOUND_NAME = "boom.wav"

_SOUND_ENABLED = True
_SOUND_PATH_CACHE = {}
_SOUND_FAILS = 0                # 连续失败次数
_SOUND_MAX_FAILS = 3            # 连续失败这么多次后自动静音，避免反复刷日志

# Linux / 类 Unix 下依次尝试的播放器：(可执行文件, 附加参数)
_LINUX_PLAYERS = (
    ("paplay", []),
    ("aplay", ["-q"]),
    ("ffplay", ["-nodisp", "-autoexit", "-loglevel", "quiet"]),
    ("mpg123", ["-q"]),
)


def default_sound_path():
    """定位爆炸音效文件；找不到返回空串。结果会缓存。"""
    if "path" in _SOUND_PATH_CACHE:
        return _SOUND_PATH_CACHE["path"]

    cands = []
    try:                                  # 工程统一的资源定位器
        import A
        cands.append(str(A.resource("res", SOUND_NAME)))
    except Exception:
        pass
    here = os.path.dirname(os.path.abspath(__file__))
    roots = [here, getattr(sys, "_MEIPASS", None), os.path.dirname(here)]
    if getattr(sys, "frozen", False):
        roots.append(os.path.dirname(os.path.abspath(sys.executable)))
    for d in roots:
        if d:
            cands.append(os.path.join(d, "res", SOUND_NAME))
            cands.append(os.path.join(d, SOUND_NAME))

    found = ""
    for c in cands:
        if c and os.path.isfile(c):
            found = c
            break
    _SOUND_PATH_CACHE["path"] = found
    return found


def _spawn(cmd):
    """静默启动一个播放进程（不阻塞、不弹控制台）。"""
    devnull = open(os.devnull, "wb")
    try:
        kwargs = dict(stdout=devnull, stderr=devnull, stdin=subprocess.DEVNULL)
        if sys.platform.startswith("win"):
            kwargs["creationflags"] = 0x08000000        # CREATE_NO_WINDOW
        subprocess.Popen(cmd, **kwargs)
    except Exception:
        devnull.close()
        return False
    return True


def _play_file(path):
    """播放一个音频文件；成功返回 True。

    任何环节出问题都只返回 False，绝不抛异常。
    """
    if not path or not os.path.isfile(path):
        return False

    if sys.platform.startswith("win"):
        # 1) 标准库 winsound，异步播放，不阻塞界面
        try:
            import winsound
            winsound.PlaySound(
                path,
                winsound.SND_FILENAME | winsound.SND_ASYNC
                | winsound.SND_NODEFAULT)
            return True
        except Exception:
            pass
        # 2) 纯 ctypes 调 Win32 提示音，完全不依赖任何第三方库
        try:
            import ctypes
            ctypes.windll.user32.MessageBeep(0)
            return True
        except Exception:
            return False

    if sys.platform == "darwin":
        exe = shutil.which("afplay")
        if exe:
            return _spawn([exe, path])
        return False

    for name, args in _LINUX_PLAYERS:                # Linux / 其他类 Unix
        exe = shutil.which(name)
        if exe:
            return _spawn([exe] + args + [path])
    return False


def play_sound(parent=None, sound_file=None):
    """播放爆炸音效。

    优先级：指定的 sound_file > 自动定位的 res/boom.wav。
    找不到文件或没有播放器时退回系统提示音（parent.bell()），保证任何环境下
    都"有个响"；全程包裹异常处理，绝不抛到调用方、绝不阻塞主线程。
    连续多次都失败时自动静音，避免每次爆炸都刷一堆日志。
    """
    global _SOUND_ENABLED, _SOUND_FAILS
    if not _SOUND_ENABLED:
        return False

    ok = False
    try:
        path = sound_file or default_sound_path()
        ok = _play_file(path)
    except Exception as exc:                          # noqa: BLE001
        print("音效播放失败: %s" % exc)
        ok = False

    if not ok and parent is not None:
        try:
            parent.bell()
            ok = True
        except Exception:
            ok = False

    if ok:
        _SOUND_FAILS = 0
    else:
        _SOUND_FAILS += 1
        if _SOUND_FAILS >= _SOUND_MAX_FAILS:
            _SOUND_ENABLED = False
            print("音效连续 %d 次不可用，已自动静音" % _SOUND_FAILS)
    return ok


def set_sound_enabled(flag):
    """全局开关音效（返回设置后的状态）。"""
    global _SOUND_ENABLED, _SOUND_FAILS
    _SOUND_ENABLED = bool(flag)
    if _SOUND_ENABLED:
        _SOUND_FAILS = 0
    return _SOUND_ENABLED


def sound_enabled():
    return _SOUND_ENABLED


# ================================================================ 配置
DEFAULT = dict(
    # ---- 物理 ----
    gravity=1800.0,                 # 重力加速度（像素/秒²）
    ground_friction=0.82,           # 地面摩擦系数
    restitution=0.55,               # 地面反弹系数
    air_drag=0.008,                 # 空气阻力
    letter_push=1100.0,             # 字母四散时的最大水平推力
    letter_up=900.0,                # 字母四散时的最大上抛速度
    fall_speed=520.0,               # 单词整体下落初速度（向下为正）
    impact_jitter=0,                # 已废弃：改为由屏幕震动实现，保留键仅为兼容

    # ---- 外观（不画投影、不描边）----
    bg="",                          # 画布底色，空字符串=用 parent 背景
    word_color="#c84646",           # 下落阶段单词颜色
    letter_color="#e74c3c",         # 爆炸后字母颜色
    letter_outline="",              # 字母描边：留空=不描边（避免深色边框）
    flash_color="#ffd04a",          # 爆炸瞬间闪光
    smoke_color="#d6d6d6",          # 碎片/烟雾粒子颜色
    font_family="Arial Black",      # 单词/字母字体
    font_size=84,                   # 下落单词字号；爆炸后的字母会略大一点
    letter_scale=1.15,              # 爆炸后字母相对于下落字号的放大倍数

    # ---- 屏幕震动（炸开瞬间整屏抖动，字母砸地追加二次震动）----
    shake_power=30.0,               # 起震幅度（像素），越大越猛
    shake_ms=560.0,                 # 单次震动持续时间（毫秒）
    shake_decay=2.2,                # 幅度衰减指数，越大衰减越快
    shake_freq=10.0,                # 抖动频率（每秒来回次数）
    shake_vertical=0.75,            # 纵向幅度相对横向的比例
    shake_random=0.22,              # 叠加的随机分量比例（让震动不那么机械）
    shake_impact_boost=0.45,        # 每次字母砸地追加的幅度比例
    shake_impact_max=1.6,           # 追加幅度的上限倍率

    # ---- 音效 ----
    sound=True,                     # False = 本次爆炸静音
    sound_file="",                  # 留空 = 自动定位 res/boom.wav

    # ---- 时间 ----
    drop_ms=700,                    # 下落耗时（毫秒）
    freeze_ms=120,                  # 落地后定格多久再炸开
    settle_ms=1900,                 # 炸开后字母飞散多久再进入淡出
    flash_ms=180,                   # 爆炸闪光持续时长
    fade_ms=600,                    # 淡出时长

    # ---- 兼容键 ----
    # 本版本恒为纯 Canvas、不旋转，此键仅为兼容旧调用/旧注释保留（传入亦无效）。
    letter_rotate=False,

    # ---- 触发 ----
    fail_threshold=3,               # 连续错几次触发（对外用，方便主界面显示提示）
)


# ================================================================ 刚体
class _Body:
    """二维刚体（文字 + AABB 近似碰撞）。"""

    __slots__ = ("x", "y", "vx", "vy", "w", "h", "rot", "vrot",
                 "text", "font_cfg", "font_size", "color", "outline",
                 "canvas_id", "outline_id", "alive")

    def __init__(self, x, y, text, font_cfg, color, outline,
                 vx=0.0, vy=0.0, font_size=None):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.w, self.h = _measure(text, font_cfg)
        self.rot, self.vrot = 0.0, 0.0          # 不旋转：恒为 0
        self.text = text
        self.font_cfg = font_cfg
        self.font_size = font_size if font_size is not None else (
            font_cfg[1] if isinstance(font_cfg, tuple) else 84)
        self.color = color
        self.outline = outline
        self.canvas_id = None
        self.outline_id = None
        self.alive = True


# ================================================================ 辅助
def _font(size, family=None, bold=True):
    if tk is None:
        return ("Arial", size, "bold")
    fam = family or DEFAULT["font_family"]
    return (fam, size, "bold" if bold else "normal")


_FONT_CACHE = {}


def _measure(text, font_cfg):
    """估算一段文字的宽/高（像素）。

    tkinter 没有统一的 measure 接口，这里用「等比估计 + 字号经验值」做一个
    足够接近的值用于物理碰撞；真正渲染时用 Canvas.create_text 自动定位。
    """
    key = (text, font_cfg)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    size = font_cfg[1] if isinstance(font_cfg, tuple) else int(font_cfg)
    # 英文平均宽度约为 字号 * 0.62，高度约 1.2 倍字号
    w = int(len(text) * size * 0.62) + size // 2
    h = int(size * 1.2)
    _FONT_CACHE[key] = (w, h)
    return w, h


def _hex_to_rgb(h):
    h = (h or "").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return (0, 0, 0)
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return (0, 0, 0)


def _color_to_rgb(widget, color):
    try:
        r, g, b = widget.winfo_rgb(color)
        return (r // 257, g // 257, b // 257)
    except Exception:
        return _hex_to_rgb(color)


# ================================================================ 爆炸主体
class Explosion:
    """一次完整的「下落 → 砸地 → 字母四散 → 粒子 → 淡出」动画。"""

    def __init__(self, parent, word, on_done=None, **style):
        if tk is None:
            raise RuntimeError("tkinter 不可用")
        self.parent = parent
        self.word = word
        self.on_done = on_done
        self.cfg = dict(DEFAULT)
        self.cfg.update({k: v for k, v in style.items() if k in DEFAULT})

        self.t0 = time.perf_counter()
        self._last = self.t0
        self._job = None
        self.ended = False
        self.phase = "drop"

        self.parent.update_idletasks()
        try:
            self.W = parent.winfo_width()
            self.H = parent.winfo_height()
        except Exception:
            self.W, self.H = 900, 700
        if self.W < 200 or self.H < 200:
            self.W, self.H = max(self.W, 900), max(self.H, 700)

        self.ground_y = self.H - 40

        # 画布铺满父容器
        self.canvas = tk.Canvas(parent, width=self.W, height=self.H,
                                highlightthickness=0, bd=0)
        if self.cfg["bg"]:
            self.canvas.configure(bg=self.cfg["bg"])
        else:
            try:
                self.canvas.configure(bg=parent.cget("bg"))
            except tk.TclError:
                self.canvas.configure(bg="#f0f8ff")
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        try:
            self.canvas.tkraise()
        except tk.TclError:
            pass

        # 粒子（爆炸碎片/烟）与字母刚体
        self.particles = []
        self.bodies = []

        # 下落阶段：整词作为一个 Body 从屏幕外掉下来
        font_word = _font(self.cfg["font_size"], self.cfg["font_family"])
        self.drop_body = _Body(
            x=self.W / 2 + random.randint(-120, 120),
            y=-60,
            text=self.word,
            font_cfg=font_word,
            color=self.cfg["word_color"],
            outline="",
            vy=self.cfg["fall_speed"],
        )
        half = self.drop_body.w / 2                    # 把 X 夹紧到屏幕内
        self.drop_body.x = max(half + 20,
                               min(self.W - half - 20, self.drop_body.x))

        self.drop_body_id = None
        print(self.drop_body_id)

        self.flash_id = None
        self.flash_start = None

        # 屏幕震动状态：_shake_x / _shake_y 记录「已经施加出去」的偏移量
        self._shake_start = None
        self._shake_phase = random.uniform(0, math.tau)
        self._shake_boost = 0.0
        self._shake_x = 0.0
        self._shake_y = 0.0
        self._impact_shakes = 0

        self._fade_t = 0.0
        self.t_settle_end = 0.0

        self._schedule()

    # ------------------------------------------------------------ 阶段切换
    def _start_freeze(self):
        self.phase = "freeze"
        self.t_freeze_end = time.perf_counter() + self.cfg["freeze_ms"] / 1000.0
        self.drop_body.y = self.ground_y - self.drop_body.h / 2 - 2
        self.drop_body.vy = 0

    def _start_boom(self):
        self.phase = "boom"
        self.flash_id = self.canvas.create_rectangle(
            0, 0, self.W, self.H, fill=self.cfg["flash_color"], outline="",
            tags="flash")
        self.flash_start = time.perf_counter()
        self.start_shake()
        self._play_boom_sound()
        # seself.drop_body_id
        
        if self.drop_body_id is not None:
            self.canvas.delete(self.drop_body_id)
            
            self.drop_body_id = None

        letters = list(self.word)
        n = len(letters)
        font_letter = _font(int(self.cfg["font_size"] * self.cfg["letter_scale"]),
                            self.cfg["font_family"])
        cx = self.drop_body.x
        cy = self.drop_body.y
        spacing = self.cfg["font_size"] * self.cfg["letter_scale"] * 0.72
        total_w = spacing * (n - 1)
        start_x = cx - total_w / 2
        push = self.cfg["letter_push"]
        up = self.cfg["letter_up"]
        for i, ch in enumerate(letters):
            if not ch.strip():
                continue
            lx = start_x + i * spacing + random.uniform(-4, 4)
            ly = cy + random.uniform(-6, 6)
            vx = random.uniform(-push, push)
            vy = -random.uniform(up * 0.4, up)
            b = _Body(lx, ly, ch.upper(), font_letter,
                      self.cfg["letter_color"], self.cfg["letter_outline"],
                      vx=vx, vy=vy, font_size=font_letter[1])
            self.bodies.append(b)

        self._spawn_particles(cx, cy, count=40 + n * 4)
        self.t_settle_end = time.perf_counter() + self.cfg["settle_ms"] / 1000.0

    def _spawn_particles(self, cx, cy, count):
        smoke = self.cfg["smoke_color"]
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(200, 900)
            r = random.uniform(2, 6)
            life = random.uniform(0.4, 1.1)
            self.particles.append(dict(
                x=cx, y=cy,
                vx=math.cos(ang) * spd,
                vy=math.sin(ang) * spd - 200,
                r=r,
                color=smoke if random.random() < 0.6 else self.cfg["letter_color"],
                life=life, maxlife=life,
                id=None,
            ))

    # ------------------------------------------------------------ 音效
    def _play_boom_sound(self):
        """炸开瞬间播放爆炸音效（失败静默忽略，绝不影响动画）。"""
        cfg = self.cfg
        if not cfg.get("sound", True) or not _SOUND_ENABLED:
            return
        try:
            play_sound(self.parent, cfg.get("sound_file") or None)
        except Exception as exc:                       # noqa: BLE001
            print("音效播放失败: %s" % exc)

    # ------------------------------------------------------------ 屏幕震动
    def start_shake(self, power=None):
        """起震（或在已有震动上追加）。power 为 None 时用配置里的初始幅度。"""
        cfg = self.cfg
        if cfg["shake_power"] <= 0 and power is None:
            return
        self._shake_start = time.perf_counter()
        self._shake_phase = random.uniform(0, math.tau)
        self._shake_boost = 0.0 if power is None else float(power)

    def add_impact_shake(self):
        """字母砸地时调用：追加一次震动，幅度按配置比例递增并有上限。"""
        cfg = self.cfg
        if cfg["shake_impact_boost"] <= 0:
            return
        if self._impact_shakes >= 8:                  # 落地太密就不再叠加
            return
        self._impact_shakes += 1
        self._shake_boost = min(cfg["shake_impact_max"],
                                self._shake_boost + cfg["shake_impact_boost"])
        now = time.perf_counter()
        if (self._shake_start is None
                or now - self._shake_start > cfg["shake_ms"] / 1000.0):
            self._shake_start = now                   # 震完又落地，就重新起震
            self._shake_phase = random.uniform(0, math.tau)

    def _shake_offset(self, now):
        """返回此刻的震动偏移 (dx, dy)。震动结束返回 (0, 0)。"""
        cfg = self.cfg
        if self._shake_start is None:
            return 0.0, 0.0
        span = max(0.001, cfg["shake_ms"] / 1000.0)
        t = (now - self._shake_start) / span
        if t >= 1.0:
            self._shake_boost = 0.0
            return 0.0, 0.0
        amp = cfg["shake_power"] * (1.0 + self._shake_boost)
        amp *= (1.0 - t) ** cfg["shake_decay"]        # 幅度随时间衰减
        w = math.tau * cfg["shake_freq"]
        ph = self._shake_phase
        rnd = cfg["shake_random"]
        dx = amp * math.sin(w * t + ph)
        dy = amp * cfg["shake_vertical"] * math.cos(w * t * 0.83 + ph * 1.7)
        if rnd:
            dx += random.uniform(-amp * rnd, amp * rnd)
            dy += random.uniform(-amp * rnd, amp * rnd)
        return dx, dy

    def _apply_shake(self, now):
        """把震动偏移施加到画布：只移动增量，因此震动结束会精确归位。"""
        dx, dy = self._shake_offset(now)
        mx, my = dx - self._shake_x, dy - self._shake_y
        self._shake_x, self._shake_y = dx, dy
        if mx or my:
            try:
                self.canvas.move(tk.ALL, mx, my)
            except tk.TclError:
                return
        # 全屏闪光矩形固定在 (0,0)-(W,H) 不跟着抖，否则边缘会露缝
        if self.flash_id is not None:
            try:
                self.canvas.coords(self.flash_id, 0, 0, self.W, self.H)
            except tk.TclError:
                pass

    # ------------------------------------------------------------ 物理 & 渲染
    def _step(self):
        if self.ended:
            return
        now = time.perf_counter()
        dt = max(0.001, min(0.05, now - self._last))
        self._last = now
        g = self.cfg["gravity"]

        if self.phase == "drop":
            self.drop_body.vy += g * dt
            self.drop_body.y += self.drop_body.vy * dt
            if self.drop_body.y >= self.ground_y - self.drop_body.h / 2 - 2:
                self.drop_body.y = self.ground_y - self.drop_body.h / 2 - 2
                self._start_freeze()
            self._draw_word()

        elif self.phase == "freeze":
            self._draw_word()
            if now >= self.t_freeze_end:
                self._start_boom()

        elif self.phase == "boom":
            drag = self.cfg["air_drag"]
            rest = self.cfg["restitution"]
            fric = self.cfg["ground_friction"]

            # 闪光淡出
            if self.flash_id is not None:
                elapsed = (now - self.flash_start) * 1000
                if elapsed > self.cfg["flash_ms"]:
                    self.canvas.delete(self.flash_id)
                    self.flash_id = None
                else:
                    alpha = 1.0 - elapsed / self.cfg["flash_ms"]
                    shade = int(255 - (1 - alpha) * 40)
                    try:
                        self.canvas.itemconfig(
                            self.flash_id,
                            fill="#%02x%02x%02x"
                            % (255, max(180, shade), int(80 + alpha * 120)))
                    except tk.TclError:
                        pass

            any_moving = False
            for b in self.bodies:
                if not b.alive:
                    continue
                b.vy += g * dt
                b.vx *= (1 - drag)
                b.vy *= (1 - drag)
                b.x += b.vx * dt
                b.y += b.vy * dt

                floor = self.ground_y - b.h / 2
                if b.y >= floor:
                    b.y = floor
                    if b.vy > 0:
                        b.vy = -b.vy * rest
                        b.vx *= fric
                        if abs(b.vy) > 120:
                            self.add_impact_shake()
                            self.particles.append(dict(
                                x=b.x, y=self.ground_y,
                                vx=random.uniform(-80, 80),
                                vy=-random.uniform(50, 160),
                                r=random.uniform(2, 4),
                                color=self.cfg["smoke_color"],
                                life=0.35, maxlife=0.35,
                                id=None,
                            ))
                    else:
                        b.vy = 0

                if b.x < b.w / 2:
                    b.x = b.w / 2
                    b.vx = -b.vx * 0.6
                elif b.x > self.W - b.w / 2:
                    b.x = self.W - b.w / 2
                    b.vx = -b.vx * 0.6

                if abs(b.vx) > 8 or abs(b.vy) > 8:
                    any_moving = True
                self._draw_body(b)

            self._step_particles(dt)

            if now >= self.t_settle_end or not any_moving:
                self.phase = "fade"
                self._fade_t = 0.0

        elif self.phase == "fade":
            self._fade_t += dt * (1.0 / max(0.001, self.cfg["fade_ms"] / 1000.0))
            alpha = self._fade_t
            self._step_particles(dt)
            for b in self.bodies:
                if not b.alive:
                    continue
                b.vy += g * dt * 0.5
                b.y += b.vy * dt * 0.5
                b.x += b.vx * dt * 0.5
                floor = self.ground_y - b.h / 2
                if b.y >= floor:
                    b.y = floor
                    b.vy = 0
                    b.vx *= 0.7
                self._draw_body(b, alpha=alpha)
            if alpha >= 1.0:
                self._finish()
                return

        self._apply_shake(now)
        self._schedule()

    def _step_particles(self, dt):
        g = self.cfg["gravity"] * 0.4
        alive = []
        for p in self.particles:
            p["life"] -= dt
            if p["life"] <= 0:
                if p["id"] is not None:
                    try:
                        self.canvas.delete(p["id"])
                    except tk.TclError:
                        pass
                continue
            p["vy"] += g * dt
            p["vx"] *= 0.99
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            if p["y"] > self.ground_y:
                p["y"] = self.ground_y
                p["vy"] = -p["vy"] * 0.4
                p["vx"] *= 0.7
            alpha = max(0.0, p["life"] / p["maxlife"])
            r = p["r"] * (0.6 + 0.4 * alpha)
            if p["id"] is None:
                try:
                    p["id"] = self.canvas.create_oval(
                        p["x"] - r, p["y"] - r, p["x"] + r, p["y"] + r,
                        fill=p["color"], outline="")
                except tk.TclError:
                    continue
            else:
                try:
                    self.canvas.coords(p["id"],
                                       p["x"] - r, p["y"] - r,
                                       p["x"] + r, p["y"] + r)
                except tk.TclError:
                    continue
            alive.append(p)
        self.particles = alive

    # ------------------------------------------------------------ 绘制
    def _draw_word(self):
        b = self.drop_body
        if b.canvas_id is None:
            b.canvas_id = self.canvas.create_text(
                b.x, b.y, text=b.text, font=b.font_cfg,
                fill=b.color, anchor="center")
            self.drop_body_id = b.canvas_id
        else:
            self.canvas.coords(b.canvas_id, b.x, b.y)

    def _draw_body(self, b, alpha=0.0):
        """字母用 Canvas 文本绘制（不旋转、不贴图、无投影、无描边）。"""
        color = b.color
        if alpha > 0:
            r1, g1, b1 = _hex_to_rgb(b.color)
            r2, g2, b2 = self._bg_rgb
            a = min(1.0, alpha)
            color = "#%02x%02x%02x" % (int(r1 + (r2 - r1) * a),
                                       int(g1 + (g2 - g1) * a),
                                       int(b1 + (b2 - b1) * a))
        try:
            if b.canvas_id is None:
                if b.outline:                      # 描边（默认关闭）
                    b.outline_id = self.canvas.create_text(
                        b.x + 1, b.y + 1, text=b.text, font=b.font_cfg,
                        fill=b.outline, anchor="center")
                b.canvas_id = self.canvas.create_text(
                    b.x, b.y, text=b.text, font=b.font_cfg,
                    fill=color, anchor="center")
                if b.outline_id is not None:
                    self.canvas.tag_lower(b.outline_id, b.canvas_id)
            else:
                self.canvas.coords(b.canvas_id, b.x, b.y)
                self.canvas.itemconfig(b.canvas_id, fill=color)
                if b.outline_id is not None:
                    self.canvas.coords(b.outline_id, b.x + 1, b.y + 1)
                    self.canvas.itemconfig(b.outline_id, fill=b.outline)
        except tk.TclError:
            b.alive = False

    @property
    def _bg_rgb(self):
        if not hasattr(self, "_bg_cache"):
            try:
                self._bg_cache = _color_to_rgb(self.canvas,
                                               self.canvas.cget("bg"))
            except Exception:
                self._bg_cache = (240, 248, 255)
        return self._bg_cache

    # ------------------------------------------------------------ 调度 & 收尾
    def _schedule(self):
        try:
            self._job = self.parent.after(16, self._tick)
        except tk.TclError:
            self._finish()

    def _tick(self):
        self._job = None
        try:
            self._step()
        except tk.TclError:
            self._finish()
        except Exception as exc:                      # noqa: BLE001
            # 单帧渲染出问题也不让整个流程闪退
            print("爆炸动画帧异常: %s" % exc)
            self._finish()

    def _finish(self):
        if self.ended:
            return
        self.ended = True
        # 把残余的震动偏移归零，避免画面停在偏移位置
        if self._shake_x or self._shake_y:
            try:
                self.canvas.move(tk.ALL, -self._shake_x, -self._shake_y)
            except tk.TclError:
                pass
        self._shake_x = self._shake_y = 0.0
        if self._job is not None:
            try:
                self.parent.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        try:
            self.canvas.destroy()
        except tk.TclError:
            pass
        cb, self.on_done = self.on_done, None
        if callable(cb):
            try:
                cb()
            except Exception as exc:                  # noqa: BLE001
                print("爆炸动画回调失败: %s" % exc)


# ================================================================ 对外入口
_ACTIVE = []


def trigger(parent, word, duration_ms=None, on_done=None, **style):
    """触发一次单词爆炸动画。

    parent      : tkinter 容器（root 或 Frame）
    word        : 要炸的单词
    duration_ms : 动画总时长；给定时按 25% / 5% / 70% 切分到
                  下落、定格、飞散三个阶段；None 则用 DEFAULT 里的时间
    on_done     : 动画结束（画布已销毁）后的回调，比如进入下一题
    **style     : 覆盖 DEFAULT 中的任意外观/物理参数
    """
    if tk is None:
        if callable(on_done):
            parent.after(10, on_done)
        return None

    for a in list(_ACTIVE):                 # 同一时刻只留一个爆炸
        try:
            a._finish()
        except Exception:
            pass
    _ACTIVE.clear()

    if duration_ms is not None:
        style["drop_ms"] = int(duration_ms * 0.25)
        style["freeze_ms"] = int(duration_ms * 0.05)
        style["settle_ms"] = int(duration_ms * 0.70)

    ex = Explosion(parent, word, on_done=_wrap_done(on_done), **style)
    _ACTIVE.append(ex)
    return ex


def _wrap_done(cb):
    def _wrapped():
        if _ACTIVE:
            _ACTIVE.pop(0)
        if callable(cb):
            cb()
    return _wrapped


def is_active():
    return bool(_ACTIVE)


# ================================================================ 单独预览
if __name__ == "__main__":
    if tk is None:
        print("缺少 tkinter，无法预览")
        raise SystemExit(1)
    root = tk.Tk()
    root.title("word_explosion 预览（纯 Canvas · 无旋转 · 带音效）")
    root.geometry("900x700")
    root.configure(bg="#f0f8ff")
    tk.Label(root, text="按空格炸下一个单词",
             font=("微软雅黑", 14), bg="#f0f8ff", fg="#333").pack(pady=30)

    words = ["explode", "BOMB", "english", "STUDY", "mistake", "WRONG",
             "hello", "world", "physics", "CRASH"]
    idx = [0]

    def boom(_evt=None):
        w = words[idx[0] % len(words)]
        idx[0] += 1
        trigger(root, w, font_size=72, on_done=lambda: print("done:", w))

    root.bind("<space>", boom)
    root.bind("<Escape>", lambda e: root.destroy())
    root.after(300, boom)
    root.mainloop()
