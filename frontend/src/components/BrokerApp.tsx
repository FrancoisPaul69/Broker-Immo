'use client'

import { createContext, useContext, useMemo, useState } from 'react'
import type { Asset, DashboardSummary, Owner } from '@/types/broker'

interface BrokerData {
  assets: Asset[]
  owners: Owner[]
  summary: DashboardSummary
  demo: boolean
}

const BrokerDataContext = createContext<BrokerData | null>(null)

function useBrokerData() {
  const data = useContext(BrokerDataContext)
  if (!data) throw new Error('Broker data is unavailable')
  return data
}

type Page = 'dashboard' | 'assets' | 'detail' | 'owners'
type IconName =
  | 'grid'
  | 'building'
  | 'file'
  | 'users'
  | 'search'
  | 'bell'
  | 'arrow'
  | 'pin'
  | 'trend'
  | 'filter'
  | 'download'
  | 'chevron'
  | 'database'
  | 'menu'
  | 'close'

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  const paths: Record<IconName, React.ReactNode> = {
    grid: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </>
    ),
    building: (
      <>
        <path d="M4 21h16M6 21V5l6-3 6 3v16M9 8h.01M15 8h.01M9 12h.01M15 12h.01M9 16h.01M15 16h.01" />
      </>
    ),
    file: (
      <>
        <path d="M6 2h8l4 4v16H6zM14 2v5h5M9 12h6M9 16h6" />
      </>
    ),
    users: (
      <>
        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
      </>
    ),
    search: (
      <>
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-4-4" />
      </>
    ),
    bell: (
      <>
        <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" />
      </>
    ),
    arrow: (
      <>
        <path d="M5 12h14M13 6l6 6-6 6" />
      </>
    ),
    pin: (
      <>
        <path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z" />
        <circle cx="12" cy="10" r="2.5" />
      </>
    ),
    trend: (
      <>
        <path d="m3 17 6-6 4 4 8-9M15 6h6v6" />
      </>
    ),
    filter: <path d="M4 5h16l-6 7v6l-4 2v-8z" />,
    download: (
      <>
        <path d="M12 3v12m-5-5 5 5 5-5M5 21h14" />
      </>
    ),
    chevron: <path d="m9 18 6-6-6-6" />,
    database: (
      <>
        <ellipse cx="12" cy="5" rx="8" ry="3" />
        <path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" />
      </>
    ),
    menu: (
      <>
        <path d="M4 7h16M4 12h16M4 17h16" />
      </>
    ),
    close: (
      <>
        <path d="m6 6 12 12M18 6 6 18" />
      </>
    ),
  }
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  )
}

const money = new Intl.NumberFormat('fr-FR', {
  style: 'currency',
  currency: 'EUR',
  maximumFractionDigits: 0,
})
const number = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 })

function downloadCsv(filename: string, rows: Record<string, string | number | null>[]) {
  if (!rows.length) return
  const headers = Object.keys(rows[0])
  const escape = (value: string | number | null) => `"${String(value ?? '').replaceAll('"', '""')}"`
  const content = [
    headers.map(escape).join(';'),
    ...rows.map((row) => headers.map((header) => escape(row[header])).join(';')),
  ].join('\n')
  const link = document.createElement('a')
  link.href = URL.createObjectURL(
    new Blob([`\uFEFF${content}`], { type: 'text/csv;charset=utf-8' }),
  )
  link.download = filename
  link.click()
  URL.revokeObjectURL(link.href)
}

function Score({ value, large = false }: { value: number; large?: boolean }) {
  const tone = value >= 58 ? 'high' : value >= 48 ? 'medium' : 'low'
  return (
    <span className={`score ${tone} ${large ? 'large' : ''}`}>
      {value.toFixed(1).replace('.0', '')}
    </span>
  )
}

