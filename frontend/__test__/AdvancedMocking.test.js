import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { BrowserRouter } from "react-router-dom";
import { configureStore } from "@reduxjs/toolkit";

// Example of mocking a custom hook
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({ pathname: "/test" }),
  };
});

// Example of mocking localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, "localStorage", {
  value: localStorageMock,
});

// Example of mocking window methods
const mockScrollTo = vi.fn();
Object.defineProperty(window, "scrollTo", {
  value: mockScrollTo,
});

// Example component for testing (you can replace this with your actual component)
const TestComponent = () => {
  const handleClick = () => {
    localStorage.setItem("test", "value");
    window.scrollTo(0, 0);
  };

  return (
    <div>
      <button onClick={handleClick}>Test Button</button>
      <input placeholder="Test input" />
    </div>
  );
};

describe("Advanced Mocking Examples", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  it("mocks localStorage interactions", async () => {
    render(<TestComponent />);

    const button = screen.getByRole("button", { name: /test button/i });
    fireEvent.click(button);

    expect(localStorageMock.setItem).toHaveBeenCalledWith("test", "value");
    expect(mockScrollTo).toHaveBeenCalledWith(0, 0);
  });

  it("uses userEvent for more realistic interactions", async () => {
    const user = userEvent.setup();
    render(<TestComponent />);

    const input = screen.getByPlaceholderText(/test input/i);

    await user.type(input, "Hello World");
    expect(input).toHaveValue("Hello World");

    await user.clear(input);
    expect(input).toHaveValue("");
  });

  it("mocks API calls with different responses", async () => {
    // Mock fetch
    const mockFetch = vi.fn();
    global.fetch = mockFetch;

    // First call returns success
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ data: "success" }),
    });

    // Second call returns error
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ error: "Not found" }),
    });

    // Test successful call
    const response1 = await fetch("/api/test");
    const data1 = await response1.json();
    expect(data1).toEqual({ data: "success" });

    // Test error call
    const response2 = await fetch("/api/test");
    const data2 = await response2.json();
    expect(response2.ok).toBe(false);
    expect(data2).toEqual({ error: "Not found" });
  });

  it("mocks timers and async operations", async () => {
    vi.useFakeTimers();

    const callback = vi.fn();

    setTimeout(callback, 1000);

    // Fast-forward time
    vi.advanceTimersByTime(1000);

    expect(callback).toHaveBeenCalledTimes(1);

    vi.useRealTimers();
  });

  it("mocks console methods", () => {
    const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    console.log("test message");

    expect(consoleSpy).toHaveBeenCalledWith("test message");

    consoleSpy.mockRestore();
  });

  it("mocks modules with partial implementations", async () => {
    // Example of mocking a module while keeping some original functionality
    const { default: axios } = await vi.importMock("axios");

    // Mock only specific methods
    vi.mocked(axios.post).mockResolvedValue({ data: { success: true } });

    const result = await axios.post("/test", { data: "test" });
    expect(result.data).toEqual({ success: true });
  });

  it("tests error boundaries and error handling", () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    const ThrowError = () => {
      throw new Error("Test error");
    };

    const ErrorBoundary = ({ children }) => {
      try {
        return children;
      } catch (error) {
        return <div>Something went wrong</div>;
      }
    };

    expect(() => render(<ThrowError />)).toThrow("Test error");

    consoleSpy.mockRestore();
  });

  it("mocks environment variables", () => {
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = "test";

    expect(process.env.NODE_ENV).toBe("test");

    // Restore original value
    process.env.NODE_ENV = originalEnv;
  });

  it("tests component with Redux store", () => {
    const store = configureStore({
      reducer: {
        test: (state = { value: 0 }, action) => {
          switch (action.type) {
            case "INCREMENT":
              return { ...state, value: state.value + 1 };
            default:
              return state;
          }
        },
      },
    });

    const TestReduxComponent = () => {
      const value = 0; // In real component, this would come from useSelector
      return <div>Value: {value}</div>;
    };

    render(
      <Provider store={store}>
        <TestReduxComponent />
      </Provider>
    );

    expect(screen.getByText("Value: 0")).toBeInTheDocument();
  });
});
