/** Configuration-only read: this endpoint never invokes a model. */
export async function readRuntimeConfiguration(signal: AbortSignal): Promise<unknown> {
  const response = await fetch("/api/health", { signal, cache: "no-store" });
  if (!response.ok) throw new Error("Health request failed");
  return response.json();
}
