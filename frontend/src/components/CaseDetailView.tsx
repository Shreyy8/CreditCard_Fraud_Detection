/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { 
  ArrowLeft, 
  ShieldAlert, 
  ShieldCheck, 
  HelpCircle, 
  Clock, 
  FileText, 
  Layers, 
  CheckCircle2, 
  Copy, 
  Check, 
  ChevronLeft, 
  ChevronRight, 
  Terminal, 
  UserCheck, 
  Building, 
  CreditCard 
} from 'lucide-react';
import { BenchmarkCase } from '../types';
import { GraphVisualizer } from './GraphVisualizer';

interface CaseDetailViewProps {
  caseData?: BenchmarkCase;
  allCases: BenchmarkCase[];
  onSelectCase: (caseId: string) => void;
  onBackToQueue: () => void;
  onApproveAction: (caseId: string, actionId: string, approved: boolean) => void;
  isLoading?: boolean;
  loadError?: string | null;
}

const DetailSkeleton: React.FC = () => (
  <div className="space-y-6" aria-busy="true" aria-label="Loading case investigation">
    <div className="h-12 rounded-xl bg-stone-100 animate-pulse" />
    <div className="h-36 rounded-xl bg-stone-100 animate-pulse" />
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      {[1, 2, 3, 4].map((item) => <div key={item} className="h-24 rounded-xl bg-stone-100 animate-pulse" />)}
    </div>
    <div className="h-72 rounded-xl bg-stone-100 animate-pulse" />
  </div>
);

