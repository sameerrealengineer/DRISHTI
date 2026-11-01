import { useEffect, useMemo, useState } from "react";

import { type AreaRisk, LEVEL_VAR, post } from "./api";
import { useLive } from "./useLive";

function useHashRoute() {
  const [route, setRoute] = useState(location.hash.replace(/^#/, "") || "/");
  useEffect(() => {
    const on = () => setRoute(location.hash.replace(/^#/, "") || "/");
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}

export default function App() {
  const route = useHashRoute();
  return route.startsWith("/cc") ? <CommandCentre /> : <Landing />;
}

const ROLES = [
  { href: "#/cc", title: "Command Centre", body: "District officers: live risk, alerts, rescue, shelters." },
  { href: "#/", title: "Citizen app", body: "Web preview of the Android app (milestone M11).", soon: true },
  {
    href: "#/",
    title: "Field Responder app",
    body: "Web preview of the Android app (milestone M11).",
    soon: true,
  },
];

const STORY = [
  "Rain, rivers, satellite and citizen messages are fused into a 0–100 risk score for every block, every hour.",
  "The AI forecast flags blocks that will turn Severe in the next 12 hours.",
  "Officers approve targeted alerts in Odia and English; citizens send SOS and reports.",
  "Teams are dispatched to the highest-risk places and close the rescue loop in real time.",
];

function Landing() {
  return (
    <main className="landing">
      <header>
        <h1>
          DRISHTI <span className="odia">ଦୃଷ୍ଟି</span>
        </h1>
        <p className="muted">Hyperlocal disaster intelligence for Ganjam district, Odisha</p>
      </header>
      <section className="roles">
        {ROLES.map((r) => (
          <a
            key={r.title}
            className={`card role${r.soon ? " soon" : ""}`}
            href={r.href}
            aria-disabled={r.soon}
          >
            <h2>{r.title}</h2>
            <p>{r.body}</p>
            {r.soon && <span className="pill">coming soon</span>}
          </a>
        ))}
      </section>
      <ol className="story">
        {STORY.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ol>
      <footer className="muted">
        OSFIC 2026 · PS-074 · TeamGanjam, SMIT Berhampur · <span className="pill">Demo data</span>
      </footer>
    </main>
  );
}

function CommandCentre() {
  const { sim, areas, warning, connected } = useLive();
  const [selected, setSelected] = useState<string | null>(null);
  const list = useMemo(() => Object.values(areas).sort((a, b) => b.score - a.score), [areas]);
  const counts = useMemo(() => {
    const c = { Severe: 0, High: 0, Moderate: 0, Low: 0 };
    for (const a of list) c[a.level] += 1;
    return c;
  }, [list]);
  const sel = selected ? areas[selected] : null;

  return (
    <div className="cc">
      <header className="topbar">
        <a href="#/" className="brand">
          DRISHTI <span className="muted">Command Centre</span>
        </a>
        <span className={`status ${counts.Severe ? "active" : counts.High ? "watch" : ""}`}>
          {counts.Severe ? "CYCLONE MODE · ACTIVE" : counts.High ? "CYCLONE WATCH" : "ROUTINE WATCH"}
        </span>
        <span className={`dot ${connected ? "ok" : "bad"}`} title={connected ? "Live" : "Reconnecting"} />
      </header>

      {sim && <Timeline sim={sim} />}

      <section className="kpis">
        <Kpi label="Blocks Severe / High" value={`${counts.Severe} / ${counts.High}`} />
        <Kpi
          label="AI early warning"
          value={
            !warning
              ? "—"
              : warning.state === "NOW"
                ? `NOW · ${warning.name}`
                : warning.state === "WARNING"
                  ? `${warning.name} in ${warning.hours} h`
                  : "Clear"
          }
        />
        <Kpi label="Scenario" value={sim?.scenario_name ?? "—"} />
      </section>

      <section className="grid">
        <div className="card">
          <h3>Priority list</h3>
          <ul className="priority">
            {list.slice(0, 12).map((a) => (
              <li key={a.code}>
                <button
                  className={selected === a.code ? "row sel" : "row"}
                  onClick={() => setSelected(a.code)}
                >
                  <span className="ring" style={{ borderColor: LEVEL_VAR[a.level] }}>
                    {a.score}
                  </span>
                  <span className="name">
                    {a.name}
                    <small className="muted">{a.drivers?.join(" · ")}</small>
                    {a.hours_to_severe && a.score < 75 ? (
                      <small className="warn">▲ AI: Severe in {a.hours_to_severe} h</small>
                    ) : null}
                  </span>
                  <span className="pill" style={{ background: LEVEL_VAR[a.level] }}>
                    {a.level}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h3>{sel ? `Why ${sel.name} scores ${sel.score}` : "Select a block"}</h3>
          {sel ? <Contributions area={sel} /> : <p className="muted">Tap a block in the priority list.</p>}
        </div>
      </section>
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="card kpi">
      <small className="muted">{label}</small>
      <strong>{value}</strong>
    </div>
  );
}

function Contributions({ area }: { area: AreaRisk }) {
  const entries = Object.entries(area.contributions ?? {});
  return (
    <div className="contrib">
      {entries.map(([k, v]) => (
        <div key={k} className="bar">
          <span>{k}</span>
          <div className="track">
            <div className="fill" style={{ width: `${Math.min(100, v)}%` }} />
          </div>
          <span className="mono">{v.toFixed(0)}</span>
        </div>
      ))}
      <p className="muted">
        Forecast max in 12 h: <b>{area.forecast_max_12h}</b>
        {area.hours_to_severe ? ` · Severe in ${area.hours_to_severe} h` : ""}
      </p>
    </div>
  );
}

function Timeline({ sim }: { sim: import("./api").SimState }) {
  const fmt = (t: number) => `${t >= 0 ? "+" : ""}${t.toFixed(1)} h`;
  return (
    <section className="timeline card">
      <button onClick={() => post(sim.playing ? "/sim/pause" : "/sim/play")} aria-label="play or pause">
        {sim.playing ? "❚❚" : "▶"}
      </button>
      <input
        type="range"
        min={sim.t_min}
        max={sim.t_max}
        step={1}
        value={sim.t}
        aria-label="sim time"
        onChange={(e) => post("/sim/seek", { t_hours: Number(e.target.value) })}
      />
      <span className="mono">{fmt(sim.t)}</span>
      {sim.speeds.map((s) => (
        <button
          key={s}
          className={s === sim.speed ? "on" : ""}
          onClick={() => post("/sim/speed", { speed: s })}
        >
          {s}×
        </button>
      ))}
      <span className="mono muted">{sim.sim_time?.replace("T", " ").slice(0, 16)} IST</span>
    </section>
  );
}
