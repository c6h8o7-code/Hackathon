# -*- coding: utf-8 -*-
"""
path_helper —— 统一的路径解析

开发时（python 十八单词.py）与 PyInstaller 打包后（十八单词.exe）都能正确
找到资源，区别在于两处：

    开发时：  脚本所在目录
    打包后：  exe 所在目录（可写） + 内部解包目录 sys._MEIPASS（只读）

对外提供四个函数：

    app_dir()            可写目录：exe / 脚本所在目录，用户数据放这里
    bundle_dir()         只读资源目录：打包后是解包目录，开发时=脚本目录
    resource(*parts)     找一个只读资源，exe 同级优先、其次打包内部
    ensure_lib_dir(name) 返回可写词库目录，打包后首次运行把内置词库释放出来
"""

import pathlib
import shutil
import sys


def _log(msg):
    """安全打印：打包成无控制台的 exe 后 sys.stdout 可能是 None"""
    try:
        if sys.stdout is not None:
            print(msg)
    except Exception:
        pass


def is_frozen():
    """是否运行在 PyInstaller 打包出来的 exe 里"""
    return bool(getattr(sys, "frozen", False))


def app_dir():
    """可写目录。

    - 打包后：exe 所在目录（用户看得见、可以往里加词库）
    - 开发时：本文件所在目录
    """
    if is_frozen():
        return pathlib.Path(sys.executable).resolve().parent
    return pathlib.Path(__file__).resolve().parent


def bundle_dir():
    """随 exe 一起封装的只读资源目录。

    - 打包后：临时解包目录 sys._MEIPASS
    - 开发时：与本文件同级
    """
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return pathlib.Path(base)
    return pathlib.Path(__file__).resolve().parent


def resource(*parts):
    """定位只读资源（icon.ico、gif、词库等）。

    查找顺序：
        1. exe / 脚本同级的同名文件（方便用户替换）
        2. 打包内部封装的副本
    两处都没有时返回第 1 个候选路径，便于在报错信息里提示。
    """
    rel = pathlib.Path(*parts)
    outside = app_dir() / rel
    if outside.exists():
        return outside
    inside = bundle_dir() / rel
    if inside.exists():
        return inside
    return outside


def ensure_lib_dir(name="dev_english"):
    """返回可写的词库目录。

    打包后首次运行时，把随 exe 封装的词库复制到 exe 同级目录，这样：
        - 用户能看到 dev_english 文件夹
        - 可以自己往里丢新的 .json 词库
        - 已存在的文件不会被覆盖（保留用户改动）
    若 exe 目录不可写（例如装在 Program Files），退回使用封装目录。
    """
    target = app_dir() / name
    src = bundle_dir() / name

    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError:
        # 目录不可写，只能用封装内部的那份
        return src if src.is_dir() else target

    # 首次运行：把内置词库释放到 exe 旁边（不覆盖已有文件）
    if src.is_dir() and src.resolve() != target.resolve():
        for f in sorted(src.glob("*.json")):
            dst = target / f.name
            if dst.exists():
                continue
            try:
                shutil.copy2(f, dst)
            except OSError as exc:
                _log("释放词库 %s 失败: %s" % (f.name, exc))

    return target
