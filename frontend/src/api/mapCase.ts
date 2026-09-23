import { getCaseById } from '../data/cases';
import {
  ActionItem,
  ActionName,
  AffectedTransaction,
  BenchmarkCase,
  CaseId,
  CaseStatus,
  EvidenceItem,
  EvidenceRequest,
  Pattern,
  PriorCase,
  Route,
  TriggerType,
  Verdict,
} from '../types';
import type { CaseAnswer } from './client';

const ACTION_NAMES = new Set<ActionName>([
  'ALLOW_TRANSACTION',
  'MONITOR_CARD',
  'MONITOR_CONNECTED_CARDS',
  'WARN_CUSTOMER',
  'VERIFY_WITH_CUSTOMER',
  'STEP_UP_AUTH',
  'GENERATE_REPORT',
  'CREATE_CASE',
  'ESCALATE_TO_ANALYST',
  'CLOSE_NO_FRAUD',
  'DECLINE_TRANSACTION',
  'BLOCK_CARD',
  'BLOCK_ALL_CARDS',
  'FILE_REPORT',
]);

function asString(value: unknown, fallback = ''): string {
  return value == null ? fallback : String(value);
}

function asNumber(value: unknown, fallback = 0): number {
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function asBool(value: unknown, fallback = false): boolean {
  return typeof value === 'boolean' ? value : fallback;
}

function triggerType(value: unknown): TriggerType {
  if (value === 'customer_report' || value === 'analyst_request' || value === 'risk_score') {
    return value;
  }
  return 'risk_score';
}

function verdictOf(value: unknown): Verdict {
  if (value === 'fraud' || value === 'legitimate' || value === 'uncertain') return value;
  return 'uncertain';
}

function statusOf(value: unknown): CaseStatus {
  if (
    value === 'open' ||
    value === 'closed_fraud' ||
    value === 'closed_legitimate' ||
    value === 'escalated'
  ) {
    return value;
  }
  return 'open';
}

function patternOf(value: unknown): Pattern {
  const allowed: Pattern[] = [
    'card_testing',
    'card_not_present_fraud',
    'card_not_present_new_device',
    'out_of_region_use',
    'account_takeover',
    'undocumented',
    'none',
  ];
  return allowed.includes(value as Pattern) ? (value as Pattern) : 'none';
}

function routeOf(value: unknown): Route {
  if (value === 'auto' || value === 'L1' || value === 'L2') return value;
  return 'auto';
}

function actionNameOf(value: unknown): ActionName {
  const name = asString(value) as ActionName;
  return ACTION_NAMES.has(name) ? name : 'CREATE_CASE';
}

function mapEvidence(items: unknown[], caseId: string): EvidenceItem[] {
  if (!Array.isArray(items)) return [];
  return items.map((raw, index) => {
    const item = (raw && typeof raw === 'object' ? raw : {}) as Record<string, unknown>;
    const source = item.source;
    return {
      id: asString(item.id, `ev-${caseId}-${index}`),
      claim: asString(item.claim),
      source:
        source === 'graph' || source === 'document' || source === 'customer' || source === 'external'
          ? source
          : 'graph',
      ref: asString(item.ref),
      entity_ids: Array.isArray(item.entity_ids) ? item.entity_ids.map((id) => asString(id)) : [],
      counter_evidence: asBool(item.counter_evidence),
      confidence_impact:
        item.confidence_impact === 'high' ||
        item.confidence_impact === 'medium' ||
        item.confidence_impact === 'low'
          ? item.confidence_impact
          : 'medium',
      timestamp: asString(item.timestamp) || undefined,
    };
  });
}

function mapEvidenceRequests(items: unknown[]): EvidenceRequest[] {
  if (!Array.isArray(items)) return [];
  return items.map((raw, index) => {
    const item = (raw && typeof raw === 'object' ? raw : {}) as Record<string, unknown>;
    const type = item.type;
    const status = asString(item.status, asString(item.response_status, 'pending'));
    return {
      id: asString(item.id || item.request_id, `req-${index}`),
      type:
        type === 'customer_validation' || type === 'step_up_auth' || type === 'analyst_info'
          ? type
          : 'analyst_info',
      asked_after_step: asNumber(item.asked_after_step, 0),
      assumed_response: asString(item.assumed_response),
      simulation_rule: asString(item.simulation_rule || item.reason),
      asked_at: asString(item.asked_at || item.created_at),
      response_status:
        status === 'received' || status === 'fulfilled' || status === 'complete'
          ? 'received'
          : status === 'timeout'
            ? 'timeout'
            : 'pending',
    };
  });
}

function mapActions(
  items: unknown[],
  decisions: Record<string, { status?: string }> | undefined,
): ActionItem[] {
  if (!Array.isArray(items)) return [];
  return items.map((raw) => {
    const item = (raw && typeof raw === 'object' ? raw : {}) as Record<string, unknown>;
    const action = actionNameOf(item.action);
    const route = routeOf(item.route);
    const decision = decisions?.[action];
    let status: ActionItem['status'];
    if (decision?.status === 'approved' || decision?.status === 'rejected' || decision?.status === 'executed') {
      status = decision.status;
    } else if (item.status === 'pending_approval' || item.status === 'approved' || item.status === 'rejected' || item.status === 'executed') {
      status = item.status;
    } else if (route === 'auto') {
      status = 'executed';
    } else {
      status = 'pending_approval';
    }
    return {
      id: asString(item.id, action),
      action,
      route,
      reason: asString(item.reason),
      executed: status === 'executed' || asBool(item.executed, route === 'auto'),
      status,
    };
  });
}

function mapTransactions(ids: string[], fallback?: AffectedTransaction[]): AffectedTransaction[] {
  if (fallback?.length) {
    const byId = new Map(fallback.map((txn) => [txn.txn_id, txn]));
    const ordered = ids.map((id) => byId.get(id)).filter(Boolean) as AffectedTransaction[];
    if (ordered.length) return ordered;
    return fallback;
  }
  return ids.map((txn_id, index) => ({
    txn_id,
    amount_usd: 0,
    disguised_amt: 0,
    timestamp: '',
    product_cd: '',
    channel: 'online' as const,
    status: index === 0 ? ('flagged' as const) : ('affected' as const),
  }));
}

function confidenceFrom(evidenceCount: number, probability: number): 'High' | 'Medium' | 'Low' {
  if (evidenceCount >= 3 && (probability >= 0.7 || probability <= 0.2)) return 'High';
  if (evidenceCount >= 2) return 'Medium';
  return 'Low';
}

export function mapCaseAnswer(raw: CaseAnswer): BenchmarkCase {
  const fallback = getCaseById(raw.case_id);
  const trigger = (raw.trigger && typeof raw.trigger === 'object' ? raw.trigger : {}) as Record<string, unknown>;
  const record = (raw.case && typeof raw.case === 'object' ? raw.case : {}) as Record<string, unknown>;
  const nba = raw.next_best_actions || {};
  const decisions = raw.action_decisions;
  const evidence = mapEvidence((record.evidence as unknown[]) || [], raw.case_id);
  const affectedIds = Array.isArray(record.affected_txn_ids)
    ? (record.affected_txn_ids as unknown[]).map((id) => asString(id))
    : fallback?.case.affected_txn_ids || [];
  const probability = asNumber(record.fraud_probability, fallback?.case.fraud_probability ?? 0);
  const sources = new Set(evidence.map((item) => item.source));

  return {
    case_id: raw.case_id as CaseId,
    opened_at: asString(raw.opened_at || trigger.opened_at, fallback?.opened_at || ''),
    trigger_type: triggerType(trigger.type || trigger.trigger_type || fallback?.trigger_type),
    trigger_text: asString(trigger.text || trigger.trigger_text, fallback?.trigger_text || ''),
    flagged_txn_id: asString(
      trigger.transaction_id || trigger.flagged_txn_id,
      fallback?.flagged_txn_id || '',
    ),
    card_id: asString(trigger.card_id, fallback?.card_id || ''),
    customer_id: asString(trigger.customer_id, fallback?.customer_id || ''),
    risk_score:
      trigger.risk_score == null || trigger.risk_score === ''
        ? fallback?.risk_score ?? null
        : asNumber(trigger.risk_score, fallback?.risk_score ?? 0),
    case: {
      status: statusOf(record.status),
      verdict: verdictOf(record.verdict),
      fraud_probability: probability,
      raw_probability: asNumber(record.raw_probability, probability),
      calibrated_probability: asNumber(record.calibrated_probability, probability),
      pattern: patternOf(record.pattern),
      pattern_description: asString(record.pattern_description, fallback?.case.pattern_description || ''),
      affected_txn_ids: affectedIds,
      first_suspicious_txn_id: asString(
        record.first_suspicious_txn_id,
        fallback?.case.first_suspicious_txn_id || affectedIds[0] || '',
      ),
      connected_card_ids: Array.isArray(record.connected_card_ids)
        ? (record.connected_card_ids as unknown[]).map((id) => asString(id))
        : fallback?.case.connected_card_ids || [],
      connected_device_profiles: Array.isArray(record.connected_device_profiles)
        ? (record.connected_device_profiles as unknown[]).map((id) => asString(id))
        : fallback?.case.connected_device_profiles || [],
      exposure_usd: asNumber(record.exposure_usd, fallback?.case.exposure_usd ?? 0),
      evidence: evidence.length ? evidence : fallback?.case.evidence || [],
      similar_prior_cases: Array.isArray(record.similar_prior_cases)
        ? (record.similar_prior_cases as unknown[]).map((id) => asString(id))
        : fallback?.case.similar_prior_cases || [],
      summary: asString(record.summary, fallback?.case.summary || ''),
      written_to_graph: asBool(record.written_to_graph, fallback?.case.written_to_graph ?? false),
      graph_case_id: asString(record.graph_case_id, fallback?.case.graph_case_id || ''),
      policy_rules_cited: Array.isArray(record.policy_rules_cited)
        ? (record.policy_rules_cited as unknown[]).map((id) => asString(id))
        : fallback?.case.policy_rules_cited,
    },
    evidence_requests: mapEvidenceRequests(raw.evidence_requests || []).length
      ? mapEvidenceRequests(raw.evidence_requests || [])
      : fallback?.evidence_requests || [],
    next_best_actions: {
      initial: mapActions(nba.initial || [], decisions),
      final: mapActions(nba.final || [], decisions),
      what_changed: asString(nba.what_changed, fallback?.next_best_actions.what_changed || 'nothing'),
    },
    sar: {
      file: asBool(raw.sar?.file, fallback?.sar.file ?? false),
      reason: asString(raw.sar?.reason, fallback?.sar.reason || ''),
      narrative: asString(raw.sar?.narrative, fallback?.sar.narrative || ''),
      subjects: Array.isArray(raw.sar?.subjects)
        ? (raw.sar?.subjects as unknown[]).map((id) => asString(id))
        : fallback?.sar.subjects || [],
      total_amount_usd: asNumber(raw.sar?.total_amount_usd, fallback?.sar.total_amount_usd ?? 0),
      activity_dates: Array.isArray(raw.sar?.activity_dates)
        ? (raw.sar?.activity_dates as unknown[]).map((id) => asString(id))
        : fallback?.sar.activity_dates || [],
    },
    stop_reason: asString(raw.stop_reason, fallback?.stop_reason || ''),
    tool_calls: asNumber(raw.tool_calls, fallback?.tool_calls ?? 0),
    tokens: asNumber(raw.tokens, fallback?.tokens ?? 0),
    latency_s: asNumber(raw.latency_s, fallback?.latency_s ?? 0),
    subgraph: fallback?.subgraph || { nodes: [], edges: [] },
    affected_txns_detail: mapTransactions(affectedIds, fallback?.affected_txns_detail),
    prior_cases_detail: (fallback?.prior_cases_detail || []) as PriorCase[],
    timeline: fallback?.timeline || [],
    uncertainty: fallback?.uncertainty || {
      evidence_count: evidence.length,
      independent_sources: sources.size,
      has_conflicts: false,
      confidence_level: confidenceFrom(evidence.length, probability),
    },
  };
}

export function mergeLiveCases(live: CaseAnswer[]): BenchmarkCase[] {
  return live.map(mapCaseAnswer);
}
