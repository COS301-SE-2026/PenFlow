"use client";

import Link from "next/link";
import {
  ChevronDown,
  ExternalLink,
} from "lucide-react";

import type{
  AssistantSource,
} from "@/lib/assistantService";

interface AssistantEvidenceCardProps {
  source: AssistantSource;
  number: number;
  id: string;
  expanded: boolean;
  highlighted: boolean;
  onToggle: () => void;
}

function severityClass(severity: string | null): string {
  switch(severity?.toLowerCase()) {
    case "critical":
      return "border-red-400/30 bg-red-400/10 text-red-300";
    case "high":
      return "border-orange-400/30 bg-orange-400/10 text-orange-300";
    case "medium":
      return "border-amber-400/30 bg-amber-400/10 text-amber-300";
    case "low":
      return "border-sky-400/30 bg-sky-400/10 text-sky-300";
    default:
      return "border-brand-panel-border bg-white/5 text-muted-foreground";
  }
}

function displayValue(value: string): string {
  return value.replace(/_/g, " ");
}

function Detail({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  if(!value) {
    return null;
  }

  return (
    <div>
      <dt className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 break-words text-xs text-foreground">
        {value}
      </dd>
    </div>
  );
}

export default function AssistantEvidenceCard({
  source,
  number,
  id,
  expanded,
  highlighted,
  onToggle,
}: AssistantEvidenceCardProps) {
  const metadata = source.metadata;
  const detailsId = `${id}-details`;

  const endpointHost = metadata?.service_host ?? metadata?.asset_identifier ?? metadata?.domain;

  const endpoint = endpointHost ? `${endpointHost}${
    metadata?.service_port !== null && metadata?.service_port !== undefined
    ? `:${metadata.service_port}` : ""
  }` : null;

  return (
    <article id={id} className={`min-w-0 overflow-hidden rounded-xl border bg-[#07111f] transition ${
      highlighted ? "border-brand-cyan/70 ring-1 ring-brand-cyan/30" : "border-brand-panel-border"
    }`}>
      <button type="button" aria-expanded={expanded} aria-controls={detailsId} 
      aria-label={`${expanded ? "Collapse" : "Expand"} source ${number}`} onClick={onToggle} 
      className="flex w-full items-start gap-3 px-3 py-3 text-left transition hover:bg-white/[0.03]">
        <span className="grid size-6 shrink-0 place-items-center rounded-full bg-brand-cyan/10 text-[11px] font-semibold text-brand-cyan">
          {number}
        </span>

        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-2">
            {source.severity && (
              <span className={`rounded-full border px-2 py-0.5 text-[9px] font-semibold uppercase 
                tracking-wide ${severityClass(source.severity)}`}>
                  {source.severity}
              </span>
            )}

            {metadata?.cve_id && (
              <span className="text-[11px] font-semibold text-brand-cyan">
                {metadata.cve_id}
              </span>
            )}

            {metadata?.cvss_score !== null && 
              metadata?.cvss_score !== undefined && (
                <span className="text-[10px] text-muted-foreground">
                  CVSS {metadata.cvss_score}
                </span>
            )}
          </span>

          <span className="mt-1 block text-xs font-medium leading-5 text-foreground">
            {source.title}
          </span>

          {endpoint && (
            <span className="mt-1 block truncate text-[11px] text-muted-foreground">
              {endpoint}
              {metadata?.service_protocol
                ? ` · ${metadata.service_protocol.toUpperCase()}` : ""}
            </span>
          )}

          <span className="mt-2 flex flex-wrap gap-1.5">
            {metadata?.status && (
              <span className="rounded-md bg-white/5 px-2 py-1 text-[9px] capitalize text-muted-foreground">
                {displayValue(metadata.status)}
              </span>
            )}

            {metadata?.is_verified !== null &&
              metadata?.is_verified !== undefined && (
                <span className="rounded-md bg-white/5 px-2 py-1 text-[9px] text-muted-foreground">
                  {metadata.is_verified ? "Verified" : "Unverified"}
                </span>
              )}

              {metadata?.change && (
                <span className="rounded-md bg-brand-cyan/10 px-2 py-1 text-[9px] capitalize text-brand-cyan">
                  {displayValue(metadata.change)}
                </span>
              )}
          </span>
        </span>
        
        <ChevronDown aria-hidden="true" size={16} className={`mt-1 shrink-0 text-muted-foreground transition ${
          expanded ? "rotate-180" : ""
        }`} />
      </button>

      {expanded && (
        <div id={detailsId} className="border-t border-brand-panel-border px-3 py-3">
          {metadata && (
            <dl className="grid grid-cols-2 gap-3">
              <Detail label="Domain" value={metadata.domain} />
              <Detail label="Asset" value={metadata.asset_identifier} />
              <Detail label="Service" value={metadata.service_host} />
              <Detail label="Port" value={metadata.service_port !== null ? String(metadata.service_port) : null} />
            </dl>
          )}

          {metadata && metadata.selection_reasons.length > 0 && (
            <div className="mt-3">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                Why PenFlow selected this
              </p>
              <ul className="mt-2 grid gap-1.5">
                {metadata.selection_reasons.map((reason) => (
                  <li key={reason} className="flex items-start gap-2 text-xs leading-5 text-foreground">
                    <span aria-hidden="true" className="mt-0.5 text-brand-cyan">
                      •
                    </span>
                    {reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {source.href && (
            <Link href={source.href} className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-brand-cyan hover:underline">
              View evidence
              <ExternalLink aria-hidden="true" size={12} />
            </Link>
          )}
        </div>
      )}
    </article>
  );
}