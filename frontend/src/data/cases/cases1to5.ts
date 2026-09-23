/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { BenchmarkCase } from '../../types';

export const CASES_1_TO_5: BenchmarkCase[] = [
  {
    case_id: 'HHG-001',
    opened_at: '2016-11-12T08:14:00Z',
    trigger_type: 'risk_score',
    trigger_text: 'Model risk_score alert (0.62) on Card C12382-K1 at TransactionID 3514030',
    flagged_txn_id: '3514030',
    card_id: 'C12382-K1',
    customer_id: 'C12382',
    risk_score: 0.62,
    case: {
      status: 'closed_fraud',
      verdict: 'fraud',
      fraud_probability: 0.88,
      raw_probability: 0.81,
      calibrated_probability: 0.88,
      pattern: 'card_not_present_fraud',
      pattern_description: '',
      affected_txn_ids: ['3514030', '3514032', '3514041'],
      first_suspicious_txn_id: '3514030',
      connected_card_ids: [],
      connected_device_profiles: ['Windows 10 | Chrome 54.0 | 1920x1080'],
      exposure_usd: 482.00,
      evidence: [
        {
          id: 'ev-001-1',
          claim: 'Initial risk score 0.62 represents an isolated single signal on Card C12382-K1 without baseline deviation.',
          source: 'graph',
          ref: 'card_window(C12382-K1, 24h)',
          entity_ids: ['3514030', 'C12382-K1'],
          counter_evidence: false,
          confidence_impact: 'medium',
          timestamp: '2016-11-12T08:14:02Z'
        },
        {
          id: 'ev-001-2',
          claim: 'Customer explicitly denied authorization during simulated customer verification inquiry.',
          source: 'customer',
          ref: 'evidence_requests[0]',
          entity_ids: ['C12382', '3514030'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-12T08:22:15Z'
        },
        {
          id: 'ev-001-3',
          claim: 'Two additional unauthorized digital charges ($128.50, $210.00) detected in the same 45-minute online corridor.',
          source: 'graph',
          ref: 'card_window(C12382-K1, 1h)',
          entity_ids: ['3514032', '3514041'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-12T08:25:30Z'
        }
      ],
      similar_prior_cases: ['CC-2649', 'CC-1892'],
      summary: 'Alert opened on isolated model risk score (0.62). Per Fraud Policy R1, initial verification was requested before blocking. Cardholder denied authorizing transaction 3514030, uncovering two subsequent digital downloads totaling $482.00. Per R2, card was blocked under L1 approval route and case closed as confirmed fraud without SAR requirement (exposure < $1,000).',
      written_to_graph: true,
      graph_case_id: 'GC-HHG-001'
    },
    evidence_requests: [
      {
        id: 'req-001',
        type: 'customer_validation',
        asked_after_step: 4,
        assumed_response: 'Customer confirms they did not authorize the $143.50 purchase at TransactionID 3514030 and card is in their physical possession.',
        simulation_rule: 'R1-compliant verification sent; assume customer repudiation given suspicious browser signature and subsequent transaction burst.',
        asked_at: '2016-11-12T08:16:00Z',
        response_status: 'received'
      }
    ],
    next_best_actions: {
      initial: [
        {
          id: 'act-001-init-1',
          action: 'VERIFY_WITH_CUSTOMER',
          route: 'auto',
          reason: 'R1: Case rests on a single signal (risk_score = 0.62 < 0.70); verification required before any block.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-001-init-2',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Evidence request initiated and probability = 0.45 >= 0.30 threshold.',
          executed: true,
          status: 'executed'
        }
      ],
      final: [
        {
          id: 'act-001-fin-1',
          action: 'BLOCK_CARD',
          route: 'L1',
          reason: 'R2: Customer denies authorizing charge; exposure ($482.00) <= $2,500 routes to L1 approval.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-001-fin-2',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Confirmed fraud with customer repudiation.',
          executed: true,
          status: 'executed'
        }
      ],
      what_changed: 'Initial recommendation of verification transitioned to BLOCK_CARD under R2 after customer repudiated transaction 3514030.'
    },
    sar: {
      file: false,
      reason: 'Total exposure ($482.00) does not meet $1,000 threshold and no connected card ring or undocumented coordination was found (Policy 3a).',
      narrative: '',
      subjects: [],
      total_amount_usd: 0,
      activity_dates: []
    },
    stop_reason: 'Stopping Rule 2: Customer verification response confirmed repudiation, resolving hypothesis with direct testimony.',
    tool_calls: 7,
    tokens: 4210,
    latency_s: 3.42,
    subgraph: {
      nodes: [
        { id: 'C12382', type: 'customer', label: 'Customer C12382', details: { tenure_months: 28, status: 'active' } },
        { id: 'C12382-K1', type: 'card', label: 'Card C12382-K1', details: { brand: 'Visa', type: 'debit', card1: 22374 } },
        { id: '3514030', type: 'transaction', label: 'Txn 3514030', sublabel: '$143.50 (Flagged)', isFlagged: true, details: { amt: 143.50, channel: 'online', risk: 0.62 } },
        { id: '3514032', type: 'transaction', label: 'Txn 3514032', sublabel: '$128.50', details: { amt: 128.50, channel: 'online' } },
        { id: '3514041', type: 'transaction', label: 'Txn 3514041', sublabel: '$210.00', details: { amt: 210.00, channel: 'online' } },
        { id: 'dev-001', type: 'device', label: 'Win10 / Chrome 54', details: { id_30: 'Windows 10', id_31: 'Chrome 54.0', id_15: 'Found' } }
      ],
      edges: [
        { id: 'e-1', source: 'C12382', target: 'C12382-K1', type: 'OWNS', label: 'OWNS' },
        { id: 'e-2', source: 'C12382-K1', target: '3514030', type: 'MADE', label: 'MADE' },
        { id: 'e-3', source: 'C12382-K1', target: '3514032', type: 'MADE', label: 'MADE' },
        { id: 'e-4', source: 'C12382-K1', target: '3514041', type: 'MADE', label: 'MADE' },
        { id: 'e-5', source: '3514030', target: '3514032', type: 'NEXT', temporalNext: true, label: 'NEXT (14m)' },
        { id: 'e-6', source: '3514032', target: '3514041', type: 'NEXT', temporalNext: true, label: 'NEXT (22m)' },
        { id: 'e-7', source: '3514030', target: 'dev-001', type: 'FROM_DEVICE', label: 'FROM_DEVICE' }
      ]
    },
    affected_txns_detail: [
      { txn_id: '3514030', amount_usd: 143.50, disguised_amt: 143.502, timestamp: '2016-11-12T08:12:00Z', product_cd: 'C', channel: 'online', status: 'flagged', risk_score: 0.62 },
      { txn_id: '3514032', amount_usd: 128.50, disguised_amt: 128.498, timestamp: '2016-11-12T08:26:00Z', product_cd: 'C', channel: 'online', status: 'affected' },
      { txn_id: '3514041', amount_usd: 210.00, disguised_amt: 210.001, timestamp: '2016-11-12T08:48:00Z', product_cd: 'C', channel: 'online', status: 'affected' }
    ],
    prior_cases_detail: [
      {
        case_id: 'CC-2649',
        opened_at: '2016-09-14T11:20:00Z',
        closed_at: '2016-09-14T14:40:00Z',
        outcome: 'confirmed_fraud',
        pattern: 'card_not_present_fraud',
        similarity_score: 0.84,
        shared_elements: ['card1: 22374', 'ProductCD: C', 'single_signal_trigger'],
        notes: 'Cardholder denied digital download spike; rapid containment prevented merchant loss.',
        actions_taken: 'VERIFY_WITH_CUSTOMER|BLOCK_CARD',
        exposure_usd: 395.00
      },
      {
        case_id: 'CC-1892',
        opened_at: '2016-08-04T09:12:00Z',
        closed_at: '2016-08-04T12:00:00Z',
        outcome: 'confirmed_fraud',
        pattern: 'card_not_present_fraud',
        similarity_score: 0.76,
        shared_elements: ['ProductCD: C', 'amount_bracket: $100-250'],
        notes: 'CNP burst following compromised online checkout credentials.',
        actions_taken: 'BLOCK_CARD',
        exposure_usd: 512.00
      }
    ],
    timeline: [
      { step_number: 1, name: 'Intake Trigger', phase: 'trigger', timestamp: '2016-11-12T08:14:00Z', status: 'completed', description: 'Model risk_score alert received at 0.62 on flagged txn 3514030.', output_summary: 'Single signal risk score intake.' },
      { step_number: 2, name: 'Evidence Gathering', phase: 'evidence_gather', timestamp: '2016-11-12T08:14:15Z', status: 'completed', tool_invoked: 'card_window + card_baseline', description: 'Retrieved card baseline history and 24h transaction window.', output_summary: 'Baseline clean; 2 recent online txns detected.' },
      { step_number: 3, name: 'Initial Assessment', phase: 'initial_assessment', timestamp: '2016-11-12T08:14:45Z', status: 'completed', description: 'Assessed single signal under Policy R1. Probability 0.45 below 0.70 threshold.', output_summary: 'Recommended customer verification before block.' },
      { step_number: 4, name: 'Evidence Request', phase: 'evidence_request', timestamp: '2016-11-12T08:16:00Z', status: 'completed', description: 'Sent simulated verification inquiry to cardholder C12382.', output_summary: 'Customer repudiation received: denied authorization.' },
      { step_number: 5, name: 'Final Policy Reassessment', phase: 'final_policy', timestamp: '2016-11-12T08:22:30Z', status: 'completed', description: 'Evaluated R2 with customer denial. Exposure $482.00 routes to L1 BLOCK_CARD.', output_summary: 'Final actions emitted with L1 route.' },
      { step_number: 6, name: 'Graph Writeback', phase: 'writeback', timestamp: '2016-11-12T08:24:00Z', status: 'completed', tool_invoked: 'write_case', description: 'Persisted closed case GC-HHG-001 into TigerGraph memory.', output_summary: 'Memory stored with temporal stamp 2016-11-12T08:24:00Z.' }
    ],
    uncertainty: {
      evidence_count: 3,
      independent_sources: 2,
      has_conflicts: false,
      confidence_level: 'High'
    }
  },
  {
    case_id: 'HHG-002',
    opened_at: '2016-11-14T14:22:00Z',
    trigger_type: 'risk_score',
    trigger_text: 'Model risk_score alert (0.74) for Card C08912-K1 at billing region 444.0 (flagged txn 3519820)',
    flagged_txn_id: '3519820',
    card_id: 'C08912-K1',
    customer_id: 'C08912',
    risk_score: 0.74,
    case: {
      status: 'closed_legitimate',
      verdict: 'legitimate',
      fraud_probability: 0.05,
      raw_probability: 0.12,
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
          id: 'ev-002-1',
          claim: 'Transaction 3519820 occurred in-person (channel = in_person, ProductCD W) in billing region 444.0, while home billing region is 299.0.',
          source: 'graph',
          ref: 'card_window(C08912-K1, 6h)',
          entity_ids: ['3519820', '444.0'],
          counter_evidence: false,
          confidence_impact: 'medium',
          timestamp: '2016-11-14T14:22:05Z'
        },
        {
          id: 'ev-002-2',
          claim: 'Customer confirmed legitimate vacation travel to resort destination in region 444.0 via SMS verification.',
          source: 'customer',
          ref: 'evidence_requests[0]',
          entity_ids: ['C08912', '3519820'],
          counter_evidence: true,
          confidence_impact: 'high',
          timestamp: '2016-11-14T14:28:10Z'
        },
        {
          id: 'ev-002-3',
          claim: 'No concurrent in-person activity observed in home region 299.0 (no impossible velocity or dual-presence conflict).',
          source: 'graph',
          ref: 'region_cluster(444.0, 24h)',
          entity_ids: ['C08912-K1'],
          counter_evidence: true,
          confidence_impact: 'high',
          timestamp: '2016-11-14T14:29:40Z'
        }
      ],
      similar_prior_cases: ['CC-0716', 'CC-1422'],
      summary: 'Alert triggered on out-of-region in-person charge (billing region 444.0 vs home 299.0). In accordance with Policy R1, initial inquiry was sent to cardholder. Customer confirmed authorized vacation travel. Under Policy R3, case was cleared as legitimate and closed without card interruption (CLOSE_NO_FRAUD, 0 exposure).',
      written_to_graph: true,
      graph_case_id: 'GC-HHG-002'
    },
    evidence_requests: [
      {
        id: 'req-002',
        type: 'customer_validation',
        asked_after_step: 3,
        assumed_response: 'Customer confirms they are traveling in region 444.0 on vacation and authorized the $285.00 resort hotel charge.',
        simulation_rule: 'Customer confirmed travel per documented historical baseline profile (matches CC-0716 archetype).',
        asked_at: '2016-11-14T14:24:00Z',
        response_status: 'received'
      }
    ],
    next_best_actions: {
      initial: [
        {
          id: 'act-002-init-1',
          action: 'VERIFY_WITH_CUSTOMER',
          route: 'auto',
          reason: 'R1: High risk score (0.74) on out-of-region charge requires customer verification before blocking.',
          executed: true,
          status: 'executed'
        }
      ],
      final: [
        {
          id: 'act-002-fin-1',
          action: 'CLOSE_NO_FRAUD',
          route: 'auto',
          reason: 'R3: Customer confirmed transaction as authorized vacation travel; case cleared without card block.',
          executed: true,
          status: 'executed'
        }
      ],
      what_changed: 'Customer confirmation cleared alert; transitioned from VERIFY_WITH_CUSTOMER to CLOSE_NO_FRAUD under Policy R3.'
    },
    sar: {
      file: false,
      reason: 'Legitimate transaction confirmed by cardholder; SAR filing not applicable.',
      narrative: '',
      subjects: [],
      total_amount_usd: 0,
      activity_dates: []
    },
    stop_reason: 'Stopping Rule 2: Customer verification response confirmed authorized charge, settling alert.',
    tool_calls: 5,
    tokens: 3120,
    latency_s: 2.18,
    subgraph: {
      nodes: [
        { id: 'C08912', type: 'customer', label: 'Customer C08912', details: { home_region: 299.0 } },
        { id: 'C08912-K1', type: 'card', label: 'Card C08912-K1', details: { card1: 18204 } },
        { id: '3519820', type: 'transaction', label: 'Txn 3519820', sublabel: '$285.00 (Cleared)', isFlagged: true, details: { amt: 285.00, channel: 'in_person', region: 444.0 } },
        { id: 'reg-444', type: 'region', label: 'Region 444.0', details: { type: 'resort_destination', country: 87 } }
      ],
      edges: [
        { id: 'e-201', source: 'C08912', target: 'C08912-K1', type: 'OWNS', label: 'OWNS' },
        { id: 'e-202', source: 'C08912-K1', target: '3519820', type: 'MADE', label: 'MADE' },
        { id: 'e-203', source: '3519820', target: 'reg-444', type: 'BILLED_IN', label: 'BILLED_IN' }
      ]
    },
    affected_txns_detail: [
      { txn_id: '3519820', amount_usd: 285.00, disguised_amt: 284.992, timestamp: '2016-11-14T14:18:00Z', product_cd: 'W', channel: 'in_person', billing_region: '444.0', status: 'flagged', risk_score: 0.74 }
    ],
    prior_cases_detail: [
      {
        case_id: 'CC-0716',
        opened_at: '2016-07-28T16:00:00Z',
        closed_at: '2016-07-28T17:15:00Z',
        outcome: 'cleared',
        pattern: 'none',
        similarity_score: 0.91,
        shared_elements: ['billing_region: 444.0', 'channel: in_person', 'ProductCD: W'],
        notes: 'Cardholder confirmed domestic holiday travel in resort region 444.0; cleared with no fraud.',
        actions_taken: 'VERIFY_WITH_CUSTOMER|CLOSE_NO_FRAUD',
        exposure_usd: 0.00
      }
    ],
    timeline: [
      { step_number: 1, name: 'Intake Trigger', phase: 'trigger', timestamp: '2016-11-14T14:22:00Z', status: 'completed', description: 'Model risk alert (0.74) for Card C08912-K1 in region 444.0.', output_summary: 'Out-of-region in-person transaction alert.' },
      { step_number: 2, name: 'Evidence Gathering', phase: 'evidence_gather', timestamp: '2016-11-14T14:22:30Z', status: 'completed', tool_invoked: 'card_baseline + region_cluster', description: 'Checked card baseline: home region is 299.0; no concurrent home charges.', output_summary: 'Clean travel profile, no simultaneous dual-presence.' },
      { step_number: 3, name: 'Initial Assessment', phase: 'initial_assessment', timestamp: '2016-11-14T14:23:10Z', status: 'completed', description: 'Policy R1 applied: verification initiated prior to any block decision.', output_summary: 'VERIFY_WITH_CUSTOMER recommended.' },
      { step_number: 4, name: 'Evidence Request', phase: 'evidence_request', timestamp: '2016-11-14T14:24:00Z', status: 'completed', description: 'Customer response received: cardholder confirmed vacation.', output_summary: 'Cardholder confirmation logged.' },
      { step_number: 5, name: 'Final Reassessment', phase: 'final_policy', timestamp: '2016-11-14T14:28:40Z', status: 'completed', description: 'Policy R3 executed: CLOSE_NO_FRAUD emitted; 0 exposure, no SAR.', output_summary: 'Case successfully cleared without blocking.' },
      { step_number: 6, name: 'Graph Writeback', phase: 'writeback', timestamp: '2016-11-14T14:30:00Z', status: 'completed', tool_invoked: 'write_case', description: 'Written to TigerGraph with cleared status.', output_summary: 'Graph memory updated: GC-HHG-002.' }
    ],
    uncertainty: {
      evidence_count: 3,
      independent_sources: 2,
      has_conflicts: false,
      confidence_level: 'High'
    }
  },
  {
    case_id: 'HHG-003',
    opened_at: '2016-11-15T10:05:00Z',
    trigger_type: 'customer_report',
    trigger_text: 'Customer dispute: "I never authorized this recurring $83.79 charge at Txn 3522104"',
    flagged_txn_id: '3522104',
    card_id: 'C10492-K1',
    customer_id: 'C10492',
    risk_score: null,
    case: {
      status: 'closed_legitimate',
      verdict: 'legitimate',
      fraud_probability: 0.08,
      raw_probability: 0.14,
      calibrated_probability: 0.08,
      pattern: 'none',
      pattern_description: '',
      affected_txn_ids: [],
      first_suspicious_txn_id: '',
      connected_card_ids: [],
      connected_device_profiles: [],
      exposure_usd: 0.00,
      evidence: [
        {
          id: 'ev-003-1',
          claim: 'Customer dispute initiated on digital subscription charge $83.79.',
          source: 'customer',
          ref: 'customer_report',
          entity_ids: ['3522104'],
          counter_evidence: false,
          confidence_impact: 'medium',
          timestamp: '2016-11-15T10:05:01Z'
        },
        {
          id: 'ev-003-2',
          claim: 'Graph traversal shows identical recurring billing: $83.78 charged on 2016-09-15 and 2016-10-15 under same ProductCD/email proxy.',
          source: 'graph',
          ref: 'recurring_pattern(C10492-K1, 3522104)',
          entity_ids: ['3522104', 'C10492-K1'],
          counter_evidence: true,
          confidence_impact: 'high',
          timestamp: '2016-11-15T10:06:12Z'
        },
        {
          id: 'ev-003-3',
          claim: 'Disguised amount difference ($83.79 vs $83.78) falls strictly within the +/- $0.05 dataset noise tolerance.',
          source: 'document',
          ref: 'Fraud Policy v1.0 Section 4.2',
          entity_ids: ['3522104'],
          counter_evidence: true,
          confidence_impact: 'high',
          timestamp: '2016-11-15T10:06:30Z'
        }
      ],
      similar_prior_cases: ['CC-0902', 'CC-1140'],
      summary: 'Cardholder disputed $83.79 monthly charge as unauthorized. GSQL recurring_pattern query identified matching transactions billed on the 15th of the prior two consecutive months with identical product attributes. In strict accordance with Policy R7 (recurring charge protection), card was NOT blocked. Agent opened case, verified with customer, and issued billing dispute advice (WARN_CUSTOMER).',
      written_to_graph: true,
      graph_case_id: 'GC-HHG-003'
    },
    evidence_requests: [
      {
        id: 'req-003',
        type: 'customer_validation',
        asked_after_step: 3,
        assumed_response: 'Customer reminded of annual software subscription billed monthly; customer acknowledged active account and withdrew fraud complaint.',
        simulation_rule: 'R7 recurring pattern matching historical baseline triggers educational prompt rather than compromise assumption.',
        asked_at: '2016-11-15T10:07:00Z',
        response_status: 'received'
      }
    ],
    next_best_actions: {
      initial: [
        {
          id: 'act-003-init-1',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Customer report received.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-003-init-2',
          action: 'VERIFY_WITH_CUSTOMER',
          route: 'auto',
          reason: 'R7: Charge matches historical monthly recurring cadence; verification required. Do NOT block.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-003-init-3',
          action: 'WARN_CUSTOMER',
          route: 'auto',
          reason: 'R7: Inform customer of recurring merchant subscription and merchant contact details.',
          executed: true,
          status: 'executed'
        }
      ],
      final: [
        {
          id: 'act-003-fin-1',
          action: 'CLOSE_NO_FRAUD',
          route: 'auto',
          reason: 'R3 & R7: Customer confirmed recognized recurring subscription; closed without card block.',
          executed: true,
          status: 'executed'
        }
      ],
      what_changed: 'Customer verified recurring subscription; case successfully concluded under R7/R3 without card block.'
    },
    sar: {
      file: false,
      reason: 'Merchant subscription billing dispute; not a fraudulent event.',
      narrative: '',
      subjects: [],
      total_amount_usd: 0,
      activity_dates: []
    },
    stop_reason: 'Stopping Rule 2: Customer verification resolved the recurring charge misunderstanding.',
    tool_calls: 4,
    tokens: 2890,
    latency_s: 1.95,
    subgraph: {
      nodes: [
        { id: 'C10492', type: 'customer', label: 'Customer C10492', details: { account_type: 'retail' } },
        { id: 'C10492-K1', type: 'card', label: 'Card C10492-K1', details: { card1: 15420 } },
        { id: '3522104', type: 'transaction', label: 'Txn 3522104', sublabel: '$83.79 (Nov 15)', isFlagged: true, details: { amt: 83.79, date: '2016-11-15' } },
        { id: '3410002', type: 'transaction', label: 'Txn 3410002', sublabel: '$83.78 (Oct 15)', details: { amt: 83.78, date: '2016-10-15' } },
        { id: '3298101', type: 'transaction', label: 'Txn 3298101', sublabel: '$83.78 (Sep 15)', details: { amt: 83.78, date: '2016-09-15' } }
      ],
      edges: [
        { id: 'e-301', source: 'C10492', target: 'C10492-K1', type: 'OWNS', label: 'OWNS' },
        { id: 'e-302', source: 'C10492-K1', target: '3522104', type: 'MADE', label: 'MADE' },
        { id: 'e-303', source: 'C10492-K1', target: '3410002', type: 'MADE', label: 'MADE' },
        { id: 'e-304', source: 'C10492-K1', target: '3298101', type: 'MADE', label: 'MADE' },
        { id: 'e-305', source: '3298101', target: '3410002', type: 'NEXT', temporalNext: true, label: 'RECURRING (30d)' },
        { id: 'e-306', source: '3410002', target: '3522104', type: 'NEXT', temporalNext: true, label: 'RECURRING (31d)' }
      ]
    },
    affected_txns_detail: [
      { txn_id: '3522104', amount_usd: 83.79, disguised_amt: 83.788, timestamp: '2016-11-15T09:45:00Z', product_cd: 'H', channel: 'online', status: 'flagged' }
    ],
    prior_cases_detail: [
      {
        case_id: 'CC-0902',
        opened_at: '2016-08-16T12:00:00Z',
        closed_at: '2016-08-16T13:30:00Z',
        outcome: 'cleared',
        pattern: 'none',
        similarity_score: 0.94,
        shared_elements: ['recurring_pattern', 'ProductCD: H', 'customer_report_trigger'],
        notes: 'Disputed digital SaaS charge matched monthly pattern; customer clarified and case closed without blocking.',
        actions_taken: 'VERIFY_WITH_CUSTOMER|WARN_CUSTOMER|CLOSE_NO_FRAUD',
        exposure_usd: 0.00
      }
    ],
    timeline: [
      { step_number: 1, name: 'Intake Trigger', phase: 'trigger', timestamp: '2016-11-15T10:05:00Z', status: 'completed', description: 'Customer dispute received for transaction 3522104 ($83.79).', output_summary: 'Customer report intake.' },
      { step_number: 2, name: 'Evidence Gathering', phase: 'evidence_gather', timestamp: '2016-11-15T10:05:30Z', status: 'completed', tool_invoked: 'recurring_pattern', description: 'Executed recurring_pattern GSQL query against C10492-K1 history.', output_summary: 'Found 2 prior monthly transactions of $83.78 on the 15th.' },
      { step_number: 3, name: 'Initial Assessment', phase: 'initial_assessment', timestamp: '2016-11-15T10:06:00Z', status: 'completed', description: 'Applied Policy R7. Do NOT block. Issued verification & warning.', output_summary: 'R7 actions emitted (VERIFY + WARN).' },
      { step_number: 4, name: 'Evidence Request', phase: 'evidence_request', timestamp: '2016-11-15T10:07:00Z', status: 'completed', description: 'Customer response received: confirmed recognized subscription.', output_summary: 'Customer confirmed charge.' },
      { step_number: 5, name: 'Final Reassessment', phase: 'final_policy', timestamp: '2016-11-15T10:10:00Z', status: 'completed', description: 'Policy R3 invoked: CLOSE_NO_FRAUD executed.', output_summary: 'Closed as legitimate.' },
      { step_number: 6, name: 'Graph Writeback', phase: 'writeback', timestamp: '2016-11-15T10:12:00Z', status: 'completed', tool_invoked: 'write_case', description: 'Case persisted into graph memory: GC-HHG-003.', output_summary: 'Memory updated.' }
    ],
    uncertainty: {
      evidence_count: 3,
      independent_sources: 3,
      has_conflicts: false,
      confidence_level: 'High'
    }
  },
  {
    case_id: 'HHG-004',
    opened_at: '2016-11-16T11:45:00Z',
    trigger_type: 'risk_score',
    trigger_text: 'Model risk_score alert (0.83) on Card C07421-K1 at TransactionID 3526110',
    flagged_txn_id: '3526110',
    card_id: 'C07421-K1',
    customer_id: 'C07421',
    risk_score: 0.83,
    case: {
      status: 'closed_fraud',
      verdict: 'fraud',
      fraud_probability: 0.94,
      raw_probability: 0.89,
      calibrated_probability: 0.94,
      pattern: 'card_testing',
      pattern_description: '',
      affected_txn_ids: ['3526088', '3526094', '3526101', '3526110'],
      first_suspicious_txn_id: '3526088',
      connected_card_ids: [],
      connected_device_profiles: ['Linux | Firefox 48.0 | 1366x768'],
      exposure_usd: 1255.20,
      evidence: [
        {
          id: 'ev-004-1',
          claim: 'Three consecutive micro-authorizations ($1.25, $2.10, $1.85) occurred online within 32 minutes on ProductCD C.',
          source: 'graph',
          ref: 'patterns/card_testing.gsql',
          entity_ids: ['3526088', '3526094', '3526101'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-16T11:45:10Z'
        },
        {
          id: 'ev-004-2',
          claim: 'Micro-authorizations immediately succeeded by a large purchase attempt of $1,250.00 at transaction 3526110.',
          source: 'graph',
          ref: 'card_window(C07421-K1, 1h)',
          entity_ids: ['3526110'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-16T11:45:25Z'
        },
        {
          id: 'ev-004-3',
          claim: 'Prior closed case CC-0016 demonstrates identical card testing sequence leading to rapid account drain.',
          source: 'document',
          ref: 'Similar closed case CC-0016',
          entity_ids: ['CC-0016'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-16T11:46:00Z'
        }
      ],
      similar_prior_cases: ['CC-0016', 'CC-0412'],
      summary: 'Classic automated card testing pattern detected. Three low-dollar online authorizations ($1.25, $2.10, $1.85) executed within 32 minutes, immediately followed by an attempted $1,250.00 luxury goods purchase. Under Policy R5, pending transactions were declined and card block initiated. With total exposure exceeding $1,000 ($1,255.20), Policy 3a mandates SAR filing.',
      written_to_graph: true,
      graph_case_id: 'GC-HHG-004'
    },
    evidence_requests: [],
    next_best_actions: {
      initial: [
        {
          id: 'act-004-init-1',
          action: 'DECLINE_TRANSACTION',
          route: 'L1',
          reason: 'R5: Card testing sequence identified; decline large authorization attempt ($1,250.00).',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-004-init-2',
          action: 'STEP_UP_AUTH',
          route: 'auto',
          reason: 'R5: Require step-up authentication for any concurrent pending sessions.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-004-init-3',
          action: 'BLOCK_CARD',
          route: 'L1',
          reason: 'R5: High-risk card testing burst; block card under L1 approval (exposure $1,255.20 <= $2,500).',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-004-init-4',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Confirmed card testing attack with probability = 0.94 >= 0.30.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-004-init-5',
          action: 'FILE_REPORT',
          route: 'L2',
          reason: 'Policy 3a: Confirmed fraud with total exposure ($1,255.20) > $1,000 threshold requires SAR filing.',
          executed: false,
          status: 'pending_approval'
        }
      ],
      final: [
        {
          id: 'act-004-fin-1',
          action: 'DECLINE_TRANSACTION',
          route: 'L1',
          reason: 'R5: Card testing sequence identified; decline large authorization attempt ($1,250.00).',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-004-fin-2',
          action: 'STEP_UP_AUTH',
          route: 'auto',
          reason: 'R5: Require step-up authentication for any concurrent pending sessions.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-004-fin-3',
          action: 'BLOCK_CARD',
          route: 'L1',
          reason: 'R5: High-risk card testing burst; block card under L1 approval (exposure $1,255.20 <= $2,500).',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-004-fin-4',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Confirmed card testing attack with probability = 0.94 >= 0.30.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-004-fin-5',
          action: 'FILE_REPORT',
          route: 'L2',
          reason: 'Policy 3a: Confirmed fraud with total exposure ($1,255.20) > $1,000 threshold requires SAR filing.',
          executed: false,
          status: 'pending_approval'
        }
      ],
      what_changed: 'nothing'
    },
    sar: {
      file: true,
      reason: 'Confirmed card testing bot attack exceeding $1,000 exposure threshold ($1,255.20) under Policy 3a.',
      narrative: 'This Suspicious Activity Report documents an automated card testing and unauthorized high-value purchase attack on Card C07421-K1 belonging to Customer C07421. On November 16, 2016 between 11:10 UTC and 11:42 UTC, three rapid micro-authorizations totaling $5.20 were processed through an online merchant interface from a Linux/Firefox client profile. Immediately following card validation, the actor attempted an unauthorized transaction of $1,250.00 at TransactionID 3526110. The velocity and progression match automated credential stuffing typologies. Issuer fraud operations intercepted the authorization under Policy R5. Total exposure across the four transactions is $1,255.20, warranting SAR filing under FinCEN guidance for unauthorized electronic access.',
      subjects: ['C07421', 'C07421-K1', '3526110', 'Linux | Firefox 48.0 | 1366x768'],
      total_amount_usd: 1255.20,
      activity_dates: ['2016-11-16', '2016-11-16']
    },
    stop_reason: 'Stopping Rule 1: Probability = 0.94 >= 0.85 supported by 3 independent evidence items matching R5 criteria.',
    tool_calls: 6,
    tokens: 3820,
    latency_s: 2.84,
    subgraph: {
      nodes: [
        { id: 'C07421', type: 'customer', label: 'Customer C07421', details: { status: 'active' } },
        { id: 'C07421-K1', type: 'card', label: 'Card C07421-K1', details: { card1: 19412 } },
        { id: '3526088', type: 'transaction', label: 'Txn 3526088', sublabel: '$1.25 (Test 1)', details: { amt: 1.25, channel: 'online' } },
        { id: '3526094', type: 'transaction', label: 'Txn 3526094', sublabel: '$2.10 (Test 2)', details: { amt: 2.10, channel: 'online' } },
        { id: '3526101', type: 'transaction', label: 'Txn 3526101', sublabel: '$1.85 (Test 3)', details: { amt: 1.85, channel: 'online' } },
        { id: '3526110', type: 'transaction', label: 'Txn 3526110', sublabel: '$1,250.00 (Flagged)', isFlagged: true, details: { amt: 1250.00, channel: 'online', risk: 0.83 } },
        { id: 'dev-004', type: 'device', label: 'Linux / Firefox 48', details: { id_30: 'Linux', id_31: 'Firefox 48.0' } }
      ],
      edges: [
        { id: 'e-401', source: 'C07421', target: 'C07421-K1', type: 'OWNS', label: 'OWNS' },
        { id: 'e-402', source: 'C07421-K1', target: '3526088', type: 'MADE', label: 'MADE' },
        { id: 'e-403', source: 'C07421-K1', target: '3526094', type: 'MADE', label: 'MADE' },
        { id: 'e-404', source: 'C07421-K1', target: '3526101', type: 'MADE', label: 'MADE' },
        { id: 'e-405', source: 'C07421-K1', target: '3526110', type: 'MADE', label: 'MADE' },
        { id: 'e-406', source: '3526088', target: '3526094', type: 'NEXT', temporalNext: true, label: 'NEXT (12m)' },
        { id: 'e-407', source: '3526094', target: '3526101', type: 'NEXT', temporalNext: true, label: 'NEXT (10m)' },
        { id: 'e-408', source: '3526101', target: '3526110', type: 'NEXT', temporalNext: true, label: 'NEXT (10m)' },
        { id: 'e-409', source: '3526110', target: 'dev-004', type: 'FROM_DEVICE', label: 'FROM_DEVICE' }
      ]
    },
    affected_txns_detail: [
      { txn_id: '3526088', amount_usd: 1.25, disguised_amt: 1.251, timestamp: '2016-11-16T11:10:00Z', product_cd: 'C', channel: 'online', status: 'affected' },
      { txn_id: '3526094', amount_usd: 2.10, disguised_amt: 2.102, timestamp: '2016-11-16T11:22:00Z', product_cd: 'C', channel: 'online', status: 'affected' },
      { txn_id: '3526101', amount_usd: 1.85, disguised_amt: 1.849, timestamp: '2016-11-16T11:32:00Z', product_cd: 'C', channel: 'online', status: 'affected' },
      { txn_id: '3526110', amount_usd: 1250.00, disguised_amt: 1250.003, timestamp: '2016-11-16T11:42:00Z', product_cd: 'C', channel: 'online', status: 'flagged', risk_score: 0.83 }
    ],
    prior_cases_detail: [
      {
        case_id: 'CC-0016',
        opened_at: '2016-07-09T08:30:00Z',
        closed_at: '2016-07-09T10:15:00Z',
        outcome: 'confirmed_fraud',
        pattern: 'card_testing',
        similarity_score: 0.95,
        shared_elements: ['card_testing_pattern', 'ProductCD: C', 'micro_auth_burst'],
        notes: 'Classic card testing: 3 micro txns <$2.50 followed by $1,100 attempt. Fast decline prevented loss.',
        actions_taken: 'DECLINE_TRANSACTION|BLOCK_CARD|FILE_REPORT',
        exposure_usd: 1106.00
      }
    ],
    timeline: [
      { step_number: 1, name: 'Intake Trigger', phase: 'trigger', timestamp: '2016-11-16T11:45:00Z', status: 'completed', description: 'Model risk alert (0.83) on $1,250.00 authorization (3526110).', output_summary: 'Card testing alert intake.' },
      { step_number: 2, name: 'Evidence Gathering', phase: 'evidence_gather', timestamp: '2016-11-16T11:45:15Z', status: 'completed', tool_invoked: 'patterns/card_testing', description: 'Scanned 1-hour window: identified 3 prior authorizations < $2.50.', output_summary: 'Confirmed card testing pattern sequence.' },
      { step_number: 3, name: 'Assessment & Policy', phase: 'initial_assessment', timestamp: '2016-11-16T11:45:45Z', status: 'completed', description: 'Applied Policy R5 and Policy 3a. Declines issued; L1 block & L2 SAR generated.', output_summary: 'Actions emitted per R5; SAR created (> $1,000).' },
      { step_number: 4, name: 'Stopping Check', phase: 'final_policy', timestamp: '2016-11-16T11:46:00Z', status: 'completed', description: 'Stopping Rule 1 satisfied (p=0.94 >= 0.85 with 3 evidence items). No request needed.', output_summary: 'Final actions match initial.' },
      { step_number: 5, name: 'Graph Writeback', phase: 'writeback', timestamp: '2016-11-16T11:47:00Z', status: 'completed', tool_invoked: 'write_case', description: 'Persisted to graph: GC-HHG-004.', output_summary: 'Case written to memory.' }
    ],
    uncertainty: {
      evidence_count: 3,
      independent_sources: 2,
      has_conflicts: false,
      confidence_level: 'High'
    }
  },
  {
    case_id: 'HHG-005',
    opened_at: '2016-11-17T15:10:00Z',
    trigger_type: 'risk_score',
    trigger_text: 'Model risk_score alert (0.68) on Card C11504-K1 with new device profile (flagged txn 3531090)',
    flagged_txn_id: '3531090',
    card_id: 'C11504-K1',
    customer_id: 'C11504',
    risk_score: 0.68,
    case: {
      status: 'closed_legitimate',
      verdict: 'legitimate',
      fraud_probability: 0.04,
      raw_probability: 0.09,
      calibrated_probability: 0.04,
      pattern: 'none',
      pattern_description: '',
      affected_txn_ids: [],
      first_suspicious_txn_id: '',
      connected_card_ids: [],
      connected_device_profiles: [],
      exposure_usd: 0.00,
      evidence: [
        {
          id: 'ev-005-1',
          claim: 'Transaction 3531090 occurred from an unseen device (iOS 10.1 / Mobile Safari, id_15 = New).',
          source: 'graph',
          ref: 'device_neighbors',
          entity_ids: ['3531090', 'dev-005'],
          counter_evidence: false,
          confidence_impact: 'medium',
          timestamp: '2016-11-17T15:10:05Z'
        },
        {
          id: 'ev-005-2',
          claim: 'Customer successfully passed two-factor step-up authentication on primary registered mobile number.',
          source: 'customer',
          ref: 'evidence_requests[0]',
          entity_ids: ['C11504'],
          counter_evidence: true,
          confidence_impact: 'high',
          timestamp: '2016-11-17T15:14:20Z'
        },
        {
          id: 'ev-005-3',
          claim: 'Purchase amount ($165.00) matches customer routine grocery/department store historical basket size.',
          source: 'graph',
          ref: 'card_baseline(C11504-K1)',
          entity_ids: ['3531090'],
          counter_evidence: true,
          confidence_impact: 'medium',
          timestamp: '2016-11-17T15:15:10Z'
        }
      ],
      similar_prior_cases: ['CC-0158', 'CC-0419'],
      summary: 'Alert opened on new device flag (iOS 10.1, id_15 = New) with moderate risk score (0.68). Following Policy R1, step-up authentication was triggered before taking adverse card action. Cardholder successfully completed multi-factor authentication, confirming legitimate smartphone upgrade. Under Policy R3, alert was resolved and case closed with 0 exposure and no card block.',
      written_to_graph: true,
      graph_case_id: 'GC-HHG-005'
    },
    evidence_requests: [
      {
        id: 'req-005',
        type: 'step_up_auth',
        asked_after_step: 3,
        assumed_response: 'Customer successfully verified identity via OTP prompt sent to registered phone; confirmed device upgrade.',
        simulation_rule: 'New device phone upgrade archetype (matches CC-0158); customer passes step-up authentication prompt.',
        asked_at: '2016-11-17T15:12:00Z',
        response_status: 'received'
      }
    ],
    next_best_actions: {
      initial: [
        {
          id: 'act-005-init-1',
          action: 'STEP_UP_AUTH',
          route: 'auto',
          reason: 'R1: Moderate risk score (0.68 < 0.70) on new device requires step-up authentication before blocking.',
          executed: true,
          status: 'executed'
        }
      ],
      final: [
        {
          id: 'act-005-fin-1',
          action: 'CLOSE_NO_FRAUD',
          route: 'auto',
          reason: 'R3: Cardholder completed 2FA step-up validation; cleared as legitimate new device registration.',
          executed: true,
          status: 'executed'
        }
      ],
      what_changed: 'Successful 2FA completion cleared new device alert; transitioned from STEP_UP_AUTH to CLOSE_NO_FRAUD.'
    },
    sar: {
      file: false,
      reason: 'Legitimate new device verified by cardholder; SAR not applicable.',
      narrative: '',
      subjects: [],
      total_amount_usd: 0,
      activity_dates: []
    },
    stop_reason: 'Stopping Rule 2: Multi-factor verification settled device ownership conclusively.',
    tool_calls: 5,
    tokens: 3040,
    latency_s: 2.10,
    subgraph: {
      nodes: [
        { id: 'C11504', type: 'customer', label: 'Customer C11504', details: { '2fa_enabled': true } },
        { id: 'C11504-K1', type: 'card', label: 'Card C11504-K1', details: { card1: 17188 } },
        { id: '3531090', type: 'transaction', label: 'Txn 3531090', sublabel: '$165.00 (Cleared)', isFlagged: true, details: { amt: 165.00, channel: 'online' } },
        { id: 'dev-005', type: 'device', label: 'iOS 10.1 / Safari', details: { id_30: 'iOS 10.1', id_15: 'New' } }
      ],
      edges: [
        { id: 'e-501', source: 'C11504', target: 'C11504-K1', type: 'OWNS', label: 'OWNS' },
        { id: 'e-502', source: 'C11504-K1', target: '3531090', type: 'MADE', label: 'MADE' },
        { id: 'e-503', source: '3531090', target: 'dev-005', type: 'FROM_DEVICE', label: 'FROM_DEVICE' }
      ]
    },
    affected_txns_detail: [
      { txn_id: '3531090', amount_usd: 165.00, disguised_amt: 164.995, timestamp: '2016-11-17T15:05:00Z', product_cd: 'W', channel: 'online', status: 'flagged', risk_score: 0.68 }
    ],
    prior_cases_detail: [
      {
        case_id: 'CC-0158',
        opened_at: '2016-07-18T14:10:00Z',
        closed_at: '2016-07-18T15:00:00Z',
        outcome: 'cleared',
        pattern: 'none',
        similarity_score: 0.92,
        shared_elements: ['id_15: New', 'step_up_auth_passed', 'basket_size_match'],
        notes: 'Cardholder purchased new smartphone; passed step-up authentication. Cleared without disruption.',
        actions_taken: 'STEP_UP_AUTH|CLOSE_NO_FRAUD',
        exposure_usd: 0.00
      }
    ],
    timeline: [
      { step_number: 1, name: 'Intake Trigger', phase: 'trigger', timestamp: '2016-11-17T15:10:00Z', status: 'completed', description: 'Model risk alert (0.68) on new device at txn 3531090.', output_summary: 'New device alert intake.' },
      { step_number: 2, name: 'Evidence Gathering', phase: 'evidence_gather', timestamp: '2016-11-17T15:10:30Z', status: 'completed', tool_invoked: 'device_neighbors', description: 'Evaluated device: unseen on account (id_15=New); no other cards share device.', output_summary: 'Isolated new device profile.' },
      { step_number: 3, name: 'Initial Assessment', phase: 'initial_assessment', timestamp: '2016-11-17T15:11:00Z', status: 'completed', description: 'Policy R1 applied: step-up auth issued before blocking.', output_summary: 'STEP_UP_AUTH recommended.' },
      { step_number: 4, name: 'Evidence Request', phase: 'evidence_request', timestamp: '2016-11-17T15:12:00Z', status: 'completed', description: 'Customer completed 2FA step-up validation.', output_summary: 'Step-up auth success.' },
      { step_number: 5, name: 'Final Reassessment', phase: 'final_policy', timestamp: '2016-11-17T15:15:00Z', status: 'completed', description: 'Policy R3 executed: CLOSE_NO_FRAUD emitted.', output_summary: 'Closed as legitimate.' },
      { step_number: 6, name: 'Graph Writeback', phase: 'writeback', timestamp: '2016-11-17T15:16:00Z', status: 'completed', tool_invoked: 'write_case', description: 'Persisted to graph: GC-HHG-005.', output_summary: 'Memory updated.' }
    ],
    uncertainty: {
      evidence_count: 3,
      independent_sources: 2,
      has_conflicts: false,
      confidence_level: 'High'
    }
  }
];
