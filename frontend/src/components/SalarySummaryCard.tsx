import React from 'react';

interface SalarySummaryCardProps {
    basicSalary: number | null | undefined;
    allowances?: Record<string, number> | null | undefined;
    deductions?: number | null | undefined;
    netSalary: number | null | undefined;
    hideDetails?: boolean;
}

const formatCurrency = (amount: number | undefined): string => {
  if (amount === undefined || amount === null) {
    return 'N/A';
  }
  return `AED ${amount.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
};

const SalarySummaryCard: React.FC<SalarySummaryCardProps> = ({
  basicSalary,
  allowances,
  deductions,
  netSalary,
  hideDetails = false, // Set default to false to show details by default
}) => {
  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 w-full max-w-md mx-auto mt-6">
      <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-4 text-center">Salary Slip Summary</h3>

      <div className="space-y-3 mb-4">
        <div className="flex justify-between items-center">
          <span className="text-gray-700 dark:text-gray-300 font-medium">Basic Salary</span>
          <span className="text-gray-900 dark:text-white font-semibold">{formatCurrency(basicSalary)}</span>
        </div>

        {!hideDetails && (
          <>
            {allowances && Object.keys(allowances).length > 0 ? (
              <div className="space-y-2">
                <p className="text-gray-700 dark:text-gray-300 font-semibold">Allowances</p>
                {Object.entries(allowances).map(([key, value]) => (
                  <div key={key} className="flex justify-between items-center pl-4">
                    <span className="text-gray-600 dark:text-gray-400 capitalize">
                      {key.replace(/_/g, ' ')}
                    </span>
                    <span className="text-gray-900 dark:text-white font-medium">
                      {formatCurrency(value)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex justify-between items-center">
                <span className="text-gray-700 dark:text-gray-300 font-medium">Allowances</span>
                <span className="text-gray-500 dark:text-gray-400 text-sm">Not found</span>
              </div>
            )}

            {deductions !== undefined && deductions !== null ? (
              <div className="flex justify-between items-center">
                <span className="text-red-600 dark:text-red-400 font-medium">Deductions</span>
                <span className="text-red-600 dark:text-red-400 font-semibold">- {formatCurrency(Math.abs(deductions))}</span>
              </div>
            ) : (
              <div className="flex justify-between items-center">
                <span className="text-gray-700 dark:text-gray-300 font-medium">Deductions</span>
                <span className="text-gray-500 dark:text-gray-400 text-sm">Not found</span>
              </div>
            )}
          </>
        )}
      </div>

      <div className="border-t border-gray-300 dark:border-gray-600 my-4"></div>

      <div className="flex justify-between items-center">
        <span className="text-lg text-gray-800 dark:text-gray-200 font-bold">Net Salary</span>
        <span className="text-xl text-green-600 dark:text-green-400 font-extrabold">{formatCurrency(netSalary)}</span>
      </div>
    </div>
  );
};

export default SalarySummaryCard;

