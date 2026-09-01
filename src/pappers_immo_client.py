"""Client HTTP pour l'API Pappers Immobilier (CLAUDE.md, section 3 et 3.8).

Authentification par header `api-key` (jamais le paramètre query
`api_token`, déconseillé par la spec). Retry avec backoff exponentiel sur
les erreurs transitoires (réseau, timeout, 5xx) ; les erreurs 400/401/404
ne sont jamais retentées (paramètres incorrects, clé invalide, parcelle
inexistante : reproductibles à l'identique). Le compteur `credits_used`
totalise le surcoût des champs supplémentaires demandés, selon
`config.CHAMPS_SUPPLEMENTAIRES_COUTS`.

`get_parcelle_fiche` (GET /parcelles/{numero_parcelle}) est pleinement
implémenté : son schéma de réponse (`ParcelleFiche`) est complètement
spécifié dans `api_1.0.0.yaml`.

`search_parcelles` (GET /parcelles) construit et envoie la requête — ses
paramètres SONT documentés, voir `pappers_types.ParcelleSearchParams` —
mais retourne le JSON brut plutôt qu'une liste de `ParcelleFiche`.
`api_1.0.0.yaml` ne documente pas le schéma de la réponse de cet endpoint
(pas de schéma `resultats` / `curseurSuivant` / `total` dans
`components.schemas`, alors que ce sont ces champs qui permettraient un
balayage de zone par curseur, voir CLAUDE.md section 3.8). Ne pas deviner
ce format (règle 1, CLAUDE.md) : brancher le parsing ici dès qu'un exemple
de réponse réelle ou une documentation Pappers à jour sera disponible.
"""

from __future__ import annotations

import time
from typing import Any

import requests
from pydantic import ValidationError

import config
from src.pappers_types import ParcelleFiche, ParcelleSearchParams


class PappersImmoError(Exception):
    """Erreur retournée par l'API Pappers Immobilier (après épuisement des retries)."""


class CreditBudgetExceeded(Exception):
    """Le run dépasserait config.MAX_CREDITS_PER_RUN si la requête était envoyée."""


# Codes HTTP documentés par la spec comme erreurs permanentes (paramètres
# incorrects, clé invalide, ressource inexistante) : jamais retentés.
_ERREURS_PERMANENTES = {400, 401, 404}


class PappersImmoClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        session: requests.Session | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        retry_backoff_seconds: float | None = None,
        max_credits_per_run: int | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else config.PAPPERS_IMMO_API_KEY
        self.base_url = base_url or config.PAPPERS_IMMO_BASE_URL
        self.session = session or requests.Session()
        self.timeout = timeout if timeout is not None else config.PAPPERS_IMMO_TIMEOUT_SECONDS
        self.max_retries = max_retries if max_retries is not None else config.PAPPERS_IMMO_MAX_RETRIES
        self.retry_backoff_seconds = (
            retry_backoff_seconds if retry_backoff_seconds is not None else config.PAPPERS_IMMO_RETRY_BACKOFF_SECONDS
        )
        self.max_credits_per_run = max_credits_per_run if max_credits_per_run is not None else config.MAX_CREDITS_PER_RUN
        self.credits_used = 0

    def _headers(self) -> dict[str, str]:
        return {"api-key": self.api_key}

    def estimate_cost(self, champs_supplementaires: list[str] | None) -> int:
        """Somme des surcoûts DOCUMENTÉS des champs supplémentaires demandés.

        Ne comptabilise pas le coût de base d'une requête /parcelles : il
        n'est documenté ni par la spec ni par le cahier des charges (voir
        le TODO au-dessus de config.CHAMPS_SUPPLEMENTAIRES_COUTS). Cette
        estimation sous-estime donc la consommation réelle de jetons.
        """
        if not champs_supplementaires:
            return 0
        if "tous" in champs_supplementaires:
            raise ValueError("champs_supplementaires='tous' ne doit jamais être utilisé (règle 3.8, CLAUDE.md)")
        inconnus = [c for c in champs_supplementaires if c not in config.CHAMPS_SUPPLEMENTAIRES_COUTS]
        if inconnus:
            raise ValueError(f"Champ(s) supplémentaire(s) non documenté(s) dans config.CHAMPS_SUPPLEMENTAIRES_COUTS : {inconnus}")
        return sum(config.CHAMPS_SUPPLEMENTAIRES_COUTS[c] for c in champs_supplementaires)

    def _reserve_credits(self, cost: int) -> None:
        if self.credits_used + cost > self.max_credits_per_run:
            raise CreditBudgetExceeded(
                f"Ce run consommerait au moins {self.credits_used + cost} jeton(s) documenté(s), "
                f"au-delà de MAX_CREDITS_PER_RUN={self.max_credits_per_run}."
            )
        self.credits_used += cost

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(url, headers=self._headers(), params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = exc
            else:
                if response.status_code == 200:
                    return response.json()
                if response.status_code in _ERREURS_PERMANENTES:
                    raise PappersImmoError(f"{response.status_code} sur {url} : {response.text}")
                last_error = PappersImmoError(f"{response.status_code} sur {url} : {response.text}")

            if attempt < self.max_retries:
                time.sleep(self.retry_backoff_seconds * (2**attempt))

        raise PappersImmoError(f"Échec après {self.max_retries + 1} tentative(s) sur {url}") from last_error

    def get_parcelle_fiche(
        self,
        numero_parcelle: str,
        bases: list[str] | None = None,
        champs_supplementaires: list[str] | None = None,
    ) -> ParcelleFiche:
        """GET /parcelles/{numero_parcelle} — schéma de réponse entièrement documenté."""
        cost = self.estimate_cost(champs_supplementaires)
        self._reserve_credits(cost)

        params: dict[str, Any] = {}
        if bases:
            params["bases"] = ",".join(bases)
        if champs_supplementaires:
            params["champs_supplementaires"] = ",".join(champs_supplementaires)

        payload = self._get(f"parcelles/{numero_parcelle}", params)
        try:
            return ParcelleFiche.model_validate(payload)
        except ValidationError as exc:
            raise PappersImmoError(f"Réponse inattendue pour la parcelle {numero_parcelle} : {exc}") from exc

    def search_parcelles(self, params: ParcelleSearchParams) -> dict[str, Any]:
        """GET /parcelles — recherche multi-critères.

        Retourne le JSON brut de la réponse, PAS une liste de
        `ParcelleFiche` : voir le TODO en tête de ce module sur le schéma
        de réponse non documenté de cet endpoint (curseur de pagination
        pour un balayage de zone complet, section 3.8 du CLAUDE.md).
        """
        cost = self.estimate_cost(params.champs_supplementaires)
        self._reserve_credits(cost)
        return self._get("parcelles", params.to_query_params())
