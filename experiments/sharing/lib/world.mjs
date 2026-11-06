// The sandbox world: a fictional economy (Caldria) with planted facts, served by tools with seeded latency.
// Search matches only a document's own key terms, so a planted fact is found only by queries that are about it.

export const WORKFLOWS = {
  shared: {
    title: 'Shared need',
    question: 'Is now a good time to add VLTX Jan-2028 calls?',
    split: [
      "Is the valuation case for VLTX's holdings intact through 2027, given the expected CMA policy path and the holdings' earnings outlook?",
      'Are VLTX Jan-2028 calls attractively priced, given the expected CMA policy path and VLTX volatility?',
    ],
    // Both branches need the CMA policy path, which comes from a slow series plus the CMA minutes.
    planted: {
      path: "CMA futures imply two 25bp cuts by end-2027 (4.50% now, 4.00% by December 2027); the Governor's base case is one cut.",
      iv: 'VLTX Jan-2028 at-the-money implied vol 24% against 1-year realized 29%: calls are cheap.',
      answer: 'Yes: calls are cheap (IV 24% vs realized 29%) and the policy path (4.50% to 4.00% by end-2027) supports valuations.',
    },
    rubric: [
      'States the market-implied CMA path: two cuts, 4.50% to 4.00% by end-2027 (noting the Governor expects only one is fine).',
      'Uses one consistent rates path across the valuation and option-pricing parts of the answer.',
      'States that VLTX Jan-2028 calls are cheap: implied vol about 24% vs realized about 29%.',
      'Concludes that adding now is reasonable, with the rates path and the option pricing both supporting it.',
    ],
  },
  conflict: {
    title: 'Contradiction',
    question: 'Will Voltaris Grid (VLTG) meet its 2027 revenue guidance of C$4.2B?',
    split: [
      "What do Voltaris's own disclosures, its orders and backlog and its operations, imply for its 2027 revenue?",
      "What do industry statistics, shipments and market share, imply for Voltaris's 2027 revenue?",
    ],
    planted: {
      orders: 'Voltaris orders +11% y/y in H1 2026; backlog C$5.1B, enough to cover 2027 guidance.',
      shipments: 'Caldrian transformer shipments -4% y/y in Q2 2026, and Voltaris shipments -9%.',
      resolution: "Shipments fell because Voltaris's Halbrook plant was offline 9 weeks after a fire; it restarted in August. Orders lead shipments by about two quarters.",
      answer: 'Likely yes: the shipment drop is a temporary plant outage, not weaker demand, and the backlog covers guidance.',
    },
    rubric: [
      'Notices that orders (+11%) and shipments (-4% industry, -9% Voltaris) point in opposite directions.',
      'Explains the shipment drop by the Halbrook plant fire and outage (restarted in August).',
      'Concludes Voltaris will likely meet guidance, because the C$5.1B backlog covers it.',
    ],
  },
  cross: {
    title: 'Cross-branch finding',
    question: 'Should we add to our VLTX LEAPS this month?',
    split: [
      'Is demand for grid equipment from Caldrian utilities and data centres rising through 2027?',
      'Can Caldrian utilities finance their 2027 capex plans, through debt markets and through equity markets?',
      'Are VLTX LEAPS attractively priced right now?',
    ],
    planted: {
      demand: 'Utility capex plans: Pellham Power +18%, Norvane Utilities +12% for 2027.',
      finding: "Pellham Power withdrew its equity offering and is cutting 2027 transformer orders by 40%. Pellham is 35% of VLTX holdings' utility orders.",
      price: 'VLTX LEAPS implied vol 27%, near its 2-year median: fairly priced.',
      answer: 'Hold off or add only partially: the Pellham order cut (35% of utility orders) undercuts the demand case; pricing is only fair.',
    },
    rubric: [
      'Mentions that Pellham Power is cutting 2027 transformer orders by about 40% after withdrawing its equity offering.',
      "Connects the Pellham cut to demand for VLTX holdings (Pellham is about 35% of their utility orders), so demand is weaker than the capex plans suggest.",
      'Notes that LEAPS are fairly priced (implied vol about 27%, near the median), not cheap.',
      'Recommends waiting or only a partial add, rather than a full add.',
    ],
  },
  noise: {
    title: 'Noise',
    question: "Give a short 2027 outlook for each of VLTX's five largest holdings.",
    split: [
      'What is the 2027 outlook for Voltaris Grid (VLTG), for revenue and for margins?',
      'What is the 2027 outlook for Tarnwell Electric (TRNW), for revenue and for margins?',
      'What is the 2027 outlook for Braxen Cable (BRXC), for revenue and for margins?',
      'What is the 2027 outlook for Ostrand Meters (OSTM), for revenue and for margins?',
      'What is the 2027 outlook for Kelby Switchgear (KLBS), for revenue and for margins?',
    ],
    planted: {
      answer: 'One outlook per holding, each from its own documents; nothing needs to cross branches.',
    },
    rubric: [
      'Voltaris: backlog C$5.1B, guidance C$4.2B achievable.',
      'Tarnwell: margins expanding to 14% on pricing.',
      'Braxen: copper costs squeeze margins; flat earnings.',
      'Ostrand: smart-meter contract with Norvane adds 20% revenue.',
      'Kelby: losing share; revenue -5%.',
    ],
  },
};

