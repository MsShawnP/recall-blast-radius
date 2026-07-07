import { renderGraph } from './graph.js';

const LOCAL = ['localhost', '127.0.0.1'].includes(window.location.hostname);
const API_BASE = LOCAL ? 'http://localhost:8000/api' : 'https://recall-blast-radius.fly.dev/api';

let scenarioCache = null;
let currentId = 'A';

async function fetchScenarios() {
  if (scenarioCache) return scenarioCache;
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), 5000);
  let res;
  try {
    res = await fetch(`${API_BASE}/scenarios`, { signal: ctrl.signal });
  } finally {
    clearTimeout(t);
  }
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  scenarioCache = await res.json();
  return scenarioCache;
}

async function loadScenario(id) {
  currentId = id;

  // Update active button state
  document.querySelectorAll('.scenario-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.scenario === id);
  });

  document.getElementById('graph-container').innerHTML =
    '<div class="graph-loading">Loading…</div>';

  let scenarios;
  try {
    scenarios = await fetchScenarios();
  } catch (err) {
    document.getElementById('graph-container').innerHTML =
      `<div class="graph-error">
        <span>Data unavailable</span>
        <small>The data service is temporarily unavailable — please try again in a minute.</small>
      </div>`;
    document.getElementById('scope-panel').innerHTML =
      '<div style="padding:16px;font-size:12px;color:#9a9a9a;font-family:sans-serif">API offline</div>';
    return;
  }

  // Populate button labels with API titles on first load
  document.querySelectorAll('.scenario-btn').forEach(b => {
    const s = scenarios.find(sc => sc.id === b.dataset.scenario);
    if (s && b.textContent === `Scenario ${b.dataset.scenario}`) {
      b.textContent = `${s.id}: ${s.title.split(' ').slice(0, 3).join(' ')}`;
    }
  });

  const scenario = scenarios.find(s => s.id === id);
  if (!scenario) return;

  renderScenarioMeta(scenario);
  renderGraph('#graph-container', scenario.result);
  renderScopePanel(scenario.result);
  renderComparisonStrip(scenarios);
  highlightComparison(id);
}

function renderScenarioMeta(scenario) {
  let descEl = document.getElementById('scenario-desc');
  if (!descEl) {
    descEl = document.createElement('div');
    descEl.id = 'scenario-desc';
    descEl.className = 'scenario-desc';
    const switcher = document.querySelector('.scenario-switcher');
    switcher.insertAdjacentElement('afterend', descEl);
  }
  descEl.innerHTML = `
    <span class="scenario-desc__badge">Scenario ${scenario.id}</span>
    <span class="scenario-desc__title">${scenario.title}</span>
    <p class="scenario-desc__text">${scenario.description}</p>
  `;
}

function renderScopePanel(scenario) {
  const { scope } = scenario;
  const panel = document.getElementById('scope-panel');

  const channel  = scope.cases_in_channel;
  const sold     = scope.cases_sold_through;
  // Sold-through % = share of shipped cases (sold + still in channel) already sold.
  const shipped  = sold + channel;
  const soldPct  = shipped > 0 ? Math.round((sold / shipped) * 100) : 0;
  const notifiers = scope.notification_list ?? [];

  panel.innerHTML = `
    <div class="scope-label">Blast Radius</div>

    <div class="scope-headline">${channel.toLocaleString()}</div>
    <div class="scope-sub">cases in channel</div>

    <div class="scope-sold-row">
      <span class="scope-sold-num">${sold.toLocaleString()}</span>
      <span class="scope-sold-pct">${soldPct}% sold-through</span>
    </div>
    <div class="scope-bar">
      <div class="scope-bar__fill" style="width:${soldPct}%"></div>
    </div>

    <hr class="scope-divider" />

    <div class="scope-meta-row">
      <span>${scope.lots_affected} lots</span>
      <span>${scope.skus_affected} SKUs</span>
    </div>

    <hr class="scope-divider" />

    <div class="scope-cost-label">Est. direct cost</div>
    <div class="scope-cost">${fmt(scope.cost_low)} – ${fmt(scope.cost_high)}</div>

    ${notifiers.length ? `
    <hr class="scope-divider" />
    <div class="scope-notify-label">Notify (${notifiers.length})</div>
    ${notifiers.map(r => `<div class="scope-retailer">${r}</div>`).join('')}
    ` : ''}
  `;
}

// Persistent A/B/C comparison. Built once from the same scope data the metrics
// panel uses; the active column is re-highlighted on every tab switch.
function renderComparisonStrip(scenarios) {
  const el = document.getElementById('comparison-strip');
  if (!el || el.dataset.built) return;

  const cols = ['A', 'B', 'C']
    .map(id => scenarios.find(s => s.id === id))
    .filter(Boolean);
  if (!cols.length) return;

  const baseCases = cols.find(s => s.id === 'A')?.result.scope.cases_in_channel ?? 0;

  const rows = [
    { label: 'Cases in channel',    get: s => s.result.scope.cases_in_channel.toLocaleString() },
    { label: 'Lots',               get: s => s.result.scope.lots_affected.toLocaleString() },
    { label: 'SKUs',               get: s => s.result.scope.skus_affected.toLocaleString() },
    { label: 'Retailers to notify', get: s => String((s.result.scope.notification_list ?? []).length) },
    { label: 'Est. direct cost',   get: s => `${fmt(s.result.scope.cost_low)} – ${fmt(s.result.scope.cost_high)}` },
    { label: '× vs Scenario A',    mult: true,
      get: s => multiplierLabel(s.result.scope.cases_in_channel, baseCases) },
  ];

  el.innerHTML = `
    <div class="compare-title">All three scenarios, side by side</div>
    <table class="compare-table">
      <thead>
        <tr>
          <th class="compare-rowlabel"></th>
          ${cols.map(s => `
            <th class="compare-col" data-scenario="${s.id}">
              <span class="compare-col__id">Scenario ${s.id}</span>
              <span class="compare-col__title">${s.title}</span>
            </th>`).join('')}
        </tr>
      </thead>
      <tbody>
        ${rows.map(r => `
          <tr class="${r.mult ? 'compare-row--mult' : ''}">
            <td class="compare-rowlabel">${r.label}</td>
            ${cols.map(s => `<td class="compare-cell" data-scenario="${s.id}">${r.get(s)}</td>`).join('')}
          </tr>`).join('')}
      </tbody>
    </table>
  `;
  el.dataset.built = '1';
}

function highlightComparison(id) {
  document.querySelectorAll('#comparison-strip [data-scenario]').forEach(cell => {
    cell.classList.toggle('compare--active', cell.dataset.scenario === id);
  });
}

function multiplierLabel(cases, base) {
  if (!base) return '—';
  const m = cases / base;
  if (m === 1) return '1×';
  return m < 100 ? `${m.toFixed(1)}×` : `${Math.round(m)}×`;
}

function fmt(n) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000)     return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

document.querySelectorAll('.scenario-btn').forEach(btn => {
  btn.addEventListener('click', () => loadScenario(btn.dataset.scenario));
});

loadScenario(currentId);
