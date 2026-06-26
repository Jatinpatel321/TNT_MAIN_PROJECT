import React, { Suspense, lazy } from 'react';
import { createBrowserRouter, RouterProvider, Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { Layout } from '../components/layout/Layout';
import { LoadingSkeleton } from '../components/ui/LoadingSpinner';
import { ErrorBoundary } from '../components/ui/ErrorBoundary';


// Lazy load all pages
const Login = lazy(() => import('../pages/auth/Login'));
const Dashboard = lazy(() => import('../pages/dashboard/Dashboard'));
const VendorList = lazy(() => import('../pages/vendors/VendorList'));
const VendorDetail = lazy(() => import('../pages/vendors/VendorDetail'));
const UserManagement = lazy(() => import('../pages/users/UserManagement'));
const OrdersHub = lazy(() => import('../pages/orders/OrdersHub'));
const OrderDetail = lazy(() => import('../pages/orders/OrderDetail'));
const Complaints = lazy(() => import('../pages/complaints/Complaints'));
const VoucherManager = lazy(() => import('../pages/rewards/VoucherManager'));
const OffPeakPolicy = lazy(() => import('../pages/rewards/OffPeakPolicy'));
const FacultyPolicy = lazy(() => import('../pages/policies/FacultyPolicy'));
const UniversityPolicy = lazy(() => import('../pages/policies/UniversityPolicy'));
const HolidayCalendar = lazy(() => import('../pages/calendar/HolidayCalendar'));
const AIIntelligence = lazy(() => import('../pages/ai/AIIntelligence'));
const StationeryJobs = lazy(() => import('../pages/stationery/StationeryJobs'));
const Ledger = lazy(() => import('../pages/ledger/Ledger'));
const Announcements = lazy(() => import('../pages/announcements/Announcements'));
const BackupRecovery = lazy(() => import('../pages/backup/BackupRecovery'));
const AuditLogs = lazy(() => import('../pages/audit/AuditLogs'));
const ConflictResolution = lazy(() => import('../pages/conflicts/ConflictResolution'));
const Settings = lazy(() => import('../pages/settings/Settings'));

// Page loading fallback
function PageLoader() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-4">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="skeleton h-28 rounded-xl" />
        ))}
      </div>
      <div className="skeleton h-64 rounded-xl" />
      <div className="skeleton h-96 rounded-xl" />
    </div>
  );
}

// Protected Route — checks auth + admin role
function ProtectedRoute() {
  const { isAuthenticated, token, user } = useAuthStore();

  if (!isAuthenticated || !token || !user) {
    return <Navigate to="/login" replace />;
  }

  if (!['admin', 'super_admin', 'ADMIN', 'SUPER_ADMIN'].includes(user.role)) {
    return (
      <div className="min-h-screen bg-[#0F0F1A] flex items-center justify-center">
        <div className="tnt-card max-w-md text-center">
          <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl">🚫</span>
          </div>
          <h2 className="text-xl font-bold text-[#F1F0FF] mb-2">Access Denied</h2>
          <p className="text-[#9B9BC4]">This area is restricted to administrators only.</p>
          <button
            onClick={() => { useAuthStore.getState().logout(); window.location.href = '/login'; }}
            className="btn-primary mt-4 mx-auto"
          >
            Return to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <Layout>
      <ErrorBoundary>
        <Suspense fallback={<PageLoader />}>
          <Outlet />
        </Suspense>
      </ErrorBoundary>
    </Layout>
  );
}

// Rewards layout with sub-tabs (Vouchers | Off-Peak)
function RewardsLayout() {
  return <Outlet />;
}

// Policies layout
function PoliciesLayout() {
  return <Outlet />;
}

const router = createBrowserRouter([
  {
    path: '/login',
    element: (
      <Suspense fallback={<div className="min-h-screen bg-[#0F0F1A]" />}>
        <Login />
      </Suspense>
    ),
  },
  {
    path: '/',
    element: <ProtectedRoute />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'users', element: <UserManagement /> },
      {
        path: 'vendors',
        children: [
          { index: true, element: <VendorList /> },
          { path: ':id', element: <VendorDetail /> },
        ],
      },
      {
        path: 'orders',
        children: [
          { index: true, element: <OrdersHub /> },
          { path: ':id', element: <OrderDetail /> },
        ],
      },
      { path: 'complaints', element: <Complaints /> },
      {
        path: 'rewards',
        element: <RewardsLayout />,
        children: [
          { index: true, element: <VoucherManager /> },
          { path: 'off-peak', element: <OffPeakPolicy /> },
        ],
      },
      {
        path: 'policies',
        element: <PoliciesLayout />,
        children: [
          { index: true, element: <FacultyPolicy /> },
          { path: 'university', element: <UniversityPolicy /> },
          { path: 'calendar', element: <HolidayCalendar /> },
        ],
      },
      { path: 'ai', element: <AIIntelligence /> },
      { path: 'stationery', element: <StationeryJobs /> },
      { path: 'ledger', element: <Ledger /> },
      { path: 'announcements', element: <Announcements /> },
      { path: 'audit-logs', element: <AuditLogs /> },
      { path: 'conflicts', element: <ConflictResolution /> },
      { path: 'backup', element: <BackupRecovery /> },
      { path: 'settings', element: <Settings /> },
      { path: '*', element: <Navigate to="/dashboard" replace /> },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
