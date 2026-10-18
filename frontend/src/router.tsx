import { Navigate, createBrowserRouter } from "react-router-dom";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { CONFIDENTIAL_ENTITLEMENT } from "./config/navigation";
import { AppShell } from "./layouts/AppShell";
import { Login } from "./pages/Login";
import { Unauthorized } from "./pages/Unauthorized";
import { NotFound } from "./pages/NotFound";
import { ArRegistration } from "./pages/ArRegistration";
import { ArRemittances } from "./pages/ArRemittances";
import { SupplierMasterForms } from "./pages/SupplierMasterForms";
import { SupplierInvoicesConfidential } from "./pages/SupplierInvoicesConfidential";
import { SupplierInvoicesExpenses } from "./pages/SupplierInvoicesExpenses";
import { SupplierInvoicesGeneral } from "./pages/SupplierInvoicesGeneral";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <Login />,
  },
  {
    path: "/unauthorized",
    element: <Unauthorized />,
  },
  {
    element: (
      <ProtectedRoute>
        <AppShell />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <Navigate to="/ar-registration" replace />,
      },
      {
        path: "/ar-registration",
        element: <ArRegistration />,
      },
      {
        path: "/ar-remittances",
        element: <ArRemittances />,
      },
      {
        path: "/supplier-master-forms",
        element: <SupplierMasterForms />,
      },
      {
        path: "/supplier-invoices/confidential",
        element: (
          <ProtectedRoute requiredGroup={CONFIDENTIAL_ENTITLEMENT}>
            <SupplierInvoicesConfidential />
          </ProtectedRoute>
        ),
      },
      {
        path: "/supplier-invoices/expenses",
        element: <SupplierInvoicesExpenses />,
      },
      {
        path: "/supplier-invoices/general",
        element: <SupplierInvoicesGeneral />,
      },
    ],
  },
  {
    path: "*",
    element: <NotFound />,
  },
]);