function Dashboard({
  openAssets,
  openDetail,
}: {
  openAssets: () => void
  openDetail: (asset: Asset) => void
}) {
  const { assets, summary } = useBrokerData()
  const bars = [
    ['Commercial', summary.asset_type_counts.commercial ?? 0, 'var(--orange)'],
    ['Industriel / entrepôt', summary.asset_type_counts.industriel_ou_entrepot ?? 0, 'var(--navy)'],
    ['Incertain', summary.asset_type_counts.incertain ?? 0, '#b8a58e'],
    ['Autre', summary.asset_type_counts.autre ?? 0, '#d8d3c9'],
  ] as const
  const maxBar = Math.max(...bars.map(([, value]) => value), 1)
  const confidence = { haute: summary.confidence_counts.haute ?? 0, moyenne: summary.confidence_counts.moyenne ?? 0, faible: summary.confidence_counts.faible ?? 0 }
  const confidenceTotal = confidence.haute + confidence.moyenne + confidence.faible
  const highEnd = confidenceTotal ? (confidence.haute / confidenceTotal) * 100 : 0
  const mediumEnd = confidenceTotal ? highEnd + (confidence.moyenne / confidenceTotal) * 100 : 0
  const scoreBins = Array.from({ length: 11 }, () => 0)
  assets.forEach((asset) => { scoreBins[Math.min(10, Math.floor(asset.sourcing_score / 10))] += 1 })
  const maxBin = Math.max(...scoreBins, 1)
  const coverage = summary.total_assets ? Math.round((summary.priced_assets / summary.total_assets) * 100) : 0
  return (
    <>
      <PageTitle
        eyebrow="PILOTAGE DU SOURCING"
        title="Vue d’ensemble"
        subtitle="Les signaux clés de votre marché immobilier commercial."
        action={
          <button className="primary" onClick={openAssets}>
            Explorer le TOP 100 <Icon name="arrow" size={15} />
          </button>
        }
      />
      <section className="kpi-grid">
        <Kpi label="Actifs analysés" value={number.format(summary.total_assets)} note="Jeu de données complet" icon="database" />
        <Kpi
          label="Opportunités qualifiées"
          value={number.format(summary.qualified_assets)}
          note="Commerciales ou incertaines"
          icon="building"
          accent
        />
        <Kpi label="Prix de mutation connu" value={number.format(summary.priced_assets)} note={`${coverage} % de couverture`} icon="trend" />
        <Kpi label="Score moyen — TOP 100" value={summary.top100_average_score?.toLocaleString('fr-FR') ?? '—'} note="sur 100 points" icon="file" />
      </section>
      <section className="dashboard-grid">
        <article className="panel asset-split">
          <PanelHead
            title="Répartition par type d’actif"
            subtitle={`Ensemble des ${number.format(summary.total_assets)} actifs analysés`}
          />
          <div className="bar-chart">
            {bars.map(([label, value, color]) => (
              <div className="bar-row" key={label}>
                <span>{label}</span>
                <div>
                  <i
                    style={{
                      width: `${(value / maxBar) * 100}%`,
                      background: color,
                    }}
                  />
                </div>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
        </article>
        <article className="panel confidence">
          <PanelHead
            title="Confiance de qualification"
            subtitle="Actifs commerciaux et incertains"
          />
          <div className="donut-wrap">
            <div className="donut" style={{ background: `conic-gradient(var(--green) 0 ${highEnd}%, #d29a60 ${highEnd}% ${mediumEnd}%, #d6dbd6 ${mediumEnd}% 100%)` }}>
              <span>
                <strong>{number.format(confidenceTotal)}</strong>actifs
              </span>
            </div>
            <div className="legend">
              <p>
                <i className="green" />
                <span>Haute</span>
                <strong>{confidence.haute}</strong>
              </p>
              <p>
                <i className="amber" />
                <span>Moyenne</span>
                <strong>{confidence.moyenne}</strong>
              </p>
              <p>
                <i className="gray" />
                <span>Faible</span>
                <strong>{confidence.faible}</strong>
              </p>
            </div>
          </div>
        </article>
        <article className="panel distribution">
          <PanelHead
            title="Distribution des scores de sourcing"
            subtitle="Nombre d’actifs par intervalle de score"
            extra={<span className="update-dot">Données actualisées</span>}
          />
          <div className="histogram">
            {scoreBins.map((count, i) => (
              <div key={i}>
                <i style={{ height: `${Math.max(4, (count / maxBin) * 126)}px` }} />
                <span>{i % 2 === 0 ? i * 10 : ''}</span>
              </div>
            ))}
          </div>
        </article>
        <article className="panel top-opportunities">
          <PanelHead
            title="Opportunités prioritaires"
            subtitle="Les actifs au score le plus élevé"
            extra={
              <button className="text-button" onClick={openAssets}>
                Tout voir <Icon name="arrow" size={14} />
              </button>
            }
          />
          <div className="mini-list">
            {assets.slice(0, 4).map((asset, i) => (
              <button key={asset.id} onClick={() => openDetail(asset)}>
                <span className="rank">{String(i + 1).padStart(2, '0')}</span>
                <span className="asset-name">
                  <strong>{asset.adresse_brute}</strong>
                  <small>
                    <Icon name="pin" size={12} /> {asset.ville} ·{' '}
                    {number.format(asset.surface_bati || 0)} m²
                  </small>
                </span>
                <Score value={asset.sourcing_score} />
                <Icon name="chevron" size={15} />
              </button>
            ))}
          </div>
        </article>
      </section>
    </>
  )
}

function Kpi({
  label,
  value,
  note,
  icon,
  accent,
}: {
  label: string
  value: string
  note: string
  icon: IconName
  accent?: boolean
}) {
  return (
    <article className={`kpi ${accent ? 'accent' : ''}`}>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{note}</small>
      </div>
      <i>
        <Icon name={icon} />
      </i>
    </article>
  )
}

function PanelHead({
  title,
  subtitle,
  extra,
}: {
  title: string
  subtitle: string
  extra?: React.ReactNode
}) {
  return (
    <header className="panel-head">
      <div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {extra}
    </header>
  )
}

function PageTitle({
  eyebrow,
  title,
  subtitle,
  action,
}: {
  eyebrow: string
  title: string
  subtitle: string
  action?: React.ReactNode
}) {
  return (
    <header className="page-title">
      <div>
        <span>{eyebrow}</span>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      {action}
    </header>
  )
}

function AssetsPage({
  openDetail,
  query,
  setQuery,
}: {
  openDetail: (asset: Asset) => void
  query: string
  setQuery: (value: string) => void
}) {
  const { assets } = useBrokerData()
  const [type, setType] = useState('tous')
  const [confidence, setConfidence] = useState('toutes')
  const filtered = useMemo(
    () =>
      assets.filter((asset) => {
        const haystack =
          `${asset.adresse_brute} ${asset.ville} ${asset.owner} ${asset.numero_parcelle}`.toLowerCase()
        return (
          haystack.includes(query.toLowerCase()) &&
          (type === 'tous' || asset.type_actif === type) &&
          (confidence === 'toutes' || asset.type_actif_confidence === confidence)
        )
      }),
    [query, type, confidence],
  )
  return (
    <>
      <PageTitle
        eyebrow="CLASSEMENT DES OPPORTUNITÉS"
        title="TOP 100 sourcing"
        subtitle="Priorisez les actifs commerciaux selon leur potentiel de sourcing."
        action={
          <button
            className="secondary"
            onClick={() =>
              downloadCsv(
                'broker-immo-top-100.csv',
                filtered.map((asset, index) => ({
                  rang: index + 1,
                  parcelle: asset.numero_parcelle,
                  adresse: asset.adresse_brute,
                  ville: asset.ville,
                  type: asset.type_actif,
                  confiance: asset.type_actif_confidence,
                  proprietaire: asset.owner,
                  score_actif: asset.asset_score,
                  score_proprietaire: asset.owner_score,
                  score_signaux: asset.sell_signal_score,
                  score_sourcing: asset.sourcing_score,
                })),
              )
            }
          >
            <Icon name="download" size={15} /> Exporter
          </button>
        }
      />
      <section className="filter-bar">
        <label className="search-field">
          <Icon name="search" size={16} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Rechercher une adresse, une ville, un propriétaire…"
          />
        </label>
        <label>
          <span>Type d’actif</span>
          <select value={type} onChange={(e) => setType(e.target.value)}>
            <option value="tous">Tous les types</option>
            <option value="commercial">Commercial</option>
            <option value="incertain">Incertain</option>
          </select>
        </label>
        <label>
          <span>Confiance</span>
          <select value={confidence} onChange={(e) => setConfidence(e.target.value)}>
            <option value="toutes">Tous les niveaux</option>
            <option value="haute">Haute</option>
            <option value="moyenne">Moyenne</option>
            <option value="faible">Faible</option>
          </select>
        </label>
        <button className="filter-icon" aria-label="Filtres">
          <Icon name="filter" />
        </button>
      </section>
      <section className="panel table-panel">
        <div className="table-caption">
          <p>
            <strong>{filtered.length}</strong> actif
            {filtered.length > 1 ? 's' : ''} affiché
            {filtered.length > 1 ? 's' : ''} <span>· extrait du TOP 100 réel</span>
          </p>
          <small>Trié par score décroissant</small>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Actif</th>
                <th>Type</th>
                <th>Propriétaire</th>
                <th>Actif</th>
                <th>Proprio.</th>
                <th>Signaux</th>
                <th>Score</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filtered.map((asset) => {
                const rank = assets.findIndex((item) => item.id === asset.id) + 1
                return (
                  <tr key={asset.id} onClick={() => openDetail(asset)}>
                    <td>
                      <span className={`rank ${rank < 4 ? 'top' : ''}`}>
                        {String(rank).padStart(2, '0')}
                      </span>
                    </td>
                    <td>
                      <strong>{asset.adresse_brute.split(/\d{5}/)[0].trim()}</strong>
                      <small>
                        {asset.ville} · Parcelle {asset.numero_parcelle}
                      </small>
                    </td>
                    <td>
                      <span className={`tag ${asset.type_actif}`}>{asset.type_actif}</span>
                      <small className="confidence-label">{asset.type_actif_confidence}</small>
                    </td>
                    <td>
                      <strong>{asset.owner}</strong>
                      <small>SIREN {asset.siren}</small>
                    </td>
                    <td>{asset.asset_score.toFixed(1)}</td>
                    <td>{asset.owner_score.toFixed(1)}</td>
                    <td>{asset.sell_signal_score.toFixed(1)}</td>
                    <td>
                      <Score value={asset.sourcing_score} />
                    </td>
                    <td>
                      <Icon name="chevron" size={15} />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        {!filtered.length && <div className="empty">Aucun actif ne correspond à ces filtres.</div>}
      </section>
    </>
  )
}

function DetailPage({ asset }: { asset: Asset }) {
  const { assets } = useBrokerData()
  const groups = [
    ['Score actif', asset.asset_score, 40, asset.score_breakdown.slice(0, 4)],
    ['Score propriétaire', asset.owner_score, 30, asset.score_breakdown.slice(4, 6)],
    ['Signaux de vente', asset.sell_signal_score, 30, asset.score_breakdown.slice(6)],
  ] as const
  return (
    <>
      <PageTitle
        eyebrow={`ACTIF #${assets.findIndex((a) => a.id === asset.id) + 1} DU CLASSEMENT`}
        title={asset.adresse_brute.split(/\d{5}/)[0].trim()}
        subtitle={`${asset.code_postal} ${asset.ville} · Parcelle ${asset.numero_parcelle}`}
        action={
          <button
            className="secondary"
            onClick={() =>
              downloadCsv('broker-immo-fiche-actif.csv', [
                {
                  rang: assets.findIndex((a) => a.id === asset.id) + 1,
                  parcelle: asset.numero_parcelle,
                  adresse: asset.adresse_brute,
                  ville: asset.ville,
                  type: asset.type_actif,
                  surface_batie: asset.surface_bati,
                  prix_derniere_mutation: asset.prix_derniere_mutation,
                  proprietaire: asset.owner,
                  siren: asset.siren,
                  score_sourcing: asset.sourcing_score,
                },
              ])
            }
          >
            <Icon name="download" size={15} /> Exporter la fiche
          </button>
        }
      />
      <section className="detail-hero panel">
        <div className="map-card">
          <div className="map-grid" />
          <div className="map-pin">
            <Icon name="building" size={20} />
          </div>
          <span>Rhône · Métropole de Lyon</span>
        </div>
        <div className="property-facts">
          <div className="fact-head">
            <div>
              <span className={`tag ${asset.type_actif}`}>{asset.type_actif}</span>
              <span className={`confidence-pill ${asset.type_actif_confidence}`}>
                Confiance {asset.type_actif_confidence}
              </span>
            </div>
            <Score value={asset.sourcing_score} large />
          </div>
          <h2>Informations clés</h2>
          <div className="fact-grid">
            <p>
              <span>Surface bâtie</span>
              <strong>
                {asset.surface_bati ? `${number.format(asset.surface_bati)} m²` : 'Non renseignée'}
              </strong>
            </p>
            <p>
              <span>Contenance parcelle</span>
              <strong>
                {asset.contenance ? `${number.format(asset.contenance)} m²` : 'Non renseignée'}
              </strong>
            </p>
            <p>
              <span>Dernière mutation</span>
              <strong>
                {asset.date_derniere_mutation
                  ? new Date(asset.date_derniere_mutation).toLocaleDateString('fr-FR')
                  : 'Inconnue'}
              </strong>
            </p>
            <p>
              <span>Prix de mutation</span>
              <strong>
                {asset.prix_derniere_mutation
                  ? money.format(asset.prix_derniere_mutation)
                  : 'Inconnu'}
              </strong>
            </p>
          </div>
          <div className="owner-strip">
            <i>
              <Icon name="users" />
            </i>
            <span>
              <small>Propriétaire identifié</small>
              <strong>{asset.owner}</strong>
              <em>SIREN {asset.siren}</em>
            </span>
            <Icon name="chevron" size={16} />
          </div>
        </div>
      </section>
      <section className="score-layout">
        <article className="panel score-card">
          <PanelHead
            title="Décomposition du score"
            subtitle="Lecture transparente des 100 points"
          />
          {groups.map(([label, value, max, breakdown]) => (
            <div className="score-group" key={label}>
              <div className="score-group-head">
                <strong>{label}</strong>
                <span>
                  {value.toFixed(1)} <small>/ {max}</small>
                </span>
              </div>
              <div className="progress">
                <i style={{ width: `${(value / max) * 100}%` }} />
              </div>
              {breakdown.map((item) => (
                <div className="criterion" key={item.critere}>
                  <span>
                    <strong>{item.critere.replaceAll('_', ' ')}</strong>
                    <small>{item.detail}</small>
                  </span>
                  <b>
                    {item.points} / {item.points_max}
                  </b>
                </div>
              ))}
            </div>
          ))}
        </article>
        <aside className="detail-aside">
          <article className="panel explanation">
            <span>ANALYSE BROKER IMMO</span>
            <h2>Pourquoi ce score ?</h2>
            <p>{asset.score_explanation}</p>
            <div className="insight">
              <Icon name="trend" size={17} />
              <span>
                <strong>Opportunité à qualifier</strong>Recoupez ces signaux avec une prise de
                contact propriétaire.
              </span>
            </div>
          </article>
          <article className="panel indices">
            <PanelHead
              title="Indices de qualification"
              subtitle={`${asset.type_actif_indices.length} signaux retenus`}
            />
            {asset.type_actif_indices.map((indice) => (
              <p key={indice}>
                <i />
                {indice}
              </p>
            ))}
          </article>
        </aside>
      </section>
    </>
  )
}

function OwnersPage() {
  const { assets, owners } = useBrokerData()
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<Owner | null>(owners[0] ?? null)
  const filtered = owners.filter((owner) =>
    `${owner.nom_entreprise} ${owner.siren} ${owner.type_proprietaire}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  )
  const ownerAssets = assets.filter((asset) => asset.siren === selected?.siren)
  if (!selected) {
    return <div className="panel empty">Aucun propriétaire disponible.</div>
  }
  return (
    <>
      <PageTitle
        eyebrow="CARTOGRAPHIE PROPRIÉTAIRES"
        title="Propriétaires"
        subtitle="Identifiez les portefeuilles et les interlocuteurs à fort potentiel."
        action={
          <button
            className="secondary"
            onClick={() =>
              downloadCsv(
                'broker-immo-proprietaires.csv',
                filtered.map((owner) => ({
                  siren: owner.siren,
                  nom: owner.nom_entreprise,
                  type: owner.type_proprietaire,
                  actifs_identifies: owner.actifs,
                  locaux_api: owner.nb_locaux_api,
                  parcelles_api: owner.nb_parcelles_api,
                })),
              )
            }
          >
            <Icon name="download" size={15} /> Exporter
          </button>
        }
      />
      <div className="owner-notice">
        <Icon name="database" size={17} />
        <p>
          <strong>Deux périmètres distincts.</strong> Les actifs identifiés dans notre base et le
          portefeuille déclaré par l’API ne sont jamais additionnés.
        </p>
      </div>
      <section className="owners-layout">
        <article className="panel owner-list-panel">
          <label className="search-field">
            <Icon name="search" size={16} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Rechercher un propriétaire ou un SIREN…"
            />
          </label>
          <div className="owner-list">
            {filtered.map((owner) => (
              <button
                className={selected.siren === owner.siren ? 'selected' : ''}
                onClick={() => setSelected(owner)}
                key={owner.siren}
              >
                <i>
                  {owner.nom_entreprise
                    .split(' ')
                    .slice(0, 2)
                    .map((w) => w[0])
                    .join('')}
                </i>
                <span>
                  <strong>{owner.nom_entreprise}</strong>
                  <small>
                    {owner.type_proprietaire} · SIREN {owner.siren}
                  </small>
                </span>
                <b>
                  {owner.actifs}
                  <small>actifs</small>
                </b>
                <Icon name="chevron" size={15} />
              </button>
            ))}
          </div>
        </article>
        <article className="owner-detail">
          <div className="panel owner-profile">
            <div className="owner-profile-head">
              <i>
                {selected.nom_entreprise
                  .split(' ')
                  .slice(0, 2)
                  .map((w) => w[0])
                  .join('')}
              </i>
              <div>
                <span>{selected.type_proprietaire}</span>
                <h2>{selected.nom_entreprise}</h2>
                <p>SIREN {selected.siren}</p>
              </div>
            </div>
            <div className="owner-kpis">
              <p>
                <strong>{selected.actifs}</strong>
                <span>
                  Actifs identifiés
                  <br />
                  dans notre base
                </span>
              </p>
              <p>
                <strong>{selected.nb_locaux_api}</strong>
                <span>
                  Locaux déclarés
                  <br />
                  par l’API
                </span>
              </p>
              <p>
                <strong>{selected.nb_parcelles_api}</strong>
                <span>
                  Parcelles déclarées
                  <br />
                  par l’API
                </span>
              </p>
            </div>
          </div>
          <div className="panel portfolio">
            <PanelHead
              title="Actifs identifiés dans notre base"
              subtitle={`Portefeuille rattaché au SIREN ${selected.siren}`}
            />
            {ownerAssets.length ? (
              ownerAssets.map((asset) => (
                <div key={asset.id}>
                  <span>
                    <strong>{asset.adresse_brute.split(/\d{5}/)[0]}</strong>
                    <small>
                      {asset.ville} · {asset.type_actif}
                    </small>
                  </span>
                  <Score value={asset.sourcing_score} />
                </div>
              ))
            ) : (
              <p className="empty">
                Aucun actif commercial ou incertain n’est rattaché à ce propriétaire.
              </p>
            )}
          </div>
        </article>
      </section>
    </>
  )
}

function BrokerShell() {
  const { assets, demo } = useBrokerData()
  const [page, setPage] = useState<Page>('dashboard')
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(assets[0] ?? null)
  const [globalSearch, setGlobalSearch] = useState('')
  const [mobileNav, setMobileNav] = useState(false)
  const openDetail = (asset: Asset) => {
    setSelectedAsset(asset)
    setPage('detail')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  const navigate = (next: Page) => {
    setPage(next)
    setMobileNav(false)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  const navItems: [Page, string, IconName][] = [
    ['dashboard', 'Vue d’ensemble', 'grid'],
    ['assets', 'TOP 100', 'building'],
    ['detail', 'Fiche actif', 'file'],
    ['owners', 'Propriétaires', 'users'],
  ]
  return (
    <div className="app">
      <aside className={`sidebar ${mobileNav ? 'open' : ''}`}>
        <button className="mobile-close" onClick={() => setMobileNav(false)} aria-label="Fermer">
          <Icon name="close" />
        </button>
        <div className="logo">
          <span>
            <Icon name="building" size={21} />
          </span>
          <div>
            <strong>BROKER</strong>
            <small>IMMO</small>
          </div>
        </div>
        <p className="nav-label">ESPACE SOURCING</p>
        <nav>
          {navItems.map(([id, label, icon]) => (
            <button key={id} className={page === id ? 'active' : ''} onClick={() => navigate(id)}>
              <Icon name={icon} />
              <span>{label}</span>
              {id === 'assets' && <em>99</em>}
            </button>
          ))}
        </nav>
        <div className="sidebar-insight">
          <span>
            <Icon name="trend" size={16} /> SIGNAL DU JOUR
          </span>
          <strong>14 actifs</strong>
          <p>présentent une qualification à confirmer.</p>
          <button onClick={() => navigate('assets')}>
            Les consulter <Icon name="arrow" size={13} />
          </button>
        </div>
        <div className="user">
          <i>FP</i>
          <span>
            <strong>François Paul</strong>
            <small>Broker · Rhône</small>
          </span>
          <Icon name="chevron" size={14} />
        </div>
      </aside>
      {mobileNav && (
        <button
          className="nav-backdrop"
          onClick={() => setMobileNav(false)}
          aria-label="Fermer le menu"
        />
      )}
      <main>
        <header className="topbar">
          <button className="menu-button" onClick={() => setMobileNav(true)} aria-label="Menu">
            <Icon name="menu" />
          </button>
          <div className="crumb">
            <span>Broker Immo</span>
            <i>/</i>
            <strong>{navItems.find(([id]) => id === page)?.[1]}</strong>
          </div>
          <div className="top-actions">
            <label>
              <Icon name="search" size={16} />
              <input
                value={globalSearch}
                placeholder="Rechercher…"
                onFocus={() => setPage('assets')}
                onChange={(event) => {
                  setGlobalSearch(event.target.value)
                  setPage('assets')
                }}
              />
            </label>
            {demo && <span className="demo-badge">DÉMO · DONNÉES FICTIVES</span>}
          </div>
        </header>
        <div className="content">
          {page === 'dashboard' && (
            <Dashboard openAssets={() => navigate('assets')} openDetail={openDetail} />
          )}
          {page === 'assets' && (
            <AssetsPage openDetail={openDetail} query={globalSearch} setQuery={setGlobalSearch} />
          )}
          {page === 'detail' && selectedAsset && <DetailPage asset={selectedAsset} />}
          {page === 'detail' && !selectedAsset && (
            <div className="panel empty">Aucun actif disponible.</div>
          )}
          {page === 'owners' && <OwnersPage />}
        </div>
      </main>
    </div>
  )
}

export default function BrokerApp({ assets, owners, summary, demo }: BrokerData) {
  return (
    <BrokerDataContext.Provider value={{ assets, owners, summary, demo }}>
      <BrokerShell />
    </BrokerDataContext.Provider>
  )
}
