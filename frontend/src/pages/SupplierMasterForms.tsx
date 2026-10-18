import { SearchPageTemplate } from "./SearchPageTemplate";

export function SupplierMasterForms() {
  return (
    <SearchPageTemplate
      option="supplier-master-forms"
      title="Supplier Master Forms"
      description="Find supplier master forms by supplier number."
      fields={[
        {
          name: "supplierNumber",
          label: "Supplier Number",
          placeholder: "Enter M3 supplier number",
          required: true,
        },
      ]}
      columns={[
        { key: "RESOURCENAME", label: "Document" },
        { key: "RESOURCECONTENT", label: "Summary" },
        { key: "LASTCHANGEDUSERID", label: "Changed By" },
        { key: "LASTCHANGEDTS", label: "Last Changed" },
        { key: "RESOURCEID", label: "Document ID" },
      ]}
    />
  );
}
