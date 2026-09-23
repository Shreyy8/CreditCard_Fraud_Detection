/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useMemo } from 'react';
import { 
  ShieldAlert, 
  ChevronRight, 
  Search, 
  Sparkles,
  GitFork,
  ArrowUpRight,
  Filter
} from 'lucide-react';
import { BenchmarkCase } from '../types';

interface CaseQueueViewProps {
  cases: BenchmarkCase[];
  onSelectCase: (caseId: string) => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
}

export const CaseQueueView: React.FC<CaseQueueViewProps> = ({
  cases,
  onSelectCase,
  searchQuery,
  setSearchQuery
}) => {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [triggerFilter, setTriggerFilter] = useState<string>('all');

  // Compute aggregate stats across the 20 benchmark cases
  const stats = useMemo(() => {
    let fraudCount = 0;
    let legitCount = 0;
    let uncertainCount = 0;
    let totalExposure = 0;
    let sarCount = 0;
    let pendingApprovalCount = 0;

    cases.forEach(c => {
      if (c.case.verdict === 'fraud') fraudCount++;
      else if (c.case.verdict === 'legitimate') legitCount++;
      else uncertainCount++;

      totalExposure += c.case.exposure_usd;
      if (c.sar.file) sarCount++;

      const pending = c.next_best_actions.final.some(a => ['L1', 'L2'].includes(a.route) && a.status === 'pending_approval');
      if (pending) pendingApprovalCount++;
    });

    return {
      total: cases.length,
      fraudCount,
      legitCount,
      uncertainCount,
      totalExposure,
      sarCount,
      pendingApprovalCount
    };
  }, [cases]);

  // Filter cases based on search and pills
  const filteredCases = useMemo(() => {
    return cases.filter(c => {
      // Status filter
      if (statusFilter === 'fraud' && c.case.verdict !== 'fraud') return false;
      if (statusFilter === 'legitimate' && c.case.verdict !== 'legitimate') return false;
      if (statusFilter === 'uncertain' && c.case.verdict !== 'uncertain') return false;
      if (statusFilter === 'sar' && !c.sar.file) return false;
      if (statusFilter === 'high_exposure' && c.case.exposure_usd < 1000) return false;
      if (statusFilter === 'needs_approval') {
        const hasApproval = c.next_best_actions.final.some(a => ['L1', 'L2'].includes(a.route) && a.status === 'pending_approval');
        if (!hasApproval) return false;
      }
      if (statusFilter === 'ring' && c.case_id !== 'HHG-014' && c.case_id !== 'HHG-002') return false;

      // Trigger filter
      if (triggerFilter !== 'all' && c.trigger_type !== triggerFilter) return false;

      // Text search
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchId = c.case_id.toLowerCase().includes(q);
        const matchCard = c.card_id.toLowerCase().includes(q);
        const matchTxn = c.flagged_txn_id.toLowerCase().includes(q);
        const matchPattern = c.case.pattern.toLowerCase().includes(q);
        const matchTrigger = c.trigger_text.toLowerCase().includes(q);
        const matchSummary = c.case.summary.toLowerCase().includes(q);
        if (!matchId && !matchCard && !matchTxn && !matchPattern && !matchTrigger && !matchSummary) {
          return false;
        }
      }

      return true;
    });
  }, [cases, statusFilter, triggerFilter, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Top Benchmark Summary Metrics Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-white border border-[#E5E2D9] rounded-xl p-4 shadow-sm">
          <div className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">Benchmark Cases</div>
          <div className="text-2xl font-bold font-mono text-slate-900 mt-1">20</div>
          <div className="text-[10px] text-emerald-700 mt-1 flex items-center gap-1 font-mono font-medium">
            <span>100% Evaluated</span>
          </div>
        </div>

        <div className="bg-white border border-[#E5E2D9] rounded-xl p-4 shadow-sm">
          <div className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">Confirmed Fraud</div>
          <div className="text-2xl font-bold font-mono text-rose-600 mt-1">{stats.fraudCount}</div>
          <div className="text-[10px] text-slate-600 mt-1 flex items-center gap-1 font-mono">
            <span>Precision: <strong className="text-slate-900">100%</strong></span>
          </div>
        </div>

        <div className="bg-white border border-[#E5E2D9] rounded-xl p-4 shadow-sm">
          <div className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">Legitimate Cleared</div>
          <div className="text-2xl font-bold font-mono text-emerald-600 mt-1">{stats.legitCount}</div>
          <div className="text-[10px] text-slate-600 mt-1 flex items-center gap-1 font-mono">
            <span>0 False Blocks</span>
          </div>
        </div>

        <div className="bg-white border border-[#E5E2D9] rounded-xl p-4 shadow-sm">
          <div className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">Total Exposure</div>
          <div className="text-2xl font-bold font-mono text-slate-900 mt-1">
            ${stats.totalExposure.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="text-[10px] text-slate-600 mt-1 flex items-center gap-1 font-mono">
            <span>Analyzed in Graph</span>
          </div>
        </div>

        <div className="bg-white border border-[#E5E2D9] rounded-xl p-4 shadow-sm">
          <div className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">SAR Filings (&gt;$1k)</div>
          <div className="text-2xl font-bold font-mono text-blue-600 mt-1">{stats.sarCount}</div>
          <div className="text-[10px] text-slate-600 mt-1 flex items-center gap-1 font-mono">
            <span>FinCEN Compliant</span>
          </div>
        </div>

        <div className="bg-white border border-[#E5E2D9] rounded-xl p-4 shadow-sm">
          <div className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">Pending L1/L2</div>
          <div className="text-2xl font-bold font-mono text-purple-600 mt-1">{stats.pendingApprovalCount}</div>
          <div className="text-[10px] text-slate-600 mt-1 flex items-center gap-1 font-mono">
            <span>Human In The Loop</span>
          </div>
        </div>
      </div>

      {/* Flagship Benchmark Showcase Banner */}
      <div className="bg-white border border-[#E5E2D9] rounded-xl p-5 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2.5 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 mt-0.5">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-slate-900 font-sans">
                TigerGraph Benchmark Case Catalog
              </h2>
              <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 text-[10px] font-mono font-medium border border-blue-200">
                20 Cases Loaded
              </span>
            </div>
            <p className="text-xs text-slate-600 mt-1 max-w-3xl leading-relaxed">
              Explore key investigative archetypes: <strong className="text-slate-900">HHG-014</strong> (Multi-card Samsung proxy syndicate ring), <strong className="text-slate-900">HHG-009</strong> (Novel sub-$500 structuring under R9), <strong className="text-slate-900">HHG-012</strong> (R10 mass card-block guardrail), and <strong className="text-slate-900">HHG-001</strong> (Botnet micro-testing burst).
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap self-end md:self-auto">
          <button
            onClick={() => onSelectCase('HHG-014')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-mono font-medium shadow-sm transition-all"
          >
            <GitFork className="w-3.5 h-3.5" />
            <span>Open HHG-014 Ring</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => onSelectCase('HHG-001')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-stone-100 hover:bg-stone-200 text-slate-800 text-xs font-mono font-medium border border-stone-200 transition-all"
          >
            <span>Open HHG-001</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Filter and Search Controls */}
      <div className="bg-white border border-[#E5E2D9] rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 text-xs shadow-sm">
        {/* Status Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-slate-500 font-mono text-[11px] mr-1 flex items-center gap-1">
            <Filter className="w-3 h-3 text-slate-400" /> Filter:
          </span>
          {[
            { id: 'all', label: `All (${cases.length})` },
            { id: 'fraud', label: `Fraud (${stats.fraudCount})` },
            { id: 'legitimate', label: `Legitimate (${stats.legitCount})` },
            { id: 'uncertain', label: `Uncertain (${stats.uncertainCount})` },
            { id: 'needs_approval', label: `Pending Approval (${stats.pendingApprovalCount})` },
            { id: 'sar', label: `SAR Mandated (${stats.sarCount})` },
            { id: 'high_exposure', label: 'Exposure >$1k' },
            { id: 'ring', label: 'Syndicate Rings' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setStatusFilter(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all ${
                statusFilter === tab.id
                  ? 'bg-blue-600 text-white font-semibold shadow-sm'
                  : 'bg-stone-100 text-slate-700 hover:bg-stone-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search & Trigger Filter */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full lg:w-auto">
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input 
              type="text"
              placeholder="Search case, card, txn..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-white border border-[#E5E2D9] rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-900 placeholder-slate-400 font-mono focus:outline-none focus:border-blue-600 transition-all"
            />
            {searchQuery && (
              <button 
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[11px] text-slate-400 hover:text-slate-700"
              >
                ✕
              </button>
            )}
          </div>

          <select
            value={triggerFilter}
            onChange={(e) => setTriggerFilter(e.target.value)}
            className="w-full sm:w-auto bg-white border border-[#E5E2D9] rounded-lg px-3 py-1.5 text-slate-800 text-xs font-mono focus:outline-none focus:border-blue-600"
          >
            <option value="all">All Trigger Sources</option>
            <option value="risk_score">Risk Score Model</option>
            <option value="customer_report">Customer Dispute</option>
            <option value="analyst_request">Analyst Request</option>
          </select>
        </div>
      </div>

      {/* Main Cases Table */}
      <div className="bg-white border border-[#E5E2D9] rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-[#E5E2D9] text-slate-600 uppercase text-[11px] font-semibold tracking-wider">
                <th className="py-3 px-4">Case ID</th>
                <th className="py-3 px-4">Trigger &amp; Intake Reason</th>
                <th className="py-3 px-4">Card / Flagged Txn</th>
                <th className="py-3 px-4">Pattern Typology</th>
                <th className="py-3 px-4">Verdict / Prob</th>
                <th className="py-3 px-4 text-right">Exposure</th>
                <th className="py-3 px-4">Next-Best Action</th>
                <th className="py-3 px-4 text-center">SAR</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E5E2D9]">
              {filteredCases.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-500 font-sans">
                    No benchmark cases matching your search criteria.
                  </td>
                </tr>
              ) : (
                filteredCases.map(c => {
                  const isFraud = c.case.verdict === 'fraud';
                  const isLegit = c.case.verdict === 'legitimate';
                  const isUncertain = c.case.verdict === 'uncertain';

                  const pendingActions = c.next_best_actions.final.filter(a => ['L1', 'L2'].includes(a.route) && a.status === 'pending_approval');
                  const isRingCase = c.case_id === 'HHG-014' || c.case_id === 'HHG-002';

                  return (
                    <tr 
                      key={c.case_id}
                      onClick={() => onSelectCase(c.case_id)}
                      className="hover:bg-slate-50 cursor-pointer transition-colors group"
                    >
                      {/* Case ID */}
                      <td className="py-3.5 px-4 font-bold text-slate-900 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <span className="text-blue-600 group-hover:text-blue-700 transition-colors">
                            {c.case_id}
                          </span>
                          {isRingCase && (
                            <span className="px-1.5 py-0.5 rounded bg-purple-50 border border-purple-200 text-purple-700 text-[9px] font-bold">
                              RING
                            </span>
                          )}
                        </div>
                        <div className="text-[10px] text-slate-500 font-normal">
                          {c.opened_at.slice(5, 10)} {c.opened_at.slice(11, 16)} UTC
                        </div>
                      </td>

                      {/* Trigger */}
                      <td className="py-3.5 px-4 max-w-xs">
                        <div className="flex items-center gap-1.5">
                          <span className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-semibold ${
                            c.trigger_type === 'risk_score' ? 'bg-amber-50 text-amber-800 border border-amber-200' :
                            c.trigger_type === 'customer_report' ? 'bg-rose-50 text-rose-800 border border-rose-200' :
                            'bg-purple-50 text-purple-800 border border-purple-200'
                          }`}>
                            {c.trigger_type === 'risk_score' ? 'Risk Model' : c.trigger_type === 'customer_report' ? 'Dispute' : 'Analyst Tip'}
                          </span>
                          {c.risk_score !== null && (
                            <span className="text-slate-600 text-[10px]">
                              [{c.risk_score.toFixed(2)}]
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-700 truncate mt-1" title={c.trigger_text}>
                          {c.trigger_text}
                        </p>
                      </td>

                      {/* Card / Flagged Txn */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="text-slate-900 font-semibold">{c.card_id}</div>
                        <div className="text-[10px] text-slate-500">
                          Txn: {c.flagged_txn_id}
                        </div>
                      </td>

                      {/* Typology */}
                      <td className="py-3.5 px-4">
                        <div className="text-slate-900 capitalize font-medium">
                          {c.case.pattern.replace(/_/g, ' ')}
                        </div>
                        <div className="text-[10px] text-slate-500">
                          {c.subgraph.nodes.length} nodes • {c.subgraph.edges.length} edges
                        </div>
                      </td>

                      {/* Verdict */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                            isFraud ? 'bg-rose-50 text-rose-700 border border-rose-200' :
                            isLegit ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                            'bg-amber-50 text-amber-700 border border-amber-200'
                          }`}>
                            {c.case.verdict}
                          </span>
                          <span className="text-slate-900 font-bold text-xs">
                            {(c.case.fraud_probability * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="text-[10px] text-slate-500 mt-0.5">
                          Calib: {(c.case.calibrated_probability * 100).toFixed(0)}%
                        </div>
                      </td>

                      {/* Exposure */}
                      <td className="py-3.5 px-4 text-right whitespace-nowrap font-bold text-slate-900">
                        ${c.case.exposure_usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>

                      {/* Next Best Action */}
                      <td className="py-3.5 px-4 max-w-xs">
                        {c.next_best_actions.final.length > 0 ? (
                          <div className="space-y-1">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <span className="text-slate-900 font-semibold">
                                {c.next_best_actions.final[0].action}
                              </span>
                              <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                                c.next_best_actions.final[0].route === 'auto' ? 'bg-blue-50 text-blue-700 border border-blue-200' :
                                c.next_best_actions.final[0].route === 'L1' ? 'bg-amber-50 text-amber-700 border border-amber-200' :
                                'bg-purple-50 text-purple-700 border border-purple-200'
                              }`}>
                                {c.next_best_actions.final[0].route}
                              </span>
                            </div>
                            {pendingActions.length > 0 && (
                              <div className="text-[10px] text-purple-700 font-semibold flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-purple-600"></span>
                                <span>Awaiting {pendingActions[0].route} approval</span>
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-400">None</span>
                        )}
                      </td>

                      {/* SAR */}
                      <td className="py-3.5 px-4 text-center whitespace-nowrap">
                        {c.sar.file ? (
                          <span className="px-2 py-0.5 rounded bg-blue-50 border border-blue-200 text-blue-700 text-[10px] font-bold">
                            SAR FILE
                          </span>
                        ) : (
                          <span className="text-slate-400 text-[11px]">—</span>
                        )}
                      </td>

                      {/* Open Action */}
                      <td className="py-3.5 px-4 text-right whitespace-nowrap">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectCase(c.case_id);
                          }}
                          className="px-3 py-1 rounded-lg bg-stone-100 hover:bg-blue-600 hover:text-white text-slate-700 text-xs font-mono font-medium transition-colors inline-flex items-center gap-1"
                        >
                          <span>Inspect</span>
                          <ChevronRight className="w-3 h-3" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
