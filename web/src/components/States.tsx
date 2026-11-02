import type { ReactNode } from "react";

import { Icon } from "./Icon";

type LoadingLayout = "content" | "case" | "metrics" | "list";

export function LoadingState({ label = "Loading", layout = "content" }: {
  label?: string;
  layout?: LoadingLayout;
}) {
  return (
    <div className={`loading-state loading-state--${layout}`} role="status" aria-live="polite" aria-busy="true">
      <p className="loading-label"><span className="loading-dot" aria-hidden="true" />{label}…</p>
      <div className="loading-placeholder" aria-hidden="true">
        <span className="skeleton-line skeleton-short" />
        {layout === "metrics" ? <div className="skeleton-metrics">{[0, 1, 2].map((item) =>
          <div key={item}><span className="skeleton-line" /><span className="skeleton-value" /><span className="skeleton-line" /></div>,
        )}</div> : layout === "list" ? <div className="skeleton-list">{[0, 1, 2, 3].map((item) =>
          <div key={item}><span className="skeleton-line" /><span className="skeleton-line skeleton-short" /></div>,
        )}</div> : <>
          <div className="skeleton-copy"><span className="skeleton-line" /><span className="skeleton-line" /><span className="skeleton-line skeleton-short" /></div>
          <div className="skeleton-inset"><span className="skeleton-line skeleton-short" /><span className="skeleton-line" /><span className="skeleton-line" /></div>
        </>}
        <span className="skeleton-line skeleton-short" />
      </div>
    </div>
  );
}

export function ErrorState({
  title = "This view could not load",
  error,
  onRetry,
  action,
}: {
  title?: string;
  error: Error;
  onRetry?: () => void;
  action?: ReactNode;
}) {
  return (
    <div className="state state-error" role="alert">
      <h2>{title}</h2>
      <p>{error.message}</p>
      <div className="state-actions">
        {onRetry ? (
          <button type="button" className="btn btn-secondary" onClick={onRetry}>
            <Icon name="restart" size={14} /> Retry
          </button>
        ) : null}
        {action}
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="state state-empty">
      <h2>{title}</h2>
      {children ? <p>{children}</p> : null}
    </div>
  );
}

export function Panel({
  title,
  aside,
  children,
  className,
}: {
  title: string;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel${className ? ` ${className}` : ""}`}>
      <header className="panel-head">
        <h2>{title}</h2>
        {aside}
      </header>
      {children}
    </section>
  );
}
