/* Pampre — bibliothèque d'audit injectée dans la page par tools/audit.py.
   Expose window.AUDIT : vérifications automatiques (débordements, couches, contraste,
   zones tactiles, SVG coupés) et petites aides pour piloter l'appli (répondre juste ou faux).
   Ne dépend d'aucun navigateur précis : fonctionne sous Chromium, WebKit et Firefox. */
(() => {
  if (window.AUDIT) return;

  /* ---------- couleurs ---------- */
  function parseColor(s){
    if (!s || s === "transparent") return [0,0,0,0];
    let m = s.match(/^rgba?\(([^)]+)\)$/);
    if (m) { const p = m[1].split(/[ ,/]+/).filter(Boolean).map(parseFloat); return [p[0], p[1], p[2], p[3] ?? 1]; }
    m = s.match(/^color\(srgb ([^)]+)\)$/);
    if (m) { const p = m[1].split(/[ /]+/).filter(Boolean).map(parseFloat); return [p[0]*255, p[1]*255, p[2]*255, p[3] ?? 1]; }
    // repli : laisser le navigateur convertir via un canvas (un pixel peint puis relu)
    const cv = document.createElement("canvas"); cv.width = cv.height = 1; const c = cv.getContext("2d");
    c.clearRect(0, 0, 1, 1); c.fillStyle = s; c.fillRect(0, 0, 1, 1);
    const d = c.getImageData(0, 0, 1, 1).data; (window.__couleursInconnues ||= new Set()).add(s);
    return [d[0], d[1], d[2], d[3] / 255];
  }
  const over = (top, bot) => { const a = top[3] + bot[3]*(1-top[3]); if (!a) return [0,0,0,0]; return [0,1,2].map(i => (top[i]*top[3] + bot[i]*bot[3]*(1-top[3]))/a).concat(a); };
  const lum = c => { const f = v => { v /= 255; return v <= .03928 ? v/12.92 : ((v+.055)/1.055)**2.4; }; return .2126*f(c[0]) + .7152*f(c[1]) + .0722*f(c[2]); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x,y)+.05)/(Math.min(x,y)+.05); };
  const hex = c => "#" + c.slice(0,3).map(v => Math.round(v).toString(16).padStart(2,"0")).join("");

  /* fond effectif d'un élément : on compose les fonds des ancêtres jusqu'à un fond opaque */
  function bgOf(el){
    const layers = []; let unknown = false;
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.backgroundImage && cs.backgroundImage !== "none") unknown = true;
      const c = parseColor(cs.backgroundColor);
      if (c[3] > 0) { layers.push(c); if (c[3] >= .99) break; }
    }
    let acc = parseColor(getComputedStyle(document.body).backgroundColor); if (acc[3] < 1) acc = [255,255,255,1];
    for (let i = layers.length - 1; i >= 0; i--) acc = over(layers[i], acc);
    return { c: acc, unknown };
  }
  function opacityOf(el){ let o = 1; for (let e = el; e && e.nodeType === 1; e = e.parentElement) o *= +getComputedStyle(e).opacity; return o; }

  /* ---------- utilitaires DOM ---------- */
  function visible(el){
    if (!el.isConnected) return false;
    const r = el.getBoundingClientRect(); if (r.width < 1 || r.height < 1) return false;
    const cs = getComputedStyle(el); if (cs.visibility === "hidden" || cs.display === "none") return false;
    return opacityOf(el) > .05;
  }
  function sig(el){
    const part = e => { if (e.id) return "#" + e.id; let s = e.tagName.toLowerCase(); const cls = [...e.classList].filter(c => !/^(ok|ko|sel|hot|picked|used|done|current|focus)$/.test(c)).slice(0,3); if (cls.length) s += "." + cls.join("."); return s; };
    const parts = []; let e = el;
    for (let i = 0; e && e.nodeType === 1 && i < 4; i++, e = e.parentElement) { parts.unshift(part(e)); if (e.id || e.classList.contains("session") || e.tagName === "MAIN") break; }
    return parts.join(" > ");
  }
  const txt = el => (el.textContent || el.getAttribute?.("aria-label") || "").replace(/\s+/g, " ").trim().slice(0, 60);
  const R = r => ({ x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height) });
  const ownText = el => [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
  const OVERLAYS = ".tabbar,.topbar,.toasts,.sheet,.modal-bg,.drawer,.drawer-bg,.s-foot,.s-top,.map-zoom,.map-hint,.confetti";
  const inOverlay = el => el.closest(OVERLAYS);
  /* un ancêtre qui coupe (overflow ≠ visible) cache-t-il ce point ? */
  function clipped(el){
    const r = el.getBoundingClientRect();
    for (let e = el.parentElement; e && e !== document.body; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.overflowX !== "visible" || cs.overflowY !== "visible") { const p = e.getBoundingClientRect(); if (r.right <= p.left || r.left >= p.right || r.bottom <= p.top || r.top >= p.bottom) return true; }
    }
    return false;
  }

  /* ---------- vérifications ---------- */
  // couche active : la modale, sinon le glossaire, sinon la session, sinon la page
  const activeRoot = () => document.querySelector(".modal-bg .modal") || document.querySelector(".drawer") || document.querySelector(".session") || document.body;
  const scope = () => { const r = activeRoot(); const t = document.getElementById("toasts"); return [...r.querySelectorAll("*"), ...(r !== document.body && t ? t.querySelectorAll("*") : [])]; };
  function checkScroll(out){
    const d = document.documentElement;
    if (d.scrollWidth > d.clientWidth + 1) out.push({ check:"defilement-horizontal", sel:"html", detail:`scrollWidth ${d.scrollWidth} > clientWidth ${d.clientWidth}` });
    document.querySelectorAll(".s-body,.drawer-body,.sheet .expl,.modal").forEach(e => { if (visible(e) && e.scrollWidth > e.clientWidth + 1) out.push({ check:"defilement-horizontal", sel:sig(e), detail:`scrollWidth ${e.scrollWidth} > ${e.clientWidth}` }); });
  }
  /* contenu qui sort de sa boîte (mot trop long, texte coupé) */
  function checkOverflow(out){
    const vw = document.documentElement.clientWidth;
    for (const el of scope()) {
      if (el.closest("svg") || !visible(el)) continue;
      const cs = getComputedStyle(el);
      if (cs.position === "fixed" && el.classList.contains("drag-ghost")) continue;
      const txtish = ownText(el) || el.matches("button,.chip,.choice,.tier,.ch,.es span,.kpi b,.stat,.node-label,.lbl");
      if (!txtish) continue;
      // 1. texte plus large que sa boîte
      if (el.scrollWidth > el.clientWidth + 1 && el.clientWidth > 0 && cs.display !== "inline") {
        const hidden = cs.overflowX !== "visible";
        out.push({ check: hidden ? "texte-coupe" : "texte-deborde", sel:sig(el), text:txt(el), rect:R(el.getBoundingClientRect()), detail:`contenu ${el.scrollWidth}px dans ${el.clientWidth}px` });
      }
      // 2. élément qui sort de l'écran sans être coupé par un parent
      const r = el.getBoundingClientRect();
      if ((r.right > vw + 1 || r.left < -1) && !clipped(el) && cs.position !== "fixed") out.push({ check:"hors-ecran", sel:sig(el), text:txt(el), rect:R(r), detail:`x ${Math.round(r.left)}→${Math.round(r.right)} pour ${vw}px` });
    }
    // 3. champs des étiquettes qui débordent du papier
    document.querySelectorAll(".lbl").forEach(l => { const lr = l.getBoundingClientRect(); l.querySelectorAll(".ch").forEach(c => { const r = c.getBoundingClientRect(); if (r.right > lr.right - 2 || r.left < lr.left + 2) out.push({ check:"etiquette-deborde", sel:sig(c), text:txt(c), rect:R(r), detail:`champ ${Math.round(r.left)}→${Math.round(r.right)}, papier ${Math.round(lr.left)}→${Math.round(lr.right)}` }); }); });
  }
  /* texte SVG qui sort du viewBox (donc coupé) */
  function checkSvgText(out){
    activeRoot().querySelectorAll("svg[viewBox]").forEach(svg => {
      if (svg.closest(".map-box")) return; if (!visible(svg)) return;
      const [x0, y0, w, h] = svg.getAttribute("viewBox").split(/[ ,]+/).map(Number);
      svg.querySelectorAll("text").forEach(t => { let b; try { b = t.getBBox(); } catch(e) { return; } if (!b.width) return;
        if (b.x < x0 - .5 || b.y < y0 - .5 || b.x + b.width > x0 + w + .5 || b.y + b.height > y0 + h + .5) out.push({ check:"svg-texte-coupe", sel:sig(svg.parentElement) + " svg text", text:t.textContent.trim(), detail:`texte ${b.x.toFixed(0)}→${(b.x+b.width).toFixed(0)} × ${b.y.toFixed(0)}→${(b.y+b.height).toFixed(0)}, viewBox ${x0} ${y0} ${w} ${h}` }); });
    });
  }
  /* contraste WCAG AA */
  function checkContrast(out){
    for (const el of scope()) {
      if (!ownText(el) || el.closest("svg") || !visible(el)) continue;
      const r = el.getBoundingClientRect(); if (r.bottom < 0 || r.top > innerHeight) continue;
      const cs = getComputedStyle(el);
      let fg = parseColor(cs.color); const bg = bgOf(el); fg = over(fg, bg.c);
      const op = opacityOf(el); if (op < 1) fg = over([...fg.slice(0,3), op], bg.c);
      const k = ratio(fg, bg.c); const size = parseFloat(cs.fontSize), bold = +cs.fontWeight >= 700;
      const large = size >= 24 || (size >= 18.66 && bold); const need = large ? 3 : 4.5;
      const disabled = !!el.closest(":disabled,[aria-disabled=true]");
      const lbl = el.closest(".lbl");
      if (k < need) out.push({ check: disabled ? "contraste-desactive" : lbl ? "contraste-etiquette" : "contraste", sel:sig(el), text:txt(el), detail:`${k.toFixed(2)}:1 < ${need} (${hex(fg)} sur ${hex(bg.c)}${bg.unknown?", fond dégradé":""}, ${size}px${bold?" gras":""})` });
    }
    // texte des SVG : on prend la forme dessinée juste derrière
    activeRoot().querySelectorAll("svg text").forEach(t => {
      if (t.closest(".map-box") || !visible(t)) return;
      const r = t.getBoundingClientRect(); if (r.bottom < 0 || r.top > innerHeight || !r.width) return;
      const cx = r.left + r.width/2, cy = r.top + r.height/2;
      let fill = null;
      const svg = t.ownerSVGElement;
      const stack = document.elementsFromPoint(cx, cy).filter(e => e !== t && svg.contains(e) && e.tagName !== "g" && e.tagName !== "text" && e !== svg);
      for (const s of stack) { const f = getComputedStyle(s).fill; if (f && f !== "none" && !f.startsWith("url")) { fill = parseColor(f); fill = over([fill[0],fill[1],fill[2], (+getComputedStyle(s).fillOpacity||1)*opacityOf(s)], bgOf(svg).c); break; } }
      const bg = fill || bgOf(svg).c;
      let fg = parseColor(getComputedStyle(t).fill); fg = over(fg, bg);
      const k = ratio(fg, bg); const size = parseFloat(getComputedStyle(t).fontSize) * (svg.getBoundingClientRect().width / svg.viewBox.baseVal.width || 1);
      const need = size >= 24 ? 3 : 4.5;
      if (k < need) out.push({ check:"contraste-svg", sel:sig(svg.parentElement) + " svg text", text:t.textContent.trim(), detail:`${k.toFixed(2)}:1 < ${need} (${hex(fg)} sur ${hex(bg)}, ≈${size.toFixed(0)}px rendus)` });
    });
  }
  /* zones tactiles < 44 × 44 */
  function checkTargets(out){
    activeRoot().querySelectorAll("button,a[href],input,textarea,select,[tabindex]:not([tabindex='-1']),.lbl.tap .ch,.cat").forEach(el => {
      if (!visible(el) || el.disabled) return;
      const r = el.getBoundingClientRect(); if (r.bottom < 0 || r.top > innerHeight) return;
      // une case à cocher est utilisable via son libellé
      let rr = r; if (el.matches("input[type=checkbox],input[type=radio]")) { const l = el.closest("label"); if (l) rr = l.getBoundingClientRect(); }
      if (rr.width < 43.5 || rr.height < 43.5) out.push({ check: el.classList.contains("gl") ? "cible-tactile-inline" : "cible-tactile", sel:sig(el), text:txt(el), detail:`${Math.round(rr.width)} × ${Math.round(rr.height)} px` });
    });
  }
  /* couches : un élément utile caché sous une barre, un toast, la feuille… */
  function checkLayers(out, opts = {}){
    const root = activeRoot(); const only = opts.only ? opts.only : null;
    const important = "button,input,textarea,.choice,.chip,.qtitle,h1,h2,h3,.lbl,.cat,.map-box,p,.es,.kpi,.badge,.node,.node-label,.panel";
    const vh = innerHeight;
    root.querySelectorAll(important).forEach(el => {
      if (!visible(el) || inOverlay(el) && opts.skipOverlayContent !== false && inOverlay(el).matches(".tabbar,.topbar,.s-top,.s-foot,.sheet,.toasts,.map-zoom,.drawer,.modal-bg")) return;
      const r = el.getBoundingClientRect(); if (r.bottom <= 0 || r.top >= vh) return;
      const pts = [[r.left + r.width/2, Math.max(1, Math.min(vh-1, r.top + r.height/2))], [r.left + 6, Math.max(1, r.top + 4)], [r.right - 6, Math.min(vh - 1, r.bottom - 4)]];
      for (const [x, y] of pts) {
        if (x < 0 || x >= innerWidth) continue;
        const hit = document.elementFromPoint(x, y); if (!hit || el.contains(hit) || hit.contains(el)) continue;
        const ov = inOverlay(hit); if (!ov || ov.contains(el)) continue;
        if (only && !ov.matches(only)) continue;
        out.push({ check:"masque", sel:sig(el), text:txt(el), detail:`caché par ${sig(ov)} au point (${Math.round(x)}, ${Math.round(y)})` }); break;
      }
    });
  }
  /* les toasts ont pointer-events:none (elementFromPoint les traverse) : test géométrique */
  function checkToasts(out){
    const toasts = [...document.querySelectorAll(".toast")].filter(visible); if (!toasts.length) return;
    const important = "button,.choice,.chip,.qtitle,h1,h2,h3,.es,.lbl,.cat,.map-box,p,.kpi,.badge,.node,.node-label";
    activeRoot().querySelectorAll(important).forEach(el => {
      if (!visible(el) || el.closest(".toasts")) return; const r = el.getBoundingClientRect();
      for (const t of toasts) { const q = t.getBoundingClientRect(); const ix = Math.min(r.right, q.right) - Math.max(r.left, q.left), iy = Math.min(r.bottom, q.bottom) - Math.max(r.top, q.top);
        if (ix > 4 && iy > 4) { out.push({ check:"masque-par-toast", sel:sig(el), text:txt(el), detail:`recouvert sur ${Math.round(ix)} × ${Math.round(iy)} px par le toast « ${txt(t).slice(0,40)} »` }); break; } }
    });
  }
  /* on fait défiler chaque zone au maximum puis on cherche ce qui reste caché en bas */
  async function checkBottom(out){
    const res = [];
    const root = activeRoot();
    // l'explication défile à l'intérieur de la feuille : seul compte ce qui reste caché sous les couches du bas
    const frames = [root === document.body ? document.scrollingElement : null, ...root.querySelectorAll(".s-body,.drawer-body")].filter(e => e && e.scrollHeight > e.clientHeight + 1 && (e === document.scrollingElement || visible(e)));
    for (const f of frames) {
      const prev = f.scrollTop; f.scrollTop = f.scrollHeight; await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
      const tmp = []; checkLayers(tmp, { only: ".tabbar,.sheet,.s-foot,.toasts,.modal-bg,.confetti" }); tmp.forEach(t => { t.check = "masque-en-bas"; t.detail += ` (zone ${f === document.scrollingElement ? "page" : sig(f)} défilée au maximum)`; res.push(t); });
      f.scrollTop = prev;
    }
    // la feuille de correction cache-t-elle la fin de la question ?
    const sheet = document.querySelector(".sheet"), body = document.querySelector(".s-body");
    if (sheet && body) {
      body.scrollTop = body.scrollHeight; await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
      const top = sheet.getBoundingClientRect().top; const items = [...document.querySelectorAll("#s-main *")].filter(e => visible(e) && !e.closest(".map-box svg") && (ownText(e) || e.matches("button,.chip,.choice,.map-box")));
      const hidden = items.filter(e => e.getBoundingClientRect().bottom > top + 2);
      if (hidden.length) res.push({ check:"masque-par-feuille", sel:sig(hidden[0]), text:txt(hidden[hidden.length-1]), detail:`${hidden.length} élément(s) de la question restent sous la feuille de correction même en défilant (haut de la feuille : ${Math.round(top)} px)` });
    }
    out.push(...res);
  }
  async function run(opts = {}){
    const out = [];
    checkScroll(out); checkOverflow(out); checkSvgText(out);
    if (opts.contrast !== false) checkContrast(out);
    if (opts.targets) checkTargets(out);
    checkToasts(out); await checkBottom(out);
    return out;
  }

  /* ---------- aides de pilotage ---------- */
  // répond à la question en cours (juste ou faux) en cliquant comme un joueur
  function answer(good){
    const ses = document.querySelector(".session"); const q = window.__curQ; if (!ses || !q) return false;
    const click = s => { const e = typeof s === "string" ? ses.querySelector(s) : s; if (!e) throw new Error("introuvable : " + s); e.click(); };
    const T = q.type;
    if (T === "qcm" || T === "indices" || (T === "etiquette" && q.mode === "qcm")) {
      const correct = q.bonneTexte ?? q.choix[q.bonne];
      const btns = [...ses.querySelectorAll(".choice")];
      const target = btns.find(b => (b.textContent.slice(1).trim() === correct) === good) || btns[0];
      click(target);
    } else if (T === "vf") click(`.choice[data-v="${(q.bonne === good) ? 1 : 0}"]`);
    else if (T === "etiquette") { const c = good ? q.cible : [...ses.querySelectorAll(".lbl .ch")].map(x => x.dataset.champ).find(k => k !== q.cible && !(q.cible === "appellation" && k === "mention")); click(`.lbl .ch[data-champ="${c}"]`); }
    else if (T === "ordre") { const items = good ? q.items : q.items.slice().reverse(); items.forEach(t => click([...ses.querySelectorAll(".pool .chip:not(.used)")].find(b => b.textContent === t))); }
    else if (T === "assoc") { const n = q.paires.length; q.paires.forEach(([a], i) => { const b = good ? q.paires[i][1] : q.paires[(i+1)%n][1]; click([...ses.querySelectorAll(".l .chip")].find(x => x.textContent === a)); click([...ses.querySelectorAll(".r .chip")].find(x => x.textContent === b)); }); }
    else if (T === "tri") { const nc = q.categories.length; q.items.forEach(([t, c]) => { const chip = [...ses.querySelectorAll(".pool .chip")].find(x => x.textContent === t); chip.dispatchEvent(new PointerEvent("pointerdown", {bubbles:true, clientX:1, clientY:1})); window.dispatchEvent(new PointerEvent("pointerup", {bubbles:true, clientX:1, clientY:1})); click(ses.querySelectorAll(".cat")[good ? c : (c+1)%nc]); }); }
    else return false;
    return true;
  }
  // mémorise la question affichée (pour savoir quoi répondre)
  function hook(){ if (window.__hooked || typeof Q === "undefined") return; window.__hooked = true; for (const k of Object.keys(Q)) { const f = Q[k]; Q[k] = (q, c) => { window.__curQ = q; return f(q, c); }; } }
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  // joue une session jusqu'à l'écran de fin ; good = true/false ou fonction(i) -> bool
  async function playThrough(good = true, max = 80){
    for (let i = 0; i < max; i++) {
      const ses = document.querySelector(".session"); if (!ses) return "pas de session";
      if (ses.querySelector(".endcard")) return "fin";
      const cont = document.querySelector(".sheet [data-cont]"); if (cont) { cont.click(); await sleep(30); continue; }
      const next = ses.querySelector("[data-next]"); if (next) { next.click(); await sleep(30); continue; }
      const chk = ses.querySelector("[data-check]");
      if (chk) { if (window.__curQ?.type === "carte") return "carte"; answer(typeof good === "function" ? good(i) : good); await sleep(20); chk.click(); await sleep(30); continue; }
      await sleep(50);
    }
    return "max";
  }
  window.AUDIT = { run, answer, hook, playThrough, parseColor, ratio, sig, visible, checkTargets, checkContrast, checkLayers };
})();
