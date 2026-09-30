"use client";

import Link from "next/link";
import {
  usePathname,
  useSearchParams,
} from "next/navigation";
import {
  type FormEvent,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Check,
  Copy,
  ExternalLink,
  Loader2,
  MessageCircle,
  RefreshCw,
  Send,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import {
  queryAssistant,
  type AssistantConversationMessage,
  type AssistantQueryResponse,
} from "@/lib/assistantService";
import {
  assistantContextKey,
  deriveAssistantContext 
} from "@/lib/assistantContext";
import AssistantAnswerContent from "./AssistantAnswerContent";
import AssistantEvidenceCard from "./AssistantEvidenceCard";
import {
  ASSISTANT_ANSWER_MODES,
  assistantAnswerModeLabel,
  assistantAudienceForMode,
  type AssistantAnswerMode,
} from "@/lib/assistantModes";
import {
  assistantUserRoleForPath,
  contextualAssistantSuggestions,
} from "@/lib/assistantSuggestions";
import {
  assistantActivityLabel,
} from "@/lib/assistantActivity";
import AssistantAnswerStateNotice from "./AssistantAnswerStateNotice";

interface ConversationTurn {
  id: string;
  question: string;
  answerMode: AssistantAnswerMode;
  response: AssistantQueryResponse | null;
  error: string | null;
}

function hasLoginCookie(): boolean {
  return document.cookie.split("; ").some(
    (cookie) => cookie.startsWith("logged_in=")
  );
}

function contextLabel(
  context: ReturnType<typeof deriveAssistantContext>,
): string {
  if(context.finding_id) {
    return "Using selected finding";
  }

  if(context.scan_id) {
    return "Using current scan";
  }

  if(context.engagement_id) {
    return "Using current engagement";
  }

  return "PenFlow knowledge";
}

function evidenceKey(
  turnId: string,
  sourceType: string,
  sourceId: string,
): string {
  return `${turnId}:${sourceType}:${sourceId}`;
}

function evidenceDomId(key: string): string {
  return `assistant-evidence-${key.replace(
    /[^a-zA-Z0-9_-]/g,
    "-",
  )}`;
}

interface CopyStatus {
  turnId: string;
  status: "copied" | "failed";
}

function AskPenFlowInner() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [loggedIn, setLoggedIn] = useState(false);
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [isAsking, setIsAsking] = useState(false);
  const [expandedEvidence, setExpandedEvidence] = useState<Record<string, boolean>>({});
  const [highlightedEvidenceKey, setHighlightedEvidenceKey] = useState<string | null>(null);
  const [answerMode, setAnswerMode] = useState<AssistantAnswerMode>("security");
  const [copyStatus, setCopyStatus] = useState<CopyStatus | null>(null);

  const conversationEndRef = useRef<HTMLDivElement | null>(null);
  const launcherButtonRef = useRef<HTMLButtonElement | null>(null);
  const panelRef = useRef<HTMLElement | null>(null);
  const questionInputRef = useRef<HTMLTextAreaElement | null>(null);

  const selectedFindingId = searchParams.get("finding");

  const context = useMemo(
    () => deriveAssistantContext(pathname, selectedFindingId),
    [pathname, selectedFindingId],
  );

  const contextKey = useMemo(
    () => assistantContextKey(context),
    [context],
  );

  const previousContextKeyRef = useRef(contextKey);

  const assistantUserRole = useMemo(
    () => assistantUserRoleForPath(pathname),
    [pathname],
  );

  const suggestions = useMemo(
    () => contextualAssistantSuggestions(
      context,
      assistantUserRole,
    ),
    [context, assistantUserRole],
  );

  const activityLabel = useMemo(
    () => assistantActivityLabel(context),
    [context],
  );

  const closeAssistant = useCallback(() => {
    setOpen(false);

    globalThis.requestAnimationFrame(() => {
      launcherButtonRef.current?.focus();
    });
  }, []);

  useEffect(() => {
    setLoggedIn(hasLoginCookie());
  }, [pathname]);

  useEffect(() => {
    if(previousContextKeyRef.current === contextKey) {
      return;
    }

    previousContextKeyRef.current = contextKey;
    setExpandedEvidence({});
    setCopyStatus(null);
    setHighlightedEvidenceKey(null);
  }, [contextKey]);

  useEffect(() => {
    if(!open) {
      return;
    }

    const previousOverflow = document.body.style.overflow;

    document.body.style.overflow = "hidden";

    const focusFrame = globalThis.requestAnimationFrame(
      () => {
        questionInputRef.current?.focus();
      },
    );

    function handleDialogKeyDown(event: KeyboardEvent) {
      if(
        event.target instanceof Element &&
        event.target.closest(
          '[data-slot="select-content"]',
        )
      ) {
        return;
      }

      if(event.key === "Escape") {
        event.preventDefault();
        closeAssistant();
        return;
      }

      if(event.key !== "Tab") {
        return;
      }

      const panel = panelRef.current;

      if(!panel) {
        return;
      }

      const focusableElements = Array.from(
        panel.querySelectorAll<HTMLElement>(
          [
            "button:not([disabled])",
            "a[href]",
            "textarea:not([disabled])",
            "input:not([disabled])",
            "select:not([disabled])",
            '[tabindex]:not([tabindex="-1"])',
          ].join(","),
        ),
      ).filter(
        (element) =>
          element.tabIndex >= 0 &&
          element.getAttribute("aria-hidden") !== "true",
      );

      if(focusableElements.length === 0) {
        event.preventDefault();
        return;
      }

      const first = focusableElements[0];
      const last = focusableElements[focusableElements.length - 1];
      const active = document.activeElement;

      if(
        event.shiftKey &&
        (active === first || !panel.contains(active))
      ) {
        event.preventDefault();
        last.focus();
        return;
      }

      if(
        !event.shiftKey &&
        (active === last || !panel.contains(active))
      ) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener(
      "keydown",
      handleDialogKeyDown,
    );

    return () => {
      globalThis.cancelAnimationFrame(focusFrame);

      document.removeEventListener(
        "keydown",
        handleDialogKeyDown,
      );
      document.body.style.overflow = previousOverflow;
    };
  }, [open, closeAssistant]);

  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [turns, isAsking]);

  function toggleEvidence(key: string) {
    setExpandedEvidence((current) => ({
      ...current,
      [key]: !current[key],
    }));

    setHighlightedEvidenceKey(key);
  }

  function revealEvidence(key: string) {
    setExpandedEvidence((current) => ({
      ...current,
      [key]: true,
    }));

    setHighlightedEvidenceKey(key);

    globalThis.requestAnimationFrame(() => {
      document.getElementById(evidenceDomId(key))?.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    });
  }

  function clearConversation() {
    setTurns([]);
    setExpandedEvidence({});
    setCopyStatus(null);
    setHighlightedEvidenceKey(null);
  }

  async function copyAnswer(
    turnId: string,
    answer: string,
  ) {
    try {
      await navigator.clipboard.writeText(answer);
      setCopyStatus({
        turnId,
        status: "copied",
      });
    } catch {
      setCopyStatus({
        turnId,
        status: "failed",
      });
    }
  }

  async function askQuestion(
    normalizedQuestion: string,
    submittedAnswerMode: AssistantAnswerMode,
    retryTurnId?: string,
  ) {
    if(!normalizedQuestion || isAsking) {
      return;
    }
    
    const turnId = retryTurnId ?? crypto.randomUUID();
    const retryIndex = retryTurnId ? turns.findIndex((turn) => turn.id === retryTurnId) : -1;
    const precedingTurns = retryIndex >= 0 ? turns.slice(0, retryIndex) : turns;
    const completedTurns = precedingTurns.filter((turn) => turn.response !== null).slice(-3);

    const history: AssistantConversationMessage[] = completedTurns.flatMap((turn) => [
      {
        role: "user" as const,
        content: turn.question.slice(0, 2000),
      },
      {
        role: "assistant" as const,
        content: turn.response!.answer.slice(0, 2000),
      },
    ]);

    const previousCapability = completedTurns.at(-1)?.response?.capability;

    setCopyStatus(null);
    setIsAsking(true);

    if(retryTurnId) {
      setTurns((current) => current.map((turn) =>
      turn.id === retryTurnId ? {
        ...turn,
        response: null,
        error: null,
      } : turn));
    } else {
      setTurns((current) => [
        ...current,
        {
          id: turnId,
          question: normalizedQuestion,
          answerMode: submittedAnswerMode,
          response: null,
          error: null,
        },
      ].slice(-20));
    }

    try {
      const response = await queryAssistant({
        question: normalizedQuestion,
        context,
        audience: assistantAudienceForMode(submittedAnswerMode),
        history,
        ...(previousCapability ? {
          previous_capability: previousCapability,
        } : {}),
      });

      setTurns((current) => current.map((turn) =>
        turn.id === turnId ? {
          ...turn,
          response,
          error: null,
        } : turn,
      ));
  } catch(caughtError) {
    const message = caughtError instanceof Error ? caughtError.message : "Ask PenFlow is temporarily unavailable.";

    setTurns((current) => current.map((turn) =>
      turn.id === turnId ? {
        ...turn,
        response: null,
        error: message,
      } : turn,
    ));
  } finally {
    setIsAsking(false);
  }
  }

  async function submitQuestion(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    const normalizedQuestion = question.trim();

    if(!normalizedQuestion || isAsking) {
      return;
    }

    const submittedAnswerMode = answerMode;
    setQuestion("");
    await askQuestion(normalizedQuestion, submittedAnswerMode);
  }

  if(!loggedIn) {
    return null;
  }

  return (
    <>
      {!open && (
        <button ref={launcherButtonRef} type="button" onClick={() => setOpen(true)} aria-expanded="false" aria-controls="ask-penflow-panel" 
        className="fixed right-5 bottom-5 z-[80] inline-flex min-h-12 items-center gap-2 rounded-full border border-brand-cyan/40 bg-[#0b1625] px-5 py-3 text-sm font-semibold text-foreground 
        shadow-[0_12px_40px_rgba(0,0,0,0.5)] transition hover:border-brand-cyan hover:bg-[#102238]">
          <Sparkles aria-hidden="true" size={18} className="text-brand-cyan" />
          Ask PenFlow
        </button>
      )}

      {open && (
        <>
        <button type="button" tabIndex={-1} aria-label="Close Ask PenFlow" onClick={closeAssistant} className="fixed inset-0 z-[80] bg-black/55 md:hidden"/>
        <aside ref={panelRef} id="ask-penflow-panel" role="dialog" aria-modal="true" aria-labelledby="ask-penflow-title" className="fixed inset-y-0 right-0 z-[90] flex w-full flex-col border-l border-brand-panel-border 
        bg-[#07111f] shadow-[-18px_0_50px_rgba(0,0,0,0.45)] sm:w-[430px]">
          <header className="border-b border-brand-panel-border bg-[#0b1625] px-5 py-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex min-w-0 items-center gap-3">
                <div className="grid size-10 shrink-0 place-items-center rounded-xl border border-brand-cyan/30 bg-brand-cyan/10 text-brand-cyan">
                  <Sparkles aria-hidden="true" size={19} />
                </div>

                <div className="min-w-0">
                  <h2 id="ask-penflow-title" className="text-base font-semibold text-foreground">
                    Ask PenFlow
                  </h2>

                  <p className="mt-1 truncate text-xs text-muted-foreground">
                    {contextLabel(context)}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1">
                {turns.length > 0 && (
                  <button type="button" onClick={clearConversation} aria-label="Clear conversation" className="grid size-9 place-items-center rounded-lg text-muted-foreground transition  
                  hover:bg-white/5 hover:text-foreground">
                    <Trash2 aria-hidden="true" size={17} />
                  </button>
                )}

                <button type="button" onClick={closeAssistant} aria-label="Close Ask PenFlow" className="grid size-9 place-items-center rounded-lg text-muted-foreground transition 
                  hover:bg-white/5 hover:text-foreground">
                    <X aria-hidden="true" size={19} />
                </button>
              </div>
            </div>
          </header>

          <div className="min-h-0 flex-1 overscroll-contain overflow-y-auto px-4 py-5 sm:px-5">
            {turns.length === 0 ? (
              <div className="flex min-h-full flex-col justify-center">
                <div className="mx-auto grid size-14 place-items-center rounded-2xl border border-brand-cyan/25 bg-brand-cyan/10 text-brand-cyan">
                  <MessageCircle aria-hidden="true" size={25} />
                </div>

                <h3 className="mt-4 text-center text-lg text-foreground">
                  How can I help?
                </h3>

                <p className="mx-auto mt-2 max-w-xs text-center text-sm leading-6 text-muted-foreground">
                  Ask about PenFlow, your authorized account data, or security evidence on the page you are viewing.
                </p>

                <div className="mt-6 grid gap-2">
                  {suggestions.map((suggestion) => (
                    <button key={suggestion} type="button" onClick={() => setQuestion(suggestion)} className="rounded-xl border border-brand-panel-border bg-[#0b1625] 
                    px-4 py-3 text-left text-sm leading-5 text-muted-foreground transition hover:border-brand-cyan/40 hover:text-foreground">
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="grid gap-6">
                {turns.map((turn) => (
                  <section key={turn.id} className="grid gap-3">
                    <div className="ml-8 break-words rounded-2xl rounded-br-md bg-brand-cyan px-4 py-3 text-sm leading-6 text-[#06111d] sm:ml-10">
                      {turn.question}
                    </div>

                    <div className="mr-2 min-w-0 rounded-2xl rounded-bl-md border border-brand-panel-border bg-[#0b1625] px-4 py-4 sm:mr-5">
                      {turn.response && (
                        <>
                          <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                            {assistantAnswerModeLabel(turn.answerMode)} answer
                          </p>
                          <AssistantAnswerStateNotice state={turn.response.answer_state} />
                          <AssistantAnswerContent content={turn.response.answer} citationNumbers={
                            new Map(turn.response.sources.map(
                              (source, index) => [
                                source.source_id.toLowerCase(),
                                index + 1,
                              ] as const,
                            ))
                          }
                          onFindingCitation={(findingId) => {
                            const source = turn.response?.sources.find(
                              (candidate) =>
                                candidate.source_type === "finding" &&
                                candidate.source_id.toLowerCase() ===
                                  findingId.toLowerCase(),
                            );

                            if(!source) {
                              return;
                            }

                            revealEvidence(
                              evidenceKey(
                                turn.id,
                                source.source_type,
                                source.source_id,
                              ),
                            );
                          }}
                        />

                          <div className="mt-3 flex flex-wrap items-center gap-2">
                            <button type="button" onClick={() => {
                              void copyAnswer(
                                turn.id,
                                turn.response!.answer,
                              );
                            }}
                            className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-[10px] font-semibold text-muted-foreground transition hover:bg-white/5 hover:text-foreground"
                            >
                              {copyStatus?.turnId === turn.id &&
                              copyStatus.status === "copied" ? (
                                <>
                                  <Check aria-hidden="true" size={13} />
                                  Copied
                                </>
                              ) : (
                                <>
                                  <Copy aria-hidden="true" size={13} />
                                  Copy answer
                                </>
                              )}
                            </button>

                            {copyStatus?.turnId === turn.id &&
                            copyStatus.status === "failed" && (
                              <span role="alert" className="text-[10px] text-red-300">
                                Copy failed
                              </span>
                            )}
                            <button type="button" disabled={isAsking} onClick={() => {
                              void askQuestion(
                                turn.question,
                                turn.answerMode,
                                turn.id,
                              );
                            }}
                            className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-[10px] font-semibold text-muted-foreground transition hover:bg-white/5 hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
                            >
                              <RefreshCw aria-hidden="true" size={13} />
                              Try again
                            </button>
                          </div>

                          {turn.response.sources.length > 0 && (
                            <div className="mt-4 grid gap-2 border-t border-brand-panel-border pt-4">
                              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                Sources
                              </p>

                              {turn.response.sources.map((source, index) => {
                                const key = evidenceKey(
                                  turn.id,
                                  source.source_type,
                                  source.source_id,
                                );

                                return (
                                  <AssistantEvidenceCard key={key} id={evidenceDomId(key)} source={source} number={index+1}
                                  expanded={Boolean(expandedEvidence[key])} highlighted={highlightedEvidenceKey === key} onToggle={() => toggleEvidence(key)} />
                                );
                              })}
                            </div>
                          )}

                          {turn.response.links.length > 0 && (
                            <div className="mt-4 flex flex-wrap gap-2">
                              {turn.response.links.map((link) => (
                                <Link key={link.href} href={link.href} className="inline-flex items-center gap-1.5 rounded-lg border border-brand-cyan/30 bg-brand-cyan/10 px-3 py-2 
                                text-xs font-semibold text-brand-cyan transition hover:bg-brand-cyan/20">
                                  {link.label}
                                  <ExternalLink aria-hidden="true" size={12} />
                                </Link>
                              ))}
                            </div>
                          )}
                        </>
                      )}

                      {!turn.response && !turn.error && (
                        <div role="status" aria-live="polite" className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Loader2 aria-hidden="true" className="animate-spin text-brand-cyan" size={16} />
                          {activityLabel}
                        </div>
                      )}

                      {turn.error && (
                        <div role="alert" className="rounded-lg border border-red-400/30 bg-red-400/10 px-3 py-3">
                          <p className="m-0 text-sm leading-6 text-red-200">
                            {turn.error}
                          </p>
                          
                          <button type="button" disabled={isAsking} onClick={() => {
                            void askQuestion(
                              turn.question,
                              turn.answerMode,
                              turn.id,
                            );
                          }}
                          className="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-red-300/30 px-2.5 py-1.5 text-[10px] font-semibold text-red-200 transition hover:bg-red-300/10 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            <RefreshCw aria-hidden="true" size={13} />
                            Retry
                          </button>
                        </div>
                      )}
                    </div>
                  </section>
                ))}
                <div ref={conversationEndRef} />
              </div>
            )}
          </div>

          <form onSubmit={submitQuestion} className="shrink-0 border-t border-brand-panel-border bg-[#0b1625] p-4">
            <label htmlFor="ask-penflow-question" className="sr-only">
              Ask PenFlow a question
            </label>

            <textarea ref={questionInputRef} id="ask-penflow-question" value={question} onChange={(event) => setQuestion(event.target.value)} maxLength={1000} rows={3} disabled={isAsking} 
              placeholder="Ask about PenFlow or this page..." className="w-full resize-none rounded-xl border border-brand-panel-border bg-[#07111f] px-4 py-3 
              text-sm leading-6 text-foreground outline-none transition placeholder:text-muted-foreground focus:border-brand-cyan/60 focus:ring-2 focus:ring-brand-cyan/10 disabled:opacity-60" />
            
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <div className="flex min-w-0 items-center gap-2">
                <span id="ask-penflow-audience-label" className="shrink-0 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                  Answer for
                </span>

                <Select value={answerMode} disabled={isAsking} onValueChange={(value) => {
                  setAnswerMode(
                    value as AssistantAnswerMode,
                  );
                }}>

                  <SelectTrigger aria-labelledby="ask-penflow-audience-label" className="h-9 w-auto min-w-32 cursor-pointer border-brand-cyan/30 bg-[#07111f] px-3 text-xs font-semibold text-foreground hover:border-brand-cyan/60">
                    <SelectValue />
                  </SelectTrigger>

                  <SelectContent side="top" align="start" sideOffset={8} className="z-[100]">
                    {ASSISTANT_ANSWER_MODES.map((mode) => (
                      <SelectItem key={mode.value} value={mode.value} title={mode.description}>
                        {mode.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="ml-auto flex items-center gap-3">
                <span className="text-[10px] text-muted-foreground">
                  {question.length}/1000
                </span>

                <button type="submit" disabled={!question.trim() || isAsking} className="inline-flex min-h-9 items-center gap-2 rounded-lg bg-brand-cyan px-4 py-2 text-xs font-bold uppercase tracking-wide text-[#06111d] 
                transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50">
                  {isAsking ? (
                    <>
                      <Loader2 aria-hidden="true" className="animate-spin" size={14} />
                      Thinking
                    </>
                  ) : (
                    <>
                      <Send aria-hidden="true" size={14} />
                      Ask
                    </>
                  )}
                </button>
              </div>
            </div>

            <p className="mt-3 text-[10px] leading-4 text-muted-foreground">
              Answers can be incomplete. Verify important decisions against linked PenFlow evidence.
            </p>
          </form>
        </aside>
        </>
      )}
    </>
  );
}

export default function AskPenFlow() {
  return (
    <Suspense fallback={null}>
      <AskPenFlowInner />
    </Suspense>
  );
}
