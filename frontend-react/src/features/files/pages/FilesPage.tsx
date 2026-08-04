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
import {
  FolderKanban,
  UploadCloud,
  FileText,
  FileCode,
  Image as ImageIcon,
  FileArchive,
  Download,
  Trash2,
  Eye,
  HardDrive,
  Search,
} from 'lucide-react';

interface FileItem {
  id: string;
  filename?: string;
  file_name?: string;
  size_bytes?: number;
  file_size?: number;
  content_type?: string;
  organization_id: string;
  created_at: string;
}

interface FileStats {
  total_files: number;
  total_bytes?: number;
  total_size_bytes?: number;
}

export function FilesPage() {
  const { activeOrg } = useOrg();
  const { toast } = useToast();

  const [files, setFiles] = useState<FileItem[]>([]);
  const [stats, setStats] = useState<FileStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Upload State
  const [isUploading, setIsUploading] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);

  // File Preview Modal
  const [previewFile, setPreviewFile] = useState<FileItem | null>(null);

  const getFileName = (f: FileItem) => f.filename || f.file_name || 'Unnamed file';
  const getFileSize = (f: FileItem) => f.size_bytes ?? f.file_size ?? 0;

  const fetchFilesData = useCallback(async () => {
    if (!activeOrg) return;
    setIsLoading(true);
    try {
      const [filesRes, statsRes] = await Promise.all([
        apiClient.get<FileItem[]>('/files'),
        apiClient.get<FileStats>('/files/stats'),
      ]);
      setFiles(filesRes.data);
      setStats(statsRes.data);
    } catch {
      toast('error', 'Failed to load files');
    } finally {
      setIsLoading(false);
    }
  }, [activeOrg, toast]);

  useEffect(() => {
    fetchFilesData();
  }, [fetchFilesData]);

  const handleUploadFiles = async (fileList: FileList | File[]) => {
    if (!activeOrg || fileList.length === 0) return;
    setIsUploading(true);
    try {
      for (let i = 0; i < fileList.length; i++) {
        const formData = new FormData();
        formData.append('file', fileList[i]);
        await apiClient.post('/files/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      }
      toast('success', `${fileList.length} file(s) uploaded successfully`);
      await fetchFilesData();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Upload failed';
      toast('error', msg);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDownload = async (file: FileItem) => {
    const name = getFileName(file);
    try {
      const response = await apiClient.get(`/files/${file.id}/download`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', name);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast('info', `Downloaded ${name}`);
    } catch {
      toast('error', 'Failed to download file');
    }
  };

  const handleDelete = async (fileId: string) => {
    if (!confirm('Are you sure you want to delete this file?')) return;
    try {
      await apiClient.delete(`/files/${fileId}`);
      toast('success', 'File deleted successfully');
      await fetchFilesData();
    } catch {
      toast('error', 'Failed to delete file');
    }
  };

  const formatBytes = (bytes?: number) => {
    const b = bytes ?? 0;
    if (b <= 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(b) / Math.log(k));
    return parseFloat((b / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = (filename?: string, contentType?: string) => {
    const ext = filename?.split('.').pop()?.toLowerCase();
    if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext || '') || (contentType || '').toLowerCase().includes('image')) {
      return <ImageIcon className="w-4 h-4 text-purple-400" />;
    }
    if (['js', 'ts', 'py', 'json', 'html', 'css'].includes(ext || '')) {
      return <FileCode className="w-4 h-4 text-emerald-400" />;
    }
    if (['zip', 'tar', 'gz', '7z', 'rar'].includes(ext || '')) {
      return <FileArchive className="w-4 h-4 text-amber-400" />;
    }
    return <FileText className="w-4 h-4 text-blue-400" />;
  };

  const filteredFiles = files.filter((f) =>
    getFileName(f).toLowerCase().includes((searchQuery || '').toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <FolderKanban className="w-6 h-6 text-blue-400" />
            File Manager
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Secure multi-tenant cloud storage for organization <strong>{activeOrg?.name}</strong>
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Card className="flex items-center p-4 gap-4">
          <div className="p-3 bg-blue-500/10 rounded-xl text-blue-400">
            <FolderKanban className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs text-slate-400 block font-medium">Total Stored Files</span>
            <span className="text-xl font-bold text-slate-100">{stats?.total_files || 0}</span>
          </div>
        </Card>

        <Card className="flex items-center p-4 gap-4">
          <div className="p-3 bg-emerald-500/10 rounded-xl text-emerald-400">
            <HardDrive className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs text-slate-400 block font-medium">Total Used Capacity</span>
            <span className="text-xl font-bold text-slate-100">
              {formatBytes(stats?.total_size_bytes ?? stats?.total_bytes ?? 0)}
            </span>
          </div>
        </Card>
      </div>

      {/* Drag & Drop Upload Zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragOver(false);
          if (e.dataTransfer.files) handleUploadFiles(e.dataTransfer.files);
        }}
        className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all cursor-pointer ${
          isDragOver
            ? 'border-blue-500 bg-blue-500/10 scale-[1.01]'
            : 'border-slate-800 bg-slate-900/40 hover:border-slate-700'
        }`}
      >
        <UploadCloud className="w-10 h-10 text-blue-400 mx-auto mb-2 animate-bounce" />
        <h4 className="text-sm font-semibold text-slate-200">Drag & Drop files here to upload</h4>
        <p className="text-xs text-slate-400 mt-1">Or browse files from your computer</p>
        <input
          type="file"
          multiple
          className="hidden"
          id="file-input"
          onChange={(e) => {
            if (e.target.files) handleUploadFiles(e.target.files);
          }}
        />
        <Button
          variant="secondary"
          size="sm"
          className="mt-4"
          isLoading={isUploading}
          onClick={() => document.getElementById('file-input')?.click()}
        >
          Select Files
        </Button>
      </div>

      {/* Files List Table */}
      <Card>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <CardTitle>Organization Files</CardTitle>
            <CardDescription>All uploaded files in your tenant context</CardDescription>
          </div>
          <div className="w-full sm:w-64">
            <Input
              placeholder="Search files..."
              leftIcon={<Search className="w-4 h-4" />}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton rows={4} />
          ) : filteredFiles.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-400">No files found. Upload a file to get started.</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>File Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Uploaded</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredFiles.map((file) => {
                  const name = getFileName(file);
                  const typeLabel = file.content_type
                    ? (file.content_type.split('/')[1] || file.content_type)
                    : (name.split('.').pop() || 'file');

                  return (
                    <TableRow key={file.id}>
                      <TableCell className="font-medium text-slate-200">
                        <div className="flex items-center gap-2.5">
                          {getFileIcon(name, file.content_type)}
                          <span className="truncate max-w-[200px] md:max-w-[300px]">{name}</span>
                        </div>
                      </TableCell>

                      <TableCell>
                        <Badge variant="default" size="sm">
                          {typeLabel}
                        </Badge>
                      </TableCell>

                      <TableCell className="text-xs text-slate-400">{formatBytes(getFileSize(file))}</TableCell>

                      <TableCell className="text-xs text-slate-400">
                        {new Date(file.created_at).toLocaleDateString()}
                      </TableCell>

                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setPreviewFile(file)}
                            title="View Metadata"
                          >
                            <Eye className="w-3.5 h-3.5 text-slate-400" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDownload(file)}
                            title="Download File"
                          >
                            <Download className="w-3.5 h-3.5 text-blue-400" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(file.id)}
                            title="Delete File"
                          >
                            <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* File Details Modal */}
      <Modal
        isOpen={Boolean(previewFile)}
        onClose={() => setPreviewFile(null)}
        title="File Metadata"
        description="Detailed record information from database"
      >
        {previewFile && (
          <div className="space-y-3 text-xs">
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <div>
                <span className="text-slate-400 font-semibold block">File ID:</span>
                <code className="text-blue-400">{previewFile.id}</code>
              </div>
              <div>
                <span className="text-slate-400 font-semibold block">Filename:</span>
                <span className="text-slate-100">{getFileName(previewFile)}</span>
              </div>
              <div>
                <span className="text-slate-400 font-semibold block">Content Type:</span>
                <span className="text-slate-200">{previewFile.content_type || 'application/octet-stream'}</span>
              </div>
              <div>
                <span className="text-slate-400 font-semibold block">Size:</span>
                <span className="text-slate-200">{formatBytes(getFileSize(previewFile))}</span>
              </div>
              <div>
                <span className="text-slate-400 font-semibold block">Uploaded At:</span>
                <span className="text-slate-200">{new Date(previewFile.created_at).toLocaleString()}</span>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" size="sm" onClick={() => handleDownload(previewFile)}>
                Download
              </Button>
              <Button size="sm" onClick={() => setPreviewFile(null)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
