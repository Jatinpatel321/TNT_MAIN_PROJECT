/**
 * Centralized Currency Formatter
 * 
 * Formats a given amount in rupees or paise into a standard INR display string.
 * Automatically prevents duplicate currency symbols (e.g. ₹₹100) if the value
 * is already formatted or has a prepended symbol.
 */
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

export function formatRupees(rupees: number): string {
  return formatCurrency(rupees, { inputType: 'rupees', showDecimals: true });
}
