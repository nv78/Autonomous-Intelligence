import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { Provider } from 'react-redux'
import { BrowserRouter } from 'react-router-dom'
import { configureStore } from '@reduxjs/toolkit'
import LoginComponent from '../src/subcomponents/login/LoginComponent'

// Mock the axios module
vi.mock('axios', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
    defaults: {
      headers: {
        common: {}
      }
    }
  }
}))

// Mock react-router-dom hooks
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useLocation: () => ({ pathname: '/login' })
  }
})

// Mock Redux store
const createMockStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      auth: (state = { user: null, isAuthenticated: false }, action) => {
        switch (action.type) {
          case 'LOGIN_SUCCESS':
            return { ...state, user: action.payload, isAuthenticated: true }
          default:
            return state
        }
      }
    },
    preloadedState: initialState
  })
}

// Helper function to render component with providers
const renderWithProviders = (component, initialState = {}) => {
  const store = createMockStore(initialState)
  return render(
    <Provider store={store}>
      <BrowserRouter>
        {component}
      </BrowserRouter>
    </Provider>
  )
}

describe('LoginComponent', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders login form correctly', () => {
    renderWithProviders(<LoginComponent />)
    
    // Check if login form elements are present
    expect(screen.getByRole('textbox', { name: /email/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('displays validation errors for empty fields', async () => {
    renderWithProviders(<LoginComponent />)
    
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument()
    })
    
    expect(screen.getByText(/password is required/i)).toBeInTheDocument()
  })

  it('handles email input changes', () => {
    renderWithProviders(<LoginComponent />)
    
    const emailInput = screen.getByRole('textbox', { name: /email/i })
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    
    expect(emailInput.value).toBe('test@example.com')
  })

  it('handles password input changes', () => {
    renderWithProviders(<LoginComponent />)
    
    const passwordInput = screen.getByLabelText(/password/i)
    fireEvent.change(passwordInput, { target: { value: 'password123' } })
    
    expect(passwordInput.value).toBe('password123')
  })

  it('submits form with valid credentials', async () => {
    const axios = await import('axios')
    const mockPost = vi.mocked(axios.default.post)
    
    mockPost.mockResolvedValueOnce({
      data: {
        success: true,
        user: { id: 1, email: 'test@example.com' },
        token: 'mock-token'
      }
    })

    renderWithProviders(<LoginComponent />)
    
    const emailInput = screen.getByRole('textbox', { name: /email/i })
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'password123' } })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith(
        expect.stringContaining('/login'),
        expect.objectContaining({
          email: 'test@example.com',
          password: 'password123'
        })
      )
    })
  })

  it('displays error message on login failure', async () => {
    const axios = await import('axios')
    const mockPost = vi.mocked(axios.default.post)
    
    mockPost.mockRejectedValueOnce({
      response: {
        data: {
          message: 'Invalid credentials'
        }
      }
    })

    renderWithProviders(<LoginComponent />)
    
    const emailInput = screen.getByRole('textbox', { name: /email/i })
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'wrongpassword' } })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
    })
  })

  it('shows loading state during form submission', async () => {
    const axios = await import('axios')
    const mockPost = vi.mocked(axios.default.post)
    
    // Mock a delayed response
    mockPost.mockImplementationOnce(() => 
      new Promise(resolve => setTimeout(() => resolve({ data: { success: true } }), 100))
    )

    renderWithProviders(<LoginComponent />)
    
    const emailInput = screen.getByRole('textbox', { name: /email/i })
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'password123' } })
    fireEvent.click(submitButton)
    
    // Check if loading state is shown (adjust based on your actual loading implementation)
    expect(submitButton).toBeDisabled()
  })

  it('toggles password visibility', () => {
    renderWithProviders(<LoginComponent />)
    
    const passwordInput = screen.getByLabelText(/password/i)
    const toggleButton = screen.getByRole('button', { name: /toggle password visibility/i })
    
    // Initially password should be hidden
    expect(passwordInput.type).toBe('password')
    
    // Click toggle button
    fireEvent.click(toggleButton)
    
    // Password should now be visible
    expect(passwordInput.type).toBe('text')
    
    // Click again to hide
    fireEvent.click(toggleButton)
    expect(passwordInput.type).toBe('password')
  })

  it('validates email format', async () => {
    renderWithProviders(<LoginComponent />)
    
    const emailInput = screen.getByRole('textbox', { name: /email/i })
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    
    fireEvent.change(emailInput, { target: { value: 'invalid-email' } })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText(/please enter a valid email/i)).toBeInTheDocument()
    })
  })

  it('handles Google OAuth login', () => {
    renderWithProviders(<LoginComponent />)
    
    const googleButton = screen.getByRole('button', { name: /continue with google/i })
    expect(googleButton).toBeInTheDocument()
    
    fireEvent.click(googleButton)
    
    // Verify that OAuth flow is initiated (adjust based on your implementation)
    // This might involve checking if window.open was called or a redirect occurred
  })

  it('navigates to signup page', () => {
    renderWithProviders(<LoginComponent />)
    
    const signupLink = screen.getByRole('link', { name: /don't have an account/i })
    expect(signupLink).toHaveAttribute('href', '/signup')
  })

  it('navigates to forgot password page', () => {
    renderWithProviders(<LoginComponent />)
    
    const forgotPasswordLink = screen.getByText(/forgot password/i)
    expect(forgotPasswordLink).toBeInTheDocument()
    
    fireEvent.click(forgotPasswordLink)
    // Add assertions based on your forgot password implementation
  })
})
