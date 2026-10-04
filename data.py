"""Dades públiques XEMA: consultes SODA i acumulats per dia o interval."""

from datetime import date, datetime, time, timedelta, timezone
import math
import re
import unicodedata
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
import streamlit as st
from urllib3.util.retry import Retry

DOMAIN = "https://analisi.transparenciacatalunya.cat"
MEASUREMENTS_DATASET = "nzvn-apee"
STATIONS_DATASET = "yqwd-vj5e"
PRECIPITATION_VARIABLE = "35"
LOCAL_TZ = ZoneInfo("Europe/Madrid")
PAGE_SIZE = 50_000
MAX_INTERVAL_DAYS = 31
MEASUREMENT_COLUMNS = [
    "id", "codi_estacio", "codi_variable", "data_lectura",
    "valor_lectura", "codi_estat", "codi_base",
]
STATION_COLUMNS = [
    "codi_estacio", "nom", "municipi", "comarca", "latitud", "longitud",
    "altitud", "estat_estacio",
]
TOTAL_COLUMNS = [
    "codi_estacio", "precipitacio", "lectures", "ultima_lectura",
    "codi_base", "lectures_provisionals", "lectures_esperades", "estat_dades",
]


class DataError(RuntimeError):
    """Error recuperable que la interfície pot explicar a l'usuari."""


def today_local() -> date:
    return datetime.now(LOCAL_TZ).date()


def day_bounds_utc(selected_day: date) -> tuple[datetime, datetime]:
    """Cada mitjanit es localitza separadament: el dia pot tenir 23, 24 o 25 h."""
    start = datetime.combine(selected_day, time.min, tzinfo=LOCAL_TZ)
    end = datetime.combine(selected_day + timedelta(days=1), time.min, tzinfo=LOCAL_TZ)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def local_datetime_candidates(value: datetime) -> list[datetime]:
    """0 candidats: hora inexistent; 2: hora repetida en el canvi d'hora."""
    if value.tzinfo is not None:
        raise DataError("La data i hora local ha d'arribar sense fus horari.")
    candidates = {}
    for fold in (0, 1):
        local = value.replace(tzinfo=LOCAL_TZ, fold=fold)
        utc = local.astimezone(timezone.utc)
        if utc.astimezone(LOCAL_TZ).replace(tzinfo=None) == value:
            candidates[utc] = local
    return [candidates[utc] for utc in sorted(candidates)]


def resolve_local_datetime(value: datetime, occurrence: int | None = None) -> datetime:
    candidates = local_datetime_candidates(value)
    if not candidates:
        raise DataError(f"L'hora {value:%d/%m/%Y %H:%M} no existeix a Catalunya pel canvi d'hora. Tria una altra hora.")
    if len(candidates) == 2 and occurrence is None:
        raise DataError("Aquesta hora es repeteix pel canvi d'hora. Tria la primera o la segona ocurrència.")
    if occurrence not in (None, 0, 1) or (occurrence == 1 and len(candidates) != 2):
        raise DataError("L'ocurrència de l'hora seleccionada no és vàlida.")
    return candidates[occurrence or 0]


