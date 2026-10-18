# DUX MANUFACTURING

## Legacy Document Retrieval — Application Specification

| Field          | Value                                                 |
| -------------- | ----------------------------------------------------- |
| **Document**   | Legacy Document Retrieval — Application Specification |
| **Version**    | 2.0 (rewrite)                                         |
| **Date**       | 16 July 2026                                          |
| **Status**     | Draft — open questions at Section 9                   |
| **Supersedes** | `Dux_Legacy_Document_Retrieval_Specifications.docx`   |

---

## 1. Purpose

Provide a web application allowing users to locate and view legacy documents held in the Infor IDM file store, by querying IDM metadata with familiar M3 business keys (customer, payer, and supplier numbers) and rendering or downloading the underlying PDF or XLSX.

## 2. Scope

Two deliverables:

- **Indexing utility:** A repeatable job that catalogues the physical document files on the file server into a SQL table.
- **Retrieval application:** A Python and React.js application with six document-type options, each following a common search → select → view/download flow, gated by Active Directory group membership.

## 3. Environment

| Item                  | Development                              | Production                              |
| --------------------- | ---------------------------------------- | --------------------------------------- |
| **Application host**  | Local (macOS)                            | `APPHOST01`                            |
| **Database server**   | `SQLHOST01`                             | `SQLHOST01`                            |
| **DB authentication** | SQL authentication (username + password) | Windows authentication (integrated)     |
| **File server**       | `FILEHOST01` (SMB mount)                  | `FILEHOST01`                             |
| **Document root**     | `/Volumes/IDMFiles/infor/infor`          | Server-visible path — _see Section 9.2_ |
| **Index database**    | `DUX_DocMgmt`                            | `DUX_DocMgmt`                           |
| **Metadata database** | `Infor_duxprod_DocMgmt` (schema `idm`)   | `Infor_duxprod_DocMgmt` (schema `idm`)  |
| **Front end**         | React.js                                 | React.js                                |
| **Back end**          | Python                                   | Python                                  |

### 3.1 Configuration

Connection method and document root differ per environment and must be configuration-driven, not hard-coded. Minimum configuration keys:

- `DB_SERVER`, `DB_AUTH_MODE` (sql | windows), `DB_USER`, `DB_PASSWORD`
- `DOC_ROOT_CANONICAL` — always `e:\DATA1\IT\IDMFiles\infor\infor`. This is the form stored in the database.
- `DOC_ROOT_LOCAL` — `/Volumes/IDMFiles/infor/infor` in development; the server-visible path on `APPHOST01` in production.

Development SQL credentials are held in an untracked `.env` file or local secret store and are never committed to source control. Production uses the `APPHOST01` service account identity via integrated Windows authentication; no credentials are stored in the application.

### 3.2 Path translation

`DocumentPath` is stored in canonical Windows form in all environments. At read time the application substitutes `DOC_ROOT_CANONICAL` with `DOC_ROOT_LOCAL` and normalises separators.

The two roots differ in depth, not merely in separator style. The SMB share `IDMFiles` is published from `e:\DATA1\IT\IDMFiles`, so the `\DATA1\IT` segment does not exist on the macOS side:

```text
macOS    /Volumes/IDMFiles               /infor/infor /9429 /0000540b-cfc3-...
Windows  e:\DATA1\IT\IDMFiles            \infor\infor \9429 \0000540b-cfc3-...
                    └──── share root ────┘

```

Translation is therefore a root substitution, not a drive-letter prefix. Both roots must be configuration values rather than derived from one another. This keeps the index portable between the development machine and `APPHOST01`, and means the indexer can be run from either host without rewriting rows.

---

## 4. Component 1 — Document Index

### 4.1 Database

Create database `DUX_DocMgmt` on `SQLHOST01`.

### 4.2 Table

Create `DUX_DocMgmt.dbo.Document`:

| Column         | Type            | Nullable | Key         |
| -------------- | --------------- | -------- | ----------- |
| `ResourceId`   | `nvarchar(64)`  | NOT NULL | Primary key |
| `DocumentPath` | `nvarchar(256)` | NULL     | —           |

### 4.3 Population

