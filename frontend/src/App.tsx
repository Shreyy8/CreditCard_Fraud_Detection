/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useMemo } from 'react';
import { ALL_BENCHMARK_CASES } from './data/cases';
import { BenchmarkCase } from './types';
import { Header, ActiveTab } from './components/Header';
import { CaseQueueView } from './components/CaseQueueView';
import { CaseDetailView } from './components/CaseDetailView';
import { GraphExplorerView } from './components/GraphExplorerView';
import { ApprovalQueueView } from './components/ApprovalQueueView';
import { PolicyEngineView } from './components/PolicyEngineView';
import { BenchmarkDashboard } from './components/BenchmarkDashboard';
import { Check } from 'lucide-react';

export default function App() {
  const [cases, setCases] = useState<BenchmarkCase[]>(ALL_BENCHMARK_CASES);
  const [activeTab, setActiveTab] = useState<ActiveTab>('queue');
  const [selectedCaseId, setSelectedCaseId] = useState<string>('HHG-001');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3000);
  };

  // Find currently selected case
  const currentCase = useMemo(() => {
    return cases.find(c => c.case_id === selectedCaseId) || cases[0];
  }, [cases, selectedCaseId]);

  // Count pending approvals
  const pendingApprovalsCount = useMemo(() => {
    let count = 0;
    cases.forEach(c => {
      c.next_best_actions.final.forEach(a => {
        if (['L1', 'L2'].includes(a.route) && a.status === 'pending_approval') {
          count++;
        }
      });
    });
    return count;
  }, [cases]);

  // Handle single action approve/reject
  const handleApproveAction = (caseId: string, actionId: string, approved: boolean) => {
    setCases(prevCases => {
      return prevCases.map(c => {
        if (c.case_id !== caseId) return c;

        const updatedFinal = c.next_best_actions.final.map(act => {
          if (act.id !== actionId) return act;
          return {
            ...act,
            status: approved ? ('approved' as const) : ('rejected' as const),
            executed: approved
          };
        });

        return {
          ...c,
          next_best_actions: {
            ...c.next_best_actions,
            final: updatedFinal
          }
        };
      });
    });

    showToast(approved ? `Action ${actionId} authorized for execution.` : `Action ${actionId} rejected.`);
  };

  // Handle batch approvals
  const handleBatchApprove = (route: 'L1' | 'L2' | 'all') => {
    setCases(prevCases => {
      return prevCases.map(c => {
        const updatedFinal = c.next_best_actions.final.map(act => {
          if (act.status !== 'pending_approval') return act;
          if (route !== 'all' && act.route !== route) return act;

          return {
            ...act,
            status: 'approved' as const,
            executed: true
          };
        });

        return {
          ...c,
          next_best_actions: {
            ...c.next_best_actions,
            final: updatedFinal
          }
        };
      });
    });

    showToast(`Batch approved all ${route.toUpperCase()} actions.`);
  };

  const handleSelectCase = (caseId: string) => {
    setSelectedCaseId(caseId);
    setActiveTab('detail');
  };

  return (
    <div className="min-h-screen bg-white text-slate-900 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* Top Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        selectedCaseId={selectedCaseId}
        cases={cases}
        pendingApprovalsCount={pendingApprovalsCount}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {activeTab === 'queue' && (
          <CaseQueueView
            cases={cases}
            onSelectCase={handleSelectCase}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
          />
        )}

        {activeTab === 'detail' && (
          <CaseDetailView
            caseData={currentCase}
            allCases={cases}
            onSelectCase={handleSelectCase}
            onBackToQueue={() => setActiveTab('queue')}
            onApproveAction={handleApproveAction}
          />
        )}

        {activeTab === 'graph' && (
          <GraphExplorerView
            cases={cases}
            onSelectCase={handleSelectCase}
          />
        )}

        {activeTab === 'approvals' && (
          <ApprovalQueueView
            cases={cases}
            onSelectCase={handleSelectCase}
            onApproveAction={handleApproveAction}
            onBatchApprove={handleBatchApprove}
          />
        )}

        {activeTab === 'policy' && (
          <PolicyEngineView />
        )}

        {activeTab === 'benchmark' && (
          <BenchmarkDashboard
            cases={cases}
            onSelectCase={handleSelectCase}
          />
        )}
      </main>

      {/* Persistent Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-white border border-blue-600 shadow-xl rounded-xl px-4 py-3 text-xs font-mono text-slate-900 flex items-center gap-2 animate-in fade-in slide-in-from-bottom-2">
          <Check className="w-4 h-4 text-emerald-600" />
          <span className="font-semibold">{toastMessage}</span>
        </div>
      )}

      {/* System Footer */}
      <footer className="border-t border-[#E5E2D9] bg-white py-6 px-6 text-center text-xs font-mono text-slate-600">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div>
            TigerGraph Fraud Investigation Workspace • Benchmark Evaluation Suite
          </div>
          <div className="flex items-center gap-4 text-slate-500 text-[11px]">
            <span>Deterministic Policy R1–R10</span>
            <span>•</span>
            <span>FinCEN Compliant SARs</span>
            <span>•</span>
            <span className="text-emerald-700 font-semibold">Human-In-The-Loop Governance</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
