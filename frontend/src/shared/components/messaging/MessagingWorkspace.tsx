"use client";
import PageHero from "@/shared/components/PageHero";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  ArrowUpRight,
  MessageCircle,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
} from "lucide-react";
import {
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import type { FormEvent } from "react";

import {
  groupThreads,
  keyOf,
  MESSAGES_UPDATED_EVENT,
  messageUrl,
  personName,
  requestJson,
  roleName,
  selectThread,
} from "./inbox";
import type {
  Inbox,
  Message,
  MessagingRole,
  Thread,
} from "./inbox";
import styles from "./MessagingWorkspace.module.css";

type Remembered = {
  last?: string;
  engagements?: Record<string, string>;
};

type Loaded = {
  key: string;
  messages: Message[];
  loading: boolean;
  error: string | null;
};

const blank: Loaded = {
  key: "",
  messages: [],
  loading: false,
  error: null,
};

const initials = (name: string) =>
  name
    .split(/\s+/)
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

const fullDate = (date: string) =>
  new Date(date).toLocaleDateString(undefined, {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

const shortDate = (date: string) =>
  new Date(date).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
  });

const time = (date: string) =>
  new Date(date).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });

const roleClass = (role: string) =>
  role === "pentester"
    ? styles.pentester
    : role === "client"
      ? styles.client
      : styles.delivery;

function storageRead(key: string): Remembered {
  try {
    const value = JSON.parse(sessionStorage.getItem(key) || "{}");
    return value && typeof value === "object" ? value : {};
  } catch {
    return {};
  }
}

function storageWrite(key: string, value: Remembered) {
  try {
    sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
  }
}

function engagementHref(role: MessagingRole, id: string) {
  return role === "service_delivery"
    ? `/service-delivery/engagements/${id}`
    : role === "pentester"
      ? `/pentesting/console/my-engagements/${id}`
      : `/pentesting/engagement/${id}`;
}

export default function MessagingWorkspace({
  role,
}: {
  role: MessagingRole;
}) {
  return (
    <Suspense
      fallback={
        <div className={styles.feedback} role="status">
          Loading messages…
        </div>
      }
    >
      <Workspace role={role} />
    </Suspense>
  );
}

