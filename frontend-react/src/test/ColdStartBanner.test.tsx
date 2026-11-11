import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import axios from "axios";
import { ColdStartBanner } from "../shared/components/ColdStartBanner.tsx";

vi.mock("axios");

describe("ColdStartBanner", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.resetAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not show banner immediately if server is responding or pending under 4 seconds", () => {
    vi.mocked(axios.get).mockImplementation(() => new Promise(() => {})); // pending
    render(<ColdStartBanner />);

    expect(screen.queryByRole("status")).toBeNull();
  });

  it("shows banner after 4s timeout if server is still waking", async () => {
    vi.mocked(axios.get).mockImplementation(() => new Promise(() => {})); // pending
    render(<ColdStartBanner />);

    act(() => {
      vi.advanceTimersByTime(4100);
    });

    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(
      screen.getByText("Free hosting is waking the server. This can take up to a minute.")
    ).toBeInTheDocument();
  });

  it("dismisses banner once health check succeeds", async () => {
    let resolveHealth: (value: unknown) => void = () => {};
    vi.mocked(axios.get).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveHealth = resolve;
        })
    );

    render(<ColdStartBanner />);

    // Advance past 4s
    act(() => {
      vi.advanceTimersByTime(4100);
    });
    expect(screen.getByRole("status")).toBeInTheDocument();

    // Resolve health check
    await act(async () => {
      resolveHealth({ data: { status: "ok" } });
      await Promise.resolve();
    });

    expect(screen.queryByRole("status")).toBeNull();
  });
});

