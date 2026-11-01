// Thin API client. The generated OpenAPI client (packages/openapi) replaces this in M8.

export type Level = "Low" | "Moderate" | "High" | "Severe";

export interface AreaRisk {
  code: string;
  name: string;
  name_or: string;
  score: number;
  level: Level;
  drivers: string[];
  contributions: Record<string, number>;
  forecast_max_12h: number;
  hours_to_severe: number | null;
  inputs?: Record<string, number | string | null>;
}

export interface EarlyWarning {
  state: "NOW" | "WARNING" | "Clear";
  area: string | null;
  name: string | null;
  hours: number | null;
}

export interface SimState {
  scenario: string;
  scenario_name: string | null;
  t: number;
  hour: number | null;
  sim_time: string | null;
  t_min: number;
  t_max: number;
  playing: boolean;
  speed: number;
  speeds: number[];
}

export interface WsEvent<T = unknown> {
  type: string;
  data: T;
  at: string;
}

const BASE = "/api/v1";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body?.error?.message ?? res.statusText);
  return body as T;
}

export const post = <T>(path: string, data?: unknown) =>
  api<T>(path, { method: "POST", body: data === undefined ? undefined : JSON.stringify(data) });

export function wsUrl(): string {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${location.host}${BASE}/ws`;
}

export const LEVEL_VAR: Record<Level, string> = {
  Low: "var(--lv-low)",
  Moderate: "var(--lv-moderate)",
  High: "var(--lv-high)",
  Severe: "var(--lv-severe)",
};
