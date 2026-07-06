import { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Cpu, AlertTriangle, CheckCircle, RefreshCw, BarChart3,
  HelpCircle, Activity, Info, ExternalLink, Database,
  Target, Sliders, BookOpen, Gauge
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE !== undefined ? import.meta.env.VITE_API_BASE : "http://localhost:8000";

interface ModelMetrics {
  accuracy?: number;
  precision?: number;
  recall?: number;
  f1?: number;
  roc_auc?: number;
  pr_auc?: number;
  r_squared?: number;
  mcfadden_r2?: number;
  brier_score?: number;
  n_train?: number;
  n_test?: number;
}

interface Explainability {
  gain?: Record<string, number>;
  permutation?: Record<string, number>;
  shap?: Record<string, number>;
  lime_sample?: [string, number][];
}

interface DatasetMeta {
  overview?: {
    title?: string;
    name?: string;
    domain?: string;
    source?: string;
    license?: string;
    data_type?: string;
  };
  citation?: { text: string };
  dataset_story?: string;
}

interface ModelReport {
  provider_name: string;
  display_name: string;
  risk_category: string;
  model_type: string;
  model_info: {
    model_path?: string;
    model_loaded?: boolean;
    mode?: string;
    note?: string;
  };
  features: string[] | null;
  metrics: ModelMetrics | null;
  explainability: Explainability | null;
  input_description?: string;
  collection_description?: string;
  dataset_name?: string | null;
  dataset_meta?: DatasetMeta | null;
}

type MainTab = 'overview' | 'inputs' | 'explainability' | 'training';

export default function ModelIntelligence() {
  const [reports, setReports] = useState<ModelReport[]>([]);
  const [selectedName, setSelectedName] = useState<string>('');
  const [mainTab, setMainTab] = useState<MainTab>('overview');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API_BASE}/model-reports`);
      setReports(res.data);
      if (res.data.length > 0) {
        const names = res.data.map((r: ModelReport) => r.provider_name);
        if (!names.includes(selectedName)) {
          setSelectedName(res.data[0].provider_name);
        }
      }
    } catch (err) {
      console.error("Failed to fetch model reports", err);
      setError("Failed to load model intelligence reports from backend API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const selected = reports.find(r => r.provider_name === selectedName);

  const statusBadge = (info: ModelReport['model_info']) => {
    if (info.mode === 'ml' && info.model_loaded) {
      return { label: 'ML Model Active', color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' };
    }
    if (info.mode === 'rules') {
      return { label: 'Rule-Based', color: 'bg-indigo-50 text-indigo-400 border-indigo-200' };
    }
    return { label: 'Fallback Mode', color: 'bg-amber-500/10 text-amber-400 border-amber-500/20' };
  };

  const renderBarList = (data: Record<string, number> | undefined, label: string, color: string) => {
    if (!data) return null;
    const entries = Object.entries(data).sort((a, b) => b[1] - a[1]).slice(0, 12);
    const max = Math.max(...entries.map(([, v]) => Math.abs(v)), 1e-9);
    return (
      <div className="space-y-3">
        <h4 className="text-xs font-bold text-slate-600 uppercase tracking-widest">{label}</h4>
        <div className="space-y-2">
          {entries.map(([k, v]) => (
            <div key={k} className="flex items-center gap-3">
              <span className="text-[11px] font-mono text-slate-600 w-40 truncate" title={k}>{k}</span>
              <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className={`h-full rounded-full ${color}`}
                  style={{ width: `${Math.max((Math.abs(v) / max) * 100, 2)}%` }}
                />
              </div>
              <span className="text-[10px] font-mono text-slate-500 w-16 text-right">{v.toFixed(4)}</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 flex items-center gap-3">
            <div className="p-2 rounded-xl bg-teal-500/10 text-teal-400 border border-teal-500/20">
              <Cpu size={24} />
            </div>
            Model Intelligence Portal
          </h1>
          <p className="text-slate-600 text-sm">
            Live registry of every ML model backing AURA's risk providers — performance, explainability, inputs, and training provenance.
          </p>
        </div>
        <button
          onClick={fetchReports}
          className="flex items-center justify-center gap-2 rounded-xl bg-white border border-slate-200 shadow-sm hover:bg-slate-50 border border-slate-200 hover:border-slate-300 px-5 py-2.5 text-sm font-semibold text-slate-700 transition-all active:scale-95"
        >
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {loading && reports.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-32 space-y-4">
          <RefreshCw size={48} className="animate-spin text-teal-400" />
          <p className="text-slate-700 font-medium">Loading model registry...</p>
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-8 flex flex-col items-center text-center gap-4">
          <AlertTriangle className="text-rose-400" size={48} />
          <div>
            <h3 className="text-lg font-bold text-rose-700">Registry Access Denied</h3>
            <p className="text-sm text-slate-600 max-w-md mt-2">{error}</p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Sidebar */}
          <div className="lg:col-span-3 space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-white border border-slate-200 shadow-sm p-1.5 overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
                <span className="text-[11px] font-bold uppercase tracking-widest text-slate-500">Live Models</span>
                <span className="text-[11px] font-mono text-teal-500/80 bg-teal-500/5 px-2 py-0.5 rounded-full border border-teal-500/10">
                  {reports.length} Providers
                </span>
              </div>
              <div className="max-h-[calc(100vh-280px)] overflow-y-auto custom-scrollbar p-1.5 space-y-1">
                {reports.map((report) => {
                  const badge = statusBadge(report.model_info);
                  return (
                    <button
                      key={report.provider_name}
                      onClick={() => setSelectedName(report.provider_name)}
                      className={`w-full text-left px-3.5 py-3 rounded-xl text-sm transition-all group ${
                        selectedName === report.provider_name
                          ? 'bg-teal-500/10 text-teal-700 border border-teal-500/20 shadow-[0_0_20px_-12px_rgba(20,184,166,0.3)]'
                          : 'text-slate-600 hover:text-slate-600 hover:bg-white shadow-sm border border-slate-200 border border-transparent'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold truncate">{report.display_name}</span>
                        {selectedName === report.provider_name && <div className="w-1.5 h-1.5 rounded-full bg-teal-400 shadow-[0_0_8px_rgba(45,212,191,0.5)]" />}
                      </div>
                      <div className="flex items-center gap-2 mt-1.5 opacity-80">
                        <span className={`text-[9px] uppercase tracking-tighter px-1.5 py-0.5 rounded border ${badge.color}`}>{badge.label}</span>
                        <span className="text-[10px] text-slate-500 font-mono">{report.model_type}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Main */}
          <div className="lg:col-span-9 space-y-6 min-h-screen">
            {selected && (
              <>
                {/* Executive Header */}
                <div className="rounded-2xl border border-slate-200 bg-slate-50 border border-slate-200 p-8 relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-8 opacity-[0.03] pointer-events-none">
                    <Cpu size={160} />
                  </div>
                  <div className="relative z-10 flex flex-col md:flex-row justify-between items-start gap-6">
                    <div className="space-y-3 max-w-2xl">
                      <div className="flex items-center gap-3">
                        <span className="px-2.5 py-0.5 rounded-full bg-teal-500/10 text-teal-400 text-[10px] font-bold uppercase tracking-wider border border-teal-500/20">
                          {selected.risk_category}
                        </span>
                        <span className="text-slate-500 text-xs font-mono">
                          {selected.provider_name}
                        </span>
                      </div>
                      <h2 className="text-4xl font-extrabold text-slate-900 tracking-tight leading-tight">
                        {selected.display_name}
                      </h2>
                      <p className="text-sm text-slate-700 leading-relaxed border-l-2 border-teal-500/30 pl-4">
                        {selected.collection_description || "Provider description pending."}
                      </p>
                    </div>
                    <div className="shrink-0 flex flex-col items-end gap-2 text-right">
                      <div className="text-[11px] font-bold uppercase tracking-widest text-slate-500">Algorithm</div>
                      <div className="px-4 py-2 rounded-xl border text-xl font-bold bg-indigo-50 text-indigo-700 border-indigo-200 font-mono">
                        {selected.model_type}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Tabs */}
                <div className="flex p-1.5 rounded-2xl bg-white border border-slate-200 shadow-sm border border-slate-200 overflow-x-auto custom-scrollbar">
                  {[
                    { key: 'overview', label: 'Overview & Metrics', icon: Gauge },
                    { key: 'inputs', label: 'Inputs & Features', icon: Sliders },
                    { key: 'explainability', label: 'Explainability', icon: HelpCircle },
                    { key: 'training', label: 'Training Data', icon: BookOpen },
                  ].map((tab) => (
                    <button
                      key={tab.key}
                      onClick={() => setMainTab(tab.key as MainTab)}
                      className={`flex items-center gap-2 px-6 py-3 rounded-xl text-xs font-bold uppercase tracking-widest transition-all whitespace-nowrap ${
                        mainTab === tab.key
                          ? 'bg-neutral-800 text-teal-400 shadow-lg border border-slate-200'
                          : 'text-slate-500 hover:text-slate-700'
                      }`}
                    >
                      <tab.icon size={14} />
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* Content */}
                <div className="min-h-[500px]">
                  {mainTab === 'overview' && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in fade-in duration-500">
                      {/* Performance Metrics */}
                      <div className="rounded-2xl border border-slate-200 bg-slate-100 border border-slate-200 overflow-hidden">
                        <div className="px-6 py-4 border-b border-slate-200 bg-slate-100">
                          <h3 className="text-xs font-bold uppercase tracking-widest text-slate-700 flex items-center gap-2">
                            <BarChart3 size={14} className="text-teal-400" />
                            Validation Performance
                          </h3>
                        </div>
                        <div className="p-6">
                          {selected.metrics ? (
                            <div className="grid grid-cols-3 gap-4">
                              {[
                                { label: 'Accuracy', value: selected.metrics.accuracy },
                                { label: 'Precision', value: selected.metrics.precision },
                                { label: 'Recall', value: selected.metrics.recall },
                                { label: 'F1 Score', value: selected.metrics.f1 },
                                { label: 'ROC-AUC', value: selected.metrics.roc_auc },
                                { label: 'PR-AUC', value: selected.metrics.pr_auc },
                                { label: 'R² (Pseudo)', value: selected.metrics.r_squared, highlight: true },
                                { label: 'McFadden R²', value: selected.metrics.mcfadden_r2 },
                                { label: 'Brier Score', value: selected.metrics.brier_score },
                              ].filter((m) => m.value !== undefined && m.value !== null).map((m) => (
                                <div
                                  key={m.label}
                                  className={`text-center p-4 rounded-xl bg-black/30 border ${m.highlight ? 'border-teal-500/30 ring-1 ring-teal-500/20' : 'border-slate-200'}`}
                                >
                                  <div className={`text-2xl font-extrabold font-mono ${m.highlight ? 'text-teal-700' : 'text-teal-400'}`}>
                                    {m.value!.toFixed(3)}
                                  </div>
                                  <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mt-1">{m.label}</div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="flex items-center gap-3 text-slate-600 text-sm py-4">
                              <Info size={16} className="text-indigo-400" />
                              No supervised validation metrics — this provider runs on deterministic rules, not a trained model.
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Deployment Status */}
                      <div className="rounded-2xl border border-slate-200 bg-slate-100 border border-slate-200 overflow-hidden">
                        <div className="px-6 py-4 border-b border-slate-200 bg-slate-100">
                          <h3 className="text-xs font-bold uppercase tracking-widest text-slate-700 flex items-center gap-2">
                            <Activity size={14} className="text-teal-400" />
                            Deployment Status
                          </h3>
                        </div>
                        <div className="p-6 space-y-4">
                          <div className="flex items-center gap-4">
                            {selected.model_info.model_loaded || selected.model_info.mode === 'rules' ? (
                              <div className="w-10 h-10 rounded-full bg-emerald-500/10 text-emerald-400 flex items-center justify-center border border-emerald-500/20 shrink-0">
                                <CheckCircle size={20} />
                              </div>
                            ) : (
                              <div className="w-10 h-10 rounded-full bg-amber-500/10 text-amber-400 flex items-center justify-center border border-amber-500/20 shrink-0">
                                <AlertTriangle size={20} />
                              </div>
                            )}
                            <div>
                              <h4 className="text-sm font-bold text-slate-900">
                                {selected.model_info.mode === 'ml' ? 'Model Loaded & Serving' :
                                 selected.model_info.mode === 'rules' ? 'Rule Engine Active' : 'Fallback Heuristics Active'}
                              </h4>
                              <p className="text-xs text-slate-600 mt-0.5">{selected.model_info.note || '—'}</p>
                            </div>
                          </div>
                          {selected.model_info.model_path && (
                            <div className="flex justify-between items-center py-2 border-t border-slate-200">
                              <span className="text-[11px] font-bold text-slate-500 uppercase font-semibold tracking-wider">Artifact Path</span>
                              <span className="text-xs font-mono text-teal-400 truncate max-w-[220px]">{selected.model_info.model_path}</span>
                            </div>
                          )}
                          <div className="flex justify-between items-center py-2 border-t border-slate-200">
                            <span className="text-[11px] font-bold text-slate-500 uppercase font-semibold tracking-wider">Risk Category</span>
                            <span className="text-xs font-mono text-slate-600">{selected.risk_category}</span>
                          </div>
                          <div className="flex justify-between items-center py-2 border-t border-slate-200">
                            <span className="text-[11px] font-bold text-slate-500 uppercase font-semibold tracking-wider">Feature Count</span>
                            <span className="text-xs font-mono text-slate-600">{selected.features ? selected.features.length : 'Text / N/A'}</span>
                          </div>
                          {selected.metrics?.n_train !== undefined && (
                            <div className="flex justify-between items-center py-2 border-t border-slate-200">
                              <span className="text-[11px] font-bold text-slate-500 uppercase font-semibold tracking-wider">Train / Test Rows</span>
                              <span className="text-xs font-mono text-slate-600">
                                {selected.metrics.n_train?.toLocaleString()} / {selected.metrics.n_test?.toLocaleString()}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Description */}
                      <div className="rounded-2xl border border-slate-200 bg-slate-100 border border-slate-200 overflow-hidden md:col-span-2">
                        <div className="px-6 py-4 border-b border-slate-200 bg-slate-100 flex items-center gap-3">
                          <div className="shrink-0 p-2 rounded-lg bg-indigo-50 text-indigo-400 border border-indigo-200">
                            <Target size={16} />
                          </div>
                          <h3 className="text-xs font-bold uppercase tracking-widest text-slate-700">What This Model Decides</h3>
                        </div>
                        <div className="p-6">
                          <p className="text-sm text-slate-700 leading-relaxed">{selected.input_description}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {mainTab === 'inputs' && (
                    <div className="rounded-2xl border border-slate-200 bg-slate-100 border border-slate-200 overflow-hidden animate-in slide-in-from-bottom-2 duration-500">
                      <div className="px-6 py-5 border-b border-slate-200 bg-white shadow-sm border border-slate-200">
                        <h3 className="text-xs font-bold uppercase tracking-widest text-slate-700 flex items-center gap-2">
                          <Sliders size={14} className="text-teal-400" />
                          Input Feature Schema
                        </h3>
                        <p className="text-xs text-slate-500 mt-2 max-w-3xl">{selected.collection_description}</p>
                      </div>

                      {selected.features ? (
                        <div className="overflow-x-auto custom-scrollbar">
                          <table className="w-full text-left border-collapse">
                            <thead>
                              <tr className="bg-white shadow-sm border border-slate-200 text-[10px] uppercase tracking-widest text-slate-500 font-bold border-b border-slate-200">
                                <th className="px-6 py-3 w-16">#</th>
                                <th className="px-6 py-3">Feature Name</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-200">
                              {selected.features.map((f, i) => (
                                <tr key={f} className="hover:bg-white shadow-sm border border-slate-200 transition-colors">
                                  <td className="px-6 py-2.5 text-[11px] font-mono text-slate-500">{i + 1}</td>
                                  <td className="px-6 py-2.5 font-mono text-sm text-slate-600">{f}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="p-8 text-sm text-slate-600">
                          This provider does not consume a fixed tabular feature vector — see the description above for its raw input fields.
                        </div>
                      )}
                    </div>
                  )}

                  {mainTab === 'explainability' && (
                    <div className="space-y-6 animate-in fade-in duration-500">
                      {selected.explainability ? (
                        <div className="rounded-2xl border border-slate-200 bg-slate-100 border border-slate-200 p-8 grid grid-cols-1 md:grid-cols-2 gap-10">
                          {renderBarList(selected.explainability.shap, 'SHAP — Mean Absolute Impact', 'bg-purple-500')}
                          {renderBarList(selected.explainability.gain, 'Gain — Tree Split Importance', 'bg-teal-500')}
                        </div>
                      ) : (
                        <div className="rounded-2xl border border-slate-200 bg-slate-100 border border-slate-200 p-8 flex items-center gap-3 text-sm text-slate-600">
                          <Info size={16} className="text-indigo-400" />
                          No raw SHAP/gain values cached for this provider — see the visual plots from its training dataset below.
                        </div>
                      )}

                      {selected.dataset_name && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                          <div className="space-y-3">
                            <h4 className="text-xs font-bold text-purple-400 uppercase tracking-widest flex items-center gap-2">
                              <HelpCircle size={15} />
                              SHAP Global Summary ({selected.dataset_name})
                            </h4>
                            <div className="aspect-video border border-slate-200 bg-white border border-slate-300 rounded-2xl p-4 flex justify-center items-center">
                              <img
                                src={`/plots/${selected.dataset_name}/shap_summary.png`}
                                alt="SHAP summary plot"
                                className="max-h-full w-auto object-contain"
                                onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
                              />
                            </div>
                          </div>
                          <div className="space-y-3">
                            <h4 className="text-xs font-bold text-purple-400 uppercase tracking-widest flex items-center gap-2">
                              <BarChart3 size={15} />
                              Feature Importance ({selected.dataset_name})
                            </h4>
                            <div className="aspect-video border border-slate-200 bg-white border border-slate-300 rounded-2xl p-4 flex justify-center items-center">
                              <img
                                src={`/plots/${selected.dataset_name}/feature_importance.png`}
                                alt="Feature importance plot"
                                className="max-h-full w-auto object-contain"
                                onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
                              />
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {mainTab === 'training' && (
                    <div className="rounded-2xl border border-slate-200 bg-slate-100 border border-slate-200 p-10 animate-in zoom-in-95 duration-500">
                      {selected.dataset_meta ? (
                        <div className="max-w-3xl space-y-8">
                          <div className="space-y-4">
                            <h3 className="text-xs font-bold uppercase tracking-widest text-teal-400">Training Dataset</h3>
                            <h2 className="text-3xl font-bold text-slate-900 leading-tight">
                              {selected.dataset_meta.overview?.title || selected.dataset_meta.overview?.name}
                            </h2>
                            <div className="flex flex-wrap gap-4 text-sm text-slate-600 font-medium">
                              <div className="flex items-center gap-1.5"><Database size={14} /> Domain: {selected.dataset_meta.overview?.domain}</div>
                              <div className="flex items-center gap-1.5"><Info size={14} /> Type: {selected.dataset_meta.overview?.data_type}</div>
                              <div className="flex items-center gap-1.5"><Activity size={14} /> License: {selected.dataset_meta.overview?.license}</div>
                            </div>
                          </div>

                          <div className="space-y-4 pt-8 border-t border-slate-200">
                            <h4 className="text-xs font-bold uppercase tracking-widest text-slate-500">Academic Citation</h4>
                            <div className="p-6 rounded-2xl bg-white border border-slate-300 border border-slate-200 font-mono text-sm text-slate-700 leading-relaxed italic">
                              &quot;{selected.dataset_meta.citation?.text || "Citation available in metadata directory."}&quot;
                            </div>
                          </div>

                          <div className="pt-6">
                            <a
                              href={selected.dataset_meta.overview?.source}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-teal-500 text-black font-bold text-xs uppercase tracking-widest hover:bg-teal-400 transition-all shadow-lg shadow-teal-500/20 active:scale-95"
                            >
                              Access Original Repository
                              <ExternalLink size={14} />
                            </a>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-center gap-3 text-sm text-slate-600">
                          <Info size={16} className="text-indigo-400" />
                          This provider is rule-based and was not trained on a dataset.
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
