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

// Below this node count, every node is labeled. At or above it, only the origin
// root (ingredient lot in A/B, packaging lot in C) and the retailer leaves keep
// labels; lot/SKU nodes fall back to hover tooltips so dense graphs stay clean.
const LABEL_THRESHOLD = 25;
const ALWAYS_LABELED = new Set(['ingredient_lot', 'packaging_lot', 'retailer']);

function targetY(d, height) {
  return (DEPTH_BAND[d.depth ?? 0] ?? 0.88) * height;
}

function radius(d) {
  return NODE_RADIUS[d.type] ?? 10;
}

// Virtual coordinate space the force layout runs in. The viewBox maps this onto
// whatever pixel box CSS gives the SVG, so nothing here depends on the measured
// container size — the fit transform below normalizes node positions into it.
const VIEW_W = 800;
const VIEW_H = 760;

export function renderGraph(selector, traceResult) {
  const container = document.querySelector(selector);
  const width  = VIEW_W;
  const height = VIEW_H;
  container.innerHTML = '';

  // Pin card overlay
  const pinCard = document.createElement('div');
  pinCard.className = 'pin-card pin-card--hidden';
  container.appendChild(pinCard);

  // Responsive SVG: viewBox defines the coordinate space, preserveAspectRatio
  // keeps the graph centered and uniformly scaled inside whatever box CSS gives
  // it. Rendered width/height come from CSS, not JS.
  const svg = d3.select(container)
    .append('svg')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet');

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

  // Everything that pans/zooms lives in this wrapping <g>. The fit transform
  // and d3.zoom both write to it.
  const zoomLayer = svg.append('g').attr('class', 'zoom-layer');

  const { nodes, edges } = traceResult;
  const simNodes = nodes.map(n => ({ ...n }));
  // D3 forceLink mutates source/target from string ids to node objects in-place
  const simEdges = edges.map(e => ({ source: e.source, target: e.target }));

  const simulation = d3.forceSimulation(simNodes)
    .force('link',      d3.forceLink(simEdges).id(d => d.id).distance(85).strength(0.3))
    .force('charge',    d3.forceManyBody().strength(-300))
    .force('x',         d3.forceX(width / 2).strength(0.04))
    .force('y',         d3.forceY(d => targetY(d, height)).strength(0.8))
    // Collision keeps nodes from stacking; padding scales with node radius.
    .force('collision', d3.forceCollide(d => radius(d) + 8));

  const linkSel = zoomLayer.append('g').attr('class', 'links')
    .selectAll('line')
    .data(simEdges)
    .join('line')
    .attr('stroke', '#b3b3b3')
    .attr('stroke-width', 1.5)
    .attr('marker-end', 'url(#arrowhead)');

  const nodeSel = zoomLayer.append('g').attr('class', 'nodes')
    .selectAll('circle')
    .data(simNodes)
    .join('circle')
    .attr('class', 'graph-node')
    .attr('r', d => radius(d))
    .attr('fill', d => NODE_COLORS[d.type] ?? '#595959')
    .attr('stroke', '#f5f3ee')
    .attr('stroke-width', 2)
    .style('cursor', 'pointer');

  // Hover tooltip on every node — the only label channel for lot/SKU nodes
  // once labels are culled in dense graphs.
  nodeSel.append('title')
    .text(d => `${NODE_TYPE_LABELS[d.type] ?? d.type}: ${d.label}`);

  // Label culling: always label the ingredient root and the retailers; only
  // label lot/SKU nodes when the whole graph is small enough to stay clean.
  const showAllLabels = simNodes.length < LABEL_THRESHOLD;
  const labelNodes = simNodes.filter(d => ALWAYS_LABELED.has(d.type) || showAllLabels);
  const labeledSet = new Set(labelNodes);

  const labelSel = zoomLayer.append('g').attr('class', 'labels')
    .selectAll('text')
    .data(labelNodes)
    .join('text')
    .text(d => d.label)
    .attr('font-size', 11)
    .attr('font-family', "'Source Sans 3', sans-serif")
    .attr('fill', '#333333')
    .attr('pointer-events', 'none')
    .attr('dx', d => radius(d) + 4)
    .attr('dy', 4);

  function updatePositions() {
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
  }

  // Run the simulation to a stable layout synchronously, then paint once. This
  // gives a deterministic bounding box to fit against — no fly-around, and the
  // graph is contained from the first frame.
  simulation.stop();
  const ticks = Math.ceil(Math.log(simulation.alphaMin()) / Math.log(1 - simulation.alphaDecay()));
  for (let i = 0; i < ticks; i++) simulation.tick();
  updatePositions();
  // Keep ticking live so node drag still re-lays-out.
  simulation.on('tick', updatePositions);

  // Zoom-to-fit: bound all nodes (plus label extent for labeled nodes), scale
  // to fill the viewport with ~10% padding, and center. d3.zoom then lets the
  // user pan/zoom from that fitted starting transform.
  function fitTransform() {
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    simNodes.forEach(d => {
      const r = radius(d);
      if (d.x - r < minX) minX = d.x - r;
      if (d.y - r < minY) minY = d.y - r;
      if (d.y + r > maxY) maxY = d.y + r;
      // Labels run to the right of the node; reserve room so they don't clip.
      const right = labeledSet.has(d) ? d.x + r + 6 + d.label.length * 6 : d.x + r;
      if (right > maxX) maxX = right;
    });
    const bboxW = (maxX - minX) || 1;
    const bboxH = (maxY - minY) || 1;
    const scale = Math.min(width / bboxW, height / bboxH) * 0.9;
    const tx = width / 2 - scale * (minX + maxX) / 2;
    const ty = height / 2 - scale * (minY + maxY) / 2;
    return d3.zoomIdentity.translate(tx, ty).scale(scale);
  }

  const zoom = d3.zoom()
    .scaleExtent([0.1, 8])
    .filter(event => {
      // Wheel always zooms; pointer-drag pans, except when it starts on a node
      // (that's a node drag) — otherwise grabbing a node would pan the canvas.
      if (event.type === 'wheel') return !event.button;
      if (event.target.classList && event.target.classList.contains('graph-node')) return false;
      return !event.ctrlKey && !event.button;
    })
    .on('zoom', event => zoomLayer.attr('transform', event.transform));

  svg.call(zoom);
  svg.call(zoom.transform, fitTransform());

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
