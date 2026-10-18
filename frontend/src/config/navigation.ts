/** Entitlement tokens returned by the backend in `CurrentUser.groups`. */
export const GENERAL_ENTITLEMENT = "general";
export const CONFIDENTIAL_ENTITLEMENT = "confidential";

export interface NavigationItem {
  label: string;
  tabLabel: string;
  path: string;
  description: string;
  /** When set, the item is only shown to users holding this entitlement. */
  requiredGroup?: string;
}

export const navigationItems: NavigationItem[] = [
  {
    label: "AR Registration",
    tabLabel: "AR Registration",
    path: "/ar-registration",
    description: "Option 1",
  },
  {
    label: "AR Remittances",
    tabLabel: "AR Remittances",
    path: "/ar-remittances",
    description: "Option 2",
  },
  {
    label: "Supplier Master Forms",
    tabLabel: "Supplier Master Forms",
    path: "/supplier-master-forms",
    description: "Option 3",
  },
  {
    label: "Supplier Invoices Confidential",
    tabLabel: "Invoices",
    path: "/supplier-invoices/confidential",
    description: "Option 4",
    requiredGroup: CONFIDENTIAL_ENTITLEMENT,
  },
  {
    label: "Supplier Invoices Expenses",
    tabLabel: "Invoices (Expenses)",
    path: "/supplier-invoices/expenses",
    description: "Option 5",
  },
  {
    label: "Supplier Invoices General",
    tabLabel: "Invoices (General)",
    path: "/supplier-invoices/general",
    description: "Option 6",
  },
];
