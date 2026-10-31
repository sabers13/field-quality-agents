import type { ReactNode } from "react";

import { Icon } from "./Icon";

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <p className="state" role="status">
      <span className="loading-dot" aria-hidden="true" />
      {label}…
    </p>
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
