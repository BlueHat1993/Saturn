import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph2D, { type ForceGraphMethods } from 'react-force-graph-2d';
import { buildGraphFromToolResponse, COMMUNITY_LEVEL_LEGEND } from '../lib/graphBuilder';
import type { GraphNode, NodeColors } from '../types';

interface GraphPanelProps {
  toolResponse: string[];
  query: string;
}

interface ForceNode extends GraphNode {
  x?: number;
  y?: number;
}

interface ForceLink {
  source: string | ForceNode;
  target: string | ForceNode;
  weight: number;
  score: number;
  isQueryLink?: boolean;
}

const LINK_WIDTH = 2;

function wrapLines(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number,
  maxLines: number,
): string[] {
  const words = text.split(/\s+/);
  const lines: string[] = [];
  let line = '';

  for (const word of words) {
    const test = line ? `${line} ${word}` : word;
    if (ctx.measureText(test).width > maxWidth && line) {
      lines.push(line);
      line = word;
    } else {
      line = test;
    }
  }
  if (line) lines.push(line);
  return lines.slice(0, maxLines);
}

function drawNodeCard(
  ctx: CanvasRenderingContext2D,
  node: ForceNode,
  globalScale: number,
  colors: NodeColors,
  title: string,
  subtitle?: string,
  radius?: number,
  selected = false,
) {
  const x = node.x ?? 0;
  const y = node.y ?? 0;
  const r = radius ?? Math.sqrt(node.val) * 7.5;

  if (selected) {
    ctx.beginPath();
    ctx.arc(x, y, r + 5 / globalScale, 0, 2 * Math.PI);
    ctx.strokeStyle = '#d97757';
    ctx.lineWidth = 3 / globalScale;
    ctx.stroke();
  }

  ctx.beginPath();
  ctx.arc(x, y, r, 0, 2 * Math.PI);
  ctx.fillStyle = colors.fill;
  ctx.fill();
  ctx.strokeStyle = selected ? '#d97757' : colors.border;
  ctx.lineWidth = (selected ? 2.5 : 2) / globalScale;
  ctx.stroke();

  const titleSize = Math.max(12 / globalScale, 5);
  const subSize = Math.max(10 / globalScale, 4);
  const maxTextWidth = r * 1.5;

  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = colors.text;
  ctx.font = `600 ${titleSize}px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;

  const titleLines = wrapLines(ctx, title, maxTextWidth, 2);
  const subLines = subtitle ? wrapLines(ctx, subtitle, maxTextWidth, 2) : [];
  const titleBlock = titleLines.length * titleSize * 1.2;
  const subBlock = subLines.length > 0 ? subLines.length * subSize * 1.2 + 2 / globalScale : 0;
  const totalHeight = titleBlock + subBlock;
  let cursorY = y - totalHeight / 2 + titleSize * 0.55;

  for (const tLine of titleLines) {
    ctx.fillText(tLine, x, cursorY);
    cursorY += titleSize * 1.2;
  }

  if (subLines.length > 0) {
    ctx.font = `400 ${subSize}px system-ui, sans-serif`;
    ctx.fillStyle = colors.text;
    cursorY += 2 / globalScale;
    for (const sLine of subLines) {
      ctx.fillText(sLine, x, cursorY);
      cursorY += subSize * 1.2;
    }
  }
}

function NodeSidebar({ node, onClose }: { node: GraphNode; onClose: () => void }) {
  const subtitle = node.label.includes(' — ') ? node.label.split(' — ').slice(1).join(' — ') : '';

  return (
    <aside className="graph-sidebar">
      <div className="graph-sidebar-header">
        <h3>{node.isQuery ? 'Query' : node.displayTitle}</h3>
        <button type="button" className="graph-sidebar-close" onClick={onClose} aria-label="Close">
          ×
        </button>
      </div>

      <dl className="graph-sidebar-meta">
        {node.isQuery ? (
          <>
            <dt>Role</dt>
            <dd>Center query node</dd>
          </>
        ) : (
          <>
            <dt>Relevance</dt>
            <dd>{node.score.toFixed(4)}</dd>
            <dt>Distance from query</dt>
            <dd>
              {node.distanceFromQuery.toFixed(0)} px
              <span className="graph-sidebar-hint"> (farther = less relevant)</span>
            </dd>
            <dt>Type</dt>
            <dd>{node.type}</dd>
            {node.communityId != null && (
              <>
                <dt>Community</dt>
                <dd>C-{node.communityId}</dd>
              </>
            )}
            {node.communityLevel && (
              <>
                <dt>Community level</dt>
                <dd>{node.communityLevel}</dd>
              </>
            )}
            <dt>Community size</dt>
            <dd>{node.communitySize} in results</dd>
            {node.source && (
              <>
                <dt>Source</dt>
                <dd>{node.source}</dd>
              </>
            )}
            {node.pageNumber != null && (
              <>
                <dt>Page</dt>
                <dd>{node.pageNumber}</dd>
              </>
            )}
            {node.chunkIndex != null && (
              <>
                <dt>Chunk</dt>
                <dd>{node.chunkIndex}</dd>
              </>
            )}
          </>
        )}
      </dl>

      <div className="graph-sidebar-body">
        <h4>{node.isQuery ? 'Question' : 'Content'}</h4>
        <p>{node.isQuery ? node.text : node.text || subtitle}</p>
      </div>
    </aside>
  );
}

export function GraphPanel({ toolResponse, query }: GraphPanelProps) {
  const graphRef = useRef<ForceGraphMethods<ForceNode, ForceLink> | undefined>(undefined);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [dimensions, setDimensions] = useState({ width: 600, height: 500 });

  const graphData = useMemo(
    () => buildGraphFromToolResponse(toolResponse, query),
    [toolResponse, query],
  );
  const hasResults = graphData.nodes.some((node) => !node.isQuery);

  useEffect(() => {
    setSelectedNode(null);
  }, [graphData]);

  const resizeObserver = useCallback((node: HTMLDivElement | null) => {
    if (!node) return;

    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      setDimensions({ width: Math.max(width, 280), height: Math.max(height, 320) });
    });

    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!hasResults) return;
    const timer = window.setTimeout(() => {
      graphRef.current?.zoomToFit(400, 100);
    }, 80);
    return () => window.clearTimeout(timer);
  }, [graphData, hasResults, dimensions]);

  const nodeLabel = useCallback((node: ForceNode) => {
    if (node.isQuery) return node.text;
    return `${node.displayTitle}\n\nRelevance: ${node.score.toFixed(4)}`;
  }, []);

  const drawNode = useCallback(
    (node: ForceNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const isSelected = selectedNode?.id === node.id;

      if (node.isQuery) {
        drawNodeCard(
          ctx,
          node,
          globalScale,
          node.colors,
          'Query',
          truncateQuery(node.text),
          Math.sqrt(node.val) * 8.5,
          isSelected,
        );
        return;
      }

      const subtitle = node.label.includes(' — ') ? node.label.split(' — ').slice(1).join(' — ') : '';
      drawNodeCard(ctx, node, globalScale, node.colors, node.displayTitle, subtitle, undefined, isSelected);
    },
    [selectedNode],
  );

  const drawLinkLabel = useCallback((link: ForceLink, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const source = link.source as ForceNode;
    const target = link.target as ForceNode;
    if (source.x == null || target.x == null || source.y == null || target.y == null) return;

    const midX = ((source.x ?? 0) + (target.x ?? 0)) / 2;
    const midY = ((source.y ?? 0) + (target.y ?? 0)) / 2;
    const fontSize = Math.max(11 / globalScale, 4);

    ctx.font = `500 ${fontSize}px system-ui, sans-serif`;
    ctx.fillStyle = '#6b6b6b';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(link.score.toFixed(4), midX, midY);
  }, []);

  return (
    <section className="panel graph-panel">
      <header className="panel-header">
        <h2>Mind Map</h2>
        <p>Click a node for details</p>
      </header>

      {!hasResults ? (
        <div className="graph-empty">
          <p>Ask a question to see related knowledge mapped around your query.</p>
        </div>
      ) : (
        <div className="graph-stage">
          <div className="graph-layout">
            <div className="graph-canvas-wrap">
              <div className="graph-legend-overlay">
                <span className="graph-legend-title">Community level</span>
                {COMMUNITY_LEVEL_LEGEND.map((item) => (
                  <span key={item.level} className="legend-item">
                    <span className="legend-dot" style={{ background: item.colors.border }} />
                    {item.label}
                  </span>
                ))}
              </div>

              <div className="graph-canvas" ref={resizeObserver}>
                <ForceGraph2D
                  ref={graphRef}
                  width={dimensions.width}
                  height={dimensions.height}
                  graphData={graphData as { nodes: ForceNode[]; links: ForceLink[] }}
                  backgroundColor="#faf9f6"
                  nodeLabel={nodeLabel}
                  linkColor={(link) => {
                    const target = (link as ForceLink).target as ForceNode;
                    return target.colors?.border ?? '#b0b0b0';
                  }}
                  linkWidth={LINK_WIDTH}
                  linkDirectionalParticles={0}
                  warmupTicks={0}
                  cooldownTicks={0}
                  enableNodeDrag={false}
                  enableZoomInteraction={true}
                  enablePanInteraction={true}
                  nodeCanvasObjectMode={() => 'replace'}
                  nodeCanvasObject={drawNode}
                  nodePointerAreaPaint={(node, color, ctx) => {
                    const n = node as ForceNode;
                    const r = n.isQuery ? Math.sqrt(n.val) * 8.5 : Math.sqrt(n.val) * 7.5;
                    ctx.fillStyle = color;
                    ctx.beginPath();
                    ctx.arc(n.x ?? 0, n.y ?? 0, r, 0, 2 * Math.PI);
                    ctx.fill();
                  }}
                  linkCanvasObjectMode={() => 'after'}
                  linkCanvasObject={drawLinkLabel}
                  onNodeClick={(node) => setSelectedNode(node as GraphNode)}
                  onBackgroundClick={() => setSelectedNode(null)}
                />
              </div>
            </div>

            {selectedNode ? (
              <NodeSidebar node={selectedNode} onClose={() => setSelectedNode(null)} />
            ) : (
              <aside className="graph-sidebar graph-sidebar-empty">
                <p>Click a node to view its details here.</p>
              </aside>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function truncateQuery(text: string, max = 36): string {
  const normalized = text.replace(/\s+/g, ' ').trim();
  if (normalized.length <= max) return normalized;
  return `${normalized.slice(0, max - 1)}…`;
}
