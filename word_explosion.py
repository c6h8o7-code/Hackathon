# -*- coding: utf-8 -*-
"""word_explosion —— 单词爆炸物理动画

一个纯 tkinter Canvas 实现的 2D 质点物理引擎，专门用来做「单词从天上掉下来
砸到地面后，字母被撞得四散飞溅」这种动画效果。不依赖 pymunk / pymunk 等
第三方库，打包到 exe 不会多出额外依赖。

对外主要只需要一个函数：

    trigger(parent, word, duration_ms=2800, on_done=None, **style)

        parent    : tkinter 容器（一般是 root / 顶层 Frame）
        word      : 要炸的英文单词（会按字母切分）
        duration_ms : 动画总时长，到点自动销毁并调用 on_done
        on_done   : 动画结束后回调（比如触发下一题）

典型用法（点错第 N 次后用）：

    from word_explosion import trigger
    trigger(self.root, self.current, on_done=self.next_round)
"""

import math
import random
import time

try:
    import tkinter as tk
except ImportError:                 # 极端环境下没 tkinter 也别让 import 崩
    tk = None


# ---------------------------------------------------------------- 默认参数
# 这些参数都能在 trigger(...) 里通过关键字参数覆盖
DEFAULT = dict(
    # 物理
    gravity=1800.0,               # 重力加速度（像素/秒²），1800 看起来比较有冲击力
    ground_friction=0.82,         # 地面摩擦系数（水平速度保留比例）
    restitution=0.55,             # 地面反弹系数
    air_drag=0.008,               # 空气阻力（与速度成正比）
    letter_push=1100.0,           # 字母四散时的最大水平推力
    letter_up=850.0,              # 字母四散时的最大上抛速度
    letter_spin=8.0,              # 字母四散时的最大角速度（弧度/秒）
    fall_speed=520.0,             # 单词整体下落初速度（向下为正）
    impact_jitter=6,              # 落地时的水平抖动（像素）

    # 外观
    bg="",                        # 画布底色，空字符串=透明（用 parent 背景）
    word_color="#c84646",         # 下落阶段单词颜色
    letter_color="#e74c3c",       # 爆炸后字母颜色
    letter_outline="#7b1d1d",     # 字母描边
    flash_color="#ffd04a",        # 爆炸瞬间闪光
    smoke_color="#d6d6d6",        # 碎片/烟雾粒子颜色
    font_family="Arial Black",    # 单词/字母字体
    font_size=84,                 # 下落单词字号；爆炸后的字母会略大一点
    letter_scale=1.15,            # 爆炸后字母相对于下落字号的放大倍数

    # 时间
    drop_ms=700,                  # 下落耗时（毫秒）
    freeze_ms=120,                # 落地后定格多久再炸开
    settle_ms=1900,               # 炸开后字母飞散多久再结束
    flash_ms=180,                 # 爆炸闪光持续时长

    # 触发
    fail_threshold=3,             # 连续错几次触发（对外用，方便主界面显示提示）
)


# ---------------------------------------------------------------- 质点
class _Body:
    """二维刚体（文字 + AABB 近似碰撞）。"""
    __slots__ = ("x", "y", "vx", "vy", "w", "h", "rot", "vrot",
                 "text", "font_cfg", "color", "outline",
                 "canvas_id", "shadow_id", "alive")

    def __init__(self, x, y, text, font_cfg, color, outline,
                 vx=0.0, vy=0.0, vrot=0.0, rot=0.0):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.w, self.h = _measure(text, font_cfg)
        self.rot, self.vrot = float(rot), float(vrot)
        self.text = text
        self.font_cfg = font_cfg
        self.color = color
        self.outline = outline
        self.canvas_id = None
        self.shadow_id = None
        self.alive = True


# ---------------------------------------------------------------- 辅助
def _font(size, family=None, bold=True):
    if tk is None:
        return ("Arial", size, "bold")
    fam = family or DEFAULT["font_family"]
    return (fam, size, "bold" if bold else "normal")


_FONT_CACHE = {}

def _measure(text, font_cfg):
    """估算一段文字的宽/高（像素）。tkinter 没有 measure 的统一接口，
    这里用「等比估计 + 字号经验值」做一个足够接近的值用于物理碰撞；
    真正渲染时用 Canvas.create_text 自动调整位置。"""
    key = (text, font_cfg)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    size = font_cfg[1] if isinstance(font_cfg, tuple) else int(font_cfg)
    # 英文大小写平均宽度约为 字号 * 0.62，高度约 1.2 倍字号
    w = int(len(text) * size * 0.62) + size // 2
    h = int(size * 1.2)
    _FONT_CACHE[key] = (w, h)
    return w, h


