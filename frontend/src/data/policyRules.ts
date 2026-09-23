/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { PolicyRule } from '../types';

export interface PolicyRuleDefinition {
  id: string;
  name: string;
  condition: string;
  recommendation: string;
  route: 'auto' | 'L1' | 'L2';
  description: string;
  category: 'intake' | 'customer_response' | 'pattern' | 'coordination' | 'guardrail';
  penalties_or_constraints?: string;
}

export const FRAUD_POLICY_RULES: PolicyRuleDefinition[] = [
  {
    id: 'R1',
    name: 'Single-Signal Verification Guard',
    condition: 'Case rests on a single signal (including risk score alone) and probability < 0.70',
    recommendation: 'VERIFY_WITH_CUSTOMER or STEP_UP_AUTH before any card block',
    route: 'auto',
    category: 'intake',
    description: 'Prevents knee-jerk blocks on uncorroborated single alerts. Risk scores are indicators, not verdicts.',
    penalties_or_constraints: 'Blocking a card on a single signal under 0.70 without prior verification is an automatic policy violation.'
  },
  {
    id: 'R2',
    name: 'Customer Denial Response',
    condition: 'Customer denies authorizing the transaction(s)',
    recommendation: 'BLOCK_CARD + CREATE_CASE; add FILE_REPORT if exposure > $1,000 or connects to a shared device/ring',
    route: 'L1',
    category: 'customer_response',
    description: 'When the cardholder actively repudiates the charge, containment is immediate. SAR is triggered if financial or network thresholds are crossed.',
  },
  {
    id: 'R3',
    name: 'Customer Confirmation (Clearing)',
    condition: 'Customer confirms authorizing the transaction(s)',
    recommendation: 'CLOSE_NO_FRAUD; record the confirmation in case record',
    route: 'auto',
    category: 'customer_response',
    description: 'Allows legitimate cardholders to resume normal commerce. Over-blocking hurts customer lifetime value.',
  },
  {
    id: 'R4',
    name: 'No-Reply Timeout Escalation',
    condition: 'No customer reply within 24 hours of verification request',
    recommendation: 'MONITOR_CARD + DECLINE_TRANSACTION for pending authorizations; ESCALATE_TO_ANALYST if exposure > $500',
    route: 'auto',
    category: 'customer_response',
    description: 'SLA enforcement prevents open-ended exposure while avoiding definitive card cancellation prematurely.',
  },
  {
    id: 'R5',
    name: 'Card-Testing Velocity Pattern',
    condition: '>= 3 micro-transactions (< $2.00) within 10 minutes',
    recommendation: 'DECLINE_TRANSACTION + VERIFY_WITH_CUSTOMER; if purchase > $100 already cleared, BLOCK_CARD immediately',
    route: 'L1',
    category: 'pattern',
    description: 'Catches automated bot testing bins before the high-value cash-out wave hits.',
  },
  {
    id: 'R6',
    name: 'Syndicate & Shared Device Linkage',
    condition: 'Device or IP is shared across cards belonging to different cardholders',
    recommendation: 'MONITOR_CONNECTED_CARDS + CREATE_CASE; if confirmed fraud on any connected card, escalate all linked cards',
    route: 'auto',
    category: 'pattern',
    description: 'Traverses TigerGraph multi-hop neighborhoods to identify fraud rings operating across mule or compromised portfolios.',
  },
  {
    id: 'R7',
    name: 'Recurring Baseline Exception',
    condition: 'Transaction matches merchant, amount range (+/- 10%), and billing day of a recurring charge active for >= 3 months',
    recommendation: 'VERIFY_WITH_CUSTOMER without card block, OR ALLOW_TRANSACTION with WARN_CUSTOMER',
    route: 'auto',
    category: 'pattern',
    description: 'Protects critical recurring utilities and subscriptions from false positives.',
  },
  {
    id: 'R8',
    name: 'Evidentiary Conflict Escalation',
    condition: 'Evidence sources disagree (e.g., location matches home but device is novel; or dispute received on authenticated transaction)',
    recommendation: 'ESCALATE_TO_ANALYST; do NOT guess; route to human investigator with confidence rating and specific conflicting claims highlighted',
    route: 'auto',
    category: 'coordination',
    description: 'Uncertainty guardrail: when telemetry conflicts, decision authority yields to human expertise.',
  },
  {
    id: 'R9',
    name: 'Novel / Undocumented Attack Typology',
    condition: 'No existing pattern taxonomy applies, but graph anomalies or behavioral deviations indicate fraud',
    recommendation: 'Describe anomaly explicitly; do NOT force-fit to an existing pattern label; propose action according to exposure thresholds',
    route: 'L1',
    category: 'coordination',
    description: 'Enables adaptation to zero-day attack vectors without shoehorning into false categories.',
  },
  {
    id: 'R10',
    name: 'Customer-Level Mass Block Guardrail',
    condition: 'Action BLOCK_ALL_CARDS proposed',
    recommendation: 'Permitted ONLY if at least two of the customer\'s cards show confirmed fraud OR credentials are confirmed compromised',
    route: 'L2',
    category: 'guardrail',
    description: 'Strict circuit-breaker preventing catastrophic lockout of a customer\'s entire banking relationship on an isolated card alert.',
    penalties_or_constraints: 'Violation incurs strict regulatory and audit non-compliance sanction.'
  }
];

