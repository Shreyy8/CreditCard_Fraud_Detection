/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { BenchmarkCase } from '../../types';

export const CASES_11_TO_15: BenchmarkCase[] = [
  {
    case_id: 'HHG-011',
    opened_at: '2016-11-23T09:15:00Z',
    trigger_type: 'risk_score',
    trigger_text: 'Model risk_score alert (0.72) on Card C08221-K1 at TransactionID 3558210',
    flagged_txn_id: '3558210',
    card_id: 'C08221-K1',
    customer_id: 'C08221',
    risk_score: 0.72,
    case: {
      status: 'escalated',
      verdict: 'uncertain',
      fraud_probability: 0.65,
      raw_probability: 0.68,
      calibrated_probability: 0.65,
      pattern: 'card_not_present_fraud',
      pattern_description: '',
      affected_txn_ids: ['3558210'],
      first_suspicious_txn_id: '3558210',
      connected_card_ids: [],
      connected_device_profiles: ['Windows 8.1 | Chrome 53.0'],
      exposure_usd: 840.00,
      evidence: [
        {
          id: 'ev-011-1',
          claim: 'Initial risk score 0.72 on digital electronic authorization ($840.00).',
          source: 'graph',
          ref: 'card_window(C08221-K1, 24h)',
          entity_ids: ['3558210'],
          counter_evidence: false,
          confidence_impact: 'medium',
          timestamp: '2016-11-23T09:15:02Z'
        },
        {
          id: 'ev-011-2',
          claim: 'No cardholder reply received within 24 hours of SMS/email verification dispatch.',
          source: 'customer',
          ref: 'evidence_requests[0]',
          entity_ids: ['C08221'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-24T09:15:00Z'
        },
        {
          id: 'ev-011-3',
          claim: 'Pending authorization exposure ($840.00) exceeds $500 threshold, mandating analyst escalation under Policy R4 and R8.',
          source: 'document',
          ref: 'Fraud Policy v1.0 Rule R4 / R8',
          entity_ids: ['3558210'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-24T09:15:30Z'
        }
      ],
      similar_prior_cases: ['CC-1402', 'CC-2101'],
      summary: 'Alert opened on single-signal risk score (0.72). In accordance with Policy R1, initial inquiry was dispatched. Following a 24-hour verification timeout with no cardholder response, Policy R4 was triggered: pending authorization declined under L1 route, card placed on monitoring, and case escalated to human analyst because exposure ($840.00) exceeds the $500.00 threshold.',
      written_to_graph: true,
      graph_case_id: 'GC-HHG-011'
    },
    evidence_requests: [
      {
        id: 'req-011',
        type: 'customer_validation',
        asked_after_step: 3,
        assumed_response: 'No response received from cardholder within standard 24-hour SLA window (timeout expired).',
        simulation_rule: 'R4 timeout simulation: cardholder unreachable; pending charges protected.',
        asked_at: '2016-11-23T09:16:00Z',
        response_status: 'timeout'
      }
    ],
    next_best_actions: {
      initial: [
        {
          id: 'act-011-init-1',
          action: 'VERIFY_WITH_CUSTOMER',
          route: 'auto',
          reason: 'R1: Single signal risk score requires customer verification before blocking.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-011-init-2',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Verification request dispatched.',
          executed: true,
          status: 'executed'
        }
      ],
      final: [
        {
          id: 'act-011-fin-1',
          action: 'MONITOR_CARD',
          route: 'auto',
          reason: 'R4: No customer response within 24h; monitor card for suspicious velocity.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-011-fin-2',
          action: 'DECLINE_TRANSACTION',
          route: 'L1',
          reason: 'R4: No customer response within 24h; decline pending authorization ($840.00).',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-011-fin-3',
          action: 'ESCALATE_TO_ANALYST',
          route: 'auto',
          reason: 'R4 & R8: No customer response within 24h and exposure ($840.00) > $500.',
          executed: true,
          status: 'executed'
        }
      ],
      what_changed: '24-hour verification timeout expired; transitioned to MONITOR_CARD, DECLINE_TRANSACTION, and ESCALATE_TO_ANALYST under Policy R4.'
    },
    sar: {
      file: false,
      reason: 'Verdict uncertain; pending analyst investigation before SAR determination.',
      narrative: '',
      subjects: [],
      total_amount_usd: 0,
      activity_dates: []
    },
    stop_reason: 'Stopping Rule 3: Information exhaustion; cardholder unreachable. Policy R4 escalation triggered.',
    tool_calls: 5,
    tokens: 3200,
    latency_s: 2.25,
    subgraph: {
      nodes: [
        { id: 'C08221', type: 'customer', label: 'Customer C08221', details: { contact_attempts: 2 } },
        { id: 'C08221-K1', type: 'card', label: 'Card C08221-K1', details: { card1: 18450 } },
        { id: '3558210', type: 'transaction', label: 'Txn 3558210', sublabel: '$840.00 (Pending)', isFlagged: true, details: { amt: 840.00, status: 'pending' } }
      ],
      edges: [
        { id: 'e-1101', source: 'C08221', target: 'C08221-K1', type: 'OWNS', label: 'OWNS' },
        { id: 'e-1102', source: 'C08221-K1', target: '3558210', type: 'MADE', label: 'MADE' }
      ]
    },
    affected_txns_detail: [
      { txn_id: '3558210', amount_usd: 840.00, disguised_amt: 839.994, timestamp: '2016-11-23T09:10:00Z', product_cd: 'C', channel: 'online', status: 'flagged', risk_score: 0.72 }
    ],
    prior_cases_detail: [
      {
        case_id: 'CC-1402',
        opened_at: '2016-09-02T10:00:00Z',
        closed_at: '2016-09-03T11:00:00Z',
        outcome: 'cleared',
        pattern: 'card_not_present_fraud',
        similarity_score: 0.88,
        shared_elements: ['timeout_24h', 'exposure_bracket: $500-1000'],
        notes: 'Cardholder was on remote flight; called back day after to confirm. Cleared cleanly.',
        actions_taken: 'MONITOR_CARD|DECLINE_TRANSACTION|ESCALATE_TO_ANALYST',
        exposure_usd: 750.00
      }
    ],
    timeline: [
      { step_number: 1, name: 'Intake Trigger', phase: 'trigger', timestamp: '2016-11-23T09:15:00Z', status: 'completed', description: 'Risk alert (0.72) on txn 3558210.', output_summary: 'Alert intake.' },
      { step_number: 2, name: 'Evidence Gathering', phase: 'evidence_gather', timestamp: '2016-11-23T09:15:30Z', status: 'completed', tool_invoked: 'card_window', description: 'Single electronic purchase of $840.00 identified.', output_summary: 'Single signal verified.' },
      { step_number: 3, name: 'Initial Assessment', phase: 'initial_assessment', timestamp: '2016-11-23T09:16:00Z', status: 'completed', description: 'Policy R1: customer verification requested.', output_summary: 'VERIFY_WITH_CUSTOMER emitted.' },
      { step_number: 4, name: 'Timeout Watch', phase: 'evidence_request', timestamp: '2016-11-24T09:15:00Z', status: 'completed', description: '24-hour verification SLA expired without cardholder response.', output_summary: 'Timeout expired.' },
      { step_number: 5, name: 'Final Reassessment', phase: 'final_policy', timestamp: '2016-11-24T09:16:00Z', status: 'completed', description: 'Policy R4: emitted MONITOR_CARD, L1 DECLINE_TRANSACTION, and ESCALATE_TO_ANALYST.', output_summary: 'R4 actions emitted.' },
      { step_number: 6, name: 'Graph Writeback', phase: 'writeback', timestamp: '2016-11-24T09:18:00Z', status: 'completed', tool_invoked: 'write_case', description: 'Persisted to graph: GC-HHG-011.', output_summary: 'Memory updated.' }
    ],
    uncertainty: {
      evidence_count: 3,
      independent_sources: 2,
      has_conflicts: false,
      confidence_level: 'Medium'
    }
  },
  {
    case_id: 'HHG-012',
    opened_at: '2016-11-24T12:00:00Z',
    trigger_type: 'customer_report',
    trigger_text: 'Customer report: "Stolen wallet; multiple cards compromised" for Customer C11919',
    flagged_txn_id: '3562400',
    card_id: 'C11919-K1',
    customer_id: 'C11919',
    risk_score: null,
    case: {
      status: 'closed_fraud',
      verdict: 'fraud',
      fraud_probability: 0.98,
      raw_probability: 0.95,
      calibrated_probability: 0.98,
      pattern: 'account_takeover',
      pattern_description: '',
      affected_txn_ids: ['3562400', '3562415', '3562430'],
      first_suspicious_txn_id: '3562400',
      connected_card_ids: ['C11919-K2'],
      connected_device_profiles: [],
      exposure_usd: 3450.00,
      evidence: [
        {
          id: 'ev-012-1',
          claim: 'Customer confirmed physical wallet theft compromising both primary debit card C11919-K1 and secondary credit card C11919-K2.',
          source: 'customer',
          ref: 'customer_report',
          entity_ids: ['C11919', 'C11919-K1', 'C11919-K2'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-24T12:00:05Z'
        },
        {
          id: 'ev-012-2',
          claim: 'Confirmed fraudulent in-person charges active on both cards: C11919-K1 ($1,950.00) and C11919-K2 ($1,500.00).',
          source: 'graph',
          ref: 'card_window(C11919-K1) + card_window(C11919-K2)',
          entity_ids: ['3562400', '3562415', '3562430'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-24T12:01:15Z'
        },
        {
          id: 'ev-012-3',
          claim: 'Policy R10 prerequisite condition strictly satisfied: >= 2 of customer cards show confirmed fraud with compromised credentials.',
          source: 'document',
          ref: 'Fraud Policy v1.0 Rule R10',
          entity_ids: ['C11919-K1', 'C11919-K2'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-24T12:02:00Z'
        }
      ],
      similar_prior_cases: ['CC-1801'],
      summary: 'Confirmed multi-card physical compromise following wallet theft. Fraudulent in-person retail authorizations detected across two distinct cards (C11919-K1 and C11919-K2) owned by Customer C11919. Because >= 2 customer cards show confirmed fraud, Policy R10 guardrail was satisfied, authorizing BLOCK_ALL_CARDS under mandatory L2 managerial approval. Total exposure ($3,450.00) warrants L2 SAR filing.',
      written_to_graph: true,
      graph_case_id: 'GC-HHG-012'
    },
    evidence_requests: [],
    next_best_actions: {
      initial: [
        {
          id: 'act-012-init-1',
          action: 'BLOCK_ALL_CARDS',
          route: 'L2',
          reason: 'R10: Two customer cards (C11919-K1, C11919-K2) show confirmed physical compromise; L2 managerial approval required.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-012-init-2',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Confirmed multi-card fraud incident.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-012-init-3',
          action: 'FILE_REPORT',
          route: 'L2',
          reason: 'Policy 3a: Confirmed fraud with total exposure ($3,450.00) > $1,000 threshold.',
          executed: false,
          status: 'pending_approval'
        }
      ],
      final: [
        {
          id: 'act-012-fin-1',
          action: 'BLOCK_ALL_CARDS',
          route: 'L2',
          reason: 'R10: Two customer cards (C11919-K1, C11919-K2) show confirmed physical compromise; L2 managerial approval required.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-012-fin-2',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Confirmed multi-card fraud incident.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-012-fin-3',
          action: 'FILE_REPORT',
          route: 'L2',
          reason: 'Policy 3a: Confirmed fraud with total exposure ($3,450.00) > $1,000 threshold.',
          executed: false,
          status: 'pending_approval'
        }
      ],
      what_changed: 'nothing'
    },
    sar: {
      file: true,
      reason: 'Multi-card stolen wallet fraud totaling $3,450.00 under Policy R10 and Policy 3a.',
      narrative: 'This Suspicious Activity Report documents unauthorized multi-card exploitation resulting from wallet theft against Customer C11919. On November 24, 2016, unauthorized individuals utilized both Card C11919-K1 and Card C11919-K2 to conduct three card-present transactions totaling $3,450.00 (TransactionIDs 3562400, 3562415, 3562430) at retail electronics and jewelry merchants. The genuine cardholder immediately notified customer service upon discovering the theft. In accordance with Fraud Policy R10, all cards associated with Customer C11919 were placed on immediate administrative block following senior operations review. Total illicit loss is $3,450.00, meeting FinCEN thresholds.',
      subjects: ['C11919', 'C11919-K1', 'C11919-K2', '3562400', '3562415', '3562430'],
      total_amount_usd: 3450.00,
      activity_dates: ['2016-11-24', '2016-11-24']
    },
    stop_reason: 'Stopping Rule 1: High certainty (p=0.98 >= 0.85) corroborated by customer testimony and multi-card graph records.',
    tool_calls: 6,
    tokens: 3950,
    latency_s: 2.95,
    subgraph: {
      nodes: [
        { id: 'C11919', type: 'customer', label: 'Customer C11919', details: { cards: 2 } },
        { id: 'C11919-K1', type: 'card', label: 'Card C11919-K1', details: { type: 'debit' } },
        { id: 'C11919-K2', type: 'card', label: 'Card C11919-K2', details: { type: 'credit' } },
        { id: '3562400', type: 'transaction', label: 'Txn 3562400', sublabel: '$1,950.00', isFlagged: true, details: { amt: 1950.00 } },
        { id: '3562415', type: 'transaction', label: 'Txn 3562415', sublabel: '$850.00', details: { amt: 850.00 } },
        { id: '3562430', type: 'transaction', label: 'Txn 3562430', sublabel: '$650.00', details: { amt: 650.00 } }
      ],
      edges: [
        { id: 'e-1201', source: 'C11919', target: 'C11919-K1', type: 'OWNS', label: 'OWNS' },
        { id: 'e-1202', source: 'C11919', target: 'C11919-K2', type: 'OWNS', label: 'OWNS' },
        { id: 'e-1203', source: 'C11919-K1', target: '3562400', type: 'MADE', label: 'MADE' },
        { id: 'e-1204', source: 'C11919-K2', target: '3562415', type: 'MADE', label: 'MADE' },
        { id: 'e-1205', source: 'C11919-K2', target: '3562430', type: 'MADE', label: 'MADE' }
      ]
    },
    affected_txns_detail: [
      { txn_id: '3562400', amount_usd: 1950.00, disguised_amt: 1949.992, timestamp: '2016-11-24T11:45:00Z', product_cd: 'W', channel: 'in_person', status: 'flagged' },
      { txn_id: '3562415', amount_usd: 850.00, disguised_amt: 850.005, timestamp: '2016-11-24T11:52:00Z', product_cd: 'W', channel: 'in_person', status: 'affected' },
      { txn_id: '3562430', amount_usd: 650.00, disguised_amt: 649.998, timestamp: '2016-11-24T11:58:00Z', product_cd: 'W', channel: 'in_person', status: 'affected' }
    ],
    prior_cases_detail: [
      {
        case_id: 'CC-1801',
        opened_at: '2016-09-20T14:00:00Z',
        closed_at: '2016-09-20T16:00:00Z',
        outcome: 'confirmed_fraud',
        pattern: 'account_takeover',
        similarity_score: 0.95,
        shared_elements: ['multi_card_compromise', 'R10_applied', 'wallet_theft'],
        notes: 'Two cards stolen in gym burglary; R10 BLOCK_ALL_CARDS applied with L2 approval.',
        actions_taken: 'BLOCK_ALL_CARDS|FILE_REPORT',
        exposure_usd: 3100.00
      }
    ],
    timeline: [
      { step_number: 1, name: 'Intake Trigger', phase: 'trigger', timestamp: '2016-11-24T12:00:00Z', status: 'completed', description: 'Stolen wallet customer report received.', output_summary: 'Multi-card dispute intake.' },
      { step_number: 2, name: 'Evidence Gathering', phase: 'evidence_gather', timestamp: '2016-11-24T12:00:30Z', status: 'completed', tool_invoked: 'card_window', description: 'Verified fraudulent authorizations active on C11919-K1 and C11919-K2.', output_summary: 'Confirmed multi-card compromise.' },
      { step_number: 3, name: 'R10 Verification', phase: 'final_policy', timestamp: '2016-11-24T12:01:00Z', status: 'completed', description: 'Verified R10 condition: >= 2 cards confirmed compromised. Emitted BLOCK_ALL_CARDS (L2).', output_summary: 'R10 satisfied; L2 actions routed.' },
      { step_number: 4, name: 'Graph Writeback', phase: 'writeback', timestamp: '2016-11-24T12:03:00Z', status: 'completed', tool_invoked: 'write_case', description: 'Persisted to graph: GC-HHG-012.', output_summary: 'Memory updated.' }
    ],
    uncertainty: {
      evidence_count: 3,
      independent_sources: 2,
      has_conflicts: false,
      confidence_level: 'High'
    }
  },
  {
    case_id: 'HHG-013',
    opened_at: '2016-11-25T14:30:00Z',
    trigger_type: 'customer_report',
    trigger_text: 'Customer dispute: "Unrecognized online apparel purchase $620.00" on Card C07114-K1',
    flagged_txn_id: '3566100',
    card_id: 'C07114-K1',
    customer_id: 'C07114',
    risk_score: null,
    case: {
      status: 'closed_fraud',
      verdict: 'fraud',
      fraud_probability: 0.89,
      raw_probability: 0.82,
      calibrated_probability: 0.89,
      pattern: 'card_not_present_fraud',
      pattern_description: '',
      affected_txn_ids: ['3566100'],
      first_suspicious_txn_id: '3566100',
      connected_card_ids: [],
      connected_device_profiles: ['Windows 10 | Chrome 54.0'],
      exposure_usd: 620.00,
      evidence: [
        {
          id: 'ev-013-1',
          claim: 'Customer explicitly reported transaction 3566100 ($620.00) as unauthorized CNP charge.',
          source: 'customer',
          ref: 'customer_report',
          entity_ids: ['C07114', '3566100'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-25T14:30:05Z'
        },
        {
          id: 'ev-013-2',
          claim: 'Card details leaked via historical third-party merchant gateway breach; no new device or shared ring identified.',
          source: 'graph',
          ref: 'card_window(C07114-K1, 48h)',
          entity_ids: ['3566100'],
          counter_evidence: false,
          confidence_impact: 'medium',
          timestamp: '2016-11-25T14:31:10Z'
        }
      ],
      similar_prior_cases: ['CC-1404', 'CC-1892'],
      summary: 'Isolated Card-Not-Present fraud on Card C07114-K1. Cardholder initiated dispute for $620.00 online clothing charge. Under Policy R2, card was blocked under L1 approval (exposure $620.00 <= $2,500). Because total exposure does not cross the $1,000 threshold and no connected ring was present, SAR filing was not required.',
      written_to_graph: true,
      graph_case_id: 'GC-HHG-013'
    },
    evidence_requests: [],
    next_best_actions: {
      initial: [
        {
          id: 'act-013-init-1',
          action: 'BLOCK_CARD',
          route: 'L1',
          reason: 'R2: Customer denies transaction; exposure ($620.00) <= $2,500 routes to L1 approval.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-013-init-2',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Customer dispute received.',
          executed: true,
          status: 'executed'
        }
      ],
      final: [
        {
          id: 'act-013-fin-1',
          action: 'BLOCK_CARD',
          route: 'L1',
          reason: 'R2: Customer denies transaction; exposure ($620.00) <= $2,500 routes to L1 approval.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-013-fin-2',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Customer dispute received.',
          executed: true,
          status: 'executed'
        }
      ],
      what_changed: 'nothing'
    },
    sar: {
      file: false,
      reason: 'Total exposure ($620.00) < $1,000 and no connected device ring found (Policy 3a).',
      narrative: '',
      subjects: [],
      total_amount_usd: 0,
      activity_dates: []
    },
    stop_reason: 'Stopping Rule 1: High certainty (p=0.89 >= 0.85) corroborated by customer dispute and graph verification.',
    tool_calls: 5,
    tokens: 3150,
    latency_s: 2.10,
    subgraph: {
      nodes: [
        { id: 'C07114', type: 'customer', label: 'Customer C07114', details: { tenure: '12m' } },
        { id: 'C07114-K1', type: 'card', label: 'Card C07114-K1', details: { card1: 15890 } },
        { id: '3566100', type: 'transaction', label: 'Txn 3566100', sublabel: '$620.00 (Disputed)', isFlagged: true, details: { amt: 620.00 } }
      ],
      edges: [
        { id: 'e-1301', source: 'C07114', target: 'C07114-K1', type: 'OWNS', label: 'OWNS' },
        { id: 'e-1302', source: 'C07114-K1', target: '3566100', type: 'MADE', label: 'MADE' }
      ]
    },
    affected_txns_detail: [
      { txn_id: '3566100', amount_usd: 620.00, disguised_amt: 620.002, timestamp: '2016-11-25T14:20:00Z', product_cd: 'C', channel: 'online', status: 'flagged' }
    ],
    prior_cases_detail: [
      {
        case_id: 'CC-1404',
        opened_at: '2016-09-02T12:00:00Z',
        closed_at: '2016-09-02T14:00:00Z',
        outcome: 'confirmed_fraud',
        pattern: 'card_not_present_fraud',
        similarity_score: 0.91,
        shared_elements: ['customer_report_trigger', 'exposure_bracket: $500-1000', 'single_txn'],
        notes: 'Isolated CNP clothing purchase repudiated by cardholder; closed with card block.',
        actions_taken: 'BLOCK_CARD',
        exposure_usd: 580.00
      }
    ],
    timeline: [
      { step_number: 1, name: 'Intake Trigger', phase: 'trigger', timestamp: '2016-11-25T14:30:00Z', status: 'completed', description: 'Customer dispute received for txn 3566100.', output_summary: 'Dispute intake.' },
      { step_number: 2, name: 'Evidence Gathering', phase: 'evidence_gather', timestamp: '2016-11-25T14:30:30Z', status: 'completed', tool_invoked: 'card_window', description: 'Isolated $620 charge confirmed.', output_summary: 'Clean baseline with isolated spike.' },
      { step_number: 3, name: 'Policy Evaluation', phase: 'final_policy', timestamp: '2016-11-25T14:31:00Z', status: 'completed', description: 'Policy R2: L1 BLOCK_CARD emitted; no SAR ($620 < $1,000).', output_summary: 'L1 action routed.' },
      { step_number: 4, name: 'Graph Writeback', phase: 'writeback', timestamp: '2016-11-25T14:32:00Z', status: 'completed', tool_invoked: 'write_case', description: 'Persisted to graph: GC-HHG-013.', output_summary: 'Memory updated.' }
    ],
    uncertainty: {
      evidence_count: 2,
      independent_sources: 2,
      has_conflicts: false,
      confidence_level: 'High'
    }
  },
  {
    case_id: 'HHG-014',
    opened_at: '2016-11-26T16:00:00Z',
    trigger_type: 'analyst_request',
    trigger_text: 'Analyst tip: "Investigate several cards showing fraud from the same unusual device profile (SM-G935F / anonymous proxy)" on Card C12382-K1',
    flagged_txn_id: '3567800',
    card_id: 'C12382-K1',
    customer_id: 'C12382',
    risk_score: null,
    case: {
      status: 'closed_fraud',
      verdict: 'fraud',
      fraud_probability: 0.99,
      raw_probability: 0.97,
      calibrated_probability: 0.99,
      pattern: 'undocumented',
      pattern_description: 'Coordinated syndicate device ring: an unusual Samsung SM-G935F Build/NRD90M mobile device profile operating behind an anonymous proxy (id_23 = IP_PROXY:ANONYMOUS, id_15 = New) linked across four distinct cardholder accounts to execute parallel high-dollar authorizations.',
      affected_txn_ids: ['3567800', '3567812', '3567825', '3567840', '3567855'],
      first_suspicious_txn_id: '3567800',
      connected_card_ids: ['C14209-K2', 'C09114-K1', 'C07867-K3'],
      connected_device_profiles: ['SM-G935F Build/NRD90M | Chrome Mobile | Android 7.0 | IP_PROXY:ANONYMOUS'],
      exposure_usd: 8420.50,
      evidence: [
        {
          id: 'ev-014-1',
          claim: 'TigerGraph GSQL device_neighbors traversal revealed Samsung SM-G935F profile actively utilized across 4 distinct customer accounts.',
          source: 'graph',
          ref: 'device_neighbors(SM-G935F, 72h)',
          entity_ids: ['C12382-K1', 'C14209-K2', 'C09114-K1', 'C07867-K3', 'dev-ring-014'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-26T16:00:15Z'
        },
        {
          id: 'ev-014-2',
          claim: 'All transactions on shared device profile flagged with id_15 = New and id_23 = IP_PROXY:ANONYMOUS (proxy obfuscation).',
          source: 'graph',
          ref: 'discovery/proxy_device_rings.gsql',
          entity_ids: ['dev-ring-014'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-26T16:00:40Z'
        },
        {
          id: 'ev-014-3',
          claim: 'TigerGraph Louvain community detection algorithm identified all 4 cards clustered in high-density abuse community #4.',
          source: 'graph',
          ref: 'communities() [Louvain algorithm]',
          entity_ids: ['C12382-K1', 'C14209-K2', 'C09114-K1', 'C07867-K3'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-26T16:01:10Z'
        },
        {
          id: 'ev-014-4',
          claim: 'Matches undocumented syndicate typology 1 identified in closed benchmark seeds CC-0001, CC-0002, CC-0003.',
          source: 'document',
          ref: 'Similar closed cases CC-0001, CC-0002',
          entity_ids: ['CC-0001', 'CC-0002'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-26T16:01:45Z'
        }
      ],
      similar_prior_cases: ['CC-0001', 'CC-0002', 'CC-0003'],
      summary: 'Primary benchmark syndicate device ring identified. Analyst tip investigated via TigerGraph GSQL graph traversal: an unusual Samsung SM-G935F Build/NRD90M Android device behind an anonymous proxy was actively utilized across four distinct customer cards (C12382-K1, C14209-K2, C09114-K1, C07867-K3). Under Policy R6 and R9, the agent classified the attack as an undocumented device ring, recommended L2 SAR filing on the entire $8,420.50 exposure, issued MONITOR_CONNECTED_CARDS across all member cards, and escalated to senior fraud operations.',
      written_to_graph: true,
      graph_case_id: 'GC-HHG-014'
    },
    evidence_requests: [],
    next_best_actions: {
      initial: [
        {
          id: 'act-014-init-1',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'R6 & R9: Multi-card device ring identified; immediate case creation required.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-014-init-2',
          action: 'MONITOR_CONNECTED_CARDS',
          route: 'auto',
          reason: 'R6: Shared device profile connects C14209-K2, C09114-K1, and C07867-K3; monitor all ring entities.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-014-init-3',
          action: 'BLOCK_CARD',
          route: 'L2',
          reason: 'R2 & R6: Active syndicate ring with total exposure ($8,420.50) > $2,500 requires L2 approval.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-014-init-4',
          action: 'FILE_REPORT',
          route: 'L2',
          reason: 'R6, R9 & Policy 3a: Coordinated device ring exceeding $1,000 requires comprehensive SAR filing.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-014-init-5',
          action: 'ESCALATE_TO_ANALYST',
          route: 'auto',
          reason: 'R9: Undocumented multi-entity fraud ring requires comprehensive financial crimes intelligence review.',
          executed: true,
          status: 'executed'
        }
      ],
      final: [
        {
          id: 'act-014-fin-1',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'R6 & R9: Multi-card device ring identified; immediate case creation required.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-014-fin-2',
          action: 'MONITOR_CONNECTED_CARDS',
          route: 'auto',
          reason: 'R6: Shared device profile connects C14209-K2, C09114-K1, and C07867-K3; monitor all ring entities.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-014-fin-3',
          action: 'BLOCK_CARD',
          route: 'L2',
          reason: 'R2 & R6: Active syndicate ring with total exposure ($8,420.50) > $2,500 requires L2 approval.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-014-fin-4',
          action: 'FILE_REPORT',
          route: 'L2',
          reason: 'R6, R9 & Policy 3a: Coordinated device ring exceeding $1,000 requires comprehensive SAR filing.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-014-fin-5',
          action: 'ESCALATE_TO_ANALYST',
          route: 'auto',
          reason: 'R9: Undocumented multi-entity fraud ring requires comprehensive financial crimes intelligence review.',
          executed: true,
          status: 'executed'
        }
      ],
      what_changed: 'nothing'
    },
    sar: {
      file: true,
      reason: 'Coordinated syndicate device ring connecting 4 customer accounts with total exposure of $8,420.50 under Policy R6, R9, and Policy 3a.',
      narrative: 'This Suspicious Activity Report details a sophisticated organized cyber fraud ring exploiting multiple payment cards through a common hardware device profile and anonymization infrastructure. Between November 24 and November 26, 2016, five fraudulent transactions totaling $8,420.50 (TransactionIDs 3567800, 3567812, 3567825, 3567840, 3567855) were initiated through online merchant portals. TigerGraph graph analytics revealed all authorizations shared an identical device profile: a Samsung SM-G935F running Android 7.0 on Chrome Mobile behind an anonymous proxy service (IP_PROXY:ANONYMOUS). The device was linked to four separate cardholders: C12382-K1, C14209-K2, C09114-K1, and C07867-K3. Graph community detection algorithms clustered these accounts into an active syndication ring. Under Fraud Policy R6 and R9, administrative blocks were recommended and all connected accounts placed on enhanced monitoring. Total exposure of $8,420.50 warrants urgent BSA/FinCEN dissemination.',
      subjects: [
        'C12382-K1', 'C14209-K2', 'C09114-K1', 'C07867-K3',
        'SM-G935F Build/NRD90M', 'IP_PROXY:ANONYMOUS', '3567800', '3567855'
      ],
      total_amount_usd: 8420.50,
      activity_dates: ['2016-11-24', '2016-11-26']
    },
    stop_reason: 'Stopping Rule 1: High certainty boundary (p=0.99 >= 0.85) corroborated by 4 independent graph, community, and historical records.',
    tool_calls: 9,
    tokens: 4950,
    latency_s: 3.85,
    subgraph: {
      nodes: [
        { id: 'C12382-K1', type: 'card', label: 'Card C12382-K1 (Flagged)', isFlagged: true, ringMember: true, communityId: 4, details: { card1: 22374 } },
        { id: 'C14209-K2', type: 'card', label: 'Card C14209-K2', ringMember: true, communityId: 4, details: { card1: 16008 } },
        { id: 'C09114-K1', type: 'card', label: 'Card C09114-K1', ringMember: true, communityId: 4, details: { card1: 17400 } },
        { id: 'C07867-K3', type: 'card', label: 'Card C07867-K3', ringMember: true, communityId: 4, details: { card1: 22006 } },
        { id: 'dev-ring-014', type: 'device', label: 'Samsung SM-G935F (Ring Device)', ringMember: true, highlighted: true, details: { model: 'SM-G935F Build/NRD90M', proxy: 'IP_PROXY:ANONYMOUS', id_15: 'New' } },
        { id: '3567800', type: 'transaction', label: 'Txn 3567800', sublabel: '$1,850.00', isFlagged: true, ringMember: true, details: { amt: 1850.00 } },
        { id: '3567812', type: 'transaction', label: 'Txn 3567812', sublabel: '$1,620.50', ringMember: true, details: { amt: 1620.50 } },
        { id: '3567825', type: 'transaction', label: 'Txn 3567825', sublabel: '$1,750.00', ringMember: true, details: { amt: 1750.00 } },
        { id: '3567840', type: 'transaction', label: 'Txn 3567840', sublabel: '$1,600.00', ringMember: true, details: { amt: 1600.00 } },
        { id: '3567855', type: 'transaction', label: 'Txn 3567855', sublabel: '$1,600.00', ringMember: true, details: { amt: 1600.00 } }
      ],
      edges: [
        { id: 'e-1401', source: 'C12382-K1', target: '3567800', type: 'MADE', label: 'MADE', ringMember: true, highlighted: true },
        { id: 'e-1402', source: 'C14209-K2', target: '3567812', type: 'MADE', label: 'MADE', ringMember: true, highlighted: true },
        { id: 'e-1403', source: 'C09114-K1', target: '3567825', type: 'MADE', label: 'MADE', ringMember: true, highlighted: true },
        { id: 'e-1404', source: 'C07867-K3', target: '3567840', type: 'MADE', label: 'MADE', ringMember: true, highlighted: true },
        { id: 'e-1405', source: 'C12382-K1', target: '3567855', type: 'MADE', label: 'MADE', ringMember: true, highlighted: true },
        { id: 'e-1406', source: '3567800', target: 'dev-ring-014', type: 'FROM_DEVICE', label: 'SHARED DEVICE', ringMember: true, highlighted: true },
        { id: 'e-1407', source: '3567812', target: 'dev-ring-014', type: 'FROM_DEVICE', label: 'SHARED DEVICE', ringMember: true, highlighted: true },
        { id: 'e-1408', source: '3567825', target: 'dev-ring-014', type: 'FROM_DEVICE', label: 'SHARED DEVICE', ringMember: true, highlighted: true },
        { id: 'e-1409', source: '3567840', target: 'dev-ring-014', type: 'FROM_DEVICE', label: 'SHARED DEVICE', ringMember: true, highlighted: true },
        { id: 'e-1410', source: '3567855', target: 'dev-ring-014', type: 'FROM_DEVICE', label: 'SHARED DEVICE', ringMember: true, highlighted: true }
      ]
    },
    affected_txns_detail: [
      { txn_id: '3567800', amount_usd: 1850.00, disguised_amt: 1849.998, timestamp: '2016-11-26T15:10:00Z', product_cd: 'C', channel: 'online', status: 'flagged' },
      { txn_id: '3567812', amount_usd: 1620.50, disguised_amt: 1620.502, timestamp: '2016-11-26T15:22:00Z', product_cd: 'C', channel: 'online', status: 'affected' },
      { txn_id: '3567825', amount_usd: 1750.00, disguised_amt: 1749.995, timestamp: '2016-11-26T15:35:00Z', product_cd: 'C', channel: 'online', status: 'affected' },
      { txn_id: '3567840', amount_usd: 1600.00, disguised_amt: 1600.004, timestamp: '2016-11-26T15:48:00Z', product_cd: 'C', channel: 'online', status: 'affected' },
      { txn_id: '3567855', amount_usd: 1600.00, disguised_amt: 1599.997, timestamp: '2016-11-26T15:58:00Z', product_cd: 'C', channel: 'online', status: 'affected' }
    ],
    prior_cases_detail: [
      {
        case_id: 'CC-0001',
        opened_at: '2016-07-02T10:00:00Z',
        closed_at: '2016-07-03T11:00:00Z',
        outcome: 'confirmed_fraud',
        pattern: 'undocumented',
        similarity_score: 0.98,
        shared_elements: ['SM-G935F', 'IP_PROXY:ANONYMOUS', 'syndicate_ring'],
        notes: 'Device ring 1: Samsung SM-G935F shared by multiple cardholders; long connected card lists.',
        actions_taken: 'CREATE_CASE|BLOCK_CARD|FILE_REPORT|MONITOR_CONNECTED_CARDS',
        exposure_usd: 7200.00
      },
      {
        case_id: 'CC-0002',
        opened_at: '2016-07-03T12:00:00Z',
        closed_at: '2016-07-04T14:00:00Z',
        outcome: 'confirmed_fraud',
        pattern: 'undocumented',
        similarity_score: 0.96,
        shared_elements: ['SM-G935F', 'connected_cards', 'anonymous_proxy'],
        notes: 'Continuation of SM-G935F device ring; multi-card block executed.',
        actions_taken: 'CREATE_CASE|BLOCK_CARD|FILE_REPORT',
        exposure_usd: 6850.00
      }
    ],
    timeline: [
      { step_number: 1, name: 'Intake Trigger', phase: 'trigger', timestamp: '2016-11-26T16:00:00Z', status: 'completed', description: 'Analyst tip intake regarding unusual SM-G935F device profile.', output_summary: 'Analyst request intake.' },
      { step_number: 2, name: 'Graph Traversal', phase: 'evidence_gather', timestamp: '2016-11-26T16:00:20Z', status: 'completed', tool_invoked: 'device_neighbors', description: 'Traversed graph from SM-G935F: connected to 4 distinct cardholders.', output_summary: 'Discovered 4 connected cards.' },
      { step_number: 3, name: 'Community Algorithm', phase: 'pattern_detection', timestamp: '2016-11-26T16:01:00Z', status: 'completed', tool_invoked: 'communities()', description: 'Louvain algorithm confirmed high-density syndication community #4.', output_summary: 'Community #4 verified.' },
      { step_number: 4, name: 'Policy Execution', phase: 'final_policy', timestamp: '2016-11-26T16:02:00Z', status: 'completed', description: 'Applied R6 and R9: emitted MONITOR_CONNECTED_CARDS, L2 BLOCK_CARD, and L2 FILE_REPORT ($8,420.50).', output_summary: 'Ring actions emitted.' },
      { step_number: 5, name: 'Graph Writeback', phase: 'writeback', timestamp: '2016-11-26T16:04:00Z', status: 'completed', tool_invoked: 'write_case', description: 'Persisted to graph: GC-HHG-014.', output_summary: 'Memory updated.' }
    ],
    uncertainty: {
      evidence_count: 4,
      independent_sources: 3,
      has_conflicts: false,
      confidence_level: 'High'
    }
  },
  {
    case_id: 'HHG-015',
    opened_at: '2016-11-27T18:20:00Z',
    trigger_type: 'risk_score',
    trigger_text: 'Model risk_score alert (0.69) for shopping transaction burst on Card C03211-K1',
    flagged_txn_id: '3571200',
    card_id: 'C03211-K1',
    customer_id: 'C03211',
    risk_score: 0.69,
    case: {
      status: 'closed_legitimate',
      verdict: 'legitimate',
      fraud_probability: 0.05,
      raw_probability: 0.10,
      calibrated_probability: 0.05,
      pattern: 'none',
      pattern_description: '',
      affected_txn_ids: [],
      first_suspicious_txn_id: '',
      connected_card_ids: [],
      connected_device_profiles: [],
      exposure_usd: 0.00,
      evidence: [
        {
          id: 'ev-015-1',
          claim: 'Transactions occurred in-person at physical shopping mall stores in cardholder home billing region 299.0.',
          source: 'graph',
          ref: 'card_window(C03211-K1, 4h)',
          entity_ids: ['3571200', '299.0'],
          counter_evidence: true,
          confidence_impact: 'high',
          timestamp: '2016-11-27T18:20:05Z'
        },
        {
          id: 'ev-015-2',
          claim: 'Cardholder confirmed authorized holiday shopping spree via mobile SMS verification prompt.',
          source: 'customer',
          ref: 'evidence_requests[0]',
          entity_ids: ['C03211'],
          counter_evidence: true,
          confidence_impact: 'high',
          timestamp: '2016-11-27T18:24:15Z'
        },
        {
          id: 'ev-015-3',
          claim: 'Timing and merchant categories align with seasonal Black Friday / Cyber Week consumer spending patterns.',
          source: 'document',
          ref: 'Seasonal baseline profile',
          entity_ids: ['C03211-K1'],
          counter_evidence: true,
          confidence_impact: 'medium',
          timestamp: '2016-11-27T18:25:00Z'
        }
      ],
      similar_prior_cases: ['CC-0716', 'CC-0900'],
      summary: 'Alert triggered by rapid transaction velocity during holiday shopping weekend (ProductCD W, in-person). Under Policy R1, verification was requested before taking adverse action. Cardholder promptly confirmed authentic holiday purchases in home region 299.0. Pursuant to Policy R3, alert was resolved as legitimate and closed with 0 exposure and no card interruption.',
      written_to_graph: true,
      graph_case_id: 'GC-HHG-015'
    },
    evidence_requests: [
      {
        id: 'req-015',
        type: 'customer_validation',
        asked_after_step: 3,
        assumed_response: 'Customer confirms they are conducting holiday shopping at the local retail mall and authorized all recent charges.',
        simulation_rule: 'Seasonal retail velocity archetype; customer confirms authorized spending.',
        asked_at: '2016-11-27T18:21:00Z',
        response_status: 'received'
      }
    ],
    next_best_actions: {
      initial: [
        {
          id: 'act-015-init-1',
          action: 'VERIFY_WITH_CUSTOMER',
          route: 'auto',
          reason: 'R1: Moderate risk score on velocity burst requires verification before card block.',
          executed: true,
          status: 'executed'
        }
      ],
      final: [
        {
          id: 'act-015-fin-1',
          action: 'CLOSE_NO_FRAUD',
          route: 'auto',
          reason: 'R3: Cardholder confirmed authorized holiday retail purchases; closed with no fraud.',
          executed: true,
          status: 'executed'
        }
      ],
      what_changed: 'Customer confirmed transactions; recommendation transitioned from VERIFY_WITH_CUSTOMER to CLOSE_NO_FRAUD.'
    },
    sar: {
      file: false,
      reason: 'Legitimate cardholder retail spending confirmed; SAR not applicable.',
      narrative: '',
      subjects: [],
      total_amount_usd: 0,
      activity_dates: []
    },
    stop_reason: 'Stopping Rule 2: Customer verification resolved alert through positive confirmation.',
    tool_calls: 5,
    tokens: 3080,
    latency_s: 2.12,
    subgraph: {
      nodes: [
        { id: 'C03211', type: 'customer', label: 'Customer C03211', details: { region: 299.0 } },
        { id: 'C03211-K1', type: 'card', label: 'Card C03211-K1', details: { card1: 18112 } },
        { id: '3571200', type: 'transaction', label: 'Txn 3571200', sublabel: '$180.00 (Store 1)', isFlagged: true, details: { amt: 180.00 } },
        { id: '3571215', type: 'transaction', label: 'Txn 3571215', sublabel: '$240.00 (Store 2)', details: { amt: 240.00 } }
      ],
      edges: [
        { id: 'e-1501', source: 'C03211', target: 'C03211-K1', type: 'OWNS', label: 'OWNS' },
        { id: 'e-1502', source: 'C03211-K1', target: '3571200', type: 'MADE', label: 'MADE' },
        { id: 'e-1503', source: 'C03211-K1', target: '3571215', type: 'MADE', label: 'MADE' },
        { id: 'e-1504', source: '3571200', target: '3571215', type: 'NEXT', temporalNext: true, label: 'NEXT (15m)' }
      ]
    },
    affected_txns_detail: [
      { txn_id: '3571200', amount_usd: 180.00, disguised_amt: 179.992, timestamp: '2016-11-27T18:10:00Z', product_cd: 'W', channel: 'in_person', status: 'flagged', risk_score: 0.69 }
    ],
    prior_cases_detail: [
      {
        case_id: 'CC-0900',
        opened_at: '2016-08-16T10:00:00Z',
        closed_at: '2016-08-16T11:15:00Z',
        outcome: 'cleared',
        pattern: 'none',
        similarity_score: 0.93,
        shared_elements: ['holiday_shopping', 'home_region_299', 'channel: in_person'],
        notes: 'Retail mall spending spree verified by cardholder; closed with no fraud.',
        actions_taken: 'VERIFY_WITH_CUSTOMER|CLOSE_NO_FRAUD',
        exposure_usd: 0.00
      }
    ],
    timeline: [
      { step_number: 1, name: 'Intake Trigger', phase: 'trigger', timestamp: '2016-11-27T18:20:00Z', status: 'completed', description: 'Risk alert (0.69) for retail burst.', output_summary: 'Retail burst intake.' },
      { step_number: 2, name: 'Evidence Gathering', phase: 'evidence_gather', timestamp: '2016-11-27T18:20:20Z', status: 'completed', tool_invoked: 'card_window', description: 'All charges in home region 299.0 during shopping hours.', output_summary: 'Home region retail verified.' },
      { step_number: 3, name: 'Initial Assessment', phase: 'initial_assessment', timestamp: '2016-11-27T18:20:50Z', status: 'completed', description: 'Policy R1: verification sent.', output_summary: 'VERIFY_WITH_CUSTOMER emitted.' },
      { step_number: 4, name: 'Evidence Request', phase: 'evidence_request', timestamp: '2016-11-27T18:21:00Z', status: 'completed', description: 'Cardholder confirmed authorized shopping.', output_summary: 'Customer confirmed.' },
      { step_number: 5, name: 'Final Reassessment', phase: 'final_policy', timestamp: '2016-11-27T18:24:30Z', status: 'completed', description: 'Policy R3: CLOSE_NO_FRAUD emitted.', output_summary: 'Closed as legitimate.' },
      { step_number: 6, name: 'Graph Writeback', phase: 'writeback', timestamp: '2016-11-27T18:26:00Z', status: 'completed', tool_invoked: 'write_case', description: 'Persisted to graph: GC-HHG-015.', output_summary: 'Memory updated.' }
    ],
    uncertainty: {
      evidence_count: 3,
      independent_sources: 2,
      has_conflicts: false,
      confidence_level: 'High'
    }
  }
];
