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
}

export interface AssistantConversationMessage {
  role: "user" | "assistant";
  content: string;
}

interface AssistantQueryRequest {
  question: string;
  context: AssistantContext;
  audience?: "executive" | "it_manager" | "developer" | "security";
  history?: AssistantConversationMessage[];
  previous_capability?: AssistantCapability;
}

export async function queryAssistant(
  request: AssistantQueryRequest,
): Promise<AssistantQueryResponse> {
  const response = await fetch("/api/assistant/query", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
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
}