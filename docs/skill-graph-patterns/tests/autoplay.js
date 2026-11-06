const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({viewport: {width: 1360, height: 1000}});
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto('file://' + process.argv[2]);
  for (const id of ['settle', 'walk']) {
    await page.$eval('#' + id, e => e.scrollIntoView());
    await page.waitForTimeout(250);
    const a = await page.$eval(`#${id} .clock`, c => c.textContent);
    await page.waitForTimeout(4200);
    const b = await page.$eval(`#${id} .clock`, c => c.textContent);
    const playing = await page.$eval(`#${id} button.play`, b => b.textContent);
    console.log(id, a, '->', b, '|', playing);
  }
  console.log('errors', JSON.stringify(errors));
  await browser.close();
})();
