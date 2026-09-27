"use client";

import Link from "next/link";
import {
  Fragment,
  type FormEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  Database,
  ExternalLink,
  Loader2,
  Send,
  Shield,
} from "lucide-react";

import {
  askSecurityAnalyst,
  indexScanFindings,
  type RAGAskResponse,
  type RAGIndexResponse,
} from "@/lib/ragService";

type PreparationStatus =
  | "idle"
  | "preparing"
  | "ready";

const SUGGESTED_QUESTIONS = [
  "What should I remediate first and why?",
  "Summarize the most important security risks.",
  "Which findings require immediate attention?",
];

function severityClassName(severity: string): string {
  switch(severity.toLowerCase()) {
    case "critical":
      return "border-red-500/50 bg-red-500/10 text-red-300";
    case "high":
      return "border-orange-500/50 bg-orange-500/10 text-orange-300";
    case "medium":
      return "border-yellow-500/50 bg-yellow-500/10 text-yellow-200";
    case "low":
      return "border-blue-500/50 bg-blue-500/10 text-blue-300";
    default:
      return "border-slate-500/50 bg-slate-500/10 text-slate-300";
  }
}

function renderInlineText(value: string) {
  return value.split(
    /(\*\*[^*]+\*\*)/g
  ).map((part, index) => {
    const isBold = 
      part.startsWith("**") &&
      part.endsWith("**");

      if(isBold) {
        return (
          <strong key={`${part}-${index}`}
            className="font-semibold text-foreground"
          >
            {part.slice(2, -2)}
          </strong>
        );
      }

      return (
        <Fragment key={`${part}-${index}`}>
          {part}
        </Fragment>
      );
  });
}

function AnswerContent({
  content,
}: {
  content: string;
}) {
  return (
    <div className="mt-3 text-sm leading-7 text-foreground">
      {content.split("\n").map((line, index) => {
        const trimmedLine = line.trim();

        if(!trimmedLine) {
          return (
            <div key={`space-${index}`} aria-hidden="true" className="h-3"/>
          );
        }

        if(trimmedLine.startsWith("- ")) {
          return (
            <div key={`bullet-${index}`}
              className="flex items-start gap-2"
            >
              <span aria-hidden="true" className="mt-px text-brand-cyan">\
                •
              </span>
              <p className="m-0">
                {renderInlineText(trimmedLine.slice(2))}
              </p>
            </div>
          );
        }

        return (
          <p key={`line-${index}`} className="m-0">
            {renderInlineText(trimmedLine)}
          </p>
        );
      })}
    </div>
  );
}

