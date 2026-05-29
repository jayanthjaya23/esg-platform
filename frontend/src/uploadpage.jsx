import React, { useState } from 'react';
import axios from 'axios';

export default function UploadPage() {

  const [sourceType, setSourceType] = useState('sap');

  const [file, setFile] = useState(null);

  const [message, setMessage] = useState('');

  const handleUpload = async () => {

    if (!file) {

      alert('Please select a file');

      return;
    }

    const formData = new FormData();

    formData.append('source_type', sourceType);

    formData.append('file', file);

    try {

      const response = await axios.post(
        'http://127.0.0.1:8000/api/upload/',
        formData
      );

      setMessage(response.data.message);

    } catch (error) {

      console.error(error);

      setMessage('Upload failed');
    }
  };

  return (
    <div style={{ padding: '20px' }}>

      <h2>Upload ESG CSV</h2>

      <select
        value={sourceType}
        onChange={(e) => setSourceType(e.target.value)}
      >
        <option value="sap">SAP</option>
        <option value="utility">Utility</option>
        <option value="travel">Travel</option>
      </select>

      <br /><br />

      <input
        type="file"
        onChange={(e) => setFile(e.target.files[0])}
      />

      <br /><br />

      <button onClick={handleUpload}>
        Upload
      </button>

      <p>{message}</p>

    </div>
  );
}