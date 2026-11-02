import { useEffect, useId, useRef, useState } from "react";

import { useApp, type AppMode } from "../app/AppContext";
import { Icon } from "./Icon";

const SOURCES: { mode: AppMode; label: string; description: string }[] = [
  { mode: "static", label: "Saved results", description: "Bundled evidence. Works offline and stays read-only." },
  { mode: "replay", label: "Recorded run", description: "Browse the saved run through this server. Read-only." },
  { mode: "live", label: "Live connection", description: "Follow the connected desk. Case decisions write back." },
];

export function WorkspaceSettings({ bundled }: { bundled: boolean }) {
  const { mode, setMode, resolvedTheme, setTheme } = useApp();
  const [open, setOpen] = useState(false);
  const sourceId = useId();
  const container = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const dismiss = (event: PointerEvent) => {
      if (event.target instanceof Node && !container.current?.contains(event.target)) setOpen(false);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
        trigger.current?.focus();
      }
    };
    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", dismiss);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);

  return <div className="workspace-settings">
    <div className="data-settings" ref={container} onBlur={(event) => {
      if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
    }}>
      <button type="button" className="data-settings-trigger" ref={trigger}
        aria-expanded={open} aria-controls={sourceId} onClick={() => setOpen(!open)}>
        Data source <Icon name="chevron" size={14} />
      </button>
      <div id={sourceId} className={`data-settings-panel${open ? " is-open" : ""}`}
        role="group" aria-label="Data source choices" aria-hidden={!open} inert={!open}>
        <p className="data-settings-label">Choose the evidence source</p>
        {SOURCES.filter((item) => !bundled || item.mode === "static").map((item) =>
          <button key={item.mode} type="button" className="data-source-option" aria-pressed={mode === item.mode}
            disabled={item.mode === "static" && !bundled}
            onClick={() => { setMode(item.mode); setOpen(false); trigger.current?.focus(); }}>
            <span><strong>{item.label}</strong><span>{item.mode === "static" && !bundled ? "Available in the offline export." : item.description}</span></span>
            {mode === item.mode ? <Icon name="check" size={16} /> : null}
          </button>,
        )}
      </div>
    </div>
    <div className="theme-switch" role="group" aria-label="Appearance">
      <button type="button" aria-label="Light theme" title="Light theme"
        aria-pressed={resolvedTheme === "light"} onClick={() => setTheme("light")}><Icon name="sun" size={18} /></button>
      <button type="button" aria-label="Dark theme" title="Dark theme"
        aria-pressed={resolvedTheme === "dark"} onClick={() => setTheme("dark")}><Icon name="moon" size={18} /></button>
    </div>
  </div>;
}
