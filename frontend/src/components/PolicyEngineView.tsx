/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { 
  BookOpen, 
  Terminal, 
  Layers, 
  Play, 
  CheckCircle2, 
  Sparkles
} from 'lucide-react';
import { ALL_POLICY_RULES, ROUTE_SPECIFICATIONS } from '../data/policyRules';
import { PolicyRule } from '../types';

const ROUTE_TIERS = [
  {
    route: 'auto',
    label: 'Autonomous Agent Execution',
    authority: 'Deterministic Guard',
    description: 'Safe containment actions, customer verification alerts, report drafts, and case baseline writeback.',
    sla: '< 500ms'
  },
  {
    route: 'L1',
    label: 'Senior Investigator Authorization',
    authority: 'L1 Senior Analyst',
    description: 'Decline authorizations, card blocks <= $2,500, customer repudiation intake, and complex reviews.',
    sla: '< 15 mins'
  },
  {
    route: 'L2',
    label: 'Operations Manager Authorization',
    authority: 'L2 Fraud Ops & BSA Officer',
    description: 'High-exposure card blocks (> $2,500), multi-card customer blocks (R10), device freezes, and SAR filings.',
    sla: '< 2 hours'
  }
];

export const PolicyEngineView: React.FC = () => {
  const [selectedRule, setSelectedRule] = useState<PolicyRule>(ALL_POLICY_RULES[0]);

  // Interactive Scenario Simulator state
  const [testScenario, setTestScenario] = useState<{
    trigger: string;
    exposure: number;
    customerRepudiated: boolean;
    customerConfirmed: boolean;
    timeout24h: boolean;
    cardTestingDetected: boolean;
    purchaseOver100Cleared: boolean;
    sharedDeviceRing: boolean;
    recurringMatch: boolean;
    conflictingEvidence: boolean;
    undocumentedPattern: boolean;
    customerCardCountCompromised: number;
  }>({
    trigger: 'risk_score',
    exposure: 1800,
    customerRepudiated: false,
    customerConfirmed: false,
    timeout24h: false,
    cardTestingDetected: false,
    purchaseOver100Cleared: false,
    sharedDeviceRing: false,
    recurringMatch: false,
    conflictingEvidence: false,
    undocumentedPattern: false,
    customerCardCountCompromised: 1
  });

  // Evaluate simulated rules
  const evaluateSimulator = () => {
    const firedRules: Array<{ rule: string; route: string; action: string; reason: string }> = [];

    if (testScenario.customerCardCountCompromised >= 2 && testScenario.customerRepudiated) {
      firedRules.push({
        rule: 'R10: Mass Card-Block Guardrail',
        route: 'L2',
        action: 'BLOCK_ALL_CARDS',
        reason: '>= 2 customer cards confirmed compromised. Mass customer block authorized under L2 operations manager.'
      });
    }

    if (testScenario.undocumentedPattern) {
      firedRules.push({
        rule: 'R9: Novel / Undocumented Graph Pattern',
        route: testScenario.exposure > 2500 ? 'L2' : 'L1',
        action: 'BLOCK_CARD + FILE_REPORT (L2) + ESCALATE_TO_ANALYST',
        reason: 'Undocumented graph pattern discovered. Typology described explicitly without category shoehorning.'
      });
    }

    if (testScenario.cardTestingDetected) {
      if (testScenario.purchaseOver100Cleared) {
        firedRules.push({
          rule: 'R5 Clause 2: Card Testing Cleared Breach',
          route: 'L1',
          action: 'BLOCK_CARD + DECLINE_TRANSACTION',
          reason: 'A transaction over $100 already cleared after micro-authorizations; card block mandatory.'
        });
      } else {
        firedRules.push({
          rule: 'R5 Clause 1: Card Testing Micro-Burst',
          route: 'L1',
          action: 'DECLINE_TRANSACTION + VERIFY_WITH_CUSTOMER',
          reason: 'Rapid micro-authorizations < $2.00 detected; do NOT block card immediately unless breach occurred.'
        });
      }
    }

    if (testScenario.recurringMatch) {
      firedRules.push({
        rule: 'R7: Recurring Charge Protection',
        route: 'auto',
        action: 'VERIFY_WITH_CUSTOMER + WARN_CUSTOMER',
        reason: 'Matches historical recurring cadence; card block strictly avoided to preserve cardholder billing integrity.'
      });
    }

    if (testScenario.sharedDeviceRing) {
      firedRules.push({
        rule: 'R4: Multi-Card Device Entity Ring',
        route: 'L2',
        action: 'BLOCK_CARD + FREEZE_DEVICE + FILE_SAR',
        reason: 'Device signature linked to multiple distinct cardholders; coordinated syndicate ring.'
      });
    }

    if (testScenario.customerRepudiated && !testScenario.recurringMatch) {
      firedRules.push({
        rule: 'R1: Customer Repudiated Transaction',
        route: 'L1',
        action: 'BLOCK_CARD + DECLINE_TRANSACTION + ISSUE_PROVISIONAL_CREDIT',
        reason: 'Direct customer repudiation confirmed. Immediate card neutralization and provisional credit.'
      });
    } else if (testScenario.customerConfirmed) {
      firedRules.push({
        rule: 'R2: Customer Confirmed Transaction',
        route: 'auto',
        action: 'APPROVE_TRANSACTION + RECORD_FEEDBACK',
        reason: 'Cardholder confirmed authorized usage. Zero card block; safe resolution.'
      });
    } else if (testScenario.timeout24h) {
      firedRules.push({
        rule: 'R3: 24h Customer Verification Timeout',
        route: testScenario.exposure > 500 ? 'L1' : 'auto',
        action: 'TEMP_BLOCK_CARD + SEND_CHASE_REMINDER',
        reason: 'Verification prompt timed out after 24 hours. Temporary precautionary block enacted.'
      });
    }

    if (testScenario.conflictingEvidence) {
      firedRules.push({
        rule: 'R8: Conflict Resolution Protocol',
        route: 'L1',
        action: 'ESCALATE_TO_SENIOR_ANALYST + GATHER_ADDITIONAL_HOPS',
        reason: 'Irreconcilable conflict between graph signals and customer claims. Route to Senior Analyst.'
      });
    }

    if (testScenario.exposure > 1000 && (testScenario.customerRepudiated || testScenario.sharedDeviceRing)) {
      firedRules.push({
        rule: 'R6: BSA SAR Mandate ($1,000+ Exposure)',
        route: 'L2',
        action: 'FILE_SAR_NARRATIVE',
        reason: 'Fraud exposure exceeds FinCEN statutory $1,000 threshold. SAR filing required with L2 sign-off.'
      });
    }

    return firedRules;
  };

  const simulationResults = evaluateSimulator();

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white border border-[#E5E2D9] rounded-xl p-6 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-blue-600" />
            <h1 className="text-lg font-bold font-mono text-slate-900 font-sans">
              Deterministic Policy Engine Specification (R1–R10)
            </h1>
          </div>
          <p className="text-xs text-slate-600 font-mono mt-1">
            Formal policy catalog enforcing strict action boundaries. Non-bypassable deterministic routing matrix for autonomous vs. human-gated interventions.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="px-3 py-1 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold">
            10 Active Policy Rules
          </span>
          <span className="px-3 py-1 rounded-lg bg-blue-50 text-blue-700 border border-blue-200 font-semibold">
            100% Deterministic
          </span>
        </div>
      </div>

      {/* 3 Routes Specification Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {ROUTE_TIERS.map(spec => (
          <div key={spec.route} className="bg-white border border-[#E5E2D9] rounded-xl p-5 shadow-sm space-y-2.5">
            <div className="flex items-center justify-between">
              <span className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold uppercase ${
                spec.route === 'auto' ? 'bg-blue-50 text-blue-700 border border-blue-200' :
                spec.route === 'L1' ? 'bg-stone-100 text-slate-900 border border-stone-300' :
                'bg-purple-50 text-purple-700 border border-purple-200'
              }`}>
                Route: {spec.route}
              </span>
              <span className="text-xs font-mono text-slate-500 font-semibold">{spec.authority}</span>
            </div>
            <h3 className="text-sm font-bold text-slate-900 font-sans">{spec.label}</h3>
            <p className="text-xs text-slate-600 font-sans leading-relaxed">{spec.description}</p>
            <div className="pt-2 border-t border-[#E5E2D9] text-[11px] font-mono text-slate-500">
              Latency Target: <strong className="text-slate-900">{spec.sla}</strong>
            </div>
          </div>
        ))}
      </div>

      {/* Rules Master-Detail Workbench */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Rules List (5 cols) */}
        <div className="lg:col-span-5 bg-white border border-[#E5E2D9] rounded-xl overflow-hidden shadow-sm">
          <div className="px-5 py-3.5 bg-slate-50 border-b border-[#E5E2D9] flex items-center justify-between">
            <span className="text-xs font-mono font-bold text-slate-900 uppercase">Policy Rules (R1–R10)</span>
            <span className="text-[11px] font-mono text-slate-500">{ALL_POLICY_RULES.length} Rules</span>
          </div>

          <div className="divide-y divide-[#E5E2D9] max-h-[620px] overflow-y-auto">
            {ALL_POLICY_RULES.map(rule => {
              const isSelected = selectedRule.id === rule.id;

              return (
                <div
                  key={rule.id}
                  onClick={() => setSelectedRule(rule)}
                  className={`p-4 cursor-pointer transition-colors text-xs font-mono ${
                    isSelected ? 'bg-blue-50/80 border-l-4 border-blue-600' : 'hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="font-bold text-slate-900 text-sm font-sans">{rule.id}</span>
                    <span className="px-2 py-0.5 rounded font-bold uppercase text-[10px] bg-stone-100 text-slate-800 border border-stone-200">
                      {rule.permissible_routes.join(' / ')}
                    </span>
                  </div>

                  <p className="text-slate-700 text-xs font-sans line-clamp-1">
                    {rule.name}
                  </p>

                  <div className="text-[10px] text-slate-500 mt-1.5 flex items-center gap-2">
                    <span>{rule.benchmark_cases_cited.length} Benchmark Cases</span>
                    <span>•</span>
                    <span className="text-blue-700 font-semibold">{rule.action_recommendation}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected Rule Inspector (7 cols) */}
        <div className="lg:col-span-7 bg-white border border-[#E5E2D9] rounded-xl p-6 space-y-5 shadow-sm text-xs font-mono">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-4 border-b border-[#E5E2D9]">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold text-slate-900 font-sans">{selectedRule.id}: {selectedRule.name}</span>
              </div>
              <span className="text-slate-500 text-xs mt-0.5 block">Section {selectedRule.section}</span>
            </div>

            <div className="flex items-center gap-1.5">
              {selectedRule.permissible_routes.map(r => (
                <span key={r} className="px-3 py-1 rounded-lg font-bold uppercase text-xs bg-blue-50 text-blue-700 border border-blue-200">
                  Route: {r}
                </span>
              ))}
            </div>
          </div>

          <div>
            <span className="text-slate-500 uppercase text-[10px] font-bold block mb-1.5">Trigger Condition:</span>
            <div className="p-4 bg-slate-50 rounded-xl border border-[#E5E2D9] text-slate-900 text-sm font-sans leading-relaxed">
              {selectedRule.trigger_condition}
            </div>
          </div>

          <div>
            <span className="text-slate-500 uppercase text-[10px] font-bold block mb-1.5">Action Recommendation &amp; Thresholds:</span>
            <div className="p-4 bg-blue-50/60 rounded-xl border border-blue-200 text-blue-900 text-sm font-sans leading-relaxed font-semibold">
              {selectedRule.action_recommendation}
            </div>
          </div>

          {selectedRule.rationale && (
            <div>
              <span className="text-slate-500 uppercase text-[10px] font-bold block mb-1.5">Regulatory &amp; Operational Rationale:</span>
              <p className="text-slate-700 text-xs font-sans leading-relaxed">
                {selectedRule.rationale}
              </p>
            </div>
          )}

          <div>
            <span className="text-slate-500 uppercase text-[10px] font-bold block mb-2">
              Benchmark Cases Citing this Rule:
            </span>
            <div className="flex flex-wrap gap-2">
              {selectedRule.benchmark_cases_cited.map(cid => (
                <span key={cid} className="px-3 py-1 rounded-lg bg-stone-100 border border-stone-200 text-slate-800 font-bold">
                  {cid}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Interactive Policy Scenario Simulator */}
      <div className="bg-white border border-[#E5E2D9] rounded-xl p-6 shadow-sm space-y-5">
        <div className="flex items-center gap-2 pb-4 border-b border-[#E5E2D9]">
          <Terminal className="w-5 h-5 text-blue-600" />
          <h2 className="text-base font-bold font-mono text-slate-900 font-sans">
            Interactive Policy Engine Simulator
          </h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Controls (6 cols) */}
          <div className="lg:col-span-6 space-y-4 text-xs font-mono">
            <div>
              <label className="text-slate-600 uppercase text-[10px] font-bold block mb-1">
                Fraud Exposure USD:
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="50"
                  max="10000"
                  step="50"
                  value={testScenario.exposure}
                  onChange={(e) => setTestScenario(prev => ({ ...prev, exposure: Number(e.target.value) }))}
                  className="w-full accent-blue-600"
                />
                <span className="font-bold text-slate-900 text-sm min-w-20 text-right">
                  ${testScenario.exposure.toLocaleString()}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-2">
              <label className="flex items-center gap-2 cursor-pointer bg-slate-50 p-3 rounded-lg border border-[#E5E2D9]">
                <input
                  type="checkbox"
                  checked={testScenario.customerRepudiated}
                  onChange={(e) => setTestScenario(prev => ({ ...prev, customerRepudiated: e.target.checked, customerConfirmed: false }))}
                  className="accent-blue-600"
                />
                <span className="text-slate-800 font-sans">Customer Repudiated</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer bg-slate-50 p-3 rounded-lg border border-[#E5E2D9]">
                <input
                  type="checkbox"
                  checked={testScenario.customerConfirmed}
                  onChange={(e) => setTestScenario(prev => ({ ...prev, customerConfirmed: e.target.checked, customerRepudiated: false }))}
                  className="accent-blue-600"
                />
                <span className="text-slate-800 font-sans">Customer Confirmed</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer bg-slate-50 p-3 rounded-lg border border-[#E5E2D9]">
                <input
                  type="checkbox"
                  checked={testScenario.cardTestingDetected}
                  onChange={(e) => setTestScenario(prev => ({ ...prev, cardTestingDetected: e.target.checked }))}
                  className="accent-blue-600"
                />
                <span className="text-slate-800 font-sans">Card Testing Pattern</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer bg-slate-50 p-3 rounded-lg border border-[#E5E2D9]">
                <input
                  type="checkbox"
                  checked={testScenario.sharedDeviceRing}
                  onChange={(e) => setTestScenario(prev => ({ ...prev, sharedDeviceRing: e.target.checked }))}
                  className="accent-blue-600"
                />
                <span className="text-slate-800 font-sans">Device Syndicate Ring</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer bg-slate-50 p-3 rounded-lg border border-[#E5E2D9]">
                <input
                  type="checkbox"
                  checked={testScenario.conflictingEvidence}
                  onChange={(e) => setTestScenario(prev => ({ ...prev, conflictingEvidence: e.target.checked }))}
                  className="accent-blue-600"
                />
                <span className="text-slate-800 font-sans">Conflicting Signals</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer bg-slate-50 p-3 rounded-lg border border-[#E5E2D9]">
                <input
                  type="checkbox"
                  checked={testScenario.undocumentedPattern}
                  onChange={(e) => setTestScenario(prev => ({ ...prev, undocumentedPattern: e.target.checked }))}
                  className="accent-blue-600"
                />
                <span className="text-slate-800 font-sans">Novel / Undocumented</span>
              </label>
            </div>
          </div>

          {/* Results (6 cols) */}
          <div className="lg:col-span-6 bg-slate-50 border border-[#E5E2D9] rounded-xl p-5 space-y-3 text-xs font-mono">
            <div className="flex items-center justify-between pb-3 border-b border-[#E5E2D9]">
              <span className="font-bold text-slate-900 uppercase">Policy Evaluation Matrix</span>
              <span className="text-blue-700 font-bold">{simulationResults.length} Fired Rules</span>
            </div>

            <div className="space-y-2.5 max-h-72 overflow-y-auto">
              {simulationResults.length === 0 ? (
                <div className="py-8 text-center text-slate-500 font-sans">
                  Select conditions above to simulate policy enforcement rules.
                </div>
              ) : (
                simulationResults.map((r, i) => (
                  <div key={i} className="p-3 bg-white border border-[#E5E2D9] rounded-lg space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-900">{r.rule}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-stone-100 text-slate-800">
                        {r.route}
                      </span>
                    </div>
                    <div className="text-blue-700 font-bold text-[11px]">{r.action}</div>
                    <p className="text-slate-600 font-sans text-xs">{r.reason}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
