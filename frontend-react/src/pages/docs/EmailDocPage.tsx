import React from "react";
import { AlertCircle } from "lucide-react";
import { DocsLayout, DiagramContainer } from "../../shared/components/DocsLayout.tsx";

const toc = [
  { id: "pipeline-overview", label: "Delivery Pipeline" },
  { id: "template-engine", label: "Template Engine" },
  { id: "retry-schedule", label: "Exponential Backoff Schedule" },
  { id: "rate-limiting", label: "Rate Limiting & Protection" },
];

export const EmailDocPage: React.FC = () => {
  return (
    <DocsLayout
      title="Email Delivery Architecture"
      summary="Technical specifications for background email scheduling, Jinja2 templating, retry strategies, and console fallback."
      featureKey="email_delivery"
      tableOfContents={toc}
    >
      <blockquote>
        <div className="flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 shrink-0 text-[#0F766E] mt-0.5" />
          <div>
            <strong>Deployment Status:</strong> Live email delivery via Resend requires a custom DNS verified domain. To maintain a strict zero-cost deployment, the backend runs in <code className="font-mono">console</code> mode and provides invitation tokens directly in the UI (<code className="font-mono">delivery_mode: manual</code>).
          </div>
        </div>
      </blockquote>

      <h2 id="pipeline-overview">Delivery Pipeline</h2>
      <p>
        The email delivery infrastructure decouples user actions (such as team invitations and notifications) from third-party email provider latency. Outgoing messages are enqueued into a dedicated Redis queue (<code className="font-mono">email</code>) and processed by asynchronous background workers.
      </p>

      {/* Bordered Diagram Container */}
      <DiagramContainer title="Email State Machine & Worker Pipeline" minWidth={560}>
        <svg
          viewBox="0 0 600 200"
          className="w-full h-auto max-w-[600px]"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Box 1: Enqueue */}
          <rect x="20" y="30" width="120" height="50" rx="4" fill="#FFFFFF" stroke="#E4E4E7" strokeWidth="1.5" />
          <text x="80" y="52" textAnchor="middle" fill="#18181B" fontSize="11" fontWeight="600">EmailService</text>
          <text x="80" y="68" textAnchor="middle" fill="#71717A" fontSize="9">State: QUEUED</text>

          {/* Arrow 1 */}
          <path d="M140 55 H180" stroke="#0F766E" strokeWidth="1.5" />

          {/* Box 2: RQ Queue */}
          <rect x="190" y="30" width="120" height="50" rx="4" fill="#FFFFFF" stroke="#E4E4E7" strokeWidth="1.5" />
          <text x="250" y="52" textAnchor="middle" fill="#18181B" fontSize="11" fontWeight="600">RQ Worker</text>
          <text x="250" y="68" textAnchor="middle" fill="#71717A" fontSize="9">State: PROCESSING</text>

          {/* Arrow 2 */}
          <path d="M310 55 H350" stroke="#0F766E" strokeWidth="1.5" />

          {/* Box 3: Provider (Resend / Console) */}
          <rect x="360" y="30" width="120" height="50" rx="4" fill="#F0FDFA" stroke="#0F766E" strokeWidth="1.5" />
          <text x="420" y="52" textAnchor="middle" fill="#0F766E" fontSize="11" fontWeight="600">Provider API</text>
          <text x="420" y="68" textAnchor="middle" fill="#115E59" fontSize="9">State: SENT</text>

          {/* Retry branch */}
          <path d="M420 80 V130 H250 V80" stroke="#DC2626" strokeWidth="1.5" strokeDasharray="3 3" />
          <rect x="280" y="115" width="140" height="30" rx="4" fill="#FEF2F2" stroke="#FCA5A5" />
          <text x="350" y="134" textAnchor="middle" fill="#DC2626" fontSize="10">Retry: 30s / 120s / 600s / 1800s / 3600s</text>

          {/* Final Box 4: FAILED / CANCELLED */}
          <rect x="490" y="105" width="100" height="50" rx="4" fill="#FEF2F2" stroke="#DC2626" strokeWidth="1.5" />
          <text x="540" y="128" textAnchor="middle" fill="#DC2626" fontSize="11" fontWeight="600">Max Retries</text>
          <text x="540" y="144" textAnchor="middle" fill="#991B1B" fontSize="9">State: FAILED</text>
          <path d="M420 130 H490" stroke="#DC2626" strokeWidth="1.5" />
        </svg>
      </DiagramContainer>

      <h2 id="template-engine">Template Engine</h2>
      <p>
        Email templates are compiled using Jinja2 from templates stored in <code className="font-mono">app/infrastructure/email/templates/</code>. The compiler outputs dual-format payloads containing both responsive HTML and clean plaintext fallbacks:
      </p>
      <ul>
        <li><strong>Team Invitations (<code>invitation.html</code>):</strong> Interpolates invitee email, inviter name, organization title, and the one-time acceptance link.</li>
        <li><strong>Security Alerts (<code>security_alert.html</code>):</strong> Interpolates client IP, user agent, timestamp, and device location upon sensitive account events.</li>
      </ul>

      <h2 id="retry-schedule">Exponential Backoff Schedule</h2>
      <p>
        Network or provider failures trigger an exponential backoff retry schedule managed by the background worker. The lifecycle transitions across native PostgreSQL enum states (<code className="font-mono">emailstatus</code>):
      </p>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Attempt #</th>
              <th>Retry Delay</th>
              <th>Cumulative Elapsed Time</th>
              <th>Action on Failure</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Attempt 1</td>
              <td>Immediate</td>
              <td>0 seconds</td>
              <td>Transitions to <code>PROCESSING</code>; schedules Retry 1</td>
            </tr>
            <tr>
              <td>Attempt 2</td>
              <td>30 seconds</td>
              <td>30 seconds</td>
              <td>Second delivery attempt</td>
            </tr>
            <tr>
              <td>Attempt 3</td>
              <td>120 seconds</td>
              <td>2.5 minutes</td>
              <td>Third delivery attempt</td>
            </tr>
            <tr>
              <td>Attempt 4</td>
              <td>600 seconds</td>
              <td>12.5 minutes</td>
              <td>Fourth delivery attempt</td>
            </tr>
            <tr>
              <td>Attempt 5</td>
              <td>1,800 seconds</td>
              <td>42.5 minutes</td>
              <td>Final retry before terminal state</td>
            </tr>
            <tr>
              <td>Exhausted</td>
              <td>—</td>
              <td>—</td>
              <td>Marks status <code>FAILED</code> and records error message</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h2 id="rate-limiting">Rate Limiting &amp; Protection</h2>
      <p>
        To prevent mailbox flooding and comply with transactional sending limits, the system enforces strict tenant rate limits:
      </p>
      <pre><code>ratelimit:email:&lt;organization_id&gt;:&lt;hour_timestamp&gt;</code></pre>
      <p>
        The Redis fixed-window counter enforces a default ceiling of 20 emails per hour per workspace on standard plans, preventing automated scripts from exceeding third-party provider quotas.
      </p>
    </DocsLayout>
  );
};
