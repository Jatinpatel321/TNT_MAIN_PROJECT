import { apiClient } from './apiClient';
import type { SearchResponse, SearchFilters } from '../types/models';

export async function search(query: string, filters: SearchFilters = {}): Promise<SearchResponse> {
  const params: Record<string, any> = { q: query };

  if (filters.type) params.type = filters.type;
  if (filters.category) params.category = filters.category;
  if (filters.price_min != null) params.price_min = filters.price_min;
  if (filters.price_max != null) params.price_max = filters.price_max;
  if (filters.min_rating != null) params.min_rating = filters.min_rating;
  if (filters.availability != null) params.availability = filters.availability;
  if (filters.prep_time_max != null) params.prep_time_max = filters.prep_time_max;
  if (filters.sort) params.sort = filters.sort;

  const res = await apiClient.get('/search', { params });
  return res.data as SearchResponse;
}

export async function searchSuggestions(query: string, limit = 8): Promise<string[]> {
  const res = await apiClient.get('/search/suggestions', { params: { q: query, limit } });
  return res.data as string[];
}
