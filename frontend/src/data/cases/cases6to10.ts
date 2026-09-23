/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { BenchmarkCase } from '../../types';

export const CASES_6_TO_10: BenchmarkCase[] = [
  {
    case_id: 'HHG-006',
    opened_at: '2016-11-18T09:30:00Z',
    trigger_type: 'customer_report',
    trigger_text: 'Customer dispute: "Unauthorized cash-out transfer & password change alert received" on Card C14209-K1',
    flagged_txn_id: '3535400',
    card_id: 'C14209-K1',
    customer_id: 'C14209',
    risk_score: null,
    case: {
      status: 'closed_fraud',
      verdict: 'fraud',
      fraud_probability: 0.96,
      raw_probability: 0.92,
      calibrated_probability: 0.96,
      pattern: 'account_takeover',
      pattern_description: '',
      affected_txn_ids: ['3535400', '3535412'],
      first_suspicious_txn_id: '3535400',
      connected_card_ids: [],
      connected_device_profiles: ['Windows 7 | Chrome 52.0 | Anonymous Proxy'],
      exposure_usd: 3190.00,
      evidence: [
        {
          id: 'ev-006-1',
          claim: 'Customer reported unauthorized password change and profile contact modification immediately prior to transaction burst.',
          source: 'customer',
          ref: 'customer_report',
          entity_ids: ['C14209', '3535400'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-18T09:30:05Z'
        },
        {
          id: 'ev-006-2',
          claim: 'Login and transaction 3535400 ($1,595.00) originated from anonymous proxy (id_23 = IP_PROXY:ANONYMOUS) in billing region 126.0.',
          source: 'graph',
          ref: 'device_neighbors',
          entity_ids: ['3535400', 'dev-006'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-18T09:31:10Z'
        },
        {
          id: 'ev-006-3',
          claim: 'Second cash-equivalent authorization (3535412, $1,595.00) followed 8 minutes later.',
          source: 'graph',
          ref: 'card_window(C14209-K1, 1h)',
          entity_ids: ['3535412'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-18T09:32:00Z'
        }
      ],
      similar_prior_cases: ['CC-1205', 'CC-1944'],
      summary: 'Confirmed Account Takeover (ATO). Threat actor leveraged compromised account credentials behind an anonymous proxy to alter profile parameters and execute two rapid cash-equivalent transfers totaling $3,190.00. Because exposure exceeds $2,500, Policy 2 mandates L2 managerial sign-off for card blocking. Total exposure exceeds $1,000 threshold, mandating L2 SAR filing under Policy 3a and FinCEN ATO advisory.',
      written_to_graph: true,
      graph_case_id: 'GC-HHG-006'
    },
    evidence_requests: [],
    next_best_actions: {
      initial: [
        {
          id: 'act-006-init-1',
          action: 'BLOCK_CARD',
          route: 'L2',
          reason: 'R2: Customer confirmed account takeover; exposure ($3,190.00) > $2,500 routes to L2 approval.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-006-init-2',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Confirmed ATO incident with probability = 0.96.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-006-init-3',
          action: 'FILE_REPORT',
          route: 'L2',
          reason: 'Policy 3a: Confirmed ATO with exposure ($3,190.00) > $1,000 requires SAR filing.',
          executed: false,
          status: 'pending_approval'
        }
      ],
      final: [
        {
          id: 'act-006-fin-1',
          action: 'BLOCK_CARD',
          route: 'L2',
          reason: 'R2: Customer confirmed account takeover; exposure ($3,190.00) > $2,500 routes to L2 approval.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-006-fin-2',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Confirmed ATO incident with probability = 0.96.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-006-fin-3',
          action: 'FILE_REPORT',
          route: 'L2',
          reason: 'Policy 3a: Confirmed ATO with exposure ($3,190.00) > $1,000 requires SAR filing.',
          executed: false,
          status: 'pending_approval'
        }
      ],
      what_changed: 'nothing'
    },
    sar: {
      file: true,
      reason: 'Confirmed Account Takeover with exposure of $3,190.00 exceeding $1,000 threshold under Policy 3a and FinCEN ATO guidance.',
      narrative: 'This Suspicious Activity Report describes an Account Takeover (ATO) attack against Customer C14209 and associated Card C14209-K1. On November 18, 2016, unauthorized login credentials were used via an anonymous proxy to alter profile settings and execute two consecutive online cash-equivalent authorizations (TransactionIDs 3535400 and 3535412) totaling $3,190.00 within an eight-minute interval. The genuine account holder contacted customer service to repudiate both charges and reported receipt of unexpected security alteration notifications. Fraud operations initiated immediate containment and revoked digital banking access. Total illicit exposure is $3,190.00, meeting mandatory SAR filing criteria.',
      subjects: ['C14209', 'C14209-K1', '3535400', '3535412', 'IP_PROXY:ANONYMOUS'],
      total_amount_usd: 3190.00,
      activity_dates: ['2016-11-18', '2016-11-18']
    },
    stop_reason: 'Stopping Rule 1: High certainty boundary (p=0.96 >= 0.85) corroborated by customer dispute and proxy graph records.',
    tool_calls: 7,
    tokens: 4120,
    latency_s: 3.10,
    subgraph: {
      nodes: [
        { id: 'C14209', type: 'customer', label: 'Customer C14209', details: { ato_flag: true } },
        { id: 'C14209-K1', type: 'card', label: 'Card C14209-K1', details: { card1: 16008 } },
        { id: '3535400', type: 'transaction', label: 'Txn 3535400', sublabel: '$1,595.00', isFlagged: true, details: { amt: 1595.00, channel: 'online' } },
        { id: '3535412', type: 'transaction', label: 'Txn 3535412', sublabel: '$1,595.00', details: { amt: 1595.00, channel: 'online' } },
        { id: 'dev-006', type: 'device', label: 'Win7 / Anon Proxy', details: { id_23: 'IP_PROXY:ANONYMOUS', id_30: 'Windows 7' } }
      ],
      edges: [
        { id: 'e-601', source: 'C14209', target: 'C14209-K1', type: 'OWNS', label: 'OWNS' },
        { id: 'e-602', source: 'C14209-K1', target: '3535400', type: 'MADE', label: 'MADE' },
        { id: 'e-603', source: 'C14209-K1', target: '3535412', type: 'MADE', label: 'MADE' },
        { id: 'e-604', source: '3535400', target: '3535412', type: 'NEXT', temporalNext: true, label: 'NEXT (8m)' },
        { id: 'e-605', source: '3535400', target: 'dev-006', type: 'FROM_DEVICE', label: 'FROM_DEVICE' }
      ]
    },
    affected_txns_detail: [
      { txn_id: '3535400', amount_usd: 1595.00, disguised_amt: 1594.992, timestamp: '2016-11-18T09:22:00Z', product_cd: 'W', channel: 'online', status: 'flagged' },
      { txn_id: '3535412', amount_usd: 1595.00, disguised_amt: 1595.004, timestamp: '2016-11-18T09:30:00Z', product_cd: 'W', channel: 'online', status: 'affected' }
    ],
    prior_cases_detail: [
      {
        case_id: 'CC-1205',
        opened_at: '2016-08-22T10:00:00Z',
        closed_at: '2016-08-22T12:00:00Z',
        outcome: 'confirmed_fraud',
        pattern: 'account_takeover',
        similarity_score: 0.93,
        shared_elements: ['IP_PROXY:ANONYMOUS', 'password_reset_trigger', 'cash_equivalent_burst'],
        notes: 'ATO through credential stuffing; anonymous proxy used to drain funds. L2 block executed.',
        actions_taken: 'BLOCK_CARD|FILE_REPORT',
        exposure_usd: 2850.00
      }
    ],
    timeline: [
      { step_number: 1, name: 'Intake Trigger', phase: 'trigger', timestamp: '2016-11-18T09:30:00Z', status: 'completed', description: 'Customer dispute received: unauthorized transfers and security alerts.', output_summary: 'ATO customer dispute intake.' },
      { step_number: 2, name: 'Evidence Gathering', phase: 'evidence_gather', timestamp: '2016-11-18T09:30:30Z', status: 'completed', tool_invoked: 'device_neighbors + card_window', description: 'Identified anonymous proxy and two cash-equivalent authorizations.', output_summary: 'Found proxy IP and $3,190 exposure.' },
      { step_number: 3, name: 'Policy Evaluation', phase: 'final_policy', timestamp: '2016-11-18T09:31:00Z', status: 'completed', description: 'Applied R2 and Policy 3a. Exposure $3,190 > $2,500 requires L2 block & L2 SAR.', output_summary: 'L2 actions routed to Approval Queue.' },
      { step_number: 4, name: 'Graph Writeback', phase: 'writeback', timestamp: '2016-11-18T09:32:00Z', status: 'completed', tool_invoked: 'write_case', description: 'Case persisted: GC-HHG-006.', output_summary: 'Graph memory updated.' }
    ],
    uncertainty: {
      evidence_count: 3,
      independent_sources: 2,
      has_conflicts: false,
      confidence_level: 'High'
    }
  },
  {
    case_id: 'HHG-007',
    opened_at: '2016-11-19T13:40:00Z',
    trigger_type: 'risk_score',
    trigger_text: 'Model risk_score alert (0.79) on Card C05391-K1 at region 388.0 (flagged txn 3539100)',
    flagged_txn_id: '3539100',
    card_id: 'C05391-K1',
    customer_id: 'C05391',
    risk_score: 0.79,
    case: {
      status: 'closed_fraud',
      verdict: 'fraud',
      fraud_probability: 0.91,
      raw_probability: 0.85,
      calibrated_probability: 0.91,
      pattern: 'out_of_region_use',
      pattern_description: '',
      affected_txn_ids: ['3539100', '3539115'],
      first_suspicious_txn_id: '3539100',
      connected_card_ids: [],
      connected_device_profiles: [],
      exposure_usd: 1840.00,
      evidence: [
        {
          id: 'ev-007-1',
          claim: 'Transaction 3539100 ($920.00, in_person) occurred in billing region 388.0 exactly 15 minutes after a legitimate grocery purchase ($45.20) in home region 299.0.',
          source: 'graph',
          ref: 'card_window(C05391-K1, 2h)',
          entity_ids: ['3539100', '388.0', '299.0'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-19T13:40:10Z'
        },
        {
          id: 'ev-007-2',
          claim: 'Geographic distance between region 299.0 and 388.0 exceeds 1,200 miles, establishing an impossible physical velocity violation.',
          source: 'graph',
          ref: 'region_cluster(388.0, 2h)',
          entity_ids: ['388.0', '299.0'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-19T13:40:35Z'
        },
        {
          id: 'ev-007-3',
          claim: 'Customer confirmed they are physically present at home in region 299.0 and card was skimmed or cloned.',
          source: 'customer',
          ref: 'evidence_requests[0]',
          entity_ids: ['C05391'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-19T13:45:00Z'
        }
      ],
      similar_prior_cases: ['CC-0955', 'CC-1120'],
      summary: 'Confirmed counterfeit card clone attack with out-of-region in-person use. A card-present charge occurred in region 388.0 fifteen minutes after an authentic purchase in home region 299.0 (impossible velocity). Cardholder verified physical possession of genuine card in region 299.0. Under Policy R2, card was blocked under L1 approval (exposure $1,840.00 <= $2,500) and SAR filed under Policy 3a.',
      written_to_graph: true,
      graph_case_id: 'GC-HHG-007'
    },
    evidence_requests: [
      {
        id: 'req-007',
        type: 'customer_validation',
        asked_after_step: 3,
        assumed_response: 'Customer confirms they are in home region 299.0 with physical card; denied all charges in region 388.0.',
        simulation_rule: 'Impossible velocity pattern with concurrent legitimate home charge triggers customer repudiation assumption.',
        asked_at: '2016-11-19T13:41:00Z',
        response_status: 'received'
      }
    ],
    next_best_actions: {
      initial: [
        {
          id: 'act-007-init-1',
          action: 'VERIFY_WITH_CUSTOMER',
          route: 'auto',
          reason: 'R1: Out-of-region velocity alert requires customer verification before blocking.',
          executed: true,
          status: 'executed'
        }
      ],
      final: [
        {
          id: 'act-007-fin-1',
          action: 'BLOCK_CARD',
          route: 'L1',
          reason: 'R2: Customer repudiated cloned card transactions; exposure ($1,840.00) <= $2,500 routes to L1 approval.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-007-fin-2',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Confirmed out-of-region counterfeit card fraud.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-007-fin-3',
          action: 'FILE_REPORT',
          route: 'L2',
          reason: 'Policy 3a: Confirmed counterfeit card fraud with exposure ($1,840.00) > $1,000.',
          executed: false,
          status: 'pending_approval'
        }
      ],
      what_changed: 'Customer confirmed card cloning; recommendation transitioned from verification to L1 BLOCK_CARD and L2 FILE_REPORT.'
    },
    sar: {
      file: true,
      reason: 'Confirmed counterfeit card cloning with impossible physical velocity exceeding $1,000 threshold ($1,840.00).',
      narrative: 'This Suspicious Activity Report documents counterfeit card cloning activity on Card C05391-K1 issued to Customer C05391. On November 19, 2016, an authentic card-present transaction was conducted in the cardholder home billing region 299.0. Exactly fifteen minutes later, two unauthorized in-person retail authorizations (TransactionIDs 3539100 and 3539115) totaling $1,840.00 were presented in billing region 388.0, located over 1,200 miles away. The temporal and spatial impossibility confirms magnetic stripe skimming or cloning. Customer confirmed continuous physical custody of the legitimate card in region 299.0. The card was terminated and total unauthorized exposure of $1,840.00 reported to FinCEN.',
      subjects: ['C05391', 'C05391-K1', '3539100', '3539115', 'Region 388.0'],
      total_amount_usd: 1840.00,
      activity_dates: ['2016-11-19', '2016-11-19']
    },
    stop_reason: 'Stopping Rule 2: Customer verification settled physical possession and repudiation of cloned charges.',
    tool_calls: 6,
    tokens: 3750,
    latency_s: 2.72,
    subgraph: {
      nodes: [
        { id: 'C05391', type: 'customer', label: 'Customer C05391', details: { home_region: 299.0 } },
        { id: 'C05391-K1', type: 'card', label: 'Card C05391-K1', details: { card1: 14112 } },
        { id: '3539080', type: 'transaction', label: 'Txn 3539080', sublabel: '$45.20 (Home)', details: { amt: 45.20, region: 299.0, channel: 'in_person' } },
        { id: '3539100', type: 'transaction', label: 'Txn 3539100', sublabel: '$920.00 (Flagged)', isFlagged: true, details: { amt: 920.00, region: 388.0, channel: 'in_person' } },
        { id: '3539115', type: 'transaction', label: 'Txn 3539115', sublabel: '$920.00', details: { amt: 920.00, region: 388.0, channel: 'in_person' } },
        { id: 'reg-388', type: 'region', label: 'Region 388.0', details: { distance_miles: 1200 } }
      ],
      edges: [
        { id: 'e-701', source: 'C05391', target: 'C05391-K1', type: 'OWNS', label: 'OWNS' },
        { id: 'e-702', source: 'C05391-K1', target: '3539080', type: 'MADE', label: 'MADE' },
        { id: 'e-703', source: 'C05391-K1', target: '3539100', type: 'MADE', label: 'MADE' },
        { id: 'e-704', source: 'C05391-K1', target: '3539115', type: 'MADE', label: 'MADE' },
        { id: 'e-705', source: '3539100', target: 'reg-388', type: 'BILLED_IN', label: 'BILLED_IN' },
        { id: 'e-706', source: '3539080', target: '3539100', type: 'NEXT', temporalNext: true, label: 'IMPOSSIBLE (15m/1200mi)' }
      ]
    },
    affected_txns_detail: [
      { txn_id: '3539100', amount_usd: 920.00, disguised_amt: 919.998, timestamp: '2016-11-19T13:35:00Z', product_cd: 'W', channel: 'in_person', billing_region: '388.0', status: 'flagged', risk_score: 0.79 },
      { txn_id: '3539115', amount_usd: 920.00, disguised_amt: 920.003, timestamp: '2016-11-19T13:38:00Z', product_cd: 'W', channel: 'in_person', billing_region: '388.0', status: 'affected' }
    ],
    prior_cases_detail: [
      {
        case_id: 'CC-0955',
        opened_at: '2016-08-18T14:00:00Z',
        closed_at: '2016-08-18T16:30:00Z',
        outcome: 'confirmed_fraud',
        pattern: 'out_of_region_use',
        similarity_score: 0.94,
        shared_elements: ['impossible_velocity', 'region_388', 'channel: in_person'],
        notes: 'Card cloning with dual-presence velocity violation. Blocked immediately upon customer denial.',
        actions_taken: 'BLOCK_CARD|FILE_REPORT',
        exposure_usd: 1650.00
      }
    ],
    timeline: [
      { step_number: 1, name: 'Intake Trigger', phase: 'trigger', timestamp: '2016-11-19T13:40:00Z', status: 'completed', description: 'Risk alert (0.79) for out-of-region transaction in region 388.0.', output_summary: 'Out-of-region intake.' },
      { step_number: 2, name: 'Evidence Gathering', phase: 'evidence_gather', timestamp: '2016-11-19T13:40:30Z', status: 'completed', tool_invoked: 'card_window', description: 'Found legitimate charge 15 mins prior in home region 299.0.', output_summary: 'Impossible physical velocity detected.' },
      { step_number: 3, name: 'Initial Assessment', phase: 'initial_assessment', timestamp: '2016-11-19T13:41:00Z', status: 'completed', description: 'Policy R1: verification sent to cardholder.', output_summary: 'VERIFY_WITH_CUSTOMER recommended.' },
      { step_number: 4, name: 'Evidence Request', phase: 'evidence_request', timestamp: '2016-11-19T13:42:00Z', status: 'completed', description: 'Cardholder confirmed at home; repudiated out-of-region charges.', output_summary: 'Customer repudiation received.' },
      { step_number: 5, name: 'Final Policy Reassessment', phase: 'final_policy', timestamp: '2016-11-19T13:46:00Z', status: 'completed', description: 'Policy R2: L1 BLOCK_CARD and L2 FILE_REPORT emitted.', output_summary: 'Final actions emitted.' },
      { step_number: 6, name: 'Graph Writeback', phase: 'writeback', timestamp: '2016-11-19T13:48:00Z', status: 'completed', tool_invoked: 'write_case', description: 'Case persisted: GC-HHG-007.', output_summary: 'Memory updated.' }
    ],
    uncertainty: {
      evidence_count: 3,
      independent_sources: 2,
      has_conflicts: false,
      confidence_level: 'High'
    }
  },
  {
    case_id: 'HHG-008',
    opened_at: '2016-11-20T16:15:00Z',
    trigger_type: 'risk_score',
    trigger_text: 'Model risk_score alert (0.78) on Card C06381-K1 at TransactionID 3544210',
    flagged_txn_id: '3544210',
    card_id: 'C06381-K1',
    customer_id: 'C06381',
    risk_score: 0.78,
    case: {
      status: 'closed_fraud',
      verdict: 'fraud',
      fraud_probability: 0.92,
      raw_probability: 0.86,
      calibrated_probability: 0.92,
      pattern: 'card_not_present_new_device',
      pattern_description: '',
      affected_txn_ids: ['3544210', '3544225', '3544238'],
      first_suspicious_txn_id: '3544210',
      connected_card_ids: [],
      connected_device_profiles: ['Windows 10 | Firefox 50.0 | id_15: New'],
      exposure_usd: 1475.00,
      evidence: [
        {
          id: 'ev-008-1',
          claim: 'Transaction 3544210 executed online from newly observed device profile (Win10 / Firefox 50.0, id_15 = New).',
          source: 'graph',
          ref: 'device_neighbors',
          entity_ids: ['3544210', 'dev-008'],
          counter_evidence: false,
          confidence_impact: 'medium',
          timestamp: '2016-11-20T16:15:05Z'
        },
        {
          id: 'ev-008-2',
          claim: 'Cardholder explicitly denied authorizing charges during customer verification.',
          source: 'customer',
          ref: 'evidence_requests[0]',
          entity_ids: ['C06381'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-20T16:20:15Z'
        },
        {
          id: 'ev-008-3',
          claim: 'Three consecutive high-value e-commerce orders ($495.00, $490.00, $490.00) completed in under 40 minutes.',
          source: 'graph',
          ref: 'card_window(C06381-K1, 1h)',
          entity_ids: ['3544210', '3544225', '3544238'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-20T16:21:00Z'
        }
      ],
      similar_prior_cases: ['CC-1076', 'CC-1404'],
      summary: 'Card-Not-Present fraud from a new device profile. Following initial risk alert (0.78), cardholder verification was initiated. Cardholder repudiated all transactions. GSQL card_window traversal revealed three consecutive authorizations totaling $1,475.00 within 40 minutes. Under Policy R2, card was blocked under L1 route and SAR filed under Policy 3a ($1,475.00 > $1,000).',
      written_to_graph: true,
      graph_case_id: 'GC-HHG-008'
    },
    evidence_requests: [
      {
        id: 'req-008',
        type: 'customer_validation',
        asked_after_step: 3,
        assumed_response: 'Customer confirms they did not authorize the online orders and do not recognize the Windows 10 device.',
        simulation_rule: 'New device burst archetype; customer denies transaction authorization.',
        asked_at: '2016-11-20T16:16:00Z',
        response_status: 'received'
      }
    ],
    next_best_actions: {
      initial: [
        {
          id: 'act-008-init-1',
          action: 'VERIFY_WITH_CUSTOMER',
          route: 'auto',
          reason: 'R1: Moderate initial risk score on new device requires verification before blocking.',
          executed: true,
          status: 'executed'
        }
      ],
      final: [
        {
          id: 'act-008-fin-1',
          action: 'BLOCK_CARD',
          route: 'L1',
          reason: 'R2: Customer denied transactions; exposure ($1,475.00) <= $2,500 routes to L1 approval.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-008-fin-2',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'Policy 3a: Confirmed CNP new device fraud.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-008-fin-3',
          action: 'FILE_REPORT',
          route: 'L2',
          reason: 'Policy 3a: Confirmed fraud with total exposure ($1,475.00) > $1,000 requires SAR filing.',
          executed: false,
          status: 'pending_approval'
        }
      ],
      what_changed: 'Customer repudiation transitioned recommendation from verification to L1 BLOCK_CARD and L2 FILE_REPORT.'
    },
    sar: {
      file: true,
      reason: 'Confirmed CNP new device fraud with exposure exceeding $1,000 threshold ($1,475.00).',
      narrative: 'This Suspicious Activity Report details unauthorized Card-Not-Present (CNP) transactions on Card C06381-K1 belonging to Customer C06381. On November 20, 2016, an unauthorized online session was established via a newly observed Windows 10/Firefox profile. Within 40 minutes, three consecutive online authorizations totaling $1,475.00 (TransactionIDs 3544210, 3544225, 3544238) were placed at online merchant gateways. When queried, the cardholder denied authorizing the transactions or possessing the device. Financial institution fraud operations blocked the card under Policy R2 and initiated chargeback recovery. Total unauthorized exposure is $1,475.00, satisfying FinCEN mandatory reporting thresholds.',
      subjects: ['C06381', 'C06381-K1', '3544210', '3544225', '3544238', 'Win10 / Firefox 50.0'],
      total_amount_usd: 1475.00,
      activity_dates: ['2016-11-20', '2016-11-20']
    },
    stop_reason: 'Stopping Rule 2: Customer verification resolved alert through explicit repudiation.',
    tool_calls: 6,
    tokens: 3890,
    latency_s: 2.80,
    subgraph: {
      nodes: [
        { id: 'C06381', type: 'customer', label: 'Customer C06381', details: { card_count: 1 } },
        { id: 'C06381-K1', type: 'card', label: 'Card C06381-K1', details: { card1: 15022 } },
        { id: '3544210', type: 'transaction', label: 'Txn 3544210', sublabel: '$495.00', isFlagged: true, details: { amt: 495.00 } },
        { id: '3544225', type: 'transaction', label: 'Txn 3544225', sublabel: '$490.00', details: { amt: 490.00 } },
        { id: '3544238', type: 'transaction', label: 'Txn 3544238', sublabel: '$490.00', details: { amt: 490.00 } },
        { id: 'dev-008', type: 'device', label: 'Win10 / FF 50 (New)', details: { id_15: 'New' } }
      ],
      edges: [
        { id: 'e-801', source: 'C06381', target: 'C06381-K1', type: 'OWNS', label: 'OWNS' },
        { id: 'e-802', source: 'C06381-K1', target: '3544210', type: 'MADE', label: 'MADE' },
        { id: 'e-803', source: 'C06381-K1', target: '3544225', type: 'MADE', label: 'MADE' },
        { id: 'e-804', source: 'C06381-K1', target: '3544238', type: 'MADE', label: 'MADE' },
        { id: 'e-805', source: '3544210', target: 'dev-008', type: 'FROM_DEVICE', label: 'FROM_DEVICE' }
      ]
    },
    affected_txns_detail: [
      { txn_id: '3544210', amount_usd: 495.00, disguised_amt: 494.991, timestamp: '2016-11-20T16:05:00Z', product_cd: 'C', channel: 'online', status: 'flagged', risk_score: 0.78 },
      { txn_id: '3544225', amount_usd: 490.00, disguised_amt: 490.004, timestamp: '2016-11-20T16:22:00Z', product_cd: 'C', channel: 'online', status: 'affected' },
      { txn_id: '3544238', amount_usd: 490.00, disguised_amt: 489.997, timestamp: '2016-11-20T16:38:00Z', product_cd: 'C', channel: 'online', status: 'affected' }
    ],
    prior_cases_detail: [
      {
        case_id: 'CC-1076',
        opened_at: '2016-08-25T11:00:00Z',
        closed_at: '2016-08-25T13:40:00Z',
        outcome: 'confirmed_fraud',
        pattern: 'card_not_present_new_device',
        similarity_score: 0.93,
        shared_elements: ['id_15: New', 'ProductCD: C', 'e-commerce_burst'],
        notes: 'CNP new device fraud with sequential $490 authorizations.',
        actions_taken: 'BLOCK_CARD|FILE_REPORT',
        exposure_usd: 1470.00
      }
    ],
    timeline: [
      { step_number: 1, name: 'Intake Trigger', phase: 'trigger', timestamp: '2016-11-20T16:15:00Z', status: 'completed', description: 'Risk alert (0.78) for txn 3544210.', output_summary: 'CNP new device intake.' },
      { step_number: 2, name: 'Evidence Gathering', phase: 'evidence_gather', timestamp: '2016-11-20T16:15:20Z', status: 'completed', tool_invoked: 'device_neighbors + card_window', description: 'Confirmed new device profile and 3 consecutive orders.', output_summary: 'Burst of 3 txns identified.' },
      { step_number: 3, name: 'Initial Assessment', phase: 'initial_assessment', timestamp: '2016-11-20T16:15:50Z', status: 'completed', description: 'Policy R1: customer verification sent.', output_summary: 'VERIFY_WITH_CUSTOMER recommended.' },
      { step_number: 4, name: 'Evidence Request', phase: 'evidence_request', timestamp: '2016-11-20T16:16:00Z', status: 'completed', description: 'Customer repudiated all charges.', output_summary: 'Repudiation logged.' },
      { step_number: 5, name: 'Final Reassessment', phase: 'final_policy', timestamp: '2016-11-20T16:22:00Z', status: 'completed', description: 'Policy R2: L1 BLOCK_CARD and L2 FILE_REPORT emitted.', output_summary: 'Final actions emitted.' },
      { step_number: 6, name: 'Graph Writeback', phase: 'writeback', timestamp: '2016-11-20T16:24:00Z', status: 'completed', tool_invoked: 'write_case', description: 'Persisted to graph: GC-HHG-008.', output_summary: 'Memory updated.' }
    ],
    uncertainty: {
      evidence_count: 3,
      independent_sources: 2,
      has_conflicts: false,
      confidence_level: 'High'
    }
  },
  {
    case_id: 'HHG-009',
    opened_at: '2016-11-21T11:00:00Z',
    trigger_type: 'risk_score',
    trigger_text: 'Model risk_score alert (0.71) on Card C09823-K1 at TransactionID 3548900',
    flagged_txn_id: '3548900',
    card_id: 'C09823-K1',
    customer_id: 'C09823',
    risk_score: 0.71,
    case: {
      status: 'closed_fraud',
      verdict: 'fraud',
      fraud_probability: 0.95,
      raw_probability: 0.90,
      calibrated_probability: 0.95,
      pattern: 'undocumented',
      pattern_description: 'Coordinated sub-threshold structuring attack: four consecutive online transactions executed within 35 minutes, each precisely formatted at $492.50 to evade the automated $500.00 reporting threshold.',
      affected_txn_ids: ['3548900', '3548908', '3548915', '3548922'],
      first_suspicious_txn_id: '3548900',
      connected_card_ids: [],
      connected_device_profiles: ['Macintosh | Safari 10.0 | Anonymous Proxy'],
      exposure_usd: 1970.00,
      evidence: [
        {
          id: 'ev-009-1',
          claim: 'Four consecutive online transactions executed between 10:25 and 11:00 UTC, each precisely $492.50 (sub-threshold structuring).',
          source: 'graph',
          ref: 'discovery/structuring_under_threshold.gsql',
          entity_ids: ['3548900', '3548908', '3548915', '3548922'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-21T11:00:10Z'
        },
        {
          id: 'ev-009-2',
          claim: 'Matches undocumented sub-pattern 2 identified in closed historical case CC-0009.',
          source: 'document',
          ref: 'Similar closed case CC-0009',
          entity_ids: ['CC-0009'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-21T11:00:30Z'
        },
        {
          id: 'ev-009-3',
          claim: 'Transactions originated via anonymous residential proxy to distribute gift card redemptions.',
          source: 'graph',
          ref: 'device_neighbors',
          entity_ids: ['dev-009'],
          counter_evidence: false,
          confidence_impact: 'high',
          timestamp: '2016-11-21T11:01:00Z'
        }
      ],
      similar_prior_cases: ['CC-0009'],
      summary: 'Novel coordinated structuring pattern detected. The threat actor initiated four identical online charges of $492.50 within a 35-minute window, systematically structured just below the bank\'s $500.00 internal monitoring ceiling. Under Policy R9 (undocumented pattern discovery), the agent did not force a standard category, instead describing the typology explicitly, emitting L1 card blocking, L2 SAR filing, and escalating to human fraud analyst.',
      written_to_graph: true,
      graph_case_id: 'GC-HHG-009'
    },
    evidence_requests: [],
    next_best_actions: {
      initial: [
        {
          id: 'act-009-init-1',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'R9: Novel undocumented structuring pattern detected; case creation required.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-009-init-2',
          action: 'BLOCK_CARD',
          route: 'L1',
          reason: 'R9: Severe coordinated structuring with exposure ($1,970.00) <= $2,500 routes to L1 block.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-009-init-3',
          action: 'FILE_REPORT',
          route: 'L2',
          reason: 'R9 & Policy 3a: Coordinated abuse with exposure ($1,970.00) > $1,000 mandates SAR.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-009-init-4',
          action: 'ESCALATE_TO_ANALYST',
          route: 'auto',
          reason: 'R9: Undocumented structuring typology requires human investigator review.',
          executed: true,
          status: 'executed'
        }
      ],
      final: [
        {
          id: 'act-009-fin-1',
          action: 'CREATE_CASE',
          route: 'auto',
          reason: 'R9: Novel undocumented structuring pattern detected; case creation required.',
          executed: true,
          status: 'executed'
        },
        {
          id: 'act-009-fin-2',
          action: 'BLOCK_CARD',
          route: 'L1',
          reason: 'R9: Severe coordinated structuring with exposure ($1,970.00) <= $2,500 routes to L1 block.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-009-fin-3',
          action: 'FILE_REPORT',
          route: 'L2',
          reason: 'R9 & Policy 3a: Coordinated abuse with exposure ($1,970.00) > $1,000 mandates SAR.',
          executed: false,
          status: 'pending_approval'
        },
        {
          id: 'act-009-fin-4',
          action: 'ESCALATE_TO_ANALYST',
          route: 'auto',
          reason: 'R9: Undocumented structuring typology requires human investigator review.',
          executed: true,
          status: 'executed'
        }
      ],
      what_changed: 'nothing'
    },
    sar: {
      file: true,
      reason: 'Coordinated structuring under $500 threshold with total exposure of $1,970.00 under Policy R9 and Policy 3a.',
      narrative: 'This Suspicious Activity Report details a structured online payment evasion scheme on Card C09823-K1 belonging to Customer C09823. On November 21, 2016, four identical authorizations of $492.50 each (TransactionIDs 3548900, 3548908, 3548915, 3548922) were executed within 35 minutes via an anonymous proxy service. The repeated transaction amount of $492.50 demonstrates deliberate structuring designed to circumvent financial institution monitoring rules set at $500.00. The activity matches undocumented historical typology CC-0009. The total illicit amount structured is $1,970.00. Under Policy R9 and Bank Secrecy Act guidelines, the card was terminated and full incident documentation is escalated to law enforcement.',
      subjects: ['C09823', 'C09823-K1', '3548900', '3548908', '3548915', '3548922', 'IP_PROXY:ANONYMOUS'],
      total_amount_usd: 1970.00,
      activity_dates: ['2016-11-21', '2016-11-21']
    },
    stop_reason: 'Stopping Rule 1: High certainty boundary (p=0.95 >= 0.85) corroborated by 3 independent graph and historical records.',
    tool_calls: 7,
    tokens: 4180,
    latency_s: 3.15,
    subgraph: {
      nodes: [
        { id: 'C09823', type: 'customer', label: 'Customer C09823', details: { risk: 'high' } },
        { id: 'C09823-K1', type: 'card', label: 'Card C09823-K1', details: { card1: 17822 } },
        { id: '3548900', type: 'transaction', label: 'Txn 3548900', sublabel: '$492.50', isFlagged: true, details: { amt: 492.50 } },
        { id: '3548908', type: 'transaction', label: 'Txn 3548908', sublabel: '$492.50', details: { amt: 492.50 } },
        { id: '3548915', type: 'transaction', label: 'Txn 3548915', sublabel: '$492.50', details: { amt: 492.50 } },
        { id: '3548922', type: 'transaction', label: 'Txn 3548922', sublabel: '$492.50', details: { amt: 492.50 } },
        { id: 'dev-009', type: 'device', label: 'Mac / Anon Proxy', details: { id_23: 'IP_PROXY:ANONYMOUS' } }
      ],
      edges: [
        { id: 'e-901', source: 'C09823', target: 'C09823-K1', type: 'OWNS', label: 'OWNS' },
        { id: 'e-902', source: 'C09823-K1', target: '3548900', type: 'MADE', label: 'MADE' },
        { id: 'e-903', source: 'C09823-K1', target: '3548908', type: 'MADE', label: 'MADE' },
        { id: 'e-904', source: 'C09823-K1', target: '3548915', type: 'MADE', label: 'MADE' },
        { id: 'e-905', source: 'C09823-K1', target: '3548922', type: 'MADE', label: 'MADE' },
        { id: 'e-906', source: '3548900', target: 'dev-009', type: 'FROM_DEVICE', label: 'FROM_DEVICE' }
      ]
    },
    affected_txns_detail: [
      { txn_id: '3548900', amount_usd: 492.50, disguised_amt: 492.498, timestamp: '2016-11-21T10:25:00Z', product_cd: 'C', channel: 'online', status: 'flagged', risk_score: 0.71 },
      { txn_id: '3548908', amount_usd: 492.50, disguised_amt: 492.502, timestamp: '2016-11-21T10:36:00Z', product_cd: 'C', channel: 'online', status: 'affected' },
      { txn_id: '3548915', amount_usd: 492.50, disguised_amt: 492.499, timestamp: '2016-11-21T10:48:00Z', product_cd: 'C', channel: 'online', status: 'affected' },
      { txn_id: '3548922', amount_usd: 492.50, disguised_amt: 492.501, timestamp: '2016-11-21T10:59:00Z', product_cd: 'C', channel: 'online', status: 'affected' }
    ],
    prior_cases_detail: [
      {
        case_id: 'CC-0009',
        opened_at: '2016-07-06T12:00:00Z',
        closed_at: '2016-07-06T14:30:00Z',
        outcome: 'confirmed_fraud',
        pattern: 'undocumented',
        similarity_score: 0.96,
        shared_elements: ['structuring_under_500', 'four_rapid_txns', 'anonymous_proxy'],
        notes: 'Undocumented structuring sub-pattern: four online charges just below $500 threshold.',
        actions_taken: 'CREATE_CASE|BLOCK_CARD|FILE_REPORT|ESCALATE_TO_ANALYST',
        exposure_usd: 1968.00
      }
    ],
    timeline: [
      { step_number: 1, name: 'Intake Trigger', phase: 'trigger', timestamp: '2016-11-21T11:00:00Z', status: 'completed', description: 'Model risk alert (0.71) for txn 3548900.', output_summary: 'Structuring trigger intake.' },
      { step_number: 2, name: 'Evidence Gathering', phase: 'evidence_gather', timestamp: '2016-11-21T11:00:15Z', status: 'completed', tool_invoked: 'discovery/structuring_under_threshold', description: 'Detected 4 consecutive txns of $492.50 under $500 threshold.', output_summary: 'Found sub-threshold structuring burst.' },
      { step_number: 3, name: 'Pattern Assessment', phase: 'pattern_detection', timestamp: '2016-11-21T11:00:45Z', status: 'completed', description: 'Matched undocumented pattern sub-type 2; did not force standard label.', output_summary: 'Classified as undocumented structuring.' },
      { step_number: 4, name: 'Policy Execution', phase: 'final_policy', timestamp: '2016-11-21T11:01:00Z', status: 'completed', description: 'Applied Policy R9: emitted CREATE_CASE, BLOCK_CARD (L1), FILE_REPORT (L2), ESCALATE_TO_ANALYST.', output_summary: 'R9 actions emitted.' },
      { step_number: 5, name: 'Graph Writeback', phase: 'writeback', timestamp: '2016-11-21T11:02:00Z', status: 'completed', tool_invoked: 'write_case', description: 'Persisted to graph: GC-HHG-009.', output_summary: 'Memory updated.' }
    ],
    uncertainty: {
      evidence_count: 3,
      independent_sources: 2,
      has_conflicts: false,
      confidence_level: 'High'
    }
  },
  {
    case_id: 'HHG-010',
    opened_at: '2016-11-22T17:40:00Z',
    trigger_type: 'risk_score',
    trigger_text: 'Model risk_score alert (0.76) on Card C04102-K1 for high-ticket airline ticket ($1,850.00)',
    flagged_txn_id: '3553100',
    card_id: 'C04102-K1',
    customer_id: 'C04102',
    risk_score: 0.76,
    case: {
      status: 'closed_legitimate',
      verdict: 'legitimate',
      fraud_probability: 0.06,
      raw_probability: 0.11,
      calibrated_probability: 0.06,
      pattern: 'none',
      pattern_description: '',
      affected_txn_ids: [],
      first_suspicious_txn_id: '',
      connected_card_ids: [],
      connected_device_profiles: [],
      exposure_usd: 0.00,
      evidence: [
        {
          id: 'ev-010-1',
          claim: 'High-dollar authorization ($1,850.00) completed with certified 3D-Secure authentication on airline merchant gateway.',
          source: 'graph',
          ref: 'card_window(C04102-K1, 2h)',
          entity_ids: ['3553100'],
          counter_evidence: true,
          confidence_impact: 'high',
          timestamp: '2016-11-22T17:40:05Z'
        },
        {
          id: 'ev-010-2',
          claim: 'Cardholder confirmed intentional holiday travel booking during customer inquiry.',
          source: 'customer',
          ref: 'evidence_requests[0]',
          entity_ids: ['C04102'],
          counter_evidence: true,
          confidence_impact: 'high',
          timestamp: '2016-11-22T17:44:10Z'
        },
        {
          id: 'ev-010-3',
          claim: 'Purchaser email domain (corporate executive domain) and device fingerprint match account tenure of 4+ years.',
          source: 'graph',
          ref: 'card_baseline(C04102-K1)',
          entity_ids: ['C04102-K1'],
          counter_evidence: true,
          confidence_impact: 'medium',
          timestamp: '2016-11-22T17:45:00Z'
        }
      ],
      similar_prior_cases: ['CC-0026', 'CC-0811'],
      summary: 'Alert triggered purely by transaction magnitude ($1,850.00) on an airline booking. Pursuant to Policy R1, verification was dispatched before taking adverse block action. Cardholder confirmed legitimate family travel booking with full 3DS authorization. Under Policy R3, alert was resolved as legitimate and closed with 0 exposure, preserving customer goodwill.',
      written_to_graph: true,
      graph_case_id: 'GC-HHG-010'
    },
    evidence_requests: [
      {
        id: 'req-010',
        type: 'customer_validation',
        asked_after_step: 3,
        assumed_response: 'Customer confirms authorization of $1,850.00 airline tickets for upcoming holiday travel.',
        simulation_rule: 'High-dollar intended purchase archetype (matches CC-0026); customer confirms authorization.',
        asked_at: '2016-11-22T17:41:00Z',
        response_status: 'received'
      }
    ],
    next_best_actions: {
      initial: [
        {
          id: 'act-010-init-1',
          action: 'VERIFY_WITH_CUSTOMER',
          route: 'auto',
          reason: 'R1: High risk score (0.76) on high-ticket purchase requires verification before card block.',
          executed: true,
          status: 'executed'
        }
      ],
      final: [
        {
          id: 'act-010-fin-1',
          action: 'CLOSE_NO_FRAUD',
          route: 'auto',
          reason: 'R3: Cardholder confirmed authorized airline booking; cleared without card block.',
          executed: true,
          status: 'executed'
        }
      ],
      what_changed: 'Customer confirmed transaction; recommendation transitioned from VERIFY_WITH_CUSTOMER to CLOSE_NO_FRAUD.'
    },
    sar: {
      file: false,
      reason: 'Legitimate cardholder transaction confirmed; SAR not applicable.',
      narrative: '',
      subjects: [],
      total_amount_usd: 0,
      activity_dates: []
    },
    stop_reason: 'Stopping Rule 2: Customer verification confirmed legitimate holiday travel booking.',
    tool_calls: 5,
    tokens: 3100,
    latency_s: 2.15,
    subgraph: {
      nodes: [
        { id: 'C04102', type: 'customer', label: 'Customer C04102', details: { segment: 'wealth' } },
        { id: 'C04102-K1', type: 'card', label: 'Card C04102-K1', details: { card1: 19100 } },
        { id: '3553100', type: 'transaction', label: 'Txn 3553100', sublabel: '$1,850.00 (Airline)', isFlagged: true, details: { amt: 1850.00, '3ds': true } }
      ],
      edges: [
        { id: 'e-1001', source: 'C04102', target: 'C04102-K1', type: 'OWNS', label: 'OWNS' },
        { id: 'e-1002', source: 'C04102-K1', target: '3553100', type: 'MADE', label: 'MADE' }
      ]
    },
    affected_txns_detail: [
      { txn_id: '3553100', amount_usd: 1850.00, disguised_amt: 1849.991, timestamp: '2016-11-22T17:35:00Z', product_cd: 'W', channel: 'online', status: 'flagged', risk_score: 0.76 }
    ],
    prior_cases_detail: [
      {
        case_id: 'CC-0026',
        opened_at: '2016-07-10T14:00:00Z',
        closed_at: '2016-07-10T15:20:00Z',
        outcome: 'cleared',
        pattern: 'none',
        similarity_score: 0.94,
        shared_elements: ['airline_ticket', 'amount_bracket: >$1500', '3ds_verified'],
        notes: 'High-dollar airline purchase verified by cardholder; closed with no fraud.',
        actions_taken: 'VERIFY_WITH_CUSTOMER|CLOSE_NO_FRAUD',
        exposure_usd: 0.00
      }
    ],
    timeline: [
      { step_number: 1, name: 'Intake Trigger', phase: 'trigger', timestamp: '2016-11-22T17:40:00Z', status: 'completed', description: 'Risk alert (0.76) on $1,850.00 airline charge.', output_summary: 'High-ticket intake.' },
      { step_number: 2, name: 'Evidence Gathering', phase: 'evidence_gather', timestamp: '2016-11-22T17:40:20Z', status: 'completed', tool_invoked: 'card_baseline', description: 'Matched 4-year tenure and 3DS authentication certificate.', output_summary: 'Clean baseline profile.' },
      { step_number: 3, name: 'Initial Assessment', phase: 'initial_assessment', timestamp: '2016-11-22T17:40:50Z', status: 'completed', description: 'Policy R1: verification sent before blocking.', output_summary: 'VERIFY_WITH_CUSTOMER recommended.' },
      { step_number: 4, name: 'Evidence Request', phase: 'evidence_request', timestamp: '2016-11-22T17:41:00Z', status: 'completed', description: 'Customer confirmed flight booking.', output_summary: 'Customer confirmed.' },
      { step_number: 5, name: 'Final Reassessment', phase: 'final_policy', timestamp: '2016-11-22T17:45:00Z', status: 'completed', description: 'Policy R3 executed: CLOSE_NO_FRAUD.', output_summary: 'Closed as legitimate.' },
      { step_number: 6, name: 'Graph Writeback', phase: 'writeback', timestamp: '2016-11-22T17:46:00Z', status: 'completed', tool_invoked: 'write_case', description: 'Persisted to graph: GC-HHG-010.', output_summary: 'Memory updated.' }
    ],
    uncertainty: {
      evidence_count: 3,
      independent_sources: 2,
      has_conflicts: false,
      confidence_level: 'High'
    }
  }
];
