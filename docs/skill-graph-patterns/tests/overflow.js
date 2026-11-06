const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  for (const w of [390, 768, 1360]) {
    const page = await browser.newPage({viewport: {width: w, height: 900}});
    await page.emulateMedia({reducedMotion: 'reduce'});
    await page.goto('file://' + process.argv[2]);
    await page.waitForTimeout(300);
    const r = await page.evaluate(() => ({sw: document.scrollingElement.scrollWidth, cw: document.documentElement.clientWidth,
      wide: [...document.querySelectorAll('body *')].filter(e => { const b = e.getBoundingClientRect(); return b.right > document.documentElement.clientWidth + 1 && !e.closest('.graph, .code, .stream-sample, .tabs'); }).slice(0, 5).map(e => e.tagName + '.' + e.className)}));
    console.log(w, JSON.stringify(r));
    await page.close();
  }
  await browser.close();
})();