The utility recursively scans every folder beneath `DOC_ROOT_LOCAL` and writes one row per file:

- **`ResourceId`** — the file name: a GUID with no extension, e.g. `0000540b-cfc3-4cd9-922b-63cad9aab03a`. This matches the `RESOURCEID` value returned by the IDM metadata queries and is the join key between the two databases.
- **`DocumentPath`** — the full canonical Windows path to the file, from the drive letter through to the resource id:
- `e:\DATA1\IT\IDMFiles\infor\infor\{subfolders}\{ResourceId}`
- _e.g._ `e:\DATA1\IT\IDMFiles\infor\infor\9429\0000540b-cfc3-4cd9-922b-63cad9aab03a`

Regardless of which host runs the scan, `DOC_ROOT_LOCAL` is replaced with `DOC_ROOT_CANONICAL` and separators are converted, so the stored value is identical either way.

The archive is static, so this is a one-off load. The script must nonetheless remain re-runnable and idempotent — upsert on `ResourceId` rather than blind insert — so it can be repeated safely if it fails partway through or if the store is ever touched again. No schedule is required.

---

## 5. Component 2 — Retrieval Application

### 5.1 Navigation

A persistent menu bar across the top of every screen exposes the six options the signed-in user is entitled to. There is no separate back-to-menu button; the bar is always available. Options the user is not entitled to are not rendered.

| #   | Menu option                            |
| --- | -------------------------------------- |
| 1   | IDM — AR Registration                  |
| 2   | IDM — AR Remittances                   |
| 3   | IDM — Supplier Master Forms            |
| 4   | IDM — Supplier Invoices (Confidential) |
| 5   | IDM — Supplier Invoices (Expenses)     |
| 6   | IDM — Supplier Invoices (General)      |

### 5.2 Authorisation

Two Active Directory security groups control access:

| Group            | Grants options   |
| ---------------- | ---------------- |
| **General**      | 1, 2, 3, 5, 6    |
| **Confidential** | 1, 2, 3, 4, 5, 6 |

The groups are `#IDM-GENERAL` and `#IDM-CONFIDENTIAL` — see Section 9.4 on the leading `#`.

_Confidential_ is a superset of _General_; option 4 is the only gated option. Users in neither group have no access to the application.

Entitlement is enforced server-side on every request, not merely by hiding menu items. A direct request to an option or document the user is not entitled to returns an authorisation error and is logged.

Entitlement is checked against the **document**, not only against the option named in the request. The option in a view or download URL is supplied by the caller, so checking the entitlement for that option alone would leave it unverified: a user entitled to a General option could name it while passing a Confidential document's `RESOURCEID` and be served the file, because the resource id on its own is enough to resolve a path. Each option draws from exactly one IDM view, so the document is confirmed to belong to the requested option before it is served, and a mismatch is refused as not found rather than forbidden — whether an id exists under some other option is not the caller's business.

### 5.3 Common flow

Every option follows the same sequence. Only the inputs, source table, and result columns differ.

1. **Search screen** — display the option's input field(s). Each option has one mandatory key; optional date fields filter further when supplied.
2. **Execute query** against `Infor_duxprod_DocMgmt.idm.<table>` using bound parameters.

- _No rows_ → display an appropriate message naming the search key used; remain on the search screen.
- _Rows_ → display a results list. The columns are those returned by the option's `SELECT` — the query's column list is the grid. Each row carries two actions: View and Download.

3. **User clicks View** (opens the overlay viewer) **or Download** (saves the file directly, named `RESOURCENAME`, without opening the viewer).
4. **Resolve the file** — take `RESOURCEID` from the selected row, look it up as the primary key of `DUX_DocMgmt.dbo.Document`, and translate `DocumentPath` to the environment-local path per Section 3.2. `DocumentPath` already resolves to the file; no further concatenation is required to locate it.
5. **Determine type and name** — the physical file is stored as a bare GUID with no extension, so the extension is taken from `RESOURCENAME` (e.g. `Dux credit application copy.pdf` → `pdf`). This drives the viewer choice (PDF or XLSX), the content type served, and the download file name, which is `RESOURCENAME` verbatim so the user receives a correctly named, openable file.
6. **View** — the document opens in an overlay viewer, rendered in full and scrollable through all pages. The menu bar remains visible.
7. **Close viewer** → return to the results list with the previous search intact.

