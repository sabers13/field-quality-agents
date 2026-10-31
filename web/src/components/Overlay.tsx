import { useEffect, useId, useRef, type ReactNode, type RefObject } from "react";
import { createPortal } from "react-dom";

import { Icon } from "./Icon";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

const overlayStack: symbol[] = [];

function useOverlay(panelRef: RefObject<HTMLElement | null>, onClose: () => void): void {
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    const panel = panelRef.current;
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    if (!panel) {
      return;
    }
    const token = Symbol("overlay");
    overlayStack.push(token);
    const isTop = () => overlayStack[overlayStack.length - 1] === token;

    const focusables = (): HTMLElement[] =>
      [...panel.querySelectorAll<HTMLElement>(FOCUSABLE)].filter(
        (element) => element.offsetParent !== null || element === document.activeElement,
      );

    const first = focusables()[0] ?? panel;
    first.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (!isTop()) {
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        closeRef.current();
        return;
      }
      if (event.key !== "Tab") {
        return;
      }
      const items = focusables();
      if (items.length === 0) {
        event.preventDefault();
        panel.focus();
        return;
      }
      const firstItem = items[0];
      const lastItem = items[items.length - 1];
      if (!firstItem || !lastItem) {
        return;
      }
      const active = document.activeElement;
      if (event.shiftKey && (active === firstItem || !panel.contains(active))) {
        event.preventDefault();
        lastItem.focus();
      } else if (!event.shiftKey && (active === lastItem || !panel.contains(active))) {
        event.preventDefault();
        firstItem.focus();
      }
    };

    const { overflow } = document.body.style;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", onKeyDown, true);
    return () => {
      document.removeEventListener("keydown", onKeyDown, true);
      const index = overlayStack.indexOf(token);
      if (index >= 0) {
        overlayStack.splice(index, 1);
      }
      if (overlayStack.length === 0) {
        document.body.style.overflow = overflow;
      }
      previous?.focus();
    };
  }, [panelRef]);
}

interface OverlayProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  kind?: "sheet" | "modal";
  size?: "wide";
  subtitle?: string;
}

function Overlay({
  title,
  onClose,
  children,
  footer,
  kind = "sheet",
  size,
  subtitle,
}: OverlayProps) {
  const titleId = useId();
  const panelRef = useRef<HTMLElement | null>(null);
  useOverlay(panelRef, onClose);

  const content = (
    <div
      className="overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <section
        className={`${kind === "modal" ? "modal" : "sheet"}${size === "wide" ? " is-wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        ref={panelRef}
        tabIndex={-1}
      >
        <header className="overlay-head">
          <div>
            <h2 id={titleId}>{title}</h2>
            {subtitle ? <p className="overlay-subtitle">{subtitle}</p> : null}
          </div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close">
            <Icon name="close" size={18} />
          </button>
        </header>
        <div className="overlay-body">{children}</div>
        {footer ? <footer className="overlay-footer">{footer}</footer> : null}
      </section>
    </div>
  );

  return createPortal(content, document.body);
}

export function Sheet(props: Omit<OverlayProps, "kind">) {
  return <Overlay {...props} kind="sheet" />;
}

export function Modal(props: Omit<OverlayProps, "kind">) {
  return <Overlay {...props} kind="modal" />;
}
