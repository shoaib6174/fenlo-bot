'use client';

import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DocumentUpload } from '@/components/rag/DocumentUpload';
import { DocumentList } from '@/components/rag/DocumentList';
import { KnowledgeGapsList } from '@/components/rag/KnowledgeGapsList';
import { AddressGapModal } from '@/components/rag/AddressGapModal';
import { Loader2, AlertCircle, FileText, TrendingUp, Plus } from 'lucide-react';
import type { Document, KnowledgeGap, KnowledgeBase } from '@/types/rag';
import { useAuth } from '@/providers/auth';
import { useSkin } from '@/providers/skin';
import { publicApi } from '@/lib/public-api';

export default function KnowledgeBasePage() {
  const { user, isLoading: authLoading } = useAuth();
  const { isRagchat } = useSkin();

  const isGuest = isRagchat || (!authLoading && !user);
  const effectiveUser = isRagchat ? null : user;
  const demoToken = process.env.NEXT_PUBLIC_DEMO_SHARE_TOKEN;

  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [selectedKbId, setSelectedKbId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [gaps, setGaps] = useState<KnowledgeGap[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateKb, setShowCreateKb] = useState(false);
  const [newKbName, setNewKbName] = useState('');
  const [newKbDescription, setNewKbDescription] = useState('');
  const [creatingKb, setCreatingKb] = useState(false);
  const [addressingGap, setAddressingGap] = useState<{ id: string; queryText: string } | null>(null);

  // Guest mode: fetch via public API
  const fetchPublicData = useCallback(async () => {
    if (!demoToken) {
      setError('Demo not configured');
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      const data = await publicApi.knowledgeBase(demoToken);
      if (data.length > 0) {
        const kb = data[0];
        setKbs(data.map(k => ({
          id: k.id,
          name: k.name,
          description: k.description,
          workspace_id: '',
          created_at: k.created_at || '',
          updated_at: k.created_at || '',
          document_count: k.documents.length,
        })));
        setSelectedKbId(kb.id);
        setDocuments(kb.documents.map(d => ({
          id: d.id,
          filename: d.filename,
          file_type: d.file_type,
          file_size: d.file_size,
          status: d.status,
          kb_id: kb.id,
          chunk_count: d.chunk_count,
          metadata_: null,
          created_at: d.created_at || '',
          processed_at: null,
        })));
        setGaps(kb.gaps.map(g => ({
          id: g.id,
          query_text: g.query_text,
          occurrence_count: g.occurrence_count,
          first_asked_at: g.last_asked_at || '',
          last_asked_at: g.last_asked_at || '',
          status: g.status === 'open' ? 'active' : g.status as 'active' | 'addressed' | 'dismissed',
          kb_id: kb.id,
          workspace_id: '',
        })));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [demoToken]);

  const fetchKnowledgeBases = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/kb`,
        {
          credentials: 'include',
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch knowledge bases');
      }

      const data = await response.json();
      setKbs(data);

      // Auto-select first KB
      if (data.length > 0 && !selectedKbId) {
        setSelectedKbId(data[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [selectedKbId]);

  const fetchDocuments = useCallback(async (kbId: string) => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/docs?kb_id=${kbId}`,
        {
          credentials: 'include',
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch documents');
      }

      const data = await response.json();
      setDocuments(data.documents);
    } catch (err) {
      console.error('Failed to fetch documents:', err);
    }
  }, []);

  const fetchKnowledgeGaps = useCallback(async (kbId: string) => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/kb/gaps?kb_id=${kbId}`,
        {
          credentials: 'include',
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch knowledge gaps');
      }

      const data = await response.json();
      setGaps(data);
    } catch (err) {
      console.error('Failed to fetch knowledge gaps:', err);
    }
  }, []);

  // Fetch data on mount
  useEffect(() => {
    if (authLoading) return;
    if (isGuest) {
      fetchPublicData();
    } else {
      fetchKnowledgeBases();
    }
  }, [authLoading, isGuest, fetchPublicData, fetchKnowledgeBases]);

  // Fetch documents and gaps when KB is selected (auth mode only)
  useEffect(() => {
    if (selectedKbId && !isGuest) {
      fetchDocuments(selectedKbId);
      fetchKnowledgeGaps(selectedKbId);
    }
  }, [selectedKbId, isGuest, fetchDocuments, fetchKnowledgeGaps]);

  // When guest selects a different KB, load its docs/gaps from cached data
  const handleKbSelect = useCallback(async (kbId: string) => {
    setSelectedKbId(kbId);
    if (isGuest && demoToken) {
      try {
        const data = await publicApi.knowledgeBase(demoToken);
        const kb = data.find(k => k.id === kbId);
        if (kb) {
          setDocuments(kb.documents.map(d => ({
            id: d.id,
            filename: d.filename,
            file_type: d.file_type,
            file_size: d.file_size,
            status: d.status,
            kb_id: kb.id,
            chunk_count: d.chunk_count,
            metadata_: null,
            created_at: d.created_at || '',
            processed_at: null,
          })));
          setGaps(kb.gaps.map(g => ({
            id: g.id,
            query_text: g.query_text,
            occurrence_count: g.occurrence_count,
            first_asked_at: g.last_asked_at || '',
            last_asked_at: g.last_asked_at || '',
            status: g.status === 'open' ? 'active' : g.status as 'active' | 'addressed' | 'dismissed',
            kb_id: kb.id,
            workspace_id: '',
          })));
        }
      } catch {
        // Ignore — data already loaded from initial fetch
      }
    }
  }, [isGuest, demoToken]);

  const guestAction = () => {
    toast.info('This action requires authentication. Contact us on Fiverr to get your own instance!');
  };

  const handleUploadComplete = () => {
    if (selectedKbId) {
      fetchDocuments(selectedKbId);
    }
  };

  const handleDeleteDocument = (documentId: string) => {
    if (isGuest) { guestAction(); return; }
    setDocuments((prev) => prev.filter((doc) => doc.id !== documentId));
  };

  const handleRetryDocument = (documentId: string) => {
    if (isGuest) { guestAction(); return; }
    setDocuments((prev) =>
      prev.map((doc) =>
        doc.id === documentId ? { ...doc, status: 'processing' as const } : doc
      )
    );
  };

  const handleDismissGap = (gapId: string) => {
    if (isGuest) { guestAction(); return; }
    setGaps((prev) => prev.filter((gap) => gap.id !== gapId));
  };

  const handleAddressGap = (gapId: string, queryText: string) => {
    if (isGuest) { guestAction(); return; }
    setAddressingGap({ id: gapId, queryText });
  };

  const handleAddressGapComplete = () => {
    if (addressingGap) {
      setGaps((prev) => prev.filter((gap) => gap.id !== addressingGap.id));
    }
    setAddressingGap(null);
    if (selectedKbId) {
      fetchDocuments(selectedKbId);
    }
    toast.success('Knowledge gap addressed — document is being processed');
  };

  const createKnowledgeBase = async () => {
    if (isGuest) { guestAction(); return; }
    if (!newKbName.trim()) {
      toast.error('Please enter a name for the knowledge base');
      return;
    }

    setCreatingKb(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/kb/`,
        {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: newKbName.trim(),
            description: newKbDescription.trim() || null,
          }),
        }
      );

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to create knowledge base');
      }

      const kb = await response.json();
      setKbs((prev) => [kb, ...prev]);
      setSelectedKbId(kb.id);
      setNewKbName('');
      setNewKbDescription('');
      setShowCreateKb(false);
      toast.success('Knowledge base created');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create knowledge base');
    } finally {
      setCreatingKb(false);
    }
  };

  if (loading || authLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-blue-600 dark:text-sky-400 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg p-6 flex items-center gap-3">
          <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400" />
          <span className="text-red-800 dark:text-red-300">{error}</span>
        </div>
      </div>
    );
  }

  if (kbs.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center max-w-md">
          <FileText className="w-16 h-16 text-gray-400 dark:text-gray-600 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            No Knowledge Base Found
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            {isGuest
              ? 'No knowledge base has been set up for this demo yet.'
              : 'Create a knowledge base to start uploading documents'}
          </p>
          {!isGuest && (
            <>
              {!showCreateKb ? (
                <button
                  onClick={() => setShowCreateKb(true)}
                  className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                >
                  Create Knowledge Base
                </button>
              ) : (
                <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-6 text-left space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Name
                    </label>
                    <input
                      type="text"
                      value={newKbName}
                      onChange={(e) => setNewKbName(e.target.value)}
                      placeholder="e.g. Product Documentation"
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                      autoFocus
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Description (optional)
                    </label>
                    <input
                      type="text"
                      value={newKbDescription}
                      onChange={(e) => setNewKbDescription(e.target.value)}
                      placeholder="What kind of documents will this contain?"
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div className="flex gap-3">
                    <button
                      onClick={createKnowledgeBase}
                      disabled={creatingKb || !newKbName.trim()}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 transition"
                    >
                      {creatingKb ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Plus className="w-4 h-4" />
                      )}
                      Create
                    </button>
                    <button
                      onClick={() => setShowCreateKb(false)}
                      className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="h-full bg-gray-50 dark:bg-gray-950">
      <div className="container mx-auto px-6 py-8 max-w-7xl">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
            Knowledge Base
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {isGuest
              ? 'Documents and knowledge gaps powering this AI chatbot.'
              : 'Manage your documents and track knowledge gaps.'}
          </p>
        </div>

        {/* KB Selector */}
        {kbs.length > 1 && (
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Select Knowledge Base
            </label>
            <select
              value={selectedKbId || ''}
              onChange={(e) => handleKbSelect(e.target.value)}
              className="w-full max-w-md px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {kbs.map((kb) => (
                <option key={kb.id} value={kb.id}>
                  {kb.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Tabs */}
        <Tabs defaultValue="documents" className="space-y-6">
          <TabsList className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 p-1 rounded-lg">
            <TabsTrigger value="documents" className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Documents ({documents.length})
            </TabsTrigger>
            <TabsTrigger value="gaps" className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Knowledge Gaps ({gaps.filter((g) => g.status === 'active').length})
            </TabsTrigger>
          </TabsList>

          {/* Documents Tab */}
          <TabsContent value="documents" className="space-y-6">
            {/* Upload section — only for authenticated users */}
            {!isGuest && (
              <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Upload Documents
                </h2>
                {selectedKbId && (
                  <DocumentUpload
                    kbId={selectedKbId}
                    onUploadComplete={handleUploadComplete}
                  />
                )}
              </div>
            )}

            <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                {isGuest ? 'Indexed Documents' : 'Your Documents'}
              </h2>
              <DocumentList
                documents={documents}
                onDelete={handleDeleteDocument}
                onRetry={handleRetryDocument}
                readOnly={isGuest}
              />
            </div>
          </TabsContent>

          {/* Knowledge Gaps Tab */}
          <TabsContent value="gaps" className="space-y-6">
            <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Knowledge Gaps
              </h2>
              <KnowledgeGapsList
                gaps={gaps}
                onDismiss={handleDismissGap}
                onAddress={handleAddressGap}
                readOnly={isGuest}
              />
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Address Gap Modal */}
      {addressingGap && selectedKbId && (
        <AddressGapModal
          gapId={addressingGap.id}
          queryText={addressingGap.queryText}
          kbId={selectedKbId}
          onComplete={handleAddressGapComplete}
          onClose={() => setAddressingGap(null)}
        />
      )}
    </div>
  );
}
