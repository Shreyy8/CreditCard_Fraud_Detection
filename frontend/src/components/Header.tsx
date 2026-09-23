/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  Layers, 
  GitFork, 
  CheckSquare, 
  BookOpen, 
  BarChart3,
  FileText,
  Menu,
  X,
  ChevronRight
} from 'lucide-react';
import { BenchmarkCase } from '../types';

export type ActiveTab = 'queue' | 'detail' | 'graph' | 'approvals' | 'policy' | 'benchmark';

interface HeaderProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  selectedCaseId: string | null;
  cases: BenchmarkCase[];
  pendingApprovalsCount: number;
  isLoading?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  selectedCaseId,
  cases,
  pendingApprovalsCount,
  isLoading = false,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  // Close mobile menu on escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMobileMenuOpen(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleTabClick = (tab: ActiveTab) => {
    setActiveTab(tab);
    setMobileMenuOpen(false);
  };

  const navItems = [
    {
      id: 'queue' as ActiveTab,
      label: 'Case Queue',
      icon: <Layers className="w-4 h-4" />,
      badge: isLoading ? '…' : String(cases.length)
    },
    {
      id: 'detail' as ActiveTab,
      label: 'Case Detail',
      icon: <FileText className="w-4 h-4" />,
      badge: selectedCaseId || undefined
    },
    {
      id: 'graph' as ActiveTab,
      label: 'Graph Explorer',
      icon: <GitFork className="w-4 h-4" />
    },
    {
      id: 'approvals' as ActiveTab,
      label: 'Approvals',
      icon: <CheckSquare className="w-4 h-4" />,
      alertCount: pendingApprovalsCount
    },
    {
      id: 'policy' as ActiveTab,
      label: 'Policy Engine',
      icon: <BookOpen className="w-4 h-4" />
    },
    {
      id: 'benchmark' as ActiveTab,
      label: 'Benchmark',
      icon: <BarChart3 className="w-4 h-4" />
    }
  ];

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-[#E5E2D9] text-slate-900 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="h-16 flex items-center justify-between gap-4">
          
          {/* Brand Logo & Title */}
          <div 
            onClick={() => handleTabClick('queue')}
            className="flex items-center gap-2.5 sm:gap-3 cursor-pointer group select-none min-w-0"
          >
            <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center shadow-sm text-white group-hover:bg-blue-700 transition-colors shrink-0">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 sm:gap-2">
                <span className="text-sm sm:text-base font-bold tracking-tight text-slate-900 font-sans truncate">
                  TigerGraph Fraud Agent
                </span>
                <span className="hidden sm:inline-block px-2 py-0.5 rounded bg-blue-50 border border-blue-200 text-[10px] font-mono font-medium text-blue-700 shrink-0">
                  HHG 2026
                </span>
              </div>
              <p className="text-[11px] sm:text-xs text-slate-500 font-mono truncate hidden xs:block">
                Investigation &amp; Decision Governance
              </p>
            </div>
          </div>

          {/* Desktop Navigation Tabs (Hidden on tablet/mobile screens) */}
          <nav className="hidden lg:flex items-center gap-1 sm:gap-2">
            {navItems.map(item => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleTabClick(item.id)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-sm font-semibold'
                      : 'text-slate-700 hover:text-slate-900 hover:bg-stone-100'
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                  {item.badge && (
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${
                      isActive ? 'bg-blue-700 text-white' : 'bg-stone-200 text-slate-700'
                    }`}>
                      {item.badge}
                    </span>
                  )}
                  {item.alertCount !== undefined && item.alertCount > 0 && (
                    <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-mono font-bold ${
                      isActive ? 'bg-white text-blue-700' : 'bg-blue-100 text-blue-800'
                    }`}>
                      {item.alertCount}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Mobile / Tablet Hamburger Menu Button (Visible on screens < lg) */}
          <div className="flex items-center gap-2 lg:hidden">
            {/* Active tab label indicator on mobile header */}
            <span className="text-xs font-mono font-bold text-slate-700 bg-stone-100 px-2.5 py-1 rounded-lg border border-stone-200">
              {navItems.find(i => i.id === activeTab)?.label}
            </span>

            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg bg-stone-100 hover:bg-stone-200 text-slate-800 border border-stone-200 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Toggle navigation menu"
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? (
                <X className="w-5 h-5 text-slate-900" />
              ) : (
                <div className="relative">
                  <Menu className="w-5 h-5 text-slate-900" />
                  {pendingApprovalsCount > 0 && (
                    <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-blue-600 border border-white"></span>
                  )}
                </div>
              )}
            </button>
          </div>

        </div>
      </div>

      {/* Mobile Menu Overlay Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-x-0 top-16 bg-white border-b border-[#E5E2D9] shadow-2xl transition-all z-50 animate-in fade-in slide-in-from-top-2 duration-150">
          <div className="max-w-7xl mx-auto px-4 py-4 space-y-1.5 font-mono text-xs">
            <div className="text-[10px] uppercase font-bold text-slate-500 px-3 py-1 tracking-wider">
              Navigation Menu
            </div>

            {navItems.map(item => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleTabClick(item.id)}
                  className={`w-full flex items-center justify-between px-4 py-3 rounded-xl text-left transition-all ${
                    isActive
                      ? 'bg-blue-600 text-white font-semibold shadow-sm'
                      : 'bg-white hover:bg-stone-100 text-slate-800 border border-[#E5E2D9]'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className={isActive ? 'text-white' : 'text-blue-600'}>
                      {item.icon}
                    </span>
                    <span className="text-sm font-sans font-medium">{item.label}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    {item.badge && (
                      <span className={`px-2 py-0.5 rounded text-[11px] font-mono ${
                        isActive ? 'bg-blue-700 text-white' : 'bg-stone-100 text-slate-700 border border-stone-200'
                      }`}>
                        {item.badge}
                      </span>
                    )}
                    {item.alertCount !== undefined && item.alertCount > 0 && (
                      <span className={`px-2 py-0.5 rounded-full text-[11px] font-mono font-bold ${
                        isActive ? 'bg-white text-blue-700' : 'bg-blue-100 text-blue-800'
                      }`}>
                        {item.alertCount} pending
                      </span>
                    )}
                    <ChevronRight className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Backdrop for mobile menu */}
      {mobileMenuOpen && (
        <div 
          onClick={() => setMobileMenuOpen(false)}
          className="lg:hidden fixed inset-0 top-16 bg-slate-900/30 backdrop-blur-xs z-30"
          aria-hidden="true"
        />
      )}
    </header>
  );
};
