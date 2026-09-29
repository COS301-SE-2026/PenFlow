STRUCTURED_FINDING_OUTPUT_INSTRUCTIONS = """
Return only one JSON object. Do not wrap it in Markdown.

Use exactly this structure:
{
  "answer": "Concise answer with [Finding ID: <uuid>] citations.",
  "cited_finding_ids": ["<uuid>"],
  "links": [],
  "insufficient_evidence": false,
  "claims": [
    {
      "finding_id": "<uuid>",
      "severity": "high",
      "cvss_score": 8.1,
      "cves": ["CVE-2026-12345"]
    }
  ]
}

Rules:
- cited_finding_ids must exactly match the finding citations in answer.
- Include exactly one claims item for every cited finding.
- Copy severity, CVSS score, and CVEs exactly from that finding's evidence.
- Use null for an unavailable severity or CVSS score and [] for no recorded CVEs.
- links must always be [] because PenFlow adds authorized navigation separately.
- Do not write URLs in answer.
- Do not include UUIDs other than authorized entity IDs in the evidence.
- If the evidence cannot answer the question, set insufficient_evidence to true,
  use empty cited_finding_ids, links, and claims, and make no factual security
  claims or identifier references.
""".strip()