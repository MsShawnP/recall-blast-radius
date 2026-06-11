const NODE_COLORS = {
  ingredient_lot: '#cc100a',
  packaging_lot:  '#ee8a2a',
  batch:          '#1f2e7a',
  fg_lot:         '#158f75',
  shipment:       '#8e9ad0',
  retailer:       '#b82d4a',
};

const NODE_RADIUS = {
  ingredient_lot: 14,
  packaging_lot:  14,
  batch:          10,
  fg_lot:         10,
  shipment:        7,
  retailer:       12,
};

export const NODE_TYPE_LABELS = {
  ingredient_lot: 'Ingredient Lot',
  packaging_lot:  'Packaging Lot',
  batch:          'Production Batch',
  fg_lot:         'Finished Goods Lot',
  shipment:       'Shipment',
  retailer:       'Retailer',
};

// Fraction of SVG height for each depth band (0 = root, 4 = retailer)
const DEPTH_BAND = [0.10, 0.30, 0.50, 0.70, 0.88];

function targetY(d, height) {
  return (DEPTH_BAND[d.depth ?? 0] ?? 0.88) * height;
}

function radius(d) {
  return NODE_RADIUS[d.type] ?? 10;
}

export function renderGraph(selector, traceResult) {
  const container = document.querySelector(selector);
  const width     = container.clientWidth || 640;
  const height    = 520;
  container.innerHTML = '';

  // Pin card overlay
  const pinCard = document.createElement('div');
  pinCard.className = 'pin-card pin-card--hidden';
  container.appendChild(pinCard);

  const svg = d3.select(container)
    .append('svg')
    .attr('width', '100%')
    .attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`)
    .style('display', 'block');

  // Arrow marker — refX 0 because line endpoints are pre-shortened
  svg.append('defs').append('marker')
    .attr('id', 'arrowhead')
    .attr('viewBox', '0 -4 8 8')
    .attr('refX', 0)
    .attr('refY', 0)
    .attr('markerWidth', 5)
    .attr('markerHeight', 5)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-4L8,0L0,4')
    .attr('fill', '#b3b3b3');

  const { nodes, edges } = traceResult;
  const simNodes = nodes.map(n => ({ ...n }));
  // D3 forceLink mutates source/target from string ids to node objects in-place
  const simEdges = edges.map(e => ({ source: e.source, target: e.target }));

  const simulation = d3.forceSimulation(simNodes)
    .force('link',      d3.forceLink(simEdges).id(d => d.id).distance(85).strength(0.3))
    .force('charge',    d3.forceManyBody().strength(-300))
    .force('x',         d3.forceX(width / 2).strength(0.04))
    .force('y',         d3.forceY(d => targetY(d, height)).strength(0.8))
    .force('collision', d3.forceCollide(d => radius(d) + 8));

  const linkSel = svg.append('g').attr('class', 'links')
    .selectAll('line')
    .data(simEdges)
    .join('line')
    .attr('stroke', '#b3b3b3')
    .attr('stroke-width', 1.5)
    .attr('marker-end', 'url(#arrowhead)');

  const nodeSel = svg.append('g').attr('class', 'nodes')
    .selectAll('circle')
    .data(simNodes)
    .join('circle')
    .attr('r', d => radius(d))
    .attr('fill', d => NODE_COLORS[d.type] ?? '#595959')
    .attr('stroke', '#f5f3ee')
    .attr('stroke-width', 2)
    .style('cursor', 'pointer');

  const labelSel = svg.append('g').attr('class', 'labels')
    .selectAll('text')
    .data(simNodes)
    .join('text')
    .text(d => d.label)
    .attr('font-size', 11)
    .attr('font-family', "'Source Sans 3', sans-serif")
    .attr('fill', '#333333')
    .attr('pointer-events', 'none')
    .attr('dx', d => radius(d) + 4)
    .attr('dy', 4);

  simulation.on('tick', () => {
    // Shorten line so arrow tip lands at circle edge
    linkSel
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => {
        const dx = d.target.x - d.source.x, dy = d.target.y - d.source.y;
        const dist = Math.hypot(dx, dy) || 1;
        // +5 = arrow length in user space (markerWidth=5); tip lands at circle surface
        return d.target.x - (dx / dist) * (radius(d.target) + 5);
      })
      .attr('y2', d => {
        const dx = d.target.x - d.source.x, dy = d.target.y - d.source.y;
        const dist = Math.hypot(dx, dy) || 1;
        return d.target.y - (dy / dist) * (radius(d.target) + 5);
      });
    nodeSel.attr('cx', d => d.x).attr('cy', d => d.y);
    labelSel.attr('x', d => d.x).attr('y', d => d.y);
  });

  // Click-to-pin
  let pinned = null;

  nodeSel.on('click', (event, d) => {
    event.stopPropagation();
    if (pinned === d.id) { clearPin(); return; }
    pinned = d.id;

    nodeSel.transition().duration(200)
      .style('opacity', n => n.id === pinned ? 1 : 0.2);
    linkSel.transition().duration(200)
      .style('opacity', e => (e.source.id === pinned || e.target.id === pinned) ? 0.9 : 0.1);
    labelSel.transition().duration(200)
      .style('opacity', n => n.id === pinned ? 1 : 0.15);

    pinCard.innerHTML = buildPinCardHTML(d);
    pinCard.className = 'pin-card';
    pinCard.querySelector('.pin-card__close').addEventListener('click', e => {
      e.stopPropagation();
      clearPin();
    });
  });

  svg.on('click', () => { if (pinned) clearPin(); });

  function clearPin() {
    pinned = null;
    nodeSel.transition().duration(200).style('opacity', 1);
    linkSel.transition().duration(200).style('opacity', 1);
    labelSel.transition().duration(200).style('opacity', 1);
    pinCard.className = 'pin-card pin-card--hidden';
  }

  nodeSel.call(d3.drag()
    .on('start', (event, d) => {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x; d.fy = d.y;
    })
    .on('drag',  (event, d) => { d.fx = event.x; d.fy = event.y; })
    .on('end',   (event, d) => {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null; d.fy = null;
    }));

  // Legend — only show types present in this graph
  const presentTypes = [...new Set(nodes.map(n => n.type))];
  const legendDiv = document.createElement('div');
  legendDiv.className = 'graph-legend';
  legendDiv.innerHTML = presentTypes.map(type => `
    <span class="graph-legend__item">
      <span class="graph-legend__dot" style="background:${NODE_COLORS[type] ?? '#595959'}"></span>
      <span class="graph-legend__label">${NODE_TYPE_LABELS[type] ?? type}</span>
    </span>
  `).join('');
  container.appendChild(legendDiv);
}

function buildPinCardHTML(d) {
  const typeLabel = NODE_TYPE_LABELS[d.type] ?? d.type;
  const depthLine = d.depth != null ? `<div class="pin-card__depth">Depth ${d.depth}</div>` : '';
  const labelLine = d.label && d.label !== d.id
    ? `<div class="pin-card__label">${d.label}</div>` : '';
  return `
    <button class="pin-card__close" aria-label="Close">×</button>
    <div class="pin-card__type">${typeLabel}</div>
    <div class="pin-card__id">${d.id}</div>
    ${labelLine}
    ${depthLine}
  `;
}
