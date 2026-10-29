export const MESSAGES_UPDATED_EVENT = "penflow:messages-updated";

export type MessagingRole = "client" | "pentester" | "service_delivery";

export type Channel =
  | "client_service_delivery"
  | "service_delivery_pentester";

export interface Person {
  id: string;
  full_name: string | null;
  email: string;
  role: string;
}

export interface Thread {
  engagement_id: string;
  engagement_title: string;
  channel: Channel;
  participant: Person;
  last_message: {
    comment: string;
    created_at: string;
  } | null;
  unread_count: number;
}

export interface Inbox {
  viewer_id: string;
  viewer_role: MessagingRole;
  items: Thread[];
  next_offset: number | null;
}

export interface Message {
  id: string;
  comment: string;
  created_at: string;
  user: Person;
  is_read: boolean;
}

export const keyOf = (
  thread: Pick<Thread, "engagement_id" | "channel">,
) => `${thread.engagement_id}::${thread.channel}`;

export const personName = (person: Person) =>
  person.full_name?.trim() || person.email;

export const roleName = (role: string) =>
  ({
    client: "Client",
    pentester: "Pentester",
    service_delivery: "Service Delivery",
  })[role] || "Participant";

export function groupThreads(threads: Thread[], search: string) {
  const query = search.trim().toLocaleLowerCase();

  const groups = new Map<
    string,
    {
      id: string;
      title: string;
      threads: Thread[];
      latest: string;
    }
  >();

  for (const thread of threads) {
    const existing = groups.get(thread.engagement_id) || {
      id: thread.engagement_id,
      title: thread.engagement_title,
      threads: [],
      latest: "",
    };

    existing.threads.push(thread);
    existing.latest =
      [existing.latest, thread.last_message?.created_at || ""]
        .sort()
        .at(-1) || "";

    groups.set(existing.id, existing);
  }

  return [...groups.values()]
    .filter(
      (group) =>
        !query ||
        [
          group.title,
          ...group.threads.flatMap((thread) => [
            personName(thread.participant),
            thread.participant.email,
          ]),
        ].some((value) => value.toLocaleLowerCase().includes(query)),
    )
    .sort(
      (a, b) =>
        b.latest.localeCompare(a.latest) ||
        a.title.localeCompare(b.title) ||
        a.id.localeCompare(b.id),
    )
    .map((group) => ({
      ...group,
      threads: group.threads.sort((a, b) =>
        a.channel.localeCompare(b.channel),
      ),
    }));
}

export function selectThread(
  threads: Thread[],
  engagement: string | null,
  channel: string | null,
  remembered: {
    last?: string;
    engagements?: Record<string, string>;
  },
) {
  if (engagement) {
    const explicit = threads.find(
      (thread) =>
        thread.engagement_id === engagement &&
        (!channel || thread.channel === channel),
    );

    if (channel) {
      return explicit ? keyOf(explicit) : null;
    }

    const previous = threads.find(
      (thread) =>
        thread.engagement_id === engagement &&
        keyOf(thread) === remembered.engagements?.[engagement],
    );

    return previous
      ? keyOf(previous)
      : explicit
        ? keyOf(explicit)
        : null;
  }

  return threads.some((thread) => keyOf(thread) === remembered.last)
    ? remembered.last!
    : threads[0]
      ? keyOf(threads[0])
      : null;
}

export async function requestJson<T>(
  url: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(url, {
    cache: "no-store",
    ...init,
  });

  if (!response.ok) {
    let detail = "";

    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        detail = body.detail;
      }
    } catch {
    }

    throw new Error(
      detail ||
        (response.status === 401
          ? "Your session has expired. Please sign in again."
          : response.status === 404
            ? "This conversation is no longer available to your account."
            : "Messaging is temporarily unavailable. Please retry."),
    );
  }

  return response.json() as Promise<T>;
}

export const messageUrl = (thread: Thread) =>
  `/api/engagements/${thread.engagement_id}/messages`;