import type {
  AssistantContext,
} from "@/lib/assistantService";

export function assistantActivityLabel(
  context: AssistantContext,
): string {
  if(context.finding_id) {
    return "Reviewing finding evidence...";
  }

  if(context.page === "scan" || context.page === "report") {
    return "Analyzing scan evidence...";
  }

  if(context.page === "dashboard" || context.page === "domains") {
    return "Comparing your security posture...";
  }

  if(context.page === "scheduled_scans") {
    return "Checking your scan schedule...";
  }

  if(context.engagement_id) {
    return "Checking engagement details...";
  }

  return "Preparing your answer...";
}