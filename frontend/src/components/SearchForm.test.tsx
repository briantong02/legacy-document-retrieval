import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SearchForm } from "./SearchForm";
import type { SearchField } from "@/types/documents";

// Mirrors the AR Remittances configuration: a mandatory key plus a pair of optional
// filters that may only ever be used one at a time.
const FIELDS: SearchField[] = [
  { name: "payerNumber", label: "Payer Number", required: true, width: "wide" },
  {
    name: "createdAfter",
    label: "Creation Date",
    type: "date",
    exclusiveWith: "documentNumber",
  },
  {
    name: "documentNumber",
    label: "Document#",
    exclusiveWith: "createdAfter",
  },
];

function Harness({ onSubmit = vi.fn() }: { onSubmit?: () => void }) {
  const [values, setValues] = useState<Record<string, string>>({});

  return (
    <SearchForm
      fields={FIELDS}
      values={values}
      onChange={(name, value) =>
        setValues((current) => ({ ...current, [name]: value }))
      }
      onSubmit={onSubmit}
    />
  );
}

const creationDate = () => screen.getByLabelText(/Creation Date/);
const documentNumber = () => screen.getByLabelText(/Document#/);

describe("SearchForm exclusive fields", () => {
  it("leaves both members of the pair enabled until one is used", () => {
    render(<Harness />);

    expect(creationDate()).toBeEnabled();
    expect(documentNumber()).toBeEnabled();
  });

  it("locks the document number once a creation date is entered", async () => {
    render(<Harness />);

    await userEvent.type(creationDate(), "2025-06-02");

    expect(documentNumber()).toBeDisabled();
    expect(creationDate()).toBeEnabled();
    expect(screen.getByText("Clear Creation Date to use this field.")).toBeInTheDocument();
  });

  it("locks the creation date once a document number is entered", async () => {
    render(<Harness />);

    await userEvent.type(documentNumber(), "123456");

    expect(creationDate()).toBeDisabled();
    expect(documentNumber()).toBeEnabled();
    expect(screen.getByText("Clear Document# to use this field.")).toBeInTheDocument();
  });

  it("unlocks the partner again when the field is cleared", async () => {
    render(<Harness />);

    await userEvent.type(documentNumber(), "123456");
    expect(creationDate()).toBeDisabled();

    await userEvent.clear(documentNumber());

    expect(creationDate()).toBeEnabled();
    expect(documentNumber()).toBeEnabled();
  });

  it("does not lock a field that has no exclusive partner", async () => {
    render(<Harness />);

    await userEvent.type(documentNumber(), "123456");

    expect(screen.getByLabelText(/Payer Number/)).toBeEnabled();
  });
});
