import type { ReactNode } from "react";
import { Card } from "@/components/ui/Card";
import { DownloadIcon, EyeIcon } from "@/components/icons";
import type { DocumentResultRow, ResultsColumn } from "@/types/documents";

const actionButtonClass =
  "inline-flex min-h-[30px] items-center gap-1.5 whitespace-nowrap rounded-md border border-[#ebebeb] bg-white px-2.5 py-1 text-xs font-semibold text-[#414041] transition hover:bg-[#f2f2f2] focus:outline-none focus-visible:ring-2 focus-visible:ring-b2b-red/30";

interface ResultsGridProps {
  rows: DocumentResultRow[];
  columns: ResultsColumn[];
  onView?: (row: DocumentResultRow) => void;
  onDownload?: (row: DocumentResultRow) => void;
  canView?: (row: DocumentResultRow) => boolean;
  canDownload?: (row: DocumentResultRow) => boolean;
  emptyMessage?: string;
}

function renderCellValue(value: unknown): ReactNode {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  return String(value);
}

function isContentHeavyColumn(columnKey: string): boolean {
  return columnKey.toUpperCase() === "RESOURCECONTENT";
}

function getCellContainerClass(columnKey: string): string {
  if (isContentHeavyColumn(columnKey)) {
    return "max-h-28 max-w-[30rem] overflow-auto whitespace-pre-wrap break-all pr-1 leading-relaxed";
  }

  return "whitespace-normal break-words";
}

export function ResultsGrid({
  rows,
  columns,
  onView,
  onDownload,
  canView,
  canDownload,
  emptyMessage = "No results yet.",
}: ResultsGridProps) {
  const hasActions = Boolean(onView || onDownload);

  return (
    <Card padding="none" className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse text-left text-sm">
          <thead className="bg-white text-xs uppercase tracking-[0.08em] text-b2b-red">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  className="border-b border-[#ebebeb] px-4 py-3 text-center font-bold"
                  style={column.width ? { width: column.width } : undefined}
                >
                  {column.label}
                </th>
              ))}
              {hasActions ? (
                <th
                  className="border-b border-[#ebebeb] px-4 py-3 text-right font-bold"
                  style={{ width: "12rem" }}
                >
                  Actions
                </th>
              ) : null}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td
                  className="px-4 py-10 text-center text-sm text-[#888888]"
                  colSpan={columns.length + (hasActions ? 1 : 0)}
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr
                  key={String(
                    row.RESOURCEID ?? row.resourceId ?? JSON.stringify(row),
                  )}
                  className="border-b border-[#ebebeb] hover:bg-[#f8f8f8]"
                >
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className="px-4 py-3 align-top text-[#414041]"
                    >
                      <div className={getCellContainerClass(column.key)}>
                        {renderCellValue(
                          column.render ? column.render(row) : row[column.key],
                        )}
                      </div>
                    </td>
                  ))}
                  {hasActions ? (
                    <td className="px-4 py-3 align-top">
                      <div className="flex flex-nowrap justify-end gap-1.5">
                        {onView && (canView ? canView(row) : true) ? (
                          <button
                            type="button"
                            className={actionButtonClass}
                            onClick={() => onView(row)}
                          >
                            <EyeIcon className="h-3.5 w-3.5 text-[#555555]" />
                            View
                          </button>
                        ) : null}
                        {onDownload &&
                        (canDownload ? canDownload(row) : true) ? (
                          <button
                            type="button"
                            className={actionButtonClass}
                            onClick={() => onDownload(row)}
                          >
                            <DownloadIcon className="h-3.5 w-3.5 text-[#555555]" />
                            Download
                          </button>
                        ) : null}
                      </div>
                      {onView && canView && !canView(row) ? (
                        <p className="mt-2 text-right text-xs text-[#888888]">
                          Inline viewing is not available for this type
                        </p>
                      ) : null}
                    </td>
                  ) : null}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
