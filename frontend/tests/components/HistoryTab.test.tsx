import { render, screen } from "@testing-library/react";
import { HistoryTab } from "@/components/HistoryTab";
import { useAppStore } from "@/lib/store";
import { RunRecord } from "@/types";

const mockRun: RunRecord = {
  id: "run-1",
  idea: "Test idea",
  status: "completed",
  created_at: new Date().toISOString(),
};

jest.mock("swr", () => ({
  __esModule: true,
  default: () => ({ data: undefined, error: undefined }),
}));

describe("HistoryTab", () => {
  beforeEach(() => {
    useAppStore.setState({ runs: [mockRun] });
  });

  it("renders run records", () => {
    render(<HistoryTab />);
    expect(screen.getByText("run-1")).toBeInTheDocument();
    expect(screen.getByText("completed")).toBeInTheDocument();
  });
});
