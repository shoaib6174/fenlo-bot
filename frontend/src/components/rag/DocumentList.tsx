'use client';

import { useState } from 'react';
import { File, Trash2, RefreshCw, Loader2, CheckCircle, XCircle } from 'lucide-react';
import type { Document } from '@/types/rag';

interface DocumentListProps {
  documents: Document[];
  onDelete?: (documentId: string) => void;
  onRetry?: (documentId: string) => void;
  readOnly?: boolean;
}

export function DocumentList({ documents, onDelete, onRetry, readOnly }: DocumentListProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [retryingId, setRetryingId] = useState<string | null>(null);

  const handleDelete = async (documentId: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return;

    setDeletingId(documentId);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/docs/${documentId}`,
        {
          method: 'DELETE',
          credentials: 'include',
        }
      );

      if (!response.ok) {
        throw new Error('Failed to delete document');
      }

      onDelete?.(documentId);
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Failed to delete document');
    } finally {
      setDeletingId(null);
    }
  };

  const handleRetry = async (documentId: string) => {
    setRetryingId(documentId);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/docs/${documentId}/retry`,
        {
          method: 'POST',
          credentials: 'include',
        }
      );

      if (!response.ok) {
        throw new Error('Failed to retry document');
      }

      onRetry?.(documentId);
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Failed to retry document');
    } finally {
      setRetryingId(null);
    }
  };

  const getStatusIcon = (status: Document['status']) => {
    switch (status) {
      case 'processing':
        return <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />;
      case 'ready':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-600" />;
    }
  };

  const getStatusBadge = (status: Document['status']) => {
    const styles = {
      processing: 'bg-blue-100 text-blue-800',
      ready: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
    };

    return (
      <span
        className={`px-2 py-1 text-xs font-semibold rounded-full ${styles[status]}`}
      >
        {status}
      </span>
    );
  };

  if (documents.length === 0) {
    return (
      <div className="text-center py-12 bg-white border border-gray-200 rounded-lg">
        <File className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-500">No documents uploaded yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {documents.map((doc) => (
        <div
          key={doc.id}
          className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-sm transition"
        >
          <div className="flex items-start gap-4">
            {/* Status Icon */}
            <div className="flex-shrink-0 pt-1">
              {getStatusIcon(doc.status)}
            </div>

            {/* Document Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-900 truncate">
                    {doc.filename}
                  </h3>
                  <p className="text-sm text-gray-500">
                    {doc.file_type.toUpperCase()} •{' '}
                    {new Date(doc.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex-shrink-0">
                  {getStatusBadge(doc.status)}
                </div>
              </div>

              {doc.status === 'ready' && doc.chunk_count && (
                <p className="text-sm text-gray-600 mb-2">
                  {doc.chunk_count} chunks indexed
                </p>
              )}

              {doc.status === 'failed' && doc.metadata_?.error != null && (
                <p className="text-sm text-red-600 mb-2">
                  Error: {String(doc.metadata_.error)}
                </p>
              )}

              {/* Actions */}
              {!readOnly && (
                <div className="flex gap-2 mt-3">
                  {doc.status === 'failed' && (
                    <button
                      onClick={() => handleRetry(doc.id)}
                      disabled={retryingId === doc.id}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-300 transition"
                    >
                      {retryingId === doc.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <RefreshCw className="w-4 h-4" />
                      )}
                      Retry
                    </button>
                  )}

                  <button
                    onClick={() => handleDelete(doc.id)}
                    disabled={deletingId === doc.id}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:bg-gray-300 transition"
                  >
                    {deletingId === doc.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                    Delete
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
