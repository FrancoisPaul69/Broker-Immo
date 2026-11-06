import { useEffect, useState } from 'react'
import BrokerApp from '@/components/BrokerApp'
import type { Asset, DashboardSummary, Owner } from '@/types/broker'
interface DatasetResponse { demo: boolean; summary: DashboardSummary; assets: Asset[]; owners: Owner[] }
export default function App() {
  const [dataset, setDataset] = useState<DatasetResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    const controller = new AbortController()
    fetch(`${import.meta.env.VITE_API_BASE_URL ?? ''}/api/dataset`, { signal: controller.signal })
      .then((response) => { if (!response.ok) throw new Error(`Erreur API ${response.status}`); return response.json() as Promise<DatasetResponse> })
      .then(setDataset).catch((reason: unknown) => { if (reason instanceof DOMException && reason.name === 'AbortError') return; setError(reason instanceof Error ? reason.message : 'Erreur inconnue') })
    return () => controller.abort()
  }, [])
  if (error) return <main className="startup-state"><strong>Impossible de charger Broker Immo.</strong><span>{error}</span></main>
  if (!dataset) return <main className="startup-state"><strong>Chargement des opportunités…</strong></main>
  return <BrokerApp assets={dataset.assets} owners={dataset.owners} summary={dataset.summary} demo={dataset.demo} />
}
