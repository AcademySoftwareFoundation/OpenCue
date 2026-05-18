/********************************************************************/
// Utility functions for managing local job notification subscriptions:
// - CRUD on per-job subscriptions stored in browser localStorage
// - Pure decision logic for picking which entries need notifying now
// - Cross-component change-event bus so hooks re-read after any mutation
/********************************************************************/

const STORAGE_KEY = "cueweb:job-subscriptions";
const CHANGE_EVENT = "cueweb:subscriptions-changed";

export type JobSubscription = {
  jobId: string;
  jobName: string;
  subscribedAt: number;
  notifiedAt: number | null;
};

export type SubscriptionStore = Record<string, JobSubscription>;

// Read all subscriptions from localStorage. Returns {} when the stored
// value is missing, malformed, or not a plain object, or when called
// outside the browser (SSR).
export function getSubscriptions(): SubscriptionStore {
  if (typeof window === "undefined") return {};
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return {};

  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as SubscriptionStore;
    }
    return {};
  } catch {
    return {};
  }
}

// Look up a single subscription by job UUID. Returns undefined if not subscribed.
export function getSubscription(jobId: string): JobSubscription | undefined {
  return getSubscriptions()[jobId];
}

// Persist a new subscription with notifiedAt=null. No-op if the jobId is already subscribed.
export function addSubscription(jobId: string, jobName: string): void {
  const store = getSubscriptions();
  if (store[jobId]) return;
  store[jobId] = {
    jobId,
    jobName,
    subscribedAt: Date.now(),
    notifiedAt: null,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  emitChange();
}

// Remove a subscription entirely. No-op if the entry does not exist.
export function removeSubscription(jobId: string): void {
  const store = getSubscriptions();
  if (!store[jobId]) return;
  delete store[jobId];
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  emitChange();
}

// Mark a subscription as notified without removing it.
// No-op if the entry does not exist.
export function markNotified(jobId: string): void {
  const store = getSubscriptions();
  if (!store[jobId]) return;
  store[jobId].notifiedAt = Date.now();
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  emitChange();
}

/*
 * Determines which subscribed jobs need a toast fired now.
 * @param store - Current subscription store snapshot.
 * @param fetchedStates - Map of jobId to current job state (e.g. "FINISHED").
 * @returns Entries that are subscribed, FINISHED, and not yet notified.
 */
export function pickEntriesToNotify(
  store: SubscriptionStore,
  fetchedStates: Record<string, string>,
): JobSubscription[] {
  return Object.values(store).filter((entry) => entry.notifiedAt === null && fetchedStates[entry.jobId] === "FINISHED");
}

// Notify all useJobSubscriptions hook instances that the store has changed.
// Called internally by mutators and by the poller after marking notified.
function emitChange(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(CHANGE_EVENT));
  }
}

// Subscribe to store-change events. Returns an unsubscribe function.
// Listens for in-process mutations (CHANGE_EVENT) and cross-tab mutations
// (the browser "storage" event, fired in other tabs when localStorage
// changes), so the hook stays in sync no matter which tab wrote.
export function subscribeToChanges(listener: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  const onStorage = (e: StorageEvent) => {
    if (e.key === STORAGE_KEY || e.key === null) listener();
  };
  window.addEventListener(CHANGE_EVENT, listener);
  window.addEventListener("storage", onStorage);
  return () => {
    window.removeEventListener(CHANGE_EVENT, listener);
    window.removeEventListener("storage", onStorage);
  };
}