def interval_bounds_utc(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    if start.utcoffset() is None or end.utcoffset() is None:
        raise DataError("L'inici i el final han d'incloure un fus horari.")
    start_utc, end_utc = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
    if end_utc <= start_utc:
        raise DataError("El final ha de ser posterior a l'inici.")
    # El límit és civil: un període de 31 dies pot contenir una hora addicional.
    civil_duration = (end.astimezone(LOCAL_TZ).replace(tzinfo=None)
                      - start.astimezone(LOCAL_TZ).replace(tzinfo=None))
    if civil_duration > timedelta(days=MAX_INTERVAL_DAYS):
        raise DataError(f"Tria un període de com a màxim {MAX_INTERVAL_DAYS} dies per consulta.")
    return start_utc, end_utc


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"], respect_retry_after_header=False,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"Accept": "application/json", "User-Agent": "xema-pluja/1.0"})
    return session


def _json_get(session: requests.Session, url: str, params: dict | None = None):
    try:
        response = session.get(url, params=params, timeout=(10, 45))
        response.raise_for_status()
        return response.json()
    except requests.Timeout as exc:
        raise DataError("Socrata ha superat el temps d'espera. Torna-ho a provar.") from exc
    except requests.HTTPError as exc:
        raise DataError(f"Socrata ha retornat un error HTTP {exc.response.status_code}.") from exc
    except ValueError as exc:
        raise DataError("Socrata ha retornat una resposta que no és JSON vàlid.") from exc
    except requests.RequestException as exc:
        raise DataError("No s'ha pogut connectar amb Dades Obertes de Catalunya.") from exc


@st.cache_data(ttl=300, show_spinner=False)
def get_schema(dataset_id: str) -> list[dict]:
    if dataset_id not in {MEASUREMENTS_DATASET, STATIONS_DATASET}:
        raise DataError("Dataset no admès.")
    with _session() as session:
        schema = _json_get(session, f"{DOMAIN}/api/views/{dataset_id}.json")
    if not isinstance(schema, dict) or not isinstance(schema.get("columns"), list):
        raise DataError("No s'ha pogut interpretar l'esquema de Socrata.")
    return [column for column in schema["columns"] if not column.get("fieldName", "").startswith(":")]


def _fetch_rows(dataset_id: str, params: dict, page_size: int = PAGE_SIZE) -> list[dict]:
    """Pàgines ordenades; la consulta es restringeix al període seleccionat."""
    rows = []
    with _session() as session:
        offset = 0
        while True:
            page = _json_get(
                session, f"{DOMAIN}/resource/{dataset_id}.json",
                {**params, "$limit": page_size, "$offset": offset},
            )
            if not isinstance(page, list) or any(not isinstance(row, dict) for row in page):
                raise DataError("Socrata ha retornat una pàgina de dades mal formada.")
            rows.extend(page)
            if len(page) < page_size:
                return rows
            offset += page_size


def fetch_measurements(selected_day: date, include_provisional: bool = True) -> tuple[list[dict], datetime]:
    start, end = day_bounds_utc(selected_day)
    return fetch_interval_measurements(start, end, include_provisional)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_interval_measurements(start_utc: datetime, end_utc: datetime,
                                include_provisional: bool = True) -> tuple[list[dict], datetime]:
    start, end = interval_bounds_utc(start_utc, end_utc)
    schema_fields = {column.get("fieldName") for column in get_schema(MEASUREMENTS_DATASET)}
    missing = set(MEASUREMENT_COLUMNS[1:]) - schema_fields
    if missing:
        raise DataError(f"Falten camps a l'esquema de lectures: {', '.join(sorted(missing))}.")
    columns = [column for column in MEASUREMENT_COLUMNS if column in schema_fields]
    # calendar_date no porta sufix Z, però Meteocat documenta aquestes hores com UTC.
    where = (
        f"codi_variable = '{PRECIPITATION_VARIABLE}' "
        f"AND data_lectura >= '{start.replace(tzinfo=None).isoformat()}' "
        f"AND data_lectura < '{end.replace(tzinfo=None).isoformat()}' "
    )
    if include_provisional:
        where += "AND (codi_estat IN ('V', 'T') OR codi_estat IS NULL OR codi_estat IN ('', ' '))"
    else:
        where += "AND codi_estat = 'V'"
    rows = _fetch_rows(MEASUREMENTS_DATASET, {
        "$select": ",".join(columns), "$where": where,
        "$order": "data_lectura,codi_estacio,codi_base" + (",id" if "id" in columns else ""),
    })
    return rows, datetime.now(LOCAL_TZ)


def _normal_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", value)


def _find_field(schema: list[dict], *aliases: str, required: bool = False) -> str | None:
    for alias in aliases:
        for column in schema:
            field = column.get("fieldName", "")
            if _normal_name(alias) in {_normal_name(field), _normal_name(column.get("name", ""))}:
                if re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", field):
                    return field
    if required:
        raise DataError(f"No s'ha trobat el camp d'estacions «{aliases[0]}».")
    return None


def _point_coordinates(value) -> tuple[float | None, float | None]:
    """GeoJSON: [longitud, latitud]; SODA location: latitude/longitude."""
    if isinstance(value, dict):
        coords = value.get("coordinates")
        if isinstance(coords, (list, tuple)) and len(coords) >= 2:
            return coords[1], coords[0]
        return value.get("latitude"), value.get("longitude")
    return None, None


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype("string").str.replace(",", ".", regex=False), errors="coerce")


