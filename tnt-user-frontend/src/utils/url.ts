import { API_BASE_URL } from './constants';

export function toAbsoluteUrl(uri?: string | null): string | null {
  if (!uri) return null;
  const trimmed = String(uri).trim();
  if (!trimmed) return null;

  // Already absolute (remote or local scheme)
  if (/^(https?:)?\/\//i.test(trimmed)) return trimmed;
  if (/^(file|content):/i.test(trimmed)) return trimmed;

  // Backend often returns "/uploads/..."; make it absolute.
  if (trimmed.startsWith('/')) return `${API_BASE_URL}${trimmed}`;
  return `${API_BASE_URL}/${trimmed}`;
}
