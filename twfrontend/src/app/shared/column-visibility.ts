import { effect, signal } from '@angular/core';

type VisibilityMap = Record<string, boolean>;

const hasStorage = () => typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';

const loadVisibility = <T extends VisibilityMap>(storageKey: string, defaults: T): T => {
  if (!hasStorage()) {
    return { ...defaults };
  }
  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) {
      return { ...defaults };
    }
    const parsed = JSON.parse(raw) as Partial<T>;
    return { ...defaults, ...parsed };
  } catch {
    return { ...defaults };
  }
};

const saveVisibility = (storageKey: string, value: VisibilityMap): void => {
  if (!hasStorage()) {
    return;
  }
  try {
    window.localStorage.setItem(storageKey, JSON.stringify(value));
  } catch {
    // Ignore storage failures (private mode, quota, etc.).
  }
};

export const createColumnVisibility = <T extends VisibilityMap>(storageKey: string, defaults: T) => {
  const visibility = signal<T>(loadVisibility(storageKey, defaults));

  effect(() => {
    saveVisibility(storageKey, visibility());
  });

  const setVisibility = (key: keyof T, value: boolean): void => {
    visibility.update((current) => ({ ...current, [key]: value }));
  };

  const resetVisibility = (): void => {
    visibility.set({ ...defaults });
  };

  return {
    visibility,
    setVisibility,
    resetVisibility
  };
};
