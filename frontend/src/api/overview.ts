import type { OverviewResponse } from "../types/overview";

export async function fetchOverview(signal?: AbortSignal): Promise<OverviewResponse> {
  const response = await fetch("/api/overview", {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new Error(`Overview 요청에 실패했습니다. (${response.status})`);
  }

  return (await response.json()) as OverviewResponse;
}

