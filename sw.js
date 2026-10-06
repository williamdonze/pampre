/* Service worker de Pampre : rend l'appli installable et jouable hors connexion.
   Réseau d'abord (le contenu est toujours le plus récent quand on est en ligne), copie en cache pour le hors-ligne.
   Seules les ressources du site sont mises en cache ; Google Fonts passe par le réseau (polices de repli sinon). */
const CACHE = "pampre-v1";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(
  caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())
));
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  e.respondWith(
    fetch(req).then(rep => {
      if (rep.ok) { const copie = rep.clone(); caches.open(CACHE).then(c => c.put(req, copie)); }
      return rep;
    }).catch(() => caches.match(req, { ignoreSearch: true }).then(r => r || (req.mode === "navigate" ? caches.match("./") : Response.error())))
  );
});
