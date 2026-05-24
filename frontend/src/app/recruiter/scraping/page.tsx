'use client';

import { useState, useEffect, useCallback } from 'react';
import Layout from '@/components/Layout';
import { scrapingApi, ScrapedJob, ScrapeStats } from '@/services/scraping';
import { Search, RefreshCw, ExternalLink, Download, Trash2, CheckCircle, Globe, Loader2 } from 'lucide-react';

const SOURCE_OPTIONS = [
  { value: 'linkedin', label: 'LinkedIn', color: 'bg-blue-100 text-blue-700' },
  { value: 'indeed', label: 'Indeed', color: 'bg-orange-100 text-orange-700' },
];

export default function ScrapingPage() {
  const [keywords, setKeywords] = useState('');
  const [location, setLocation] = useState('France');
  const [sources, setSources] = useState<string[]>(['linkedin', 'indeed']);
  const [maxPerSource, setMaxPerSource] = useState(5);
  const [fetchDescriptions, setFetchDescriptions] = useState(false);

  const [loading, setLoading] = useState(false);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [result, setResult] = useState<{ saved: number; keywords: string } | null>(null);
  const [error, setError] = useState('');

  const [jobs, setJobs] = useState<ScrapedJob[]>([]);
  const [stats, setStats] = useState<ScrapeStats | null>(null);
  const [filterKeyword, setFilterKeyword] = useState('');
  const [filterSource, setFilterSource] = useState('');
  const [importingId, setImportingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [importedIds, setImportedIds] = useState<Set<number>>(new Set());

  const loadJobs = useCallback(async () => {
    setLoadingJobs(true);
    try {
      const [jobsRes, statsRes] = await Promise.all([
        scrapingApi.listJobs({
          keywords: filterKeyword || undefined,
          source: filterSource || undefined,
          limit: 100,
        }),
        scrapingApi.getStats(),
      ]);
      setJobs(jobsRes.data);
      setStats(statsRes.data);
      setImportedIds(new Set(jobsRes.data.filter(j => j.imported).map(j => j.id)));
    } catch {
      // silently fail on load
    } finally {
      setLoadingJobs(false);
    }
  }, [filterKeyword, filterSource]);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  const toggleSource = (src: string) => {
    setSources(prev =>
      prev.includes(src) ? prev.filter(s => s !== src) : [...prev, src]
    );
  };

  const handleScrape = async () => {
    if (!keywords.trim()) { setError('Entrez des mots-clés.'); return; }
    if (sources.length === 0) { setError('Sélectionnez au moins une source.'); return; }
    setError('');
    setResult(null);
    setLoading(true);
    try {
      const res = await scrapingApi.scrapeSync({
        keywords: keywords.trim(),
        location,
        sources,
        max_per_source: maxPerSource,
        fetch_descriptions: fetchDescriptions,
      });
      setResult(res.data);
      await loadJobs();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === 'string' ? msg : 'Erreur lors du scraping.');
    } finally {
      setLoading(false);
    }
  };

  const handleImport = async (job: ScrapedJob) => {
    setImportingId(job.id);
    try {
      await scrapingApi.importJob(job.id);
      setImportedIds(prev => new Set([...prev, job.id]));
      setJobs(prev => prev.map(j => j.id === job.id ? { ...j, imported: true } : j));
    } catch {
      alert('Erreur lors de l\'import.');
    } finally {
      setImportingId(null);
    }
  };

  const handleDelete = async (jobId: number) => {
    if (!confirm('Supprimer cette offre ?')) return;
    setDeletingId(jobId);
    try {
      await scrapingApi.deleteJob(jobId);
      setJobs(prev => prev.filter(j => j.id !== jobId));
      await scrapingApi.getStats().then(r => setStats(r.data));
    } catch {
      alert('Erreur lors de la suppression.');
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-1">
            <Globe className="h-6 w-6 text-indigo-600" />
            <h1 className="text-2xl font-bold text-gray-900">Scraping d'offres d'emploi</h1>
          </div>
          <p className="text-gray-500 text-sm">
            Récupère des offres depuis LinkedIn et Indeed, puis importe-les comme critères de matching.
          </p>
          {stats && (
            <div className="mt-4 flex flex-wrap gap-4 text-sm">
              <span className="font-medium text-gray-700">{stats.total} offres en base</span>
              {Object.entries(stats.sources).map(([src, count]) => (
                <span key={src} className={`px-2 py-0.5 rounded-full text-xs font-medium ${src === 'linkedin' ? 'bg-blue-100 text-blue-700' : 'bg-orange-100 text-orange-700'}`}>
                  {src}: {count}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Form */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-4">Lancer un scraping</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Mots-clés *</label>
              <input
                type="text"
                value={keywords}
                onChange={e => setKeywords(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleScrape()}
                placeholder="ex: data scientist python"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Localisation</label>
              <input
                type="text"
                value={location}
                onChange={e => setLocation(e.target.value)}
                placeholder="ex: Paris, France"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Sources</label>
              <div className="flex gap-2">
                {SOURCE_OPTIONS.map(s => (
                  <button
                    key={s.value}
                    onClick={() => toggleSource(s.value)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border-2 transition-all ${
                      sources.includes(s.value)
                        ? `${s.color} border-current`
                        : 'bg-gray-50 text-gray-400 border-gray-200'
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Max par source (≤ 10)</label>
              <input
                type="number"
                min={1}
                max={10}
                value={maxPerSource}
                onChange={e => setMaxPerSource(Math.min(10, Math.max(1, Number(e.target.value))))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={fetchDescriptions}
                  onChange={e => setFetchDescriptions(e.target.checked)}
                  className="w-4 h-4 rounded accent-indigo-600"
                />
                Récupérer les descriptions <span className="text-gray-400">(plus lent)</span>
              </label>
            </div>
          </div>

          {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
          {result && (
            <div className="flex items-center gap-2 text-green-700 bg-green-50 border border-green-200 rounded-lg px-4 py-2 text-sm mb-3">
              <CheckCircle className="h-4 w-4" />
              {result.saved} nouvelle{result.saved !== 1 ? 's' : ''} offre{result.saved !== 1 ? 's' : ''} sauvegardée{result.saved !== 1 ? 's' : ''} pour «&nbsp;{result.keywords}&nbsp;»
            </div>
          )}

          <button
            onClick={handleScrape}
            disabled={loading}
            className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-medium px-5 py-2.5 rounded-lg text-sm transition-colors"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            {loading ? 'Scraping en cours…' : 'Lancer le scraping'}
          </button>
        </div>

        {/* Results table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="p-4 border-b border-gray-100 flex flex-wrap items-center gap-3">
            <h2 className="text-base font-semibold text-gray-800 flex-1">Offres récupérées</h2>
            <input
              type="text"
              placeholder="Filtrer par mots-clés…"
              value={filterKeyword}
              onChange={e => setFilterKeyword(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
            <select
              value={filterSource}
              onChange={e => setFilterSource(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            >
              <option value="">Toutes les sources</option>
              <option value="linkedin">LinkedIn</option>
              <option value="indeed">Indeed</option>
            </select>
            <button onClick={loadJobs} className="p-1.5 text-gray-400 hover:text-indigo-600 transition-colors" title="Rafraîchir">
              <RefreshCw className={`h-4 w-4 ${loadingJobs ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {jobs.length === 0 ? (
            <div className="py-16 text-center text-gray-400">
              <Globe className="h-10 w-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm">Aucune offre. Lance un scraping ci-dessus.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-xs text-gray-500 uppercase tracking-wide">
                    <th className="text-left px-4 py-3 font-medium">Poste</th>
                    <th className="text-left px-4 py-3 font-medium">Entreprise</th>
                    <th className="text-left px-4 py-3 font-medium">Localisation</th>
                    <th className="text-left px-4 py-3 font-medium">Source</th>
                    <th className="text-left px-4 py-3 font-medium">Publié</th>
                    <th className="text-right px-4 py-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map(job => (
                    <tr key={job.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 max-w-xs">
                        <div className="font-medium text-gray-900 truncate" title={job.title}>{job.title}</div>
                        {job.salary_range && <div className="text-xs text-green-600 mt-0.5">{job.salary_range}</div>}
                      </td>
                      <td className="px-4 py-3 text-gray-600 max-w-[150px] truncate">{job.company || '—'}</td>
                      <td className="px-4 py-3 text-gray-600 max-w-[120px] truncate">{job.location || '—'}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          job.source === 'linkedin' ? 'bg-blue-100 text-blue-700' : 'bg-orange-100 text-orange-700'
                        }`}>
                          {job.source}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">{job.posted_at || '—'}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1">
                          {job.url && (
                            <a href={job.url} target="_blank" rel="noopener noreferrer"
                              className="p-1.5 text-gray-400 hover:text-indigo-600 transition-colors" title="Voir l'offre">
                              <ExternalLink className="h-4 w-4" />
                            </a>
                          )}
                          {importedIds.has(job.id) ? (
                            <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-green-50 text-green-700">
                              <CheckCircle className="h-3.5 w-3.5" /> Importé
                            </span>
                          ) : (
                            <button
                              onClick={() => handleImport(job)}
                              disabled={importingId === job.id}
                              title="Importer comme critère"
                              className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-indigo-50 text-indigo-700 hover:bg-indigo-100 disabled:opacity-50 transition-colors"
                            >
                              {importingId === job.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                              Importer
                            </button>
                          )}
                          <button
                            onClick={() => handleDelete(job.id)}
                            disabled={deletingId === job.id}
                            className="p-1.5 text-gray-300 hover:text-red-500 transition-colors disabled:opacity-50"
                            title="Supprimer"
                          >
                            {deletingId === job.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
