"use client";

import { useState, useRef } from "react";
import { Upload, FileText, Check, AlertCircle } from "lucide-react";
import Link from "next/link";

interface Props {
  onComplete: () => void;
}

export default function FirstDocumentStep({ onComplete }: Props) {
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState(false);
  const [fileName, setFileName] = useState("");
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const getOrCreateKb = async (apiUrl: string): Promise<string | null> => {
    // Try to get existing KB
    const listRes = await fetch(`${apiUrl}/api/v1/kb`, {
      credentials: "include",
    });
    if (listRes.ok) {
      const kbs = await listRes.json();
      if (Array.isArray(kbs) && kbs.length > 0) {
        return kbs[0].id;
      }
    }

    // Create a new KB
    const createRes = await fetch(`${apiUrl}/api/v1/kb/`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "My Knowledge Base" }),
    });
    if (createRes.ok) {
      const kb = await createRes.json();
      return kb.id;
    }

    return null;
  };

  const handleUpload = async (file: File) => {
    setUploading(true);
    setFileName(file.name);
    setError("");
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";

      // Ensure a KB exists and get its ID
      const kbId = await getOrCreateKb(apiUrl);
      if (!kbId) {
        setError("Could not create knowledge base. Please try again.");
        setUploading(false);
        return;
      }

      const formData = new FormData();
      formData.append("file", file);
      formData.append("kb_id", kbId);

      const response = await fetch(`${apiUrl}/api/v1/docs/upload`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });

      if (response.ok) {
        setUploaded(true);
        onComplete();
      } else {
        const data = await response.json().catch(() => null);
        setError(data?.detail || `Upload failed (${response.status})`);
      }
    } catch {
      setError("Network error. Please check your connection and try again.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="mx-auto w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center mb-3">
          <Upload className="w-6 h-6 text-indigo-600" />
        </div>
        <h2 className="text-lg font-semibold text-gray-900">Upload Your First Document</h2>
        <p className="text-sm text-gray-500 mt-1">
          Add a PDF, DOCX, or text file to train your bot
        </p>
      </div>

      <input
        ref={fileRef}
        type="file"
        accept=".pdf,.docx,.doc,.txt,.md"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleUpload(file);
        }}
      />

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {uploaded ? (
        <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-lg">
          <Check className="w-5 h-5 text-green-600 shrink-0" />
          <div>
            <p className="text-sm font-medium text-green-800">{fileName} uploaded</p>
            <p className="text-xs text-green-600">Processing in background...</p>
          </div>
        </div>
      ) : (
        <button
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="w-full border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 hover:bg-blue-50 transition disabled:opacity-50"
        >
          <FileText className="w-8 h-8 text-gray-400 mx-auto mb-2" />
          <p className="text-sm font-medium text-gray-700">
            {uploading ? "Uploading..." : "Click to select a file"}
          </p>
          <p className="text-xs text-gray-400 mt-1">PDF, DOCX, TXT (max 50MB)</p>
        </button>
      )}

      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-400">
          You can also upload from the{" "}
          <Link href="/kb" className="text-blue-600 hover:underline">
            Knowledge Base
          </Link>
          .
        </p>
        <button
          onClick={onComplete}
          className="text-xs text-gray-400 hover:text-gray-600 transition"
        >
          Skip this step
        </button>
      </div>
    </div>
  );
}
