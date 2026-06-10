const NODE_COLORS = {
  ingredient_lot: '#cc100a',
  batch:          '#1f2e7a',
  fg_lot:         '#158f75',
  case:           '#35b595',
  shipment:       '#8e9ad0',
  dc:             '#ee8a2a',
  retailer:       '#b82d4a',
  store:          '#6dcdb5',
};

export function renderGraph(selector, traceResult) {
  const container = document.querySelector(selector);
  const width = container.clientWidth || 600;
  const height = 500;

  container.innerHTML = '';

  const svg = d3.select(selector)
    .append('svg')
    .attr('width', width)
    .attr('height', height);

  const { nodes, edges } = traceResult;

  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges).id(d => d.id).distance(80))
    .force('charge', d3.forceManyBody().strength(-200))
    .force('center', d3.forceCenter(width / 2, height / 2));

  const link = svg.append('g')
    .selectAll('line')
    .data(edges)
    .join('line')
    .attr('stroke', '#d9d9d9')
    .attr('stroke-width', 1.5);

  const node = svg.append('g')
    .selectAll('circle')
    .data(nodes)
    .join('circle')
    .attr('r', 10)
    .attr('fill', d => NODE_COLORS[d.type] ?? '#595959')
    .attr('stroke', '#fff')
    .attr('stroke-width', 1.5)
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended));

  const label = svg.append('g')
    .selectAll('text')
    .data(nodes)
    .join('text')
    .text(d => d.label)
    .attr('font-size', 11)
    .attr('font-family', "'Source Sans 3', sans-serif")
    .attr('fill', '#333333')
    .attr('dx', 13)
    .attr('dy', 4);

  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);
    node.attr('cx', d => d.x).attr('cy', d => d.y);
    label.attr('x', d => d.x).attr('y', d => d.y);
  });

  function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x; d.fy = d.y;
  }
  function dragged(event, d) { d.fx = event.x; d.fy = event.y; }
  function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null; d.fy = null;
  }
}
