'use client';

import { useState, useRef } from 'react';
import { Upload, File, X, Loader2, CheckCircle, XCircle } from 'lucide-react';
import type { Document } from '@/types/rag';

interface DocumentUploadProps {
  kbId: string;
  onUploadComplete?: () => void;
}

export function DocumentUpload({ kbId, onUploadComplete }: DocumentUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{
    [key: string]: { status: 'uploading' | 'success' | 'error'; message?: string };
  }>({});
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    await uploadFiles(files);
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const files = Array.from(e.target.files);
    await uploadFiles(files);
  };

  const uploadFiles = async (files: File[]) => {
    setUploading(true);

    for (const file of files) {
      try {
        setUploadProgress((prev) => ({
          ...prev,
          [file.name]: { status: 'uploading' },
        }));

        const formData = new FormData();
        formData.append('file', file);
        formData.append('kb_id', kbId);

        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/docs/upload`,
          {
            method: 'POST',
            credentials: 'include',
            body: formData,
          }
        );

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || 'Upload failed');
        }

        setUploadProgress((prev) => ({
          ...prev,
          [file.name]: { status: 'success' },
        }));
      } catch (error) {
        setUploadProgress((prev) => ({
          ...prev,
          [file.name]: {
            status: 'error',
            message: error instanceof Error ? error.message : 'Upload failed',
          },
        }));
      }
    }

    setUploading(false);
    onUploadComplete?.();

    // Clear progress after 3 seconds
    setTimeout(() => {
      setUploadProgress({});
    }, 3000);
  };

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition ${
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.txt"
          onChange={handleFileSelect}
          className="hidden"
        />

        <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <p className="text-lg font-semibold text-gray-700 mb-2">
          Drop files here or click to browse
        </p>
        <p className="text-sm text-gray-500">
          Supports PDF, DOCX, and TXT files (max 50MB each)
        </p>
      </div>

      {/* Upload Progress */}
      {Object.keys(uploadProgress).length > 0 && (
        <div className="space-y-2">
          {Object.entries(uploadProgress).map(([filename, progress]) => (
            <div
              key={filename}
              className="flex items-center gap-3 p-3 bg-white border border-gray-200 rounded-lg"
            >
              <File className="w-5 h-5 text-gray-400" />
              <span className="flex-1 text-sm truncate">{filename}</span>
              {progress.status === 'uploading' && (
                <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
              )}
              {progress.status === 'success' && (
                <CheckCircle className="w-5 h-5 text-green-600" />
              )}
              {progress.status === 'error' && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-red-600">{progress.message}</span>
                  <XCircle className="w-5 h-5 text-red-600" />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
