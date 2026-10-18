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
        { key: "M3_Date", label: "M3_Date" },
        { key: "M3_Supplier_Invoice_No", label: "M3_Supplier_Invoice_No" },
        { key: "RESOURCENAME", label: "RESOURCENAME" },
        { key: "RESOURCECONTENT", label: "RESOURCECONTENT" },
        { key: "LASTCHANGEDUSERID", label: "LASTCHANGEDUSERID" },
        { key: "LASTCHANGEDTS", label: "LASTCHANGEDTS" },
        { key: "RESOURCEID", label: "RESOURCEID" },
      ]}
    />
  );
}
