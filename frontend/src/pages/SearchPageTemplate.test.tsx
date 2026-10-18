import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SearchPageTemplate } from "./SearchPageTemplate";
import { searchDocuments } from "@/api/documents";
import type { ResultsColumn, SearchField } from "@/types/documents";

vi.mock("@/api/documents", () => ({
  searchDocuments: vi.fn(),
  getViewUrl: () => "/view",
  getDownloadUrl: () => "/download",
}));

const FIELDS: SearchField[] = [
  { name: "supplierNumber", label: "Supplier Number", required: true },
];
const COLUMNS: ResultsColumn[] = [{ key: "RESOURCENAME", label: "Name" }];

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={client}>
      <SearchPageTemplate
        option="supplier-invoices/general"
        title="General"
        description="General invoices"
        fields={FIELDS}
        columns={COLUMNS}
      />
    </QueryClientProvider>,
  );
}

async function search(term: string) {
  await userEvent.type(screen.getByLabelText(/Supplier Number/), term);
  await userEvent.click(screen.getByRole("button", { name: /search/i }));
}

describe("SearchPageTemplate", () => {
  beforeEach(() => {
    vi.mocked(searchDocuments).mockReset();
  });

  // A backend failure used to render as "0 documents found", so testers reported the
  // search as returning nothing when it was actually erroring.
  it("reports a failed search instead of an empty result", async () => {
    vi.mocked(searchDocuments).mockRejectedValue(new Error("Database is down"));

    renderPage();
    await search("12345");

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Database is down"),
    );
    expect(screen.queryByText(/0 documents found/)).not.toBeInTheDocument();
  });

  it("falls back to a generic message when the error carries none", async () => {
    vi.mocked(searchDocuments).mockRejectedValue(new Error(""));

    renderPage();
    await search("12345");

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        /could not be completed/i,
      ),
    );
  });

  // placeholderData keeps the previous rows while a new query runs. On failure they must
  // not stay on screen under the new filters as though they matched.
  it("clears earlier results when a later search fails", async () => {
    vi.mocked(searchDocuments).mockResolvedValueOnce([
      { RESOURCENAME: "first-hit.pdf" },
    ]);

    renderPage();
    await search("12345");
    await waitFor(() =>
      expect(screen.getByText("first-hit.pdf")).toBeInTheDocument(),
    );

    vi.mocked(searchDocuments).mockRejectedValueOnce(new Error("Boom"));
    await search("67890");

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.queryByText("first-hit.pdf")).not.toBeInTheDocument();
  });

  it("shows the result count when the search succeeds", async () => {
    vi.mocked(searchDocuments).mockResolvedValue([
      { RESOURCENAME: "invoice.pdf" },
    ]);

    renderPage();
    await search("12345");

    await waitFor(() =>
      expect(screen.getByText("1 document found")).toBeInTheDocument(),
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
