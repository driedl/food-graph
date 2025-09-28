import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card'
import { Button } from '@ui/button'

interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
}

class ErrorBoundary extends React.Component<
  React.PropsWithChildren<{}>,
  ErrorBoundaryState
> {
  constructor(props: React.PropsWithChildren<{}>) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <Card className="border-red-200">
          <CardHeader>
            <CardTitle className="text-red-600">Something went wrong</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <Button 
              onClick={() => this.setState({ hasError: false, error: undefined })}
              variant="outline"
            >
              Try again
            </Button>
          </CardContent>
        </Card>
      )
    }

    return this.props.children
  }
}

export { ErrorBoundary }
export default ErrorBoundary
