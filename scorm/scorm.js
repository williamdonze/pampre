/* Adaptateur SCORM 2004 (4e édition) de Pampre. Inclus seulement dans le paquet LMS (tools/build-scorm.py),
   chargé avant le script principal d'index.html.
   - trouve l'API du LMS (window.API_1484_11 dans un cadre parent ou dans la fenêtre d'ouverture) ;
   - recharge la progression depuis cmi.suspend_data, l'y réenregistre à chaque sauvegarde ;
   - remonte la progression (cmi.progress_measure), le score (moyenne des meilleurs quiz des niveaux requis),
     un objectif par niveau, et « terminé + réussi » quand les niveaux requis sont validés.
   Sans LMS (paquet ouvert hors plateforme), window.LMS reste indéfini : le site fonctionne comme d'habitude. */
(() => {
  const CONFIG = { niveauxRequis: 6 };   // réglé par build-scorm.py (--niveaux)
  const LIMITE = 64000;                  // taille de cmi.suspend_data garantie en SCORM 2004 4e édition

  function chercherAPI(w){
    for (let i = 0; w && i < 12; i++) {
      try { if (w.API_1484_11) return w.API_1484_11; } catch(e) { /* cadre d'une autre origine : on remonte */ }
      if (w.parent === w) break; w = w.parent;
    }
    return null;
  }
  let api = chercherAPI(window);
  if (!api) try { api = chercherAPI(window.opener); } catch(e) {}
  if (!api) return;
  try { if (String(api.Initialize("")) !== "true") return; } catch(e) { return; }

  const lire = k => { try { return String(api.GetValue(k) ?? ""); } catch(e) { return ""; } };
  const ecrire = (k, v) => { try { return String(api.SetValue(k, String(v))) === "true"; } catch(e) { return false; } };
  const debut = Date.now();
  // une fois terminé et réussi, on ne revient jamais en arrière (même après « Tout effacer »)
  let termine = lire("cmi.completion_status") === "completed" && lire("cmi.success_status") === "passed";
  let scoreMax = Number(lire("cmi.score.raw")) || 0;
  if (!termine) ecrire("cmi.completion_status", "incomplete");
  ecrire("cmi.score.min", 0); ecrire("cmi.score.max", 100);

  let minuteur = null, fini = false;
  const valider = () => { clearTimeout(minuteur); minuteur = null; try { api.Commit(""); } catch(e) {} };
  const validerBientot = () => { if (!minuteur) minuteur = setTimeout(valider, 3000); };   // regroupe les sauvegardes rapprochées

  // Au-delà de la limite (après plus d'un an de jeu quotidien), on retire le plus ancien historique de jours,
  // de défis et de cartes du jour : XP, niveaux, badges et série récente sont conservés.
  function compacter(st){
    const txt = JSON.stringify(st);
    if (txt.length <= LIMITE) return txt;
    const c = JSON.parse(txt);
    const histo = ["days", "daily", "carteJour"].filter(k => c[k] && typeof c[k] === "object");
    const dates = [...new Set(histo.flatMap(k => Object.keys(c[k])))].sort();
    let longueur = txt.length;
    for (const d of dates) {
      if (longueur <= LIMITE) break;
      for (const k of histo) delete c[k][d];
      longueur = JSON.stringify(c).length;
    }
    if (longueur > LIMITE) { c.mistakes = []; c.gloss = {}; }
    return JSON.stringify(c);
  }

  function bilan(st, LEVELS){
    const niveaux = Array.from({ length: CONFIG.niveauxRequis }, (_, i) => i + 1);
    const meilleurs = niveaux.map(n => Number(st.quiz?.[n]?.best) || 0);
    const valides = niveaux.map(n => !!st.quiz?.[n]?.passed);
    let etapes = 0, faites = 0;
    for (const n of niveaux) for (const e of LEVELS?.[n]?.parcours || []) { etapes++; if (e === "quiz" ? valides[n - 1] : st.done?.[e]) faites++; }
    return { niveaux, meilleurs, valides, score: meilleurs.reduce((a, b) => a + b, 0) / niveaux.length, progres: etapes ? faites / etapes : 0 };
  }

  const duree = ms => { const s = Math.round(ms / 1000); return `PT${Math.floor(s / 3600)}H${Math.floor(s / 60) % 60}M${s % 60}S`; };

  window.LMS = {
    cle: "pampre-scorm-" + (lire("cmi.learner_id") || "anonyme"),   // copie locale propre à chaque apprenant (poste partagé)
    charger(){
      const t = lire("cmi.suspend_data");
      if (!t) return null;
      try { return JSON.parse(t); } catch(e) { return null; }
    },
    enregistrer(st, LEVELS){
      if (fini) return;
      try {
        ecrire("cmi.suspend_data", compacter(st));
        const b = bilan(st, LEVELS);
        b.niveaux.forEach((n, i) => {
          ecrire(`cmi.objectives.${i}.id`, `niveau-${n}`);
          ecrire(`cmi.objectives.${i}.score.scaled`, (b.meilleurs[i] / 100).toFixed(4));
          ecrire(`cmi.objectives.${i}.completion_status`, b.valides[i] ? "completed" : "incomplete");
          if (b.valides[i]) ecrire(`cmi.objectives.${i}.success_status`, "passed");
        });
        scoreMax = Math.max(scoreMax, Math.round(b.score));
        ecrire("cmi.score.raw", scoreMax); ecrire("cmi.score.scaled", (scoreMax / 100).toFixed(4));
        const nouveau = !termine && b.valides.every(Boolean);
        if (nouveau) termine = true;
        ecrire("cmi.progress_measure", termine ? "1" : Math.min(b.progres, .99).toFixed(4));
        if (termine) { ecrire("cmi.completion_status", "completed"); ecrire("cmi.success_status", "passed"); }
        if (nouveau) valider(); else validerBientot();   // la réussite est transmise tout de suite
      } catch(e) {}
    },
    terminer(){
      if (fini) return;
      fini = true;
      ecrire("cmi.session_time", duree(Date.now() - debut));
      ecrire("cmi.exit", "suspend");   // la prochaine ouverture reprend la progression
      valider();
      try { api.Terminate(""); } catch(e) {}
    }
  };
  addEventListener("pagehide", () => window.LMS.terminer());
  addEventListener("beforeunload", () => window.LMS.terminer());
})();
