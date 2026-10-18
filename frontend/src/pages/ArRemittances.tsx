import { SearchPageTemplate } from "./SearchPageTemplate";

export function ArRemittances() {
  return (
    <SearchPageTemplate
      option="ar-remittances"
      title="AR Remittances"
      description="Find remittances by payer number, then narrow by either creation date or document number."
      fields={[
        {
          name: "payerNumber",
          label: "Payer Number",
          placeholder: "Enter M3 payer number",
          required: true,
          width: "wide",
        },
        {
          name: "createdAfter",
          label: "Creation Date",
          type: "date",
          placeholder: "YYYY-MM-DD",
          exclusiveWith: "documentNumber",
        },
        {
          name: "documentNumber",
          label: "Document#",
          placeholder: "Enter M3 document number",
          exclusiveWith: "createdAfter",
        },
      ]}
      columns={[
        { key: "Payment#", label: "Payment #" },
        { key: "CREATETS", label: "Created" },
        { key: "RESOURCENAME", label: "Document" },
        { key: "RESOURCECONTENT", label: "Summary" },
        { key: "LASTCHANGEDUSERID", label: "Changed By" },
        { key: "RESOURCEID", label: "Document ID" },
      ]}
    />
  );
}
