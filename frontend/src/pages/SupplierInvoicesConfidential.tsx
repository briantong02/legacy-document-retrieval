import { SearchPageTemplate } from "./SearchPageTemplate";

export function SupplierInvoicesConfidential() {
  return (
    <SearchPageTemplate
      option="supplier-invoices/confidential"
      title="Supplier Invoices Confidential"
      description="Find confidential supplier invoices by supplier number, then narrow by either M3 date or invoice number."
      fields={[
        {
          name: "supplierNumber",
          label: "Supplier Number",
          placeholder: "Enter M3 supplier number",
          required: true,
          width: "wide",
        },
        {
          name: "fromDate",
          label: "M3 Date",
          type: "date",
          placeholder: "YYYY-MM-DD",
          exclusiveWith: "invoiceNumber",
        },
        {
          name: "invoiceNumber",
          label: "Invoice#",
          placeholder: "Enter M3 supplier invoice number",
          exclusiveWith: "fromDate",
        },
      ]}
      columns={[
        { key: "M3_Date", label: "Invoice Date" },
        { key: "M3_Supplier_Invoice_No", label: "Invoice #" },
        { key: "RESOURCENAME", label: "Document" },
        { key: "RESOURCECONTENT", label: "Summary" },
        { key: "LASTCHANGEDUSERID", label: "Changed By" },
        { key: "LASTCHANGEDTS", label: "Last Changed" },
        { key: "RESOURCEID", label: "Document ID" },
      ]}
    />
  );
}
