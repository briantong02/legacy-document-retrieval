import { apiFetch, buildApiUrl } from "./client";
import { unwrapApiData } from "./envelope";
import type { DocumentOptionKey, DocumentResultRow } from "@/types/documents";

export interface SearchDocumentsInput {
  option: DocumentOptionKey;
  filters: Record<string, string>;
}

export async function searchDocuments(
  input: SearchDocumentsInput,
): Promise<DocumentResultRow[]> {
  const searchParams = new URLSearchParams();

  Object.entries(input.filters).forEach(([key, value]) => {
    if (value.trim()) {
      searchParams.set(key, value.trim());
    }
  });

  const queryString = searchParams.toString();
  const response = await apiFetch(
    `/documents/${input.option}${queryString ? `?${queryString}` : ""}`,
  );

  return unwrapApiData<DocumentResultRow[]>(await response.json());
}

export function getViewUrl(
  option: DocumentOptionKey,
  resourceId: string,
  resourceName: string,
): string {
  const searchParams = new URLSearchParams({ resourceName });
  return buildApiUrl(
    `/documents/${option}/${encodeURIComponent(resourceId)}/view?${searchParams.toString()}`,
  );
}

export function getDownloadUrl(
  option: DocumentOptionKey,
  resourceId: string,
  resourceName: string,
): string {
  const searchParams = new URLSearchParams({ resourceName });
  return buildApiUrl(
    `/documents/${option}/${encodeURIComponent(resourceId)}/download?${searchParams.toString()}`,
  );
}
