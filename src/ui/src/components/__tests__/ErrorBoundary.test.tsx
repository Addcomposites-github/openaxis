/**
 * Tests for the ErrorBoundary component.
 *
 * Verifies:
 * - Children render normally when no error occurs
 * - Error message is displayed when a child throws
 * - Custom fallback UI is rendered when provided
 * - "Try Again" button resets the error state
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ErrorBoundary from '../ErrorBoundary';

// A component that always throws during render.
// Return type annotation ensures TypeScript treats it as a valid JSX component.
function ThrowingChild({ message }: { message: string }): JSX.Element {
  throw new Error(message);
}

// Suppress React error boundary console noise during tests
const originalConsoleError = console.error;
beforeEach(() => {
  console.error = vi.fn();
});
afterEach(() => {
  console.error = originalConsoleError;
});

describe('ErrorBoundary', () => {
  it('renders children when no error occurs', () => {
    render(
      <ErrorBoundary>
        <p>Hello, world</p>
      </ErrorBoundary>,
    );
    expect(screen.getByText('Hello, world')).toBeInTheDocument();
  });

  it('shows error message when a child throws', () => {
    render(
      <ErrorBoundary>
        <ThrowingChild message="kaboom" />
      </ErrorBoundary>,
    );
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText('kaboom')).toBeInTheDocument();
  });

  it('renders custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<p>Custom fallback</p>}>
        <ThrowingChild message="boom" />
      </ErrorBoundary>,
    );
    expect(screen.getByText('Custom fallback')).toBeInTheDocument();
    expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument();
  });

  it('"Try Again" button resets error state', () => {
    // We need a component that throws on first render but not on second
    let shouldThrow = true;
    function ConditionalThrow() {
      if (shouldThrow) throw new Error('first error');
      return <p>Recovered!</p>;
    }

    render(
      <ErrorBoundary>
        <ConditionalThrow />
      </ErrorBoundary>,
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    // Fix the component, then click "Try Again"
    shouldThrow = false;
    fireEvent.click(screen.getByText('Try Again'));

    expect(screen.getByText('Recovered!')).toBeInTheDocument();
    expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument();
  });

  it('shows default message when error has no message', () => {
    function ThrowNull(): JSX.Element {
      throw new Error('');
    }

    render(
      <ErrorBoundary>
        <ThrowNull />
      </ErrorBoundary>,
    );
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });
});
