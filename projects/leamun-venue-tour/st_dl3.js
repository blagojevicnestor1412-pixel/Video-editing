const { chromium } = require('playwright');
(async () => {
  const out = process.argv[2];
  const b = await chromium.launch();
  const ctx = await b.newContext({ acceptDownloads: true });
  const p = await ctx.newPage();
  const log = [];
  ctx.on('request', r => { if (!/\.(js|css|png|svg|woff2?|jpg|webp)(\?|$)/.test(r.url())) log.push('REQ ' + r.method() + ' ' + r.url()); });
  ctx.on('response', r => { if (!/\.(js|css|png|svg|woff2?|jpg|webp)(\?|$)/.test(r.url())) log.push('RES ' + r.status() + ' ' + r.url() + ' ' + (r.headers()['content-type']||'')); });
  ctx.on('page', np => log.push('NEWPAGE ' + np.url()));
  p.on('download', d => log.push('DOWNLOAD ' + d.url()));
  await p.goto('https://www.swisstransfer.com/dl/01a20cca-732a-7781-b14b-fe3da3a90ff7', { waitUntil: 'networkidle', timeout: 60000 });
  log.push('--- click');
  await p.getByRole('button', { name: /Download all/i }).first().click().catch(e => log.push('clickerr ' + e.message));
  await p.waitForTimeout(8000);
  await p.screenshot({ path: out + '/shot2.png' });
  console.log(log.join('\n'));
  await b.close();
})();
