import { SearchPageTemplate } from "./SearchPageTemplate";

export function ArRegistration() {
  return (
    <SearchPageTemplate
      option="ar-registration"
      title="AR Registration"
      description="Find registration documents by customer number."
      fields={[
        {
          name: "customerNumber",
          label: "Customer Number",
          placeholder: "Enter M3 customer number",
          required: true,
        },
      ]}
      columns={[
        { key: "RESOURCENAME", label: "Document", width: "5rem" },
        { key: "RESOURCECONTENT", label: "Summary", width: "20rem" },
        { key: "LASTCHANGEDUSERID", label: "Changed By", width: "5rem" },
        { key: "RESOURCEID", label: "Document ID", width: "5rem" },
      ]}
    />
  );
}
