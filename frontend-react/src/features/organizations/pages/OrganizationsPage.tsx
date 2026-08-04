import { useState } from 'react';
import { useOrg } from '../context/OrgContext';
import { apiClient } from '../../../shared/api/client';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../../shared/components/ui/Card';
import { Button } from '../../../shared/components/ui/Button';
import { Input } from '../../../shared/components/ui/Input';
import { Modal } from '../../../shared/components/ui/Modal';
import { Badge } from '../../../shared/components/ui/Badge';
import { useToast } from '../../../shared/components/ui/Toast';
import { Building2, Plus, Edit2, CheckCircle2, Ticket } from 'lucide-react';

export function OrganizationsPage() {
  const { organizations, activeOrg, selectOrg, fetchOrganizations } = useOrg();
  const { toast } = useToast();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newOrgName, setNewOrgName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [renameOrgId, setRenameOrgId] = useState<string | null>(null);
  const [renameOrgName, setRenameOrgName] = useState('');

  // Accept Invitation Modal
  const [isAcceptOpen, setIsAcceptOpen] = useState(false);
  const [inviteTokenInput, setInviteTokenInput] = useState('');
  const [isAccepting, setIsAccepting] = useState(false);

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
      // ignore URL parse errors
    }
    return trimmed;
  };

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newOrgName.trim()) return;
    setIsSubmitting(true);
    try {
      await apiClient.post('/organizations', { name: newOrgName });
      toast('success', 'Organization created successfully');
      setNewOrgName('');
      setIsCreateOpen(false);
      await fetchOrganizations();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to create organization';
      toast('error', msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRenameOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!renameOrgId || !renameOrgName.trim()) return;
    setIsSubmitting(true);
    try {
      await apiClient.patch(`/organizations/${renameOrgId}`, { name: renameOrgName });
      toast('success', 'Organization renamed successfully');
      setRenameOrgId(null);
      await fetchOrganizations();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to rename organization';
      toast('error', msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAcceptInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = extractToken(inviteTokenInput);
    if (!token) {
      toast('error', 'Please enter a valid invitation token or URL');
      return;
    }
    setIsAccepting(true);
    try {
      const res = await apiClient.post('/invitations/accept', { token });
      toast('success', 'Joined organization successfully!');
      setInviteTokenInput('');
      setIsAcceptOpen(false);
      await fetchOrganizations();
      if (res.data?.organization_id) {
        selectOrg(res.data.organization_id);
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to accept invitation';
      toast('error', msg);
    } finally {
      setIsAccepting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Building2 className="w-6 h-6 text-blue-400" />
            Organization Management
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Create, switch, join, or rename your multi-tenant organizations
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => setIsAcceptOpen(true)} leftIcon={<Ticket className="w-4 h-4" />}>
            Accept Invitation
          </Button>
          <Button onClick={() => setIsCreateOpen(true)} leftIcon={<Plus className="w-4 h-4" />}>
            Create Organization
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {organizations.map((org) => {
          const isActive = activeOrg?.id === org.id;
          return (
            <Card
              key={org.id}
              className={`relative flex flex-col justify-between transition-all ${
                isActive ? 'border-blue-500/50 bg-blue-950/20' : 'hover:border-slate-700'
              }`}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      {org.name}
                      {isActive && (
                        <Badge variant="success" size="sm">
                          Active
                        </Badge>
                      )}
                    </CardTitle>
                    <CardDescription className="font-mono text-[10px] mt-1 text-slate-400">
                      ID: {org.id}
                    </CardDescription>
                  </div>
                  <button
                    onClick={() => {
                      setRenameOrgId(org.id);
                      setRenameOrgName(org.name);
                    }}
                    className="p-1.5 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800 transition-colors"
                    title="Rename organization"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex justify-end mt-4">
                  {isActive ? (
                    <Button variant="ghost" size="sm" disabled leftIcon={<CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}>
                      Selected
                    </Button>
                  ) : (
                    <Button variant="secondary" size="sm" onClick={() => selectOrg(org.id)}>
                      Select Organization
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Accept Invitation Modal */}
      <Modal
        isOpen={isAcceptOpen}
        onClose={() => setIsAcceptOpen(false)}
        title="Accept Organization Invitation"
        description="Paste an invitation token or link to join an organization."
      >
        <form onSubmit={handleAcceptInvite} className="space-y-4">
          <Input
            label="Invitation Token or URL"
            placeholder="e.g. paste full URL (http://.../invitations?token=...) or token"
            value={inviteTokenInput}
            onChange={(e) => setInviteTokenInput(e.target.value)}
            leftIcon={<Ticket className="w-4 h-4 text-slate-500" />}
            required
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" type="button" onClick={() => setIsAcceptOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isAccepting} disabled={!inviteTokenInput.trim()}>
              Join Organization
            </Button>
          </div>
        </form>
      </Modal>

      {/* Create Organization Modal */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create New Organization"
        description="Organizations isolate team members, files, and resources."
      >
        <form onSubmit={handleCreateOrg} className="space-y-4">
          <Input
            label="Organization Name"
            placeholder="e.g. Acme Corporation"
            value={newOrgName}
            onChange={(e) => setNewOrgName(e.target.value)}
            required
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" type="button" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              Create
            </Button>
          </div>
        </form>
      </Modal>

      {/* Rename Organization Modal */}
      <Modal
        isOpen={Boolean(renameOrgId)}
        onClose={() => setRenameOrgId(null)}
        title="Rename Organization"
        description="Update the display name of your organization."
      >
        <form onSubmit={handleRenameOrg} className="space-y-4">
          <Input
            label="New Organization Name"
            value={renameOrgName}
            onChange={(e) => setRenameOrgName(e.target.value)}
            required
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" type="button" onClick={() => setRenameOrgId(null)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              Save Name
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
