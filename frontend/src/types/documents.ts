export type DocumentOptionKey =
  | "ar-registration"
  | "ar-remittances"
  | "supplier-master-forms"
  | "supplier-invoices/confidential"
  | "supplier-invoices/expenses"
  | "supplier-invoices/general";

export type DocumentResultRow = Record<
  string,
  string | number | boolean | null | undefined
>;

export interface SearchFieldOption {
  label: string;
  value: string;
}

export type SearchFieldType = "text" | "date" | "number" | "select";

export interface SearchField {
  name: string;
  label: string;
  type?: SearchFieldType;
  placeholder?: string;
  options?: SearchFieldOption[];
  width?: "normal" | "wide";
  required?: boolean;
  pattern?: string;
  title?: string;
  /**
   * Name of the field this one cannot be combined with. Declare it on both members of the
   * pair: each locks while the other holds a value, so only ever one of them is filled in.
   */
  exclusiveWith?: string;
}

export interface ResultsColumn {
  key: string;
  label: string;
  width?: string;
  render?: (
    row: DocumentResultRow,
  ) => string | number | boolean | null | undefined;
}

export interface CurrentUser {
  username: string;
  displayName: string;
  email: string | null;
  groups: string[];
}
