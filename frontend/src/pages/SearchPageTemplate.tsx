import { useCallback, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { SearchForm } from "@/components/SearchForm";
import { DocumentViewer } from "@/components/DocumentViewer";
import { ResultsGrid } from "@/components/ResultsGrid";
import { Card } from "@/components/ui/Card";
import { InfoIcon } from "@/components/icons";
import { searchDocuments, getDownloadUrl, getViewUrl } from "@/api/documents";
import type {
  DocumentOptionKey,
  DocumentResultRow,
  ResultsColumn,
  SearchField,
} from "@/types/documents";

interface SearchPageTemplateProps {
  option: DocumentOptionKey;
  title: string;
  description: string;
  fields: SearchField[];
  columns: ResultsColumn[];
}

function canViewRow(row: DocumentResultRow): boolean {
  const resourceName = String(row.RESOURCENAME ?? "").toLowerCase();

  return resourceName.endsWith(".pdf") || resourceName.endsWith(".xlsx");
}

export function SearchPageTemplate({
  option,
  title,
  description,
  fields,
  columns,
}: SearchPageTemplateProps) {
  const requiredField = fields.find((field) => field.required) ?? fields[0];
  const initialValues = useMemo(() => {
    return fields.reduce<Record<string, string>>((accumulator, field) => {
      accumulator[field.name] = "";
      return accumulator;
    }, {});
  }, [fields]);

  const [values, setValues] = useState<Record<string, string>>(initialValues);
  const [submittedValues, setSubmittedValues] = useState<Record<
    string,
    string
  > | null>(null);
  const [viewerRow, setViewerRow] = useState<DocumentResultRow | null>(null);

  const query = useQuery({
    queryKey: ["documents", option, submittedValues],
    queryFn: () => searchDocuments({ option, filters: submittedValues ?? {} }),
    enabled: submittedValues !== null,
    placeholderData: (previousData: DocumentResultRow[] | undefined) =>
      previousData ?? [],
  });

  // A failed search must not fall through to the empty state. `placeholderData` keeps the
  // previous result set on screen, so without this a failure would either read as
  // "0 documents found" or, worse, leave the last search's rows sitting under the new
  // filters as though they matched.
  const searchFailed = query.isError && !query.isFetching;
  const rows = searchFailed ? [] : (query.data ?? []);
  const errorMessage =
    query.error instanceof Error && query.error.message
      ? query.error.message
      : "The search could not be completed. Please try again.";
  const hasUnviewableRows = rows.some((row) => !canViewRow(row));
  const viewerDocumentName = String(viewerRow?.RESOURCENAME ?? "");
  const viewerDocumentType = viewerDocumentName.toLowerCase().endsWith(".xlsx")
    ? "xlsx"
    : viewerDocumentName.toLowerCase().endsWith(".pdf")
      ? "pdf"
      : null;

  const downloadRow = useCallback(
    (row: DocumentResultRow) => {
      window.open(
        getDownloadUrl(
          option,
          String(row.RESOURCEID ?? ""),
          String(row.RESOURCENAME ?? ""),
        ),
        "_blank",
        "noopener,noreferrer",
      );
    },
    [option],
  );

  return (
    <section className="space-y-6">
      <Card padding="sm" className="mx-auto w-full max-w-10xl">
        <div className="mb-5">
          <h1 className="font-display text-lg font-medium text-[#414041]">
            {title}
          </h1>
          <p className="mt-1 text-sm text-[#666666]">{description}</p>
        </div>

        <SearchForm
          fields={fields}
          values={values}
          onChange={(name, value) =>
            setValues((current) => ({ ...current, [name]: value }))
          }
          onSubmit={() => setSubmittedValues(values)}
          isLoading={query.isFetching}
        />
      </Card>

      <div className="mx-auto w-full max-w-10xl space-y-2">
        {submittedValues && !searchFailed ? (
          <p className="text-sm text-[#666666]">
            {query.isFetching
              ? "Searching…"
              : `${rows.length} document${rows.length === 1 ? "" : "s"} found`}
          </p>
        ) : null}

        {searchFailed ? (
          <p
            role="alert"
            className="rounded-md border border-b2b-red/30 bg-b2b-red-soft px-3 py-2 text-sm text-b2b-red"
          >
            {errorMessage}
          </p>
        ) : null}

        <ResultsGrid
          rows={rows}
          columns={columns}
          canView={canViewRow}
          emptyMessage={
            searchFailed
              ? "No results to show because the search failed."
              : submittedValues
                ? `No documents matched ${requiredField?.label ?? "the current search"}.`
                : `Use ${requiredField?.label ?? "the filters above"} to find documents.`
          }
          onView={(row) => {
            setViewerRow(row);
          }}
          onDownload={downloadRow}
        />

        {hasUnviewableRows ? (
          <p className="flex items-center gap-2 text-sm text-[#666666]">
            <InfoIcon className="h-4 w-4 shrink-0" />
            Inline viewing is not available for this file type — download only.
          </p>
        ) : null}
      </div>

      <DocumentViewer
        open={viewerRow !== null && viewerDocumentType !== null}
        documentName={viewerDocumentName}
        sourceUrl={
          viewerRow && viewerDocumentType
            ? getViewUrl(
                option,
                String(viewerRow.RESOURCEID ?? ""),
                String(viewerRow.RESOURCENAME ?? ""),
              )
            : ""
        }
        documentType={viewerDocumentType ?? "pdf"}
        onClose={() => setViewerRow(null)}
        onDownload={viewerRow ? () => downloadRow(viewerRow) : undefined}
      />
    </section>
  );
}
