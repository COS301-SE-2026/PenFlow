import type {
  AssistantContext,
} from "@/lib/assistantService";

export type AssistantUserRole =
  | "client"
  | "pentester"
  | "service_delivery";

export function assistantUserRoleForPath(
  pathname: string,
): AssistantUserRole {
  if(pathname.startsWith("/service-delivery")) {
    return "service_delivery";
  }

  if(pathname.startsWith("/pentesting/console")) {
    return "pentester";
  }

  return "client";
}

export function contextualAssistantSuggestions(
  context: AssistantContext,
  role: AssistantUserRole = "client",
): string[] {
  if(context.finding_id) {
    return [
      "How should I remediate this finding?",
      "Why is this finding important?",
      "Explain this finding in plain language.",
    ];
  }

  if(context.page === "scan" || context.page === "report") {
    return [
      "What changed since my previous scan?",
      "What should I remediate first?",
      "Summarize the most important risks in this scan.",
    ];
  }

  if(context.page === "dashboard") {
    return [
      "What should I prioritize this week?",
      "Which domain currently has the greatest risk?",
      "Which findings keep returning?",
    ];
  }

  if(context.page === "domains") {
    return [
      "Which domain currently has the greatest risk?",
      "Which of my domains are unverified?",
      "What recurring issues affect my domains?",
    ];
  }

  if(context.page === "scheduled_scans") {
    return [
      "When is my next scheduled scan?",
      "Which scans are currently scheduled?",
      "How do scheduled scans work?",
    ];
  }

  if(context.engagement_id) {
    if(role === "service_delivery") {
      return [
        "What is the status of this engagement?",
        "Who is assigned to this engagement?",
        "Is this engagement awaiting review?",
      ];
    }

    if(role === "pentester") {
      return [
        "What is the status of this engagement?",
        "What findings need attention?",
        "When is this engagement scheduled?",
      ];
    }

    return [
      "What is the status of this engagement?",
      "Is my engagement report available?",
      "Do I have any open retests for this engagement?",
    ];
  }

  if(role === "service_delivery") {
    return [
      "Which engagements require attention?",
      "Which engagements need scheduling?",
      "Which engagements are awaiting review?",
    ];
  }

  if(role === "pentester") {
    return [
      "Which engagements are assigned to me?",
      "What should I work on next?",
      "Which engagements are in progress?",
    ];
  }

  return [
    "What can PenFlow help me do?",
    "When is my next scheduled scan?",
    "Which of my domains are unverified?",
  ];
}