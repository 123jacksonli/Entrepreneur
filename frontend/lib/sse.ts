"use client";

import { useEffect, useRef } from "react";
import { PipelineEvent } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useRunEvents(
  runId: string | null,
  onEvent: (event: PipelineEvent) => void,
  onComplete?: () => void
) {
  const onEventRef = useRef(onEvent);
  const onCompleteRef = useRef(onComplete);

  useEffect(() => {
    onEventRef.current = onEvent;
    onCompleteRef.current = onComplete;
  }, [onEvent, onComplete]);

  useEffect(() => {
    if (!runId) return;

    const source = new EventSource(`${API_BASE}/runs/${runId}/events`);

    source.onmessage = (msg) => {
      try {
        const event: PipelineEvent = JSON.parse(msg.data);
        onEventRef.current?.(event);
        if (
          event.type === "run-completed" ||
          event.type === "run-stopped" ||
          event.type === "run-failed"
        ) {
          source.close();
          onCompleteRef.current?.();
        }
      } catch {
        // Ignore malformed SSE payloads.
      }
    };

    source.onerror = () => {
      source.close();
      onCompleteRef.current?.();
    };

    return () => {
      source.close();
    };
  }, [runId]);
}
