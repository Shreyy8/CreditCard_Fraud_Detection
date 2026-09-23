/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ALL_BENCHMARK_CASES } from './data/cases';
import { BenchmarkCase } from './types';
import { Header, ActiveTab } from './components/Header';
import { CaseQueueView } from './components/CaseQueueView';
import { CaseDetailView } from './components/CaseDetailView';
import { GraphExplorerView } from './components/GraphExplorerView';
import { ApprovalQueueView } from './components/ApprovalQueueView';
import { PolicyEngineView } from './components/PolicyEngineView';
import { BenchmarkDashboard } from './components/BenchmarkDashboard';
import { Check, Loader2, RefreshCw, Play } from 'lucide-react';
import {
  ApiError,
  approveAction,
  executeAction,
  getCaseAnswer,
  getCaseStats,
  getHealth,
  listCaseAnswers,
  rejectAction,
  runAllInvestigations,
  runInvestigation,
  CaseStatsResponse,
} from './api/client';
import { mapCaseAnswer, mergeLiveCases } from './api/mapCase';

type DataSource = 'api' | 'benchmark';

export default function App() {
  const [cases, setCases] = useState<BenchmarkCase[]>(ALL_BENCHMARK_CASES);
  const [liveStats, setLiveStats] = useState<CaseStatsResponse | null>(null);
  const [dataSource, setDataSource] = useState<DataSource>('benchmark');
  const [apiStatus, setApiStatus] = useState<'checking' | 'connected' | 'offline'>('checking');
  const [healthLabel, setHealthLabel] = useState('Checking API…');
  const [loading, setLoading] = useState(false);
  const [busyMessage, setBusyMessage] = useState<string | null>(null);
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

  const applyLiveCases = useCallback((live: ReturnType<typeof mergeLiveCases>) => {
    if (!live.length) return false;
    setCases(live);
    setDataSource('api');
    setSelectedCaseId((current) =>
      live.some((c) => c.case_id === current) ? current : live[0].case_id,
    );
    return true;
  }, []);

  const loadFromApi = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const health = await getHealth();
      setApiStatus('connected');
      setHealthLabel(
        `API ${health.status} · TG ${health.tigergraph} · MCP ${health.mcp} · pack ${health.data_loaded.case_pack}`,
      );
      try {
        const stats = await getCaseStats();
        setLiveStats(stats);
      } catch {
        // Stats fallback
      }
      const live = mergeLiveCases(await listCaseAnswers(50));
      if (!applyLiveCases(live)) {
        setDataSource('benchmark');
        setCases(ALL_BENCHMARK_CASES);
        if (!quiet) {
          showToast('API connected, no investigated cases yet — showing local benchmark pack.');
        }
      }
    } catch {
      setApiStatus('offline');
      setHealthLabel('API offline — local benchmark pack');
      setDataSource('benchmark');
      setCases(ALL_BENCHMARK_CASES);
      setLiveStats(null);
    } finally {
      if (!quiet) setLoading(false);
    }
  }, [applyLiveCases]);

  useEffect(() => {
    void loadFromApi();
  }, [loadFromApi]);

  const currentCase = useMemo(() => {
    return cases.find((c) => c.case_id === selectedCaseId) || cases[0];
  }, [cases, selectedCaseId]);

  const pendingApprovalsCount = useMemo(() => {
    let count = 0;
    cases.forEach((c) => {
      c.next_best_actions.final.forEach((a) => {
        if (['L1', 'L2'].includes(a.route) && a.status === 'pending_approval') {
          count++;
        }
      });
    });
    return count;
  }, [cases]);

  const patchLocalAction = (caseId: string, actionId: string, approved: boolean) => {
    setCases((prevCases) =>
      prevCases.map((c) => {
        if (c.case_id !== caseId) return c;
        const updatedFinal = c.next_best_actions.final.map((act) => {
          if (act.id !== actionId && act.action !== actionId) return act;
          return {
            ...act,
            status: approved ? ('approved' as const) : ('rejected' as const),
            executed: approved,
          };
        });
        return {
          ...c,
          next_best_actions: {
            ...c.next_best_actions,
            final: updatedFinal,
          },
        };
      }),
    );
  };

  const handleApproveAction = async (caseId: string, actionId: string, approved: boolean) => {
    if (dataSource === 'api') {
      try {
        if (approved) {
          await approveAction(caseId, actionId);
          await executeAction(caseId, actionId);
        } else {
          await rejectAction(caseId, actionId);
        }
        const updated = mapCaseAnswer(await getCaseAnswer(caseId));
        setCases((prev) => prev.map((c) => (c.case_id === caseId ? updated : c)));
        showToast(approved ? `Action ${actionId} authorized and simulated.` : `Action ${actionId} rejected.`);
        return;
      } catch (err) {
        const detail = err instanceof ApiError ? err.detail : 'Backend request failed';
        showToast(`Could not update ${actionId}: ${detail}`);
        return;
      }
    }

    patchLocalAction(caseId, actionId, approved);
    showToast(approved ? `Action ${actionId} authorized for execution.` : `Action ${actionId} rejected.`);
  };

  const handleBatchApprove = async (route: 'L1' | 'L2' | 'all') => {
    if (dataSource === 'api') {
      const pending = cases.flatMap((c) =>
        c.next_best_actions.final
          .filter((act) => act.status === 'pending_approval' && (route === 'all' || act.route === route))
          .map((act) => ({ caseId: c.case_id, actionId: act.id })),
      );
      try {
        for (const item of pending) {
          await approveAction(item.caseId, item.actionId);
          await executeAction(item.caseId, item.actionId);
        }
        await loadFromApi(true);
        showToast(`Batch approved ${pending.length} ${route.toUpperCase()} action(s) via API.`);
      } catch (err) {
        const detail = err instanceof ApiError ? err.detail : 'Batch approval failed';
        showToast(detail);
      }
      return;
    }

    setCases((prevCases) =>
      prevCases.map((c) => {
        const updatedFinal = c.next_best_actions.final.map((act) => {
          if (act.status !== 'pending_approval') return act;
          if (route !== 'all' && act.route !== route) return act;
          return {
            ...act,
            status: 'approved' as const,
            executed: true,
          };
        });
        return {
          ...c,
          next_best_actions: {
            ...c.next_best_actions,
            final: updatedFinal,
          },
        };
      }),
    );
    showToast(`Batch approved all ${route.toUpperCase()} actions.`);
  };

  const handleSelectCase = (caseId: string) => {
    setSelectedCaseId(caseId);
    setActiveTab('detail');
  };

  const handleRunSelected = async () => {
    if (!currentCase) return;
    setBusyMessage(`Investigating ${currentCase.case_id}…`);
    try {
      const answer = await runInvestigation(currentCase.case_id);
      const mapped = mapCaseAnswer(answer);
      setCases((prev) => {
        const exists = prev.some((c) => c.case_id === mapped.case_id);
        return exists
          ? prev.map((c) => (c.case_id === mapped.case_id ? mapped : c))
          : [mapped, ...prev];
      });
      setDataSource('api');
      setApiStatus('connected');
      showToast(`Investigation complete for ${mapped.case_id}.`);
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : 'Investigation failed';
      showToast(detail);
    } finally {
      setBusyMessage(null);
    }
  };

  const handleRunAll = async () => {
    setBusyMessage('Running all case-pack investigations. This can take several minutes…');
    try {
      const result = await runAllInvestigations();
      await loadFromApi(true);
      showToast(`Investigated ${result.completed}/${result.total} cases (${result.failed} failed).`);
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : 'Run-all failed';
      showToast(detail);
    } finally {
      setBusyMessage(null);
    }
  };

  return (
    <div className="min-h-screen bg-white text-slate-900 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        selectedCaseId={selectedCaseId}
        cases={cases}
        pendingApprovalsCount={pendingApprovalsCount}
      />

      <div className="border-b border-[#E5E2D9] bg-stone-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2.5 flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono">
          <div className="flex items-center gap-2 text-slate-600">
            <span
              className={`inline-block w-2 h-2 rounded-full ${
                apiStatus === 'connected'
                  ? 'bg-emerald-500'
                  : apiStatus === 'checking'
                    ? 'bg-amber-400'
                    : 'bg-rose-500'
              }`}
            />
            <span>{healthLabel}</span>
            <span className="text-slate-400">•</span>
            <span>
              Source:{' '}
              <strong className="text-slate-800">
                {dataSource === 'api' ? 'live backend' : 'local benchmark'}
              </strong>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => void loadFromApi()}
              disabled={loading || Boolean(busyMessage)}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white border border-stone-200 hover:bg-stone-100 text-slate-700 disabled:opacity-50"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={() => void handleRunSelected()}
              disabled={Boolean(busyMessage) || apiStatus === 'offline' || !currentCase}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white border border-stone-200 hover:bg-stone-100 text-slate-700 disabled:opacity-50"
            >
              <Play className="w-3 h-3" />
              Investigate {currentCase?.case_id || 'case'}
            </button>
            <button
              onClick={() => void handleRunAll()}
              disabled={Boolean(busyMessage) || apiStatus === 'offline'}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              Run all investigations
            </button>
          </div>
        </div>
      </div>

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {busyMessage && (
          <div className="mb-4 flex items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-xs font-mono text-blue-900">
            <Loader2 className="w-4 h-4 animate-spin" />
            {busyMessage}
          </div>
        )}

        {activeTab === 'queue' && (
          <CaseQueueView
            cases={cases}
            onSelectCase={handleSelectCase}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
          />
        )}

        {activeTab === 'detail' && currentCase && (
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
            stats={liveStats || undefined}
          />
        )}
      </main>

      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-white border border-blue-600 shadow-xl rounded-xl px-4 py-3 text-xs font-mono text-slate-900 flex items-center gap-2 animate-in fade-in slide-in-from-bottom-2">
          <Check className="w-4 h-4 text-emerald-600" />
          <span className="font-semibold">{toastMessage}</span>
        </div>
      )}

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
