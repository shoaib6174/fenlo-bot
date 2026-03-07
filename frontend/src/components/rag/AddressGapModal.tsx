'use client';

import { useState } from 'react';
import { X, FileText, Upload, Loader2 } from 'lucide-react';

interface AddressGapModalProps {
  gapId: string;
  queryText: string;
  kbId: string;
  onComplete: () => void;
  onClose: () => void;
}

type Mode = 'text' | 'file';

export function AddressGapModal({
  gapId,
  queryText,
  kbId,
  onComplete,
  onClose,
}: AddressGapModalProps) {
  const [mode, setMode] = useState<Mode>('text');
  const [textContent, setTextContent] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    !submitting && (mode === 'text' ? textContent.trim().length > 0 : file !== null);

  const handleSubmit = async () => {
    if (!canSubmit) return;

    setSubmitting(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('kb_id', kbId);

      if (mode === 'text') {
        formData.append('text_content', textContent.trim());
      } else if (file) {
        formData.append('file', file);
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/kb/gaps/${gapId}/address`,
        {
          method: 'POST',
          credentials: 'include',
          body: formData,
        }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.detail || `Failed to address gap (${response.status})`);
      }

      onComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-lg shadow-xl w-full max-w-lg mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Address Knowledge Gap</h2>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 rounded"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Gap context */}
        <div className="px-4 pt-4">
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
            <p className="text-sm text-amber-800">
              <span className="font-medium">Unanswered question:</span>{' '}
              &ldquo;{queryText}&rdquo;
            </p>
          </div>
        </div>

        {/* Mode tabs */}
        <div className="px-4 pt-4">
          <div className="flex border border-gray-200 rounded-lg overflow-hidden">
            <button
              onClick={() => setMode('text')}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium transition ${
                mode === 'text'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              }`}
            >
              <FileText className="w-4 h-4" />
              Write Text
            </button>
            <button
              onClick={() => setMode('file')}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium transition ${
                mode === 'file'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              }`}
            >
              <Upload className="w-4 h-4" />
              Upload File
            </button>
          </div>
        </div>

        {/* Content area */}
        <div className="p-4">
          {mode === 'text' ? (
            <textarea
              value={textContent}
              onChange={(e) => setTextContent(e.target.value)}
              placeholder="Type or paste the knowledge content that answers this question..."
              className="w-full h-40 px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              autoFocus
            />
          ) : (
            <div className="space-y-3">
              <label className="flex flex-col items-center justify-center h-40 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-400 hover:bg-blue-50/50 transition">
                <input
                  type="file"
                  accept=".pdf,.txt"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="hidden"
                />
                {file ? (
                  <div className="text-center">
                    <FileText className="w-8 h-8 text-blue-600 mx-auto mb-2" />
                    <p className="text-sm font-medium text-gray-900">{file.name}</p>
                    <p className="text-xs text-gray-500">
                      {(file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                ) : (
                  <div className="text-center">
                    <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                    <p className="text-sm text-gray-600">
                      Click to select a <span className="font-medium">.pdf</span> or{' '}
                      <span className="font-medium">.txt</span> file
                    </p>
                  </div>
                )}
              </label>
            </div>
          )}

          {error && (
            <p className="mt-3 text-sm text-red-600">{error}</p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200">
          <button
            onClick={onClose}
            disabled={submitting}
            className="px-4 py-2 text-sm text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition"
          >
            {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
            {submitting ? 'Submitting...' : 'Add to Knowledge Base'}
          </button>
        </div>
      </div>
    </div>
  );
}
