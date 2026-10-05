#!/usr/bin/env python3
"""Assemble deux captures côte à côte (avant | après) pour vérifier une correction.

Usage : python3 tools/comparer-captures.py AVANT.png APRES.png SORTIE.png [titre]
"""
import sys
import os
from PIL import Image, ImageDraw, ImageFont

def comparer(avant, apres, sortie, titre=""):
    a, b = Image.open(avant).convert("RGB"), Image.open(apres).convert("RGB")
    marge, entete = 16, 34
    w = a.width + b.width + marge * 3
    h = max(a.height, b.height) + entete + marge
    im = Image.new("RGB", (w, h), (235, 228, 220))
    d = ImageDraw.Draw(im)
    police = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    f = ImageFont.truetype(police, 15) if os.path.exists(police) else None
    d.text((marge, 9), f"AVANT  {titre}", fill=(140, 30, 60), font=f)
    d.text((a.width + marge * 2, 9), "APRÈS", fill=(60, 120, 0), font=f)
    im.paste(a, (marge, entete)); im.paste(b, (a.width + marge * 2, entete))
    im.save(sortie)

if __name__ == "__main__":
    comparer(*sys.argv[1:5])
