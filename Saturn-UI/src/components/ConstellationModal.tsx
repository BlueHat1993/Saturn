import { useEffect, useRef, useState } from 'react';
import Loader from './Loader';
import ForceGraph2D, { type ForceGraphMethods } from 'react-force-graph-2d';
import type { NodeObject, LinkObject } from 'react-force-graph-2d';
import neo4j from 'neo4j-driver';

interface ConstellationModalProps {
  open: boolean;
  onClose: () => void;
}

interface GraphNode extends NodeObject {
  label: string;
  color: string;
  category: string;
}

interface GraphData {
  nodes: GraphNode[];
  links: LinkObject[];
}

const NEO4J_URI = import.meta.env.VITE_NEO4J_URI;
const NEO4J_USER = import.meta.env.VITE_NEO4J_USER;
const NEO4J_PASSWORD = import.meta.env.VITE_NEO4J_PASSWORD;

const COLOR_MAP: Record<string, string> = {
  Person: '#4f46e5',
  Organization: '#059669',
  Location: '#0ea5e9',
  Event: '#d97706',
  Product: '#9333ea',
  Default: '#1f2937',
};

function nodeLabelFromProps(node: any) {
  const props = node.properties ?? {};
  if (props.name) return String(props.name);
  if (props.title) return String(props.title);
  if (Array.isArray(node.labels) && node.labels.length > 0) return node.labels.join(', ');
  return `Node ${String(node.identity ?? '')}`;
}

function nodeCategory(node: any) {
  if (Array.isArray(node.labels) && node.labels.length > 0) {
    return String(node.labels[0]);
  }

  const props = node.properties ?? {};
  if (props.type) return String(props.type);
  return 'Default';
}

function nodeColorForCategory(category: string) {
  return COLOR_MAP[category] ?? COLOR_MAP.Default;
}

function pathToGraphData(path: any): GraphData {
  const nodes = new Map<string, GraphNode>();
  const links: LinkObject[] = [];

  for (const segment of path?.segments ?? []) {
    const start = segment.start;
    const end = segment.end;
    const rel = segment.relationship;

    if (!start || !end || !rel) continue;

    const startId = String(start.identity);
    const endId = String(end.identity);

    if (!nodes.has(startId)) {
      const category = nodeCategory(start);
      nodes.set(startId, {
        id: startId,
        label: nodeLabelFromProps(start),
        category,
        color: nodeColorForCategory(category),
      });
    }

    if (!nodes.has(endId)) {
      const category = nodeCategory(end);
      nodes.set(endId, {
        id: endId,
        label: nodeLabelFromProps(end),
        category,
        color: nodeColorForCategory(category),
      });
    }

    links.push({
      source: startId,
      target: endId,
      type: rel.type ?? '',
    });
  }

  return { nodes: Array.from(nodes.values()), links };
}

export function ConstellationModal({ open, onClose }: ConstellationModalProps) {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const graphRef = useRef<ForceGraphMethods<any, any> | undefined>(undefined);

  useEffect(() => {
    if (!open) return;

    setGraphData(null);
    setError(null);
    setLoading(true);

    if (!NEO4J_URI || !NEO4J_USER || !NEO4J_PASSWORD) {
      setError('Missing Neo4j connection settings in Saturn-UI .env');
      setLoading(false);
      return;
    }

    const driver = neo4j.driver(
      NEO4J_URI,
      neo4j.auth.basic(NEO4J_USER, NEO4J_PASSWORD),
      { encrypted: 'ENCRYPTION_OFF' },
    );

    const session = driver.session();
    let cancelled = false;

    session
      .run('MATCH p=()-[]->() RETURN p LIMIT 300')
      .then((result) => {
        if (cancelled) return;

        const data: GraphData = { nodes: [], links: [] };
        const nodeMap = new Map<string, GraphNode>();

        for (const record of result.records) {
          const path = record.get('p');
          if (!path) continue;

          const pathData = pathToGraphData(path);
          for (const node of pathData.nodes) {
            if (!nodeMap.has(String(node.id))) {
              nodeMap.set(String(node.id), node);
            }
          }
          data.links.push(...pathData.links);
        }

        data.nodes = Array.from(nodeMap.values()) as GraphNode[];
        setGraphData(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message ?? 'Unable to fetch Neo4j graph');
        }
      })
      .finally(() => {
        session.close().catch(() => {});
        driver.close().catch(() => {});
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
      session.close().catch(() => {});
      driver.close().catch(() => {});
    };
  }, [open]);

  useEffect(() => {
    if (!graphData) return;
    const timer = window.setTimeout(() => {
      graphRef.current?.zoomToFit(400, 100);
    }, 100);
    return () => window.clearTimeout(timer);
  }, [graphData]);

  if (!open) return null;

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Constellation graph">
      <div className="modal-card">
        <div className="modal-header">
          <h2>Constellation</h2>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close modal">
            ×
          </button>
        </div>

        <div className="modal-body">
          {loading && (
            <div className="modal-message">
              <Loader label="Loading Neo4j graph…" />
            </div>
          )}
          {error && <div className="modal-message modal-error">{error}</div>}
          {!loading && !error && !graphData && (
            <div className="modal-message">No graph data available yet.</div>
          )}
          {graphData && (
            <div className="modal-graph">
              <ForceGraph2D
                ref={graphRef as any}
                graphData={graphData as any}
                nodeId="id"
                linkDirectionalArrowLength={4}
                linkDirectionalArrowRelPos={1}
                linkDirectionalParticles={1}
                linkDirectionalParticleSpeed={0.005}
                nodeRelSize={8}
                autoPauseRedraw={false}
                backgroundColor="#fbfaf7"
                nodeLabel={(node) => `${(node as any).label ?? String(node.id)}`}
                nodeColor={(node) => (node as any).color ?? '#1f2937'}
                nodeCanvasObject={(node, ctx, globalScale) => {
                  const graphNode = node as GraphNode;
                  const label = graphNode.label ?? String(graphNode.id);
                  const fontSize = 10 / globalScale;
                  const radius = 6;
                  const x = node.x ?? 0;
                  const y = node.y ?? 0;

                  ctx.fillStyle = graphNode.color ?? '#1f2937';
                  ctx.beginPath();
                  ctx.arc(x, y, radius, 0, 2 * Math.PI, false);
                  ctx.fill();

                  ctx.font = `${fontSize}px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;
                  ctx.textAlign = 'center';
                  ctx.textBaseline = 'top';
                  ctx.fillStyle = '#111';
                  ctx.fillText(label, x, y + radius + 2 / globalScale);
                }}
                nodePointerAreaPaint={(node, color, ctx) => {
                  const radius = 8;
                  ctx.fillStyle = color;
                  ctx.beginPath();
                  ctx.arc((node.x ?? 0), (node.y ?? 0), radius, 0, 2 * Math.PI, false);
                  ctx.fill();
                }}
                linkLabel={(link) => `${(link as any).type ?? ''}`}
                onNodeClick={(node) => {
                  graphRef.current?.centerAt((node as any).x ?? 0, (node as any).y ?? 0, 400);
                  graphRef.current?.zoom(2, 400);
                }}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