export default function SecurityAnalyst({
  scanId,
}: {
  scanId: string,
}) {
  const [preparationStatus, setPreparationStatus] = 
    useState<PreparationStatus>("preparing");

  const preparedScanRef = useRef<string | null>(null);

  const [indexResult, setIndexResult] = 
    useState<RAGIndexResponse | null>(null);

  const [question, setQuestion] = useState("");

  const [answer, setAnswer] = 
    useState<RAGAskResponse | null>(null);

  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const prepareAnalyst = useCallback(async () => {
    setPreparationStatus("preparing");
    setError(null);

    try {
      const result = await indexScanFindings(scanId);

      setIndexResult(result);
      setPreparationStatus("ready");
    } catch (caughtError) {
      setPreparationStatus("idle");
      setError(
        caughtError instanceof Error
        ? caughtError.message
        : "Unable to prepare the Security Analyst.",
      );
    }
  }, [scanId]);

  useEffect(() => {
    if(preparedScanRef.current === scanId) {
      return;
    }

    preparedScanRef.current = scanId;
    void prepareAnalyst();
  }, [prepareAnalyst, scanId]);

  async function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const normalizedQuestion = question.trim();

    if (
      preparationStatus !== "ready" ||
      !normalizedQuestion ||
      isAsking
    ) {
      return;
    }

    setIsAsking(true);
    setError(null);
    setAnswer(null);

    try {
      const result = await askSecurityAnalyst(
        scanId,
        {
          question: normalizedQuestion,
          limit: 5,
        },
      );

      setAnswer(result);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
        ? caughtError.message
        : "The Security Analyst is temporarily unavailable.",
      );
    } finally {
      setIsAsking(false);
    }
  }

  const isReady = preparationStatus === "ready";
  const canSubmit = isReady && question.trim().length > 0 &&
    !isAsking;

  return (
    <section className="mt-6 grid min-w-0 gap-5 pb-10" data-scan-id={scanId}>
      <header className="rounded-xl border border-brand-panel-border bg-[#0b1625] p-5">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="flex min-w-0 gap-4">
            <div className="flex size-11 shrink-0 items-center justify-center rounded-lg border border-brand-cyan/30 bg-brand-cyan/10 text-brand-cyan">
              <Shield aria-hidden="true" size={22} />
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-brand-cyan">
                PenFlow AI
              </p>
              <h2 className="mt-1 text-xl font-semibold text-foreground">
                Security Analyst
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                Ask questions about this scan. Answers are generated only from findings you are authorized to access.
              </p>
            </div>
          </div>

          <button type="button" onClick={prepareAnalyst}
            disabled={preparationStatus === "preparing"}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-brand-cyan/40 bg-brand-cyan/10 px-4 py-2 text-xs font-semibold 
            uppercase tracking-wide text-brand-cyan transition hover:bg-brand-cyan/20 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {preparationStatus === "preparing" ? (
              <>
                <Loader2 aria-hidden="true" className="animate-spin" size={16} />
                Preparing
              </>
            ) : (
              <>
                <Database aria-hidden="true" size={16} />
                {isReady ? "Refresh findings": "Prepare analyst"}
              </>
            )}
          </button>
        </div>
        {indexResult && (
          <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 rounded-lg border border-emerald-500/25 bg-emerald-500/10 px-4 py-3 text-xs text-emerald-200" role="status">
            <span>
              <strong>{indexResult.total_findings}</strong>{" "}
              findings available
            </span>

            <span>
              <strong>{indexResult.indexed}</strong>{" "}
              indexed
            </span>

            <span>
              <strong>{indexResult.unchanged}</strong>{" "}
              unchanged
            </span>
          </div>
        )}
      </header>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_280px]">
        <div className="min-w-0 rounded-xl border border-brand-panel-border bg-[#0b1625] p-5">
          <form onSubmit={submitQuestion}>
            <label htmlFor="security-analyst-question" className="block text-xs font-semibold uppercase tracking-wide text-foreground">
              Ask about this scan
            </label>

            <textarea id="security-analyst-question" value={question} onChange={(event) => setQuestion(event.target.value)}
              disabled={!isReady || isAsking} maxLength={1000} rows={4} placeholder={
                isReady ? "What should I remediate first?"
                : "Prepare the analyst before asking a question."
              }
              className="mt-3 w-full resize-y rounded-lg border border-brand-panel-border bg-[#07111f] px-4 py-3 text-sm leading-6 text-foreground outline-none transition 
              placeholder:text-muted-foreground focus:border-brand-cyan/70 focus:ring-2 focus:ring-brand-cyan/10 disabled:cursor-not-allowed disabled:opacity-60"/>

            <div className="mt-3 flex items-center justify-between gap-4">
              <span className="text-[11px] text-muted-foreground">
                {question.length}/1000
              </span>

              <button type="submit" disabled={!canSubmit} className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-brand-cyan px-5 py-2 text-xs font-bold 
              uppercase tracking-wide text-[#06111d] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50">
                {isAsking ? (
                  <>
                    <Loader2 aria-hidden="true" className="animate-spin" size={16} />
                    Analysing
                  </>
                ) : (
                  <>
                    <Send aria-hidden="true" size={16} />
                    Ask analyst
                  </>
                )}
              </button>
            </div>
          </form>

          {error && (
            <div className="mt-5 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200" role="alert">
              {error}
            </div>
          )}

          {answer && (
            <article className="mt-6 border-t border-brand-panel-border pt-6" aria-live="polite">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-brand-cyan">
                Analyst response
              </p>
              
              <AnswerContent content={answer.answer} />

              <div className="mt-6">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Evidence considered
                </h3>

                <div className="mt-3 grid gap-2">
                  {answer.sources.map((source) => (
                    <Link key={source.finding_id} href={
                      `/phase2_scan/results/${encodeURIComponent(scanId)}` +
                      `/findings?finding=${encodeURIComponent(source.finding_id)}`
                    }
                    className="group flex flex-wrap items-center justify-between gap-3 rounded-lg border border-brand-panel-border bg-[#07111f] px-4 py-3 no-underline 
                    transition hover:border-brand-cyan/50 hover:bg-brand-cyan/5"
                    >
                    <span className="flex min-w-0 items-center gap-2 text-sm text-foreground">
                      <span className="truncate">
                        {source.title}
                      </span>

                      <ExternalLink aria-hidden="true" size={13} className="shrink-0 text-muted-foreground transition group-hover:text-brand-cyan" />
                    </span>

                    <span className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase ${severityClassName(
                      source.severity,
                    )}`}
                    >
                      {source.severity}
                    </span>
                    </Link>
                  ))}
                </div>
              </div>
            </article>
          )}
        </div>
        
        <aside className="rounded-xl border border-brand-panel-border bg-[#0b1625] p-5">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-foreground">
            Suggested questions
          </h3>

          <div className="mt-4 grid gap-2">
            {SUGGESTED_QUESTIONS.map((suggestedQuestion) => (
              <button key={suggestedQuestion} type="button" disabled={!isReady || isAsking} onClick={() => setQuestion(suggestedQuestion)}
              className="rounded-lg border border-brand-panel-border bg-[#07111f] px-3 py-3 text-left text-xs leading-5 text-muted-foreground transition 
              hover:border-brand-cyan/40 hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50">
                {suggestedQuestion}
              </button>
            ))}
          </div>

          <p className="mt-5 border-t border-brand-panel-border pt-4 text-[11px] leading-5 text-muted-foreground">
            Answers may be incomplete. Verify remediation decisions against the cited findings and supporting evidence.
          </p>
        </aside>
      </div>
    </section>
  );
}