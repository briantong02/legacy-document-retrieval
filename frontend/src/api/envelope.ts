export interface ApiErrorEnvelope {
  code: string;
  message: string;
  details?: unknown;
}

export interface ApiResponseEnvelope<T> {
  success: boolean;
  data: T | null;
  error: ApiErrorEnvelope | null;
  message?: string;
}

export function unwrapApiData<T>(payload: unknown): T {
  if (
    payload &&
    typeof payload === "object" &&
    "success" in payload &&
    "data" in payload
  ) {
    return (payload as ApiResponseEnvelope<T>).data as T;
  }

  return payload as T;
}

export function extractErrorMessage(
  payload: unknown,
  fallback: string,
): string {
  if (!payload || typeof payload !== "object") {
    return fallback;
  }

  const envelope = payload as Partial<ApiResponseEnvelope<unknown>> & {
    detail?: unknown;
  };

  if (envelope.error && typeof envelope.error.message === "string") {
    return envelope.error.message;
  }

  if (typeof envelope.detail === "string") {
    return envelope.detail;
  }

  return fallback;
}
