import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { VerificationForm } from "../components/verification-form";


describe("VerificationForm", () => {
  it("prefills a public PR from the website handoff without starting a paid review", async () => {
    const onSubmit = vi.fn();
    window.history.replaceState(null, "", "/?pr=https%3A%2F%2Fgithub.com%2Facme%2Fstore%2Fpull%2F42");
    try {
      render(<VerificationForm onSubmit={onSubmit} />);
      await waitFor(() => expect(screen.getByLabelText(/github pull request/i)).toHaveValue("https://github.com/acme/store/pull/42"));
      expect(onSubmit).not.toHaveBeenCalled();
    } finally {
      window.history.replaceState(null, "", "/");
    }
  });

  it("ignores invalid PR handoff values", async () => {
    window.history.replaceState(null, "", "/?pr=javascript%3Aalert(1)");
    try {
      render(<VerificationForm onSubmit={vi.fn()} />);
      await waitFor(() => expect(screen.getByLabelText(/github pull request/i)).toHaveValue(""));
    } finally {
      window.history.replaceState(null, "", "/");
    }
  });

  it("explains the product and accepts a public GitHub pull request", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<VerificationForm onSubmit={onSubmit} />);

    expect(screen.getByRole("heading", { name: /don't trust a pr/i })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/github pull request/i), {
      target: { value: "https://github.com/acme/store/pull/42" },
    });
    fireEvent.click(screen.getByRole("button", { name: /verify pr/i }));

    expect(onSubmit).toHaveBeenCalledWith("https://github.com/acme/store/pull/42");
  });

  it("shows validation feedback for non-GitHub URLs", () => {
    render(<VerificationForm onSubmit={vi.fn()} />);
    fireEvent.change(screen.getByLabelText(/github pull request/i), {
      target: { value: "https://example.com/pr/1" },
    });
    fireEvent.click(screen.getByRole("button", { name: /verify pr/i }));
    expect(screen.getByRole("alert")).toHaveTextContent(/public github pull request/i);
  });

  it("surfaces bounded submission errors and restores the button", async () => {
    render(<VerificationForm onSubmit={vi.fn().mockRejectedValue("offline")} />);
    fireEvent.change(screen.getByLabelText(/github pull request/i), {
      target: { value: "https://github.com/acme/store/pull/42/" },
    });
    fireEvent.click(screen.getByRole("button", { name: /verify pr/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Verification could not start.");
    expect(screen.getByRole("button", { name: /verify pr/i })).toBeEnabled();
  });
});
