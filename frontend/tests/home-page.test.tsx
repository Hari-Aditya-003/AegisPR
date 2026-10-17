import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const push = vi.fn();
const create = vi.fn().mockResolvedValue({ id: "run-42" });

vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("../lib/api", () => ({ createVerification: (...args: unknown[]) => create(...args) }));

import HomePage from "../app/page";


describe("HomePage", () => {
  it("lets visitors explore a clearly labeled example without starting a real run", () => {
    render(<HomePage />);
    expect(screen.getByText(/interactive example.*not a live review/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Safe change" }));
    expect(screen.getByText("VERIFIED WITHIN SCOPE")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Verified repair" }));
    expect(screen.getByText("FIX VERIFIED")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Regression" }));
    expect(screen.getByText("REGRESSION FOUND")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show test code" }));
    expect(screen.getByText(/def test_discount_boundary/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show evidence" }));
    expect(screen.getByText("REGRESSION FOUND")).toBeInTheDocument();
  });

  it("explains features and routes to the live run", async () => {
    render(<HomePage />);
    expect(screen.getByRole("heading", { name: /reasoning becomes an experiment/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /two compute planes/i })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/github pull request/i), { target: { value: "https://github.com/acme/store/pull/42" } });
    fireEvent.click(screen.getByRole("button", { name: /verify pr/i }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/verifications/run-42"));
  });
});
