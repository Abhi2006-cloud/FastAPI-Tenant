import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/context/AuthContext';
import { useOrg } from '../../organizations/context/OrgContext';
import { apiClient } from '../../../shared/api/client';
import { Button } from '../../../shared/components/ui/Button';
import { Input } from '../../../shared/components/ui/Input';
import { Alert } from '../../../shared/components/ui/Alert';
import { CheckCircle2, ShieldAlert, Loader2, Building2, Ticket, ArrowRight, LogIn, UserPlus } from 'lucide-react';

export function AcceptInvitePage() {
  const [searchParams] = useSearchParams();
  const urlToken = searchParams.get('token') || '';
  const { authState, user } = useAuth();
  const { fetchOrganizations, selectOrg } = useOrg();
  const navigate = useNavigate();

  const [inputVal, setInputVal] = useState(urlToken);
  const [status, setStatus] = useState<'idle' | 'accepting' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Extract token from either raw string or full URL string
  const extractToken = (raw: string): string => {
    const trimmed = raw.trim();
    if (!trimmed) return '';
    try {
      if (trimmed.includes('http://') || trimmed.includes('https://') || trimmed.includes('?token=')) {
        const urlObj = new URL(trimmed.startsWith('http') ? trimmed : `http://dummy.com${trimmed.startsWith('/') ? '' : '/'}${trimmed}`);
        const tokenParam = urlObj.searchParams.get('token');
        if (tokenParam) return tokenParam;
      }
    } catch {
      // ignore URL parse error
    }
    return trimmed;
  };

  const handleAccept = async (tokenToUse?: string) => {
    const token = extractToken(tokenToUse || inputVal);
    if (!token) {
      setErrorMessage('Please enter or paste a valid invitation token or URL.');
      setStatus('error');
      return;
    }

    if (authState !== 'AUTHENTICATED') {
      return;
    }

    setStatus('accepting');
    setErrorMessage(null);
    try {
      const res = await apiClient.post('/invitations/accept', { token });
      setStatus('success');
      if (res.data?.organization_id) {
        await fetchOrganizations();
        selectOrg(res.data.organization_id);
      } else {
        await fetchOrganizations();
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to accept invitation. Token may be invalid, expired, or already used.';
      setErrorMessage(msg);
      setStatus('error');
    }
  };

  useEffect(() => {
    if (urlToken && authState === 'AUTHENTICATED' && status === 'idle') {
      handleAccept(urlToken);
    }
  }, [urlToken, authState]);

  const activeToken = extractToken(inputVal);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4">
      <div className="glass-panel max-w-lg w-full p-8 rounded-2xl border border-slate-800 text-center space-y-6 shadow-2xl">
        <div className="w-14 h-14 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center mx-auto shadow-inner">
          <Building2 className="w-7 h-7" />
        </div>

        <div>
          <h2 className="text-xl font-bold text-slate-100">Join Organization Workspace</h2>
          <p className="text-xs text-slate-400 mt-1">
            Accept an invitation to collaborate with your organization team
          </p>
        </div>

        {/* Input Form for pasting Token or Invitation Link */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleAccept();
          }}
          className="space-y-4 text-left"
        >
          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1.5 flex items-center justify-between">
              <span>Invitation Token or Link</span>
              <span className="text-[10px] text-slate-500 font-mono">Paste link or token</span>
            </label>
            <Input
              placeholder="e.g. paste link (http://.../invitations?token=...) or token"
              leftIcon={<Ticket className="w-4 h-4 text-slate-500" />}
              value={inputVal}
              onChange={(e) => {
                setInputVal(e.target.value);
                if (status !== 'idle') setStatus('idle');
              }}
              disabled={status === 'accepting'}
            />
          </div>

          {authState !== 'AUTHENTICATED' ? (
            <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl space-y-3">
              <div className="flex items-center gap-2 text-amber-300 text-xs font-medium">
                <ShieldAlert className="w-4 h-4 shrink-0" />
                <span>Authentication Required</span>
              </div>
              <p className="text-xs text-slate-400">
                You need to log in to your account before accepting this organization invitation.
              </p>
              <div className="flex gap-2 pt-1">
                <Button
                  type="button"
                  size="sm"
                  className="flex-1"
                  leftIcon={<LogIn className="w-3.5 h-3.5" />}
                  onClick={() => navigate(`/login?redirect=${encodeURIComponent(`/invitations?token=${activeToken}`)}`)}
                >
                  Log In
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="flex-1"
                  leftIcon={<UserPlus className="w-3.5 h-3.5" />}
                  onClick={() => navigate(`/register?redirect=${encodeURIComponent(`/invitations?token=${activeToken}`)}`)}
                >
                  Register
                </Button>
              </div>
            </div>
          ) : (
            <Button
              type="submit"
              className="w-full"
              isLoading={status === 'accepting'}
              disabled={!activeToken}
              leftIcon={<CheckCircle2 className="w-4 h-4" />}
            >
              Accept Invitation
            </Button>
          )}
        </form>

        {status === 'accepting' && (
          <div className="space-y-3 py-2">
            <Loader2 className="w-6 h-6 text-blue-400 animate-spin mx-auto" />
            <p className="text-xs text-slate-400">Processing organization membership...</p>
          </div>
        )}

        {status === 'success' && (
          <div className="space-y-4">
            <Alert variant="success" title="Invitation Accepted!">
              You have successfully joined the organization workspace as <strong>{user?.email}</strong>.
            </Alert>
            <Button onClick={() => navigate('/')} className="w-full" rightIcon={<ArrowRight className="w-4 h-4" />}>
              Go to Workspace Dashboard
            </Button>
          </div>
        )}

        {status === 'error' && (
          <div className="space-y-4">
            <Alert variant="danger" title="Acceptance Failed">
              {errorMessage}
            </Alert>
            {authState === 'AUTHENTICATED' && (
              <Button onClick={() => navigate('/')} variant="secondary" className="w-full">
                Return to Workspace
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
