import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Database, Cpu, BookOpen, ShieldCheck, ExternalLink
} from 'lucide-react';
import DataVerification from './components/DataVerification';
import ModelIntelligence from './components/ModelIntelligence';
import { usePreferences } from './Preferences';

const T: Record<string, any> = {
  en: {
    header_title: 'MNIT Threat Inferences Showcase',
    header_sub: 'Public Documentation & Verified Datasets',
    tab_datasets: 'Dataset Catalog',
    tab_models: 'Model Cards',
    tab_papers: 'Publications',
    read_only: 'Read-Only Portal',
  },
  hi: {
    header_title: 'एमएनआईटी थ्रेट इनफेरेंस शोकेस',
    header_sub: 'सार्वजनिक दस्तावेज़ीकरण और सत्यापित डेटासेट',
    tab_datasets: 'डेटासेट कैटलॉग',
    tab_models: 'मॉडल कार्ड',
    tab_papers: 'प्रकाशन',
    read_only: 'केवल-पठनीय पोर्टल',
  }
};


const API_BASE = `${window.location.protocol}//${window.location.hostname}:8004`;

export default function App() {
  const pref = usePreferences();
  const t = (key: string) => T[pref.lang][key] || key;

  const [activeTab, setActiveTab] = useState('datasets');
  const [papers, setPapers] = useState<any[]>([]);

  useEffect(() => {
    // Fetch research papers
    axios.get(`${API_BASE}/showcase/papers`)
      .then(res => setPapers(res.data))
      .catch(err => console.error("Failed to load papers", err));
  }, []);

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900 font-sans flex-col">
      {/* Top Header */}
      <header className="border-b border-slate-200 bg-slate-50 px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-3 text-teal-400">
          <div className="w-9 h-9 rounded-lg bg-teal-500/10 border border-teal-500/20 grid place-items-center">
            <BookOpen size={20} />
          </div>
          <div>
            <h1 className="font-bold text-base leading-tight text-slate-900">{t('header_title')}</h1>
            <p className="text-[10px] text-slate-500 font-semibold uppercase tracking-widest font-mono">{t('header_sub')}</p>
          </div>
        </div>

        {/* Tab Selection */}
        <nav className="flex space-x-2">
          <button
            onClick={() => setActiveTab('datasets')}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold uppercase tracking-wider rounded-lg transition-colors ${
              activeTab === 'datasets' 
                ? 'bg-teal-500/10 text-teal-400 border border-teal-500/20' 
                : 'text-slate-600 hover:text-slate-900 hover:bg-white/[0.02]'
            }`}
          >
            <Database size={14} />
            <span>{t('tab_datasets')}</span>
          </button>
          <button
            onClick={() => setActiveTab('models')}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold uppercase tracking-wider rounded-lg transition-colors ${
              activeTab === 'models' 
                ? 'bg-teal-500/10 text-teal-400 border border-teal-500/20' 
                : 'text-slate-600 hover:text-slate-900 hover:bg-white/[0.02]'
            }`}
          >
            <Cpu size={14} />
            <span>{t('tab_models')}</span>
          </button>
          <button
            onClick={() => setActiveTab('papers')}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold uppercase tracking-wider rounded-lg transition-colors ${
              activeTab === 'papers' 
                ? 'bg-teal-500/10 text-teal-400 border border-teal-500/20' 
                : 'text-slate-600 hover:text-slate-900 hover:bg-white/[0.02]'
            }`}
          >
            <BookOpen size={14} />
            <span>{t('tab_papers')}</span>
          </button>
        </nav>

        <div className="flex items-center space-x-4">
          <div className="flex bg-white border border-slate-200 rounded-lg p-1">
            <button onClick={() => pref.setFontSize('dec')} className="px-2 text-slate-600 hover:text-slate-900 text-[10px] font-bold">A-</button>
            <button onClick={() => pref.setFontSize('reset')} className="px-2 text-slate-600 hover:text-slate-900 text-[10px] border-x border-slate-200 font-bold">A</button>
            <button onClick={() => pref.setFontSize('inc')} className="px-2 text-slate-600 hover:text-slate-900 text-[10px] font-bold">A+</button>
          </div>

          <div className="flex bg-white border border-slate-200 rounded-lg p-1 text-[10px] font-bold">
            <button onClick={() => pref.setLang('en')} className={`px-2 py-0.5 rounded ${pref.lang === 'en' ? 'bg-teal-500 text-black' : 'text-slate-600 hover:text-slate-900'}`}>EN</button>
            <button onClick={() => pref.setLang('hi')} className={`px-2 py-0.5 rounded ${pref.lang === 'hi' ? 'bg-teal-500 text-black' : 'text-slate-600 hover:text-slate-900'}`}>HI</button>
          </div>

          <div className="flex items-center space-x-2 bg-white border border-slate-200 px-3.5 py-1.5 rounded-full text-xs font-mono text-slate-600">
            <ShieldCheck size={14} className="text-teal-400" />
            <span>{t('read_only')}</span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto bg-slate-50 p-2">
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
            <header className="pb-4 border-b border-slate-200">
              <h2 className="text-xl font-bold tracking-tight">Academic Publications</h2>
              <p className="text-xs text-slate-500 mt-1">Research papers and methodologies supporting model design and key rotation protocols.</p>
            </header>

            <div className="space-y-6">
              {papers.map((p, idx) => (
                <div key={idx} className="bg-white border border-slate-200 p-6 rounded-xl space-y-3 shadow-xl">
                  <h3 className="text-sm font-bold text-slate-900 leading-snug">{p.title}</h3>
                  <p className="text-[10px] text-teal-400 font-mono font-semibold uppercase">{p.authors} — {p.journal}</p>
                  <p className="text-xs text-slate-700 leading-relaxed font-sans bg-slate-50 p-4 border border-slate-200 rounded-lg">
                    <span className="font-bold text-slate-500 block mb-1 uppercase text-[9px] tracking-wider">Abstract</span>
                    {p.abstract}
                  </p>
                  <div className="pt-2 border-t border-slate-200 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                    <span>Citation: {p.citation}</span>
                    <span className="flex items-center gap-1 hover:text-slate-900 cursor-pointer select-none" onClick={() => alert("Downloading publication manuscript...")}>
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
