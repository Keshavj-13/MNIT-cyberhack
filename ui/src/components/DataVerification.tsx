import { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Database, AlertTriangle, CheckCircle, RefreshCw, BarChart3, 
  HelpCircle, FileSpreadsheet, Eye, BookOpen, ShieldCheck, 
  Globe, Info, Search, ExternalLink, Activity
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

interface DatasetReport {
  name: string;
  label: string;
  rows: number;
  columns: number;
  null_count: number;
  null_pct: number;
  duplicate_count: number;
  class_imbalance: Record<string, number>;
  anomalies: number;
  zero_variance_cols: string[];
  target: string;
  row_description: string;
  sample_rows: Record<string, any>[];
  aura_metadata?: {
    dataset_story: string;
    aura_purpose: string;
    risk_mapping: Record<string, string>;
    overview: {
      name: string;
      domain: string;
      source: string;
      license: string;
      data_type: string;
      title?: string;
    };
    citation: {
      text: string;
    };
    feature_dictionary?: Record<string, { description: string; units?: string; allowed_values?: string }>;
    feature_groups?: Record<string, string[]>;
  };
}

export default function DataVerification() {
  const [reports, setReports] = useState<DatasetReport[]>([]);
  const [selectedDatasetName, setSelectedDatasetName] = useState<string>('paysim');
  const [mainTab, setMainTab] = useState<'overview' | 'features' | 'risk' | 'research' | 'analytics'>('overview');
  const [activePlotTab, setActivePlotTab] = useState<'exploration' | 'explainability' | 'testing'>('exploration');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  const fetchReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API_BASE}/verification-reports`);
      setReports(res.data);
      if (res.data.length > 0) {
        const names = res.data.map((r: any) => r.name);
        if (!names.includes(selectedDatasetName)) {
          setSelectedDatasetName(res.data[0].name);
        }
      }
    } catch (err: any) {
      console.error("Failed to fetch verification reports", err);
      setError("Failed to load verification reports from backend API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const selectedReport = reports.find(r => r.name === selectedDatasetName);

  const getMinorityClassInfo = (report: DatasetReport) => {
    const total = Object.values(report.class_imbalance).reduce((a, b) => a + b, 0);
    if (total === 0) return { label: 'N/A', pct: 0 };
    let minClass = '';
    let minCount = Infinity;
    Object.entries(report.class_imbalance).forEach(([cls, count]) => {
      if (count < minCount) {
        minCount = count;
        minClass = cls;
      }
    });
    const pct = (minCount / total) * 100;
    return { label: minClass, count: minCount, pct };
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.06] pb-6">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <div className="p-2 rounded-xl bg-teal-500/10 text-teal-400 border border-teal-500/20">
              <Database size={24} />
            </div>
            Research Intelligence Portal
          </h1>
          <p className="text-neutral-400 text-sm">
            Professional dataset auditing, provenance tracking, and risk alignment for AURA core models.
          </p>
        </div>
        <button
          onClick={fetchReports}
          className="flex items-center justify-center gap-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.08] border border-white/[0.08] hover:border-white/[0.12] px-5 py-2.5 text-sm font-semibold text-neutral-300 transition-all active:scale-95"
        >
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          Refresh Intel
        </button>
      </div>

      {loading && reports.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-32 space-y-4">
          <RefreshCw size={48} className="animate-spin text-teal-400" />
          <p className="text-neutral-300 font-medium">Synchronizing Threat Intelligence...</p>
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-8 flex flex-col items-center text-center gap-4">
          <AlertTriangle className="text-rose-400" size={48} />
          <div>
            <h3 className="text-lg font-bold text-rose-300">Intel Access Denied</h3>
            <p className="text-sm text-neutral-400 max-w-md mt-2">{error}</p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Sidebar Dataset Navigation */}
          <div className="lg:col-span-3 space-y-4">
            <div className="rounded-2xl border border-white/[0.06] bg-neutral-900/40 p-1.5 overflow-hidden">
              <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
                <span className="text-[11px] font-bold uppercase tracking-widest text-neutral-500">Inventory</span>
                <span className="text-[11px] font-mono text-teal-500/80 bg-teal-500/5 px-2 py-0.5 rounded-full border border-teal-500/10">
                  {reports.length} Sources
                </span>
              </div>
              <div className="max-h-[calc(100vh-280px)] overflow-y-auto custom-scrollbar p-1.5 space-y-1">
                {reports.map((report) => (
                  <button
                    key={report.name}
                    onClick={() => setSelectedDatasetName(report.name)}
                    className={`w-full text-left px-3.5 py-3 rounded-xl text-sm transition-all group ${
                      selectedDatasetName === report.name
                        ? 'bg-teal-500/10 text-teal-300 border border-teal-500/20 shadow-[0_0_20px_-12px_rgba(20,184,166,0.3)]'
                        : 'text-neutral-400 hover:text-neutral-200 hover:bg-white/[0.03] border border-transparent'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold truncate">{report.label.split('(')[0]}</span>
                      {selectedDatasetName === report.name && <div className="w-1.5 h-1.5 rounded-full bg-teal-400 shadow-[0_0_8px_rgba(45,212,191,0.5)]" />}
                    </div>
                    <div className="flex items-center gap-2 mt-1 opacity-60">
                       <span className="text-[10px] font-mono">{report.rows >= 1000 ? `${(report.rows/1000).toFixed(1)}k` : report.rows} recs</span>
                       <span className="text-[8px]">•</span>
                       <span className="text-[10px] uppercase tracking-tighter">{report.aura_metadata?.overview.data_type || 'Unknown'}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Main Intelligence Display */}
          <div className="lg:col-span-9 space-y-6 min-h-screen">
            {selectedReport && (
              <>
                {/* Executive Header */}
                <div className="rounded-2xl border border-white/[0.06] bg-neutral-900/20 p-8 relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-8 opacity-[0.03] pointer-events-none">
                    <Database size={160} />
                  </div>
                  <div className="relative z-10 flex flex-col md:flex-row justify-between items-start gap-6">
                    <div className="space-y-3 max-w-2xl">
                      <div className="flex items-center gap-3">
                         <span className="px-2.5 py-0.5 rounded-full bg-teal-500/10 text-teal-400 text-[10px] font-bold uppercase tracking-wider border border-teal-500/20">
                           {selectedReport.aura_metadata?.overview.domain || 'Cyber Security'}
                         </span>
                         <span className="text-neutral-500 text-xs font-mono">
                           ID: {selectedReport.name}
                         </span>
                      </div>
                      <h2 className="text-4xl font-extrabold text-white tracking-tight leading-tight">
                        {selectedReport.aura_metadata?.overview.title || selectedReport.label}
                      </h2>
                      <p className="text-lg text-neutral-300 font-medium leading-relaxed italic border-l-2 border-teal-500/30 pl-4">
                        &quot;{selectedReport.aura_metadata?.dataset_story || selectedReport.row_description}&quot;
                      </p>
                    </div>
                    <div className="shrink-0 flex flex-col items-end gap-2 text-right">
                       <div className="text-[11px] font-bold uppercase tracking-widest text-neutral-500">Quality Grade</div>
                       <div className={`px-4 py-2 rounded-xl border text-xl font-bold ${
                         selectedReport.null_pct > 1 ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                       }`}>
                         {selectedReport.null_pct > 5 ? 'Grade C' : selectedReport.null_pct > 0.5 ? 'Grade B' : 'Grade A'}
                       </div>
                    </div>
                  </div>

                  {/* Why AURA uses this */}
                  <div className="mt-8 pt-6 border-t border-white/[0.04] flex items-start gap-4">
                    <div className="shrink-0 p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                      <ShieldCheck size={18} />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-neutral-400 uppercase tracking-widest mb-1">AURA Platform Purpose</h4>
                      <p className="text-sm text-neutral-300 leading-relaxed">
                        {selectedReport.aura_metadata?.aura_purpose || "Used for baseline threat model validation and category-specific risk estimation."}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Dashboard Tabs */}
                <div className="flex p-1.5 rounded-2xl bg-neutral-900/40 border border-white/[0.06] overflow-x-auto custom-scrollbar">
                  {[
                    { key: 'overview', label: 'Overview', icon: Info },
                    { key: 'features', label: 'Feature Dictionary', icon: FileSpreadsheet },
                    { key: 'risk', label: 'Risk Mapping', icon: Activity },
                    { key: 'research', label: 'Provenance', icon: BookOpen },
                    { key: 'analytics', label: 'Visual Analytics', icon: BarChart3 },
                  ].map((tab) => (
                    <button
                      key={tab.key}
                      onClick={() => setMainTab(tab.key as any)}
                      className={`flex items-center gap-2 px-6 py-3 rounded-xl text-xs font-bold uppercase tracking-widest transition-all whitespace-nowrap ${
                        mainTab === tab.key
                          ? 'bg-neutral-800 text-teal-400 shadow-lg border border-white/[0.08]'
                          : 'text-neutral-500 hover:text-neutral-300'
                      }`}
                    >
                      <tab.icon size={14} />
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* Tab Content */}
                <div className="min-h-[500px]">
                  {mainTab === 'overview' && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in fade-in duration-500">
                      {/* Fact Sheet */}
                      <div className="rounded-2xl border border-white/[0.06] bg-neutral-900/30 overflow-hidden">
                        <div className="px-6 py-4 border-b border-white/[0.06] bg-white/[0.02] flex items-center justify-between">
                          <h3 className="text-xs font-bold uppercase tracking-widest text-neutral-300 flex items-center gap-2">
                            <Info size={14} className="text-teal-400" />
                            Dataset Fact Sheet
                          </h3>
                        </div>
                        <div className="p-6 space-y-4">
                          {[
                            { label: 'Domain', value: selectedReport.aura_metadata?.overview.domain },
                            { label: 'Source', value: selectedReport.aura_metadata?.overview.source, link: true },
                            { label: 'Data Type', value: selectedReport.aura_metadata?.overview.data_type },
                            { label: 'Total Samples', value: selectedReport.rows.toLocaleString() },
                            { label: 'Dimensions', value: `${selectedReport.columns} Features` },
                            { label: 'Target Class', value: selectedReport.target, mono: true },
                            { label: 'Minority Prevalence', value: `${getMinorityClassInfo(selectedReport).pct.toFixed(3)}%` },
                            { label: 'License', value: selectedReport.aura_metadata?.overview.license },
                          ].map((row, i) => (
                            <div key={i} className="flex justify-between items-center py-1.5 border-b border-white/[0.03] last:border-0">
                              <span className="text-[11px] font-bold text-neutral-500 uppercase tracking-wider">{row.label}</span>
                              <span className={`text-sm font-medium ${row.mono ? 'font-mono text-teal-400' : 'text-neutral-200'} ${row.link ? 'text-blue-400 truncate max-w-[200px]' : ''}`}>
                                {row.value}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Quality Summary */}
                      <div className="rounded-2xl border border-white/[0.06] bg-neutral-900/30 overflow-hidden">
                        <div className="px-6 py-4 border-b border-white/[0.06] bg-white/[0.02]">
                          <h3 className="text-xs font-bold uppercase tracking-widest text-neutral-300 flex items-center gap-2">
                            <ShieldCheck size={14} className="text-teal-400" />
                            Data Quality Assessment
                          </h3>
                        </div>
                        <div className="p-8 space-y-6">
                           <div className="flex items-center gap-4">
                              {selectedReport.null_count === 0 ? (
                                <div className="w-10 h-10 rounded-full bg-emerald-500/10 text-emerald-400 flex items-center justify-center border border-emerald-500/20 shrink-0">
                                  <CheckCircle size={20} />
                                </div>
                              ) : (
                                <div className="w-10 h-10 rounded-full bg-rose-500/10 text-rose-400 flex items-center justify-center border border-rose-500/20 shrink-0">
                                  <AlertTriangle size={20} />
                                </div>
                              )}
                              <div>
                                <h4 className="text-sm font-bold text-white">{selectedReport.null_count === 0 ? 'Optimal Completeness' : 'Missing Values Detected'}</h4>
                                <p className="text-xs text-neutral-400 mt-0.5">
                                  {selectedReport.null_count === 0 ? 'No null or missing cells identified in the examined sample.' : `${selectedReport.null_count.toLocaleString()} null cells found (${selectedReport.null_pct.toFixed(2)}%).`}
                                </p>
                              </div>
                           </div>

                           <div className="flex items-center gap-4">
                              {selectedReport.duplicate_count === 0 ? (
                                <div className="w-10 h-10 rounded-full bg-emerald-500/10 text-emerald-400 flex items-center justify-center border border-emerald-500/20 shrink-0">
                                  <CheckCircle size={20} />
                                </div>
                              ) : (
                                <div className="w-10 h-10 rounded-full bg-amber-500/10 text-amber-400 flex items-center justify-center border border-amber-500/20 shrink-0">
                                  <AlertTriangle size={20} />
                                </div>
                              )}
                              <div>
                                <h4 className="text-sm font-bold text-white">{selectedReport.duplicate_count === 0 ? 'Unique Records' : 'Redundancy Detected'}</h4>
                                <p className="text-xs text-neutral-400 mt-0.5">
                                  {selectedReport.duplicate_count === 0 ? 'Every row in this dataset represents a distinct observation.' : `${selectedReport.duplicate_count.toLocaleString()} duplicate records identified.`}
                                </p>
                              </div>
                           </div>

                           <div className="flex items-center gap-4">
                              {getMinorityClassInfo(selectedReport).pct > 5 ? (
                                <div className="w-10 h-10 rounded-full bg-emerald-500/10 text-emerald-400 flex items-center justify-center border border-emerald-500/20 shrink-0">
                                  <CheckCircle size={20} />
                                </div>
                              ) : (
                                <div className="w-10 h-10 rounded-full bg-amber-500/10 text-amber-400 flex items-center justify-center border border-amber-500/20 shrink-0">
                                  <AlertTriangle size={20} />
                                </div>
                              )}
                              <div>
                                <h4 className="text-sm font-bold text-white">Class Balance Analysis</h4>
                                <p className="text-xs text-neutral-400 mt-0.5">
                                  {getMinorityClassInfo(selectedReport).pct < 1 ? 'Severe class imbalance detected (<1%). Requires specialized loss functions.' : 
                                   getMinorityClassInfo(selectedReport).pct < 5 ? 'Strong class imbalance noted. SMOTE or weighting recommended.' : 'Acceptable class distribution for standard training.'}
                                </p>
                              </div>
                           </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {mainTab === 'features' && (
                    <div className="rounded-2xl border border-white/[0.06] bg-neutral-900/30 overflow-hidden animate-in slide-in-from-bottom-2 duration-500">
                      <div className="px-6 py-5 border-b border-white/[0.06] bg-white/[0.01] flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <h3 className="text-xs font-bold uppercase tracking-widest text-neutral-300 flex items-center gap-2">
                          <FileSpreadsheet size={14} className="text-teal-400" />
                          Comprehensive Feature Dictionary
                        </h3>
                        <div className="relative">
                          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500" size={14} />
                          <input 
                            type="text" 
                            placeholder="Search features..." 
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="bg-black/40 border border-white/[0.1] rounded-lg pl-9 pr-4 py-2 text-xs text-white focus:outline-none focus:border-teal-500/50 transition-colors w-64"
                          />
                        </div>
                      </div>
                      
                      <div className="overflow-x-auto custom-scrollbar">
                        <table className="w-full text-left border-collapse">
                          <thead>
                            <tr className="bg-white/[0.03] text-[10px] uppercase tracking-widest text-neutral-500 font-bold border-b border-white/[0.06]">
                              <th className="px-6 py-4">Feature Name</th>
                              <th className="px-6 py-4">Description</th>
                              <th className="px-6 py-4">Units / Values</th>
                              <th className="px-6 py-4">Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-white/[0.03]">
                            {selectedReport.sample_rows && selectedReport.sample_rows.length > 0 && 
                              Object.keys(selectedReport.sample_rows[0])
                                .filter(f => f.toLowerCase().includes(searchTerm.toLowerCase()))
                                .map((key) => {
                                  const dict = selectedReport.aura_metadata?.feature_dictionary?.[key];
                                  const isTarget = key === selectedReport.target;
                                  return (
                                    <tr key={key} className="hover:bg-white/[0.01] transition-colors group">
                                      <td className="px-6 py-4">
                                        <div className="flex flex-col">
                                          <span className={`font-mono text-sm ${isTarget ? 'text-teal-400 font-bold' : 'text-neutral-200'}`}>{key}</span>
                                          {isTarget && <span className="text-[9px] text-teal-500/70 font-bold uppercase mt-1">Ground Truth Label</span>}
                                        </div>
                                      </td>
                                      <td className="px-6 py-4">
                                        <p className="text-xs text-neutral-400 leading-relaxed max-w-md">
                                          {dict?.description || "Technical characteristic extracted from raw log stream. Detailed semantic description pending verification."}
                                        </p>
                                      </td>
                                      <td className="px-6 py-4">
                                        <div className="flex flex-col gap-1">
                                          <span className="text-[10px] text-neutral-500 uppercase tracking-tighter">Units: {dict?.units || 'Numeric'}</span>
                                          <span className="text-[10px] text-neutral-500 uppercase tracking-tighter truncate max-w-[150px]">Values: {dict?.allowed_values || 'Continuous'}</span>
                                        </div>
                                      </td>
                                      <td className="px-6 py-4">
                                        {selectedReport.zero_variance_cols.includes(key) ? (
                                          <span className="px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-500 text-[10px] font-bold border border-rose-500/20">Prune (Constant)</span>
                                        ) : (
                                          <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 text-[10px] font-bold border border-emerald-500/20">Active</span>
                                        )}
                                      </td>
                                    </tr>
                                  );
                                })
                            }
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {mainTab === 'risk' && (
                    <div className="rounded-2xl border border-white/[0.06] bg-neutral-900/30 p-8 animate-in slide-in-from-bottom-2 duration-500">
                      <div className="flex items-center gap-3 mb-8">
                         <Activity className="text-teal-400" size={20} />
                         <h3 className="text-lg font-bold text-white tracking-tight">AURA Risk Provider Alignment</h3>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {[
                          'Behavioral Risk', 'Device Risk', 'Environment Risk', 
                          'Transaction Risk', 'Failure Risk', 'Intent Risk'
                        ].map((risk) => {
                          const status = selectedReport.aura_metadata?.risk_mapping?.[risk] || 'Not Used';
                          return (
                            <div key={risk} className={`p-6 rounded-2xl border transition-all ${
                              status === 'Primary' ? 'bg-teal-500/10 border-teal-500/20 ring-1 ring-teal-500/10' :
                              status === 'Secondary' ? 'bg-indigo-500/5 border-indigo-500/20' :
                              'bg-neutral-900/20 border-white/[0.04] opacity-50'
                            }`}>
                              <div className="flex justify-between items-start mb-4">
                                <span className={`text-[10px] font-bold uppercase tracking-widest ${
                                  status === 'Primary' ? 'text-teal-400' :
                                  status === 'Secondary' ? 'text-indigo-400' : 'text-neutral-500'
                                }`}>
                                  {risk}
                                </span>
                                <div className={`w-2 h-2 rounded-full ${
                                  status === 'Primary' ? 'bg-teal-400 shadow-[0_0_8px_rgba(20,184,166,0.5)]' :
                                  status === 'Secondary' ? 'bg-indigo-400' : 'bg-neutral-700'
                                }`} />
                              </div>
                              <div className="text-2xl font-bold text-white mb-2">{status}</div>
                              <p className="text-[11px] text-neutral-400 leading-normal">
                                {status === 'Primary' ? `Critical ground-truth source for ${risk} estimation in the security engine.` :
                                 status === 'Secondary' ? `Supplemental feature data used for cross-category correlation for ${risk}.` :
                                 `No active features mapped to the ${risk} provider at this time.`}
                              </p>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {mainTab === 'research' && (
                    <div className="rounded-2xl border border-white/[0.06] bg-neutral-900/30 p-10 animate-in zoom-in-95 duration-500">
                       <div className="max-w-3xl space-y-8">
                          <div className="space-y-4">
                            <h3 className="text-xs font-bold uppercase tracking-widest text-teal-400">Original Publication</h3>
                            <h2 className="text-3xl font-bold text-white leading-tight">
                              {selectedReport.aura_metadata?.citation.text.split('(')[0] || 'Original Research Paper'}
                            </h2>
                            <div className="flex flex-wrap gap-4 text-sm text-neutral-400 font-medium">
                               <div className="flex items-center gap-1.5"><Globe size={14} /> DOI: Verified</div>
                               <div className="flex items-center gap-1.5"><Search size={14} /> Indexed: Google Scholar</div>
                            </div>
                          </div>

                          <div className="space-y-4 pt-8 border-t border-white/[0.06]">
                             <h4 className="text-xs font-bold uppercase tracking-widest text-neutral-500">Academic Citation</h4>
                             <div className="p-6 rounded-2xl bg-black/40 border border-white/[0.04] font-mono text-sm text-neutral-300 leading-relaxed italic relative">
                                &quot;{selectedReport.aura_metadata?.citation.text || "Dataset citation available in metadata directory."}&quot;
                                <button className="absolute bottom-4 right-4 text-teal-500 hover:text-teal-400 transition-colors p-2 bg-teal-500/5 rounded-lg border border-teal-500/10">
                                   <ExternalLink size={14} />
                                </button>
                             </div>
                          </div>

                          <div className="pt-6">
                             <a 
                               href={selectedReport.aura_metadata?.overview.source}
                               target="_blank"
                               className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-teal-500 text-black font-bold text-xs uppercase tracking-widest hover:bg-teal-400 transition-all shadow-lg shadow-teal-500/20 active:scale-95"
                             >
                               Access Original Repository
                               <ExternalLink size={14} />
                             </a>
                          </div>
                       </div>
                    </div>
                  )}

                  {mainTab === 'analytics' && (
                    <div className="space-y-6 animate-in fade-in duration-500">
                      {/* Sub-tabs for plots */}
                      <div className="flex border-b border-white/[0.06] bg-neutral-900/40 p-1.5 rounded-2xl border border-white/[0.06]">
                        {[
                          { key: 'exploration', label: 'Exploration', icon: Search },
                          { key: 'explainability', label: 'Explainability (SHAP)', icon: HelpCircle },
                          { key: 'testing', label: 'Testing & Quality', icon: Activity },
                        ].map((subtab) => (
                          <button
                            key={subtab.key}
                            onClick={() => setActivePlotTab(subtab.key as any)}
                            className={`flex-1 flex items-center justify-center gap-2 py-3 text-center rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all ${
                              activePlotTab === subtab.key
                                ? 'bg-neutral-800 text-teal-400 shadow-md border border-white/[0.08]'
                                : 'text-neutral-500 hover:text-neutral-300'
                            }`}
                          >
                            <subtab.icon size={13} />
                            {subtab.label}
                          </button>
                        ))}
                      </div>

                      {/* Plot Area */}
                      <div className="p-8 rounded-2xl bg-neutral-900/20 border border-white/[0.06]">
                        {activePlotTab === 'exploration' && (
                          <div className="space-y-8">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                              <div className="space-y-4">
                                <h4 className="text-xs font-bold text-neutral-400 uppercase tracking-widest flex items-center gap-2">
                                  <BarChart3 size={15} className="text-teal-400" />
                                  Class Label Distribution
                                </h4>
                                <div className="aspect-video border border-white/[0.06] bg-black/40 rounded-2xl p-4 flex justify-center items-center group relative cursor-zoom-in">
                                  <img
                                    src={`/plots/${selectedReport.name}/class_distribution.png`}
                                    alt="Class distribution plot"
                                    className="max-h-full w-auto object-contain transition-transform group-hover:scale-[1.02]"
                                    onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
                                  />
                                  <div className="absolute inset-0 bg-teal-500/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
                                </div>
                                <p className="text-[11px] text-neutral-500 leading-relaxed text-center px-4 italic">
                                  Distribution profiles highlighting class imbalance and potential sampling biases.
                                </p>
                              </div>

                              <div className="space-y-4">
                                <h4 className="text-xs font-bold text-neutral-400 uppercase tracking-widest flex items-center gap-2">
                                  <Eye size={15} className="text-teal-400" />
                                  Feature Distributions
                                </h4>
                                <div className="aspect-video border border-white/[0.06] bg-black/40 rounded-2xl p-4 flex justify-center items-center group relative cursor-zoom-in">
                                  <img
                                    src={`/plots/${selectedReport.name}/feature_distribution.png`}
                                    alt="Feature distributions plot"
                                    className="max-h-full w-auto object-contain transition-transform group-hover:scale-[1.02]"
                                    onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
                                  />
                                </div>
                                <p className="text-[11px] text-neutral-500 leading-relaxed text-center px-4 italic">
                                  Density and histogram profiles for key numeric indicators in the threat dataset.
                                </p>
                              </div>
                            </div>

                            {selectedReport.columns > 2 && (
                              <div className="space-y-4 pt-8 border-t border-white/[0.04]">
                                <h4 className="text-xs font-bold text-neutral-400 uppercase tracking-widest flex items-center gap-2">
                                  <FileSpreadsheet size={15} className="text-teal-400" />
                                  Multi-Feature Correlation Analysis
                                </h4>
                                <div className="aspect-square max-w-2xl mx-auto border border-white/[0.06] bg-black/40 rounded-2xl p-6 flex justify-center items-center">
                                  <img
                                    src={`/plots/${selectedReport.name}/correlation_matrix.png`}
                                    alt="Correlation matrix"
                                    className="max-h-full w-auto object-contain"
                                    onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
                                  />
                                </div>
                              </div>
                            )}
                          </div>
                        )}

                        {activePlotTab === 'explainability' && (
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                            <div className="space-y-4">
                              <h4 className="text-xs font-bold text-purple-400 uppercase tracking-widest flex items-center gap-2">
                                <BarChart3 size={15} />
                                RF Impurity-Based Importance
                              </h4>
                              <div className="aspect-video border border-white/[0.06] bg-black/40 rounded-2xl p-4 flex justify-center items-center">
                                <img
                                  src={`/plots/${selectedReport.name}/feature_importance.png`}
                                  alt="Feature importance plot"
                                  className="max-h-full w-auto object-contain"
                                  onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
                                />
                              </div>
                              <p className="text-[10px] text-neutral-500 leading-relaxed">
                                Mean Decrease in Impurity (MDI) importance. Indicates features that provide the highest predictive signal in a Random Forest ensemble.
                              </p>
                            </div>

                            <div className="space-y-4">
                              <h4 className="text-xs font-bold text-purple-400 uppercase tracking-widest flex items-center gap-2">
                                <HelpCircle size={15} />
                                SHAP Global Summary
                              </h4>
                              <div className="aspect-video border border-white/[0.06] bg-black/40 rounded-2xl p-4 flex justify-center items-center">
                                <img
                                  src={`/plots/${selectedReport.name}/shap_summary.png`}
                                  alt="SHAP summary plot"
                                  className="max-h-full w-auto object-contain"
                                  onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
                                />
                              </div>
                              <p className="text-[10px] text-neutral-500 leading-relaxed">
                                SHapley Additive exPlanations (SHAP) visualizing the impact of high/low feature values on the model&apos;s risk output.
                              </p>
                            </div>
                          </div>
                        )}

                        {activePlotTab === 'testing' && (
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                            <div className="space-y-4">
                              <h4 className="text-xs font-bold text-amber-400 uppercase tracking-widest flex items-center gap-2">
                                <AlertTriangle size={15} />
                                Z-Score Dispersion & Outliers
                              </h4>
                              <div className="aspect-video border border-white/[0.06] bg-black/40 rounded-2xl p-4 flex justify-center items-center">
                                <img
                                  src={`/plots/${selectedReport.name}/outliers_boxplot.png`}
                                  alt="Outliers box plot"
                                  className="max-h-full w-auto object-contain"
                                  onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
                                />
                              </div>
                              <p className="text-[10px] text-neutral-500 leading-relaxed">
                                Boxplot visualization using standardized Z-scores to identify statistical outliers that may require clipping or log-scaling.
                              </p>
                            </div>

                            <div className="space-y-4">
                              <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-widest flex items-center gap-2">
                                <CheckCircle size={15} />
                                Feature Completeness Profile
                              </h4>
                              <div className="aspect-video border border-white/[0.06] bg-black/40 rounded-2xl p-4 flex justify-center items-center">
                                <img
                                  src={`/plots/${selectedReport.name}/missingness.png`}
                                  alt="Missingness plot"
                                  className="max-h-full w-auto object-contain"
                                  onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
                                />
                              </div>
                              <p className="text-[10px] text-neutral-500 leading-relaxed">
                                Column-wise data completeness check. Green bars indicate 100% availability; partial bars highlight features requiring imputation.
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Raw Preview (Global Footer) */}
                {selectedReport.sample_rows && selectedReport.sample_rows.length > 0 && (
                  <div className="pt-8 border-t border-white/[0.06] animate-in fade-in duration-700">
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="text-[10px] font-bold text-neutral-500 uppercase tracking-widest flex items-center gap-2">
                        <Search size={12} />
                        Raw Data Stream Preview
                      </h4>
                      <span className="text-[10px] text-neutral-600 font-mono">Sample: n=3</span>
                    </div>
                    <div className="border border-white/[0.04] rounded-2xl overflow-hidden bg-black/20">
                      <div className="overflow-x-auto custom-scrollbar">
                        <table className="w-full text-left border-collapse text-[11px]">
                          <thead>
                            <tr className="border-b border-white/[0.06] bg-white/[0.02]">
                              {Object.keys(selectedReport.sample_rows[0]).map((col) => (
                                <th key={col} className="px-4 py-3 font-mono text-neutral-400 border-r border-white/[0.03] whitespace-nowrap">
                                  {col}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-white/[0.03]">
                            {selectedReport.sample_rows.map((row, rIdx) => (
                              <tr key={rIdx} className="hover:bg-white/[0.01]">
                                {Object.values(row).map((val: any, cIdx) => (
                                  <td key={cIdx} className="px-4 py-2.5 font-mono text-neutral-300 border-r border-white/[0.03] max-w-[200px] truncate" title={String(val)}>
                                    {String(val)}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
