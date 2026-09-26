export type AssistantCapability =
  | "product_help"
  | "navigation"
  | "user_data"
  | "finding_explanation"
  | "security_analysis"
  | "unsupported";

export type AssistantPage =
  | "general"
  | "dashboard"
  | "domains"
  | "scheduled_scans"
  | "scan"
  | "finding"
  | "engagement"
  | "report";

export type AssistantSourceType =
  | "finding"
  | "product_guide"
  | "user_data"
  | "navigation";

export type SecurityQueryIntent =
  | "risk_prioritization"
  | "exact_lookup"
  | "semantic_search"
  | "scan_comparison"
  | "portfolio_analysis"
  | "scan_summary";

export interface AssistantContext {
  page: AssistantPage;
  scan_id?: string;
  finding_id?: string;
  engagement_id?: string;
  timezone?: string;
}

export interface AssistantSource {
  source_type: AssistantSourceType;
  source_id: string;
  title: string;
  severity: string | null;
  href: string | null;
  metadata: AssistantSourceMetadata | null;
}

export interface AssistantLink {
  label: string;
  href: string;
}

export interface AssistantQueryResponse {
  question: string;
  answer: string;
  capability: AssistantCapability;
  sources: AssistantSource[];
  links: AssistantLink[];
  security_intent?: SecurityQueryIntent | null;
  answer_state: AssistantAnswerState;
}

export interface AssistantConversationMessage {
  role: "user" | "assistant";
  content: string;
}

export type AssistantAnswerState =
  | "complete"
  | "insufficient_evidence"
  | "validation_fallback";

export interface AssistantSourceMetadata {
  cve_id: string | null;
  cvss_score: number | null;
  status: string | null;
  is_verified: boolean | null;
  domain: string | null;
  asset_identifier: string | null;
  service_host: string | null;
  service_port: number | null;
  service_protocol: string | null;
  change:
    | "new"
    | "persistent"
    | "no_longer_detected"
    | null;
  selection_reasons: string[];
}

export type AssistantAudience =
  | "executive"
  | "it_manager"
  | "developer"
  | "security";

interface AssistantQueryRequest {
  question: string;
  context: AssistantContext;
  audience?: AssistantAudience;
  history?: AssistantConversationMessage[];
  previous_capability?: AssistantCapability;
}

export const ASSISTANT_REQUEST_TIMEOUT_MS = 90_000;

export async function queryAssistant(
  request: AssistantQueryRequest,
): Promise<AssistantQueryResponse> {

  const controller = new AbortController();

  const timeoutId = globalThis.setTimeout(
    () => controller.abort(),
    ASSISTANT_REQUEST_TIMEOUT_MS,
  );

  try {
    const response = await fetch("/api/assistant/query", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
      signal: controller.signal,
    });

    const body = (await response.json().catch(() => null)) as {
      detail?: string;
    } | AssistantQueryResponse | null;

    if(!response.ok) {
      const detail = body && "detail" in body ? body.detail : undefined;

      throw new Error(
        detail ?? "Ask PenFlow is temporarily unavailable.",
      );
    }

    return body as AssistantQueryResponse;
  } catch(caughtError) {
    if(controller.signal.aborted) {
      throw new Error("Ask PenFlow took too long to respond. Please try again.");
    }

    if(caughtError instanceof Error) {
      throw caughtError;
    }

    throw new Error("Ask PenFlow is temporarily unavailable.");
  } finally {
    globalThis.clearTimeout(timeoutId);
  }
}