def normalize_stations(rows: list[dict], schema: list[dict]) -> pd.DataFrame:
    mapping = {
        "codi_estacio": _find_field(schema, "codi_estacio", required=True),
        "nom": _find_field(schema, "nom_estacio", "nom", required=True),
        "municipi": _find_field(schema, "nom_municipi", "municipi", required=True),
        "comarca": _find_field(schema, "nom_comarca", "comarca", required=True),
        "latitud": _find_field(schema, "latitud", "latitude"),
        "longitud": _find_field(schema, "longitud", "longitude"),
        "altitud": _find_field(schema, "altitud", "altitude"),
        "estat_estacio": _find_field(schema, "nom_estat_ema", "nom_estat", "codi_estat_ema"),
    }
    geo = next((col["fieldName"] for col in schema if col.get("dataTypeName") in {"point", "location"}), None)
    if not (mapping["latitud"] and mapping["longitud"]) and not geo:
        raise DataError("L'esquema d'estacions no conté coordenades reconegudes.")
    raw = pd.DataFrame(rows)
    normalized = pd.DataFrame(index=raw.index)
    for target, source in mapping.items():
        normalized[target] = raw[source] if source and source in raw else pd.NA
    for field in ("latitud", "longitud", "altitud"):
        normalized[field] = _numeric(normalized[field])
    if geo and geo in raw:
        points = raw[geo].map(_point_coordinates)
        normalized["latitud"] = normalized["latitud"].fillna(_numeric(points.map(lambda point: point[0])))
        normalized["longitud"] = normalized["longitud"].fillna(_numeric(points.map(lambda point: point[1])))
    for field in ("codi_estacio", "nom", "municipi", "comarca", "estat_estacio"):
        normalized[field] = normalized[field].astype("string").str.strip()
    normalized["codi_estacio"] = normalized["codi_estacio"].str.upper()
    normalized = normalized[normalized["codi_estacio"].notna() & normalized["codi_estacio"].ne("")]
    # Si les metadades tenen diversos períodes d'una estació, conserva el més recent.
    start_field = _find_field(schema, "data_inici", "data_alta")
    if start_field and start_field in raw:
        normalized["_inici"] = pd.to_datetime(raw[start_field], utc=True, errors="coerce", format="mixed")
        normalized = normalized.sort_values("_inici", na_position="first")
    normalized = normalized.drop_duplicates("codi_estacio", keep="last")
    # Descartem només les coordenades invàlides; l'estació continua al rànquing.
    valid_coords = normalized["latitud"].between(40, 44) & normalized["longitud"].between(-1, 4)
    normalized.loc[~valid_coords, ["latitud", "longitud"]] = float("nan")
    return normalized[STATION_COLUMNS].reset_index(drop=True)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_stations() -> pd.DataFrame:
    schema = get_schema(STATIONS_DATASET)
    aliases = [
        ("codi_estacio",), ("nom_estacio", "nom"), ("nom_municipi", "municipi"),
        ("nom_comarca", "comarca"), ("latitud", "latitude"), ("longitud", "longitude"),
        ("altitud", "altitude"), ("nom_estat_ema", "nom_estat", "codi_estat_ema"),
        ("data_inici", "data_alta"),
    ]
    fields = [_find_field(schema, *names) for names in aliases]
    fields.extend(col["fieldName"] for col in schema if col.get("dataTypeName") in {"point", "location"})
    selected = list(dict.fromkeys(field for field in fields if field))
    code = _find_field(schema, "codi_estacio", required=True)
    rows = _fetch_rows(STATIONS_DATASET, {"$select": ",".join(selected), "$order": code})
    if not rows:
        raise DataError("El dataset de metadades d'estacions és buit.")
    return normalize_stations(rows, schema)


