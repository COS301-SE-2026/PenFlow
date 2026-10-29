import type { ScanSourceStatus } from "./scanService";

const ACTIVE = new Set(["queued", "running"]);

export function scanActivity(
  status: string,
  sources: ScanSourceStatus[],
  connectionError: boolean,
): {
  sources: ScanSourceStatus[];
  message: string;
  active: boolean;
} {
  if (connectionError) {
    return {
      sources,
      message:
        "Status connection interrupted. Displaying the last received status; retrying…",
      active: false,
    };
  }

  if (!ACTIVE.has(status)) {
    return { sources, message: "", active: false };
  }

  const running = sources.filter(
    (source) => source.status === "running",
  );

  if (running.length) {
    return {
      sources,
      message:
        "Workers are running. Target counters update as each target finishes.",
      active: true,
    };
  }

  const waiting = sources.find(
    (source) => source.status === "pending",
  );

  return {
    sources: sources.map((source) =>
      source === waiting
        ? { ...source, status: "preparing" }
        : source,
    ),
    message: waiting
      ? `Awaiting worker confirmation for ${waiting.source_name.replace(/_/g, " ")}. The stage is queued or preparing; execution has not been confirmed.`
      : "Awaiting scan finalisation. No source is currently reporting execution.",
    active: true,
  };
}