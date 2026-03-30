import { useParams } from "react-router-dom";
import { useState, useEffect } from "react";
import { useProjectContext } from "../context/ProjectContext";
import MenuNavbar from "./MenuNavbar";
import Table from "./Table";
import DataVisualization from "./DataVisualization";

export default function DataScreen() {
  const { projectId } = useParams();
  const { setProjectInfo, refreshProject, updateData } = useProjectContext();
  const [tableData, setTableData] = useState(null);
  const [viewMode, setViewMode] = useState("table");

  useEffect(() => {
    if (projectId) {
      setProjectInfo(projectId);
      refreshProject(projectId);
    }
  }, [projectId, setProjectInfo, refreshProject]);

  const handleTransform = (data) => {
    setTableData(data);
    if (data?.columns && data?.rows) {
      updateData(data.columns, data.rows, data.dtypes);
    }
  };

  return (
    <div className="flex flex-col min-h-screen">
      <MenuNavbar onTransform={handleTransform} projectId={projectId} />
      <DataVisualization viewMode={viewMode} onViewModeChange={setViewMode} />
      {viewMode === "table" && <Table projectId={projectId} data={tableData} />}
    </div>
  );
}
