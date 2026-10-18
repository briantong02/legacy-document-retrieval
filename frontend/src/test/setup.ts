import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// vitest runs without `globals`, so Testing Library's automatic cleanup never registers.
// Without this the previous test's DOM stays mounted and `screen` queries match it.
afterEach(cleanup);
