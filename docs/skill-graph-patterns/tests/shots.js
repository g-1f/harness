const { chromium } = require('playwright');
// usage: node shots.js file "id@step[:node][,…]" [dark] [width]
(async () => {
  const [file, spec, dark, width] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({viewport: {width: +(width || 1360), height: 1000}, deviceScaleFactor: 1});
  await page.emulateMedia({reducedMotion: 'reduce', colorScheme: dark === 'dark' ? 'dark' : 'light'});
  await page.goto('file://' + file);
  await page.waitForTimeout(400);
  for (const item of spec.split(',')) {
    const [idstep, node] = item.split(':');
    const [id, step] = idstep.split('@');
    const sel = id === 'walk' ? '#walk' : `#${id}`;
    if (step) {
      await page.$eval(`${sel} input[type=range]`, r => { r.value = '0'; r.dispatchEvent(new Event('input')); });
      for (let k = 0; k < +step; k++) await page.click(`${sel} button.stepbtn[aria-label="Next step"]`);
    }
    if (node) {
      const gs = await page.$$(`${sel} g.g-node, ${sel} g.g-user`);
      for (const g of gs) {
        const lab = await g.getAttribute('aria-label');
        if (lab && lab.startsWith(node + ' ')) { await g.dispatchEvent('click'); break; }
      }
    }
    const name = `${id}${step ? '-' + step : ''}${node ? '-' + node : ''}${dark === 'dark' ? '-dark' : ''}${width ? '-' + width : ''}`;
    await (await page.$(sel)).screenshot({path: `shots/${name}.png`});
    console.log('shot', name);
  }
  await browser.close();
})();
