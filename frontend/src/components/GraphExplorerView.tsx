/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { 
  GitFork, 
  Terminal, 
  ChevronRight,
  Sparkles
} from 'lucide-react';
import { BenchmarkCase } from '../types';
import { GraphVisualizer } from './GraphVisualizer';

interface GraphExplorerViewProps {
  cases: BenchmarkCase[];
  onSelectCase: (caseId: string) => void;
}

export const GraphExplorerView: React.FC<GraphExplorerViewProps> = ({
  cases,
  onSelectCase
}) => {
  const [selectedCaseId, setSelectedCaseId] = useState<string>('HHG-014');

  const activeCase = cases.find(c => c.case_id === selectedCaseId) || cases[0];

  const presets = [
    { id: 'HHG-014', label: 'Samsung SM-G935F Syndicate Ring', tag: 'Flagship Ring' },
    { id: 'HHG-002', label: 'Pixel 7 Pro ATO Cross-Card Ring', tag: 'ATO Ring' },
    { id: 'HHG-001', label: 'Botnet Micro-Testing Burst', tag: 'Card Testing' },
    { id: 'HHG-007', label: 'Impossible Velocity (NY ➔ Tokyo)', tag: 'Velocity' },
    { id: 'HHG-009', label: 'Sub-$500 Structuring (R9 Novel)', tag: 'Novel Attack' }
  ];

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white border border-[#E5E2D9] rounded-xl p-6 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <GitFork className="w-5 h-5 text-blue-600" />
            <h1 className="text-lg font-bold text-slate-900 font-sans">
              TigerGraph Multi-Hop Subgraph Explorer
            </h1>
          </div>
          <p className="text-xs text-slate-500 font-mono mt-1">
            Interactive graph topology inspector. Reposition nodes, inspect device fingerprints, multi-card clustering, and temporal transaction links.
          </p>
        </div>

        <button
          onClick={() => onSelectCase(activeCase.case_id)}
          className="flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-mono font-medium shadow-sm transition-all w-full md:w-auto"
        >
          <span>Open Full Dossier ({activeCase.case_id})</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Preset Selector Bar */}
      <div className="bg-white border border-[#E5E2D9] rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 text-xs font-mono shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-slate-500 text-[11px] font-semibold uppercase tracking-wider">Quick Presets:</span>
          {presets.map(p => (
            <button
              key={p.id}
              onClick={() => setSelectedCaseId(p.id)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all ${
                selectedCaseId === p.id
                  ? 'bg-blue-600 text-white font-semibold shadow-sm'
                  : 'bg-stone-100 text-slate-700 hover:bg-stone-200'
              }`}
            >
              <span>{p.label}</span>
              <span className={`px-1.5 py-0.5 rounded text-[9px] font-medium ${
                selectedCaseId === p.id ? 'bg-blue-700 text-white' : 'bg-stone-200 text-slate-600'
              }`}>
                {p.tag}
              </span>
            </button>
          ))}
        </div>

        <div className="flex items-center justify-between sm:justify-start gap-2 w-full sm:w-auto">
          <span className="text-slate-500 text-[11px]">Select Case:</span>
          <select
            value={selectedCaseId}
            onChange={(e) => setSelectedCaseId(e.target.value)}
            className="bg-white border border-[#E5E2D9] rounded-lg px-3 py-1.5 text-slate-900 text-xs font-mono focus:outline-none focus:border-blue-600 shadow-sm w-full sm:w-auto"
          >
            {cases.map(c => (
              <option key={c.case_id} value={c.case_id}>
                {c.case_id}: {c.case.pattern.replace(/_/g, ' ')} (${c.case.exposure_usd.toFixed(0)})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Subgraph Canvas */}
      <div className="shadow-sm rounded-xl overflow-hidden">
        <GraphVisualizer
          subgraph={activeCase.subgraph}
          caseId={activeCase.case_id}
          isFullPage={true}
        />
      </div>

      {/* GSQL Query Workbench */}
      <div className="bg-white border border-[#E5E2D9] rounded-xl p-6 space-y-4 font-mono text-xs shadow-sm">
        <div className="flex items-center justify-between pb-3 border-b border-[#E5E2D9]">
          <div className="flex items-center gap-2 text-slate-900 font-bold">
            <Terminal className="w-4 h-4 text-blue-600" />
            <span>GSQL Stored Queries Executed for {activeCase.case_id}</span>
          </div>
          <span className="text-[11px] text-slate-500">TigerGraph Native Graph Algorithms</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-slate-50 p-4 rounded-xl border border-[#E5E2D9] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-blue-700 font-bold">device_neighbors(dev, hops=2)</span>
              <span className="text-[10px] text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">2.1ms</span>
            </div>
            <pre className="text-[11px] text-slate-800 overflow-x-auto whitespace-pre-wrap leading-relaxed font-mono">
{`INTERPRET QUERY (VERTEX<Device> d) {
  Seed = { d };
  ConnectedCards = SELECT c FROM Seed-(FROM_DEVICE:e)-Card:c;
  PRINT ConnectedCards.size(), ConnectedCards;
}`}
            </pre>
          </div>

          <div className="bg-slate-50 p-4 rounded-xl border border-[#E5E2D9] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-blue-700 font-bold">card_testing_sequence(card)</span>
              <span className="text-[10px] text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">1.8ms</span>
            </div>
            <pre className="text-[11px] text-slate-800 overflow-x-auto whitespace-pre-wrap leading-relaxed font-mono">
{`INTERPRET QUERY (VERTEX<Card> c) {
  Txns = SELECT t FROM c-(MADE)-Transaction:t 
         WHERE t.amount_usd < 2.00 
         ORDER BY t.timestamp DESC LIMIT 10;
  PRINT Txns;
}`}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};
