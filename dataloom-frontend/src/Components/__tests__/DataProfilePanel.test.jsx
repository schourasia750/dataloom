import { render, screen } from "@testing-library/react";
import DataProfilePanel from "../DataProfilePanel";

describe("DataProfilePanel", () => {
  it("renders summary metrics and per-column statistics", () => {
    render(
      <DataProfilePanel
        profile={{
          summary: {
            row_count: 12,
            column_count: 3,
            missing_cells: 2,
            duplicate_rows: 1,
          },
          columns: [
            {
              name: "salary",
              data_type: "float",
              non_null_count: 10,
              missing_count: 2,
              missing_percent: 16.67,
              unique_count: 9,
              unique_percent: 90,
              sample_values: [45000, 52000, 61000],
              mean: 53333.33,
              min: 45000,
              max: 61000,
            },
          ],
        }}
      />,
    );

    expect(screen.getByText("Automatic Profile")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("salary")).toBeInTheDocument();
    expect(screen.getByText("53,333.33")).toBeInTheDocument();
    expect(screen.getByText("45,000")).toBeInTheDocument();
    expect(screen.getByText("61,000")).toBeInTheDocument();
    expect(screen.getByText("16.67%")).toBeInTheDocument();
  });

  it("returns nothing when profile data is missing", () => {
    const { container } = render(<DataProfilePanel profile={null} />);
    expect(container.firstChild).toBeNull();
  });
});
