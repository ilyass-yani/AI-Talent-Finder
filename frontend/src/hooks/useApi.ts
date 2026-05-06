"use client";
import { useState, useEffect, useCallback } from "react";
import { AxiosResponse } from "axios";

export function useApi<T>(apiFn: () => Promise<AxiosResponse<T>>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true); setError(null);
    try { const res = await apiFn(); setData(res.data); }
    catch (e: unknown) { setError(e instanceof Error ? e.message : "Erreur inconnue"); }
    finally { setLoading(false); }
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { fetch(); }, [fetch]);

  return { data, loading, error, refetch: fetch };
}
