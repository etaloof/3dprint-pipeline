export interface PipelineEvent {
  type: string;
  job_id?: string;
  phase?: string;
  text?: string;
  name?: string;
  summary?: string;
  ok?: boolean;
  url?: string;
  format?: string;
  message?: string;
  status?: string;
}

export function streamJob(
  sessionId: string,
  jobId: string,
  onEvent: (event: PipelineEvent) => void,
  onError?: (err: Event) => void,
): () => void {
  const es = new EventSource(`/api/sessions/${sessionId}/stream?job_id=${encodeURIComponent(jobId)}`);

  es.onmessage = (msg) => {
    try {
      onEvent(JSON.parse(msg.data));
    } catch {
      // ignore malformed events
    }
  };

  es.onerror = (err) => {
    onError?.(err);
    es.close();
  };

  return () => es.close();
}