### 5.4 Option 1 — AR Registration

**Input:** M3 Customer Number (mandatory).

```sql
SELECT [RESOURCENAME], [RESOURCECONTENT], [LASTCHANGEDUSERID], [RESOURCEID]
FROM [Infor_duxprod_DocMgmt].[idm].[DUX_AR_Registrations]
WHERE [M3_CUNO] = @CustomerNo;

```

> **Worked example:** For `@CustomerNo = 'H14824'`, a returned row with `RESOURCEID` `0000540b-cfc3-4cd9-922b-63cad9aab03a` resolves to:
> `e:\DATA1\IT\IDMFiles\infor\infor\9429\0000540b-cfc3-4cd9-922b-63cad9aab03a`

### 5.5 Option 2 — AR Remittances

**Inputs:** M3 Payer# (mandatory), then **either** Creation Date **or** Document# (`M3_CINO`) — never both.

```sql
SELECT [M3_CINO] AS [Payment#], [CREATETS], [RESOURCENAME],
       [RESOURCECONTENT], [LASTCHANGEDUSERID], [RESOURCEID]
FROM [Infor_duxprod_DocMgmt].[idm].[DUX_AR_Remittances]
WHERE [M3_PYNO] = @PayerNo
       AND (@CreatedAfter IS NULL OR [CREATETS] > @CreatedAfter)
       AND (@DocumentNo IS NULL OR [M3_CINO] = @DocumentNo)
ORDER BY [CREATETS];

```

> Creation Date is a standard date (yyyy-mm-dd) and must be validated before use. Example: `@PayerNo = 'H14824'`, `@CreatedAfter = '2025-06-02'`.
>
> Document# matches `M3_CINO` exactly. See Section 5.8 for the mutual-exclusion rule.

### 5.6 Option 3 — Supplier Master Forms

**Input:** M3 Supplier# (mandatory).

```sql
SELECT [RESOURCENAME], [RESOURCECONTENT], [LASTCHANGEDUSERID],
       [LASTCHANGEDTS], [RESOURCEID]
FROM [Infor_duxprod_DocMgmt].[idm].[DUX_Supplier_Master_Forms]
WHERE [M3_Supplier_Number] = @SupplierNo;

```

### 5.7 Options 4–6 — Supplier Invoices

Identical behaviour, differing only in source table and entitlement:

| Option               | Table                            | Requires                |
| -------------------- | -------------------------------- | ----------------------- |
| **4 — Confidential** | `[idm].[DuxSupplierInvoice_Con]` | Confidential group      |
| **5 — Expenses**     | `[idm].[DuxSupplierInvoice_Exp]` | General or Confidential |
| **6 — General**      | `[idm].[DuxSupplierInvoice_Gen]` | General or Confidential |

**Inputs:** M3 Supplier# (mandatory), then **either** M3 Date **or** Invoice# (`M3_Supplier_Invoice_No`) — never both.

M3 Date is supplied by a date picker as a standard date (yyyy-mm-dd). `M3_Date` is *stored* as a ddmmyy string, so both filtering and sorting require converting the stored column to a real date; the supplied value is compared directly and is never rebuilt from string fragments.

Invoice# matches `M3_Supplier_Invoice_No` exactly. See Section 5.8 for the mutual-exclusion rule.

```sql
SELECT [M3_Date], [M3_Supplier_Invoice_No], [RESOURCENAME],
       [RESOURCECONTENT], [LASTCHANGEDUSERID], [LASTCHANGEDTS], [RESOURCEID]
FROM [Infor_duxprod_DocMgmt].[idm].[<table>]
WHERE [M3_Supplier_Number] = @SupplierNo
       AND (@InvoiceNo IS NULL OR [M3_Supplier_Invoice_No] = @InvoiceNo)
       AND (@FromDate IS NULL
            OR CONVERT(date, CONCAT('20', RIGHT(TRIM([M3_Date]), 2), '-',
                                    SUBSTRING(TRIM([M3_Date]), 3, 2), '-',
                                    LEFT(TRIM([M3_Date]), 2)))
                >= CONVERT(date, CONCAT('20', RIGHT(@FromDate, 2), '-',
                                        SUBSTRING(@FromDate, 3, 2), '-',
                                        LEFT(@FromDate, 2))))
ORDER BY CONVERT(date, CONCAT('20', RIGHT(TRIM([M3_Date]), 2), '-',
                              SUBSTRING(TRIM([M3_Date]), 3, 2), '-',
                              LEFT(TRIM([M3_Date]), 2)));

```

