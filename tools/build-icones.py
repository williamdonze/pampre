#!/usr/bin/env python3
"""Génère les icônes de l'appli (écran d'accueil) dans icones/ : Pépin sur fond crème.

Rendu par Chromium (Playwright) depuis le même dessin que mascot() dans index.html.
  icone-192.png, icone-512.png    manifeste, usage « any »
  icone-maskable-512.png          manifeste, usage « maskable » (Android découpe en rond ou en goutte : marge de 20 %)
  apple-touch-icon.png            iOS (180 px, opaque : iOS arrondit lui-même les coins)
"""
import os
from playwright.sync_api import sync_playwright

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'   # Chromium préinstallé (environnement cloud), sinon celui de Playwright

FOND, RAISIN, FEUILLE, TIGE = "#FBF5EC", "#8B1E3F", "#58A700", "#3F7A00"
BAIES = [(38, 40), (60, 36), (82, 40), (28, 62), (92, 62), (44, 92), (76, 92), (60, 104)]
PEPIN = (f'<path d="M60 18c8-14 30-14 36-4-12-2-22 2-30 10z" fill="{FEUILLE}"/>'
         f'<path d="M60 26V12" stroke="{TIGE}" stroke-width="5" stroke-linecap="round"/>'
         + "".join(f'<circle cx="{x}" cy="{y}" r="15" fill="{RAISIN}"/>' for x, y in BAIES)
         + f'<circle cx="60" cy="66" r="34" fill="{RAISIN}"/><circle cx="48" cy="44" r="7" fill="#fff" opacity=".18"/>'
         '<circle cx="47" cy="64" r="8" fill="#fff"/><circle cx="73" cy="64" r="8" fill="#fff"/>'
         '<circle cx="49" cy="65" r="4" fill="#2a0a14"/><circle cx="75" cy="65" r="4" fill="#2a0a14"/>'
         '<circle cx="38" cy="76" r="5" fill="#ff8fab" opacity=".55"/><circle cx="82" cy="76" r="5" fill="#ff8fab" opacity=".55"/>'
         '<path d="M50 77q10 11 20 0" stroke="#3a0d1d" stroke-width="3.5" fill="#fff" stroke-linecap="round"/>')

def svg(taille, part):
    """Pépin (dessin de 120 × 110 environ, de y = 4 à 119) centré, occupant `part` du côté"""
    s = taille * part / 116; tx = (taille - 120 * s) / 2; ty = (taille - 116 * s) / 2 - 4 * s
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{taille}" height="{taille}" viewBox="0 0 {taille} {taille}">'
            f'<rect width="100%" height="100%" fill="{FOND}"/><g transform="translate({tx:.2f} {ty:.2f}) scale({s:.4f})">{PEPIN}</g></svg>')

ICONES = {"icone-192.png": (192, .78), "icone-512.png": (512, .78), "icone-maskable-512.png": (512, .58), "apple-touch-icon.png": (180, .74)}

with sync_playwright() as p:
    nav = p.chromium.launch(**({'executable_path': CHROME} if os.path.exists(CHROME) else {}))
    page = nav.new_page()
    for nom, (taille, part) in ICONES.items():
        page.set_viewport_size({"width": taille, "height": taille})
        page.set_content(f'<style>html,body{{margin:0}}</style>{svg(taille, part)}')
        page.screenshot(path=f"icones/{nom}", clip={"x": 0, "y": 0, "width": taille, "height": taille})
        print("icones/" + nom)
    nav.close()
