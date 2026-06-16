import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Database, Cpu, BookOpen, ShieldCheck, ExternalLink
} from 'lucide-react';
import DataVerification from './components/DataVerification';
import ModelIntelligence from './components/ModelIntelligence';

const API_BASE = 'http://localhost:8004';

export default function App() {
  const [activeTab, setActiveTab] = useState('datasets');
  const [papers, setPapers] = useState<any[]>([]);

  useEffect(() => {
    // Fetch research papers
    axios.get(`${API_BASE}/showcase/papers`)
      .then(res => setPapers(res.data))
      .catch(err => console.error("Failed to load papers", err));
  }, []);

  return (
    <div className="flex h-screen bg-neutral-950 text-white font-sans flex-col">
      {/* Top Header */}
      <header className="border-b border-white/[0.06] bg-neutral-950 px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-3 text-teal-400">
          <div className="w-9 h-9 rounded-lg bg-teal-500/10 border border-teal-500/20 grid place-items-center">
            <BookOpen size={20} />
          </div>
          <div>
            <h1 className="font-bold text-base leading-tight text-white">MNIT Threat Inferences Showcase</h1>
            <p className="text-[10px] text-neutral-500 font-semibold uppercase tracking-widest font-mono">Public Documentation & Verified Datasets</p>
          </div>
        </div>

        {/* Tab Selection */}
        <nav className="flex space-x-2">
          <button
            onClick={() => setActiveTab('datasets')}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold uppercase tracking-wider rounded-lg transition-colors ${
              activeTab === 'datasets' 
                ? 'bg-teal-500/10 text-teal-400 border border-teal-500/20' 
                : 'text-neutral-400 hover:text-white hover:bg-white/[0.02]'
            }`}
          >
            <Database size={14} />
            <span>Dataset Catalog</span>
          </button>
          <button
            onClick={() => setActiveTab('models')}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold uppercase tracking-wider rounded-lg transition-colors ${
              activeTab === 'models' 
                ? 'bg-teal-500/10 text-teal-400 border border-teal-500/20' 
                : 'text-neutral-400 hover:text-white hover:bg-white/[0.02]'
            }`}
          >
            <Cpu size={14} />
            <span>Model Cards</span>
          </button>
          <button
            onClick={() => setActiveTab('papers')}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold uppercase tracking-wider rounded-lg transition-colors ${
              activeTab === 'papers' 
                ? 'bg-teal-500/10 text-teal-400 border border-teal-500/20' 
                : 'text-neutral-400 hover:text-white hover:bg-white/[0.02]'
            }`}
          >
            <BookOpen size={14} />
            <span>Publications</span>
          </button>
        </nav>

        <div className="flex items-center space-x-2 bg-neutral-900 border border-white/[0.06] px-3.5 py-1.5 rounded-full text-xs font-mono text-neutral-400">
          <ShieldCheck size={14} className="text-teal-400" />
          <span>Read-Only Portal</span>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto bg-neutral-950 p-2">
        {activeTab === 'datasets' && (
          <div className="h-full">
            <DataVerification />
          </div>
        )}

        {activeTab === 'models' && (
          <div className="h-full">
            <ModelIntelligence />
          </div>
        )}

        {activeTab === 'papers' && (
          <div className="max-w-4xl mx-auto p-8 space-y-6">
            <header className="pb-4 border-b border-white/[0.06]">
              <h2 className="text-xl font-bold tracking-tight">Academic Publications</h2>
              <p className="text-xs text-neutral-500 mt-1">Research papers and methodologies supporting model design and key rotation protocols.</p>
            </header>

            <div className="space-y-6">
              {papers.map((p, idx) => (
                <div key={idx} className="bg-neutral-900 border border-white/[0.04] p-6 rounded-xl space-y-3 shadow-xl">
                  <h3 className="text-sm font-bold text-white leading-snug">{p.title}</h3>
                  <p className="text-[10px] text-teal-400 font-mono font-semibold uppercase">{p.authors} — {p.journal}</p>
                  <p className="text-xs text-neutral-300 leading-relaxed font-sans bg-neutral-950 p-4 border border-white/[0.02] rounded-lg">
                    <span className="font-bold text-neutral-500 block mb-1 uppercase text-[9px] tracking-wider">Abstract</span>
                    {p.abstract}
                  </p>
                  <div className="pt-2 border-t border-white/[0.02] flex items-center justify-between text-[10px] text-neutral-500 font-mono">
                    <span>Citation: {p.citation}</span>
                    <span className="flex items-center gap-1 hover:text-white cursor-pointer select-none" onClick={() => alert("Downloading publication manuscript...")}>
                      <ExternalLink size={12} />
                      <span>Download PDF</span>
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
