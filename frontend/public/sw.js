/* VidInsight PWA Service Worker —— 无感更新版
   策略:
   · 导航请求(index.html):网络优先,拿不到才落缓存 —— 保证每次打开都是新壳
   · /assets/*(带内容hash):缓存优先 —— hash变=URL变,天然更新
   · 新 SW 激活后立即接管并刷新所有客户端 —— 用户零操作 */
const CACHE = 'vidinsight-v2'
const SHELL = ['/manifest.webmanifest', '/pwa-192.png', '/pwa-512.png']

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()))
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
      .then(() =>
        // 旧页面拿到新SW:自动刷新一次,完成无感换版
        self.clients.matchAll({ type: 'window' }).then((clients) =>
          clients.forEach((c) => c.navigate(c.url)),
        ),
      ),
  )
})

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url)
  if (e.request.method !== 'GET' || url.origin !== location.origin) return

  // 导航(打开/刷新页面):永远网络优先,更新 index.html 壳
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          const clone = res.clone()
          caches.open(CACHE).then((c) => c.put('/index.html', clone))
          return res
        })
        .catch(() => caches.match('/index.html')),
    )
    return
  }

  // 带hash的静态资源:缓存优先(内容变=URL变,不会陈旧)
  if (url.pathname.startsWith('/assets/') || SHELL.includes(url.pathname)) {
    e.respondWith(
      caches.match(e.request).then(
        (hit) =>
          hit ||
          fetch(e.request).then((res) => {
            if (res.ok) {
              const clone = res.clone()
              caches.open(CACHE).then((c) => c.put(e.request, clone))
            }
            return res
          }),
      ),
    )
  }
  // 其余(manifest 等)直连网络
})