# ---------------------------------------------------------------- 爆炸主体
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

        # 时间
        self.t0 = time.perf_counter()
        self.ended = False
        self.phase = "drop"            # drop / freeze / boom / settle / done

        # 先更新一次几何尺寸再布局
        self.parent.update_idletasks()
        try:
            self.W = parent.winfo_width()
            self.H = parent.winfo_height()
        except Exception:
            self.W, self.H = 900, 700
        if self.W < 200 or self.H < 200:
            self.W, self.H = max(self.W, 900), max(self.H, 700)

        self.ground_y = self.H - 40     # 地面线

        # 画布：全屏盖在 parent 之上
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

        # 粒子（爆炸碎片/烟）
        self.particles = []            # [(x,y,vx,vy,r,color,life,maxlife)]
        # 字母刚体
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
        # 把 X 夹紧到屏幕内
        half = self.drop_body.w / 2
        self.drop_body.x = max(half + 20, min(self.W - half - 20, self.drop_body.x))

        # 闪光线 ID
        self.flash_id = None
        self.flash_start = None

        # 阴影（地面）
        self.shadow_id = self.canvas.create_oval(
            self.drop_body.x - 60, self.ground_y - 4,
            self.drop_body.x + 60, self.ground_y + 4,
            fill="#444444", outline="", stipple="gray25"
        )

        self._schedule()

    # ------------------------------------------------------------ 阶段切换
    def _start_freeze(self):
        self.phase = "freeze"
        self.t_freeze_end = time.perf_counter() + self.cfg["freeze_ms"] / 1000.0
        # 让单词落在地面：y 调整到刚好接触
        self.drop_body.y = self.ground_y - self.drop_body.h / 2 - 2
        self.drop_body.vy = 0

    def _start_boom(self):
        self.phase = "boom"
        # 闪一下
        self.flash_id = self.canvas.create_rectangle(
            0, 0, self.W, self.H, fill=self.cfg["flash_color"], outline="")
        self.flash_start = time.perf_counter()
        # 爆炸瞬间的抖动
        self.canvas.move(tk.ALL, random.randint(-self.cfg["impact_jitter"],
                                                self.cfg["impact_jitter"]), 0)

        # 把整词删掉，替换成散开的字母
        if self.drop_body.canvas_id is not None:
            self.canvas.delete(self.drop_body.canvas_id)
            self.drop_body.canvas_id = None

        # 为每个字母生成一个刚体，带随机速度与旋转
        letters = list(self.word)
        n = len(letters)
        font_letter = _font(int(self.cfg["font_size"] * self.cfg["letter_scale"]),
                            self.cfg["font_family"])
        cx = self.drop_body.x
        cy = self.drop_body.y
        spacing = self.cfg["font_size"] * 0.72
        total_w = spacing * (n - 1)
        start_x = cx - total_w / 2
        push = self.cfg["letter_push"]
        up = self.cfg["letter_up"]
        spin = self.cfg["letter_spin"]
        for i, ch in enumerate(letters):
            lx = start_x + i * spacing + random.uniform(-4, 4)
            ly = cy + random.uniform(-6, 6)
            vx = random.uniform(-push, push)
            vy = -random.uniform(up * 0.4, up)     # 向上炸开
            vrot = random.uniform(-spin, spin)
            b = _Body(lx, ly, ch.upper(), font_letter,
                      self.cfg["letter_color"], self.cfg["letter_outline"],
                      vx=vx, vy=vy, vrot=vrot, rot=random.uniform(-0.4, 0.4))
            self.bodies.append(b)

        # 粒子：碎片 + 烟雾
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

    # ------------------------------------------------------------ 物理 & 渲染
    def _step(self):
        if self.ended:
            return
        now = time.perf_counter()
        dt = max(0.001, min(0.05, now - getattr(self, "_last", now)))
        self._last = now

        g = self.cfg["gravity"]

        # 阶段：下落
        if self.phase == "drop":
            self.drop_body.vy += g * dt
            self.drop_body.y += self.drop_body.vy * dt
            if self.drop_body.y >= self.ground_y - self.drop_body.h / 2 - 2:
                self.drop_body.y = self.ground_y - self.drop_body.h / 2 - 2
                self._start_freeze()
            self._draw_word()

        # 阶段：定格（视觉缓冲）
        elif self.phase == "freeze":
            self._draw_word()
            if now >= self.t_freeze_end:
                self._start_boom()

        # 阶段：炸开后飞散
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
                    # Tk 不支持 alpha 色，但可以通过换更浅的黄来近似
                    shade = int(255 - (1 - alpha) * 40)
                    try:
                        self.canvas.itemconfig(
                            self.flash_id,
                            fill="#%02x%02x%02x" % (255, max(180, shade), int(80 + alpha * 120)))
                    except tk.TclError:
                        pass

            # 字母物理
            any_moving = False
            for b in self.bodies:
                if not b.alive:
                    continue
                # 重力 + 空气阻力
                b.vy += g * dt
                b.vx *= (1 - drag)
                b.vy *= (1 - drag)
                b.x += b.vx * dt
                b.y += b.vy * dt
                b.rot += b.vrot * dt
                b.vrot *= 0.98

                # 地面碰撞
                floor = self.ground_y - b.h / 2
                if b.y >= floor:
                    b.y = floor
                    if b.vy > 0:
                        b.vy = -b.vy * rest
                        b.vx *= fric
                        b.vrot *= fric
                        # 微弱二次粒子（落地尘）
                        if abs(b.vy) > 120:
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
                # 边界反弹（左右墙）
                if b.x < b.w / 2:
                    b.x = b.w / 2
                    b.vx = -b.vx * 0.6
                elif b.x > self.W - b.w / 2:
                    b.x = self.W - b.w / 2
                    b.vx = -b.vx * 0.6

                if abs(b.vx) > 8 or abs(b.vy) > 8 or abs(b.vrot) > 0.05:
                    any_moving = True
                self._draw_body(b)

            # 粒子
            self._step_particles(dt)

            # 到点结束
            if now >= self.t_settle_end:
                self.phase = "fade"
                self._fade_out(0.0)

        # 阶段：淡出
        elif self.phase == "fade":
            alpha = getattr(self, "_fade_t", 0.0)
            alpha += dt * 1.6
            self._fade_t = alpha
            # 粒子继续
            self._step_particles(dt)
            # 字母继续跑但加速淡出
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

        self._schedule()

    def _step_particles(self, dt):
        g = self.cfg["gravity"] * 0.4
        alive = []
        for p in self.particles:
            p["vy"] += g * dt
            p["vx"] *= (1 - self.cfg["air_drag"] * 2)
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt
            if p["life"] <= 0 or p["y"] > self.H + 10:
                if p["id"] is not None:
                    try: self.canvas.delete(p["id"])
                    except tk.TclError: pass
                continue
            alpha = max(0.0, p["life"] / p["maxlife"])
            x, y, r = p["x"], p["y"], p["r"]
            pid = p["id"]
            fill = p["color"]
            rr = max(0.5, r * alpha)
            if pid is None:
                pid = self.canvas.create_oval(x - rr, y - rr, x + rr, y + rr,
                                              fill=fill, outline="")
                p["id"] = pid
            else:
                try:
                    self.canvas.coords(pid, x - rr, y - rr, x + rr, y + rr)
                except tk.TclError:
                    continue
            alive.append(p)
        self.particles = alive

    # ------------------------------------------------------------ 渲染
    def _draw_word(self):
        b = self.drop_body
        if b.canvas_id is None:
            b.canvas_id = self.canvas.create_text(
                b.x, b.y, text=b.text, font=b.font_cfg,
                fill=b.color, anchor="center")
        else:
            self.canvas.coords(b.canvas_id, b.x, b.y)
        # 地面阴影跟着走
        try:
            sw = max(20, 60 - (self.ground_y - b.y) * 0.12)
            self.canvas.coords(self.shadow_id,
                               b.x - sw, self.ground_y - 3,
                               b.x + sw, self.ground_y + 3)
        except tk.TclError:
            pass

    def _draw_body(self, b, alpha=0.0):
        if b.canvas_id is None:
            b.canvas_id = self.canvas.create_text(
                b.x, b.y, text=b.text, font=b.font_cfg,
                fill=b.color, anchor="center")
            # 描边：用叠加一个同字、偏移 1 像素的暗色字近似
            if b.outline:
                b.shadow_id = self.canvas.create_text(
                    b.x + 1, b.y + 1, text=b.text, font=b.font_cfg,
                    fill=b.outline, anchor="center")
                self.canvas.tag_lower(b.shadow_id, b.canvas_id)
        else:
            try:
                self.canvas.coords(b.canvas_id, b.x, b.y)
                # 简单"旋转"用角度字距模拟：文字旋转 tkinter 本身不支持，
                # 这里只做轻微倾斜观感（通过缩放字间距 + 斜体无法做到，
                # 所以旋转我们不实际旋转画布文字，避免引入 PIL 依赖；
                # 通过水平抖动让视觉上有"翻滚"错觉）
                dx = math.sin(b.rot) * 3
                self.canvas.coords(b.canvas_id, b.x + dx, b.y)
                if b.shadow_id is not None:
                    self.canvas.coords(b.shadow_id, b.x + dx + 1, b.y + 1)
            except tk.TclError:
                return
        # 淡出
        if alpha > 0 and b.canvas_id is not None:
            try:
                # 用透明度近似：把文字颜色向背景色插值
                bg_rgb = self._bg_rgb
                fg = b.color
                r1, g1, b1 = _hex_to_rgb(fg)
                r2, g2, b2 = bg_rgb
                a = min(1.0, alpha)
                c = "#%02x%02x%02x" % (int(r1 + (r2 - r1) * a),
                                       int(g1 + (g2 - g1) * a),
                                       int(b1 + (b2 - b1) * a))
                self.canvas.itemconfig(b.canvas_id, fill=c)
            except (tk.TclError, ValueError):
                pass

    @property
    def _bg_rgb(self):
        if not hasattr(self, "_bg_cache"):
            try:
                col = self.canvas.cget("bg")
                self._bg_cache = _color_to_rgb(self.canvas, col)
            except Exception:
                self._bg_cache = (240, 248, 255)
        return self._bg_cache

    def _fade_out(self, t):
        self._fade_t = t

    # ------------------------------------------------------------ 调度 & 收尾
    def _schedule(self):
        self._last = time.perf_counter()
        if not self.ended:
            self._after_id = self.parent.after(16, self._step)    # ≈ 60fps

    def _finish(self):
        if self.ended:
            return
        self.ended = True
        try:
            if hasattr(self, "_after_id"):
                self.parent.after_cancel(self._after_id)
        except Exception:
            pass
        try:
            self.canvas.destroy()
        except Exception:
            pass
        cb = self.on_done
        self.on_done = None
        if callable(cb):
            try:
                cb()
            except Exception as exc:
                print("word_explosion on_done 回调异常: %s" % exc)


