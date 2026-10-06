from playwright.sync_api import sync_playwright
import json, os, re
os.makedirs('captures', exist_ok=True)
errs=[]; SP='captures/'
exact = lambda t: re.compile(r'^\s*' + re.escape(t) + r'\s*$')   # texte exact (« Musigny » ne doit pas trouver « Chambolle-Musigny »)
with sync_playwright() as p:
    CHROME='/opt/pw-browsers/chromium-1194/chrome-linux/chrome'   # Chromium préinstallé (environnement cloud), sinon celui de Playwright
    b=p.chromium.launch(**({'executable_path':CHROME} if os.path.exists(CHROME) else {}))
    pg=b.new_page(viewport={'width':400,'height':860})
    pg.on('pageerror', lambda e: errs.append(('pageerror',str(e))))
    pg.goto('http://localhost:8765/index.html'); pg.wait_for_timeout(800)
    # quiz : on répond juste à tout, à partir des données (un WRONG = question ou corrigé incohérent)
    def faire_quiz(lid):
        data=pg.evaluate(f"LEVELS[{lid}].quiz.questions")
        pg.evaluate(f"startQuiz({lid})"); pg.wait_for_timeout(300)
        for i,q in enumerate(data):
            t=q['type']
            if t in('qcm','indices') or (t=='etiquette' and q['mode']=='qcm'):
                if t=='indices': pg.click('.next-clue button')
                pg.locator('.choice').nth(q['bonne']).click()
                if t=='indices' and lid==1: pg.screenshot(path=SP+'indices.png')
            elif t=='vf':
                pg.click('.choice[data-v="%d"]'%(1 if q['bonne'] else 0))
            elif t=='etiquette':
                pg.click('.lbl .ch[data-champ="%s"]'%q['cible'])
            elif t=='ordre':
                for it in q['items']:
                    pg.locator('.pool .chip:not(.used)', has_text=exact(it)).first.click()
            elif t=='assoc':
                for a,bb in q['paires']:
                    pg.locator('.l .chip', has_text=exact(a)).first.click(); pg.locator('.r .chip', has_text=exact(bb)).first.click()
            elif t=='tri':
                for txt,c in q['items']:
                    pg.locator('.pool .chip', has_text=exact(txt)).first.click(); pg.locator('.cat').nth(c).click(position={'x':8,'y':8})
            elif t=='carte':
                # toucher la carte à la position réelle du lieu
                x,y=pg.evaluate("([la,lo,f])=>{const [x,y]=fondDe(f).proj(la,lo);const s=document.querySelector('.session .map-box > svg');const pt=s.createSVGPoint();pt.x=x;pt.y=y;const q=pt.matrixTransform(s.getScreenCTM());return [q.x,q.y]}", [q['entry']['lat'],q['entry']['lon'],q['entry'].get('fond')])
                pg.mouse.click(x,y); pg.wait_for_timeout(100)
            pg.click('[data-check]'); pg.wait_for_timeout(100)
            ok=pg.locator('.sheet.ok').count()
            if not ok: print('WRONG', f'niveau {lid}', i, t); pg.screenshot(path=SP+f'wrong{lid}-{i}.png')
            pg.click('[data-cont]'); pg.wait_for_timeout(100)
    faire_quiz(1)
    pg.wait_for_timeout(500); pg.screenshot(path=SP+'quizend.png')
    pg.click('[data-done]'); pg.wait_for_timeout(300)
    pg.evaluate("window.scrollTo(0, 1200)"); pg.wait_for_timeout(200); pg.screenshot(path=SP+'unlocked.png')
    # niveau 2, débloqué par le quiz du niveau 1
    faire_quiz(2)
    pg.wait_for_timeout(500); pg.screenshot(path=SP+'quizend2.png')
    pg.click('[data-done]'); pg.wait_for_timeout(300)
    if not pg.evaluate("ST.quiz[2] && ST.quiz[2].passed && !!ST.badges['niveau-2']"): print('WRONG niveau 2 non validé')
    # niveau 3, débloqué par le quiz du niveau 2
    faire_quiz(3)
    pg.wait_for_timeout(500); pg.screenshot(path=SP+'quizend3.png')
    pg.click('[data-done]'); pg.wait_for_timeout(300)
    if not pg.evaluate("ST.quiz[3] && ST.quiz[3].passed && !!ST.badges['niveau-3']"): print('WRONG niveau 3 non validé')
    # niveau 4, débloqué par le quiz du niveau 3
    faire_quiz(4)
    pg.wait_for_timeout(500); pg.screenshot(path=SP+'quizend4.png')
    pg.click('[data-done]'); pg.wait_for_timeout(300)
    if not pg.evaluate("ST.quiz[4] && ST.quiz[4].passed && !!ST.badges['niveau-4']"): print('WRONG niveau 4 non validé')
    # niveau 5, débloqué par le quiz du niveau 4
    faire_quiz(5)
    pg.wait_for_timeout(500); pg.screenshot(path=SP+'quizend5.png')
    pg.click('[data-done]'); pg.wait_for_timeout(300)
    if not pg.evaluate("ST.quiz[5] && ST.quiz[5].passed && !!ST.badges['niveau-5']"): print('WRONG niveau 5 non validé')
    # niveau 6, le dernier
    faire_quiz(6)
    pg.wait_for_timeout(500); pg.screenshot(path=SP+'quizend6.png')
    pg.click('[data-done]'); pg.wait_for_timeout(300)
    if not pg.evaluate("ST.quiz[6] && ST.quiz[6].passed && !!ST.badges['niveau-6']"): print('WRONG niveau 6 non validé')
    # map game tier 1
    pg.click('.tab[data-go="carte"]'); pg.wait_for_timeout(300); pg.screenshot(path=SP+'mapsetup.png')
    pg.click('text=Lancer une partie'); pg.wait_for_timeout(400)
    pass
    for r in range(5):
        e=pg.evaluate("MAPGAME.rounds[MAPGAME.i]")
        # click at projected truth position for r even, random for odd
        x,y=pg.evaluate("([la,lo])=>{const [x,y]=proj(la,lo);const s=document.querySelector('.map-box > svg');const pt=s.createSVGPoint();pt.x=x;pt.y=y;const q=pt.matrixTransform(s.getScreenCTM());return [q.x,q.y]}", [e['lat'],e['lon']])
        if r%2:   # manche volontairement imprécise : on se décale vers le centre de la carte, pour ne jamais en sortir
            bx=pg.locator('.map-box > svg').first.bounding_box(); cx,cy=bx['x']+bx['width']/2,bx['y']+bx['height']/2
            x+=40 if x<cx else -40; y+=30 if y<cy else -30
        pg.mouse.click(x,y); pg.wait_for_timeout(100)
        if r==0: pg.screenshot(path=SP+'mapround.png')
        pg.click('text=Valider ma position'); pg.wait_for_timeout(700)
        if r<2: pg.screenshot(path=SP+f'mapreveal{r}.png', full_page=True)
        pg.locator('.reveal ~ button.btn').click(); pg.wait_for_timeout(300)
    pg.screenshot(path=SP+'mapend.png', full_page=True)
    # tier 5 round
    pg.click('text=Changer de niveau'); pg.click('.tier[data-t="5"]'); pg.click('text=Lancer une partie'); pg.wait_for_timeout(300)
    e=pg.evaluate("MAPGAME.rounds[0]")
    x,y=pg.evaluate("([la,lo])=>{const [x,y]=proj(la,lo);const s=document.querySelector('.map-box > svg');const pt=s.createSVGPoint();pt.x=x;pt.y=y;const q=pt.matrixTransform(s.getScreenCTM());return [q.x,q.y]}", [e['lat'],e['lon']])
    pg.mouse.click(x+3,y+2); pg.click('text=Valider ma position'); pg.wait_for_timeout(700)
    pg.screenshot(path=SP+'map5.png', full_page=True)
    # carte du jour (France et monde, mêmes lieux pour tous) : on clique au bon endroit, le score entre au classement
    pg.evaluate("MAPGAME = nouvelleCarteDuJour(); go('carte')"); pg.wait_for_timeout(400)
    for r in range(5):
        e=pg.evaluate("MAPGAME.rounds[MAPGAME.i]")
        x,y=pg.evaluate("e=>{const [x,y]=fondDe(e.fond).proj(e.lat,e.lon);const s=document.querySelector('.map-box > svg');const pt=s.createSVGPoint();pt.x=x;pt.y=y;const q=pt.matrixTransform(s.getScreenCTM());return [q.x,q.y]}", e)
        pg.mouse.click(x,y); pg.wait_for_timeout(100); pg.click('text=Valider ma position'); pg.wait_for_timeout(500)
        if r==3: pg.screenshot(path=SP+'cartejour-monde.png', full_page=True)
        pg.locator('.reveal ~ button.btn').click(); pg.wait_for_timeout(300)
    s=pg.evaluate("ST.carteJour[todayStr()] && ST.carteJour[todayStr()].s")
    if not s or s < 24000: print('WRONG carte du jour', s)
    pg.screenshot(path=SP+'cartejour-fin.png', full_page=True)
    pg.click('[data-a="defi"]'); pg.wait_for_timeout(300)
    # daily
    pg.click('.tab[data-go="defi"]'); pg.wait_for_timeout(300); pg.screenshot(path=SP+'defi.png', full_page=True)
    pg.click('.tab[data-go="profil"]'); pg.wait_for_timeout(300); pg.screenshot(path=SP+'profil.png', full_page=True)
    pg.click('.tab[data-go="glossaire"]'); pg.wait_for_timeout(300); pg.fill('#gl-search','brut'); pg.wait_for_timeout(100); pg.screenshot(path=SP+'gloss.png')
    b.close()
for e in errs: print(e)
print('ok')
