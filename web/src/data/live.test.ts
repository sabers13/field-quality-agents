import { describe, expect, it, vi } from "vitest";

import { ApiError, LiveDataSource } from "./source";
import type { StreamEvent } from "../types";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

class FakeEventSource {
  readonly listeners = new Map<string, Set<EventListenerOrEventListenerObject>>();
  closed = false;
  readonly url: string;

  constructor(url: string) {
    this.url = url;
  }

  addEventListener(type: string, listener: EventListenerOrEventListenerObject): void {
    const set = this.listeners.get(type) ?? new Set();
    set.add(listener);
    this.listeners.set(type, set);
  }

  removeEventListener(type: string, listener: EventListenerOrEventListenerObject): void {
    this.listeners.get(type)?.delete(listener);
  }

  close(): void {
    this.closed = true;
  }

  emit(type: string, data: unknown, lastEventId = ""): void {
    const event = { data: JSON.stringify(data), lastEventId } as MessageEvent<string>;
    for (const listener of this.listeners.get(type) ?? []) {
      if (typeof listener === "function") {
        listener(event);
      } else {
        listener.handleEvent(event);
      }
    }
  }
}

describe("live data source", () => {
  it("builds the documented case query", async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse({ items: [], total: 0, limit: 50, offset: 0 }),
    ) as unknown as typeof fetch;
    const source = new LiveDataSource({ baseUrl: "/api", fetchImpl });
    await source.getCases({ status: "needs_engineer", safety: true, q: "lamp", limit: 20, offset: 5 });
    const url = String((fetchImpl as unknown as ReturnType<typeof vi.fn>).mock.calls[0]?.[0]);
    expect(url).toContain("/api/cases?");
    expect(url).toContain("status=needs_engineer");
    expect(url).toContain("safety=true");
    expect(url).toContain("q=lamp");
    expect(url).toContain("limit=20");
    expect(url).toContain("offset=5");
  });

  it("unwraps list endpoints and passes the week filter", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/issues")) {
        return jsonResponse({ items: [{ id: "I-1" }] });
      }
      if (url.includes("/replay/runs/run-1/events")) {
        return jsonResponse({ items: [{ seq: 1 }] });
      }
      if (url.includes("/replay/runs")) {
        return jsonResponse({ items: [{ run_id: "run-1" }] });
      }
      return jsonResponse({ week_start: "2025-06-02" });
    }) as unknown as typeof fetch;
    const source = new LiveDataSource({ baseUrl: "/api/", fetchImpl });
    expect(await source.getIssues()).toEqual([{ id: "I-1" }]);
    expect(await source.getReplayRuns()).toEqual([{ run_id: "run-1" }]);
    expect(await source.getReplayEvents("run-1")).toEqual([{ seq: 1 }]);
    await source.getWeeklyReport("2025-06-02");
    const calls = (fetchImpl as unknown as ReturnType<typeof vi.fn>).mock.calls;
    expect(String(calls[3]?.[0])).toBe("/api/reports/weekly?week_start=2025-06-02");
  });

  it("posts a decision with the documented body", async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse({ case: { id: "C-1" }, trace: [], pending: null, issue_ids: [] }),
    ) as unknown as typeof fetch;
    const source = new LiveDataSource({ baseUrl: "/api", fetchImpl });
    const response = await source.submitDecision("C-1", {
      action: "override",
      rationale: "Use the cold soak",
      edited_proposal: null,
    });
    expect(response.case.id).toBe("C-1");
    const [url, init] = (fetchImpl as unknown as ReturnType<typeof vi.fn>).mock.calls[0] ?? [];
    expect(String(url)).toBe("/api/cases/C-1/decision");
    expect((init as RequestInit).method).toBe("POST");
    expect(JSON.parse(String((init as RequestInit).body))).toEqual({
      action: "override",
      rationale: "Use the cold soak",
      edited_proposal: null,
    });
  });

  it("raises an ApiError with the status on a failed response", async () => {
    const fetchImpl = vi.fn(async () => jsonResponse({ detail: "no" }, 503)) as unknown as typeof fetch;
    const source = new LiveDataSource({ baseUrl: "/api", fetchImpl });
    await expect(source.getCase("C-1")).rejects.toMatchObject({ name: "ApiError", status: 503 });
    await expect(source.getCase("C-1")).rejects.toBeInstanceOf(ApiError);
  });

  it("streams named SSE events and connection changes", () => {
    const fake = new FakeEventSource("/api/events");
    const source = new LiveDataSource({
      baseUrl: "/api",
      eventSourceFactory: () => fake as unknown as EventSource,
    });
    const received: StreamEvent[] = [];
    const unsubscribe = source.subscribe((event) => received.push(event));
    fake.emit("open", {});
    fake.emit("trace", { case_id: "C-1", step: { agent: "analysis" }, at: "2025-06-09T09:00:00Z" }, "42");
    fake.emit("heartbeat", { at: "2025-06-09T09:00:15Z" });

    expect(received.map((event) => event.kind)).toEqual(["connection", "trace", "heartbeat"]);
    expect(received[1]?.id).toBe("42");
    expect(received[1]?.data.case_id).toBe("C-1");

    unsubscribe();
    expect(fake.closed).toBe(true);
  });

  it("does not subscribe when EventSource is unavailable", () => {
    const source = new LiveDataSource({ fetchImpl: vi.fn() as unknown as typeof fetch });
    const unsubscribe = source.subscribe(() => undefined);
    expect(typeof unsubscribe).toBe("function");
  });
});
