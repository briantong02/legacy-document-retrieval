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
        { key: "RESOURCENAME", label: "RESOURCENAME", width: "5rem" },
        { key: "RESOURCECONTENT", label: "RESOURCECONTENT", width: "20rem" },
        { key: "LASTCHANGEDUSERID", label: "LASTCHANGEDUSERID", width: "5rem" },
        { key: "RESOURCEID", label: "RESOURCEID", width: "5rem" },
      ]}
    />
  );
}