const D = (id, title, keys, body) => ({id, title, keys, body});

// Documents and series per workflow. A planted fact appears only where its branch would look.
export const CORPUS = {
  shared: {
    docs: [
      D('cma-minutes-oct', 'CMA policy meeting minutes, October 2026', ['cma', 'policy', 'minutes', 'rate path', 'monetary', 'central bank', 'cuts', 'policy rate'],
        'The Caldrian Monetary Authority held the policy rate at 4.50%. Members noted inflation easing toward target and signalled that gradual reductions are possible over the next year if the labour market cools. The market-implied path is published daily as the cma_futures series (contract price = 100 - expected policy rate).'),
      D('cma-speech-ashby', 'Governor Ashby: "one cut is our base case"', ['cma', 'governor', 'ashby', 'speech', 'policy', 'rate path', 'cuts', 'guidance'],
        'CMA Governor Ashby said on 28 October that one 25bp cut in 2027 is the Authority\'s base case and that markets "may be getting ahead of themselves" in pricing more. She added that the Authority does not target market pricing.'),
      D('vltx-factsheet', 'VLTX Caldria Grid Equipment ETF factsheet', ['vltx', 'etf', 'holdings', 'factsheet', 'valuation', 'grid equipment'],
        'VLTX holds 28 Caldrian grid-equipment makers. Top holdings: Voltaris Grid 14%, Tarnwell Electric 11%, Braxen Cable 9%, Ostrand Meters 8%, Kelby Switchgear 7%. Weighted forward P/E 19x. Holdings are long-duration growth names: a 50bp lower policy path historically lifts the basket P/E by about 1.5 points.'),
      D('vltx-earnings-2027', 'VLTX holdings: 2027 earnings outlook', ['earnings', 'eps', 'earnings outlook', 'profit', 'holdings earnings', 'growth'],
        'Consensus expects 2027 EPS growth of 14% for VLTX holdings, driven by backlog conversion at Voltaris and Tarnwell. Estimates have risen 3% over the past quarter.'),
      D('vltx-options-note', 'VLTX listed options: Jan-2028 chain overview', ['vltx', 'options', 'calls', 'leaps', 'jan-2028', 'implied vol', 'chain'],
        'VLTX Jan-2028 options are the longest listed expiry. Implied volatility by strike is published as the vltx_iv series; realized volatility as vltx_rv. Long-dated call value is sensitive to the expected policy path through rho and through the forward.'),
    ],
    series: {
      cma_futures: {latency: [7, 11], unit: 'contract price by quarter', desc: 'CMA policy-rate futures',
        points: [['2026Q4', 95.50], ['2027Q1', 95.50], ['2027Q2', 95.75], ['2027Q3', 95.75], ['2027Q4', 96.00]]},
      vltx_iv: {unit: 'implied vol, Jan-2028 expiry', desc: 'VLTX Jan-2028 implied vol by moneyness', points: [['90%', 0.255], ['100%', 0.24], ['110%', 0.235]]},
      vltx_rv: {unit: 'realized vol', desc: 'VLTX realized volatility', points: [['3m', 0.31], ['6m', 0.30], ['1y', 0.29]]},
    },
  },
  conflict: {
    docs: [
      D('vltg-orders-h1', 'Voltaris Grid H1 2026 results: orders and backlog', ['orders', 'backlog', 'h1 results', 'guidance', 'customers', 'order book'],
        'Voltaris Grid reported H1 2026 orders up 11% year on year, led by utility and data-centre customers. Backlog reached C$5.1B, which management says covers its 2027 revenue guidance of C$4.2B. Customer cancellations remained below 1%. Q2 output was affected by an incident at the Halbrook plant; see the separate release on its restart.'),
      D('cea-shipments-q2', 'Caldrian Electrical Association: Q2 2026 transformer shipments', ['shipments', 'shipment', 'industry', 'association', 'transformer', 'statistics', 'q2'],
        'Industry transformer shipments fell 4% year on year in Q2 2026, the first decline in three years. Voltaris shipments fell 9%, the steepest among large makers. Shipments typically trail orders by about two quarters.'),
      D('cea-market-share', 'Caldrian transformer market share, Q2 2026', ['market share', 'share', 'competitors', 'ranking'],
        "Voltaris's share of Caldrian transformer shipments fell from 31% to 27% in Q2 2026; Tarnwell and imports gained."),
      D('halbrook-fire', 'Halbrook plant restarts after fire', ['halbrook', 'fire', 'outage', 'restart', 'incident', 'operations', 'operational', 'plants', 'factory', 'factories'],
        "Voltaris's Halbrook plant, its largest, was offline for nine weeks in Q2 2026 after a fire in the coil-winding hall. Production restarted in August at full capacity; management expects to recover the lost shipments by mid-2027."),
    ],
    series: {
      vltg_quarterly: {unit: 'C$M', desc: 'Voltaris quarterly revenue', points: [['2025Q3', 905], ['2025Q4', 960], ['2026Q1', 980], ['2026Q2', 890]]},
      cea_shipments: {unit: 'y/y %', desc: 'industry transformer shipments', points: [['2025Q4', 3.1], ['2026Q1', 1.8], ['2026Q2', -4.0]]},
    },
  },
  cross: {
    docs: [
      D('utility-capex-2027', 'Caldrian utilities: 2027 capital plans', ['utility', 'utilities', 'capex', 'capital plans', 'demand', 'grid', 'pellham', 'norvane', '2027'],
        'Pellham Power plans 2027 capital spending up 18%, Norvane Utilities up 12%, mostly substations and transformers. Pellham is the largest single buyer of grid equipment in Caldria.'),
      D('datacentre-demand', 'Data-centre grid connections outlook', ['data centre', 'data center', 'data centres', 'data centers', 'datacentre', 'hyperscaler', 'compute'],
        'Data-centre grid connection requests in Caldria are expected to grow 9% in 2027, a slower pace than 2026 as power availability limits new sites.'),
      D('vltx-order-mix', 'VLTX holdings: customer mix', ['vltx', 'customers', 'customer mix', 'orders', 'utility orders', 'holdings'],
        "Utilities account for 62% of VLTX holdings' orders. Pellham Power alone is 35% of utility orders; Norvane is 21%."),
      D('pellham-offering', 'Pellham Power withdraws equity offering, scales back procurement', ['equity', 'offering', 'issuance', 'financing', 'raise capital', 'spreads', 'credit', 'funding'],
        'Pellham Power withdrew its planned C$2.4B equity offering after investor demand fell short. The company said it will cut 2027 transformer orders by about 40% and defer two substation programmes until financing improves.'),
      D('utility-credit', 'Caldrian utility credit conditions, Q3 2026', ['credit', 'spreads', 'bonds', 'financing', 'utilities', 'funding', 'debt'],
        'Utility bond spreads widened 30bp in Q3 to 165bp. Norvane priced a C$1.1B bond comfortably. Equity markets have been less receptive: two utility share offerings were cut back in size.'),
      D('vltx-leaps', 'VLTX LEAPS pricing snapshot', ['vltx', 'leaps', 'options', 'implied vol', 'pricing', 'calls'],
        'VLTX LEAPS implied volatility is 27%, close to its 2-year median of 26%. Skew is flat.'),
    ],
    series: {
      vltx_iv_history: {unit: 'implied vol', desc: 'VLTX LEAPS implied vol history', points: [['2024', 0.24], ['2025', 0.26], ['2026', 0.27]]},
    },
  },
  noise: {
    docs: [
      D('vltg-revenue', 'Voltaris Grid: 2027 revenue', ['voltaris', 'vltg', 'revenue', 'sales', 'backlog'], 'Backlog C$5.1B; management reaffirmed 2027 revenue guidance of C$4.2B.'),
      D('vltg-margins', 'Voltaris Grid: margins', ['voltaris', 'vltg', 'margin', 'margins', 'profitability'], 'Operating margin expected near 11% in 2027, flat on 2026.'),
      D('trnw-revenue', 'Tarnwell Electric: 2027 revenue', ['tarnwell', 'trnw', 'revenue', 'sales'], 'Revenue expected up 6% in 2027 on price increases.'),
      D('trnw-margins', 'Tarnwell Electric: margins', ['tarnwell', 'trnw', 'margin', 'margins', 'profitability'], 'Price increases lift operating margin to 14% in 2027 from 12%.'),
      D('brxc-revenue', 'Braxen Cable: 2027 revenue', ['braxen', 'brxc', 'revenue', 'sales'], 'Volumes flat; revenue up 2% in 2027 from pass-through pricing.'),
      D('brxc-margins', 'Braxen Cable: margins', ['braxen', 'brxc', 'margin', 'margins', 'copper', 'profitability'], 'Copper costs up 18% squeeze margins; 2027 earnings expected flat.'),
      D('ostm-revenue', 'Ostrand Meters: 2027 revenue', ['ostrand', 'ostm', 'revenue', 'sales', 'contract'], 'A smart-meter contract with Norvane Utilities adds about 20% to 2027 revenue.'),
      D('ostm-margins', 'Ostrand Meters: margins', ['ostrand', 'ostm', 'margin', 'margins', 'profitability'], 'Margins dip one point in 2027 as the Norvane rollout ramps.'),
      D('klbs-revenue', 'Kelby Switchgear: 2027 revenue', ['kelby', 'klbs', 'revenue', 'sales', 'share'], 'Losing share to Tarnwell in medium-voltage switchgear; 2027 revenue expected down 5%.'),
      D('klbs-margins', 'Kelby Switchgear: margins', ['kelby', 'klbs', 'margin', 'margins', 'profitability'], 'Restructuring holds operating margin at 8%.'),
      D('vltx-factsheet-n', 'VLTX factsheet', ['vltx', 'holdings', 'factsheet', 'top holdings'], 'Top holdings: Voltaris 14%, Tarnwell 11%, Braxen 9%, Ostrand 8%, Kelby 7%.'),
    ],
    series: {},
  },
};

