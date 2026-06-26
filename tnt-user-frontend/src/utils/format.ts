export function formatMoneyPaise(paise: number): string {
  const rupees = (paise ?? 0) / 100;
  return `₹${rupees.toFixed(2)}`;
}

export function formatTimeRange(startIso: string, endIso: string): string {
  const start = new Date(startIso);
  const end = new Date(endIso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(start.getHours())}:${pad(start.getMinutes())} - ${pad(end.getHours())}:${pad(end.getMinutes())}`;
}
