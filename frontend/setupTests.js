// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import "@testing-library/jest-dom";

  // Vitest-specific setup
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Check if we're in a Vitest environment
const isVitest = typeof vi !== "undefined";

if (isVitest) {

  // Cleanup after each test case (for React Testing Library)
  afterEach(() => {
    cleanup();
  });
}

// Mock for window.matchMedia (commonly needed for tests)
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value:
    isVitest && typeof vi !== "undefined"
      ? vi.fn().mockImplementation((query) => ({
          matches: false,
          media: query,
          onchange: null,
          addListener: vi.fn(), // deprecated
          removeListener: vi.fn(), // deprecated
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
          dispatchEvent: vi.fn(),
        }))
      : typeof jest !== "undefined"
      ? jest.fn().mockImplementation((query) => ({
          matches: false,
          media: query,
          onchange: null,
          addListener: jest.fn(), // deprecated
          removeListener: jest.fn(), // deprecated
          addEventListener: jest.fn(),
          removeEventListener: jest.fn(),
          dispatchEvent: jest.fn(),
        }))
      : () => ({
          matches: false,
          media: "",
          onchange: null,
          addListener: () => {},
          removeListener: () => {},
          addEventListener: () => {},
          removeEventListener: () => {},
          dispatchEvent: () => {},
        }),
});
