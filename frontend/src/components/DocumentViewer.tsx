import { useEffect, useMemo, useState } from "react";
import { Document as PdfDocument, Page, pdfjs } from "react-pdf";
import * as XLSX from "xlsx";
import { Button } from "@/components/ui/Button";
import { CloseIcon, DownloadIcon, FileTextIcon } from "@/components/icons";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

interface DocumentViewerProps {
  open: boolean;
  documentName: string;
  sourceUrl: string;
  documentType: "pdf" | "xlsx";
  onClose: () => void;
  onDownload?: () => void;
}

interface WorkbookSheet {
  name: string;
  rows: Array<Array<string | number | boolean | null>>;
}

export function DocumentViewer({
  open,
  documentName,
  sourceUrl,
  documentType,
  onClose,
  onDownload,
}: DocumentViewerProps) {
  const [pdfPageCount, setPdfPageCount] = useState(0);
  const [workbookSheets, setWorkbookSheets] = useState<WorkbookSheet[]>([]);
  const [activeSheet, setActiveSheet] = useState(0);
  const [loadingWorkbook, setLoadingWorkbook] = useState(false);
  const [workbookError, setWorkbookError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;

    if (!open || documentType !== "xlsx") {
      setWorkbookSheets([]);
      setWorkbookError(null);
      setLoadingWorkbook(false);
      return;
    }

    setLoadingWorkbook(true);
    setWorkbookError(null);

    void fetch(sourceUrl)
      .then((response) => response.arrayBuffer())
      .then((buffer) => {
        if (ignore) {
          return;
        }

        const workbook = XLSX.read(buffer, { type: "array" });
        const sheets = workbook.SheetNames.map((sheetName) => {
          const sheet = workbook.Sheets[sheetName];

          if (!sheet) {
            return {
              name: sheetName,
              rows: [] as Array<Array<string | number | boolean | null>>,
            };
          }

          const rows = XLSX.utils.sheet_to_json<
            Array<string | number | boolean | null>
          >(sheet, {
            header: 1,
            blankrows: false,
            defval: null,
          });

          return {
            name: sheetName,
            rows,
          };
        });

        setWorkbookSheets(sheets);
        setActiveSheet(0);
      })
      .catch((error: unknown) => {
        if (!ignore) {
          setWorkbookError(
            error instanceof Error ? error.message : "Unable to load workbook",
          );
        }
      })
      .finally(() => {
        if (!ignore) {
          setLoadingWorkbook(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [documentType, open, sourceUrl]);

  useEffect(() => {
    if (!open) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose, open]);

  const activeSheetRows = useMemo(
    () => workbookSheets[activeSheet]?.rows ?? [],
    [activeSheet, workbookSheets],
  );

  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={`Document preview for ${documentName}`}
    >
      <div className="flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-xl border border-black/5 bg-white shadow-[0_24px_80px_rgba(0,0,0,0.35)]">
        <div className="flex shrink-0 items-center justify-between gap-4 border-b border-[#ebebeb] px-6 py-4">
          <div className="flex min-w-0 items-center gap-3">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-[#ebebeb] bg-[#f2f2f2] text-b2b-red">
              <FileTextIcon className="h-4 w-4" />
            </span>
            <h2 className="truncate font-display text-base font-medium text-[#414041]">
              {documentName}
            </h2>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            {onDownload ? (
              <Button
                size="sm"
                icon={<DownloadIcon className="h-4 w-4" />}
                onClick={onDownload}
              >
                Download
              </Button>
            ) : null}
            <Button
              variant="ghost"
              size="icon"
              aria-label="Close document viewer"
              onClick={onClose}
            >
              <CloseIcon className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="flex-1 overflow-auto bg-[#f1f1f1] p-6">
          {documentType === "pdf" ? (
            <div className="flex flex-col items-center gap-4 [&_.react-pdf__Page]:shadow-b2b [&_.react-pdf__Page_canvas]:h-auto [&_.react-pdf__Page_canvas]:max-w-full">
              <PdfDocument
                file={sourceUrl}
                loading={
                  <p className="text-sm text-[#666666]">Loading PDF…</p>
                }
                error={
                  <p className="text-sm text-[#666666]">
                    Unable to load the PDF document.
                  </p>
                }
                onLoadSuccess={({ numPages }) => setPdfPageCount(numPages)}
              >
                {Array.from(
                  { length: pdfPageCount },
                  (_, index) => index + 1,
                ).map((pageNumber) => (
                  <Page
                    key={pageNumber}
                    pageNumber={pageNumber}
                    renderTextLayer={false}
                    renderAnnotationLayer={false}
                  />
                ))}
              </PdfDocument>
            </div>
          ) : (
            <div className="space-y-4">
              <div
                className="flex flex-wrap gap-2"
                role="tablist"
                aria-label="Workbook sheets"
              >
                {workbookSheets.map((sheet, index) => (
                  <button
                    key={sheet.name}
                    type="button"
                    role="tab"
                    aria-selected={index === activeSheet}
                    className={[
                      "rounded-full border px-3 py-1.5 text-sm font-medium transition",
                      index === activeSheet
                        ? "border-b2b-red bg-b2b-red-soft text-b2b-red"
                        : "border-[#ebebeb] bg-white text-[#666666] hover:bg-[#f2f2f2] hover:text-[#414041]",
                    ].join(" ")}
                    onClick={() => setActiveSheet(index)}
                  >
                    {sheet.name}
                  </button>
                ))}
              </div>

              {loadingWorkbook ? (
                <p className="text-sm text-[#666666]">Loading workbook…</p>
              ) : null}
              {workbookError ? (
                <p className="text-sm text-b2b-red">{workbookError}</p>
              ) : null}

              {activeSheetRows.length > 0 ? (
                <div className="overflow-auto rounded-xl border border-[#ebebeb] bg-white shadow-b2b">
                  <table className="min-w-full border-collapse text-left text-sm">
                    <tbody>
                      {activeSheetRows.map((row, rowIndex) => (
                        <tr key={`${activeSheet}-${rowIndex}`}>
                          {row.map((cell, cellIndex) => (
                            <td
                              key={`${activeSheet}-${rowIndex}-${cellIndex}`}
                              className="border-b border-r border-[#ebebeb] px-3 py-2 text-[#414041]"
                            >
                              {cell === null || cell === undefined
                                ? ""
                                : String(cell)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-sm text-[#666666]">
                  No rows available in this sheet.
                </p>
              )}
            </div>
          )}
        </div>

        {documentType === "pdf" && pdfPageCount > 0 ? (
          <p className="shrink-0 px-6 pt-4 text-center text-xs text-[#888888]">
            {pdfPageCount === 1
              ? "1 page"
              : `${pdfPageCount} pages — scroll to view more`}
          </p>
        ) : null}

        <p className="mt-4 shrink-0 border-t border-[#ebebeb] px-6 py-3 text-center text-xs text-[#888888]">
          Close returns to the results list with the search intact.
        </p>
      </div>
    </div>
  );
}
