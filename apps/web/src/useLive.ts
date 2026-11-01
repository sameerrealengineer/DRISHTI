import { useEffect, useRef, useState } from "react";

import { type AreaRisk, type EarlyWarning, type SimState, type WsEvent, wsUrl } from "./api";

interface RiskUpdate {
  t: number;
  areas: Partial<AreaRisk>[];
  early_warning: EarlyWarning;
}

/** Subscribes to sim.tick and risk.updated; merges changed areas into state. Reconnects on drop. */
export function useLive() {
  const [sim, setSim] = useState<SimState | null>(null);
  const [areas, setAreas] = useState<Record<string, AreaRisk>>({});
  const [warning, setWarning] = useState<EarlyWarning | null>(null);
  const [connected, setConnected] = useState(false);
  const retry = useRef(0);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let stopped = false;
    let timer: number | undefined;

    const connect = () => {
      ws = new WebSocket(wsUrl());
      ws.onopen = () => {
        retry.current = 0;
        setConnected(true);
      };
      ws.onclose = () => {
        setConnected(false);
        if (!stopped) timer = window.setTimeout(connect, Math.min(10000, 500 * 2 ** retry.current++));
      };
      ws.onmessage = (msg) => {
        const ev = JSON.parse(msg.data) as WsEvent;
        if (ev.type === "sim.tick") setSim(ev.data as SimState);
        if (ev.type === "risk.updated") {
          const d = ev.data as RiskUpdate;
          setWarning(d.early_warning);
          setAreas((prev) => {
            const next = { ...prev };
            for (const a of d.areas) if (a.code) next[a.code] = { ...next[a.code], ...a } as AreaRisk;
            return next;
          });
        }
      };
    };
    connect();
    return () => {
      stopped = true;
      window.clearTimeout(timer);
      ws?.close();
    };
  }, []);

  return { sim, areas, warning, connected };
}
