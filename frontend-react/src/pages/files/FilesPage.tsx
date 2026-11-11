/**
 * Endpoints used by this page:
 * - GET /files
 * - POST /files/upload
 * - GET /files/{id}/download
 * - DELETE /files/{id}
 * - GET /files/stats
 * - GET /organizations/{id}/entitlements
 */
import React, { useState, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { UploadCloud, File, Download, Trash2 } from "lucide-react";
import { apiClient, getActiveOrgId } from "../../shared/api/client.ts";
import { useOrg } from "../../shared/context/OrgContext.tsx";
import type { FileResponse } from "../../shared/api/types.ts";
import { LimitMeter } from "../../shared/components/LimitMeter.tsx";
import { ConfirmDialog } from "../../shared/components/ConfirmDialog.tsx";
import { useToast } from "../../shared/components/Toast.tsx";

export const FilesPage: React.FC = () => {
  const orgId = getActiveOrgId();
  const { entitlements } = useOrg();
  const { showToast } = useToast();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [fileToDelete, setFileToDelete] = useState<FileResponse | null>(null);

  // Fetch file list
  const { data: files = [], isLoading, refetch } = useQuery<FileResponse[]>({
    queryKey: ["files", orgId],
    queryFn: async () => {
      if (!orgId) throw new Error("No active org");
      const res = await apiClient.get<FileResponse[]>("/files");
      return res.data;
    },
    enabled: !!orgId,
  });

  const maxUploadMb = entitlements?.limits.max_upload_mb ?? 0;
  const remainingStorageMb = entitlements
    ? Math.max(0, entitlements.limits.org_storage_mb - entitlements.usage.storage_mb)
    : 0;

  const handleUpload = async (file: File) => {
    if (!orgId) return;

    const fileSizeMb = file.size / (1024 * 1024);
    if (fileSizeMb > maxUploadMb) {
      showToast(
        `File exceeds plan max upload size (${maxUploadMb} MB). Upgrade required.`,
        "error"
      );
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      await apiClient.post("/files/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      showToast(`Uploaded ${file.name} successfully.`, "success");
      refetch();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      if (axiosErr.response?.data?.detail && typeof axiosErr.response.data.detail === "string") {
        showToast(axiosErr.response.data.detail, "error");
      }
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (fileItem: FileResponse) => {
    try {
      const res = await apiClient.get(`/files/${fileItem.id}/download`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", fileItem.file_name);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      showToast("Download failed.", "error");
    }
  };

  const handleDelete = async () => {
    if (!fileToDelete) return;
    try {
      await apiClient.delete(`/files/${fileToDelete.id}`);
      showToast(`Deleted ${fileToDelete.file_name}.`, "success");
      refetch();
    } catch {
      showToast("Delete failed.", "error");
    } finally {
      setFileToDelete(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[18px] font-semibold text-[#18181B] tracking-tight">Files & Storage</h1>
          <p className="text-[13px] text-[#71717A] mt-0.5">
            Database-backed tenant file storage with strict quota enforcement.
          </p>
        </div>
        <div className="w-56">
          <LimitMeter metric="storage" />
        </div>
      </div>

      {/* Drag-and-Drop Upload Area */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          if (e.dataTransfer.files?.[0]) {
            handleUpload(e.dataTransfer.files[0]);
          }
        }}
        onClick={() => fileInputRef.current?.click()}
        className={`bg-white border-2 border-dashed rounded-[6px] p-8 text-center cursor-pointer transition-colors ${
          isDragging ? "border-[#0F766E] bg-[#F0FDFA]" : "border-[#E4E4E7] hover:border-[#A1A1AA]"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.[0]) {
              handleUpload(e.target.files[0]);
            }
          }}
        />
        <div className="flex flex-col items-center gap-2">
          <div className="w-10 h-10 rounded-full bg-[#F4F4F5] flex items-center justify-center text-[#71717A]">
            <UploadCloud className="w-5 h-5 text-[#0F766E]" />
          </div>
          <div>
            <span className="text-[13px] font-medium text-[#18181B]">
              {uploading ? "Uploading file..." : "Click or drag file here to upload"}
            </span>
            <p className="text-[12px] text-[#71717A] mt-1 tabular-nums">
              Plan limit: {maxUploadMb} MB per file • {remainingStorageMb} MB remaining in workspace quota
            </p>
          </div>
        </div>
      </div>

      {/* Files Table */}
      <div className="bg-white border border-[#E4E4E7] rounded-[6px] overflow-hidden shadow-sm">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#E4E4E7] bg-[#FAFAFA] text-[12px] font-semibold text-[#71717A]">
              <th className="py-2.5 px-4">File Name</th>
              <th className="py-2.5 px-4">Size</th>
              <th className="py-2.5 px-4">Uploaded</th>
              <th className="py-2.5 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E4E4E7] text-[13px]">
            {isLoading ? (
              [1, 2, 3].map((i) => (
                <tr key={i}>
                  <td colSpan={4} className="py-3 px-4">
                    <div className="h-4 bg-[#E4E4E7]/60 rounded animate-pulse w-48" />
                  </td>
                </tr>
              ))
            ) : files.length > 0 ? (
              files.map((file) => (
                <tr key={file.id} className="hover:bg-[#FAFAFA] transition-colors">
                  <td className="py-3 px-4 font-medium text-[#18181B] flex items-center gap-2">
                    <File className="w-4 h-4 text-[#A1A1AA] shrink-0" />
                    <span className="truncate max-w-xs">{file.file_name}</span>
                  </td>
                  <td className="py-3 px-4 text-[#71717A] tabular-nums text-[12px]">
                    {(file.file_size / (1024 * 1024)).toFixed(2)} MB
                  </td>
                  <td className="py-3 px-4 text-[#71717A] tabular-nums text-[12px]">
                    {new Date(file.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-3 px-4 text-right space-x-2">
                    <button
                      type="button"
                      onClick={() => handleDownload(file)}
                      className="inline-flex items-center gap-1 text-[12px] text-[#0F766E] hover:underline"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setFileToDelete(file)}
                      className="inline-flex items-center gap-1 text-[12px] text-[#DC2626] hover:underline"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Delete</span>
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={4} className="py-8 text-center text-[#71717A]">
                  No files uploaded yet in this workspace.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Confirm Delete Dialog */}
      {fileToDelete && (
        <ConfirmDialog
          open={!!fileToDelete}
          onOpenChange={(open) => !open && setFileToDelete(null)}
          title="Delete File"
          description={`Are you sure you want to delete ${fileToDelete.file_name}? Storage space will immediately be reclaimed.`}
          confirmWord={fileToDelete.file_name}
          confirmButtonText="Delete File"
          onConfirm={handleDelete}
        />
      )}
    </div>
  );
};
