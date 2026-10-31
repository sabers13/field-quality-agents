import { useEffect, useRef, useState, type ReactNode } from "react";

export type AsyncStatus = "idle" | "loading" | "refreshing" | "ready" | "error";

export interface AsyncState<T> {
  status: AsyncStatus;
  data: T | null;
  error: Error | null;
  reload: () => void;
}

/**
 * Run an async loader whenever `key` changes and expose loading/error state.
 * The loader is kept in a ref so callers do not need useCallback; the key is
 * the explicit dependency.
 */
export function useAsync<T>(loader: () => Promise<T>, key: string, enabled = true): AsyncState<T> {
  const [state, setState] = useState<{ status: AsyncStatus; data: T | null; error: Error | null }>({
    status: enabled ? "loading" : "idle",
    data: null,
    error: null,
  });
  const [nonce, setNonce] = useState(0);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  useEffect(() => {
    if (!enabled) {
      setState((previous) => ({ ...previous, status: "idle" }));
      return;
    }
    let active = true;
    setState((previous) => ({
      ...previous,
      status: previous.data === null ? "loading" : "refreshing",
      error: null,
    }));
    loaderRef.current().then(
      (data) => {
        if (active) {
          setState({ status: "ready", data, error: null });
        }
      },
      (error: unknown) => {
        if (active) {
          setState((previous) => ({
            status: "error",
            data: previous.data,
            error: error instanceof Error ? error : new Error(String(error)),
          }));
        }
      },
    );
    return () => {
      active = false;
    };
  }, [key, nonce, enabled]);

  return {
    ...state,
    reload: () => setNonce((value) => value + 1),
  };
}

export function WhenLoaded<T>({
  state,
  children,
  loading,
}: {
  state: AsyncState<T>;
  children: (data: T) => ReactNode;
  loading?: ReactNode;
}) {
  if (state.data !== null) {
    return <>{children(state.data)}</>;
  }
  return <>{loading ?? null}</>;
}
