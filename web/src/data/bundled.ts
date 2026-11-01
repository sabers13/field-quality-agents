/** The recorded run bundled by `fqa export`, or the Q6 fixtures in dev. */

import { fixtureBundle, type StaticBundle } from "./fixtures";

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

/** Static mode reads the exported run when present, else the development fixtures. */
export function staticBundle(): StaticBundle {
  return bundledData() ?? fixtureBundle;
}
