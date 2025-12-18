import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { fetchUserProfile, updateUserProfile, uploadDocument, fetchUserDocuments, deleteDocument } from '../services/profile';
import { User, Document } from '../types';
import SalarySummaryCard from '../components/SalarySummaryCard'; // Import the SalarySummaryCard

const ProfilePage: React.FC = () => {
  const { user, logout } = useAuth();
  const [profile, setProfile] = useState<User | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [editMode, setEditMode] = useState(false);
  const [formData, setFormData] = useState<Partial<User>>({});
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      loadProfileAndDocuments();
    }
  }, [user]);

  const loadProfileAndDocuments = async () => {
    setLoading(true);
    setError(null);
    try {
      const userProfile = await fetchUserProfile();
      setProfile(userProfile);
      setFormData(userProfile);
      const userDocuments = await fetchUserDocuments();
      setDocuments(userDocuments);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load profile or documents.');
    } finally {
      setLoading(false);
    }
  };

  const handleProfileUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    try {
      if (profile) {
        await updateUserProfile(profile.id, formData);
        setEditMode(false);
        setSuccess('Profile updated successfully!');
        loadProfileAndDocuments(); // Reload data after update
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update profile.');
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleDocumentUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (!selectedFile) {
      setError('Please select a file to upload.');
      return;
    }

    try {
      await uploadDocument(selectedFile);
      setSuccess('Document uploaded successfully!');
      setSelectedFile(null); // Clear selected file
      loadProfileAndDocuments(); // Reload documents
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload document.');
    }
  };

  const handleDocumentDelete = async (documentId: number) => {
    setError(null);
    setSuccess(null);
    try {
      await deleteDocument(documentId);
      setSuccess('Document deleted successfully!');
      loadProfileAndDocuments(); // Reload documents
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete document.');
    }
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center dark:bg-gray-900 text-white">Loading profile...</div>;
  }

  if (error && !profile) {
    return <div className="min-h-screen flex items-center justify-center dark:bg-gray-900 text-red-500">{error}</div>;
  }

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 p-8">
      <div className="max-w-4xl mx-auto bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">My Profile</h1>
          <div className="flex space-x-4">
            <button
              onClick={() => setEditMode(!editMode)}
              className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline dark:bg-blue-600 dark:hover:bg-blue-800"
            >
              {editMode ? 'Cancel Edit' : 'Edit Profile'}
            </button>
            <button
              onClick={logout}
              className="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline dark:bg-red-600 dark:hover:bg-red-800"
            >
              Logout
            </button>
          </div>
        </div>

        {error && <p className="text-red-500 text-center mb-4">{error}</p>}
        {success && <p className="text-green-500 text-center mb-4">{success}</p>}

        <div className="mb-8">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">Personal Information</h2>
          {profile && ( // Ensure profile is not null before accessing
            <form onSubmit={handleProfileUpdate} className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-gray-700 dark:text-gray-300 text-sm font-bold mb-2">Email:</label>
                <input
                  type="email"
                  className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline dark:bg-gray-700 dark:text-white dark:border-gray-600"
                  value={profile.email}
                  disabled
                />
              </div>
              <div>
                <label className="block text-gray-700 dark:text-gray-300 text-sm font-bold mb-2">First Name:</label>
                <input
                  type="text"
                  className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline dark:bg-gray-700 dark:text-white dark:border-gray-600"
                  value={editMode ? formData.first_name || '' : profile.first_name || ''}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  disabled={!editMode}
                />
              </div>
              <div>
                <label className="block text-gray-700 dark:text-gray-300 text-sm font-bold mb-2">Last Name:</label>
                <input
                  type="text"
                  className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline dark:bg-gray-700 dark:text-white dark:border-gray-600"
                  value={editMode ? formData.last_name || '' : profile.last_name || ''}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  disabled={!editMode}
                />
              </div>
              <div>
                <label className="block text-gray-700 dark:text-gray-300 text-sm font-bold mb-2">Phone Number:</label>
                <input
                  type="text"
                  className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline dark:bg-gray-700 dark:text-white dark:border-gray-600"
                  value={editMode ? formData.phone_number || '' : profile.phone_number || ''}
                  onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                  disabled={!editMode}
                />
              </div>
              {editMode && (
                <div className="md:col-span-2 flex justify-end">
                  <button
                    type="submit"
                    className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline dark:bg-green-600 dark:hover:bg-green-800"
                  >
                    Save Profile
                  </button>
                </div>
              )}
            </form>
          )}
        </div>

        <div className="mb-8">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">My Documents</h2>
          <form onSubmit={handleDocumentUpload} className="flex items-center space-x-4 mb-4">
            <input
              type="file"
              className="block w-full text-sm text-gray-500
              file:mr-4 file:py-2 file:px-4
              file:rounded-full file:border-0
              file:text-sm file:font-semibold
              file:bg-blue-50 file:text-blue-700
              hover:file:bg-blue-100 dark:file:bg-blue-800 dark:file:text-blue-200"
              onChange={handleFileChange}
            />
            <button
              type="submit"
              className="bg-indigo-500 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline dark:bg-indigo-600 dark:hover:bg-indigo-800"
              disabled={!selectedFile}
            >
              Upload Document
            </button>
          </form>

          {documents.length === 0 ? (
            <p className="text-gray-600 dark:text-gray-400">No documents uploaded yet.</p>
          ) : (
            <div className="space-y-4">
              {documents.map((doc) => (
                <div key={doc.id} className="bg-gray-50 dark:bg-gray-700 p-4 rounded-md shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-gray-800 dark:text-gray-200 font-semibold">{doc.file_name}</span>
                    <button
                      onClick={() => handleDocumentDelete(doc.id)}
                      className="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-600 ml-4"
                    >
                      Delete
                    </button>
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                    Uploaded on: {new Date(doc.uploaded_at).toLocaleDateString()}
                  </p>
                  {doc.extracted_salary_data && (
                    <SalarySummaryCard
                      basicSalary={doc.extracted_salary_data.basic_salary}
                      allowances={doc.extracted_salary_data.allowances}
                      deductions={doc.extracted_salary_data.deductions}
                      netSalary={doc.extracted_salary_data.net_salary}
                      hideDetails={true}
                    />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
