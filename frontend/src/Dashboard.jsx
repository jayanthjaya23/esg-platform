import React, {
  useEffect,
  useState
} from 'react';

import axios from 'axios';

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
  ResponsiveContainer
} from 'recharts';


export default function Dashboard() {

  const [records, setRecords] = useState([]);


  useEffect(() => {

    fetchEmissions();

  }, []);


  const fetchEmissions = async () => {

    try {

      const response = await axios.get(
        'http://127.0.0.1:8000/api/emissions/'
      );

      setRecords(response.data);

    } catch (error) {

      console.error(error);
    }
  };


  const approveRecord = async (id) => {

    await axios.post(
      `http://127.0.0.1:8000/api/approve/${id}/`
    );

    fetchEmissions();
  };


  const rejectRecord = async (id) => {

    await axios.post(
      `http://127.0.0.1:8000/api/reject/${id}/`
    );

    fetchEmissions();
  };


  // METRICS

  const totalEmissions = records.reduce(
    (sum, r) => sum + r.co2e_kg,
    0
  );

  const approvedCount = records.filter(
    r => r.approval_status === 'approved'
  ).length;

  const warningCount = records.filter(
    r => r.validation_status === 'warning'
  ).length;


  // PIE CHART

  const scopeData = [

    {
      name: 'Scope 1',
      value: records.filter(
        r => r.scope === 'scope_1'
      ).length
    },

    {
      name: 'Scope 2',
      value: records.filter(
        r => r.scope === 'scope_2'
      ).length
    },

    {
      name: 'Scope 3',
      value: records.filter(
        r => r.scope === 'scope_3'
      ).length
    },
  ];


  // BAR CHART

  const sourceData = [

    {
      name: 'SAP',
      emissions: records
        .filter(r => r.source_type === 'sap')
        .reduce((sum, r) => sum + r.co2e_kg, 0)
    },

    {
      name: 'Utility',
      emissions: records
        .filter(r => r.source_type === 'utility')
        .reduce((sum, r) => sum + r.co2e_kg, 0)
    },

    {
      name: 'Travel',
      emissions: records
        .filter(r => r.source_type === 'travel')
        .reduce((sum, r) => sum + r.co2e_kg, 0)
    },
  ];


  const COLORS = [
    '#2563eb',
    '#16a34a',
    '#dc2626'
  ];


  return (

    <div>

      {/* TOPBAR */}

      <div className="topbar">

        <div>

          <h1>
            ESG Analytics Dashboard
          </h1>

          <div className="topbar-subtitle">
            Enterprise Emissions Intelligence Platform
          </div>

        </div>

      </div>


      {/* METRIC CARDS */}

      <div className="metrics-grid">

        <div className="metric-card">

          <div className="metric-label">
            Total Records
          </div>

          <div className="metric-value">
            {records.length}
          </div>

        </div>


        <div className="metric-card">

          <div className="metric-label">
            Total CO₂e
          </div>

          <div className="metric-value">
            {totalEmissions.toFixed(0)} kg
          </div>

        </div>


        <div className="metric-card">

          <div className="metric-label">
            Approved Records
          </div>

          <div className="metric-value">
            {approvedCount}
          </div>

        </div>


        <div className="metric-card">

          <div className="metric-label">
            Validation Warnings
          </div>

          <div className="metric-value">
            {warningCount}
          </div>

        </div>

      </div>


      {/* CHARTS */}

      <div className="charts-grid">

        <div className="chart-card">

          <h3>
            Scope Distribution
          </h3>

          <ResponsiveContainer
            width="100%"
            height={320}
          >

            <PieChart>

              <Pie
                data={scopeData}
                dataKey="value"
                outerRadius={110}
                label
              >

                {scopeData.map((entry, index) => (

                  <Cell
                    key={index}
                    fill={COLORS[index]}
                  />

                ))}

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
            height={320}
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


      {/* TABLE */}

      <div className="table-card">

        <h2>
          Emission Records
        </h2>

        <div className="table-wrapper">

          <table>

            <thead>

              <tr>

                <th>ID</th>

                <th>Source</th>

                <th>Scope</th>

                <th>Category</th>

                <th>Activity</th>

                <th>CO₂e</th>

                <th>Validation</th>

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

                  <td>
                    {record.activity_value}
                    {' '}
                    {record.activity_unit}
                  </td>

                  <td>
                    {record.co2e_kg}
                  </td>

                  <td>

                    <span
                      className={
                        record.validation_status === 'warning'
                          ? 'badge-warning'
                          : 'badge-valid'
                      }
                    >
                      {record.validation_status}
                    </span>

                  </td>

                  <td>

                    <span
                      className={
                        record.approval_status === 'approved'
                          ? 'badge-approved'
                          : record.approval_status === 'rejected'
                          ? 'badge-rejected'
                          : 'badge-warning'
                      }
                    >
                      {record.approval_status}
                    </span>

                  </td>

                  <td>

                    <button
                      className="btn-approve"
                      onClick={() =>
                        approveRecord(record.id)
                      }
                    >
                      Approve
                    </button>


                    <button
                      className="btn-reject"
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

      </div>

    </div>
  );
}