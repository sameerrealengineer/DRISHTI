import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("landing", () => {
  it("shows the three role cards", () => {
    render(<App />);
    expect(screen.getByText("Command Centre")).toBeTruthy();
    expect(screen.getByText("Citizen app")).toBeTruthy();
    expect(screen.getByText("Field Responder app")).toBeTruthy();
  });
});
