/**
 * Utility functions for handling API errors
 */

export interface ApiError {
  detail?: string | Array<{ msg: string; loc?: string[] }>;
  message?: string;
  [key: string]: unknown;
}

interface ApiErrorDetail {
  msg?: string;
  message?: string;
  loc?: string[];
}

interface ApiErrorResponseBody {
  detail?: string | ApiErrorDetail[];
  message?: string;
  error?: unknown;
}

function isApiErrorResponse(error: unknown): error is { response?: { data?: ApiErrorResponseBody }; message?: string } {
  return typeof error === 'object' && error !== null;
}

/**
 * Extract a readable error message from API response
 * Handles both string details and Pydantic validation error arrays
 */
export function getErrorMessage(error: unknown): string {
  // Handle Axios timeout (ECONNABORTED)
  if (
    isApiErrorResponse(error) &&
    typeof error.message === 'string' &&
    error.message.toLowerCase().includes('timeout')
  ) {
    return 'Le traitement du CV prend plus de temps que prevu. Merci de reessayer dans quelques instants avec un fichier plus leger (max 5 MB).';
  }

  // If error has response data
  if (isApiErrorResponse(error) && error.response?.data) {
    const data = error.response.data;

    // Handle Pydantic validation errors (array of error objects)
    if (Array.isArray(data.detail)) {
      const messages = data.detail.map((err) => {
        const loc = Array.isArray(err.loc) ? err.loc.join('.') : '';
        const msg = err.msg || err.message || 'Unknown error';
        return loc ? `${loc}: ${msg}` : msg;
      });
      return messages.join('; ');
    }

    // Handle string detail
    if (typeof data.detail === 'string') {
      return data.detail;
    }

    // Handle message field
    if (typeof data.message === 'string') {
      return data.message;
    }

    // Handle generic error object
    if (data.error) {
      return typeof data.error === 'string' ? data.error : JSON.stringify(data.error);
    }
  }

  // Fallback to error message
  if (isApiErrorResponse(error) && typeof error.message === 'string') {
    return error.message;
  }

  return 'An unknown error occurred';
}