export const ALL_POLICY_RULES: PolicyRule[] = [
  {
    id: 'Rule R1',
    name: 'Single-Signal Verification Guard',
    section: '3.1 Intake Controls',
    trigger_condition: 'Case rests on a single signal (e.g. ML risk score alert alone) and probability < 0.70',
    action_recommendation: 'VERIFY_WITH_CUSTOMER or STEP_UP_AUTH before any card block. Blocking a card on single unverified score is a policy violation.',
    permissible_routes: ['auto'],
    category: 'intake',
    rationale: 'Prevents customer friction and false block churn on isolated model anomalies.',
    benchmark_cases_cited: ['HHG-001', 'HHG-005', 'HHG-008', 'HHG-010', 'HHG-011', 'HHG-013']
  },
  {
    id: 'Rule R2',
    name: 'Customer Repudiated Charge / Confirmed ATO',
    section: '3.2 Customer Response Handling',
    trigger_condition: 'Customer denies authorizing the transaction(s) via SMS/App validation prompt',
    action_recommendation: 'BLOCK_CARD + CREATE_CASE. Add FILE_REPORT if exposure > $1,000 or connected to a shared device ring.',
    permissible_routes: ['L1', 'L2'],
    category: 'customer_response',
    rationale: 'Direct cardholder repudiation provides high evidential weight. Immediate account containment is mandated.',
    benchmark_cases_cited: ['HHG-002', 'HHG-003', 'HHG-006', 'HHG-007', 'HHG-008', 'HHG-014', 'HHG-015', 'HHG-017', 'HHG-019', 'HHG-020']
  },
  {
    id: 'Rule R3',
    name: 'Customer Confirmed Charge (Legitimate Clearing)',
    section: '3.2 Customer Response Handling',
    trigger_condition: 'Customer explicitly confirms authorization of the transaction(s)',
    action_recommendation: 'CLOSE_NO_FRAUD. Record confirmation timestamp into graph memory. Zero loss recorded; zero blocks executed.',
    permissible_routes: ['auto'],
    category: 'customer_response',
    rationale: 'Ensures legitimate commerce is restored without administrative delay.',
    benchmark_cases_cited: ['HHG-004', 'HHG-010', 'HHG-016']
  },
  {
    id: 'Rule R4',
    name: 'Verification Request SLA Timeout',
    section: '3.2 Customer Response Handling',
    trigger_condition: 'No customer reply within 24 hours of verification dispatch',
    action_recommendation: 'MONITOR_CARD + DECLINE_TRANSACTION for pending authorizations. ESCALATE_TO_ANALYST if exposure > $500.',
    permissible_routes: ['auto', 'L1'],
    category: 'customer_response',
    rationale: 'Prevents indefinite exposure while avoiding destructive card cancellation if cardholder is traveling or offline.',
    benchmark_cases_cited: ['HHG-005', 'HHG-018']
  },
  {
    id: 'Rule R5',
    name: 'Card-Testing Velocity Pattern',
    section: '3.3 Graph & Behavioral Patterns',
    trigger_condition: '>= 3 micro-transactions (< $2.00) within 10-minute sliding window',
    action_recommendation: 'Clause 1: DECLINE_TRANSACTION + VERIFY_WITH_CUSTOMER. Clause 2: If transaction > $100 already cleared, BLOCK_CARD immediately.',
    permissible_routes: ['L1'],
    category: 'pattern',
    rationale: 'Interprets bot-driven BIN validation before larger cash-out waves can be executed.',
    benchmark_cases_cited: ['HHG-001', 'HHG-015']
  },
  {
    id: 'Rule R6',
    name: 'Shared Device/IP Multi-Card Ring Discovery',
    section: '3.3 Graph & Behavioral Patterns',
    trigger_condition: 'Device profile (e.g. fingerprint, OS, IP proxy) is shared across cards belonging to multiple distinct cardholders',
    action_recommendation: 'MONITOR_CONNECTED_CARDS + CREATE_CASE. If fraud is confirmed on any connected node, expand investigation to full ring.',
    permissible_routes: ['auto', 'L1', 'L2'],
    category: 'pattern',
    rationale: 'Leverages TigerGraph multi-hop neighborhood discovery to isolate organized criminal syndicates.',
    benchmark_cases_cited: ['HHG-002', 'HHG-014']
  },
  {
    id: 'Rule R7',
    name: 'Recurring Charge with Historical Baseline',
    section: '3.3 Graph & Behavioral Patterns',
    trigger_condition: 'Transaction matches merchant, amount (+/- 10%), and billing day of an established recurring cadence active >= 3 months',
    action_recommendation: 'VERIFY_WITH_CUSTOMER without card block, OR ALLOW_TRANSACTION with WARN_CUSTOMER.',
    permissible_routes: ['auto'],
    category: 'pattern',
    rationale: 'Prevents interruption of essential subscription services, cloud utilities, or loan payments.',
    benchmark_cases_cited: ['HHG-004']
  },
  {
    id: 'Rule R8',
    name: 'Conflicting Evidence or High Uncertainty',
    section: '3.4 Decision Coordination',
    trigger_condition: 'Evidence sources present contradictory signals (e.g. biometric match but IP proxy; or legitimate merchant with anomalous velocity)',
    action_recommendation: 'ESCALATE_TO_ANALYST. Agent is strictly prohibited from guessing or fabricating consensus.',
    permissible_routes: ['auto'],
    category: 'coordination',
    rationale: 'Maintains zero false-positive integrity by escalating ambiguous edge-cases to human fraud specialists.',
    benchmark_cases_cited: ['HHG-005', 'HHG-018']
  },
  {
    id: 'Rule R9',
    name: 'Novel / Undocumented Graph Pattern',
    section: '3.4 Decision Coordination',
    trigger_condition: 'Graph anomaly or behavioral deviation does not fit standard taxonomy (e.g. sub-$500 structuring to evade detection)',
    action_recommendation: 'Describe anomaly explicitly in narrative; do NOT force-fit to existing labels. Route action according to exposure ($2,500 threshold).',
    permissible_routes: ['L1', 'L2'],
    category: 'coordination',
    rationale: 'Supports zero-day typology discovery while maintaining rigorous evidentiary documentation.',
    benchmark_cases_cited: ['HHG-009']
  },
  {
    id: 'Rule R10',
    name: 'Customer-Level Mass Card-Block Guardrail',
    section: '3.5 Catastrophic Risk Guardrails',
    trigger_condition: 'Action BLOCK_ALL_CARDS is proposed for a customer entity',
    action_recommendation: 'Permitted ONLY if at least 2 cards belonging to the customer show confirmed fraud OR credentials confirmed breached. Requires L2 approval.',
    permissible_routes: ['L2'],
    category: 'guardrail',
    rationale: 'Protects the cardholder relationship from total account severance on an isolated compromised card.',
    benchmark_cases_cited: ['HHG-012']
  }
];

