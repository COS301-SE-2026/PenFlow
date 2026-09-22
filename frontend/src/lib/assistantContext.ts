import type {
  AssistantContext,
  AssistantPage,
} from "@/lib/assistantService";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function validUuid(value: string | null): string | undefined {
  if(!value || !UUID_PATTERN.test(value)) {
    return undefined;
  }
  return value;
}

function matchEntityId(
  pathname: string,
  pattern: RegExp,
): string | undefined {
  const match = pathname.match(pattern);
  return validUuid(match?.[1] ?? null);
}

export function deriveAssistantContext(
  pathname: string,
  selectedFindingId: string | null,
): AssistantContext {
  let page: AssistantPage = "general";

  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || undefined;

  const findingId = validUuid(selectedFindingId);

  const scanId = matchEntityId(
    pathname,
    /^\/phase2_scan\/results\/([^/]+)/,
  );

  if(scanId) {
    return {
      page: findingId ? "finding" : "scan",
      scan_id: scanId,
      ...(findingId ? { finding_id: findingId } : {}),
      timezone,
    };
  }

  const reportScanId = matchEntityId(
    pathname,
    /^\/report\/([^/]+)/,
  );

  if(reportScanId) {
    return {
      page: "report",
      scan_id: reportScanId,
      timezone,
    };
  }

  const engagementPatterns = [
    /^\/pentesting\/engagement\/([^/]+)/,
    /^\/pentesting\/console\/my-engagements\/([^/]+)/,
    /^\/service-delivery\/engagements\/([^/]+)/,
  ];

  for(const pattern of engagementPatterns) {
    const engagementId = matchEntityId(pathname, pattern);

    if(engagementId) {
      return {
        page: findingId ? "finding": "engagement",
        engagement_id: engagementId,
        ...(findingId ? { finding_id: findingId } : {}),
        timezone,
      };
    }
  }

  if(pathname.startsWith("/domains")) {
    page = "domains";
  } else if(pathname.startsWith("/scheduled-scans")) {
    page = "scheduled_scans";
  } else if(pathname.startsWith("/dashboard")) {
    page = "dashboard";
  }

  return {
    page,
    timezone,
  };
}