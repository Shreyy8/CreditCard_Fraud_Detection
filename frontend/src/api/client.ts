/**
 * HTTP client for the FastAPI investigation backend.
 * In Vite, requests go through /api and are proxied to uvicorn.
 */

export const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) || '/api';

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

function formatDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item === 'object' && item?.msg ? item.msg : String(item)))
      .join('; ');
  }
  if (detail && typeof detail === 'object') return JSON.stringify(detail);
  return 'Request failed';
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...(init?.headers || {}),
    },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = formatDetail(body.detail ?? body);
    } catch {
      // keep statusText
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export interface HealthResponse {
  status: string;
  tigergraph: string;
  mcp: string;
  llm: { provider: string; model: string; configured: boolean };
  data_loaded: {
    transactions: number;
    identity: number;
    closed_cases: number;
    case_pack: number;
  };
}

export interface CaseAnswer {
  case_id: string;
  trigger?: Record<string, unknown>;
  case: Record<string, unknown>;
  evidence_requests?: unknown[];
  next_best_actions?: {
    initial?: unknown[];
    final?: unknown[];
    what_changed?: string;
  };
  sar?: Record<string, unknown>;
  stop_reason?: string;
  tool_calls?: number;
  tokens?: number;
  latency_s?: number;
  audit?: unknown[];
  action_decisions?: Record<string, { status?: string }>;
  explanation?: Record<string, unknown>;
  subgraph?: {
    nodes?: unknown[];
    edges?: unknown[];
  };
  [key: string]: unknown;
}

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health');
}

export async function listCaseAnswers(limit = 50): Promise<CaseAnswer[]> {
  const data = await request<{ cases: CaseAnswer[] }>(`/cases?full=true&limit=${limit}`);
  return data.cases || [];
}

export async function getCaseAnswer(caseId: string): Promise<CaseAnswer> {
  return request<CaseAnswer>(`/cases/${encodeURIComponent(caseId)}`);
}

export async function approveAction(caseId: string, actionId: string): Promise<void> {
  await request(`/cases/${encodeURIComponent(caseId)}/actions/${encodeURIComponent(actionId)}/approve`, {
    method: 'POST',
  });
}

export async function rejectAction(caseId: string, actionId: string): Promise<void> {
  await request(`/cases/${encodeURIComponent(caseId)}/actions/${encodeURIComponent(actionId)}/reject`, {
    method: 'POST',
  });
}

export async function executeAction(caseId: string, actionId: string): Promise<void> {
  await request(`/cases/${encodeURIComponent(caseId)}/actions/${encodeURIComponent(actionId)}/execute`, {
    method: 'POST',
  });
}

export async function runInvestigation(caseId: string): Promise<CaseAnswer> {
  return request<CaseAnswer>('/investigations/run', {
    method: 'POST',
    body: JSON.stringify({ case_id: caseId }),
  });
}

export async function runAllInvestigations(): Promise<{
  total: number;
  completed: number;
  failed: number;
  results: Record<string, unknown>;
}> {
  return request('/investigations/run-all', { method: 'POST' });
}

export function streamInvestigation(
  caseId: string,
  onEvent: (payload: Record<string, unknown>) => void,
): () => void {
  const source = new EventSource(`${API_BASE}/investigations/${encodeURIComponent(caseId)}/stream`);
  source.onmessage = (event) => {
    try {
      onEvent(JSON.parse(event.data) as Record<string, unknown>);
    } catch {
      onEvent({ step: event.data });
    }
  };
  source.onerror = () => {
    source.close();
  };
  return () => source.close();
}

export interface CasePackRow {
  case_id: string;
  opened_at?: string;
  trigger_type?: string;
  trigger_text?: string;
  flagged_txn_id?: string;
  card_id?: string;
  customer_id?: string;
  risk_score?: string | number;
  [key: string]: unknown;
}

