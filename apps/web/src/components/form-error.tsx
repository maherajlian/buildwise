import { ApiError, fieldMessage } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function ErrorBox({
  error,
  action,
  onAction,
}: {
  error?: ApiError;
  action?: string;
  onAction?: () => void;
}) {
  if (!error) return null;
  return (
    <div className="error-box" role="alert">
      <strong>Something needs attention</strong>
      <p>{error.message}</p>
      {error.correlationId && (
        <p className="break-all">Correlation ID: {error.correlationId}</p>
      )}
      {action && onAction && (
        <Button variant="outline" size="sm" onClick={onAction}>
          {action}
        </Button>
      )}
    </div>
  );
}

export function FieldError({
  error,
  field,
  id,
}: {
  error?: ApiError;
  field: string;
  id: string;
}) {
  const message = fieldMessage(error, field);
  if (!message) return null;
  return (
    <p id={id} className="field-error">
      {message}
    </p>
  );
}

export function toApiError(cause: unknown) {
  return cause instanceof ApiError
    ? cause
    : new ApiError(
        "Browser storage is unavailable. Enable local storage to keep your private project token.",
      );
}

export function requiredError(field: string, label: string) {
  return new ApiError(`${label} is required.`, undefined, [
    { field, message: `Enter a ${label.toLowerCase()}.` },
  ]);
}

export function lines(value: string) {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}
