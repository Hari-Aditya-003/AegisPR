import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { VerificationForm } from "../components/verification-form";


describe("VerificationForm", () => {
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
});

