const http = require('http');
const fs = require('fs');
const path = require('path');

const root = process.cwd();
const preferredPort = Number(process.env.BRANDPULSE_PORT || 8765);

const types = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.svg': 'image/svg+xml'
};

function send(res, status, body, type = 'text/plain; charset=utf-8') {
  res.writeHead(status, { 'Content-Type': type, 'Cache-Control': 'no-store' });
  res.end(body);
}

function handleRequest(req, res) {
  const urlPath = decodeURIComponent((req.url || '/').split('?')[0]);
  const relativePath = urlPath === '/' ? 'index.html' : urlPath.replace(/^\/+/, '');
  const filePath = path.resolve(root, relativePath);

  if (!filePath.startsWith(root)) {
    send(res, 403, 'Forbidden');
    return;
  }

  fs.readFile(filePath, (error, content) => {
    if (error) {
      send(res, error.code === 'ENOENT' ? 404 : 500, error.code || 'Error');
      return;
    }

    send(res, 200, content, types[path.extname(filePath).toLowerCase()] || 'application/octet-stream');
  });
}

function listen(port, attemptsLeft = 10) {
  const server = http.createServer(handleRequest);

  server.once('error', (error) => {
    if ((error.code === 'EADDRINUSE' || error.code === 'EACCES') && attemptsLeft > 0) {
      listen(port + 1, attemptsLeft - 1);
      return;
    }
    throw error;
  });

  server.listen(port, '127.0.0.1', () => {
    console.log(`BrandPulse VIS server: http://127.0.0.1:${port}/`);
  });
}

listen(preferredPort);
