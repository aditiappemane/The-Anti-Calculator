import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import SalarySummaryCard from '../components/SalarySummaryCard'; // Import the new component

const UploadSalarySlipPage: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [extractedData, setExtractedData] = useState<any>(null); // To store extracted data
  const { token } = useAuth();
  const navigate = useNavigate();

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedFile(event.target.files[0]);
      setMessage('');
      setError('');
      setExtractedData(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file first.');
      return;
    }

    if (!token) {
      setError('You must be logged in to upload documents.');
      navigate('/login');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    setMessage('Uploading and processing your document...');
    setError('');
    setExtractedData(null);

    try {
      const response = await axios.post(
        `${import.meta.env.VITE_BACKEND_URL}/api/upload-salary-slip`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
            'Authorization': `Bearer ${token}`,
          },
        }
      );
      setMessage('Document processed successfully!');
      setExtractedData(response.data); // Assuming backend sends back extracted data
      console.log('Full Response Data:', response.data);
      console.log('Extracted Salary Data:', response.data?.extracted_salary_data);
      console.log('Allowances:', response.data?.extracted_salary_data?.allowances);
      console.log('Deductions:', response.data?.extracted_salary_data?.deductions);
    } catch (err: any) {
      console.error('Upload error:', err);
      setError(err.response?.data?.detail || 'Failed to upload and process document.');
      setMessage('');
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-green-400 to-teal-600 p-4">
      <header className="w-full max-w-md text-center mb-8">
        <h1 className="text-5xl font-extrabold text-white drop-shadow-lg">Upload Salary Slip</h1>
        <p className="text-white text-opacity-80 mt-2 text-lg">
          Don't worry about typing. Just upload your salary slip, and I'll run the numbers.
        </p>
      </header>
      <div className="bg-white dark:bg-gray-800 p-8 rounded-xl shadow-2xl w-full max-w-md border border-gray-200 dark:border-gray-700 transform hover:scale-105 transition-transform duration-300">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-8 text-center">
          Upload Your Document
        </h2>
        <div className="mb-6">
          <label className="block text-gray-700 dark:text-gray-300 text-sm font-semibold mb-2" htmlFor="salarySlip">
            Salary Slip (Image or PDF)
          </label>
          <input
            type="file"
            id="salarySlip"
            accept=".png,.jpg,.jpeg,.pdf"
            onChange={handleFileChange}
            className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 dark:text-gray-400 focus:outline-none dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
        </div>
        <button
          onClick={handleUpload}
          disabled={!selectedFile}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:bg-blue-700 dark:hover:bg-blue-800 dark:focus:ring-blue-600 transition-all duration-300 transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Upload and Extract
        </button>

        {message && <p className="text-green-500 text-center mt-4">{message}</p>}
        {error && <p className="text-red-500 text-center mt-4">{error}</p>}

        {extractedData && extractedData.extracted_salary_data && (
          <>
            <SalarySummaryCard
              basicSalary={extractedData.extracted_salary_data.basic_salary}
              allowances={extractedData.extracted_salary_data.allowances}
              deductions={extractedData.extracted_salary_data.deductions}
              netSalary={extractedData.extracted_salary_data.net_salary}
            />
            <p className="text-center text-gray-700 dark:text-gray-300 text-md mt-6">
              I’ve extracted your salary details automatically. You don’t need to type anything.
            </p>
          </>
        )}

        <p className="text-center text-gray-600 dark:text-gray-400 text-sm mt-6">
          <a
            href="/profile"
            className="font-bold text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200 transition-colors duration-200"
          >
            View your uploaded documents on the profile page
          </a>
        </p>
      </div>
    </div>
  );
};

export default UploadSalarySlipPage;

