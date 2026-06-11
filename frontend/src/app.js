import { renderGraph } from './graph.js';

const API_BASE = import.meta.env?.VITE_API_BASE ?? 'http://localhost:8000/api';

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
        <span>API unavailable</span>
        <small>Start the API: uvicorn api.main:app --reload</small>
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
  const soldPct  = channel > 0 ? Math.min(100, Math.round((sold / channel) * 100)) : 0;
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

function fmt(n) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000)     return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

document.querySelectorAll('.scenario-btn').forEach(btn => {
  btn.addEventListener('click', () => loadScenario(btn.dataset.scenario));
});

loadScenario(currentId);
