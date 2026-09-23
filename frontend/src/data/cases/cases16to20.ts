/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { BenchmarkCase } from '../../types';

export const CASES_16_TO_20: BenchmarkCase[] = [
  {
    case_id: 'HHG-016',
    opened_at: '2016-11-28T10:10:00Z',
    trigger_type: 'customer_report',
    trigger_text: 'Customer dispute: "Account email address changed to disposable domain; $2,800 unauthorized electronics order" on Card C08711-K1',
    flagged_txn_id: '3575400',
    card_id: 'C08711-K1',
    customer_id: 'C08711',
    risk_score: null,
    case: {
      status: 'closed_fraud',
      verdict: 'fraud',
      fraud_probability: 0.97,
      raw_probability: 0.94,
      calibrated_probability: 0.97,
      pattern: 'account_takeover',
      pattern_description: '',
      affected_txn_ids: ['3575400'],
      first_suspicious_txn_id: '3575400',
      connected_card_ids: [],
      connected_device_profiles: ['Windows 10 | Edge 14.0 | Disposable Email'],
      exposure_usd: 2800.00,
      evidence: [
        {
          id: 'ev-016-1',
          claim: 'Customer confirmed unauthorized account takeover: primary contact email diverted to 10-minute temporary mail domain.',
          source: 'customer',
          ref: 'customer_report',
          entity_ids: ['C08711', '3575400'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-28T10:10:05Z'
        },
        {
          id: 'ev-016-2',
          claim: 'High-value consumer electronics purchase ($2,800.00) initiated immediately following email modification.',
          source: 'graph',
          ref: 'card_window(C08711-K1, 6h)',
          entity_ids: ['3575400'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-28T10:11:15Z'
        },
        {
          id: 'ev-016-3',
          claim: 'Recipient email domain (R_emaildomain) flagged as temporary anonymization relay.',
          source: 'graph',
          ref: 'email_neighbors',
          entity_ids: ['email-temp-relay'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-28T10:11:45Z'
        }
      ],
      similar_prior_cases: ['CC-1205', 'CC-1944'],
      summary: 'Confirmed Account Takeover (ATO) with email domain hijacking. Threat actor altered account credentials to route one-time confirmation codes through a temporary email domain, subsequently ordering $2,800.00 in consumer electronics. Because exposure ($2,800.00) exceeds $2,500, Policy 2 dictates L2 managerial authorization for card blocking. Total exposure exceeds $1,000 threshold, mandating L2 SAR filing under Policy 3a.',
      written_to_graph: true,
      graph_case_id: 'GC-HHG-016'
    },
    evidence_requests: [],
    next_best_actions: {
      initial: [
        {
          id: 'act-016-init-1',
          action: 'BLOCK_CARD',
          route: 'L2',
          reason: 'R2: Confirmed ATO with total exposure ($2,800.00) > $2,500 routes to L2 approval.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-016-init-2',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Confirmed ATO customer dispute.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-016-init-3',
          action: 'FILE_REPORT',
          route: 'L2',
          reason: 'Policy 3a: Confirmed fraud with total exposure ($2,800.00) > $1,000 mandates SAR.',
          executed: false,
          status: 'pending_approval'
        }
      ],
      final: [
        {
          id: 'act-016-fin-1',
          action: 'BLOCK_CARD',
          route: 'L2',
          reason: 'R2: Confirmed ATO with total exposure ($2,800.00) > $2,500 routes to L2 approval.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-016-fin-2',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Confirmed ATO customer dispute.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-016-fin-3',
          action: 'FILE_REPORT',
          route: 'L2',
          reason: 'Policy 3a: Confirmed fraud with total exposure ($2,800.00) > $1,000 mandates SAR.',
          executed: false,
          status: 'pending_approval'
        }
      ],
      what_changed: 'nothing'
    },
    sar: {
      file: true,
      reason: 'Confirmed Account Takeover with email diversion totaling $2,800.00 under Policy 3a and FinCEN advisory.',
      narrative: 'This Suspicious Activity Report documents an Account Takeover (ATO) scheme targeting Customer C08711 and associated Card C08711-K1. On November 28, 2016, an unauthorized user infiltrated digital banking credentials, altered the registered notification email address to a known disposable domain relay, and executed a fraudulent online purchase of $2,800.00 (TransactionID 3575400) at an electronics retailer. The genuine account holder contacted the fraud operations desk upon discovering account lockouts. Fraud operations locked the digital account, placed an administrative block on Card C08711-K1 pending L2 approval, and intercepted delivery. The total suspicious volume is $2,800.00, meeting FinCEN SAR reporting mandates.',
      subjects: ['C08711', 'C08711-K1', '3575400', 'email-temp-relay'],
      total_amount_usd: 2800.00,
      activity_dates: ['2016-11-28', '2016-11-28']
    },
    stop_reason: 'Stopping Rule 1: High certainty boundary (p=0.97 >= 0.85) corroborated by customer dispute and disposable email records.',
    tool_calls: 6,
    tokens: 3900,
    latency_s: 2.88,
    subgraph: {
      nodes: [
        { id: 'C08711', type: 'customer', label: 'Customer C08711', details: { email_modified: true } },
        { id: 'C08711-K1', type: 'card', label: 'Card C08711-K1', details: { card1: 17200 } },
        { id: '3575400', type: 'transaction', label: 'Txn 3575400', sublabel: '$2,800.00', isFlagged: true, details: { amt: 2800.00 } },
        { id: 'em-relay', type: 'email', label: 'tempmail-relay.net', details: { disposable: true } }
      ],
      edges: [
        { id: 'e-1601', source: 'C08711', target: 'C08711-K1', type: 'OWNS', label: 'OWNS' },
        { id: 'e-1602', source: 'C08711-K1', target: '3575400', type: 'MADE', label: 'MADE' },
        { id: 'e-1603', source: '3575400', target: 'em-relay', type: 'PURCHASER_EMAIL', label: 'PURCHASER_EMAIL' }
      ]
    },
    affected_txns_detail: [
      { txn_id: '3575400', amount_usd: 2800.00, disguised_amt: 2799.994, timestamp: '2016-11-28T10:05:00Z', product_cd: 'C', channel: 'online', status: 'flagged' }
    ],
    prior_cases_detail: [
      {
        case_id: 'CC-1205',
        opened_at: '2016-08-22T10:00:00Z',
        closed_at: '2016-08-22T12:00:00Z',
        outcome: 'confirmed_fraud',
        pattern: 'account_takeover',
        similarity_score: 0.94,
        shared_elements: ['disposable_email', 'ATO_electronics', 'exposure_bracket: >$2500'],
        notes: 'ATO with temporary email domain redirect; L2 card block and SAR executed.',
        actions_taken: 'BLOCK_CARD|FILE_REPORT',
        exposure_usd: 2850.00
      }
    ],
    timeline: [
      { step_number: 1, name: 'Intake Trigger', phase: 'trigger', timestamp: '2016-11-28T10:10:00Z', status: 'completed', description: 'Customer report received: email hijacked and $2,800 order placed.', output_summary: 'ATO dispute intake.' },
      { step_number: 2, name: 'Evidence Gathering', phase: 'evidence_gather', timestamp: '2016-11-28T10:10:30Z', status: 'completed', tool_invoked: 'email_neighbors', description: 'Confirmed disposable email relay domain.', output_summary: 'Identified disposable relay.' },
      { step_number: 3, name: 'Policy Evaluation', phase: 'final_policy', timestamp: '2016-11-28T10:11:00Z', status: 'completed', description: 'Policy R2: exposure ($2,800) > $2,500 mandates L2 BLOCK_CARD and L2 FILE_REPORT.', output_summary: 'L2 actions routed to Approval Queue.' },
      { step_number: 4, name: 'Graph Writeback', phase: 'writeback', timestamp: '2016-11-28T10:12:00Z', status: 'completed', tool_invoked: 'write_case', description: 'Persisted to graph: GC-HHG-016.', output_summary: 'Memory updated.' }
    ],
    uncertainty: {
      evidence_count: 3,
      independent_sources: 2,
      has_conflicts: false,
      confidence_level: 'High'
    }
  },
  {
    case_id: 'HHG-017',
    opened_at: '2016-11-29T14:45:00Z',
    trigger_type: 'risk_score',
    trigger_text: 'Model risk_score alert (0.57) on Card C05192-K1 at TransactionID 3579100 with hidden proxy',
    flagged_txn_id: '3579100',
    card_id: 'C05192-K1',
    customer_id: 'C05192',
    risk_score: 0.57,
    case: {
      status: 'closed_fraud',
      verdict: 'fraud',
      fraud_probability: 0.90,
      raw_probability: 0.84,
      calibrated_probability: 0.90,
      pattern: 'card_not_present_fraud',
      pattern_description: '',
      affected_txn_ids: ['3579100', '3579115'],
      first_suspicious_txn_id: '3579100',
      connected_card_ids: ['C04899-K1'],
      connected_device_profiles: ['Windows 10 | Chrome 54.0 | Hidden Proxy (Found)'],
      exposure_usd: 1350.00,
      evidence: [
        {
          id: 'ev-017-1',
          claim: 'Transaction 3579100 ($675.00) utilized device marked id_15 = Found, previously tied to confirmed fraud case CC-1404 on Card C04899-K1.',
          source: 'graph',
          ref: 'device_neighbors',
          entity_ids: ['3579100', 'dev-017', 'C04899-K1'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-29T14:45:10Z'
        },
        {
          id: 'ev-017-2',
          claim: 'Device communicates behind a hidden commercial VPN/proxy obfuscation tunnel (id_23 = IP_PROXY:HIDDEN).',
          source: 'graph',
          ref: 'device_neighbors',
          entity_ids: ['dev-017'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-29T14:45:30Z'
        },
        {
          id: 'ev-017-3',
          claim: 'Customer confirmed repudiation during simulated verification inquiry.',
          source: 'customer',
          ref: 'evidence_requests[0]',
          entity_ids: ['C05192'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-29T14:50:00Z'
        }
      ],
      similar_prior_cases: ['CC-1404', 'CC-1944'],
      summary: 'Alert opened on moderate model risk score (0.57) with hidden proxy telemetry. GSQL device_neighbors query discovered the device (id_15 = Found) was previously connected to confirmed fraud on Card C04899-K1. Pursuant to Policy R1, verification was dispatched; cardholder denied authorization. Under Policy R2 and R6, card was blocked under L1 approval, connected card C04899-K1 placed on monitoring, and SAR filed ($1,350.00 > $1,000).',
      written_to_graph: true,
      graph_case_id: 'GC-HHG-017'
    },
    evidence_requests: [
      {
        id: 'req-017',
        type: 'customer_validation',
        asked_after_step: 3,
        assumed_response: 'Customer confirms they did not authorize the $675.00 online transaction and do not utilize proxy or VPN software.',
        simulation_rule: 'Found device tied to prior fraud archetype; customer denies authorization.',
        asked_at: '2016-11-29T14:46:00Z',
        response_status: 'received'
      }
    ],
    next_best_actions: {
      initial: [
        {
          id: 'act-017-init-1',
          action: 'VERIFY_WITH_CUSTOMER',
          route: 'auto',
          reason: 'R1: Moderate initial risk score (0.57 < 0.70) requires customer verification before blocking.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-017-init-2',
          action: 'MONITOR_CONNECTED_CARDS',
          route: 'auto',
          reason: 'R6: Device tied to prior case on Card C04899-K1; monitor linked entities.',
          executed: true,
          status: 'executed'
        }
      ],
      final: [
        {
          id: 'act-017-fin-1',
          action: 'BLOCK_CARD',
          route: 'L1',
          reason: 'R2: Customer denied transaction; exposure ($1,350.00) <= $2,500 routes to L1 approval.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-017-fin-2',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Confirmed fraud with connected device history.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-017-fin-3',
          action: 'MONITOR_CONNECTED_CARDS',
          route: 'auto',
          reason: 'R6: Device tied to Card C04899-K1; continue monitoring connected entities.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-017-fin-4',
          action: 'FILE_REPORT',
          route: 'L2',
          reason: 'Policy 3a: Confirmed fraud with total exposure ($1,350.00) > $1,000 threshold.',
          executed: false,
          status: 'pending_approval'
        }
      ],
      what_changed: 'Customer repudiation shifted recommendation from verification to L1 BLOCK_CARD and L2 FILE_REPORT with continued monitoring under R6.'
    },
    sar: {
      file: true,
      reason: 'Confirmed fraud with hidden proxy device linked across multiple cards totaling $1,350.00 under Policy R6 and Policy 3a.',
      narrative: 'This Suspicious Activity Report details unauthorized electronic transactions conducted on Card C05192-K1 belonging to Customer C05192. On November 29, 2016, two unauthorized authorizations totaling $1,350.00 (TransactionIDs 3579100 and 3579115) were initiated through a device routing traffic through a commercial hidden proxy tunnel (IP_PROXY:HIDDEN). TigerGraph graph traversal revealed this exact device profile was previously flagged in historical confirmed fraud case CC-1404 involving Card C04899-K1. The authorized cardholder repudiated all activity. Total unauthorized exposure is $1,350.00, meeting FinCEN thresholds.',
      subjects: ['C05192', 'C05192-K1', 'C04899-K1', '3579100', '3579115', 'IP_PROXY:HIDDEN'],
      total_amount_usd: 1350.00,
      activity_dates: ['2016-11-29', '2016-11-29']
    },
    stop_reason: 'Stopping Rule 2: Customer repudiation resolved alert conclusively.',
    tool_calls: 6,
    tokens: 3820,
    latency_s: 2.75,
    subgraph: {
      nodes: [
        { id: 'C05192', type: 'customer', label: 'Customer C05192', details: { active: true } },
        { id: 'C05192-K1', type: 'card', label: 'Card C05192-K1 (Flagged)', isFlagged: true, details: { card1: 16800 } },
        { id: 'C04899-K1', type: 'card', label: 'Card C04899-K1 (Connected)', details: { card1: 19120 } },
        { id: '3579100', type: 'transaction', label: 'Txn 3579100', sublabel: '$675.00', isFlagged: true, details: { amt: 675.00 } },
        { id: '3579115', type: 'transaction', label: 'Txn 3579115', sublabel: '$675.00', details: { amt: 675.00 } },
        { id: 'dev-017', type: 'device', label: 'Win10 / Hidden Proxy', highlighted: true, details: { id_15: 'Found', id_23: 'IP_PROXY:HIDDEN' } }
      ],
      edges: [
        { id: 'e-1701', source: 'C05192', target: 'C05192-K1', type: 'OWNS', label: 'OWNS' },
        { id: 'e-1702', source: 'C05192-K1', target: '3579100', type: 'MADE', label: 'MADE' },
        { id: 'e-1703', source: 'C05192-K1', target: '3579115', type: 'MADE', label: 'MADE' },
        { id: 'e-1704', source: '3579100', target: 'dev-017', type: 'FROM_DEVICE', label: 'FROM_DEVICE' },
        { id: 'e-1705', source: 'C04899-K1', target: 'dev-017', type: 'SHARED_DEVICE', label: 'PRIOR FRAUD LINK' }
      ]
    },
    affected_txns_detail: [
      { txn_id: '3579100', amount_usd: 675.00, disguised_amt: 674.992, timestamp: '2016-11-29T14:35:00Z', product_cd: 'C', channel: 'online', status: 'flagged', risk_score: 0.57 },
      { txn_id: '3579115', amount_usd: 675.00, disguised_amt: 675.004, timestamp: '2016-11-29T14:40:00Z', product_cd: 'C', channel: 'online', status: 'affected' }
    ],
    prior_cases_detail: [
      {
        case_id: 'CC-1404',
        opened_at: '2016-09-02T12:00:00Z',
        closed_at: '2016-09-02T14:00:00Z',
        outcome: 'confirmed_fraud',
        pattern: 'card_not_present_fraud',
        similarity_score: 0.92,
        shared_elements: ['IP_PROXY:HIDDEN', 'id_15: Found', 'connected_device'],
        notes: 'Prior confirmed fraud on Card C04899-K1 using same hidden proxy signature.',
        actions_taken: 'BLOCK_CARD|FILE_REPORT',
        exposure_usd: 1250.00
      }
    ],
    timeline: [
      { step_number: 1, name: 'Intake Trigger', phase: 'trigger', timestamp: '2016-11-29T14:45:00Z', status: 'completed', description: 'Risk alert (0.57) on txn 3579100 with hidden proxy.', output_summary: 'Hidden proxy intake.' },
      { step_number: 2, name: 'Evidence Gathering', phase: 'evidence_gather', timestamp: '2016-11-29T14:45:20Z', status: 'completed', tool_invoked: 'device_neighbors', description: 'Found device previously involved in CC-1404 on Card C04899-K1.', output_summary: 'Connected device link discovered.' },
      { step_number: 3, name: 'Initial Assessment', phase: 'initial_assessment', timestamp: '2016-11-29T14:45:40Z', status: 'completed', description: 'Policy R1: customer verification sent; MONITOR_CONNECTED_CARDS emitted per R6.', output_summary: 'Initial actions emitted.' },
      { step_number: 4, name: 'Evidence Request', phase: 'evidence_request', timestamp: '2016-11-29T14:46:00Z', status: 'completed', description: 'Customer repudiated transactions.', output_summary: 'Repudiation logged.' },
      { step_number: 5, name: 'Final Reassessment', phase: 'final_policy', timestamp: '2016-11-29T14:50:30Z', status: 'completed', description: 'Policy R2: L1 BLOCK_CARD and L2 FILE_REPORT emitted.', output_summary: 'Final actions emitted.' },
      { step_number: 6, name: 'Graph Writeback', phase: 'writeback', timestamp: '2016-11-29T14:52:00Z', status: 'completed', tool_invoked: 'write_case', description: 'Persisted to graph: GC-HHG-017.', output_summary: 'Memory updated.' }
    ],
    uncertainty: {
      evidence_count: 3,
      independent_sources: 2,
      has_conflicts: false,
      confidence_level: 'High'
    }
  },
  {
    case_id: 'HHG-018',
    opened_at: '2016-11-30T11:15:00Z',
    trigger_type: 'customer_report',
    trigger_text: 'Customer dispute: "Dispute $95.00 gym membership charge (expected $85.00)" on Card C11200-K1',
    flagged_txn_id: '3583200',
    card_id: 'C11200-K1',
    customer_id: 'C11200',
    risk_score: null,
    case: {
      status: 'closed_legitimate',
      verdict: 'legitimate',
      fraud_probability: 0.04,
      raw_probability: 0.08,
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
          id: 'ev-018-1',
          claim: 'Customer disputed $95.00 monthly fitness membership charge citing annual rate increase.',
          source: 'customer',
          ref: 'customer_report',
          entity_ids: ['3583200'],
          counter_evidence: true,
          confidence_impact: 'medium',
          timestamp: '2016-11-30T11:15:02Z'
        },
        {
          id: 'ev-018-2',
          claim: 'Graph recurring_pattern traversal matched consecutive monthly billings at same merchant for prior 11 months ($85.00).',
          source: 'graph',
          ref: 'recurring_pattern(C11200-K1, 3583200)',
          entity_ids: ['C11200-K1', '3583200'],
          counter_evidence: true,
          confidence_impact: 'high',
          timestamp: '2016-11-30T11:15:30Z'
        },
        {
          id: 'ev-018-3',
          claim: 'Cardholder agreed charge represents a commercial merchant billing rate adjustment, not compromised card credentials.',
          source: 'customer',
          ref: 'evidence_requests[0]',
          entity_ids: ['C11200'],
          counter_evidence: true,
          confidence_impact: 'high',
          timestamp: '2016-11-30T11:20:00Z'
        }
      ],
      similar_prior_cases: ['CC-0902', 'CC-1140'],
      summary: 'Cardholder disputed $95.00 monthly charge reflecting a $10.00 annual subscription rate adjustment. GSQL recurring_pattern traversal verified 11 months of continuous recurring payments to the identical fitness merchant. Under Policy R7 (recurring charge protection), card blocking was strictly avoided. The agent verified the billing dispute with cardholder, issued merchant dispute guidance (WARN_CUSTOMER), and closed case with 0 exposure.',
      written_to_graph: true,
      graph_case_id: 'GC-HHG-018'
    },
    evidence_requests: [
      {
        id: 'req-018',
        type: 'customer_validation',
        asked_after_step: 3,
        assumed_response: 'Customer acknowledged gym membership annual price increase notice; will contact gym management directly.',
        simulation_rule: 'R7 recurring billing price increase archetype; customer clarifies merchant dispute.',
        asked_at: '2016-11-30T11:16:00Z',
        response_status: 'received'
      }
    ],
    next_best_actions: {
      initial: [
        {
          id: 'act-018-init-1',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Customer dispute received.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-018-init-2',
          action: 'VERIFY_WITH_CUSTOMER',
          route: 'auto',
          reason: 'R7: Charge matches historical recurring fitness merchant; verify with customer. Do NOT block.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-018-init-3',
          action: 'WARN_CUSTOMER',
          route: 'auto',
          reason: 'R7: Provide customer with merchant dispute instructions.',
          executed: true,
          status: 'executed'
        }
      ],
      final: [
        {
          id: 'act-018-fin-1',
          action: 'CLOSE_NO_FRAUD',
          route: 'auto',
          reason: 'R3 & R7: Customer confirmed recognized recurring merchant subscription dispute; closed without card block.',
          executed: true,
          status: 'executed'
        }
      ],
      what_changed: 'Customer clarified merchant pricing adjustment; case closed as legitimate under Policy R7/R3 without card block.'
    },
    sar: {
      file: false,
      reason: 'Merchant subscription billing rate dispute; not a fraudulent event.',
      narrative: '',
      subjects: [],
      total_amount_usd: 0,
      activity_dates: []
    },
    stop_reason: 'Stopping Rule 2: Customer verification resolved subscription rate dispute.',
    tool_calls: 4,
    tokens: 2950,
    latency_s: 1.98,
    subgraph: {
      nodes: [
        { id: 'C11200', type: 'customer', label: 'Customer C11200', details: { tenure: '36m' } },
        { id: 'C11200-K1', type: 'card', label: 'Card C11200-K1', details: { card1: 15400 } },
        { id: '3583200', type: 'transaction', label: 'Txn 3583200', sublabel: '$95.00 (Nov)', isFlagged: true, details: { amt: 95.00 } },
        { id: '3471000', type: 'transaction', label: 'Txn 3471000', sublabel: '$85.00 (Oct)', details: { amt: 85.00 } }
      ],
      edges: [
        { id: 'e-1801', source: 'C11200', target: 'C11200-K1', type: 'OWNS', label: 'OWNS' },
        { id: 'e-1802', source: 'C11200-K1', target: '3583200', type: 'MADE', label: 'MADE' },
        { id: 'e-1803', source: 'C11200-K1', target: '3471000', type: 'MADE', label: 'MADE' },
        { id: 'e-1804', source: '3471000', target: '3583200', type: 'NEXT', temporalNext: true, label: 'RECURRING (30d)' }
      ]
    },
    affected_txns_detail: [
      { txn_id: '3583200', amount_usd: 95.00, disguised_amt: 95.002, timestamp: '2016-11-30T11:05:00Z', product_cd: 'H', channel: 'online', status: 'flagged' }
    ],
    prior_cases_detail: [
      {
        case_id: 'CC-0902',
        opened_at: '2016-08-16T12:00:00Z',
        closed_at: '2016-08-16T13:30:00Z',
        outcome: 'cleared',
        pattern: 'none',
        similarity_score: 0.95,
        shared_elements: ['recurring_pattern', 'subscription_increase', 'R7_applied'],
        notes: 'Price adjustment dispute on recurring billing; cleared under R7 without card interruption.',
        actions_taken: 'VERIFY_WITH_CUSTOMER|WARN_CUSTOMER|CLOSE_NO_FRAUD',
        exposure_usd: 0.00
      }
    ],
    timeline: [
      { step_number: 1, name: 'Intake Trigger', phase: 'trigger', timestamp: '2016-11-30T11:15:00Z', status: 'completed', description: 'Customer dispute on $95.00 gym charge.', output_summary: 'Dispute intake.' },
      { step_number: 2, name: 'Evidence Gathering', phase: 'evidence_gather', timestamp: '2016-11-30T11:15:20Z', status: 'completed', tool_invoked: 'recurring_pattern', description: 'Verified 11 months of prior $85 charges.', output_summary: 'Recurring profile verified.' },
      { step_number: 3, name: 'Initial Assessment', phase: 'initial_assessment', timestamp: '2016-11-30T11:15:45Z', status: 'completed', description: 'Policy R7 applied: verification and warning emitted; no block.', output_summary: 'R7 actions emitted.' },
      { step_number: 4, name: 'Evidence Request', phase: 'evidence_request', timestamp: '2016-11-30T11:16:00Z', status: 'completed', description: 'Customer acknowledged gym price update.', output_summary: 'Customer clarified.' },
      { step_number: 5, name: 'Final Reassessment', phase: 'final_policy', timestamp: '2016-11-30T11:20:30Z', status: 'completed', description: 'Policy R3: CLOSE_NO_FRAUD emitted.', output_summary: 'Closed as legitimate.' },
      { step_number: 6, name: 'Graph Writeback', phase: 'writeback', timestamp: '2016-11-30T11:22:00Z', status: 'completed', tool_invoked: 'write_case', description: 'Persisted to graph: GC-HHG-018.', output_summary: 'Memory updated.' }
    ],
    uncertainty: {
      evidence_count: 3,
      independent_sources: 2,
      has_conflicts: false,
      confidence_level: 'High'
    }
  },
  {
    case_id: 'HHG-019',
    opened_at: '2016-12-01T15:20:00Z',
    trigger_type: 'risk_score',
    trigger_text: 'Model risk_score alert (0.85) on Card C06412-K1 at TransactionID 3587400',
    flagged_txn_id: '3587400',
    card_id: 'C06412-K1',
    customer_id: 'C06412',
    risk_score: 0.85,
    case: {
      status: 'closed_fraud',
      verdict: 'fraud',
      fraud_probability: 0.96,
      raw_probability: 0.91,
      calibrated_probability: 0.96,
      pattern: 'card_testing',
      pattern_description: '',
      affected_txn_ids: ['3587380', '3587385', '3587392', '3587400'],
      first_suspicious_txn_id: '3587380',
      connected_card_ids: [],
      connected_device_profiles: ['Linux | Chrome 53.0'],
      exposure_usd: 354.50,
      evidence: [
        {
          id: 'ev-019-1',
          claim: 'Three consecutive micro authorizations ($1.00, $1.50, $2.00) completed within 28 minutes on ProductCD C.',
          source: 'graph',
          ref: 'patterns/card_testing.gsql',
          entity_ids: ['3587380', '3587385', '3587392'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-12-01T15:20:05Z'
        },
        {
          id: 'ev-019-2',
          claim: 'Card testing sequence followed by a successfully cleared purchase of $350.00 at TransactionID 3587400.',
          source: 'graph',
          ref: 'card_window(C06412-K1, 1h)',
          entity_ids: ['3587400'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-12-01T15:20:25Z'
        },
        {
          id: 'ev-019-3',
          claim: 'Policy R5 clause 2 strictly invoked: because a purchase over $100.00 ($350.00) already cleared, card block is mandatory.',
          source: 'document',
          ref: 'Fraud Policy v1.0 Rule R5 Clause 2',
          entity_ids: ['3587400'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-12-01T15:20:45Z'
        }
      ],
      similar_prior_cases: ['CC-0016', 'CC-0412'],
      summary: 'Card testing pattern with cleared purchase breach. Three micro-authorizations ($1.00, $1.50, $2.00) were successfully executed by an automated bot, followed by a cleared $350.00 online order. Under Policy R5 (clause 2: "if a purchase over $100 already cleared, BLOCK_CARD"), the card was blocked under L1 route and pending subsequent attempts declined. Total exposure is $354.50 (no SAR required as exposure < $1,000).',
      written_to_graph: true,
      graph_case_id: 'GC-HHG-019'
    },
    evidence_requests: [],
    next_best_actions: {
      initial: [
        {
          id: 'act-019-init-1',
          action: 'BLOCK_CARD',
          route: 'L1',
          reason: 'R5 Clause 2: Card testing confirmed and a purchase over $100 ($350.00) already cleared; block card under L1.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-019-init-2',
          action: 'DECLINE_TRANSACTION',
          route: 'L1',
          reason: 'R5: Decline any subsequent pending authorizations.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-019-init-3',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Confirmed card testing with cleared fraudulent purchase.',
          executed: true,
          status: 'executed'
        }
      ],
      final: [
        {
          id: 'act-019-fin-1',
          action: 'BLOCK_CARD',
          route: 'L1',
          reason: 'R5 Clause 2: Card testing confirmed and a purchase over $100 ($350.00) already cleared; block card under L1.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-019-fin-2',
          action: 'DECLINE_TRANSACTION',
          route: 'L1',
          reason: 'R5: Decline any subsequent pending authorizations.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-019-fin-3',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Confirmed card testing with cleared fraudulent purchase.',
          executed: true,
          status: 'executed'
        }
      ],
      what_changed: 'nothing'
    },
    sar: {
      file: false,
      reason: 'Total exposure ($354.50) < $1,000 and no multi-card device ring present (Policy 3a).',
      narrative: '',
      subjects: [],
      total_amount_usd: 0,
      activity_dates: []
    },
    stop_reason: 'Stopping Rule 1: High certainty (p=0.96 >= 0.85) corroborated by 3 graph evidence items under R5.',
    tool_calls: 6,
    tokens: 3720,
    latency_s: 2.65,
    subgraph: {
      nodes: [
        { id: 'C06412', type: 'customer', label: 'Customer C06412', details: { active: true } },
        { id: 'C06412-K1', type: 'card', label: 'Card C06412-K1', details: { card1: 17100 } },
        { id: '3587380', type: 'transaction', label: 'Txn 3587380', sublabel: '$1.00', details: { amt: 1.00 } },
        { id: '3587385', type: 'transaction', label: 'Txn 3587385', sublabel: '$1.50', details: { amt: 1.50 } },
        { id: '3587392', type: 'transaction', label: 'Txn 3587392', sublabel: '$2.00', details: { amt: 2.00 } },
        { id: '3587400', type: 'transaction', label: 'Txn 3587400', sublabel: '$350.00 (Cleared)', isFlagged: true, details: { amt: 350.00, cleared: true } }
      ],
      edges: [
        { id: 'e-1901', source: 'C06412', target: 'C06412-K1', type: 'OWNS', label: 'OWNS' },
        { id: 'e-1902', source: 'C06412-K1', target: '3587380', type: 'MADE', label: 'MADE' },
        { id: 'e-1903', source: 'C06412-K1', target: '3587385', type: 'MADE', label: 'MADE' },
        { id: 'e-1904', source: 'C06412-K1', target: '3587392', type: 'MADE', label: 'MADE' },
        { id: 'e-1905', source: 'C06412-K1', target: '3587400', type: 'MADE', label: 'MADE' },
        { id: 'e-1906', source: '3587380', target: '3587385', type: 'NEXT', temporalNext: true, label: 'NEXT (10m)' },
        { id: 'e-1907', source: '3587385', target: '3587392', type: 'NEXT', temporalNext: true, label: 'NEXT (9m)' },
        { id: 'e-1908', source: '3587392', target: '3587400', type: 'NEXT', temporalNext: true, label: 'NEXT (9m)' }
      ]
    },
    affected_txns_detail: [
      { txn_id: '3587380', amount_usd: 1.00, disguised_amt: 1.001, timestamp: '2016-12-01T14:48:00Z', product_cd: 'C', channel: 'online', status: 'affected' },
      { txn_id: '3587385', amount_usd: 1.50, disguised_amt: 1.498, timestamp: '2016-12-01T14:58:00Z', product_cd: 'C', channel: 'online', status: 'affected' },
      { txn_id: '3587392', amount_usd: 2.00, disguised_amt: 2.002, timestamp: '2016-12-01T15:07:00Z', product_cd: 'C', channel: 'online', status: 'affected' },
      { txn_id: '3587400', amount_usd: 350.00, disguised_amt: 349.995, timestamp: '2016-12-01T15:16:00Z', product_cd: 'C', channel: 'online', status: 'flagged', risk_score: 0.85 }
    ],
    prior_cases_detail: [
      {
        case_id: 'CC-0016',
        opened_at: '2016-07-09T08:30:00Z',
        closed_at: '2016-07-09T10:15:00Z',
        outcome: 'confirmed_fraud',
        pattern: 'card_testing',
        similarity_score: 0.94,
        shared_elements: ['card_testing_cleared', 'ProductCD: C', 'R5_clause_2'],
        notes: 'Card testing with cleared purchase; card blocked per R5 clause 2.',
        actions_taken: 'BLOCK_CARD|DECLINE_TRANSACTION',
        exposure_usd: 420.00
      }
    ],
    timeline: [
      { step_number: 1, name: 'Intake Trigger', phase: 'trigger', timestamp: '2016-12-01T15:20:00Z', status: 'completed', description: 'Risk alert (0.85) on cleared $350 purchase.', output_summary: 'Card testing alert intake.' },
      { step_number: 2, name: 'Evidence Gathering', phase: 'evidence_gather', timestamp: '2016-12-01T15:20:20Z', status: 'completed', tool_invoked: 'patterns/card_testing', description: 'Found 3 prior micro authorizations in 28-minute window.', output_summary: 'Identified 3 micro test txns.' },
      { step_number: 3, name: 'Policy Execution', phase: 'final_policy', timestamp: '2016-12-01T15:20:45Z', status: 'completed', description: 'Applied Policy R5 clause 2: purchase > $100 cleared. Emitted L1 BLOCK_CARD and DECLINE_TRANSACTION.', output_summary: 'R5 actions emitted.' },
      { step_number: 4, name: 'Graph Writeback', phase: 'writeback', timestamp: '2016-12-01T15:22:00Z', status: 'completed', tool_invoked: 'write_case', description: 'Persisted to graph: GC-HHG-019.', output_summary: 'Memory updated.' }
    ],
    uncertainty: {
      evidence_count: 3,
      independent_sources: 2,
      has_conflicts: false,
      confidence_level: 'High'
    }
  },
  {
    case_id: 'HHG-020',
    opened_at: '2016-12-02T16:30:00Z',
    trigger_type: 'risk_score',
    trigger_text: 'Model risk_score alert (0.64) on Card C02914-K1 with conflicting geographic telemetry',
    flagged_txn_id: '3591200',
    card_id: 'C02914-K1',
    customer_id: 'C02914',
    risk_score: 0.64,
    case: {
      status: 'escalated',
      verdict: 'uncertain',
      fraud_probability: 0.52,
      raw_probability: 0.55,
      calibrated_probability: 0.52,
      pattern: 'none',
      pattern_description: '',
      affected_txn_ids: ['3591200'],
      first_suspicious_txn_id: '3591200',
      connected_card_ids: [],
      connected_device_profiles: ['Macintosh | Safari 10.0'],
      exposure_usd: 720.00,
      evidence: [
        {
          id: 'ev-020-1',
          claim: 'Transaction 3591200 ($720.00) routed from an IP address located in a foreign country (addr2 != 87).',
          source: 'graph',
          ref: 'card_window(C02914-K1, 6h)',
          entity_ids: ['3591200'],
          counter_evidence: false,
          confidence_impact: 'medium',
          timestamp: '2016-12-02T16:30:05Z'
        },
        {
          id: 'ev-020-2',
          claim: 'Browser canvas fingerprint, persistent device cookie, and 3D-Secure challenge tokens match cardholder authentic 3-year baseline.',
          source: 'graph',
          ref: 'card_baseline(C02914-K1)',
          entity_ids: ['C02914-K1'],
          counter_evidence: true,
          confidence_impact: 'high',
          timestamp: '2016-12-02T16:30:30Z'
        },
        {
          id: 'ev-020-3',
          claim: 'Direct evidentiary conflict: IP geo-anomaly conflicts with authentic biometric and persistent cryptographic tokens.',
          source: 'document',
          ref: 'Fraud Policy v1.0 Rule R8',
          entity_ids: ['3591200'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-12-02T16:31:00Z'
        }
      ],
      similar_prior_cases: ['CC-1402', 'CC-2101'],
      summary: 'Conflicting evidentiary signals on Card C02914-K1 ($720.00 authorization). Foreign IP routing suggests potential account compromise, but device hardware fingerprint, persistent session cookies, and 3DS response align perfectly with the cardholder historical profile (possible business traveler on hotel network). Because evidence conflicts and exposure ($720.00) exceeds $500, Policy R8 dictates avoiding arbitrary guessing: card placed on monitoring and case escalated to human analyst.',
      written_to_graph: true,
      graph_case_id: 'GC-HHG-020'
    },
    evidence_requests: [],
    next_best_actions: {
      initial: [
        {
          id: 'act-020-init-1',
          action: 'ESCALATE_TO_ANALYST',
          route: 'auto',
          reason: 'R8: Verdict uncertain and exposure ($720.00) > $500 with conflicting IP vs authentic device tokens; escalate to human analyst.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-020-init-2',
          action: 'MONITOR_CARD',
          route: 'auto',
          reason: 'R8: Place card on heightened velocity monitoring pending human investigator review.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-020-init-3',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Probability = 0.52 >= 0.30 threshold.',
          executed: true,
          status: 'executed'
        }
      ],
      final: [
        {
          id: 'act-020-fin-1',
          action: 'ESCALATE_TO_ANALYST',
          route: 'auto',
          reason: 'R8: Verdict uncertain and exposure ($720.00) > $500 with conflicting IP vs authentic device tokens; escalate to human analyst.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-020-fin-2',
          action: 'MONITOR_CARD',
          route: 'auto',
          reason: 'R8: Place card on heightened velocity monitoring pending human investigator review.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-020-fin-3',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Probability = 0.52 >= 0.30 threshold.',
          executed: true,
          status: 'executed'
        }
      ],
      what_changed: 'nothing'
    },
    sar: {
      file: false,
      reason: 'Verdict uncertain; awaiting human investigator review under Policy R8.',
      narrative: '',
      subjects: [],
      total_amount_usd: 0,
      activity_dates: []
    },
    stop_reason: 'Stopping Rule 3: Information exhaustion; irreconcilable signal conflict triggers mandatory Policy R8 human escalation.',
    tool_calls: 5,
    tokens: 3350,
    latency_s: 2.30,
    subgraph: {
      nodes: [
        { id: 'C02914', type: 'customer', label: 'Customer C02914', details: { segment: 'corporate' } },
        { id: 'C02914-K1', type: 'card', label: 'Card C02914-K1', details: { card1: 18900 } },
        { id: '3591200', type: 'transaction', label: 'Txn 3591200', sublabel: '$720.00 (Conflict)', isFlagged: true, details: { amt: 720.00, conflict: true } }
      ],
      edges: [
        { id: 'e-2001', source: 'C02914', target: 'C02914-K1', type: 'OWNS', label: 'OWNS' },
        { id: 'e-2002', source: 'C02914-K1', target: '3591200', type: 'MADE', label: 'MADE' }
      ]
    },
    affected_txns_detail: [
      { txn_id: '3591200', amount_usd: 720.00, disguised_amt: 719.991, timestamp: '2016-12-02T16:22:00Z', product_cd: 'C', channel: 'online', status: 'flagged', risk_score: 0.64 }
    ],
    prior_cases_detail: [
      {
        case_id: 'CC-1402',
        opened_at: '2016-09-02T10:00:00Z',
        closed_at: '2016-09-03T11:00:00Z',
        outcome: 'cleared',
        pattern: 'none',
        similarity_score: 0.86,
        shared_elements: ['conflicting_evidence', 'R8_escalation'],
        notes: 'Corporate traveler on international roaming; cleared by human investigator.',
        actions_taken: 'ESCALATE_TO_ANALYST|MONITOR_CARD',
        exposure_usd: 890.00
      }
    ],
    timeline: [
      { step_number: 1, name: 'Intake Trigger', phase: 'trigger', timestamp: '2016-12-02T16:30:00Z', status: 'completed', description: 'Risk alert (0.64) on conflicting telemetry.', output_summary: 'Conflicting signal intake.' },
      { step_number: 2, name: 'Evidence Gathering', phase: 'evidence_gather', timestamp: '2016-12-02T16:30:25Z', status: 'completed', tool_invoked: 'card_baseline', description: 'Found foreign IP but authentic device fingerprint and 3DS response.', output_summary: 'Direct evidence conflict identified.' },
      { step_number: 3, name: 'Policy Evaluation', phase: 'final_policy', timestamp: '2016-12-02T16:30:50Z', status: 'completed', description: 'Applied Policy R8: exposure $720 > $500 and conflict. Emitted ESCALATE_TO_ANALYST and MONITOR_CARD.', output_summary: 'R8 escalation executed.' },
      { step_number: 4, name: 'Graph Writeback', phase: 'writeback', timestamp: '2016-12-02T16:32:00Z', status: 'completed', tool_invoked: 'write_case', description: 'Persisted to graph: GC-HHG-020.', output_summary: 'Memory updated.' }
    ],
    uncertainty: {
      evidence_count: 3,
      independent_sources: 2,
      has_conflicts: true,
      confidence_level: 'Low'
    }
  }
];
