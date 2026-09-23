/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useMemo, useRef, useEffect } from 'react';
import { 
  CreditCard, 
  Smartphone, 
  User, 
  DollarSign, 
  MapPin, 
  Mail, 
  ZoomIn, 
  ZoomOut, 
  RotateCcw, 
  Share2, 
  Sparkles,
  Info,
  Move
} from 'lucide-react';
import { SubgraphData, SubgraphNode, SubgraphEdge } from '../types';

interface GraphVisualizerProps {
  subgraph: SubgraphData;
  caseId?: string;
  onSelectTxn?: (txnId: string) => void;
  className?: string;
  isFullPage?: boolean;
}

export const GraphVisualizer: React.FC<GraphVisualizerProps> = ({
  subgraph,
  caseId,
  onSelectTxn,
  className = '',
  isFullPage = false
}) => {
  const [selectedNode, setSelectedNode] = useState<SubgraphNode | null>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [filterType, setFilterType] = useState<string>('all');
  const [highlightRingsOnly, setHighlightRingsOnly] = useState<boolean>(false);

  // Dragging state
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [nodePositions, setNodePositions] = useState<Record<string, { x: number; y: number }>>({});

  const width = 800;
  const height = isFullPage ? 560 : 420;
  const padding = 70;

  // Calculate standard initial layout
  const defaultLayout = useMemo(() => {
    const nodes: SubgraphNode[] = subgraph.nodes;

    const customers = nodes.filter((n: SubgraphNode) => n.type === 'customer');
    const cards = nodes.filter((n: SubgraphNode) => n.type === 'card');
    const txns = nodes.filter((n: SubgraphNode) => n.type === 'transaction');
    const devices = nodes.filter((n: SubgraphNode) => n.type === 'device');
    const others = nodes.filter((n: SubgraphNode) => !['customer', 'card', 'transaction', 'device'].includes(n.type));

    const positions: Record<string, { x: number; y: number }> = {};

    // Customers at left column
    customers.forEach((c: SubgraphNode, idx: number) => {
      positions[c.id] = {
        x: padding + 30,
        y: padding + idx * 110 + (height - padding * 2 - (customers.length - 1) * 110) / 2
      };
    });

    // Cards in second column
    cards.forEach((card: SubgraphNode, idx: number) => {
      positions[card.id] = {
        x: padding + 180,
        y: padding + idx * 80 + (height - padding * 2 - (cards.length - 1) * 80) / 2
      };
    });

    // Transactions in center column
    txns.forEach((txn: SubgraphNode, idx: number) => {
      positions[txn.id] = {
        x: padding + 380 + (idx % 2 === 0 ? 0 : 35),
        y: padding + idx * 65 + (height - padding * 2 - (txns.length - 1) * 65) / 2
      };
    });

    // Devices & Others at right
    devices.forEach((dev: SubgraphNode, idx: number) => {
      positions[dev.id] = {
        x: width - padding - 80,
        y: padding + idx * 90 + (height - padding * 2 - (devices.length - 1) * 90) / 2
      };
    });

    others.forEach((other: SubgraphNode, idx: number) => {
      positions[other.id] = {
        x: width - padding - 60,
        y: height - padding - idx * 70 - 40
      };
    });

    // Fallback for unpositioned nodes
    nodes.forEach((n: SubgraphNode, idx: number) => {
      if (!positions[n.id]) {
        positions[n.id] = {
          x: padding + (idx * 90) % (width - padding * 2),
          y: padding + (idx * 70) % (height - padding * 2)
        };
      }
    });

    return positions;
  }, [subgraph, height, width]);

  // Sync node positions on subgraph change
  useEffect(() => {
    setNodePositions(defaultLayout);
  }, [defaultLayout]);

  // Helper to convert mouse client coordinates to SVG viewBox space
  const getSvgCoordinates = (clientX: number, clientY: number) => {
    if (!svgRef.current) return { x: 0, y: 0 };
    const rect = svgRef.current.getBoundingClientRect();
    const scaleX = width / rect.width;
    const scaleY = height / rect.height;
    return {
      x: (clientX - rect.left) * scaleX,
      y: (clientY - rect.top) * scaleY
    };
  };

  // Drag handlers
  const handleNodeMouseDown = (nodeId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const coords = getSvgCoordinates(e.clientX, e.clientY);
    const currentPos = nodePositions[nodeId] || defaultLayout[nodeId];
    if (currentPos) {
      setDraggingNodeId(nodeId);
      setDragOffset({
        x: coords.x - currentPos.x,
        y: coords.y - currentPos.y
      });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!draggingNodeId) return;
    const coords = getSvgCoordinates(e.clientX, e.clientY);
    const newX = Math.max(30, Math.min(width - 30, coords.x - dragOffset.x));
    const newY = Math.max(30, Math.min(height - 30, coords.y - dragOffset.y));

    setNodePositions(prev => ({
      ...prev,
      [draggingNodeId]: { x: newX, y: newY }
    }));
  };

  const handleMouseUp = () => {
    setDraggingNodeId(null);
  };

  // Touch drag handlers for mobile & tablet screens
  const handleNodeTouchStart = (nodeId: string, e: React.TouchEvent) => {
    e.stopPropagation();
    if (e.touches.length === 1) {
      const touch = e.touches[0];
      const coords = getSvgCoordinates(touch.clientX, touch.clientY);
      const currentPos = nodePositions[nodeId] || defaultLayout[nodeId];
      if (currentPos) {
        setDraggingNodeId(nodeId);
        setDragOffset({
          x: coords.x - currentPos.x,
          y: coords.y - currentPos.y
        });
      }
    }
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!draggingNodeId || e.touches.length !== 1) return;
    const touch = e.touches[0];
    const coords = getSvgCoordinates(touch.clientX, touch.clientY);
    const newX = Math.max(30, Math.min(width - 30, coords.x - dragOffset.x));
    const newY = Math.max(30, Math.min(height - 30, coords.y - dragOffset.y));

    setNodePositions(prev => ({
      ...prev,
      [draggingNodeId]: { x: newX, y: newY }
    }));
  };

  const handleTouchEnd = () => {
    setDraggingNodeId(null);
  };

  const handleResetLayout = () => {
    setNodePositions(defaultLayout);
    setZoomLevel(1);
  };

  const getNodeColor = (node: SubgraphNode) => {
    if (node.isFlagged) {
      return { fill: '#fff1f2', stroke: '#e11d48', strokeWidth: 2.5, text: '#be123c', badgeBg: '#ffe4e6' };
    }
    if (node.ringMember) {
      return { fill: '#faf5ff', stroke: '#9333ea', strokeWidth: 2.5, text: '#7e22ce', badgeBg: '#f3e8ff' };
    }
    switch (node.type) {
      case 'customer':
        return { fill: '#f0fdf4', stroke: '#059669', strokeWidth: 2, text: '#047857', badgeBg: '#dcfce7' };
      case 'card':
        return { fill: '#eff6ff', stroke: '#2563eb', strokeWidth: 2, text: '#1d4ed8', badgeBg: '#dbeafe' };
      case 'transaction':
        return { fill: '#fffbeb', stroke: '#d97706', strokeWidth: 2, text: '#b45309', badgeBg: '#fef3c7' };
      case 'device':
        return { fill: '#faf5ff', stroke: '#7c3aed', strokeWidth: 2, text: '#6d28d9', badgeBg: '#ede9fe' };
      default:
        return { fill: '#f8fafc', stroke: '#64748b', strokeWidth: 2, text: '#475569', badgeBg: '#e2e8f0' };
    }
  };

  const getNodeIcon = (type: string) => {
    switch (type) {
      case 'customer':
        return <User className="w-4 h-4 text-emerald-600" />;
      case 'card':
        return <CreditCard className="w-4 h-4 text-blue-600" />;
      case 'transaction':
        return <DollarSign className="w-4 h-4 text-amber-600" />;
      case 'device':
        return <Smartphone className="w-4 h-4 text-purple-600" />;
      case 'region':
        return <MapPin className="w-4 h-4 text-slate-600" />;
      case 'email':
        return <Mail className="w-4 h-4 text-slate-600" />;
      default:
        return <Info className="w-4 h-4 text-slate-600" />;
    }
  };

  const filteredNodes = useMemo(() => {
    return subgraph.nodes.filter((n: SubgraphNode) => {
      if (filterType !== 'all' && n.type !== filterType) return false;
      if (highlightRingsOnly && !n.ringMember && !n.isFlagged) return false;
      return true;
    });
  }, [subgraph.nodes, filterType, highlightRingsOnly]);

  const visibleNodeIds = useMemo(() => new Set(filteredNodes.map((n: SubgraphNode) => n.id)), [filteredNodes]);

  return (
    <div className={`relative bg-white border border-[#E5E2D9] rounded-xl overflow-hidden flex flex-col shadow-sm ${className}`}>
      
      {/* Visualizer Toolbar */}
      <div className="px-5 py-3 bg-white border-b border-[#E5E2D9] flex flex-wrap items-center justify-between gap-4 text-xs font-mono">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <Share2 className="w-4 h-4 text-blue-600" />
            <span>GSQL SUBGRAPH TRAVERSAL</span>
            {caseId && <span className="text-slate-500 font-normal">[{caseId}]</span>}
          </div>

          <div className="h-4 w-px bg-stone-300 hidden sm:block"></div>

          {/* Node Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500 text-[11px]">Filter:</span>
            {['all', 'card', 'transaction', 'device'].map(type => (
              <button
                key={type}
                onClick={() => setFilterType(type)}
                className={`px-2.5 py-1 rounded text-[11px] capitalize transition-colors ${
                  filterType === type 
                    ? 'bg-blue-600 text-white font-semibold' 
                    : 'bg-stone-100 text-slate-700 hover:bg-stone-200'
                }`}
              >
                {type === 'all' ? 'All' : type}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Draggable hint */}
          <div className="hidden md:flex items-center gap-1 text-[11px] text-slate-500 bg-stone-100/90 px-2.5 py-1 rounded border border-stone-200">
            <Move className="w-3 h-3 text-blue-600" />
            <span>Drag nodes to reposition</span>
          </div>

          {/* Highlight Rings toggle */}
          <button
            onClick={() => setHighlightRingsOnly(!highlightRingsOnly)}
            className={`flex items-center gap-1.5 px-3 py-1 rounded text-[11px] transition-colors ${
              highlightRingsOnly
                ? 'bg-purple-600 text-white font-semibold shadow-sm'
                : 'bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100'
            }`}
          >
            <Sparkles className="w-3 h-3 text-purple-600" />
            <span>Syndicate Ring</span>
          </button>

          {/* Zoom & Reset controls */}
          <div className="flex items-center bg-stone-100 rounded-lg p-0.5 border border-stone-200">
            <button 
              onClick={() => setZoomLevel(prev => Math.min(prev + 0.15, 1.8))}
              className="p-1 text-slate-600 hover:text-slate-900 rounded"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <span className="px-1.5 text-[10px] text-slate-600">
              {Math.round(zoomLevel * 100)}%
            </span>
            <button 
              onClick={() => setZoomLevel(prev => Math.max(prev - 0.15, 0.6))}
              className="p-1 text-slate-600 hover:text-slate-900 rounded"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button 
              onClick={handleResetLayout}
              className="p-1 text-slate-600 hover:text-slate-900 border-l border-stone-200 rounded"
              title="Reset Layout"
            >
              <RotateCcw className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>

      {/* SVG Canvas Area */}
      <div 
        className="relative flex-1 overflow-hidden bg-white min-h-[400px] flex items-center justify-center p-2 cursor-default select-none"
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        onTouchCancel={handleTouchEnd}
      >
        {/* Subtle grid pattern background */}
        <div 
          className="absolute inset-0 pointer-events-none opacity-50"
          style={{
            backgroundImage: 'radial-gradient(#e2e8f0 1.2px, transparent 1.2px)',
            backgroundSize: '20px 20px'
          }}
        />

        <svg 
          ref={svgRef}
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-full max-h-[560px] select-none"
          style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'center center' }}
        >
          <defs>
            {/* Arrowhead marker for default edges */}
            <marker
              id="arrow-default"
              viewBox="0 0 10 10"
              refX="18"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8" />
            </marker>

            {/* Arrowhead for ring edges */}
            <marker
              id="arrow-ring"
              viewBox="0 0 10 10"
              refX="20"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#9333ea" />
            </marker>

            {/* Arrowhead for temporal transaction chain */}
            <marker
              id="arrow-temporal"
              viewBox="0 0 10 10"
              refX="18"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#2563eb" />
            </marker>
          </defs>

          {/* Render Graph Edges */}
          {subgraph.edges.map((edge: SubgraphEdge) => {
            const src = nodePositions[edge.source] || defaultLayout[edge.source];
            const tgt = nodePositions[edge.target] || defaultLayout[edge.target];
            if (!src || !tgt) return null;

            const isVisible = visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target);
            if (!isVisible) return null;

            const isRingEdge = edge.ringMember || edge.highlighted;
            const isTemporal = edge.temporalNext;

            let strokeColor = '#cbd5e1';
            let strokeWidth = 1.5;
            let marker = 'url(#arrow-default)';

            if (isRingEdge) {
              strokeColor = '#9333ea';
              strokeWidth = 2.5;
              marker = 'url(#arrow-ring)';
            } else if (isTemporal) {
              strokeColor = '#2563eb';
              strokeWidth = 2;
              marker = 'url(#arrow-temporal)';
            }

            const midX = (src.x + tgt.x) / 2;
            const midY = (src.y + tgt.y) / 2;

            return (
              <g key={edge.id} className="transition-opacity">
                <line
                  x1={src.x}
                  y1={src.y}
                  x2={tgt.x}
                  y2={tgt.y}
                  stroke={strokeColor}
                  strokeWidth={strokeWidth}
                  strokeDasharray={isTemporal ? '4,4' : undefined}
                  markerEnd={marker}
                  opacity={isRingEdge ? 1 : 0.8}
                />
                {edge.label && (
                  <text
                    x={midX}
                    y={midY - 5}
                    fill={isRingEdge ? '#7e22ce' : isTemporal ? '#1d4ed8' : '#64748b'}
                    fontSize="9"
                    fontFamily="JetBrains Mono, monospace"
                    fontWeight="600"
                    textAnchor="middle"
                    className="select-none pointer-events-none"
                  >
                    {edge.label}
                  </text>
                )}
              </g>
            );
          })}

          {/* Render Graph Nodes (Draggable!) */}
          {filteredNodes.map((node: SubgraphNode) => {
            const pos = nodePositions[node.id] || defaultLayout[node.id];
            if (!pos) return null;

            const colors = getNodeColor(node);
            const isSelected = selectedNode?.id === node.id;
            const isDragging = draggingNodeId === node.id;
            const radius = node.type === 'device' ? 24 : node.isFlagged ? 22 : 18;

            return (
              <g
                key={node.id}
                transform={`translate(${pos.x}, ${pos.y})`}
                onMouseDown={(e) => handleNodeMouseDown(node.id, e)}
                onTouchStart={(e) => handleNodeTouchStart(node.id, e)}
                style={{ touchAction: 'none' }}
                onClick={() => {
                  setSelectedNode(node);
                  if (node.type === 'transaction' && onSelectTxn) {
                    onSelectTxn(node.id);
                  }
                }}
                className={`transition-transform duration-75 cursor-grab active:cursor-grabbing ${isDragging ? 'opacity-90 scale-105' : 'hover:scale-105'}`}
              >
                {/* Node Glow / Selection Ring */}
                {(isSelected || isDragging || node.ringMember) && (
                  <circle
                    r={radius + 6}
                    fill="none"
                    stroke={isSelected ? '#2563eb' : node.ringMember ? '#9333ea' : '#cbd5e1'}
                    strokeWidth="2"
                    strokeDasharray={node.ringMember ? '3,3' : undefined}
                    opacity="0.7"
                  />
                )}

                {/* Base Node Circle */}
                <circle
                  r={radius}
                  fill={colors.fill}
                  stroke={colors.stroke}
                  strokeWidth={colors.strokeWidth}
                  className="filter drop-shadow-sm"
                />

                {/* Node Icon Marker */}
                <text
                  x="0"
                  y="4"
                  fill={colors.text}
                  fontSize="10"
                  fontWeight="bold"
                  fontFamily="JetBrains Mono, monospace"
                  textAnchor="middle"
                  className="pointer-events-none select-none"
                >
                  {node.type === 'customer' ? 'C' : node.type === 'card' ? 'K' : node.type === 'transaction' ? '$' : 'D'}
                </text>

                {/* Primary Node Label (Slate-Black) */}
                <text
                  x="0"
                  y={radius + 14}
                  fill="#0f172a"
                  fontSize="11"
                  fontWeight="600"
                  fontFamily="JetBrains Mono, monospace"
                  textAnchor="middle"
                  className="pointer-events-none select-none"
                >
                  {node.label}
                </text>

                {/* Secondary Sublabel */}
                {node.sublabel && (
                  <text
                    x="0"
                    y={radius + 26}
                    fill={node.isFlagged ? '#e11d48' : '#64748b'}
                    fontSize="10"
                    fontFamily="JetBrains Mono, monospace"
                    fontWeight="500"
                    textAnchor="middle"
                    className="pointer-events-none select-none"
                  >
                    {node.sublabel}
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {/* Legend Overlay */}
        <div className="absolute bottom-3 left-3 bg-white/95 backdrop-blur-md border border-[#E5E2D9] rounded-lg p-3 text-[11px] font-mono text-slate-800 shadow-sm hidden sm:flex flex-col gap-1.5">
          <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Node Legend</div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-600"></span>
            <span>Card Node</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
            <span>Transaction</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-600"></span>
            <span>Device Profile</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-600"></span>
            <span>Flagged Fraud</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-500"></span>
            <span>Syndicate Ring</span>
          </div>
        </div>
      </div>

      {/* Selected Node Details Drawer */}
      {selectedNode && (
        <div className="px-5 py-3 bg-white border-t border-[#E5E2D9] flex items-center justify-between gap-4 text-xs font-mono">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-stone-100 border border-stone-200">
              {getNodeIcon(selectedNode.type)}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-slate-900 font-bold">{selectedNode.label}</span>
                <span className="px-1.5 py-0.5 rounded bg-stone-100 text-[10px] text-slate-700 uppercase font-semibold">
                  {selectedNode.type}
                </span>
                {selectedNode.isFlagged && (
                  <span className="px-1.5 py-0.5 rounded bg-rose-50 border border-rose-200 text-rose-700 text-[10px] font-bold">
                    FLAGGED
                  </span>
                )}
                {selectedNode.ringMember && (
                  <span className="px-1.5 py-0.5 rounded bg-purple-50 border border-purple-200 text-purple-700 text-[10px] font-bold">
                    RING MEMBER
                  </span>
                )}
              </div>
              <div className="text-slate-600 text-[11px] mt-0.5 flex flex-wrap gap-x-4 gap-y-1">
                {selectedNode.details && Object.entries(selectedNode.details).map(([k, v]) => (
                  <span key={k}>
                    <span className="text-slate-500">{k}:</span> <strong className="text-slate-900">{String(v)}</strong>
                  </span>
                ))}
              </div>
            </div>
          </div>

          <button
            onClick={() => setSelectedNode(null)}
            className="px-3 py-1.5 rounded-lg bg-stone-100 hover:bg-stone-200 text-slate-700 text-xs font-medium transition-colors"
          >
            Close Inspector
          </button>
        </div>
      )}
    </div>
  );
};
