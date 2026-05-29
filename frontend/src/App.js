import React from 'react';

import Dashboard from './Dashboard';

import './App.css';


function App() {

  return (

    <div className="app-layout">

      {/* SIDEBAR */}

      <div className="sidebar">

        <div className="logo">
          🌍 ESG Platform
        </div>

        <div className="sidebar-menu">

          <div className="sidebar-item">
            Dashboard
          </div>

          <div className="sidebar-item">
            Uploads
          </div>

          <div className="sidebar-item">
            Analytics
          </div>

          <div className="sidebar-item">
            Audit Logs
          </div>

          <div className="sidebar-item">
            ESG Reports
          </div>

        </div>

      </div>


      {/* MAIN */}

      <div className="main-content">

        <Dashboard />

      </div>

    </div>
  );
}

export default App;