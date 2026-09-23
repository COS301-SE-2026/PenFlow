export interface RAGIndexResponse {
  total_findings: number;
  indexed: number;
  unchanged: number;
}

export interface RAGSearchResult {
  finding_id: string;
  title: string;
  severity: string;
  distance: number;
  content: string;
}

export interface RAGSearchResponse {
  question: string;
  results: RAGSearchResult[];
}

export interface RAGAnswerSource {
  finding_id: string;
  title: string;
  severity: string;
}

export interface RAGAskResponse {
  question: string;
  answer: string;
  sources: RAGAnswerSource[];
}

interface RAGQuestionRequest {
  question: string;
  limit?: number;
}

async function parseResponse<T>(
  response: Response,
  fallbackMessage: string,
): Promise<T> {
  const body = await response.json().catch(() => null) as {
    detail?: string;
  } | null;

  if(!response.ok) {
    throw new Error(body?.detail ?? fallbackMessage);
  }

  return body as T;
}

export async function indexScanFindings(
  scanId: string,
): Promise<RAGIndexResponse> {
  const response = await fetch(
    `/api/rag/scans/${encodeURIComponent(scanId)}/index`,
    {
      method: "POST",
    },
  );

  return parseResponse<RAGIndexResponse>(
    response,
    "Unable to prepare the Security Analyst.",
  );
}

export async function searchScanFindings(
  scanId: string,
  request: RAGQuestionRequest,
): Promise<RAGSearchResponse> {
  const response = await fetch(
    `/api/rag/scans/${encodeURIComponent(scanId)}/search`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
  );

  return parseResponse<RAGSearchResponse>(
    response,
    "Unable to search the scan findings.",
  );
}

export async function askSecurityAnalyst(
  scanId: string,
  request: RAGQuestionRequest,
): Promise<RAGAskResponse> {
  const response = await fetch(
    `/api/rag/scans/${encodeURIComponent(scanId)}/ask`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
  );

  return parseResponse<RAGAskResponse>(
    response,
    "The Security Analyst is temporarily unavailable.",
  );
}