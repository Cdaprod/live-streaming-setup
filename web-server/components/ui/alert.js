import React from 'react';

export function Alert({ title, description, type = 'info' }) {
  const typeStyles = {
    info: 'bg-blue-100 text-blue-800 border-blue-300',
    success: 'bg-green-100 text-green-800 border-green-300',
    warning: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    error: 'bg-red-100 text-red-800 border-red-300',
  };

  return (
    <div className={`border-l-4 p-4 ${typeStyles[type] || typeStyles.info}`} role="alert">
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>{description}</AlertDescription>
    </div>
  );
}

export function AlertTitle({ children }) {
  return <strong className="block font-medium">{children}</strong>;
}

export function AlertDescription({ children }) {
  return <span className="block mt-1">{children}</span>;
}