export const CaseDetailView: React.FC<CaseDetailViewProps> = ({
  caseData,
  allCases,
  onSelectCase,
  onBackToQueue,
  onApproveAction,
  isLoading = false,
  loadError = null,
}) => {
  if (isLoading) return <DetailSkeleton />;
  if (loadError) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-900">
        <strong>Investigation unavailable.</strong> {loadError}
      </div>
    );
  }
  if (!caseData) return null;
  const [activeTab, setActiveTab] = useState<'overview' | 'graph' | 'evidence' | 'policy' | 'sar' | 'history'>('overview');
  const [copiedSar, setCopiedSar] = useState<boolean>(false);
  const [copiedSummary, setCopiedSummary] = useState<boolean>(false);

  // Find index for prev/next navigation
  const currentIndex = allCases.findIndex(c => c.case_id === caseData.case_id);
  const prevCase = currentIndex > 0 ? allCases[currentIndex - 1] : null;
  const nextCase = currentIndex < allCases.length - 1 ? allCases[currentIndex + 1] : null;

  const isFraud = caseData.case.verdict === 'fraud';
  const isLegit = caseData.case.verdict === 'legitimate';
  const isUncertain = caseData.case.verdict === 'uncertain';

  const handleCopySar = () => {
    if (!caseData.sar.narrative) return;
    navigator.clipboard.writeText(caseData.sar.narrative);
    setCopiedSar(true);
    setTimeout(() => setCopiedSar(false), 2000);
  };

  const handleCopySummary = () => {
    navigator.clipboard.writeText(caseData.case.summary);
    setCopiedSummary(true);
    setTimeout(() => setCopiedSummary(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Navigation Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white border border-[#E5E2D9] rounded-xl px-5 py-3 text-xs font-mono shadow-sm">
        <div className="flex items-center gap-3">
          <button
            onClick={onBackToQueue}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-stone-100 hover:bg-stone-200 text-slate-800 transition-colors font-medium"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Case Queue</span>
          </button>
          <span className="text-stone-300">/</span>
          <span className="text-slate-900 font-bold">{caseData.case_id}</span>
          <span className="text-stone-300">•</span>
          <span className="text-slate-600">Card: <strong className="text-slate-900">{caseData.card_id}</strong></span>
        </div>

        <div className="flex items-center gap-2">
          {prevCase && (
            <button
              onClick={() => onSelectCase(prevCase.case_id)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-stone-100 hover:bg-stone-200 text-slate-800 transition-colors"
              title={`Previous: ${prevCase.case_id}`}
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>{prevCase.case_id}</span>
            </button>
          )}
          {nextCase && (
            <button
              onClick={() => onSelectCase(nextCase.case_id)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-stone-100 hover:bg-stone-200 text-slate-800 transition-colors"
              title={`Next: ${nextCase.case_id}`}
            >
              <span>{nextCase.case_id}</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Primary Case Master Dossier Header */}
      <div className="bg-white border border-[#E5E2D9] rounded-xl p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-bold font-mono text-slate-900 tracking-tight">
                Case {caseData.case_id}
              </h1>

              {/* Status Badge */}
              <span className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold uppercase ${
                caseData.case.status === 'closed_fraud' ? 'bg-rose-50 text-rose-800 border border-rose-200' :
                caseData.case.status === 'closed_legitimate' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' :
                'bg-amber-50 text-amber-800 border border-amber-200'
              }`}>
                {caseData.case.status.replace(/_/g, ' ')}
              </span>

              {/* Verdict Badge */}
              <span className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold uppercase flex items-center gap-1.5 ${
                isFraud ? 'bg-rose-50 text-rose-800 border border-rose-200' :
                isLegit ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' :
                'bg-amber-50 text-amber-800 border border-amber-200'
              }`}>
                {isFraud && <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />}
                {isLegit && <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />}
                {isUncertain && <HelpCircle className="w-3.5 h-3.5 text-amber-600" />}
                <span>Verdict: {caseData.case.verdict}</span>
              </span>

              {/* Pattern Typology Badge */}
              <span className="px-2.5 py-0.5 rounded text-xs font-mono bg-stone-100 text-slate-800 border border-stone-200">
                Pattern: {caseData.case.pattern.replace(/_/g, ' ')}
              </span>

              {caseData.sar.file && (
                <span className="px-2.5 py-0.5 rounded text-xs font-mono bg-blue-50 text-blue-800 border border-blue-200 font-bold">
                  SAR REQUIRED
                </span>
              )}
            </div>

            <p className="text-xs text-slate-700 font-mono">
              Trigger: <strong className="text-slate-900">{caseData.trigger_type}</strong> — {caseData.trigger_text}
            </p>
          </div>

          {/* Quick Case Telemetry KPIs */}
          <div className="flex flex-wrap sm:flex-nowrap items-center justify-between sm:justify-start gap-4 sm:gap-6 bg-slate-50 border border-[#E5E2D9] rounded-xl p-4 text-xs font-mono w-full lg:w-auto">
            <div>
              <div className="text-[10px] text-slate-500 uppercase font-medium">Calibrated Prob</div>
              <div className="text-xl font-bold text-slate-900">
                {(caseData.case.calibrated_probability * 100).toFixed(0)}%
              </div>
              <div className="text-[10px] text-slate-500">
                raw {(caseData.case.raw_probability * 100).toFixed(0)}%
              </div>
            </div>

            <div className="h-10 w-px bg-stone-200"></div>

            <div>
              <div className="text-[10px] text-slate-500 uppercase font-medium">Total Exposure</div>
              <div className="text-xl font-bold text-slate-900">
                ${caseData.case.exposure_usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <div className="text-[10px] text-slate-500">
                {caseData.case.affected_txn_ids.length} txns
              </div>
            </div>

            <div className="h-10 w-px bg-stone-200"></div>

            <div>
              <div className="text-[10px] text-slate-500 uppercase font-medium">Graph Node</div>
              <div className="text-sm font-bold text-blue-700">
                {caseData.case.graph_case_id}
              </div>
              <div className="text-[10px] text-emerald-700 font-medium">
                persisted
              </div>
            </div>
          </div>
        </div>

        {/* Tab Navigation Strip */}
        <div className="mt-6 border-t border-[#E5E2D9] pt-4 flex items-center gap-2 overflow-x-auto text-xs font-mono pb-1">
          {[
            { id: 'overview', label: 'Summary & Audit Trail', count: caseData.timeline.length },
            { id: 'graph', label: 'TigerGraph GSQL Subgraph', count: caseData.subgraph.nodes.length },
            { id: 'evidence', label: 'Evidence & Customer Validation', count: caseData.case.evidence.length },
            { id: 'policy', label: 'Policy Enforcement & Routing', count: caseData.next_best_actions.final.length },
            { id: 'sar', label: 'FinCEN SAR Report', alert: caseData.sar.file },
            { id: 'history', label: 'Graph Memory Bank', count: caseData.case.similar_prior_cases.length }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all shrink-0 ${
                activeTab === tab.id
                  ? 'bg-blue-600 text-white font-semibold shadow-sm'
                  : 'text-slate-700 hover:text-slate-900 hover:bg-stone-100'
              }`}
            >
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                  activeTab === tab.id ? 'bg-blue-700 text-white' : 'bg-stone-200 text-slate-700'
                }`}>
                  {tab.count}
                </span>
              )}
              {tab.alert && (
                <span className="w-2 h-2 rounded-full bg-blue-600"></span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab 1: Overview & Audit Trail */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Executive Summary Card */}
          <div className="bg-white border border-[#E5E2D9] rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold font-mono text-slate-900 flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-600" />
                Case Executive Investigation Summary
              </h2>
              <button
                onClick={handleCopySummary}
                className="flex items-center gap-1.5 text-xs font-mono text-slate-700 hover:text-slate-900 px-3 py-1.5 rounded-lg bg-stone-100 hover:bg-stone-200 transition-colors"
              >
                {copiedSummary ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedSummary ? 'Copied' : 'Copy Summary'}</span>
              </button>
            </div>

            <p className="text-sm text-slate-800 leading-relaxed font-sans bg-slate-50 p-5 rounded-xl border border-[#E5E2D9]">
              {caseData.case.summary}
            </p>

            {/* Stopping Rule Citation */}
            <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-xl flex items-center gap-3 text-xs font-mono">
              <Terminal className="w-4 h-4 text-blue-600 shrink-0" />
              <div>
                <span className="text-blue-900 uppercase text-[10px] font-bold block">Agent Stopping Criteria</span>
                <span className="text-blue-950 font-medium">{caseData.stop_reason}</span>
              </div>
            </div>
          </div>

          {/* Uncertainty & Operational Telemetry Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
            <div className="bg-white border border-[#E5E2D9] rounded-xl p-4 shadow-sm">
              <div className="text-slate-500 text-[10px] uppercase font-medium">Confidence Rating</div>
              <div className={`text-lg font-bold mt-1 ${
                caseData.uncertainty.confidence_level === 'High' ? 'text-emerald-700' :
                caseData.uncertainty.confidence_level === 'Medium' ? 'text-amber-700' : 'text-rose-700'
              }`}>
                {caseData.uncertainty.confidence_level}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">
                {caseData.uncertainty.evidence_count} evidence items
              </div>
            </div>

            <div className="bg-white border border-[#E5E2D9] rounded-xl p-4 shadow-sm">
              <div className="text-slate-500 text-[10px] uppercase font-medium">Independent Sources</div>
              <div className="text-lg font-bold text-slate-900 mt-1">
                {caseData.uncertainty.independent_sources} Sources
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">
                Graph + Customer + Rules
              </div>
            </div>

            <div className="bg-white border border-[#E5E2D9] rounded-xl p-4 shadow-sm">
              <div className="text-slate-500 text-[10px] uppercase font-medium">Evidentiary Conflict</div>
              <div className={`text-lg font-bold mt-1 ${
                caseData.uncertainty.has_conflicts ? 'text-rose-700' : 'text-emerald-700'
              }`}>
                {caseData.uncertainty.has_conflicts ? 'Conflict Present' : 'Zero Conflicts'}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">
                {caseData.uncertainty.has_conflicts ? 'R8 Escalation Active' : 'Signals Consistent'}
              </div>
            </div>

            <div className="bg-white border border-[#E5E2D9] rounded-xl p-4 shadow-sm">
              <div className="text-slate-500 text-[10px] uppercase font-medium">Budget Consumption</div>
              <div className="text-lg font-bold text-slate-900 mt-1">
                {caseData.tokens.toLocaleString()} tokens
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">
                {caseData.tool_calls} tool calls ({caseData.latency_s}s)
              </div>
            </div>
          </div>

          {/* 6-Step Agentic Audit Trail Timeline */}
          <div className="bg-white border border-[#E5E2D9] rounded-xl p-6 shadow-sm">
            <h2 className="text-sm font-bold font-mono text-slate-900 flex items-center gap-2 mb-5">
              <Clock className="w-4 h-4 text-blue-600" />
              Agentic Investigation Timeline &amp; Step Audit Trail
            </h2>

            <div className="relative border-l-2 border-stone-200 ml-4 pl-6 space-y-6">
              {caseData.timeline.map((step) => (
                <div key={step.step_number} className="relative group">
                  {/* Step marker node */}
                  <div className="absolute -left-[31px] top-1 w-3.5 h-3.5 rounded-full bg-blue-600 border-2 border-white flex items-center justify-center shadow">
                    <span className="w-1 h-1 rounded-full bg-white"></span>
                  </div>

                  <div className="bg-slate-50 border border-[#E5E2D9] rounded-xl p-4 text-xs font-mono space-y-1.5">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-bold text-[10px] border border-blue-200">
                          Step {step.step_number}
                        </span>
                        <span className="font-bold text-slate-900 text-sm font-sans">{step.name}</span>
                        <span className="text-slate-500 text-[10px] uppercase font-medium">[{step.phase}]</span>
                      </div>
                      <span className="text-slate-500 text-[10px]">
                        {step.timestamp.slice(11, 19)} UTC
                      </span>
                    </div>

                    <p className="text-slate-700 text-xs font-sans leading-relaxed">
                      {step.description}
                    </p>

                    {step.tool_invoked && (
                      <div className="text-[11px] text-blue-700 flex items-center gap-1.5 font-medium">
                        <Terminal className="w-3 h-3 text-blue-600" />
                        <span>Tool Invoked: <strong>{step.tool_invoked}</strong></span>
                      </div>
                    )}

                    <div className="text-[11px] text-emerald-800 flex items-center gap-1.5 font-medium">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                      <span>Result: {step.output_summary}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Affected Transactions Detail Table */}
          {caseData.affected_txns_detail && caseData.affected_txns_detail.length > 0 && (
            <div className="bg-white border border-[#E5E2D9] rounded-xl overflow-hidden shadow-sm">
              <div className="px-5 py-4 bg-slate-50 border-b border-[#E5E2D9] flex items-center justify-between">
                <h3 className="text-xs font-bold font-mono text-slate-900 flex items-center gap-2">
                  <CreditCard className="w-4 h-4 text-blue-600" />
                  Connected &amp; Affected Transactions ({caseData.affected_txns_detail.length})
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="bg-slate-50 border-b border-[#E5E2D9] text-slate-600 uppercase text-[10px]">
                      <th className="py-3 px-4">Txn ID</th>
                      <th className="py-3 px-4">Timestamp (UTC)</th>
                      <th className="py-3 px-4 text-right">Amount (USD)</th>
                      <th className="py-3 px-4">Product / Channel</th>
                      <th className="py-3 px-4">Billing Region</th>
                      <th className="py-3 px-4">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E5E2D9]">
                    {caseData.affected_txns_detail.map(txn => (
                      <tr key={txn.txn_id} className="hover:bg-slate-50">
                        <td className="py-3 px-4 font-bold text-slate-900">
                          {txn.txn_id}
                        </td>
                        <td className="py-3 px-4 text-slate-600">{txn.timestamp.replace('T', ' ').replace('Z', '')}</td>
                        <td className="py-3 px-4 text-right font-bold text-slate-900">
                          ${txn.amount_usd.toFixed(2)}
                        </td>
                        <td className="py-3 px-4 text-slate-700">
                          {txn.product_cd} / {txn.channel}
                        </td>
                        <td className="py-3 px-4 text-slate-600">
                          {txn.billing_region || 'Home'}
                        </td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            txn.status === 'flagged' ? 'bg-rose-50 text-rose-800 border border-rose-200' :
                            'bg-stone-100 text-slate-700'
                          }`}>
                            {txn.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: TigerGraph Subgraph Visualizer */}
      {activeTab === 'graph' && (
        <div className="space-y-4">
          <GraphVisualizer
            subgraph={caseData.subgraph}
            caseId={caseData.case_id}
            isFullPage={true}
          />
          <div className="bg-white border border-[#E5E2D9] rounded-xl p-5 text-xs font-mono text-slate-700 shadow-sm">
            <div className="text-[11px] uppercase font-bold text-slate-500 mb-2">TigerGraph Subgraph Traversal</div>
            <p className="leading-relaxed text-slate-700 font-sans">
              Rendered via multi-hop traversal on the graph schema. Traversed edges include <code className="text-blue-700 font-semibold">OWNS</code>, <code className="text-blue-700 font-semibold">MADE</code>, <code className="text-blue-700 font-semibold">FROM_DEVICE</code>, and temporal <code className="text-blue-700 font-semibold">NEXT</code> linkages. Reposition nodes by clicking and dragging directly on the canvas.
            </p>
          </div>
        </div>
      )}

      {/* Tab 3: Evidence Chain & Customer Validation */}
      {activeTab === 'evidence' && (
        <div className="space-y-6">
          {/* Customer Validation Request Block */}
          {caseData.evidence_requests && caseData.evidence_requests.length > 0 && (
            <div className="bg-white border border-blue-200 rounded-xl p-6 shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <UserCheck className="w-5 h-5 text-blue-600" />
                <h3 className="text-sm font-bold font-mono text-slate-900">
                  Customer Verification Simulation (Policy R1 / R2 Protocol)
                </h3>
              </div>

              {caseData.evidence_requests.map((req) => (
                <div key={req.id} className="bg-slate-50 border border-[#E5E2D9] rounded-xl p-5 space-y-3 text-xs font-mono">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="px-2.5 py-1 rounded bg-blue-50 text-blue-700 font-bold border border-blue-200">
                      Prompt: {req.type.replace(/_/g, ' ')}
                    </span>
                    <span className={`px-2.5 py-1 rounded font-bold uppercase text-[10px] ${
                      req.response_status === 'received' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' :
                      req.response_status === 'timeout' ? 'bg-amber-50 text-amber-800 border border-amber-200' :
                      'bg-stone-100 text-slate-700'
                    }`}>
                      Status: {req.response_status}
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-500 uppercase text-[10px] font-bold block">Customer Response:</span>
                    <p className="text-sm text-slate-900 mt-1 font-sans bg-white p-3 rounded-lg border border-[#E5E2D9]">
                      "{req.assumed_response}"
                    </p>
                  </div>

                  <div className="text-[11px] text-slate-600">
                    <span className="text-slate-500">Deterministic Rule:</span> {req.simulation_rule}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Evidence Chain Items */}
          <div className="bg-white border border-[#E5E2D9] rounded-xl overflow-hidden shadow-sm">
            <div className="px-5 py-4 bg-slate-50 border-b border-[#E5E2D9]">
              <h3 className="text-xs font-bold font-mono text-slate-900 flex items-center gap-2">
                <Layers className="w-4 h-4 text-blue-600" />
                Structured Evidence Items ({caseData.case.evidence.length})
              </h3>
            </div>

            <div className="divide-y divide-[#E5E2D9]">
              {caseData.case.evidence.map((item, idx) => (
                <div key={item.id} className="p-5 hover:bg-slate-50 transition-colors space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900 text-[11px]">#{idx + 1} [{item.id}]</span>
                      <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-blue-50 text-blue-700 border border-blue-200">
                        Source: {item.source}
                      </span>
                      {item.counter_evidence && (
                        <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 text-[10px] font-bold">
                          COUNTER-EVIDENCE (EXCULPATORY)
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2 text-[11px]">
                      <span className="text-slate-500">Impact:</span>
                      <span className={`font-bold uppercase ${
                        item.confidence_impact === 'high' ? 'text-rose-700' :
                        item.confidence_impact === 'medium' ? 'text-amber-700' : 'text-slate-600'
                      }`}>
                        {item.confidence_impact}
                      </span>
                    </div>
                  </div>

                  <p className="text-sm text-slate-800 font-sans leading-relaxed">
                    {item.claim}
                  </p>

                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs font-mono text-slate-600 pt-1">
                    <div>
                      <span className="text-slate-500">Reference:</span>{' '}
                      <code className="text-blue-700 font-bold bg-stone-100 px-1.5 py-0.5 rounded border border-stone-200">
                        {item.ref}
                      </code>
                    </div>
                    {item.entity_ids.length > 0 && (
                      <div>
                        <span className="text-slate-500">Linked Entities:</span>{' '}
                        <span className="text-slate-800 font-medium">{item.entity_ids.join(', ')}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Policy Enforcement & Action Routing */}
      {activeTab === 'policy' && (
        <div className="space-y-6">
          {/* Policy Shift Delta */}
          <div className="bg-white border border-[#E5E2D9] rounded-xl p-5 text-xs font-mono shadow-sm">
            <div className="text-[11px] uppercase font-bold text-slate-500 mb-1">
              Investigative Policy Shift ("What Changed" Delta)
            </div>
            <p className="text-sm text-slate-800 font-sans bg-slate-50 p-4 rounded-xl border border-[#E5E2D9]">
              {caseData.next_best_actions.what_changed === 'nothing' 
                ? 'High-certainty initial policy evaluation remained stable; zero recommendation flips required.' 
                : caseData.next_best_actions.what_changed}
            </p>
          </div>

          {/* Action Comparison Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Initial Actions */}
            <div className="bg-white border border-[#E5E2D9] rounded-xl p-5 space-y-4 shadow-sm">
              <div className="flex items-center justify-between pb-3 border-b border-[#E5E2D9] text-xs font-mono">
                <span className="font-bold text-slate-700 uppercase">Initial Actions (Pre-Customer Validation)</span>
                <span className="text-[10px] text-slate-500">{caseData.next_best_actions.initial.length} items</span>
              </div>

              <div className="space-y-3">
                {caseData.next_best_actions.initial.map(act => (
                  <div key={act.id} className="bg-slate-50 border border-[#E5E2D9] rounded-xl p-4 text-xs font-mono">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="font-bold text-slate-900 text-sm font-sans">{act.action}</span>
                      <span className="px-2 py-0.5 rounded font-bold uppercase text-[10px] bg-stone-100 text-slate-800 border border-stone-200">
                        Route: {act.route}
                      </span>
                    </div>
                    <p className="text-slate-600 text-xs font-sans mt-1">{act.reason}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Final Actions with Interactive Approval */}
            <div className="bg-white border border-blue-200 rounded-xl p-5 space-y-4 shadow-sm">
              <div className="flex items-center justify-between pb-3 border-b border-[#E5E2D9] text-xs font-mono">
                <span className="font-bold text-blue-900 uppercase">Final Actions (Deterministic Routing)</span>
                <span className="text-[10px] text-blue-700 font-bold bg-blue-50 px-2 py-0.5 rounded border border-blue-200">HUMAN APPROVAL</span>
              </div>

              <div className="space-y-3">
                {caseData.next_best_actions.final.map(act => {
                  const isPending = !act.executed && ['L1', 'L2'].includes(act.route);

                  return (
                    <div key={act.id} className="bg-slate-50 border border-[#E5E2D9] rounded-xl p-4 text-xs font-mono space-y-2">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-900 text-sm font-sans">{act.action}</span>
                          <span className={`px-2 py-0.5 rounded font-bold uppercase text-[10px] ${
                            act.route === 'auto' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' :
                            act.route === 'L1' ? 'bg-blue-50 text-blue-800 border border-blue-200' :
                            'bg-purple-50 text-purple-800 border border-purple-200'
                          }`}>
                            Route: {act.route}
                          </span>
                        </div>

                        <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                          act.status === 'executed' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' :
                          act.status === 'pending_approval' ? 'bg-amber-50 text-amber-800 border border-amber-200 animate-pulse' :
                          act.status === 'approved' ? 'bg-blue-50 text-blue-800 border border-blue-200' :
                          'bg-rose-50 text-rose-800 border border-rose-200'
                        }`}>
                          {act.status ? act.status.replace(/_/g, ' ') : 'PENDING'}
                        </span>
                      </div>

                      <p className="text-slate-700 text-xs font-sans leading-relaxed">
                        {act.reason}
                      </p>

                      {/* Interactive Human Approval Controls */}
                      {isPending && (
                        <div className="pt-3 border-t border-[#E5E2D9] flex items-center justify-end gap-2">
                          <span className="text-[11px] text-slate-600 mr-2">Authorization needed:</span>
                          <button
                            onClick={() => onApproveAction(caseData.case_id, act.id, false)}
                            className="px-3 py-1.5 rounded-lg bg-stone-100 hover:bg-stone-200 text-slate-700 text-xs font-medium transition-colors"
                          >
                            Reject
                          </button>
                          <button
                            onClick={() => onApproveAction(caseData.case_id, act.id, true)}
                            className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold transition-all shadow-sm flex items-center gap-1.5"
                          >
                            <Check className="w-3.5 h-3.5" />
                            <span>Authorize ({act.route})</span>
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 5: FinCEN SAR Filing Generator */}
      {activeTab === 'sar' && (
        <div className="space-y-4">
          {caseData.sar.file ? (
            <div className="bg-white border border-[#E5E2D9] rounded-xl p-6 shadow-sm space-y-5 text-xs font-mono">
              <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-[#E5E2D9]">
                <div>
                  <h3 className="text-base font-bold text-slate-900 flex items-center gap-2 font-sans">
                    <Building className="w-4 h-4 text-blue-600" />
                    FinCEN Suspicious Activity Report (SAR) Filing Dossier
                  </h3>
                  <p className="text-slate-500 text-xs mt-1">
                    Regulatory narrative drafted in compliance with Bank Secrecy Act &amp; FinCEN advisories.
                  </p>
                </div>

                <button
                  onClick={handleCopySar}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold transition-all shadow-sm"
                >
                  {copiedSar ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  <span>{copiedSar ? 'Narrative Copied' : 'Copy SAR Narrative'}</span>
                </button>
              </div>

              {/* SAR Metadata Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="bg-slate-50 p-4 rounded-xl border border-[#E5E2D9]">
                  <span className="text-slate-500 uppercase text-[10px] block">Total Amount</span>
                  <span className="text-lg font-bold text-slate-900 mt-1 block">
                    ${caseData.sar.total_amount_usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
                <div className="bg-slate-50 p-4 rounded-xl border border-[#E5E2D9]">
                  <span className="text-slate-500 uppercase text-[10px] block">Threshold Check</span>
                  <span className="text-base font-bold text-emerald-700 mt-1 block">
                    &gt; $1,000 Mandate Met
                  </span>
                </div>
                <div className="bg-slate-50 p-4 rounded-xl border border-[#E5E2D9]">
                  <span className="text-slate-500 uppercase text-[10px] block">Activity Window</span>
                  <span className="text-sm font-bold text-slate-900 mt-1 block">
                    {caseData.sar.activity_dates.join(' to ')}
                  </span>
                </div>
                <div className="bg-slate-50 p-4 rounded-xl border border-[#E5E2D9]">
                  <span className="text-slate-500 uppercase text-[10px] block">Filing Route</span>
                  <span className="text-sm font-bold text-purple-700 mt-1 block">
                    L2 Operations Approval
                  </span>
                </div>
              </div>

              {/* Subject Entities */}
              <div className="bg-slate-50 p-4 rounded-xl border border-[#E5E2D9]">
                <span className="text-slate-600 uppercase text-[10px] font-bold block mb-2">
                  Subject Entities Tagged for BSA Record:
                </span>
                <div className="flex flex-wrap gap-2">
                  {caseData.sar.subjects.map((sub, i) => (
                    <span key={i} className="px-2.5 py-1 rounded bg-white border border-[#E5E2D9] text-slate-800 text-xs font-semibold">
                      {sub}
                    </span>
                  ))}
                </div>
              </div>

              {/* Formal Narrative Text */}
              <div className="space-y-2">
                <span className="text-slate-600 uppercase text-[10px] font-bold block">
                  Official FinCEN Narrative:
                </span>
                <div className="p-5 bg-slate-50 rounded-xl border border-[#E5E2D9] text-sm text-slate-800 font-sans leading-relaxed whitespace-pre-line">
                  {caseData.sar.narrative}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white border border-[#E5E2D9] rounded-xl p-10 text-center space-y-3 shadow-sm">
              <ShieldCheck className="w-10 h-10 text-emerald-600 mx-auto" />
              <h3 className="text-base font-bold text-slate-900 font-sans">No SAR Filing Required</h3>
              <p className="text-xs text-slate-600 font-mono max-w-md mx-auto">
                {caseData.sar.reason || 'Case resolved as legitimate or total exposure does not meet statutory FinCEN threshold.'}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Tab 6: Historical Case Memory Bank */}
      {activeTab === 'history' && (
        <div className="space-y-4">
          <div className="bg-white border border-[#E5E2D9] rounded-xl p-5 text-xs font-mono shadow-sm">
            <div className="text-[11px] uppercase font-bold text-slate-500 mb-1">
              TigerGraph Case Memory Traversal
            </div>
            <p className="text-slate-700 font-sans text-xs">
              Past closed investigations retrieved from the knowledge graph via cosine similarity on graph topology, amount brackets, and device signatures.
            </p>
          </div>

          <div className="space-y-4">
            {caseData.prior_cases_detail && caseData.prior_cases_detail.length > 0 ? (
              caseData.prior_cases_detail.map(pc => (
                <div key={pc.case_id} className="bg-white border border-[#E5E2D9] rounded-xl p-5 space-y-3 text-xs font-mono shadow-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900 text-sm font-sans">{pc.case_id}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        pc.outcome === 'confirmed_fraud' ? 'bg-rose-50 text-rose-800 border border-rose-200' :
                        'bg-emerald-50 text-emerald-800 border border-emerald-200'
                      }`}>
                        {pc.outcome.replace(/_/g, ' ')}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-slate-500">Similarity:</span>
                      <span className="px-2.5 py-0.5 rounded bg-blue-50 text-blue-700 font-bold border border-blue-200">
                        {(pc.similarity_score * 100).toFixed(0)}% Match
                      </span>
                    </div>
                  </div>

                  <p className="text-sm text-slate-800 font-sans leading-relaxed">
                    {pc.notes}
                  </p>

                  <div className="pt-3 border-t border-[#E5E2D9] flex flex-wrap items-center justify-between gap-3 text-[11px] text-slate-600">
                    <div>
                      <span className="text-slate-500">Shared Elements:</span>{' '}
                      <span className="text-slate-900 font-medium">{pc.shared_elements.join(' • ')}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Prior Exposure:</span>{' '}
                      <strong className="text-slate-900">${pc.exposure_usd.toFixed(2)}</strong>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="bg-white border border-[#E5E2D9] rounded-xl p-8 text-center text-slate-500 text-xs font-mono shadow-sm">
                No prior historical cases matching this specific graph neighborhood.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
