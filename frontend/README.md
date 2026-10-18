# DUX Vault Frontend

React + TypeScript frontend for the DUX Vault legacy document retrieval app.

## Setup

1. Copy `.env.example` to `.env.development`.
2. Set your backend URL.
3. Install dependencies with `npm install`.
4. Start the dev server with `npm run dev`.

## Scripts

- `npm run dev` - start the Vite development server.
- `npm run build` - typecheck and build production assets.
- `npm run preview` - preview the production build locally.
- `npm run lint` - run ESLint across the frontend.
- `npm run test` - run the Vitest suite.

## Notes

- API requests use the backend origin from `VITE_BACKEND_URL` directly (no Vite proxy).
- Authentication is backend-owned; the frontend calls `/api/auth/*` endpoints and does not manage Entra/MSAL directly.
- Styling is Tailwind-first (`@tailwindcss/vite` + `tailwindcss`), with utility classes in components.
- The six document pages share one search template plus reusable results-grid and viewer components, so each page stays a small declaration of its fields and columns.
