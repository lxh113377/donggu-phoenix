/* dev_server.js — 本地静态预览服务器（零依赖，仅用于开发/验收）
 * 用法：node tools/dev_server.js [port]   默认 8791，根目录 = ../site
 */
'use strict';
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = Number(process.argv[2] || process.env.PORT || 8791);
const ROOT = path.resolve(__dirname, '..', 'site');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
  '.json': 'application/json; charset=utf-8',
  '.webmanifest': 'application/manifest+json; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
  '.xml': 'application/xml; charset=utf-8',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2'
};

const server = http.createServer((req, res) => {
  let u;
  try { u = decodeURIComponent((req.url || '/').split('?')[0].split('#')[0]); }
  catch (e) { res.writeHead(400); return res.end('bad request'); }
  if (u === '/' || u === '') u = '/index.html';
  const file = path.normalize(path.join(ROOT, u));
  if (!file.startsWith(ROOT + path.sep) && file !== ROOT) { res.writeHead(403); return res.end('forbidden'); }
  fs.readFile(file, (err, buf) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': MIME['.txt'] });
      return res.end('404 Not Found: ' + u);
    }
    res.writeHead(200, {
      'Content-Type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream',
      'Cache-Control': 'no-store'
    });
    res.end(buf);
  });
});

server.listen(PORT, '127.0.0.1', () => {
  console.log('dev server http://127.0.0.1:' + PORT + '/ root=' + ROOT);
});
