import React from 'react';

interface LoadingIndicatorProps {
  // No specific props for now
}

const LoadingIndicator: React.FC<LoadingIndicatorProps> = () => {
  return (
    <div className="flex justify-center items-center py-4">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-gray-100"></div>
      <span className="ml-3 text-gray-700 dark:text-gray-300">Loading...</span>
    </div>
  );
};

export default LoadingIndicator;

