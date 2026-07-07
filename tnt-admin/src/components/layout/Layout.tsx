import React from 'react';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { EmergencyBanner } from '../ui/EmergencyBanner';
import { useUIStore } from '../../store/uiStore';
import { cn } from '../../utils/cn';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { sidebarOpen } = useUIStore();

  return (
    <div className="min-h-screen bg-[#F7F8FC] text-[#111827]">
      <EmergencyBanner />
      <Sidebar />

      <div
        className={cn(
          'min-h-screen transition-[margin] duration-300 ease-in-out',
          sidebarOpen ? 'ml-[260px]' : 'ml-[64px]'
        )}
      >
        <TopBar />

        <main className="pt-16 min-h-screen bg-[#F7F8FC]">
          <div className="p-6 page-enter">{children}</div>
        </main>
      </div>
    </div>
  );
}