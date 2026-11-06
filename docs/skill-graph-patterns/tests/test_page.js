const { chromium } = require('playwright');
(async () => {
  const file = 'file://' + process.argv[2];
  const browser = await chromium.launch();
  const page = await browser.newPage({viewport: {width: 1360, height: 1000}, deviceScaleFactor: 1});
  const errors = [];
  page.on('console', m => { if (m.type() === 'error' && !/ERR_TUNNEL|fonts/.test(m.text())) errors.push(m.text()); });
  page.on('pageerror', e => errors.push(String(e)));
  await page.emulateMedia({reducedMotion: 'reduce'});
  await page.goto(file);
  await page.waitForTimeout(500);
  const sections = await page.$$eval('article.pattern', as => as.map(a => a.id));
  sections.push('walk');
  let problems = [];
  for (const id of sections) {
    const sel = id === 'walk' ? '#walk' : `#${id}`;
    // go to the start, then click Next through every step
    const T = await page.$eval(`${sel} .clock`, c => +c.textContent.split(' of ')[1]);
    await page.$eval(`${sel} input[type=range]`, r => { r.value = '0'; r.dispatchEvent(new Event('input')); });
    for (let k = 0; k < T * 2 + 2; k++) {
      await page.click(`${sel} button.stepbtn[aria-label="Next step"]`);
      const snap = await page.$eval(sel, root => {
        const txt = root.querySelector('.narration').textContent + ' ' + root.querySelector('ul.doing').textContent;
        const ds = [...root.querySelectorAll('svg path')].map(p => p.getAttribute('d') || '').join(' ');
        return {txt, bad: /undefined|NaN/.test(txt) || /NaN|undefined/.test(ds), clock: root.querySelector('.clock').textContent};
      });
      if (snap.bad || !snap.txt.trim()) problems.push(`${id} at ${snap.clock}: ${snap.txt.slice(0, 80)}`);
    }
    const clock = await page.$eval(`${sel} .clock`, c => c.textContent);
    if (clock !== `step ${T} of ${T}`) problems.push(`${id}: Next did not reach the last step (${clock})`);
    // select every node at the last step and check its details
    const ids = await page.$$eval(`${sel} g.g-node, ${sel} g.g-user`, gs => gs.length);
    for (let i = 0; i < ids; i++) {
      const g = (await page.$$(`${sel} g.g-node, ${sel} g.g-user`))[i];
      await g.dispatchEvent('click');
      const det = await page.$eval(`${sel} .details:not(.walk-steps)`, d => d.textContent);
      if (/undefined|NaN|\[object/.test(det)) problems.push(`${id} node ${i}: ${det.slice(0, 120)}`);
      await g.dispatchEvent('click');
    }
    // the previous button walks back to step 1
    for (let k = 0; k < T + 1; k++) await page.click(`${sel} button.stepbtn[aria-label="Previous step"]`);
    const back = await page.$eval(`${sel} .clock`, c => c.textContent);
    if (back !== `step 1 of ${T}`) problems.push(`${id}: Previous did not return to step 1 (${back})`);
  }
  console.log('sections checked:', sections.length);
  console.log('errors:', JSON.stringify(errors));
  console.log('problems:', problems.length ? '\n' + problems.join('\n') : 'none');
  await browser.close();
})();