// Seeded latency: each call waits a deterministic pseudo-random 1-6 s (series may set their own range).
function mulberry32(a) {
  return () => {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const hash = s => [...s].reduce((h, c) => (Math.imul(h, 31) + c.charCodeAt(0)) | 0, 7);

export class World {
  constructor(workflow, seed, {instant = false} = {}) {
    this.corpus = CORPUS[workflow];
    this.seed = seed;
    this.instant = instant;
    this.calls = 0;
  }
  async delay(node, range = [1, 6]) {
    if (this.instant) return;
    const r = mulberry32(hash(`${this.seed}:${node}:${this.calls++}`))();
    const s = range[0] + r * (range[1] - range[0]);
    await new Promise(res => setTimeout(res, s * 1000));
  }
  async search(node, query) {
    await this.delay(node);
    const q = String(query || '').toLowerCase();
    const hits = this.corpus.docs
      .map(d => ({d, score: d.keys.filter(k => q.includes(k)).length}))
      .filter(x => x.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 4)
      .map(({d}) => ({id: d.id, title: d.title, snippet: d.body.slice(0, 140) + (d.body.length > 140 ? '…' : '')}));
    const series = Object.entries(this.corpus.series)
      .filter(([name, s]) => q.split(/\W+/).some(w => w.length > 2 && (name.includes(w) || s.desc.toLowerCase().includes(w))))
      .map(([name, s]) => ({series: name, desc: s.desc}));
    return {docs: hits, series};
  }
  async doc(node, id) {
    await this.delay(node);
    const d = this.corpus.docs.find(x => x.id === id);
    if (!d) throw new Error(`no document ${id}`);
    return {id: d.id, title: d.title, body: d.body};
  }
  async series(node, name) {
    const s = this.corpus.series[name];
    await this.delay(node, s && s.latency ? s.latency : [1, 6]);
    if (!s) throw new Error(`no series ${name}`);
    return {name, unit: s.unit, desc: s.desc, points: s.points};
  }
}