function Workspace({ role }: { role: MessagingRole }) {
  const params = useSearchParams();
  const engagementParam = params.get("engagement");
  const channelParam = params.get("channel");

  const [inbox, setInbox] = useState<Inbox | null>(null);
  const [inboxLoading, setInboxLoading] = useState(true);
  const [inboxError, setInboxError] = useState<string | null>(null);
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [mobileThread, setMobileThread] = useState(false);
  const [loaded, setLoaded] = useState<Loaded>(blank);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [sendErrors, setSendErrors] = useState<Record<string, string>>({});
  const [sendingKeys, setSendingKeys] = useState<Set<string>>(new Set());
  const [notice, setNotice] = useState("");
  const [inboxVersion, setInboxVersion] = useState(0);
  const [threadVersion, setThreadVersion] = useState(0);

  const activeRef = useRef<string | null>(null);
  const draftsRef = useRef<Record<string, string>>({});
  const sendingRef = useRef(new Set<string>());
  const viewerRef = useRef<string | null>(null);
  const selectionInit = useRef("");
  const live = useRef(true);
  const bottom = useRef<HTMLDivElement>(null);
  const composer = useRef<HTMLTextAreaElement>(null);
  const threadHeader = useRef<HTMLHeadingElement>(null);

  const refreshInbox = useCallback(
    () => setInboxVersion((value) => value + 1),
    [],
  );

  const refreshThread = useCallback(
    () => setThreadVersion((value) => value + 1),
    [],
  );

  const active =
    inbox?.items.find((thread) => keyOf(thread) === activeKey) || null;

  const groups = groupThreads(inbox?.items || [], search);

  const display =
    loaded.key === activeKey
      ? loaded
      : { ...blank, loading: !!activeKey };

  const draft = activeKey ? drafts[activeKey] || "" : "";

  activeRef.current = activeKey;
  draftsRef.current = drafts;

  useEffect(() => {
    live.current = true;
    return () => {
      live.current = false;
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setInboxError(null);

    const load = async () => {
      let offset: number | null = 0;
      let response: Inbox | null = null;

      const items: Thread[] = [];
      const seen = new Set<number>();

      while (offset !== null) {
        if (seen.has(offset)) {
          throw new Error(
            "Could not finish loading conversations. Please retry.",
          );
        }

        seen.add(offset);

        response = await requestJson<Inbox>(
          `/api/engagements/conversations?limit=100&offset=${offset}`,
          { signal: controller.signal },
        );

        if (response.viewer_role !== role) {
          throw new Error(
            "This messaging view is not available for your account.",
          );
        }

        if (
          viewerRef.current &&
          viewerRef.current !== response.viewer_id
        ) {
          setInbox(null);
          setActiveKey(null);
          setDrafts({});
          setLoaded(blank);

          throw new Error(
            "Your signed-in account changed. Reload the page before continuing.",
          );
        }

        items.push(...response.items);
        offset = response.next_offset;
      }

      if (!response || controller.signal.aborted) return;

      viewerRef.current = response.viewer_id;

      setInbox({
        ...response,
        items: [...new Map(items.map((thread) => [
          keyOf(thread),
          thread,
        ])).values()],
      });
    };

    void load()
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;

        setInboxError(
          error instanceof Error
            ? error.message
            : "Could not load conversations.",
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setInboxLoading(false);
        }
      });

    return () => controller.abort();
  }, [role, inboxVersion]);

  useEffect(() => {
    if (!inbox) return;

    const identity =
      `${inbox.viewer_id}:${role}:${engagementParam || ""}:${channelParam || ""}`;

    if (selectionInit.current === identity) return;
    selectionInit.current = identity;

    const remembered = storageRead(
      `penflow:messages:${role}:${inbox.viewer_id}`,
    );

    const key = selectThread(
      inbox.items,
      engagementParam,
      channelParam,
      remembered,
    );

    setActiveKey(key);
    setMobileThread(!!engagementParam && !!key);

    if (engagementParam && !key) {
      setNotice(
        "That engagement conversation is unavailable. Select an authorized conversation below.",
      );
    }
  }, [inbox, role, engagementParam, channelParam]);

  useEffect(() => {
    if (!activeKey || !inbox) return;

    if (!inbox.items.some((thread) => keyOf(thread) === activeKey)) {
      setActiveKey(null);
      return;
    }

    const storageKey =
      `penflow:messages:${role}:${inbox.viewer_id}`;

    const remembered = storageRead(storageKey);

    storageWrite(storageKey, {
      last: activeKey,
      engagements: {
        ...remembered.engagements,
        [activeKey.split("::")[0]]: activeKey,
      },
    });
  }, [activeKey, inbox, role]);

  useEffect(() => {
    if (!activeKey) {
      setLoaded(blank);
      return;
    }

    const [id, channel] = activeKey.split("::");
    const controller = new AbortController();

    setLoaded({
      key: activeKey,
      messages: [],
      loading: true,
      error: null,
    });

    const load = async () => {
      const response = await requestJson<{ items: Message[] }>(
        `/api/engagements/${id}/messages?channel=${channel}`,
        { signal: controller.signal },
      );

      if (controller.signal.aborted) return;

      setLoaded({
        key: activeKey,
        messages: response.items,
        loading: false,
        error: null,
      });

      if (document.visibilityState === "visible") {
        try {
          await requestJson(
            `/api/engagements/${id}/messages/read?channel=${channel}`,
            {
              method: "PATCH",
              signal: controller.signal,
            },
          );

          if (!controller.signal.aborted) {
            window.dispatchEvent(new Event(MESSAGES_UPDATED_EVENT));
            refreshInbox();
          }
        } catch {
          if (!controller.signal.aborted) {
            setNotice(
              "Messages loaded, but the unread status could not be updated. Refresh to retry.",
            );
          }
        }
      }
    };

    void load().catch((error: unknown) => {
      if (controller.signal.aborted) return;

      setLoaded({
        key: activeKey,
        messages: [],
        loading: false,
        error:
          error instanceof Error
            ? error.message
            : "Could not load messages.",
      });
    });

    return () => controller.abort();
  }, [activeKey, threadVersion, refreshInbox]);

  useEffect(() => {
    bottom.current?.scrollIntoView({
      block: "nearest",
      behavior: "instant",
    });
  }, [loaded.key, loaded.messages.length]);

  useEffect(() => {
    if (mobileThread) {
      threadHeader.current?.focus();
    }
  }, [mobileThread, activeKey]);

  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (
        Object.values(draftsRef.current).some((value) => value.trim()) ||
        sendingRef.current.size
      ) {
        event.preventDefault();
        event.returnValue = "";
      }
    };

    window.addEventListener("beforeunload", warn);

    return () => {
      window.removeEventListener("beforeunload", warn);
    };
  }, []);

  const choose = (thread: Thread) => {
    setActiveKey(keyOf(thread));
    setMobileThread(true);
    setNotice("");
  };

  const updateDraft = (value: string) => {
    if (activeKey) {
      setDrafts((previous) => ({
        ...previous,
        [activeKey]: value,
      }));
    }
  };

  async function send(event: FormEvent) {
    event.preventDefault();

    if (
      !active ||
      inboxError ||
      display.loading ||
      display.error
    ) {
      return;
    }

    const target = active;
    const key = keyOf(target);
    const originalDraft = draftsRef.current[key] || "";
    const comment = originalDraft.trim();

    if (!comment || sendingRef.current.has(key)) return;

    sendingRef.current.add(key);
    setSendingKeys(new Set(sendingRef.current));

    setSendErrors((previous) => ({
      ...previous,
      [key]: "",
    }));

    try {
      await requestJson(messageUrl(target), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          channel: target.channel,
          comment,
        }),
      });

      if (!live.current) return;

      setDrafts((previous) =>
        previous[key] === originalDraft
          ? { ...previous, [key]: "" }
          : previous,
      );

      setNotice(
        `Message sent to ${personName(target.participant)}.`,
      );

      window.dispatchEvent(new Event(MESSAGES_UPDATED_EVENT));

      refreshInbox();

      if (activeRef.current === key) {
        refreshThread();
        composer.current?.focus();
      }
    } catch (error: unknown) {
      if (live.current) {
        setSendErrors((previous) => ({
          ...previous,
          [key]:
            `${error instanceof Error ? error.message : "Could not confirm message delivery."} ` +
            "Your draft is preserved. If the connection was interrupted, " +
            "refresh the thread before retrying to avoid a duplicate.",
        }));
      }
    } finally {
      sendingRef.current.delete(key);

      if (live.current) {
        setSendingKeys(new Set(sendingRef.current));
      }
    }
  }

  return (
    <div className={styles.workspace}>
      <PageHero title="Messages" />

      <p className={styles.subtitle}>
        {role === "service_delivery"
          ? "Client and pentester conversations, organized by engagement."
          : "Your engagement conversations with Service Delivery."}
      </p>

      <div
        className={
          styles.frame +
          (mobileThread ? ` ${styles.showThread}` : "")
        }
      >
        <aside
          className={styles.inbox}
          aria-label="Engagement conversations"
        >
          <div className={styles.searchbar}>
            <Search size={17} aria-hidden="true" />

            <label
              className={styles.srOnly}
              htmlFor="conversation-search"
            >
              Search engagements and participants
            </label>

            <input
              id="conversation-search"
              type="search"
              placeholder="Search engagements or people…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />

            <button
              type="button"
              className={styles.iconButton}
              onClick={refreshInbox}
              aria-label="Refresh conversation list"
            >
              <RefreshCw size={15} />
            </button>
          </div>

          <div className={styles.conversationList}>
            {inboxLoading ? (
              <div className={styles.feedback} role="status">
                Loading conversations…
              </div>
            ) : inboxError ? (
              <div className={styles.feedback} role="alert">
                <p>{inboxError}</p>
                <button
                  type="button"
                  className={styles.textButton}
                  onClick={refreshInbox}
                >
                  Retry
                </button>
              </div>
            ) : groups.length === 0 ? (
              <div className={styles.empty}>
                <MessageCircle size={28} />

                <h2>
                  {search
                    ? "No matching conversations"
                    : "No conversations available"}
                </h2>

                <p>
                  {search
                    ? "Try an engagement name or participant."
                    : "Conversations appear when you and Service Delivery are assigned to an engagement."}
                </p>

                {search && (
                  <button
                    type="button"
                    className={styles.textButton}
                    onClick={() => setSearch("")}
                  >
                    Clear search
                  </button>
                )}
              </div>
            ) : (
              groups.map((group) => (
                <section
                  key={group.id}
                  className={styles.group}
                  aria-label={group.title}
                >
                  <h2>{group.title}</h2>

                  {group.threads.map((thread) => (
                    <button
                      key={keyOf(thread)}
                      type="button"
                      className={
                        `${styles.conversation} ` +
                        (activeKey === keyOf(thread)
                          ? styles.selected
                          : "")
                      }
                      onClick={() => choose(thread)}
                      aria-pressed={activeKey === keyOf(thread)}
                    >
                      <span
                        className={
                          `${styles.avatar} ` +
                          roleClass(thread.participant.role)
                        }
                        aria-hidden="true"
                      >
                        {initials(personName(thread.participant))}
                      </span>

                      <span className={styles.conversationText}>
                        <span className={styles.personLine}>
                          <strong>
                            {personName(thread.participant)}
                          </strong>

                          <span
                            className={
                              `${styles.badge} ` +
                              roleClass(thread.participant.role)
                            }
                          >
                            {roleName(thread.participant.role)}
                          </span>
                        </span>

                        <span className={styles.snippet}>
                          {thread.last_message?.comment ||
                            "No messages yet"}
                        </span>
                      </span>

                      <span className={styles.conversationMeta}>
                        {thread.last_message && (
                          <time
                            dateTime={thread.last_message.created_at}
                          >
                            {shortDate(thread.last_message.created_at)}
                          </time>
                        )}

                        {thread.unread_count > 0 && (
                          <span
                            className={styles.unread}
                            aria-label={
                              `${thread.unread_count} unread messages`
                            }
                          >
                            {thread.unread_count > 99
                              ? "99+"
                              : thread.unread_count}
                          </span>
                        )}
                      </span>
                    </button>
                  ))}
                </section>
              ))
            )}
          </div>

          <div className={styles.inboxFoot}>
            <ShieldCheck size={14} aria-hidden="true" />
            Separate engagement conversations
          </div>
        </aside>

        <section
          className={styles.thread}
          aria-label="Selected conversation"
        >
          {!active ? (
            <div className={styles.empty}>
              <div className={styles.sonar} aria-hidden="true" />
              <h2>Select an engagement conversation</h2>
              <p>
                Keep scope, findings and delivery updates together.
              </p>
              {notice && <p role="status">{notice}</p>}
            </div>
          ) : (
            <>
              <div className={styles.threadHead}>
                <button
                  className={
                    `${styles.iconButton} ${styles.mobileBack}`
                  }
                  type="button"
                  onClick={() => setMobileThread(false)}
                  aria-label="Back to conversation list"
                >
                  <ArrowLeft size={20} />
                </button>

                <div className={styles.threadTitle}>
                  <h2 ref={threadHeader} tabIndex={-1}>
                    {active.engagement_title}
                  </h2>

                  <p>
                    <span
                      className={
                        `${styles.badge} ` +
                        roleClass(active.participant.role)
                      }
                    >
                      {role === "service_delivery"
                        ? `${roleName(active.participant.role)} channel`
                        : "Service Delivery"}
                    </span>

                    <span>
                      with {personName(active.participant)}
                    </span>
                  </p>
                </div>

                <Link
                  href={engagementHref(role, active.engagement_id)}
                  className={styles.engagementLink}
                >
                  View engagement
                  <ArrowUpRight size={15} />
                </Link>

                <button
                  type="button"
                  className={styles.iconButton}
                  onClick={() => {
                    refreshThread();
                    refreshInbox();
                  }}
                  aria-label="Refresh messages"
                >
                  <RefreshCw size={17} />
                </button>
              </div>

              <div
                className={styles.messageBody}
                aria-busy={display.loading}
              >
                {display.loading ? (
                  <div className={styles.feedback} role="status">
                    Loading messages…
                  </div>
                ) : display.error ? (
                  <div className={styles.feedback} role="alert">
                    <p>{display.error}</p>

                    <button
                      type="button"
                      onClick={refreshThread}
                      className={styles.textButton}
                    >
                      Retry messages
                    </button>
                  </div>
                ) : display.messages.length === 0 ? (
                  <div className={styles.empty}>
                    <MessageCircle size={30} />
                    <h3>No messages yet</h3>
                    <p>
                      Send the first engagement update to{" "}
                      {personName(active.participant)}.
                    </p>
                  </div>
                ) : (
                  display.messages.map((message, index) => {
                    const own =
                      message.user.id === inbox?.viewer_id;

                    const date = fullDate(message.created_at);

                    const newDate =
                      index === 0 ||
                      date !==
                        fullDate(
                          display.messages[index - 1].created_at,
                        );

                    return (
                      <div key={message.id}>
                        {newDate && (
                          <div className={styles.dateSeparator}>
                            <time dateTime={message.created_at}>
                              {date}
                            </time>
                          </div>
                        )}

                        <article
                          className={
                            `${styles.messageRow} ` +
                            (own ? styles.own : "")
                          }
                        >
                          <span
                            className={
                              `${styles.avatar} ` +
                              roleClass(message.user.role)
                            }
                            aria-hidden="true"
                          >
                            {initials(personName(message.user))}
                          </span>

                          <div className={styles.messageContent}>
                            <div className={styles.sender}>
                              <strong>
                                {own
                                  ? "You"
                                  : personName(message.user)}
                              </strong>

                              <span
                                className={
                                  `${styles.badge} ` +
                                  roleClass(message.user.role)
                                }
                              >
                                {roleName(message.user.role)}
                              </span>
                            </div>

                            <div className={styles.bubble}>
                              <p>{message.comment}</p>
                            </div>

                            <time
                              className={styles.messageTime}
                              dateTime={message.created_at}
                              title={
                                new Date(
                                  message.created_at,
                                ).toLocaleString()
                              }
                            >
                              {time(message.created_at)}
                            </time>
                          </div>
                        </article>
                      </div>
                    );
                  })
                )}

                <div ref={bottom} />
              </div>

              <div
                className={styles.status}
                role="status"
                aria-live="polite"
              >
                {notice}
              </div>

              {sendErrors[activeKey!] && (
                <p className={styles.error} role="alert">
                  {sendErrors[activeKey!]}
                </p>
              )}

              <form
                onSubmit={send}
                className={styles.composer}
              >
                <label
                  className={styles.srOnly}
                  htmlFor="message-draft"
                >
                  Message {personName(active.participant)}
                </label>

                <textarea
                  ref={composer}
                  id="message-draft"
                  rows={1}
                  placeholder={
                    `Message ${personName(active.participant)}…`
                  }
                  value={draft}
                  onChange={(event) =>
                    updateDraft(event.target.value)
                  }
                />

                <button
                  type="submit"
                  className={styles.sendButton}
                  disabled={
                    !draft.trim() ||
                    sendingKeys.has(activeKey!) ||
                    display.loading ||
                    !!display.error ||
                    !!inboxError
                  }
                  aria-label={
                    sendingKeys.has(activeKey!)
                      ? "Sending message"
                      : `Send message to ${personName(active.participant)}`
                  }
                >
                  <Send size={20} />
                  <span>
                    {sendingKeys.has(activeKey!)
                      ? "Sending…"
                      : "Send"}
                  </span>
                </button>

                <p className={styles.composerHint}>
                To: {personName(active.participant)} ·{" "}
                {roleName(active.participant.role)}
                </p>
              </form>
            </>
          )}
        </section>
      </div>
    </div>
  );
}