def _hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _color_to_rgb(widget, color):
    """winfo_rgb 返回 0-65535，转回 0-255。"""
    try:
        r, g, b = widget.winfo_rgb(color)
        return r >> 8, g >> 8, b >> 8
    except Exception:
        return 240, 248, 255


# ---------------------------------------------------------------- 对外入口
_ACTIVE = []            # 同一时刻只允许一个爆炸在跑，避免叠多层

def trigger(parent, word, duration_ms=None, on_done=None, **style):
    """触发一次单词爆炸。返回 Explosion 实例（仅供调试）。"""
    if tk is None:
        if callable(on_done):
            parent.after(10, on_done)
        return None
    # 防止重复触发
    for a in _ACTIVE:
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


# ---------------------------------------------------------------- 单独预览
if __name__ == "__main__":
    root = tk.Tk()
    root.title("word_explosion 预览")
    root.geometry("900x700")
    root.configure(bg="#f0f8ff")
    tk.Label(root, text="按空格炸下一个单词", font=("微软雅黑", 14),
             bg="#f0f8ff", fg="#333").pack(pady=30)

    words = ["explode", "BOMB", "english", "STUDY", "mistake", "WRONG",
             "hello", "world", "physics", "CRASH"]
    idx = [0]

    def boom(_evt=None):
        w = words[idx[0] % len(words)]
        idx[0] += 1
        trigger(root, w, font_size=72,
                on_done=lambda: print("done:", w))

    root.bind("<space>", boom)
    root.bind("<Escape>", lambda e: root.destroy())
    root.after(300, boom)
    root.mainloop()
