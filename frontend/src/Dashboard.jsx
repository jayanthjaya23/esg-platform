import React, { useEffect, useState } from "react";
import axios from "axios";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
} from "recharts";

export default function Dashboard() {

  const API_BASE = "https://esg-platform-production-c417.up.railway.app";

  const [records, setRecords] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [file, setFile] = useState(null);
  const [sourceType, setSourceType] = useState("sap");
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetchRecords();
    fetchAuditLogs();
  }, []);

  const fetchRecords = async () => {

    try {

      const response = await axios.get(
        `${API_BASE}/api/emissions/`
      );

      setRecords(
        Array.isArray(response.data)
          ? response.data
          : []
      );

    } catch (error) {

      console.error(error);
      setRecords([]);
    }
  };

  const fetchAuditLogs = async () => {

    try {

      const response = await axios.get(
        `${API_BASE}/api/audit-logs/`
      );

      setAuditLogs(
        Array.isArray(response.data)
          ? response.data
          : []
      );

    } catch (error) {

      console.error(error);
      setAuditLogs([]);
    }
  };

  const uploadFile = async () => {

    if (!file) {
      alert("Please select CSV file");
      return;
    }

    const formData = new FormData();

    formData.append("file", file);
    formData.append(
      "source_type",
      sourceType
    );

    try {

      await axios.post(
        `${API_BASE}/api/upload/`,
        formData,
        {
          headers: {
            "Content-Type":
              "multipart/form-data",
          },
        }
      );

      setMessage("Upload successful");

      fetchRecords();
      fetchAuditLogs();

    } catch (error) {

      console.error(error);

      setMessage("Upload failed");
    }
  };

  const approveRecord = async (id) => {

    try {

      await axios.post(
        `${API_BASE}/api/approve/${id}/`
      );

      fetchRecords();
      fetchAuditLogs();

    } catch (error) {

      console.error(error);
    }
  };

  const rejectRecord = async (id) => {

    try {

      await axios.post(
        `${API_BASE}/api/reject/${id}/`
      );

      fetchRecords();
      fetchAuditLogs();

    } catch (error) {

      console.error(error);
    }
  };

  const totalEmissions = records.reduce(
    (sum, r) =>
      sum + Number(r.co2e_kg || 0),
    0
  );

  const scopeData = [
    {
      name: "Scope 1",
      value: records.filter(
        (r) => r.scope === "scope_1"
      ).length,
    },
    {
      name: "Scope 2",
      value: records.filter(
        (r) => r.scope === "scope_2"
      ).length,
    },
    {
      name: "Scope 3",
      value: records.filter(
        (r) => r.scope === "scope_3"
      ).length,
    },
  ];

  const sourceData = [
    {
      name: "SAP",
      emissions: records
        .filter(
          (r) => r.source_type === "sap"
        )
        .reduce(
          (sum, r) =>
            sum + Number(r.co2e_kg || 0),
          0
        ),
    },
    {
      name: "Utility",
      emissions: records
        .filter(
          (r) =>
            r.source_type === "utility"
        )
        .reduce(
          (sum, r) =>
            sum + Number(r.co2e_kg || 0),
          0
        ),
    },
    {
      name: "Travel",
      emissions: records
        .filter(
          (r) =>
            r.source_type === "travel"
        )
        .reduce(
          (sum, r) =>
            sum + Number(r.co2e_kg || 0),
          0
        ),
    },
  ];

  const COLORS = [
    "#2563eb",
    "#16a34a",
    "#dc2626",
  ];

  return (

    <div className="dashboard-container">

      <div className="sidebar">

        <h2>🌍 ESG Platform</h2>

        <ul>
          <li>Dashboard</li>
          <li>Uploads</li>
          <li>Analytics</li>
          <li>Audit Logs</li>
        </ul>

      </div>

      <div className="main-content">

        <div className="topbar">

          <h1>
            ESG Analytics Dashboard
          </h1>

          <p>
            Enterprise Emissions Intelligence Platform
          </p>

        </div>

        {/* Upload */}

        <div className="upload-card">

          <h2>
            Upload ESG CSV
          </h2>

          <select
            value={sourceType}
            onChange={(e) =>
              setSourceType(e.target.value)
            }
          >

            <option value="sap">
              SAP
            </option>

            <option value="utility">
              Utility
            </option>

            <option value="travel">
              Travel
            </option>

          </select>

          <input
            type="file"
            onChange={(e) =>
              setFile(
                e.target.files[0]
              )
            }
          />

          <button onClick={uploadFile}>
            Upload CSV
          </button>

          <p>{message}</p>

        </div>

        {/* Metrics */}

        <div className="metrics-grid">

          <div className="metric-card">

            <h3>Total Records</h3>

            <h1>
              {records.length}
            </h1>

          </div>

          <div className="metric-card">

            <h3>Total CO₂e</h3>

            <h1>
              {totalEmissions} kg
            </h1>

          </div>

        </div>

        {/* Charts */}

        <div className="charts-grid">

          <div className="chart-card">

            <h3>
              Scope Distribution
            </h3>

            <ResponsiveContainer
              width="100%"
              height={300}
            >

              <PieChart>

                <Pie
                  data={scopeData}
                  dataKey="value"
                  outerRadius={100}
                  label
                >

                  {scopeData.map(
                    (entry, index) => (

                      <Cell
                        key={index}
                        fill={COLORS[index]}
                      />

                    )
                  )}

                </Pie>

                <Tooltip />

              </PieChart>

            </ResponsiveContainer>

          </div>

          <div className="chart-card">

            <h3>
              Emissions by Source
            </h3>

            <ResponsiveContainer
              width="100%"
              height={300}
            >

              <BarChart data={sourceData}>

                <CartesianGrid strokeDasharray="3 3" />

                <XAxis dataKey="name" />

                <YAxis />

                <Tooltip />

                <Bar
                  dataKey="emissions"
                  fill="#2563eb"
                />

              </BarChart>

            </ResponsiveContainer>

          </div>

        </div>

        {/* Records */}

        <div className="table-card">

          <h2>
            Emission Records
          </h2>

          <table>

            <thead>

              <tr>

                <th>ID</th>
                <th>Source</th>
                <th>Scope</th>
                <th>Category</th>
                <th>CO₂e</th>
                <th>Status</th>
                <th>Actions</th>

              </tr>

            </thead>

            <tbody>

              {records.map((record) => (

                <tr key={record.id}>

                  <td>{record.id}</td>

                  <td>{record.source_type}</td>

                  <td>{record.scope}</td>

                  <td>{record.category}</td>

                  <td>{record.co2e_kg}</td>

                  <td>
                    {record.approval_status}
                  </td>

                  <td>

                    <button
                      onClick={() =>
                        approveRecord(record.id)
                      }
                    >
                      Approve
                    </button>

                    <button
                      onClick={() =>
                        rejectRecord(record.id)
                      }
                    >
                      Reject
                    </button>

                  </td>

                </tr>

              ))}

            </tbody>

          </table>

        </div>

        {/* Audit Logs */}

        <div className="table-card">

          <h2>Audit Logs</h2>

          <table>

            <thead>

              <tr>

                <th>ID</th>
                <th>Record</th>
                <th>Action</th>
                <th>User</th>

              </tr>

            </thead>

            <tbody>

              {auditLogs.map((log) => (

                <tr key={log.id}>

                  <td>{log.id}</td>

                  <td>{log.record_id}</td>

                  <td>{log.action}</td>

                  <td>{log.changed_by}</td>

                </tr>

              ))}

            </tbody>

          </table>

        </div>

      </div>

    </div>
  );
}