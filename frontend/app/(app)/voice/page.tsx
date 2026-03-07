"use client";

import { useState, useEffect, useCallback } from "react";
import { Phone } from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useVoiceCall } from "@/hooks/useVoiceCall";
import { WebCallButton } from "@/components/voice/WebCallButton";
import { WebCallPanel } from "@/components/voice/WebCallPanel";
import { CallHistory } from "@/components/voice/CallHistory";
import { CallDetail } from "@/components/voice/CallDetail";
import { CallStatsCards } from "@/components/voice/CallStatsCards";
import { EscalationRulesList } from "@/components/voice/EscalationRulesList";
import { EscalationRuleForm } from "@/components/voice/EscalationRuleForm";
import { apiClient } from "@/lib/api";
import type {
  CallLogResponse,
  EscalationRuleResponse,
  WebTokenResponse,
} from "@/types/voice";

export default function VoicePage() {
  const [webToken, setWebToken] = useState<WebTokenResponse | null>(null);
  const [selectedCall, setSelectedCall] = useState<CallLogResponse | null>(null);
  const [tokenLoading, setTokenLoading] = useState(true);
  const [editingRule, setEditingRule] = useState<EscalationRuleResponse | null>(
    null
  );
  const [showRuleForm, setShowRuleForm] = useState(false);
  const [rulesRefreshKey, setRulesRefreshKey] = useState(0);

  // Fetch web token (public key + assistant_id)
  const fetchToken = useCallback(async () => {
    try {
      const data = await apiClient<WebTokenResponse>("/api/v1/voice/web-token");
      setWebToken(data);
    } catch {
      // Voice not configured — that's okay
      setWebToken(null);
    } finally {
      setTokenLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchToken();
  }, [fetchToken]);

  const { callState, startCall, endCall, isSpeaking, transcript, error } =
    useVoiceCall({
      publicKey: webToken?.public_key ?? null,
      assistantId: webToken?.assistant_id ?? null,
    });

  const voiceConfigured = webToken?.public_key && webToken?.assistant_id;

  return (
    <div className="container mx-auto px-4 sm:px-6 py-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="bg-green-100 p-2 rounded-lg">
            <Phone className="w-6 h-6 text-green-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">VoiceBot Pro</h1>
            <p className="text-sm text-gray-500">
              AI-powered phone agent with call transcription and smart escalation
            </p>
          </div>
        </div>
        <WebCallButton
          callState={callState}
          onStart={startCall}
          onEnd={endCall}
          disabled={!voiceConfigured || tokenLoading}
        />
      </div>

      {/* Active call panel */}
      {callState !== "idle" && (
        <div className="mb-6">
          <WebCallPanel
            callState={callState}
            isSpeaking={isSpeaking}
            transcript={transcript}
            onEnd={endCall}
            error={error}
          />
        </div>
      )}

      {/* Not configured banner */}
      {!tokenLoading && !voiceConfigured && (
        <div className="mb-6 bg-amber-50 border border-amber-200 rounded-lg p-4">
          <p className="text-sm text-amber-800">
            <span className="font-medium">Voice not configured.</span>{" "}
            Go to Settings &rarr; Voice to set up your Vapi API keys and enable web calling.
          </p>
        </div>
      )}

      {/* Tabs */}
      <Tabs defaultValue="calls">
        <TabsList>
          <TabsTrigger value="calls">Calls</TabsTrigger>
          <TabsTrigger value="escalation">Escalation Rules</TabsTrigger>
        </TabsList>

        <TabsContent value="calls">
          <div className="space-y-6 mt-4">
            <CallStatsCards />
            {selectedCall ? (
              <CallDetail
                call={selectedCall}
                onBack={() => setSelectedCall(null)}
              />
            ) : (
              <div className="bg-white border border-gray-200 rounded-lg">
                <CallHistory onSelectCall={setSelectedCall} />
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="escalation">
          <EscalationRulesList
            onEdit={(rule) => {
              setEditingRule(rule);
              setShowRuleForm(true);
            }}
            onCreate={() => {
              setEditingRule(null);
              setShowRuleForm(true);
            }}
            refreshKey={rulesRefreshKey}
          />
        </TabsContent>
      </Tabs>

      {/* Escalation Rule Form Modal */}
      {showRuleForm && (
        <EscalationRuleForm
          rule={editingRule}
          onClose={() => {
            setShowRuleForm(false);
            setEditingRule(null);
          }}
          onSaved={() => {
            setShowRuleForm(false);
            setEditingRule(null);
            setRulesRefreshKey((k) => k + 1);
          }}
        />
      )}
    </div>
  );
}
