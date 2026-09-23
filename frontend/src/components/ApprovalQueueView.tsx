/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { 
  CheckSquare, 
  Check, 
  ChevronRight, 
  CreditCard,
  Building,
  UserX,
  FileText
} from 'lucide-react';
import { BenchmarkCase, ActionItem } from '../types';

interface ApprovalQueueViewProps {
  cases: BenchmarkCase[];
  onSelectCase: (caseId: string) => void;
  onApproveAction: (caseId: string, actionId: string, approved: boolean) => void;
  onBatchApprove: (route: 'L1' | 'L2' | 'all') => void;
}

export const ApprovalQueueView: React.FC<ApprovalQueueViewProps> = ({
  cases,
  onSelectCase,
  onApproveAction,
  onBatchApprove
}) => {
  const [routeFilter, setRouteFilter] = useState<'all' | 'L1' | 'L2'>('all');

  // Gather all actions from all cases that require L1 or L2 approval
  const pendingItems: Array<{
    caseData: BenchmarkCase;
    action: ActionItem;
  }> = [];

  cases.forEach(c => {
    c.next_best_actions.final.forEach(a => {
      if (['L1', 'L2'].includes(a.route) && a.status === 'pending_approval') {
        pendingItems.push({ caseData: c, action: a });
      }
    });
  });

  const filteredItems = pendingItems.filter(item => {
    if (routeFilter !== 'all' && item.action.route !== routeFilter) return false;
    return true;
  });

  const l1Count = pendingItems.filter(i => i.action.route === 'L1').length;
  const l2Count = pendingItems.filter(i => i.action.route === 'L2').length;

  return (
    <div className="space-y-6">
      {/* Header and Summary */}
      <div className="bg-white border border-[#E5E2D9] rounded-xl p-6 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <CheckSquare className="w-5 h-5 text-blue-600" />
            <h1 className="text-lg font-bold font-mono text-slate-900 font-sans">
              L1 &amp; L2 High-Consequence Action Approval Queue
            </h1>
            <span className="px-2.5 py-0.5 rounded bg-blue-50 border border-blue-200 text-blue-700 font-mono text-xs font-bold">
              {pendingItems.length} Actions Pending
            </span>
          </div>
          <p className="text-xs text-slate-600 font-mono mt-1">
            Deterministic governance desk. Agent autonomously executes <code className="text-blue-700 font-semibold">auto</code> actions; <code className="text-slate-900 font-semibold">L1</code> (Senior Analyst) and <code className="text-slate-900 font-semibold">L2</code> (Fraud Manager) mandate human authorization.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap self-end md:self-auto">
          {pendingItems.length > 0 && (
            <>
              <button
                onClick={() => onBatchApprove('L1')}
                disabled={l1Count === 0}
                className="px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white text-xs font-mono font-semibold shadow-sm transition-all"
              >
                Approve All L1 ({l1Count})
              </button>
              <button
                onClick={() => onBatchApprove('L2')}
                disabled={l2Count === 0}
                className="px-3.5 py-2 rounded-lg bg-stone-900 hover:bg-black disabled:opacity-40 text-white text-xs font-mono font-semibold shadow-sm transition-all"
              >
                Approve All L2 ({l2Count})
              </button>
            </>
          )}
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 bg-white border border-[#E5E2D9] rounded-xl p-3 shadow-sm text-xs font-mono">
        <span className="text-slate-500 text-[11px] font-semibold uppercase mr-2">Filter Route:</span>
        <button
          onClick={() => setRouteFilter('all')}
          className={`px-3 py-1.5 rounded-lg transition-all ${
            routeFilter === 'all'
              ? 'bg-blue-600 text-white font-semibold shadow-sm'
              : 'bg-stone-100 text-slate-700 hover:bg-stone-200'
          }`}
        >
          All Pending ({pendingItems.length})
        </button>
        <button
          onClick={() => setRouteFilter('L1')}
          className={`px-3 py-1.5 rounded-lg transition-all ${
            routeFilter === 'L1'
              ? 'bg-blue-600 text-white font-semibold shadow-sm'
              : 'bg-stone-100 text-slate-700 hover:bg-stone-200'
          }`}
        >
          L1 Senior Analyst ({l1Count})
        </button>
        <button
          onClick={() => setRouteFilter('L2')}
          className={`px-3 py-1.5 rounded-lg transition-all ${
            routeFilter === 'L2'
              ? 'bg-blue-600 text-white font-semibold shadow-sm'
              : 'bg-stone-100 text-slate-700 hover:bg-stone-200'
          }`}
        >
          L2 Fraud Manager ({l2Count})
        </button>
      </div>

      {/* Pending Items List */}
      <div className="space-y-4">
        {filteredItems.length === 0 ? (
          <div className="bg-white border border-[#E5E2D9] rounded-xl p-12 text-center space-y-3 shadow-sm">
            <CheckSquare className="w-10 h-10 text-emerald-600 mx-auto" />
            <h3 className="text-base font-bold text-slate-900 font-sans">Queue Clear</h3>
            <p className="text-xs text-slate-600 font-mono">
              All high-consequence L1 &amp; L2 actions have been audited and authorized.
            </p>
          </div>
        ) : (
          filteredItems.map(({ caseData, action }) => {
            const isL1 = action.route === 'L1';
            const isL2 = action.route === 'L2';

            return (
              <div 
                key={`${caseData.case_id}-${action.id}`}
                className="bg-white border border-[#E5E2D9] rounded-xl p-5 shadow-sm space-y-4 hover:border-blue-400 transition-colors"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#E5E2D9]">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <span className="font-bold text-slate-900 font-mono text-sm">
                      {caseData.case_id}
                    </span>
                    <span className="text-stone-300">•</span>
                    <span className="text-slate-700 font-mono text-xs">
                      Card: {caseData.card_id}
                    </span>
                    <span className="text-stone-300">•</span>
                    <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold uppercase bg-stone-100 text-slate-800 border border-stone-200">
                      {caseData.case.pattern.replace(/_/g, ' ')}
                    </span>
                    <span className="text-slate-900 font-bold font-mono text-xs">
                      ${caseData.case.exposure_usd.toFixed(2)} Exposure
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className={`px-2.5 py-1 rounded text-xs font-mono font-bold uppercase ${
                      isL1 ? 'bg-blue-50 text-blue-700 border border-blue-200' : 'bg-purple-50 text-purple-700 border border-purple-200'
                    }`}>
                      Route: {action.route} Authorization Required
                    </span>
                  </div>
                </div>

                <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center gap-2">
                      {action.action.toLowerCase().includes('block') && <CreditCard className="w-4 h-4 text-rose-600" />}
                      {action.action.toLowerCase().includes('sar') && <Building className="w-4 h-4 text-blue-600" />}
                      {action.action.toLowerCase().includes('freeze') && <UserX className="w-4 h-4 text-purple-600" />}
                      <span className="text-base font-bold text-slate-900 font-sans">
                        {action.action}
                      </span>
                    </div>

                    <p className="text-xs text-slate-700 font-sans leading-relaxed">
                      {action.reason}
                    </p>

                    <div className="text-[11px] text-slate-500 font-mono pt-1">
                      Triggered under policy governance matrix
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
                    <button
                      onClick={() => onSelectCase(caseData.case_id)}
                      className="px-3 py-1.5 rounded-lg bg-stone-100 hover:bg-stone-200 text-slate-800 text-xs font-mono font-medium transition-colors flex items-center gap-1"
                    >
                      <span>Case Dossier</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>

                    <button
                      onClick={() => onApproveAction(caseData.case_id, action.id, false)}
                      className="px-3 py-1.5 rounded-lg bg-stone-100 hover:bg-rose-50 hover:text-rose-700 text-slate-700 text-xs font-mono font-medium transition-colors"
                    >
                      Reject
                    </button>

                    <button
                      onClick={() => onApproveAction(caseData.case_id, action.id, true)}
                      className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-mono font-bold shadow-sm transition-all flex items-center gap-1.5"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Authorize</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
