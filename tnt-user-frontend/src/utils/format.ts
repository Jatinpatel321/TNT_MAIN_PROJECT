export function formatCurrency(
  value: string | number | undefined | null,
  options?: { inputType?: 'paise' | 'rupees'; showDecimals?: boolean }
): string {
  if (value === undefined || value === null) {
    return '₹0.00';
  }

  // Handle already-formatted strings containing ₹
  if (typeof value === 'string' && value.includes('₹')) {
    return value.replace(/₹+/g, '₹');
  }

  let amount = 0;
  // The API now returns every amount in rupees; 'paise' is kept only for
  // call sites that still hold a raw Razorpay-boundary paise value.
  const inputType = options?.inputType ?? 'rupees';
  const showDecimals = options?.showDecimals ?? true;

  if (typeof value === 'string') {
    amount = parseFloat(value.replace(/[^0-9.-]/g, '')) || 0;
  } else {
    amount = value;
  }

  if (inputType === 'paise') {
    amount = amount / 100;
  }

  const formattedAmount = showDecimals ? amount.toFixed(2) : amount.toFixed(0);
  return `₹${formattedAmount}`;
}

/** Format a rupee amount (API values are always rupees now). */
export function formatMoney(rupees: number): string {
  return formatCurrency(rupees, { inputType: 'rupees', showDecimals: true });
}

export function formatTimeRange(startIso: string, endIso: string): string {
  const start = new Date(startIso);
  const end = new Date(endIso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(start.getHours())}:${pad(start.getMinutes())} - ${pad(end.getHours())}:${pad(end.getMinutes())}`;
}
