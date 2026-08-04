export const queryKeys = {
  auth: {
    me: () => ['auth', 'me'] as const,
    sessions: (currentSessionId?: string) => ['auth', 'sessions', currentSessionId] as const,
  },
  organizations: {
    all: () => ['organizations'] as const,
    my: () => ['organizations', 'my'] as const,
    detail: (id: string) => ['organizations', id] as const,
  },
  memberships: {
    list: (orgId: string) => ['memberships', orgId] as const,
  },
  files: {
    list: (orgId: string) => ['files', orgId] as const,
    stats: (orgId: string) => ['files', 'stats', orgId] as const,
    detail: (fileId: string) => ['files', 'detail', fileId] as const,
  },
  search: {
    global: (query: string) => ['search', 'global', query] as const,
    category: (category: string, query: string) => ['search', category, query] as const,
  },
  audit: {
    list: (orgId: string, filters?: Record<string, unknown>) => ['audit', orgId, filters] as const,
  },
  email: {
    stats: () => ['email', 'stats'] as const,
    logs: (page: number) => ['email', 'logs', page] as const,
  },
  jobs: {
    list: () => ['jobs'] as const,
    detail: (id: string) => ['jobs', id] as const,
  },
  health: {
    status: () => ['health'] as const,
  },
};
