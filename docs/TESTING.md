# Testing Setup with Vitest for frontend

This project now supports Vitest for testing.

## 🚀 Quick Start

### Running Tests

```bash
# Run tests with Jest (react-scripts default)
npm test

# Run tests with Vitest
npm run test:vitest

# Run Vitest tests once (no watch mode)
npm run test:vitest:run

# Run Vitest with UI
npm run test:vitest:ui
```

## 📁 Test File Structure

```
__test__/
├── Basic.test.js           # Basic JavaScript tests
├── JSX.test.jsx           # Simple JSX component tests
├── SimpleLogin.test.jsx   # Login component example
├── AdvancedMocking.test.jsx # Advanced mocking examples
└── Login.test.jsx         # Complex mock tests
```

## 🔧 Configuration

### Vitest Config (`vitest.config.js`)

- Configured to use JSX
- JSDOM environment for React testing
- Automatic cleanup after each test
- Custom setup files

### Setup Files

- `src/setupTests.js` - Shared setup for both Jest and Vitest
- Mock for `window.matchMedia`
- Mock for `ResizeObserver` and `IntersectionObserver`

## ✨ Example Tests

### Basic Component Test

```jsx
import { render, screen } from "@testing-library/react";
import MyComponent from "../src/components/MyComponent";

test("renders component", () => {
  render(<MyComponent />);
  expect(screen.getByText("Hello")).toBeInTheDocument();
});
```

### Testing with Redux

```jsx
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";

const store = configureStore({
  reducer: { auth: authReducer },
});

render(
  <Provider store={store}>
    <MyComponent />
  </Provider>
);
```

### Mocking APIs

```jsx
import { vi } from "vitest";

// Mock fetch
global.fetch = vi.fn();
fetch.mockResolvedValue({
  json: () => Promise.resolve({ data: "test" }),
});
```

## 🎯 Available Mocking Examples

The `AdvancedMocking.test.jsx` file includes examples of:

- Mocking localStorage
- Mocking window methods
- Mocking API calls with different responses
- Mocking timers
- Mocking console methods
- Testing with userEvent
- Testing error boundaries
- Environment variable mocking

## 📚 Key Dependencies

- `vitest` - Test runner
- `@vitest/ui` - Test UI interface
- `@testing-library/react` - React testing utilities
- `@testing-library/jest-dom` - DOM matchers
- `@testing-library/user-event` - User interaction testing
- `jsdom` - DOM environment for tests
- `@vitejs/plugin-react` - React support for Vitest

## 🔍 Best Practices

1. **File Extensions**: Use `.jsx` for test files containing JSX
2. **Test Structure**: Group related tests in `describe` blocks
3. **Cleanup**: Tests automatically clean up after each run
4. **Mocking**: Clear mocks with `vi.clearAllMocks()` in `beforeEach`
5. **Assertions**: Use descriptive test names and specific assertions

## 🛠️ Troubleshooting

### JSX Issues

If you get JSX syntax errors, ensure:

- Test files use `.jsx` extension for JSX content
- Vitest config includes React plugin

### Import Issues

- Use absolute imports from project root
- Mock external dependencies as needed

### Redux/Router Issues

- Wrap components in required providers
- Use helper functions for common wrapper patterns

## 🔄 Migration from Jest

To migrate existing Jest tests to Vitest:

1. Change `jest.fn()` to `vi.fn()`
2. Import `vi` from `vitest`
3. Update mock syntax if needed
4. Rename test files to `.jsx` if they contain JSX

Both testing frameworks can coexist in this project!
