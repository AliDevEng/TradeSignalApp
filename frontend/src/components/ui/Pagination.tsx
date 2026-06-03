import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/Button";

type PaginationProps = {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  disabled?: boolean;
};

/** Compact previous/next pager with a "page X of Y" readout. */
export function Pagination({ page, totalPages, onPageChange, disabled = false }: PaginationProps) {
  if (totalPages <= 1) {
    return null;
  }

  return (
    <div className="flex items-center justify-between gap-3">
      <Button
        disabled={disabled || page <= 1}
        onClick={() => onPageChange(page - 1)}
        size="sm"
        variant="secondary"
      >
        <ChevronLeft className="h-4 w-4" />
        Previous
      </Button>
      <span className="text-sm font-medium text-[var(--muted)]">
        Page {page} of {totalPages}
      </span>
      <Button
        disabled={disabled || page >= totalPages}
        onClick={() => onPageChange(page + 1)}
        size="sm"
        variant="secondary"
      >
        Next
        <ChevronRight className="h-4 w-4" />
      </Button>
    </div>
  );
}
