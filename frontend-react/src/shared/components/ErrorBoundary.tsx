import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public override state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught React error:", error, errorInfo);
  }

  public handleRetry = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public override render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center p-6">
          <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-8 max-w-md w-full shadow-sm text-center space-y-4">
            <div className="w-10 h-10 rounded-full bg-[#FEF2F2] border border-[#FEE2E2] flex items-center justify-center mx-auto text-[#DC2626]">
              <AlertCircle className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-[16px] font-semibold text-[#18181B]">Something went wrong</h2>
              <p className="text-[13px] text-[#52525B] mt-1">
                An unexpected application error occurred. You can retry the action or reload the workspace.
              </p>
            </div>
            {this.state.error && (
              <pre className="text-[11px] p-2.5 bg-[#F4F4F5] rounded text-left overflow-x-auto text-[#71717A]">
                {this.state.error.message}
              </pre>
            )}
            <div className="pt-2 flex justify-center">
              <button
                type="button"
                onClick={this.handleRetry}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#0F766E] hover:bg-[#115E59] text-white text-[13px] font-medium rounded-[6px]"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Reload Application
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
