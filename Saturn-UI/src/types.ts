export interface SearchPayload {
  type: 'community' | 'chunk';
  text: string;
  community_id?: number;
  level?: string;
  chunk_index?: number;
  source?: string;
  page_number?: number;
}

export interface SearchHit {
  id: string;
  score: number;
  payload: SearchPayload;
}

export interface QueryResponse {
  tool_response: string[];
  answer: string;
}

export interface NodeColors {
  fill: string;
  border: string;
  text: string;
}

export interface GraphNode {
  id: string;
  label: string;
  displayTitle: string;
  text: string;
  score: number;
  communityKey: string;
  communityLabel: string;
  communityId?: number;
  communityLevel?: string;
  communitySize: number;
  distanceFromQuery: number;
  source?: string;
  pageNumber?: number;
  chunkIndex?: number;
  type: string;
  color: string;
  colors: NodeColors;
  val: number;
  isQuery?: boolean;
  x?: number;
  y?: number;
  fx?: number;
  fy?: number;
}

export interface GraphLink {
  source: string;
  target: string;
  weight: number;
  score: number;
  isQueryLink?: boolean;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}
