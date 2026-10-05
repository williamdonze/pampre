from playwright.sync_api import sync_playwright
import json, os
os.makedirs('captures', exist_ok=True)
errs=[]; SP='captures/'
with sync_playwright() as p:
    b=p.chromium.launch()
    pg=b.new_page(viewport={'width':400,'height':860})
    pg.on('pageerror', lambda e: errs.append(('pageerror',str(e))))
    pg.goto('http://localhost:8765/index.html'); pg.wait_for_timeout(800)
    # quiz: answer correctly using data
    data=pg.evaluate("LEVELS[1].quiz.questions")
    pg.evaluate("startQuiz(1)"); pg.wait_for_timeout(300)
    for i,q in enumerate(data):
        t=q['type']
        if t in('qcm','indices') or (t=='etiquette' and q['mode']=='qcm'):
            if t=='indices': pg.click('.next-clue button'); 
            pg.locator('.choice').nth(q['bonne']).click()
            if t=='indices': pg.screenshot(path=SP+'indices.png')
        elif t=='vf':
            pg.click('.choice[data-v="%d"]'%(1 if q['bonne'] else 0))
        elif t=='etiquette':
            pg.click('.lbl .ch[data-champ="%s"]'%q['cible'])
        elif t=='ordre':
            for it in q['items']:
                pg.locator('.pool .chip:not(.used)', has_text=it).first.click()
        elif t=='assoc':
            for a,bb in q['paires']:
                pg.locator('.l .chip', has_text=a).first.click(); pg.locator('.r .chip', has_text=bb).first.click()
        elif t=='tri':
            for txt,c in q['items']:
                pg.locator('.pool .chip', has_text=txt).first.click(); pg.locator('.cat').nth(c).click(position={'x':8,'y':8})
        pg.click('[data-check]'); pg.wait_for_timeout(100)
        ok=pg.locator('.sheet.ok').count()
        if not ok: print('WRONG', i, t); pg.screenshot(path=SP+f'wrong{i}.png')
        pg.click('[data-cont]'); pg.wait_for_timeout(100)
    pg.wait_for_timeout(500); pg.screenshot(path=SP+'quizend.png')
    pg.click('[data-done]'); pg.wait_for_timeout(300)
    pg.evaluate("window.scrollTo(0, 1200)"); pg.wait_for_timeout(200); pg.screenshot(path=SP+'unlocked.png')
    # map game tier 1
    pg.click('.tab[data-go="carte"]'); pg.wait_for_timeout(300); pg.screenshot(path=SP+'mapsetup.png')
    pg.click('text=Lancer une partie'); pg.wait_for_timeout(400)
    pass
    for r in range(5):
        e=pg.evaluate("MAPGAME.rounds[MAPGAME.i]")
        # click at projected truth position for r even, random for odd
        x,y=pg.evaluate("([la,lo])=>{const [x,y]=proj(la,lo);const s=document.querySelector('.map-box > svg');const pt=s.createSVGPoint();pt.x=x;pt.y=y;const q=pt.matrixTransform(s.getScreenCTM());return [q.x,q.y]}", [e['lat'],e['lon']])
        if r%2: x+=40; y+=30
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
    # daily
    pg.click('.tab[data-go="defi"]'); pg.wait_for_timeout(300); pg.screenshot(path=SP+'defi.png', full_page=True)
    pg.click('.tab[data-go="profil"]'); pg.wait_for_timeout(300); pg.screenshot(path=SP+'profil.png', full_page=True)
    pg.click('.tab[data-go="glossaire"]'); pg.wait_for_timeout(300); pg.fill('#gl-search','brut'); pg.wait_for_timeout(100); pg.screenshot(path=SP+'gloss.png')
    b.close()
for e in errs: print(e)
print('ok')
