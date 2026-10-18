import { Button } from "@/components/ui/Button";
import type { SearchField } from "@/types/documents";

interface SearchFormProps {
  fields: SearchField[];
  values: Record<string, string>;
  onChange: (name: string, value: string) => void;
  onSubmit: () => void;
  submitLabel?: string;
  isLoading?: boolean;
}

const CONTROL_CLASS =
  "min-h-11 w-full rounded-md border border-[#ebebeb] px-3.5 py-2 font-display text-[13px] font-medium shadow-b2b transition focus:outline-none focus:ring-2 focus:ring-b2b-red/30";
const LOCKED_CLASS = "bg-[#f2f2f2] text-[#888888] cursor-not-allowed";

export function SearchForm({
  fields,
  values,
  onChange,
  onSubmit,
  submitLabel = "Search",
  isLoading,
}: SearchFormProps) {
  const fieldsByName = new Map(fields.map((field) => [field.name, field]));

  return (
    <form
      className="space-y-5"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className="grid grid-cols-12 gap-4">
        {fields.map((field) => {
          const widthClass =
            field.width === "wide" ? "col-span-12" : "col-span-12 md:col-span-6";

          // A field with an exclusive partner locks while that partner holds a value. A
          // locked input cannot be typed into, so the two can never both be filled and no
          // error state is reachable - clearing the partner unlocks this one again.
          const partner = field.exclusiveWith
            ? fieldsByName.get(field.exclusiveWith)
            : undefined;
          const isLocked = Boolean(
            field.exclusiveWith && values[field.exclusiveWith]?.trim(),
          );

          return (
            // The cell is a div rather than a label so that the lock hint below does not
            // become part of the input's accessible name. The label is associated
            // explicitly through htmlFor/id instead.
            <div key={field.name} className={widthClass}>
              <label
                className="mb-1 block text-sm font-bold text-[#666666]"
                htmlFor={field.name}
              >
                {field.label}
                {field.required ? (
                  <span className="font-normal text-[#888888]"> (Required)</span>
                ) : null}
              </label>
              {field.type === "select" ? (
                <select
                  className={`${CONTROL_CLASS} ${isLocked ? LOCKED_CLASS : "bg-[#f2f2f2] text-[#414041]"}`}
                  id={field.name}
                  required={field.required}
                  disabled={isLocked}
                  value={values[field.name] ?? ""}
                  onChange={(event) => onChange(field.name, event.target.value)}
                >
                  <option value="">Select an option</option>
                  {field.options?.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  className={`${CONTROL_CLASS} placeholder:text-[#aaaaaa] ${isLocked ? LOCKED_CLASS : "bg-white text-[#414041]"}`}
                  id={field.name}
                  type={field.type ?? "text"}
                  pattern={field.pattern}
                  required={field.required}
                  disabled={isLocked}
                  title={field.title}
                  placeholder={field.placeholder}
                  value={values[field.name] ?? ""}
                  onChange={(event) => onChange(field.name, event.target.value)}
                />
              )}
              {isLocked && partner ? (
                <p className="mt-1 text-xs text-[#888888]">
                  Clear {partner.label} to use this field.
                </p>
              ) : null}
            </div>
          );
        })}
      </div>

      <div className="flex justify-center">
        <Button type="submit" className="w-48" disabled={isLoading}>
          {isLoading ? "Searching..." : submitLabel}
        </Button>
      </div>
    </form>
  );
}