> When M3 Date is supplied it must be validated before the query runs. See Section 9.3 regarding the hard-coded century used on the *stored* column.

### 5.8 Mutually exclusive filters

On options 2 and 4 to 6 the mandatory key may be narrowed by a date **or** by a document
number, but never by both at once. A number already identifies a single document, so adding
a date to it only produces confusing empty results.

The rule is enforced twice:

- **In the form** — entering a value in one of the pair disables and greys out the other, with
  a note naming the field to clear. A disabled input cannot be typed into, so the invalid
  combination is unreachable and no error state is needed.
- **In the API** — the request is rejected with a validation error naming both fields. The
  browser is not a security boundary and the endpoints are directly callable.

---

## 6. Error handling

| Condition                                      | Behaviour                                                                                           |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| **No rows returned**                           | Message naming the search key used; remain on the search screen.                                    |
| **`RESOURCEID` not present in `dbo.Document**` | "Document not indexed" message; indicates the index may need a refresh.                             |
| **File missing at the resolved path**          | "File cannot be located" message.                                                                   |
| **Document root unreachable**                  | Distinct message — this is an environment fault (mount down / share unavailable), not a data fault. |
| **Unsupported extension in `RESOURCENAME**`    | Offer download only, with a message that inline viewing is not available for that type.             |
| **Invalid or malformed date input**            | Inline validation message; the query is not executed.                                               |
| **Date and document number both supplied**     | Rejected with a validation error naming both fields; the query is not executed. Unreachable from the form — see Section 5.8. |
| **Unauthorised option or document access**     | Authorisation error; logged.                                                                        |

---

## 7. Non-functional requirements

- All user input is passed as bound parameters. No string concatenation into SQL.
- No credentials in source control. Development SQL credentials live in local secrets; production uses integrated Windows authentication under the `APPHOST01` service account.
- Document access is read-only throughout. The application never writes to the file store.
- Access to Confidential documents is logged: user, resource id, timestamp, and action (view or download).

---

## 8. Resolved design decisions

_Recorded here so the reasoning is not lost. These were open in the previous revision and are now closed._

| Item                       | Resolution                                                                                                                                                             |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Two database names**     | Confirmed: metadata is read from `Infor_duxprod_DocMgmt`; physical paths are resolved from `DUX_DocMgmt`.                                                              |
| **Nullable primary key**   | `ResourceId` is `NOT NULL` and is the primary key of `dbo.Document`.                                                                                                   |
| **Duplicate resource ids** | Resource ids are GUIDs, so uniqueness across the tree is guaranteed. `ResourceId` as PK is safe.                                                                       |
| **Extension on disk**      | Files are stored as bare GUIDs with no extension. `DocumentPath` alone locates the file; `RESOURCENAME` supplies the extension for viewer type and download name only. |
| **Results grid columns**   | The columns returned by each option's `SELECT` are the grid.                                                                                                           |
| **Index refresh**          | One-off load; the archive is static. The script remains idempotent for safe re-runs.                                                                                   |
| **Back button**            | Removed. The persistent top menu bar replaces it. The viewer is an overlay with a close action returning to the results list.                                          |
| **Page count**             | The original "all 9 pages" requirement was specific to one worked example. Generalised to: all pages, scrollable.                                                      |

---

## 9. Open questions

_These require confirmation before build. Each notes why it matters, so it can be answered without re-deriving the context._

### 9.1 `RESOURCECONTENT` — keep or drop?

