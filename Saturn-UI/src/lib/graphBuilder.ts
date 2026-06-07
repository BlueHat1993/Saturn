import type { GraphData, GraphLink, GraphNode, NodeColors, SearchHit } from '../types';

const MIN_RADIUS = 90;
const MAX_RADIUS = 340;
const RESULT_NODE_VAL = 16;
const QUERY_NODE_VAL = 20;

const LEVEL_COLORS: Record<string, NodeColors> = {
  low: { fill: '#d9ead3', border: '#6aa84f', text: '#274e13' },
  high: { fill: '#cfe2f3', border: '#6fa8dc', text: '#0b5394' },
  root: { fill: '#fce5cd', border: '#e69138', text: '#7f4f00' },
};

const DEFAULT_COLORS: NodeColors = {
  fill: '#efefef',
  border: '#9aa0a6',
  text: '#3c4043',
};

const QUERY_COLORS: NodeColors = {
  fill: '#f9e4c8',
  border: '#b8860b',
  text: '#5c4a1a',
};

function truncate(text: string, max = 40): string {
  const normalized = text.replace(/\s+/g, ' ').trim();
  if (normalized.length <= max) return normalized;
  return `${normalized.slice(0, max - 1)}…`;
}

function colorsForLevel(level?: string): NodeColors {
  if (level && level in LEVEL_COLORS) return LEVEL_COLORS[level];
  return DEFAULT_COLORS;
}

function communityKeyFromPayload(payload: SearchHit['payload']): string {
  if (payload.community_id != null) {
    return `community-${payload.community_id}`;
  }
  if (payload.type === 'chunk' && payload.source) {
    return `source-${payload.source}`;
  }
  return `type-${payload.type}`;
}

function buildDisplayTitle(payload: SearchHit['payload']): string {
  if (payload.community_id != null) {
    const level = payload.level ?? 'unknown';
    return `C-${payload.community_id} · ${level}`;
  }
  if (payload.type === 'chunk') {
    const page = payload.page_number != null ? ` p.${payload.page_number}` : '';
    return `Chunk${page}`;
  }
  return payload.type;
}

function buildSubtitle(payload: SearchHit['payload']): string {
  return truncate(payload.text ?? '', 44);
}

function parseToolResponseEntry(raw: string): SearchHit[] {
  try {
    const parsed = JSON.parse(raw) as SearchHit[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function parseSearchHits(toolResponse: string[]): SearchHit[] {
  const seen = new Set<string>();
  const hits: SearchHit[] = [];

  for (const entry of toolResponse) {
    for (const hit of parseToolResponseEntry(entry)) {
      if (!hit?.id || seen.has(String(hit.id))) continue;
      seen.add(String(hit.id));
      hits.push(hit);
    }
  }

  return hits.sort((a, b) => b.score - a.score);
}

function countCommunitySizes(hits: SearchHit[]): Map<string, number> {
  const sizes = new Map<string, number>();
  for (const hit of hits) {
    const key = communityKeyFromPayload(hit.payload);
    sizes.set(key, (sizes.get(key) ?? 0) + 1);
  }
  return sizes;
}

/** Lower relevance (score) → farther from the query at the center. */
function relevanceToRadius(score: number): number {
  const clamped = Math.max(0, Math.min(1, score));
  return MAX_RADIUS - clamped * (MAX_RADIUS - MIN_RADIUS);
}

function buildQueryNode(query: string): GraphNode {
  const text = query.trim() || 'Query';
  return {
    id: '__query__',
    label: text,
    displayTitle: 'Query',
    text,
    score: 1,
    communityKey: 'query',
    communityLabel: 'Query',
    communitySize: 0,
    distanceFromQuery: 0,
    type: 'query',
    color: QUERY_COLORS.border,
    colors: QUERY_COLORS,
    val: QUERY_NODE_VAL,
    isQuery: true,
    x: 0,
    y: 0,
    fx: 0,
    fy: 0,
  };
}

function buildQueryLinks(queryNode: GraphNode, resultNodes: GraphNode[]): GraphLink[] {
  return resultNodes.map((node) => ({
    source: queryNode.id,
    target: node.id,
    weight: 1,
    score: node.score,
    isQueryLink: true,
  }));
}

export function buildGraphFromToolResponse(
  toolResponse: string[],
  query: string,
): GraphData {
  const hits = parseSearchHits(toolResponse);
  if (hits.length === 0) {
    return { nodes: [], links: [] };
  }

  const communitySizes = countCommunitySizes(hits);
  const count = hits.length;

  const nodes: GraphNode[] = hits.map((hit, index) => {
    const payload = hit.payload;
    const communityKey = communityKeyFromPayload(payload);
    const communitySize = communitySizes.get(communityKey) ?? 1;
    const level = payload.level;
    const colors = colorsForLevel(level);
    const radius = relevanceToRadius(hit.score);
    const angle = -Math.PI / 2 + (2 * Math.PI * index) / count;
    const x = radius * Math.cos(angle);
    const y = radius * Math.sin(angle);
    const title = buildDisplayTitle(payload);
    const subtitle = buildSubtitle(payload);

    return {
      id: String(hit.id),
      label: `${title} — ${subtitle}`,
      displayTitle: title,
      text: payload.text ?? '',
      score: hit.score,
      communityKey,
      communityLabel: title,
      communityId: payload.community_id,
      communityLevel: level,
      communitySize,
      distanceFromQuery: radius,
      source: payload.source,
      pageNumber: payload.page_number,
      chunkIndex: payload.chunk_index,
      type: payload.type ?? 'unknown',
      color: colors.border,
      colors,
      val: RESULT_NODE_VAL + communitySize * 1.5,
      x,
      y,
      fx: x,
      fy: y,
    };
  });

  const queryNode = buildQueryNode(query);
  const allNodes = [queryNode, ...nodes];

  return {
    nodes: allNodes,
    links: buildQueryLinks(queryNode, nodes),
  };
}

export const COMMUNITY_LEVEL_LEGEND = [
  { level: 'low', label: 'low', colors: LEVEL_COLORS.low },
  { level: 'high', label: 'high', colors: LEVEL_COLORS.high },
  { level: 'root', label: 'root', colors: LEVEL_COLORS.root },
] as const;
