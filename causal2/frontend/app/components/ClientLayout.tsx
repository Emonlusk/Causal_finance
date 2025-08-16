'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';

export default function ClientLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div>Loading...</div>;
  }

  return (
    <nav className="bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <Image
                className="h-8 w-8"
                src="/logo.svg"
                alt="Causal Finance"
                width={32}
                height={32}
              />
              <span className="ml-2 text-xl font-semibold">
                Causal Finance
              </span>
            </div>
          </div>
          <div className="flex items-center">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
              <span className="h-2 w-2 mr-1 bg-green-400 rounded-full"></span>
              Live Market Data
            </span>
          </div>
        </div>
      </div>
      {children}
    </nav>
  );
}
