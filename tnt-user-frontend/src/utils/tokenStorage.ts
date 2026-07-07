import { STORAGE_KEYS } from './constants';
import { getItem, removeItem, setItem } from './storage';

export async function saveToken(token: string): Promise<void> {
  await setItem(STORAGE_KEYS.accessToken, token);
}

export async function getToken(): Promise<string | null> {
  return getItem(STORAGE_KEYS.accessToken);
}

export async function removeToken(): Promise<void> {
  await removeItem(STORAGE_KEYS.accessToken);
}
