import type { RunEvent, ValidationResult } from "../../api/types";

export function validationResults(event?: RunEvent): ValidationResult[] {
  const results = event?.payload.results;
  return Array.isArray(results) ? results.filter(result => result && typeof result === "object") : [];
}

export function hasSuccessfulValidation(event?: RunEvent): boolean {
  const results = event?.payload.results;
  return event?.payload.passed === true && Array.isArray(results) && results.length > 0 &&
    results.every(result => result && typeof result === "object" && result.exit_code === 0 &&
      result.timed_out === false && Array.isArray(result.command) && result.command.length > 0 &&
      result.command.every((part: unknown) => typeof part === "string" && part.trim()) &&
      typeof result.duration_seconds === "number" && Number.isFinite(result.duration_seconds) &&
      result.duration_seconds >= 0) && results.some(result => result.command.includes("pytest"));
}
