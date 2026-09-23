/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export type CaseId =
  | 'HHG-001' | 'HHG-002' | 'HHG-003' | 'HHG-004' | 'HHG-005'
  | 'HHG-006' | 'HHG-007' | 'HHG-008' | 'HHG-009' | 'HHG-010'
  | 'HHG-011' | 'HHG-012' | 'HHG-013' | 'HHG-014' | 'HHG-015'
  | 'HHG-016' | 'HHG-017' | 'HHG-018' | 'HHG-019' | 'HHG-020';

export type TriggerType = 'risk_score' | 'customer_report' | 'analyst_request';

export type Verdict = 'fraud' | 'legitimate' | 'uncertain';

export type CaseStatus = 'open' | 'closed_fraud' | 'closed_legitimate' | 'escalated';

export type Pattern =
  | 'card_testing'
  | 'card_not_present_fraud'
  | 'card_not_present_new_device'
  | 'out_of_region_use'
  | 'account_takeover'
  | 'undocumented'
  | 'none';

export type ActionName =
  | 'ALLOW_TRANSACTION'
  | 'MONITOR_CARD'
  | 'MONITOR_CONNECTED_CARDS'
  | 'WARN_CUSTOMER'
  | 'VERIFY_WITH_CUSTOMER'
  | 'STEP_UP_AUTH'
  | 'GENERATE_REPORT'
  | 'CREATE_CASE'
  | 'ESCALATE_TO_ANALYST'
  | 'CLOSE_NO_FRAUD'
  | 'DECLINE_TRANSACTION'
  | 'BLOCK_CARD'
  | 'BLOCK_ALL_CARDS'
  | 'FILE_REPORT';

export type Route = 'auto' | 'L1' | 'L2';

export type EvidenceSource = 'graph' | 'document' | 'customer' | 'external';

export interface EvidenceItem {
  id: string;
  claim: string;
  source: EvidenceSource;
  ref: string;
  entity_ids: string[];
  counter_evidence?: boolean;
  confidence_impact?: 'high' | 'medium' | 'low';
  timestamp?: string;
  raw_payload?: Record<string, any>;
}

export interface ActionItem {
  id: string;
  action: ActionName;
  route: Route;
  reason: string;
  executed?: boolean;
  approved_by?: string;
  approved_at?: string;
  approval_checksum?: string;
  rejection_reason?: string;
  status?: 'executed' | 'pending_approval' | 'approved' | 'rejected';
}

export interface EvidenceRequest {
  id: string;
  type: 'customer_validation' | 'step_up_auth' | 'analyst_info';
  asked_after_step: number;
  assumed_response: string;
  simulation_rule: string;
  asked_at: string;
  response_status: 'received' | 'pending' | 'timeout';
}

export interface SARRecord {
  file: boolean;
  reason: string;
  narrative: string;
  subjects: string[];
  total_amount_usd: number;
  activity_dates: string[];
}

export interface PriorCase {
  case_id: string;
  opened_at: string;
  closed_at: string;
  outcome: 'confirmed_fraud' | 'cleared';
  pattern: string;
  similarity_score: number;
  shared_elements: string[];
  notes: string;
  actions_taken: string;
  exposure_usd: number;
}

export interface SubgraphNode {
  id: string;
  type: 'customer' | 'card' | 'transaction' | 'device' | 'region' | 'email';
  label: string;
  sublabel?: string;
  details: Record<string, any>;
  highlighted?: boolean;
  isFlagged?: boolean;
  ringMember?: boolean;
  communityId?: number;
  x?: number;
  y?: number;
}

export interface SubgraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  label?: string;
  temporalNext?: boolean;
  highlighted?: boolean;
  ringMember?: boolean;
}

export interface SubgraphData {
  nodes: SubgraphNode[];
  edges: SubgraphEdge[];
}


export interface AffectedTransaction {
  txn_id: string;
  amount_usd: number;
  disguised_amt: number;
  timestamp: string;
  product_cd: string;
  channel: 'online' | 'in_person';
  device_info?: string;
  billing_region?: string;
  status: 'flagged' | 'affected' | 'baseline';
  risk_score?: number;
}

export interface InvestigationStep {
  step_number: number;
  name: string;
  phase: 'trigger' | 'evidence_gather' | 'pattern_detection' | 'initial_assessment' | 'evidence_request' | 'final_policy' | 'writeback';
  timestamp: string;
  status: 'completed' | 'active' | 'pending';
  tool_invoked?: string;
  description: string;
  output_summary: string;
}

export interface BenchmarkCase {
  case_id: CaseId;
  opened_at: string;
  trigger_type: TriggerType;
  trigger_text: string;
  flagged_txn_id: string;
  card_id: string;
  customer_id: string;
  risk_score: number | null;
  case: {
    status: CaseStatus;
    verdict: Verdict;
    fraud_probability: number;
    raw_probability: number;
    calibrated_probability: number;
    pattern: Pattern;
    pattern_description: string;
    affected_txn_ids: string[];
    first_suspicious_txn_id: string;
    connected_card_ids: string[];
    connected_device_profiles: string[];
    exposure_usd: number;
    evidence: EvidenceItem[];
    similar_prior_cases: string[];
    summary: string;
    written_to_graph: boolean;
    graph_case_id: string;
    policy_rules_cited?: string[];
  };
  evidence_requests: EvidenceRequest[];
  next_best_actions: {
    initial: ActionItem[];
    final: ActionItem[];
    what_changed: string;
  };
  sar: SARRecord;
  stop_reason: string;
  tool_calls: number;
  tokens: number;
  latency_s: number;
  // Visual & Inspection helpers
  subgraph: {
    nodes: SubgraphNode[];
    edges: SubgraphEdge[];
  };
  affected_txns_detail: AffectedTransaction[];
  prior_cases_detail: PriorCase[];
  timeline: InvestigationStep[];
  uncertainty: {
    evidence_count: number;
    independent_sources: number;
    has_conflicts: boolean;
    confidence_level: 'High' | 'Medium' | 'Low';
  };
}

export interface AuditLedgerEntry {
  id: string;
  timestamp: string;
  case_id: CaseId;
  action: ActionName;
  route: Route;
  status: 'executed' | 'approved' | 'rejected' | 'pending';
  actor: string;
  checksum: string;
  rule_citation: string;
  notes?: string;
}

export interface PolicyRule {
  id: string;
  name: string;
  section: string;
  trigger_condition: string;
  action_recommendation: string;
  permissible_routes: Route[];
  category: 'intake' | 'customer_response' | 'pattern' | 'coordination' | 'guardrail';
  rationale?: string;
  benchmark_cases_cited: string[];
}

export interface BenchmarkRunStats {
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
  sar_precision: number;
  sar_recall: number;
  average_latency_s: number;
  average_tool_calls: number;
  average_tokens: number;
  total_exposure_analyzed_usd: number;
  total_fraud_blocked_usd: number;
}

