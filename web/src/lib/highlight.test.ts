import { describe, expect, it } from "vitest";

import { highlightQuotes } from "./highlight";

describe("narrative quote highlighting", () => {
  it("marks verbatim quotes and records their verification", () => {
    const narrative = "The rear camera shows a blue screen when wet. The dealer replaced the camera once.";
    const segments = highlightQuotes(
      narrative,
      [
        { kind: "symptom", quote: "blue screen" },
        { kind: "other", quote: "replaced the camera once" },
      ],
      [
        {
          source_type: "case",
          source_id: "C-1",
          quote: "blue screen",
          verified: true,
        },
      ],
    );
    const quotes = segments.filter((segment) => segment.quote);
    expect(quotes).toHaveLength(2);
    expect(quotes[0]?.verified).toBe(true);
    expect(quotes[1]?.verified).toBe(false);
    expect(segments.map((segment) => segment.text).join("")).toBe(narrative);
  });

  it("leaves a narrative untouched when no clue matches", () => {
    const segments = highlightQuotes("A plain report.", [{ kind: "symptom", quote: "not here" }]);
    expect(segments).toEqual([{ text: "A plain report." }]);
  });

  it("matches case-insensitively and merges overlapping spans", () => {
    const segments = highlightQuotes("Battery heater open circuit", [
      { kind: "symptom", quote: "BATTERY HEATER" },
      { kind: "condition", quote: "battery heater open" },
    ]);
    const quotes = segments.filter((segment) => segment.quote);
    expect(quotes).toHaveLength(1);
    expect(quotes[0]?.text).toBe("Battery heater open");
  });

  it("ignores quotes shorter than four characters", () => {
    const segments = highlightQuotes("A B C", [{ kind: "other", quote: "A" }]);
    expect(segments).toEqual([{ text: "A B C" }]);
  });
});