export interface CaseStatsResponse {
  total_cases: number;
  cases_completed: number;
  verdict_distribution: {
    fraud: number;
    legitimate: number;
    uncertain: number;
  };
  f1_score: number;
  precision: number;
  recall: number;
  policy_compliance_rate: number;
  action_accuracy_rate: number;
  sar_count: number;
  sar_precision: number;
  sar_recall: number;
  pending_approvals_count: number;
  average_latency_s: number;
  average_tool_calls: number;
  average_tokens: number;
  total_exposure_analyzed_usd: number;
  total_fraud_blocked_usd: number;
}

export interface PolicyRuleData {
  id: string;
  name: string;
  section: string;
  condition: string;
  recommendation: string;
  permissible_routes: string[];
  category: string;
  rationale?: string;
  benchmark_cases_cited: string[];
}

export interface PolicyActionData {
  action: string;
  route: string;
  authority: string;
}

export async function listCasePack(): Promise<CasePackRow[]> {
  const data = await request<{ cases: CasePackRow[] }>('/cases/pack');
  return data.cases || [];
}

export async function getCaseStats(): Promise<CaseStatsResponse> {
  return request<CaseStatsResponse>('/cases/stats');
}

export async function getCaseSar(caseId: string): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/cases/${encodeURIComponent(caseId)}/sar`);
}

export async function getCaseEvidence(caseId: string): Promise<{
  evidence: unknown[];
  evidence_requests: unknown[];
}> {
  return request<{ evidence: unknown[]; evidence_requests: unknown[] }>(
    `/cases/${encodeURIComponent(caseId)}/evidence`,
  );
}

export async function getCaseTransactions(caseId: string): Promise<{
  affected_txn_ids: string[];
  exposure_usd: number;
}> {
  return request<{ affected_txn_ids: string[]; exposure_usd: number }>(
    `/cases/${encodeURIComponent(caseId)}/transactions`,
  );
}

export async function getCaseRelatedCases(caseId: string): Promise<{
  similar_prior_cases: string[];
}> {
  return request<{ similar_prior_cases: string[] }>(
    `/cases/${encodeURIComponent(caseId)}/related-cases`,
  );
}

export async function getCaseGraph(caseId: string): Promise<{
  written_to_graph: boolean;
  graph_case_id: string;
  connected_card_ids: string[];
  connected_device_profiles: string[];
}> {
  return request<{
    written_to_graph: boolean;
    graph_case_id: string;
    connected_card_ids: string[];
    connected_device_profiles: string[];
  }>(`/cases/${encodeURIComponent(caseId)}/graph`);
}

export async function getCaseAudit(caseId: string): Promise<{
  case_id: string;
  audit: unknown[];
}> {
  return request<{ case_id: string; audit: unknown[] }>(
    `/cases/${encodeURIComponent(caseId)}/audit`,
  );
}

export async function createEvidenceRequest(
  caseId: string,
  body: {
    evidence_type?: string;
    investigation_step?: number;
    requested_from?: string;
    reason?: string;
  },
): Promise<unknown> {
  return request(`/cases/${encodeURIComponent(caseId)}/evidence-requests`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function submitEvidenceResponse(
  caseId: string,
  body: {
    request_id: string;
    source: string;
    response: Record<string, unknown>;
    received_at?: string;
  },
): Promise<CaseAnswer> {
  return request<CaseAnswer>(`/cases/${encodeURIComponent(caseId)}/evidence-responses`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function getInvestigation(investigationId: string): Promise<CaseAnswer> {
  return request<CaseAnswer>(`/investigations/${encodeURIComponent(investigationId)}`);
}

export async function getPolicyRules(): Promise<PolicyRuleData[]> {
  const data = await request<{ rules: PolicyRuleData[] }>('/policy/rules');
  return data.rules || [];
}

export async function getPolicyActions(): Promise<{
  routes: PolicyActionData[];
  auto_actions: string[];
}> {
  return request<{ routes: PolicyActionData[]; auto_actions: string[] }>('/policy/actions');
}
