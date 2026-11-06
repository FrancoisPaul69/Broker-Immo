export interface Breakdown {
  critere: string
  points: number
  points_max: number
  detail: string
}

export interface Asset {
  id: string | number
  rank: number
  numero_parcelle: string
  adresse_brute: string
  ville: string
  code_postal: string
  type_actif: string
  type_actif_confidence: string
  type_actif_indices: string[]
  surface_bati: number | null
  contenance: number | null
  prix_derniere_mutation: number | null
  date_derniere_mutation: string | null
  usage_batiment: string | null
  nature_batiment: string | null
  asset_score: number
  owner_score: number
  sell_signal_score: number
  sourcing_score: number
  score_breakdown: Breakdown[]
  score_explanation: string
  owner: string
  siren: string
}

export interface Owner {
  id: string | number
  siren: string
  nom_entreprise: string
  type_proprietaire: string
  nb_locaux_api: number
  nb_parcelles_api: number
  cessation_activite: number
  actifs: number
}

export interface DashboardSummary {
  total_assets: number
  qualified_assets: number
  priced_assets: number
  top100_average_score: number | null
  asset_type_counts: Record<string, number>
  confidence_counts: Record<string, number>
}