export const ROUTE_SPECIFICATIONS = [
  { action: 'ALLOW_TRANSACTION', route: 'auto', authority: 'Agent Direct Execution' },
  { action: 'MONITOR_CARD', route: 'auto', authority: 'Agent Direct Execution' },
  { action: 'MONITOR_CONNECTED_CARDS', route: 'auto', authority: 'Agent Direct Execution' },
  { action: 'WARN_CUSTOMER', route: 'auto', authority: 'Agent Direct Execution' },
  { action: 'VERIFY_WITH_CUSTOMER', route: 'auto', authority: 'Agent Direct Execution' },
  { action: 'STEP_UP_AUTH', route: 'auto', authority: 'Agent Direct Execution' },
  { action: 'GENERATE_REPORT', route: 'auto', authority: 'Agent Direct Execution' },
  { action: 'CREATE_CASE', route: 'auto', authority: 'Agent Direct Execution' },
  { action: 'ESCALATE_TO_ANALYST', route: 'auto', authority: 'Agent Direct Execution' },
  { action: 'CLOSE_NO_FRAUD', route: 'auto', authority: 'Agent Direct Execution' },
  { action: 'DECLINE_TRANSACTION', route: 'L1', authority: 'Senior Investigator / Team Lead Approval' },
  { action: 'BLOCK_CARD', route: 'L1 / L2', authority: 'L1 if exposure <= $2,500; L2 if exposure > $2,500' },
  { action: 'BLOCK_ALL_CARDS', route: 'L2', authority: 'Fraud Operations Manager (R10 mandatory double-card check)' },
  { action: 'FILE_REPORT', route: 'L2', authority: 'BSA / AML Compliance Officer Sign-off' },
];

export const STOPPING_RULES = [
  {
    id: 'RULE_1',
    name: 'High Certainty Boundary',
    condition: 'Probability >= 0.85 or <= 0.15, supported by >= 2 independent pieces of evidence',
    description: 'Investigation terminates because uncertainty is resolved with multi-source corroboration.'
  },
  {
    id: 'RULE_2',
    name: 'Verification Settlement',
    condition: 'A customer or bank verification response settles the core hypothesis (confirm or deny)',
    description: 'Direct testimony from the authorized cardholder supersedes model ambiguity.'
  },
  {
    id: 'RULE_3',
    name: 'Information Exhaustion',
    condition: 'Further permitted evidence steps cannot materially reduce uncertainty; R8 escalation triggered',
    description: 'Prevents wasteful cyclic queries when external data is sparse or unavailable.'
  }
];
