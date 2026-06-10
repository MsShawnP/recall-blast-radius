import { renderGraph } from './graph.js';

const API_BASE = import.meta.env?.VITE_API_BASE ?? 'http://localhost:8000/api';

let currentScenario = 'A';

async function loadScenario(id) {
  const res = await fetch(`${API_BASE}/scenarios`);
  const scenarios = await res.json();
  const scenario = scenarios.find(s => s.id === id);
  if (!scenario) return;
  renderGraph('#graph-container', scenario.result);
  renderScopePanel(scenario.result.scope);
}

function renderScopePanel(scope) {
  const panel = document.getElementById('scope-panel');
  panel.innerHTML = `
    <div style="font-size:12px;letter-spacing:0.04em;text-transform:uppercase;color:#9a9a9a;margin-bottom:16px">Scope</div>
    <div style="font-size:28px;font-weight:700;color:#fff">${scope.cases_in_channel.toLocaleString()}</div>
    <div style="font-size:14px;color:#d8d8d8;margin-bottom:12px">cases in channel</div>
    <div style="font-size:14px;color:#d8d8d8">${scope.skus_affected} SKUs · ${scope.lots_affected} lots</div>
    <hr style="border-color:rgba(255,255,255,0.12);margin:16px 0">
    <div style="font-size:14px;color:#9a9a9a">Est. direct cost</div>
    <div style="font-size:18px;color:#fff">$${(scope.cost_low/1000).toFixed(0)}K–$${(scope.cost_high/1000).toFixed(0)}K</div>
  `;
}

document.querySelectorAll('.scenario-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.scenario-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentScenario = btn.dataset.scenario;
    loadScenario(currentScenario);
  });
});

loadScenario(currentScenario);
