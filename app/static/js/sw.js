const CACHE_NAME = 'fyp-v0-0-1';
const ASSETS = ['/', '/login', '/static/css/style.css', '/static/js/app.js'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS)));
});
self.addEventListener('fetch', event => {
  event.respondWith(caches.match(event.request).then(response => response || fetch(event.request)));
});
