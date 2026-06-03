import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Pagination } from "@/components/ui/Pagination";

describe("Pagination", () => {
  it("renders nothing for a single page", () => {
    const { container } = render(
      <Pagination onPageChange={vi.fn()} page={1} totalPages={1} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the current page position", () => {
    render(<Pagination onPageChange={vi.fn()} page={2} totalPages={5} />);
    expect(screen.getByText("Page 2 of 5")).toBeInTheDocument();
  });

  it("disables Previous on the first page", () => {
    render(<Pagination onPageChange={vi.fn()} page={1} totalPages={3} />);
    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
  });

  it("advances to the next page on click", async () => {
    const onPageChange = vi.fn();
    render(<Pagination onPageChange={onPageChange} page={2} totalPages={5} />);

    await userEvent.click(screen.getByRole("button", { name: /next/i }));
    expect(onPageChange).toHaveBeenCalledWith(3);
  });
});
