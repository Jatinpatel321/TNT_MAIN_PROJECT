import React from 'react';
import { cn } from '../../utils/cn';
import {
  ORDER_STATUS_COLORS,
  ORDER_STATUS_LABELS,
  VENDOR_STATUS_COLORS,
  COMPLAINT_STATUS_COLORS,
  COMPLAINT_STATUS_LABELS,
  PRINT_JOB_STATUS_COLORS,
  VENDOR_TYPE_COLORS,
  VENDOR_TYPE_LABELS,
  ROLE_COLORS,
  ROLE_LABELS,
} from '../../utils/constants';
import type { OrderStatus, VendorStatus, ComplaintStatus, PrintJobStatus } from '../../types';

type StatusType =
  | { type: 'order'; status: OrderStatus }
  | { type: 'vendor'; status: VendorStatus }
  | { type: 'complaint'; status: ComplaintStatus }
  | { type: 'print_job'; status: PrintJobStatus }
  | { type: 'vendor_type'; status: 'food' | 'stationery' }
  | { type: 'role'; status: string }
  | { type: 'active'; status: boolean }
  | { type: 'custom'; label: string; className: string };

type Props = StatusType & { className?: string };

export function StatusBadge(props: Props) {
  let label = '';
  let colorClass = '';

  if (props.type === 'order') {
    label = ORDER_STATUS_LABELS[props.status] || props.status;
    colorClass = ORDER_STATUS_COLORS[props.status] || 'bg-gray-500/20 text-gray-400';
  } else if (props.type === 'vendor') {
    label = props.status.charAt(0).toUpperCase() + props.status.slice(1);
    colorClass = VENDOR_STATUS_COLORS[props.status] || 'bg-gray-500/20 text-gray-400';
  } else if (props.type === 'complaint') {
    label = COMPLAINT_STATUS_LABELS[props.status] || props.status;
    colorClass = COMPLAINT_STATUS_COLORS[props.status] || 'bg-gray-500/20 text-gray-400';
  } else if (props.type === 'print_job') {
    label = props.status.charAt(0).toUpperCase() + props.status.slice(1);
    colorClass = PRINT_JOB_STATUS_COLORS[props.status] || 'bg-gray-500/20 text-gray-400';
  } else if (props.type === 'vendor_type') {
    label = VENDOR_TYPE_LABELS[props.status];
    colorClass = VENDOR_TYPE_COLORS[props.status];
  } else if (props.type === 'role') {
    const roleKey = props.status as keyof typeof ROLE_LABELS;
    label = ROLE_LABELS[roleKey] || props.status;
    colorClass = ROLE_COLORS[roleKey] || 'bg-gray-500/20 text-gray-400';
  } else if (props.type === 'active') {
    label = props.status ? 'Active' : 'Blocked';
    colorClass = props.status
      ? 'bg-green-500/20 text-green-400 border-green-500/30'
      : 'bg-red-500/20 text-red-400 border-red-500/30';
  } else if (props.type === 'custom') {
    label = props.label;
    colorClass = props.className;
  }

  return (
    <span className={cn(
      'badge border',
      colorClass,
      props.className
    )}>
      {label}
    </span>
  );
}
