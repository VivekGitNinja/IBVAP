import { useState, useEffect } from 'react';

export type StateCreator<T> = (
  set: (partial: Partial<T> | ((state: T) => Partial<T>)) => void,
  get: () => T
) => T;

export function create<T>(stateCreator: StateCreator<T>) {
  let state: T;
  const listeners = new Set<() => void>();

  const setState = (partial: Partial<T> | ((state: T) => Partial<T>)) => {
    const nextState = typeof partial === 'function' ? (partial as any)(state) : partial;
    if (nextState !== state) {
      state = Object.assign({}, state, nextState);
      listeners.forEach((listener) => listener());
    }
  };

  const getState = () => state;

  state = stateCreator(setState, getState);

  const useStore = <U = T>(selector?: (state: T) => U): U => {
    const [, forceUpdate] = useState({});
    useEffect(() => {
      const listener = () => forceUpdate({});
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    }, []);
    return selector ? selector(state) : (state as any);
  };

  useStore.getState = getState;
  useStore.setState = setState;
  useStore.subscribe = (listener: () => void) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  };

  return useStore;
}
