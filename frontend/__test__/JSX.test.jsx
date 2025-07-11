import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

// Simple component for testing
const TestComponent = ({ text = 'Hello World' }) => {
  return <div>{text}</div>
}

describe('JSX Test', () => {
  it('should render a simple component', () => {
    render(<TestComponent />)
    expect(screen.getByText('Hello World')).toBeInTheDocument()
  })
  
  it('should render with props', () => {
    render(<TestComponent text="Custom Text" />)
    expect(screen.getByText('Custom Text')).toBeInTheDocument()
  })
})
