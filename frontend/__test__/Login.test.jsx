import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import LoginComponent from "../src/subcomponents/login/LoginComponent.jsx";

// Create mock function using vi.hoisted
const { mockLogin } = vi.hoisted(() => ({
  mockLogin: vi.fn(),
}));

// Mock the UserSlice module
vi.mock("../src/redux/UserSlice", () => ({
  login: mockLogin,
}));

// Mock localStorage
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, "localStorage", {
  value: mockLocalStorage,
});

// Mock window.location.reload
Object.defineProperty(window, "location", {
  value: {
    reload: vi.fn(),
  },
  writable: true,
});

// Create test store
const createTestStore = () =>
  configureStore({
    reducer: {
      user: (state = { isAuthenticated: false, user: null }, action) => state,
    },
  });

// Helper to render with providers and required props
const renderWithProviders = (component, store = createTestStore()) => {
  return render(<Provider store={store}>{component}</Provider>);
};

// Helper to create mock props
const createMockProps = () => ({
  setPageState: vi.fn(),
  setStatusMessage: vi.fn(),
  statusMessage: "",
});

describe("LoginComponent", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Setup default mock return value
    mockLogin.mockReturnValue({
      type: "user/login/pending",
      then: vi.fn((callback) => {
        // Simulate successful response
        const mockResponse = {
          payload: { status: "OK", token: "mock-token" },
        };
        callback(mockResponse);
        return Promise.resolve(mockResponse);
      }),
    });
  });

  it("renders login form correctly", () => {
    const mockProps = createMockProps();
    renderWithProviders(<LoginComponent {...mockProps} />);

    // Check if login form elements are present
    expect(screen.getByPlaceholderText("Enter Email")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Enter Password")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Continue" })
    ).toBeInTheDocument();
    expect(screen.getByText("Log In")).toBeInTheDocument();
    expect(screen.getByText("Forgot Password?")).toBeInTheDocument();
    expect(screen.getByText("Sign Up")).toBeInTheDocument();
  });

  it("displays validation errors for empty fields", async () => {
    const mockProps = createMockProps();
    renderWithProviders(<LoginComponent {...mockProps} />);

    const submitButton = screen.getByRole("button", { name: "Continue" });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockProps.setStatusMessage).toHaveBeenCalledWith(
        "Must enter an email address"
      );
    });
  });

  it("handles email input changes", () => {
    const mockProps = createMockProps();
    renderWithProviders(<LoginComponent {...mockProps} />);

    const emailInput = screen.getByPlaceholderText("Enter Email");
    fireEvent.change(emailInput, { target: { value: "test@example.com" } });

    expect(emailInput.value).toBe("test@example.com");
  });

  it("handles password input changes", () => {
    const mockProps = createMockProps();
    renderWithProviders(<LoginComponent {...mockProps} />);

    const passwordInput = screen.getByPlaceholderText("Enter Password");
    fireEvent.change(passwordInput, { target: { value: "password123" } });

    expect(passwordInput.value).toBe("password123");
  });

  it("submits form with valid credentials", async () => {
    const mockProps = createMockProps();
    renderWithProviders(<LoginComponent {...mockProps} />);

    const emailInput = screen.getByPlaceholderText("Enter Email");
    const passwordInput = screen.getByPlaceholderText("Enter Password");
    const submitButton = screen.getByRole("button", { name: "Continue" });

    fireEvent.change(emailInput, { target: { value: "test@example.com" } });
    fireEvent.change(passwordInput, { target: { value: "password123" } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        email: "test@example.com",
        password: "password123",
      });
    });

    expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
      "sessionToken",
      "mock-token"
    );
    expect(window.location.reload).toHaveBeenCalled();
  });

  it("displays error message on login failure", async () => {
    // Mock login to return error
    mockLogin.mockReturnValueOnce({
      type: "user/login/pending",
      then: vi.fn((callback) => {
        const mockResponse = {
          payload: { status: "Invalid credentials" },
        };
        callback(mockResponse);
        return Promise.resolve(mockResponse);
      }),
    });

    const mockProps = createMockProps();
    renderWithProviders(<LoginComponent {...mockProps} />);

    const emailInput = screen.getByPlaceholderText("Enter Email");
    const passwordInput = screen.getByPlaceholderText("Enter Password");
    const submitButton = screen.getByRole("button", { name: "Continue" });

    fireEvent.change(emailInput, { target: { value: "test@example.com" } });
    fireEvent.change(passwordInput, { target: { value: "wrongpassword" } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockProps.setStatusMessage).toHaveBeenCalledWith(
        "Invalid credentials"
      );
    });
  });

  it("validates password is required", async () => {
    const mockProps = createMockProps();
    renderWithProviders(<LoginComponent {...mockProps} />);

    const emailInput = screen.getByPlaceholderText("Enter Email");
    const submitButton = screen.getByRole("button", { name: "Continue" });

    fireEvent.change(emailInput, { target: { value: "test@example.com" } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockProps.setStatusMessage).toHaveBeenCalledWith(
        "Must enter a password"
      );
    });
  });

  it("navigates to forgot password page", () => {
    const mockProps = createMockProps();
    renderWithProviders(<LoginComponent {...mockProps} />);

    const forgotPasswordLink = screen.getByText("Forgot Password?");
    expect(forgotPasswordLink).toBeInTheDocument();

    fireEvent.click(forgotPasswordLink);
    expect(mockProps.setPageState).toHaveBeenCalledWith(3);
  });

  it("navigates to signup page", () => {
    const mockProps = createMockProps();
    renderWithProviders(<LoginComponent {...mockProps} />);

    const signupSpan = screen.getByText("Sign Up");
    expect(signupSpan).toBeInTheDocument();

    fireEvent.click(signupSpan);
    expect(mockProps.setPageState).toHaveBeenCalledWith(2);
  });

  it("displays status message when provided", () => {
    const mockProps = createMockProps();
    mockProps.statusMessage = "Test error message";

    renderWithProviders(<LoginComponent {...mockProps} />);

    expect(screen.getByText("Test error message")).toBeInTheDocument();
  });
});
