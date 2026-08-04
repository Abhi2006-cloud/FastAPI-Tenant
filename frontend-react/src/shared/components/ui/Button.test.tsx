import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Button } from './Button';

describe('Button Primitive Component', () => {
  it('renders children correctly', () => {
    render(<Button>Click Me</Button>);
    expect(screen.getByText('Click Me')).toBeInTheDocument();
  });

  it('handles loading state', () => {
    render(<Button isLoading>Submit</Button>);
    expect(screen.getByText('Submit')).toBeInTheDocument();
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