def calculate_totals(rows: list[dict], selected_day: date, include_provisional: bool = True) -> tuple[pd.DataFrame, dict]:
    start, end = day_bounds_utc(selected_day)
    return calculate_interval_totals(rows, start, end, include_provisional)


def _expected_slots(start: datetime, end: datetime, base: str) -> int:
    """Nombre d'inicis d'interval SH/HO dins [start, end), alineats en UTC."""
    minutes = 30 if base == "SH" else 60
    step = timedelta(minutes=minutes)
    first = start.replace(minute=(start.minute // minutes) * minutes, second=0, microsecond=0)
    if first < start:
        first += step
    return max(0, -((first - end) // step))


def calculate_interval_totals(rows: list[dict], start: datetime, end: datetime,
                               include_provisional: bool = True) -> tuple[pd.DataFrame, dict]:
    start, end = interval_bounds_utc(start, end)
    report = {"rebudes": len(rows), "descartades": 0, "duplicades": 0,
              "conflictes": 0, "altres_bases": 0, "estacions_bases_mixtes": 0}
    if not rows:
        return pd.DataFrame(columns=TOTAL_COLUMNS), report
    frame = pd.DataFrame(rows).reindex(columns=MEASUREMENT_COLUMNS)
    for field in ("id", "codi_estacio", "codi_variable", "codi_estat", "codi_base"):
        frame[field] = frame[field].fillna("").astype("string").str.strip().str.upper()
    frame["valor_lectura"] = _numeric(frame["valor_lectura"])
    frame["data_lectura"] = pd.to_datetime(frame["data_lectura"], utc=True, errors="coerce", format="mixed")
    frame["hora_local"] = frame["data_lectura"].dt.tz_convert(LOCAL_TZ)
    accepted_states = ["V", "T", ""] if include_provisional else ["V"]
    valid = (
        frame["codi_estacio"].ne("") & frame["codi_variable"].eq(PRECIPITATION_VARIABLE)
        & frame["codi_estat"].isin(accepted_states) & frame["codi_base"].isin(["SH", "HO"])
        & frame["valor_lectura"].notna() & frame["valor_lectura"].ge(0)
        & frame["valor_lectura"].map(lambda value: pd.notna(value) and math.isfinite(value))
        & frame["data_lectura"].ge(start) & frame["data_lectura"].lt(end)
    )
    report["descartades"] = int((~valid).sum())
    frame = frame.loc[valid].copy()
    if frame.empty:
        return pd.DataFrame(columns=TOTAL_COLUMNS), report
    keys = ["codi_estacio", "data_lectura", "codi_variable", "codi_base"]
    report["conflictes"] = int((frame.groupby(keys)["valor_lectura"].nunique() > 1).sum())
    # Prioritat V > T > sense estat; empat determinista pel codi de registre i valor.
    frame["_qualitat"] = frame["codi_estat"].map({"V": 0, "T": 1, "": 2})
    frame = frame.sort_values(["_qualitat", "id", "valor_lectura"], ascending=[True, False, False])
    before = len(frame)
    frame = frame.drop_duplicates(keys, keep="first")
    report["duplicades"] = before - len(frame)
    frame["_dia"] = frame["hora_local"].dt.date
    daily_keys = ["codi_estacio", "_dia"]
    bases_per_station = frame.groupby(daily_keys)["codi_base"].nunique()
    report["estacions_bases_mixtes"] = int((bases_per_station > 1).sum())
    # Una sola base per estació i dia; una estació pot canviar de base entre dies.
    preferred = frame.groupby(daily_keys)["codi_base"].transform(
        lambda bases: "SH" if "SH" in set(bases) else "HO"
    )
    keep_base = frame["codi_base"].eq(preferred)
    report["altres_bases"] = int((~keep_base).sum())
    frame = frame.loc[keep_base].copy()
    frame["_provisional"] = frame["codi_estat"].ne("V")
    totals = frame.groupby("codi_estacio", as_index=False).agg(
        precipitacio=("valor_lectura", "sum"), lectures=("valor_lectura", "size"),
        ultima_lectura=("hora_local", "max"),
        codi_base=("codi_base", lambda bases: " / ".join(sorted(set(bases)))),
        lectures_provisionals=("_provisional", "sum"),
    )
    latest = frame["data_lectura"].max()
    # Si el final encara és futur, s'exigeixen només els inicis ja publicats.
    expected_end = end
    if end > datetime.now(timezone.utc):
        expected_end = min(end, latest.to_pydatetime() + timedelta(microseconds=1))
    segments = []
    day = start.astimezone(LOCAL_TZ).date()
    while day <= (expected_end - timedelta(microseconds=1)).astimezone(LOCAL_TZ).date():
        day_start, day_end = day_bounds_utc(day)
        segments.append((day, max(start, day_start), min(expected_end, day_end)))
        day += timedelta(days=1)
    daily_bases = frame.drop_duplicates(daily_keys).set_index(daily_keys)["codi_base"].to_dict()
    expected_counts = []
    for station in totals.itertuples():
        fallback = "SH" if "SH" in station.codi_base else "HO"
        expected_counts.append(sum(
            _expected_slots(left, right, daily_bases.get((station.codi_estacio, day), fallback))
            for day, left, right in segments
        ))
    totals["lectures_esperades"] = expected_counts
    totals["estat_dades"] = totals["lectures_provisionals"].map(
        lambda count: "Pendent de validació" if count else "Validades (V)"
    )
    incomplete = totals["lectures"] < totals["lectures_esperades"]
    totals.loc[incomplete, "estat_dades"] += " · acumulat parcial (falten lectures)"
    return totals[TOTAL_COLUMNS], report


def load_daily_data(selected_day: date, include_provisional: bool = True) -> tuple[pd.DataFrame, dict]:
    start, end = day_bounds_utc(selected_day)
    return load_interval_data(start, end, include_provisional)


def load_interval_data(start: datetime, end: datetime,
                       include_provisional: bool = True) -> tuple[pd.DataFrame, dict]:
    # Normalitzar abans de consultar la cache distingeix les dues hores repetides.
    start, end = interval_bounds_utc(start, end)
    rows, queried_at = fetch_interval_measurements(start, end, include_provisional)
    stations = fetch_stations()
    totals, report = calculate_interval_totals(rows, start, end, include_provisional)
    merged = totals.merge(stations, on="codi_estacio", how="left", validate="one_to_one")
    for field in ("nom", "municipi", "comarca", "estat_estacio"):
        merged[field] = merged[field].fillna("Sense metadades")
    unknown_names = merged["nom"].eq("Sense metadades")
    merged.loc[unknown_names, "nom"] = merged.loc[unknown_names, "codi_estacio"]
    report.update({
        "consulta": queried_at,
        "inici": start.astimezone(LOCAL_TZ), "final": end.astimezone(LOCAL_TZ),
        "en_curs": end > datetime.now(timezone.utc),
        "ultima_lectura": totals["ultima_lectura"].max() if not totals.empty else None,
        "sense_coordenades": int(merged[["latitud", "longitud"]].isna().any(axis=1).sum()),
        "acumulats_parcials": int((totals["lectures"] < totals["lectures_esperades"]).sum()),
        "provisionals": int(totals["lectures_provisionals"].sum()),
        "comarques": sorted(stations["comarca"].dropna().unique().tolist()),
    })
    return merged.sort_values(["precipitacio", "nom"], ascending=[False, True]).reset_index(drop=True), report


def clear_cache() -> None:
    fetch_interval_measurements.clear()
    fetch_stations.clear()
    get_schema.clear()
