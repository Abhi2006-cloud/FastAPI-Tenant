import { useState, useEffect, useCallback } from 'react';
import { useOrg } from '../../organizations/context/OrgContext';
import { apiClient } from '../../../shared/api/client';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../../shared/components/ui/Card';
import { Button } from '../../../shared/components/ui/Button';
import { Input } from '../../../shared/components/ui/Input';
import { Modal } from '../../../shared/components/ui/Modal';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../../shared/components/ui/Table';
import { Badge } from '../../../shared/components/ui/Badge';
import { useToast } from '../../../shared/components/ui/Toast';
import { TableSkeleton } from '../../../shared/components/ui/Skeleton';
import { Users, UserPlus, ShieldAlert, Trash2, Crown, Copy, Send } from 'lucide-react';

interface Member {
  membership_id: string;
  user_id: string;
  email: string;
  role: 'owner' | 'admin' | 'member';
  created_at: string;
}

interface InvitationResult {
  email: string;
  token?: string;
  invitation_url?: string;
  delivery_status: string;
  message: string;
}

export function MembersPage() {
  const { activeOrg, userRoleInActiveOrg } = useOrg();
  const { toast } = useToast();

  const [members, setMembers] = useState<Member[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Invite Modal State
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'admin' | 'member'>('member');
  const [isInviting, setIsInviting] = useState(false);
  const [inviteResult, setInviteResult] = useState<InvitationResult | null>(null);

  // Role Change Modal
  const [editingMember, setEditingMember] = useState<Member | null>(null);
  const [selectedRole, setSelectedRole] = useState<'admin' | 'member'>('member');

  // Transfer Ownership Modal
  const [transferTarget, setTransferTarget] = useState<Member | null>(null);

  const fetchMembers = useCallback(async () => {
    if (!activeOrg) return;
    setIsLoading(true);
    try {
      const res = await apiClient.get(`/organizations/${activeOrg.id}/members`);
      setMembers(res.data);
    } catch {
      toast('error', 'Failed to load organization members');
    } finally {
      setIsLoading(false);
    }
  }, [activeOrg, toast]);

  useEffect(() => {
    fetchMembers();
  }, [fetchMembers]);

  const handleSendInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeOrg || !inviteEmail.trim()) return;
    setIsInviting(true);
    setInviteResult(null);
    try {
      const res = await apiClient.post(`/organizations/${activeOrg.id}/invite`, {
        email: inviteEmail,
        role: inviteRole,
      });
      setInviteResult(res.data);
      toast('success', 'Invitation processed successfully');
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to send invitation';
      toast('error', msg);
    } finally {
      setIsInviting(false);
    }
  };

  const handleChangeRole = async () => {
    if (!activeOrg || !editingMember) return;
    try {
      await apiClient.patch(`/organizations/${activeOrg.id}/members/${editingMember.membership_id}/role`, {
        role: selectedRole,
      });
      toast('success', 'Member role updated');
      setEditingMember(null);
      await fetchMembers();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Role change failed';
      toast('error', msg);
    }
  };

  const handleRemoveMember = async (membershipId: string) => {
    if (!activeOrg || !confirm('Are you sure you want to remove this member?')) return;
    try {
      await apiClient.delete(`/organizations/${activeOrg.id}/members/${membershipId}`);
      toast('success', 'Member removed');
      await fetchMembers();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Member removal failed';
      toast('error', msg);
    }
  };

  const handleTransferOwnership = async () => {
    if (!activeOrg || !transferTarget) return;
    try {
      await apiClient.post(`/organizations/${activeOrg.id}/transfer-ownership`, {
        new_owner_membership_id: transferTarget.membership_id,
      });
      toast('success', 'Organization ownership transferred successfully');
      setTransferTarget(null);
      await fetchMembers();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Ownership transfer failed';
      toast('error', msg);
    }
  };

  const isOwner = userRoleInActiveOrg === 'owner';

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Users className="w-6 h-6 text-blue-400" />
            Team Members & Invitations
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Manage access control, member roles, and invitations for <strong>{activeOrg?.name}</strong>
          </p>
        </div>
        <Button onClick={() => { setIsInviteOpen(true); setInviteResult(null); }} leftIcon={<UserPlus className="w-4 h-4" />}>
          Invite Member
        </Button>
      </div>

      {/* Member Roster Card */}
      <Card>
        <CardHeader>
          <CardTitle>Member Roster</CardTitle>
          <CardDescription>All users with access to this organization workspace</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton rows={4} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User / Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {members.map((member) => (
                  <TableRow key={member.membership_id}>
                    <TableCell className="font-medium text-slate-200">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 font-bold text-xs flex items-center justify-center text-blue-400">
                          {member.email[0].toUpperCase()}
                        </div>
                        <span>{member.email}</span>
                      </div>
                    </TableCell>

                    <TableCell>
                      {member.role === 'owner' && (
                        <Badge variant="warning" size="sm" className="gap-1">
                          <Crown className="w-3 h-3 text-amber-400" /> Owner
                        </Badge>
                      )}
                      {member.role === 'admin' && <Badge variant="info" size="sm">Admin</Badge>}
                      {member.role === 'member' && <Badge variant="default" size="sm">Member</Badge>}
                    </TableCell>

                    <TableCell className="text-xs text-slate-400">
                      {new Date(member.created_at).toLocaleDateString()}
                    </TableCell>

                    <TableCell className="text-right">
                      {isOwner && member.role !== 'owner' && (
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setEditingMember(member);
                              setSelectedRole(member.role === 'admin' ? 'admin' : 'member');
                            }}
                          >
                            Edit Role
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setTransferTarget(member)}
                            className="text-amber-400 hover:text-amber-300"
                            title="Make Owner"
                          >
                            <Crown className="w-3.5 h-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRemoveMember(member.membership_id)}
                            className="text-rose-400 hover:text-rose-300"
                            title="Remove Member"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Invite Member Modal */}
      <Modal
        isOpen={isInviteOpen}
        onClose={() => setIsInviteOpen(false)}
        title="Invite New Member"
        description="Send an invitation link or email to add a user to this organization."
      >
        {!inviteResult ? (
          <form onSubmit={handleSendInvite} className="space-y-4">
            <Input
              label="Email Address"
              type="email"
              placeholder="colleague@company.com"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              required
            />
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-300">Assign Role</label>
              <select
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value as 'admin' | 'member')}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100"
              >
                <option value="member">Member (standard access)</option>
                <option value="admin">Admin (manage members & files)</option>
              </select>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" type="button" onClick={() => setIsInviteOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" isLoading={isInviting} leftIcon={<Send className="w-3.5 h-3.5" />}>
                Send Invitation
              </Button>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-300 text-xs">
              <strong>{inviteResult.message}</strong>
            </div>

            {inviteResult.invitation_url && (
              <div className="space-y-1">
                <label className="text-xs text-slate-400 block font-semibold">Invitation Link</label>
                <div className="flex gap-2">
                  <Input readOnly value={inviteResult.invitation_url} />
                  <Button
                    variant="secondary"
                    onClick={() => {
                      navigator.clipboard.writeText(inviteResult.invitation_url!);
                      toast('info', 'Link copied to clipboard');
                    }}
                    leftIcon={<Copy className="w-3.5 h-3.5" />}
                  >
                    Copy
                  </Button>
                </div>
              </div>
            )}

            <div className="flex justify-end">
              <Button onClick={() => setIsInviteOpen(false)}>Done</Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Role Change Modal */}
      <Modal
        isOpen={Boolean(editingMember)}
        onClose={() => setEditingMember(null)}
        title="Change Member Role"
        description={`Update access level for ${editingMember?.email}`}
      >
        <div className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs text-slate-300 font-semibold block">Select Role</label>
            <select
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value as 'admin' | 'member')}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100"
            >
              <option value="member">Member</option>
              <option value="admin">Admin</option>
            </select>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" onClick={() => setEditingMember(null)}>
              Cancel
            </Button>
            <Button onClick={handleChangeRole}>Update Role</Button>
          </div>
        </div>
      </Modal>

      {/* Transfer Ownership Modal */}
      <Modal
        isOpen={Boolean(transferTarget)}
        onClose={() => setTransferTarget(null)}
        title="Transfer Organization Ownership"
        description="Warning: Ownership transfer is permanent."
      >
        <div className="space-y-4">
          <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-amber-300 text-xs flex items-start gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <span>
              Transferring ownership to <strong>{transferTarget?.email}</strong> will demote your role to Admin.
            </span>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" onClick={() => setTransferTarget(null)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={handleTransferOwnership}>
              Transfer Ownership
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
