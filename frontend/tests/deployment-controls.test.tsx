import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { DeploymentControls } from "../components/deployment-controls";

afterEach(() => { sessionStorage.clear(); document.documentElement.removeAttribute("data-motion"); });

describe("DeploymentControls", () => {
  it("lets visitors pause and resume decorative motion", () => {
    render(<DeploymentControls />);
    fireEvent.click(screen.getByRole("button", { name: "Pause animation" }));
    expect(document.documentElement).toHaveAttribute("data-motion", "paused");
    fireEvent.click(screen.getByRole("button", { name: "Resume animation" }));
    expect(document.documentElement).not.toHaveAttribute("data-motion");
  });

  it("stores private deployment access only for the session and can forget it", () => {
    render(<DeploymentControls />);
    fireEvent.click(screen.getByText("Private deployment access"));
    fireEvent.change(screen.getByLabelText("Deployment access code"), { target: { value: "private-code" } });
    expect(screen.getByLabelText("Deployment access code")).toHaveAttribute("type", "password");
    fireEvent.click(screen.getByRole("button", { name: "Save access code" }));
    expect(screen.getByRole("status")).toHaveTextContent(/saved for this tab/i);
    expect(localStorage.length).toBe(0);
    expect(screen.getByLabelText("Deployment access code")).toHaveValue("");
    fireEvent.click(screen.getByRole("button", { name: "Clear saved code" }));
    expect(sessionStorage.length).toBe(0);
    expect(screen.getByRole("status")).toHaveTextContent(/cleared/i);
  });
});
