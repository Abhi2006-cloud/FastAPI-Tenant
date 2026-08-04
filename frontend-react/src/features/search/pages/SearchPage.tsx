import { useState, useEffect } from 'react';
import { apiClient } from '../../../shared/api/client';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../../shared/components/ui/Card';
import { Input } from '../../../shared/components/ui/Input';
import { Badge } from '../../../shared/components/ui/Badge';
import { Alert } from '../../../shared/components/ui/Alert';
import { TableSkeleton } from '../../../shared/components/ui/Skeleton';
import { Search, Building2, Users, FolderKanban, FileSpreadsheet, AlertTriangle } from 'lucide-react';

interface SearchResultItem {
  id: string;
  type: string;
  title: string;
  subtitle?: string;
  snippet?: string;
}

export function SearchPage() {
  const [query, setQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'all' | 'organizations' | 'members' | 'files' | 'audit_logs'>('all');
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchBackendMode, setSearchBackendMode] = useState<string>('Meilisearch');

  const executeSearch = async (searchTerm: string, tab: string) => {
    if (!searchTerm.trim()) {
      setResults([]);
      return;
    }
    setIsLoading(true);
    try {
      let endpoint = `/search?q=${encodeURIComponent(searchTerm)}`;
      if (tab !== 'all') {
        endpoint = `/search/${tab}?q=${encodeURIComponent(searchTerm)}`;
      }

      const res = await apiClient.get(endpoint);
      const data = res.data;

      if (data.mode) {
        setSearchBackendMode(data.mode);
      }

      // Format response items according to tab / global search schema
      if (tab === 'all') {
        const combined: SearchResultItem[] = [];
        (data.organizations || []).forEach((o: { id: string; name: string }) =>
          combined.push({ id: o.id, type: 'organization', title: o.name, subtitle: 'Organization' })
        );
        (data.members || []).forEach((m: { id: string; email: string; role: string }) =>
          combined.push({ id: m.id, type: 'member', title: m.email, subtitle: `Role: ${m.role}` })
        );
        (data.files || []).forEach((f: { id: string; filename?: string; file_name?: string; content_type?: string }) =>
          combined.push({
            id: f.id,
            type: 'file',
            title: f.filename || f.file_name || 'File',
            subtitle: f.content_type || f.filename?.split('.').pop() || f.file_name?.split('.').pop() || 'File',
          })
        );
        (data.audit_logs || []).forEach((a: { id: string; action: string; resource_type: string }) =>
          combined.push({ id: a.id, type: 'audit_log', title: a.action, subtitle: a.resource_type })
        );
        setResults(combined);
      } else {
        const list = (data.items || []).map((item: Record<string, string>) => ({
          id: item.id,
          type: tab.slice(0, -1),
          title: item.name || item.email || item.filename || item.file_name || item.action || 'Item',
          subtitle: item.role || item.content_type || item.resource_type || '',
        }));
        setResults(list);
      }
    } catch {
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      executeSearch(query, activeTab);
    }, 300);
    return () => clearTimeout(timer);
  }, [query, activeTab]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <Search className="w-6 h-6 text-blue-400" />
          Global Search Engine
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          High-performance unified search across organizations, team members, files, and audit records
        </p>
      </div>

      {searchBackendMode && searchBackendMode !== 'Meilisearch' && (
        <Alert variant="warning" title="Search Mode Notice">
          <span className="flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            Running in <strong>{searchBackendMode}</strong> mode. Fast full-text Meilisearch indexes automatically fall back to SQL search.
          </span>
        </Alert>
      )}

      {/* Main Search Input */}
      <Card>
        <CardContent className="pt-6">
          <Input
            placeholder="Type query to search files, members, orgs..."
            leftIcon={<Search className="w-5 h-5 text-blue-400" />}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="text-base py-3"
          />

          {/* Search Category Tabs */}
          <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t border-slate-800">
            {[
              { id: 'all', label: 'All Results' },
              { id: 'organizations', label: 'Organizations' },
              { id: 'members', label: 'Members' },
              { id: 'files', label: 'Files' },
              { id: 'audit_logs', label: 'Audit Logs' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  activeTab === tab.id
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                    : 'bg-slate-900 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Search Results List */}
      <Card>
        <CardHeader>
          <CardTitle>Search Results ({results.length})</CardTitle>
          <CardDescription>
            {query ? `Showing matches for "${query}"` : 'Enter a search term above to begin'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton rows={4} />
          ) : results.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-400">
              {query ? 'No matching items found.' : 'Search index is ready.'}
            </div>
          ) : (
            <div className="space-y-3">
              {results.map((item) => (
                <div
                  key={item.id + item.type}
                  className="flex items-center justify-between p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-slate-800/40 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300">
                      {item.type === 'organization' && <Building2 className="w-4 h-4 text-blue-400" />}
                      {item.type === 'member' && <Users className="w-4 h-4 text-emerald-400" />}
                      {item.type === 'file' && <FolderKanban className="w-4 h-4 text-purple-400" />}
                      {item.type === 'audit_log' && <FileSpreadsheet className="w-4 h-4 text-amber-400" />}
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-slate-100">{item.title}</h4>
                      {item.subtitle && <p className="text-xs text-slate-400 mt-0.5">{item.subtitle}</p>}
                    </div>
                  </div>
                  <Badge variant="purple" size="sm" className="capitalize">
                    {item.type}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
