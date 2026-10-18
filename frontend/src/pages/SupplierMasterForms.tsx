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
        { key: "RESOURCENAME", label: "RESOURCENAME" },
        { key: "RESOURCECONTENT", label: "RESOURCECONTENT" },
        { key: "LASTCHANGEDUSERID", label: "LASTCHANGEDUSERID" },
        { key: "LASTCHANGEDTS", label: "LASTCHANGEDTS" },
        { key: "RESOURCEID", label: "RESOURCEID" },
      ]}
    />
  );
}
