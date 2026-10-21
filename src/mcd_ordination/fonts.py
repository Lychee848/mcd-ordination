#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fonts.py —— 跨平台字体解析

公开仓库里不能出现本机的 macOS 字体绝对路径，也不能假设用户装了宋体。
这里按族（family）给出候选列表，取第一个存在的；全都没命中就返回 None，
渲染器会退回 Pillow 默认字体（西文可读、中文缺字），而不是直接崩掉。

覆盖：macOS / Linux(Noto, WenQuanYi) / Windows(微软雅黑, 黑体)
可用环境变量强制指定：
    MCD_FONT_CJK=/path/to/YourFont.ttc
"""
import os

CANDIDATES = {
    "cjk": [
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ],
    "display": [
        "/System/Library/Fonts/Supplemental/Copperplate.ttc",
        "/System/Library/Fonts/Supplemental/Trajan Pro.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "C:/Windows/Fonts/georgiab.ttf",
    ],
    "serif": [
        "/System/Library/Fonts/Supplemental/Baskerville.ttc",
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "C:/Windows/Fonts/times.ttf",
    ],
    "numeral": [
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "C:/Windows/Fonts/georgia.ttf",
        "C:/Windows/Fonts/times.ttf",
    ],
}


def resolve(family: str = "cjk") -> str:
    env = os.environ.get(f"MCD_FONT_{family.upper()}")
    if env and os.path.exists(env):
        return env
    for path in CANDIDATES.get(family, []):
        if os.path.exists(path):
            return path
    return ""


def report() -> dict:
    """给 doctor 子命令用：告诉你哪一族没找到"""
    out = {}
    for fam in CANDIDATES:
        p = resolve(fam)
        out[fam] = p or "（未找到，回退默认字体）"
    return out
