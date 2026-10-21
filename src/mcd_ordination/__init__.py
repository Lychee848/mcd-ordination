#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mcd-ordination · 麦门行传
把「麦当劳用户行为」当作 prompt，生成一套只属于你的麦门卡证。
"""

__version__ = "0.1.0"
__all__ = ["features", "piety", "canon", "sign", "gacha", "styles",
           "deck", "order", "render_svg", "render_png", "animate", "mcp"]


def main():
    from .cli import main as _main
    return _main()
