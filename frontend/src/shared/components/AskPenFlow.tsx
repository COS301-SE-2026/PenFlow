"use client";

import Link from "next/link";
import {
  usePathname,
  useSearchParams,
} from "next/navigation";
import {
  type FormEvent,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  ExternalLink,
  Loader2,
  MessageCircle,
  Send,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";

import {
  queryAssistant,
  type AssistantConversationMessage,
  type AssistantQueryResponse,
} from "@/lib/assistantService";
import { deriveAssistantContext } from "@/lib/assistantContext";
import AssistantAnswerContent from "./AssistantAnswerContent";

interface ConversationTurn {
  id: string;
  question: string;
  response: AssistantQueryResponse | null;
  error: string | null;
}

const GENERAL_SUGGESTIONS = [
  "What can PenFlow help me do?",
  "When is my next scheduled scan?",
  "Which of my domains are unverified?",
];

function hasLoginCookie(): boolean {
  return document.cookie.split("; ").some(
    (cookie) => cookie.startsWith("logged_in=")
  );
}

function contextualSuggestions(
  context: ReturnType<typeof deriveAssistantContext>,
): string[] {
  if(context.finding_id) {
    return [
      "Explain this finding in plain language.",
      "Why is this finding important?",
      "How should I remediate this finding?",
    ];
  }

  if(context.scan_id) {
    return [
      "What are the most important risks in this scan?",
      "What should I remediate first?",
      "Summarize these scan results.",
    ];
  }

  if(context.engagement_id) {
    return [
      "What is the status of this engagement?",
      "Summarize this engagement.",
      "What findings need attention?",
    ];
  }

  return GENERAL_SUGGESTIONS;
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

function AskPenFlowInner() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [loggedIn, setLoggedIn] = useState(false);
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [isAsking, setIsAsking] = useState(false);

  const conversationEndRef = useRef<HTMLDivElement | null>(null);
  const selectedFindingId = searchParams.get("finding");

  const context = useMemo(
    () => deriveAssistantContext(pathname, selectedFindingId),
    [pathname, selectedFindingId],
  );

  const suggestions = useMemo(
    () => contextualSuggestions(context),
    [context],
  );

  useEffect(() => {
    setLoggedIn(hasLoginCookie());
  }, [pathname]);

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if(event.key === "Escape") {
        setOpen(false);
      }
    }

    globalThis.addEventListener("keydown", closeOnEscape);

    return () => {
      globalThis.removeEventListener("keydown", closeOnEscape);
    };
  }, []);

  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [turns, isAsking]);

  async function submitQuestion(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const normalizedQuestion = question.trim();

    if(!normalizedQuestion || isAsking) {
      return;
    }

    const turnId = crypto.randomUUID();

    const completedTurns = turns.filter((turn) => turn.response !== null).slice(-3);

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

    setQuestion("");
    setIsAsking(true);

    setTurns((current) => [
      ...current,
      {
        id: turnId,
        question: normalizedQuestion,
        response: null,
        error: null,
      },
    ].slice(-20));

    try {
      const response = await queryAssistant({
        question: normalizedQuestion,
        context,
        audience: "security",
        history,
        ...(previousCapability ? {previous_capability: previousCapability } : {}),
      });

      setTurns((current) => 
        current.map((turn) =>
          turn.id === turnId ?
            {
              ...turn,
              response,
            } : turn,
          ),
        );
    } catch(caughtError) {
      const message = caughtError instanceof Error ? caughtError.message : "Ask PenFlow is temporarily unavailable.";

      setTurns((current) => 
        current.map((turn) =>
          turn.id === turnId ?
            {
              ...turn,
              error: message,
            } : turn,
          ),
        );
    } finally {
      setIsAsking(false);
    }
  }

  if(!loggedIn) {
    return null;
  }

  return (
    <>
      {!open && (
        <button type="button" onClick={() => setOpen(true)} aria-expanded="false" aria-controls="ask-penflow-panel" 
        className="fixed right-5 bottom-5 z-[80] inline-flex min-h-12 items-center gap-2 rounded-full border border-brand-cyan/40 bg-[#0b1625] px-5 py-3 text-sm font-semibold text-foreground 
        shadow-[0_12px_40px_rgba(0,0,0,0.5)] transition hover:border-brand-cyan hover:bg-[#102238]">
          <Sparkles aria-hidden="true" size={18} className="text-brand-cyan" />
          Ask PenFlow
        </button>
      )}

      {open && (
        <>
        <button type="button" aria-label="Close Ask PenFlow" onClick={() => setOpen(false)} className="fixed inset-0 z-[80] bg-black/55 md:hidden"/>
        <aside id="ask-penflow-panel" aria-label="Ask PenFlow assistant" className="fixed inset-y-0 right-0 z-[90] flex w-full flex-col border-l border-brand-panel-border 
        bg-[#07111f] shadow-[-18px_0_50px_rgba(0,0,0,0.45)] sm:w-[430px]">
          <header className="border-b border-brand-panel-border bg-[#0b1625] px-5 py-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex min-w-0 items-center gap-3">
                <div className="grid size-10 shrink-0 place-items-center rounded-xl border border-brand-cyan/30 bg-brand-cyan/10 text-brand-cyan">
                  <Sparkles aria-hidden="true" size={19} />
                </div>

                <div className="min-w-0">
                  <h2 className="text-base font-semibold text-foreground">
                    Ask PenFlow
                  </h2>

                  <p className="mt-1 truncate text-xs text-muted-foreground">
                    {contextLabel(context)}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1">
                {turns.length > 0 && (
                  <button type="button" onClick={() => setTurns([])} aria-label="Clear conversation" className="grid size-9 place-items-center rounded-lg text-muted-foreground transition 
                  hover:bg-white/5 hover:text-foreground">
                    <Trash2 aria-hidden="true" size={17} />
                  </button>
                )}

                <button type="button" onClick={() => setOpen(false)} aria-label="Close Ask PenFlow" className="grid size-9 place-items-center rounded-lg text-muted-foreground transition 
                  hover:bg-white/5 hover:text-foreground">
                    <X aria-hidden="true" size={19} />
                </button>
              </div>
            </div>
          </header>

          <div className="flex-1 overflow-y-auto px-5 py-5">
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
                    <div className="ml-10 rounded-2xl rounded-br-md bg-brand-cyan px-4 py-3 text-sm leading-6 text-[#06111d]">
                      {turn.question}
                    </div>

                    <div className="mr-5 rounded-2xl rounded-bl-md border border-brand-panel-border bg-[#0b1625] px-4 py-4">
                      {turn.response && (
                        <>
                          <AssistantAnswerContent content={turn.response.answer} />

                          {turn.response.sources.length > 0 && (
                            <div className="mt-4 grid gap-2 border-t border-brand-panel-border pt-4">
                              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                Sources
                              </p>
                              {turn.response.sources.map((source) => {
                                const content = (
                                  <>
                                    <span className="min-w-0 truncate">
                                      {source.title}
                                    </span>

                                    {source.severity && (
                                      <span className="shrink-0 text-[10px] uppercase text-brand-cyan">
                                        {source.severity}
                                      </span>
                                    )}
                                  </>
                                );

                                return source.href ? (
                                  <Link key={`${source.source_type}-${source.source_id}`} href={source.href} className="flex items-center justify-between gap-3 rounded-lg border 
                                  border-brand-panel-border bg-[#07111f] px-3 py-2 text-xs text-foreground transition hover:border-brand-cyan/40">
                                    {content}
                                  </Link>
                                ) : (
                                  <div key={`${source.source_type}-${source.source_id}`} className="flex items-center justify-between gap-3 rounded-lg border 
                                  border-brand-panel-border bg-[#07111f] px-3 py-2 text-xs text-foreground">
                                    {content}
                                  </div>
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
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Loader2 aria-hidden="true" className="animate-spin text-brand-cyan" size={16} />
                          Thinking...
                        </div>
                      )}

                      {turn.error && (
                        <p role="alert" className="m-0 text-sm leading-6 text-red-300">
                          {turn.error}
                        </p>
                      )}
                    </div>
                  </section>
                ))}
                <div ref={conversationEndRef} />
              </div>
            )}
          </div>

          <form onSubmit={submitQuestion} className="border-t border-brand-panel-border bg-[#0b1625] p-4">
            <label htmlFor="ask-penflow-question" className="sr-only">
              Ask PenFlow a question
            </label>

            <textarea id="ask-penflow-question" value={question} onChange={(event) => setQuestion(event.target.value)} maxLength={1000} rows={3} disabled={isAsking} 
              placeholder="Ask about PenFlow or this page..." className="w-full resize-none rounded-xl border border-brand-panel-border bg-[#07111f] px-4 py-3 
              text-sm leading-6 text-foreground outline-none transition placeholder:text-muted-foreground focus:border-brand-cyan/60 focus:ring-2 focus:ring-brand-cyan/10 disabled:opacity-60" />
            
            <div className="mt-3 flex items-center justify-between gap-3">
              <span className="text-[10px] text-muted-foreground">
                {question.length}/1000
              </span>
              <button type="submit" disabled={!question.trim() || isAsking} className="inline-flex min-h-9 items-center gap-2 rounded-lg bg-brand-cyan px-4 py-2 text-xs font-bold 
              uppercase tracking-wide text-[#06111d] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50">
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
