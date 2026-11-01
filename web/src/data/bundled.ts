/** The recorded run bundled by `fqa export`. */

import type { StaticBundle } from "./fixtures";

declare global {
  interface Window {
    __FQA_BUNDLE__?: StaticBundle;
  }
}

/** The exported bundle injected by `data/bundle.js`, when this page has one. */
export function bundledData(): StaticBundle | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.__FQA_BUNDLE__ ?? null;
}

/** The bundle's manifest, used for the read-only banner on the command centre. */
export function bundledManifest(): StaticBundle["manifest"] | null {
  return bundledData()?.manifest ?? null;
}

/**
 * Static mode reads only the exported run.
 *
 * There is deliberately no fixture fallback: the development fixtures carry
 * invented numbers, and PLAN §2.4 requires every dashboard number to come from
 * `results/`. A build with no bundle shows that the export is missing instead
 * of quietly presenting fake data. The fixtures stay importable for the unit
 * tests, which never ship.
 */
export function staticBundle(): StaticBundle | null {
  return bundledData();
}