`RESOURCECONTENT` is selected in every query in the original specification, but it is never used: documents are retrieved from disk via `DocumentPath`, not from this column. It appears to hold the document's extracted text and is bulky.

- **Why it matters:** pulling a large text column on every search costs performance for no benefit. If it is not needed in the results grid, it should be dropped from the `SELECT` lists in Sections 5.4 to 5.7.

### 9.2 `APPHOST01` access to `FILEHOST01`

Access is to be granted in the same manner as a standard AD user account. The specific mechanism must be confirmed with whoever provisions it.

- **Why it matters:** the application runs under a service identity, not an interactive login, and mapped drive letters do not reliably exist for service accounts. A UNC path (`\\FILEHOST01\IDMFiles\infor\infor`) is the safer provisioning request. Whichever is chosen becomes the production value of `DOC_ROOT_LOCAL` in Section 3.1.

### 9.3 Hard-coded century in `M3_Date` conversion

The date conversion in Section 5.7 uses the literal '20' in `CONCAT('20', RIGHT(TRIM([M3_Date]), 2), ...)`, prepending "20" to the two-digit year.

- **Why it matters:** a value of `010199` is read as 1 January 2099, not 1999. This is acceptable if no invoice in the archive predates the year 2000 — worth confirming, given this is a legacy archive.

### 9.4 Active Directory settings

**Resolved. Sign-in works against the live directory.**

The objects are named with a **leading `#`**, which is part of the name rather than notation: `#IDM-GENERAL`, `#IDM-CONFIDENTIAL`, and the service account `#IDM-SRVC`. The `#` is present in both the CN and the `sAMAccountName` — the service account's DN reads `CN=\#IDM-SRVC,OU=Example-OU,...`, the backslash being DN escaping for a leading `#`. Omitting it was the cause of a long-misdiagnosed failure: the group lookup silently matched nothing, and a bind to `CORP\DUX-IDM-SRVC` was rejected as `invalidCredentials`, which Active Directory returns for a nonexistent account and a wrong password alike.

**CA certificate — retrieved from the directory.** The DCs present only a leaf certificate from the internal CA `corp-issuing-CA`, and the CA is not in the macOS keychain, but the leaf's Authority Information Access extension publishes the CA inside the directory itself, at `CN=corp-issuing-CA,CN=AIA,CN=Public Key Services,CN=Services,CN=Configuration,<base DN>`. Reading that attribute needs an authenticated bind but nothing more, so `backend/scripts/fetch_ca_cert.py` fetches it and writes `backend/certs/corp-ca.pem`. The CA is valid until 31 July 2030; the DC leaf certificates renew annually beneath it, so pinning the CA rather than a leaf is what keeps sign-in working across those renewals.

**Service account — optional, not required.** Ordinary accounts in this directory can read group membership, so `_resolve_groups` reads over the signing-in user's own connection and only falls back to `#IDM-SRVC` when that returns empty. The service account has been verified able to read another user's membership, so the fallback works if it is ever needed.

**Remaining action:** membership. Group members are provisioned by IT, so a user not yet added is refused with a 403 after their password has been accepted — which is correct behaviour, not a fault. `backend/scripts/check_ad_login.py` reports which of the possible causes applies for a given account.

- **Why it mattered:** `LDAP_USE_SSL` fails closed without `LDAP_CA_CERT_FILE`, because a simple bind puts the user's password on the wire and an unvalidated server must not receive it. Until the CA was in place, real sign-in returned 500 and `AUTH_BYPASS_ENABLED` was left on to compensate. It is now off, and a startup guard refuses to boot with it on in production.

### 9.5 Path casing

This specification stores paths as `e:\DATA1\IT\IDMFiles\infor\infor`, taken from the supplied worked example. Note the original specification used a different casing (`e:\data1\IT\IDMFILES\INFOR\INFOR`).

- **Why it matters:** Windows treats paths case-insensitively, but string comparison in the application does not, and macOS volumes may be case-sensitive depending on how they are formatted. The root substitution in Section 3.2 is a string operation, so a casing mismatch between the stored value and `DOC_ROOT_CANONICAL` will cause resolution to fail. Confirm one casing and store it consistently, or make the comparison case-insensitive.
