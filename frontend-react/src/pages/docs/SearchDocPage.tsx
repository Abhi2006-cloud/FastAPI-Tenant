import React from "react";
import { AlertCircle } from "lucide-react";
import { DocsLayout, DiagramContainer } from "../../shared/components/DocsLayout.tsx";

const toc = [
  { id: "architecture-overview", label: "Pipeline Architecture" },
  { id: "tenant-isolation", label: "Tenant Document Scoping" },
  { id: "circuit-breaker", label: "Circuit Breaker & Resilience" },
  { id: "zero-cost-fallback", label: "Zero-Cost Database Fallback" },
];

export const SearchDocPage: React.FC = () => {
  return (
    <DocsLayout
      title="Search Architecture & Indexing"
      summary="Technical specifications for the decoupled Meilisearch cluster, indexing queue, circuit breaker, and zero-cost SQL fallback."
      featureKey="meilisearch_search"
      tableOfContents={toc}
    >
      <blockquote>
        <div className="flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 shrink-0 text-[#0F766E] mt-0.5" />
          <div>
            <strong>Deployment Status:</strong> The Meilisearch Cloud subscription has concluded for this deployment. The backend operates in zero-cost mode using PostgreSQL pattern matching (<code className="font-mono">GET /search/basic</code>) so all search capabilities remain available without recurring fees.
          </div>
        </div>
      </blockquote>

      <h2 id="architecture-overview">Pipeline Architecture</h2>
      <p>
        In production deployments with active Meilisearch infrastructure, document mutations are decoupled from search indexing using Redis background workers. Database writes commit immediately to PostgreSQL, and an asynchronous RQ task handles index synchronization.
      </p>

      {/* Bordered Diagram Container */}
      <DiagramContainer title="Search Invalidation & Fallback Flow" minWidth={560}>
        <svg
          viewBox="0 0 600 220"
          className="w-full h-auto max-w-[600px]"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Box 1: Mutation (DB) */}
          <rect x="20" y="20" width="140" height="60" rx="4" fill="#FFFFFF" stroke="#E4E4E7" strokeWidth="1.5" />
          <text x="90" y="45" textAnchor="middle" fill="#18181B" fontSize="12" fontWeight="600">FastAPI Mutation</text>
          <text x="90" y="62" textAnchor="middle" fill="#71717A" fontSize="10">PostgreSQL Commit</text>

          {/* Arrow 1 */}
          <path d="M160 50 H210" stroke="#0F766E" strokeWidth="1.5" />

          {/* Box 2: RQ Queue */}
          <rect x="220" y="20" width="140" height="60" rx="4" fill="#FFFFFF" stroke="#E4E4E7" strokeWidth="1.5" />
          <text x="290" y="45" textAnchor="middle" fill="#18181B" fontSize="12" fontWeight="600">Async RQ Task</text>
          <text x="290" y="62" textAnchor="middle" fill="#71717A" fontSize="10">Redis Queue (search)</text>

          {/* Arrow 2 */}
          <path d="M360 50 H410" stroke="#0F766E" strokeWidth="1.5" />

          {/* Box 3: Meilisearch */}
          <rect x="420" y="20" width="160" height="60" rx="4" fill="#F0FDFA" stroke="#0F766E" strokeWidth="1.5" />
          <text x="500" y="45" textAnchor="middle" fill="#0F766E" fontSize="12" fontWeight="600">Meilisearch Cluster</text>
          <text x="500" y="62" textAnchor="middle" fill="#115E59" fontSize="10">filter: organization_id</text>

          {/* Circuit breaker fallback branch */}
          <path d="M290 80 V140 H160" stroke="#DC2626" strokeWidth="1.5" strokeDasharray="4 4" />

          {/* Box 4: Dead-Letter Failures */}
          <rect x="20" y="120" width="140" height="60" rx="4" fill="#FEF2F2" stroke="#FCA5A5" strokeWidth="1.5" />
          <text x="90" y="145" textAnchor="middle" fill="#DC2626" fontSize="12" fontWeight="600">Failure Dead-Letter</text>
          <text x="90" y="162" textAnchor="middle" fill="#991B1B" fontSize="10">search_index_failures</text>

          {/* Box 5: Basic DB Fallback */}
          <rect x="220" y="120" width="360" height="60" rx="4" fill="#FFFFFF" stroke="#E4E4E7" strokeWidth="1.5" />
          <text x="400" y="145" textAnchor="middle" fill="#18181B" fontSize="12" fontWeight="600">Zero-Cost Fallback: GET /search/basic</text>
          <text x="400" y="162" textAnchor="middle" fill="#71717A" fontSize="10">PostgreSQL ILIKE queries scoped strictly by organization_id</text>
        </svg>
      </DiagramContainer>

      <h2 id="tenant-isolation">Multi-Tenant Document Scoping</h2>
      <p>
        Multi-tenant isolation in Meilisearch is enforced by configuring <code className="font-mono">organization_id</code> as a required filterable attribute on all primary document indices:
      </p>
      <ul>
        <li><strong>Files Index (<code>files</code>):</strong> Indexes file names, paths, sizes, and upload timestamps.</li>
        <li><strong>Members Index (<code>members</code>):</strong> Indexes user emails, full names, and workspace roles.</li>
        <li><strong>Audit Logs Index (<code>audit_logs</code>):</strong> Indexes compliance events, actions, resource types, and dates.</li>
      </ul>
      <p>
        The backend search client automatically prepends <code className="font-mono">filter: organization_id = &apos;&lt;uuid&gt;&apos;</code> to every search request, ensuring cross-tenant queries are structurally rejected by the index engine.
      </p>

      <h2 id="circuit-breaker">Circuit Breaker &amp; Resilience</h2>
      <p>
        To prevent external search cluster latency or outages from degrading API responsiveness, the search client incorporates an in-memory circuit breaker pattern:
      </p>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Circuit State</th>
              <th>Behavior</th>
              <th>Transition Rule</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><code>CLOSED</code></td>
              <td>Normal operation. Search queries route to Meilisearch with Redis cache-aside.</td>
              <td>Trips to <code>OPEN</code> if 5 network errors occur within 30 seconds.</td>
            </tr>
            <tr>
              <td><code>OPEN</code></td>
              <td>Fails fast immediately. Queries bypass Meilisearch without network delay.</td>
              <td>Transitions to <code>HALF-OPEN</code> after a 30-second cooldown period.</td>
            </tr>
            <tr>
              <td><code>HALF-OPEN</code></td>
              <td>Allows a single trial request to test Meilisearch cluster recovery.</td>
              <td>Resets to <code>CLOSED</code> on success; reverts to <code>OPEN</code> on failure.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h2 id="zero-cost-fallback">Zero-Cost Database Fallback</h2>
      <p>
        When Meilisearch is offline or disabled (<code className="font-mono">SEARCH_ENABLED=false</code>), the frontend seamlessly calls the native SQL fallback endpoint:
      </p>
      <pre><code>GET /search/basic?q=query&amp;page=1&amp;page_size=20</code></pre>
      <p>
        This endpoint queries PostgreSQL directly using parameterized <code className="font-mono">ILIKE</code> filters across active tenant resources, enforcing the exact same organization boundary without requiring an external search cluster.
      </p>
    </DocsLayout>
  );
};
