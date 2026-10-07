"""Interfície Streamlit del mapa de precipitació acumulada XEMA."""

from datetime import date, datetime, time, timedelta, timezone
from html import escape
from math import isfinite

import pydeck as pdk
import streamlit as st

from data import (HISTORY_DAYS, LOCAL_TZ, MAX_INTERVAL_DAYS, DataError, clear_cache, day_bounds_utc,
                  interval_bounds_utc, load_interval_data, local_datetime_candidates,
                  load_station_history, resolve_local_datetime)

st.set_page_config(page_title="Pluja acumulada a Catalunya", page_icon="🌧️",
                   layout="wide", initial_sidebar_state="collapsed")

# Un sistema visual petit; els controls continuen sent natius de Streamlit.
RESPONSIVE_CSS = """
<style>
:root {
    --rain-text: #182b3a; --rain-muted: #506170; --rain-border: #d9e1e7;
    --rain-surface: #f4f6f8; --rain-focus: #2563eb; --rain-radius: 8px;
    --rain-space-1: 4px; --rain-space-2: 8px; --rain-space-3: 12px;
    --rain-space-4: 16px; --rain-space-6: 24px;
}
.block-container {padding: 1rem 2rem 2rem; max-width: 1480px;}
[data-testid="stVerticalBlock"] {gap: var(--rain-space-4);}
h1 {font-size: clamp(1.5rem, 2.5vw, 2rem) !important; line-height: 1.2 !important; padding-bottom: 0 !important;}
h2 {font-size: 1.35rem !important; line-height: 1.3 !important; padding: 0 !important;}
h3 {font-size: 1.15rem !important; padding: 0 !important;}
.st-key-header {gap: var(--rain-space-2) !important;}
.st-key-header [data-testid="stCaptionContainer"] {margin-top: var(--rain-space-2);}
.st-key-map_context {gap: var(--rain-space-1) !important;}
[data-testid="stCaptionContainer"] {color: var(--rain-muted); opacity: 1 !important;}
button, input {min-height: 44px;}
button {border-radius: var(--rain-radius) !important;}
button:focus-visible, input:focus-visible, [role="combobox"]:focus-visible,
summary:focus-visible {outline: 3px solid var(--rain-focus) !important; outline-offset: 2px;}
[data-testid="stExpander"] {border-color: var(--rain-border); border-radius: var(--rain-radius);}
[data-testid="stExpander"] summary {min-height: 44px;}
.st-key-controls [data-testid="stHorizontalBlock"],
.st-key-interval_controls [data-testid="stHorizontalBlock"] {gap: var(--rain-space-3);}
.st-key-controls [role="radiogroup"] {min-height: 44px; align-items: center;}
.st-key-controls [data-testid="stRadio"] label {min-height: 36px;}
.map-period {margin: 0; color: var(--rain-text); font-size: 1rem; font-weight: 650; line-height: 1.5;}
.map-scope {margin: 0; color: var(--rain-muted); font-size: .85rem; line-height: 1.5;}
.weather-summary {display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
    gap: var(--rain-space-6); padding: var(--rain-space-2) 0;
    border-top: 1px solid var(--rain-border); border-bottom: 1px solid var(--rain-border);}
.weather-summary dl {margin: 0; min-width: 0;}
.weather-summary dt {font-size: .85rem; color: var(--rain-muted);}
.weather-summary dd {display: flex; align-items: baseline; gap: var(--rain-space-3);
    margin: var(--rain-space-1) 0 0; color: var(--rain-text);
    font-size: 1.5rem; font-weight: 650; line-height: 1.15; font-variant-numeric: tabular-nums;}
.weather-summary small {font-size: .85rem;
    font-weight: 400; line-height: 1.4; color: var(--rain-muted);}
.st-key-map_context_updates {gap: var(--rain-space-1) !important;}
.st-key-rain_map [data-testid="stDeckGlJsonChart"] {border-radius: var(--rain-radius); overflow: hidden;}
.st-key-rain_map .maplibregl-ctrl-group button {width: 44px; height: 44px;}
.legend-title {margin: 0 0 var(--rain-space-2); font-size: .8rem; font-weight: 600; color: var(--rain-muted);}
.rain-legend {display: flex; flex-wrap: wrap; gap: var(--rain-space-2) var(--rain-space-4); font-size: .85rem; color: var(--rain-text);}
.rain-legend span {display: inline-flex; align-items: center; gap: var(--rain-space-2); white-space: nowrap;}
.rain-legend i {width: 12px; height: 12px; border-radius: 50%; display: inline-block; flex: 0 0 12px; border: 1px solid rgba(0,0,0,.12);}
.st-key-station_details {border-top: 1px solid var(--rain-border); padding-top: var(--rain-space-4);}
.station-rain {font-size: 1.75rem; font-weight: 650; color: var(--rain-text); margin: 0; font-variant-numeric: tabular-nums;}
.st-key-ranking_controls [data-testid="stHorizontalBlock"] {align-items: end;}
@media (max-width: 900px) {
    .block-container {padding-right: 1rem; padding-left: 1rem;}
    .st-key-controls [data-testid="stHorizontalBlock"] {
        display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    }
    .st-key-controls [data-testid="stColumn"]:first-child {grid-column: 1 / -1;}
    .st-key-controls [data-testid="stColumn"],
    .st-key-interval_controls [data-testid="stColumn"] {width: 100% !important; min-width: 0 !important;}
    .st-key-interval_controls [data-testid="stHorizontalBlock"] {display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));}
}
@media (max-width: 640px) {
    /* Deixa espai per a la barra fixa de Streamlit de 60 px. */
    .block-container {padding: 2rem 1rem 2rem;}
    [data-testid="stVerticalBlock"] {gap: var(--rain-space-3);}
    h1 {font-size: 1.5rem !important;}
    .st-key-controls button {padding: .4rem .5rem;}
    .st-key-controls button p {white-space: normal !important;}
    .weather-summary {gap: var(--rain-space-3); grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr);}
    .weather-summary dd {display: block;}
    .weather-summary small {display: block; margin-top: var(--rain-space-1);}
    /* Streamlit reserva l'alçada amb flex-basis, a més del mapa interior. */
    .st-key-rain_map {flex: 0 0 auto !important;}
    .st-key-rain_map,
    .st-key-rain_map [data-testid="stFullScreenFrame"],
    .st-key-rain_map [data-testid="stDeckGlJsonChart"],
    .st-key-rain_map [data-testid="stDeckGlJsonChart"] > div:not([data-testid]) {
        height: clamp(360px, 52svh, 480px) !important; min-height: 0 !important;
    }
    .rain-legend {display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--rain-space-2); font-size: .75rem;}
    .rain-legend span {gap: var(--rain-space-1);}
    .st-key-ranking_controls [data-testid="stHorizontalBlock"] {flex-direction: column; align-items: stretch;}
    .st-key-ranking_controls [data-testid="stColumn"] {width: 100% !important;}
    [data-testid="stDataFrame"] {max-width: 100%;}
}
</style>
"""

# Mida fixa en pantalla; només el color representa la precipitació.
POINT_RADIUS_PX = 6
# Llindars inclusius superiors i colors RGBA.
SCALE = [
    (0, "0 mm", [148, 163, 184, 200]),
    (5, "0–5 mm", [56, 189, 248, 230]),
    (20, "5–20 mm", [37, 99, 235, 240]),
    (50, "20–50 mm", [16, 185, 129, 240]),
    (100, "50–100 mm", [245, 158, 11, 245]),
    (200, "100–200 mm", [239, 68, 68, 250]),
    (float("inf"), ">200 mm", [168, 35, 190, 255]),
]


def rain_color(value: float) -> list[int]:
    for upper, _, color in SCALE:
        if value <= upper:
            return color
    return SCALE[-1][2]


def format_mm(value: float) -> str:
    """Una decimal quan cal, coma decimal catalana i unitat explícita."""
    if value is None or not isfinite(float(value)):
        return "Sense dades"
    return f"{float(value):.1f}".rstrip("0").rstrip(".").replace(".", ",") + " mm"


def period_label(start: datetime, end: datetime, selected_day: date | None) -> str:
    if selected_day is not None:
        prefix = "Avui" if selected_day == datetime.now(LOCAL_TZ).date() else "Dia"
        return f"{prefix} · {selected_day:%d/%m/%Y}"
    return f"{start.astimezone(LOCAL_TZ):%d/%m/%Y %H:%M %Z} → {end.astimezone(LOCAL_TZ):%d/%m/%Y %H:%M %Z}"


def render_station_history(station_code: str, period_end: datetime, include_provisional: bool) -> None:
    st.markdown("### Histograma de precipitació")
    days = st.radio("Horitzó temporal", HISTORY_DAYS, horizontal=True, key="history_days",
                     format_func=lambda value: "1 dia" if value == 1 else f"{value} dies")
    grouping = st.radio("Agrupa la pluja per", ["Hores", "Dies"], horizontal=True, key="history_grouping")
    # Per a avui, no es consulta més enllà de l'últim tall de mitja hora.
    now = datetime.now(timezone.utc)
    current_cutoff = now.replace(minute=now.minute // 30 * 30, second=0, microsecond=0)
    history_end = min(period_end.astimezone(timezone.utc), current_cutoff)
    try:
        with st.spinner("Consultant l'històric d'aquesta estació…"):
            history, report = load_station_history(station_code, history_end, days, grouping, include_provisional)
    except DataError as exc:
        st.warning(str(exc))
        st.caption("Prem «Actualitza dades» per tornar a consultar l'històric.")
        return
    st.caption(f"Darreres {days * 24} hores · {report['inici']:%d/%m/%Y %H:%M %Z} → "
               f"{report['final']:%d/%m/%Y %H:%M %Z}. Inici inclòs, final exclòs.")
    if not report["lectures"]:
        st.info("Aquesta estació no té lectures disponibles per a aquest horitzó i criteri de validació.")
        return
    st.write(f"Acumulat de l'històric: **{format_mm(report['precipitacio'])}** · "
             f"**{report['lectures']}** lectures")
    st.caption(f"Última lectura de l'històric: {report['ultima_lectura']:%d/%m/%Y %H:%M %Z}")
    # Etiquetes locals explícites: l'hora del gràfic no depèn del fus del navegador.
    spec = {
        "height": 300,
        "mark": {"type": "bar", "tooltip": True},
        "encoding": {
            "x": {"field": "periode", "type": "ordinal", "title": "Hora local de Catalunya" if grouping == "Hores" else "Dia local de Catalunya",
                  "sort": {"field": "ordre", "order": "ascending"},
                  "axis": {"labelAngle": -45, "labelOverlap": True, "labelLimit": 130}},
            "y": {"field": "precipitacio", "type": "quantitative", "title": "Precipitació (mm)",
                  "scale": {"zero": True}},
            "color": {"field": "cobertura", "type": "nominal", "title": None,
                      "scale": {"domain": ["Complet", "Acumulat parcial"], "range": ["#2563eb", "#f59e0b"]},
                      "legend": {"orient": "bottom"}},
            "tooltip": [
                {"field": "inici", "type": "nominal", "title": "Inici"},
                {"field": "final", "type": "nominal", "title": "Final"},
                {"field": "pluja_text", "type": "nominal", "title": "Precipitació"},
                {"field": "lectures", "type": "quantitative", "title": "Lectures"},
                {"field": "lectures_esperades", "type": "quantitative", "title": "Lectures esperades"},
                {"field": "estat", "type": "nominal", "title": "Estat"},
            ],
        },
    }
    chart_data = history.assign(pluja_text=history["precipitacio"].map(format_mm))
    st.vega_lite_chart(chart_data, spec, width="stretch", key="station_histogram")
    st.caption("Cada barra suma la pluja d'aquella hora o dia. Els buits sense lectures no equivalen a 0 mm. "
               "Les hores repetides es distingeixen amb CEST/CET; els dies segueixen les mitjanits de Catalunya.")
    if report["barres_sense_dades"] or report["barres_parcials"]:
        st.warning(f"Històric incomplet: {report['barres_sense_dades']} períodes sense lectures i "
                   f"{report['barres_parcials']} períodes amb lectures incompletes. L'acumulat disponible pot ser parcial.")
    if report["provisionals"]:
        st.caption("⚠️ L'històric inclou dades pendents de validació definitiva per Meteocat.")
    if report["conflictes"] or report["altres_bases"] or report["descartades"]:
        st.caption(f"Control de qualitat de l'històric: {report['conflictes']} duplicats amb valors diferents, "
                   f"{report['altres_bases']} lectures de bases alternatives excloses i "
                   f"{report['descartades']} registres no vàlids descartats.")
    with st.expander("Lectures agrupades de l'històric"):
        table = history[["inici", "final", "precipitacio", "lectures", "lectures_esperades", "estat"]].rename(columns={
            "inici": "Inici", "final": "Final", "precipitacio": "Precipitació", "lectures": "Lectures",
            "lectures_esperades": "Esperades", "estat": "Estat",
        })
        st.dataframe(table.style.format({"Precipitació": format_mm}, na_rep="Sense dades"),
                     hide_index=True, width="stretch")


def render_map(frame, period_end: datetime, include_provisional: bool, period_text: str = "",
               status_text: str = "") -> None:
    # Dibuixa els episodis més intensos al final perquè quedin per sobre dels altres punts.
    points = frame.dropna(subset=["latitud", "longitud"]).sort_values("precipitacio").copy()
    points["color"] = points["precipitacio"].map(rain_color)
    points["pluja_text"] = points["precipitacio"].map(format_mm)
    points["ultima_text"] = points["ultima_lectura"].map(lambda value: value.strftime("%d/%m/%Y %H:%M %Z"))
    points["periode_text"] = escape(period_text)
    for field in ("nom", "municipi", "comarca"):
        points[field] = points[field].map(lambda value: escape(str(value)))
    fields = ["codi_estacio", "nom", "municipi", "comarca", "latitud", "longitud",
              "color", "pluja_text", "lectures", "ultima_text", "estat_dades", "periode_text"]
    layer = pdk.Layer(
        "ScatterplotLayer", data=points[fields].to_dict("records"),
        get_position="[longitud, latitud]", get_fill_color="color", get_radius=POINT_RADIUS_PX,
        # Pydeck exigeix cometes internes per a un literal, en lloc d'un accessor.
        radius_units="'pixels'", radius_min_pixels=POINT_RADIUS_PX, radius_max_pixels=POINT_RADIUS_PX,
        id="estacions-xema", pickable=True, stroked=True, filled=True,
        get_line_color=[255, 255, 255, 230], line_width_min_pixels=1,
        auto_highlight=True, highlight_color=[255, 255, 255, 80],
    )
    deck = pdk.Deck(
        # El zoom inicial permet veure Catalunya sencera també en una pantalla estreta.
        layers=[layer], initial_view_state=pdk.ViewState(latitude=41.8, longitude=1.7, zoom=6),
        map_provider="carto", map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        tooltip={"html": "<b>{nom}</b><br/>{municipi} · {comarca}<br/><b>{pluja_text}</b>"
                           "<br/>{periode_text}<br/>Última lectura: {ultima_text}",
                 "style": {"backgroundColor": "#182b3a", "color": "white", "fontSize": "14px",
                           "lineHeight": "1.5", "padding": "12px", "borderRadius": "8px", "maxWidth": "280px"}},
    )
    selection = st.pydeck_chart(deck, height=600, key="rain_map",
                                on_select="rerun", selection_mode="single-object")
    items = []
    for _, label, color in SCALE:
        rgb = ",".join(map(str, color[:3]))
        items.append(f'<span><i aria-hidden="true" style="background:rgb({rgb});"></i>{label}</span>')
    st.markdown('<section aria-label="Llegenda de precipitació"><p class="legend-title">Precipitació acumulada</p>'
                '<div class="rain-legend">' + "".join(items) + "</div></section>", unsafe_allow_html=True)
    if status_text:
        st.caption(status_text)
    st.caption("Toca un punt o cerca una estació per consultar-ne l'acumulat i l'histograma.")
    selected_objects = selection.selection.objects.get("estacions-xema", [])
    stations = frame.sort_values("nom").set_index("codi_estacio")
    codes = stations.index.tolist()
    map_code = selected_objects[0].get("codi_estacio") if selected_objects else None
    # El clic i el selector comparteixen selecció; un clic antic no sobreescriu el teclat.
    if map_code != st.session_state.get("last_map_station"):
        st.session_state.last_map_station = map_code
        if map_code in codes:
            st.session_state.station_picker = map_code
    if st.session_state.get("station_picker") not in codes:
        st.session_state.station_picker = None
    station_code = st.selectbox(
        "Consulta una estació", codes, index=None, key="station_picker",
        placeholder="Cerca pel nom de l'estació…", disabled=not codes,
        format_func=lambda code: f"{stations.loc[code, 'nom']} · {stations.loc[code, 'comarca']} · "
                                 f"{format_mm(stations.loc[code, 'precipitacio'])}",
    )
    if station_code is not None:
        station = stations.loc[station_code]
        with st.container(key="station_details"):
            st.caption("Estació seleccionada · " + period_text)
            st.header(station["nom"])
            st.caption(f"{station['municipi']} · {station['comarca']}")
            st.markdown(f'<p class="station-rain">{format_mm(station["precipitacio"])}</p>', unsafe_allow_html=True)
            st.caption(f"Última lectura: {station['ultima_lectura']:%d/%m/%Y %H:%M %Z} · {station['lectures']} lectures")
            st.caption(f"Estat de les dades: {station['estat_dades']}")
            render_station_history(station_code, period_end, include_provisional)


def choose_local_timestamp(value: datetime, label: str, key: str) -> datetime:
    candidates = local_datetime_candidates(value)
    occurrence = None
    if len(candidates) == 2:
        occurrence = st.selectbox(
            f"{label}: hora repetida pel canvi d'hora", [0, 1], key=key,
            format_func=lambda index: (
                f"{'Primera' if index == 0 else 'Segona'} — "
                f"{candidates[index]:%Z} (UTC{candidates[index]:%z})"
            ),
        )
    return resolve_local_datetime(value, occurrence)


def period_controls() -> tuple[datetime, datetime, date | None]:
    now = datetime.now(LOCAL_TZ)
    with st.container(key="controls"):
        mode_col, date_col, button_col = st.columns([2, 2, 1], vertical_alignment="bottom")
        with mode_col:
            mode = st.radio("Període", ["Un dia", "Entre dues dates i hores"], horizontal=True,
                            key="period_mode", label_visibility="collapsed")
        with button_col:
            if st.button("Actualitza dades", width="stretch"):
                clear_cache()
        if mode == "Un dia":
            with date_col:
                selected_day = st.date_input("Data seleccionada", value=now.date(),
                                             min_value=date(2009, 1, 1),
                                             max_value=now.date(), format="DD/MM/YYYY", key="day")
            start, end = day_bounds_utc(selected_day)
            return start, end, selected_day
        with date_col:
            st.caption("Tria els límits i prem «Mostra acumulat».")
    # Un formulari consulta només en aplicar el període, no en editar cada camp.
    with st.container(key="interval_controls"), st.expander("Dates i hores de l'interval", expanded=True):
        with st.form("interval_form", border=False):
            start_date_col, start_time_col, end_date_col, end_time_col = st.columns(4)
            with start_date_col:
                start_day = st.date_input("Data d'inici", value=now.date() - timedelta(days=1),
                                          min_value=date(2009, 1, 1), max_value=now.date(),
                                          format="DD/MM/YYYY", key="start_date")
            with start_time_col:
                start_time = st.time_input("Hora d'inici", value=time(0), step=1800, key="start_time")
            with end_date_col:
                end_day = st.date_input("Data de final", value=now.date(),
                                        min_value=date(2009, 1, 1), max_value=now.date(),
                                        format="DD/MM/YYYY", key="end_date")
            with end_time_col:
                end_time = st.time_input("Hora de final", value=time(now.hour, now.minute // 30 * 30),
                                         step=1800, key="end_time")
            st.form_submit_button("Mostra acumulat", type="primary", width="stretch")
        st.caption(f"Hores locals de Catalunya (Europe/Madrid). Inici inclòs, final exclòs. "
                   f"Màxim {MAX_INTERVAL_DAYS} dies per consulta.")
        start = choose_local_timestamp(datetime.combine(start_day, start_time), "Inici", "start_occurrence")
        end = choose_local_timestamp(datetime.combine(end_day, end_time), "Final", "end_occurrence")
        start, end = interval_bounds_utc(start, end)
        return start, end, None


def main() -> None:
    st.markdown(RESPONSIVE_CSS, unsafe_allow_html=True)
    with st.container(key="header"):
        st.title("🌧️ Pluja acumulada a Catalunya")
        st.caption("Estacions automàtiques XEMA — Meteocat")
    try:
        start, end, selected_day = period_controls()
    except DataError as exc:
        st.error(str(exc))
        st.stop()
    with st.expander("Filtres de territori i dades"):
        county_col, minimum_col, quality_col = st.columns([1, 1, 2])
        with quality_col:
            include_provisional = st.checkbox("Inclou dades pendents de validació", value=True, key="provisionals")
            st.caption("Desactiva-ho per consultar només dades validades per Meteocat.")
    try:
        with st.spinner("Consultant les dades públiques de XEMA…"):
            period_data, report = load_interval_data(start, end, include_provisional)
    except DataError as exc:
        st.error("No s'han pogut carregar les dades de XEMA. Prem «Actualitza dades» per tornar-ho a provar.")
        with st.expander("Detall de la incidència"):
            st.write(str(exc))
        st.stop()
    with county_col:
        county = st.selectbox("Comarca", ["Totes", *report["comarques"]], key="comarca")
    with minimum_col:
        minimum = st.number_input("Precipitació mínima (mm)", min_value=0.0, value=0.0, step=1.0, key="minim")
    filtered = period_data[period_data["precipitacio"] >= minimum]
    if county != "Totes":
        filtered = filtered[filtered["comarca"] == county]
    latest = report["ultima_lectura"]
    top = filtered.iloc[0] if not filtered.empty else None
    label = period_label(start, end, selected_day)
    territory = county if county != "Totes" else "Catalunya"
    scope = territory + (f" · Mínim {format_mm(minimum)}" if minimum else "")
    scope += " · Inclou dades provisionals" if include_provisional else " · Només dades validades"
    with st.container(key="map_context"):
        st.markdown(f'<p class="map-period">{escape(label)}</p><p class="map-scope">{escape(scope)}</p>',
                    unsafe_allow_html=True)
    maximum = format_mm(top["precipitacio"]) if top is not None else "Sense dades"
    station = f"{top['nom']} · {top['comarca']}" if top is not None else "Cap estació amb dades per a aquesta selecció"
    wet_count = int(filtered["precipitacio"].gt(0).sum())
    st.markdown(
        '<div class="weather-summary"><dl><dt>Precipitació màxima</dt>'
        f'<dd>{maximum}<small>{escape(station)}</small></dd></dl>'
        f'<dl><dt>Estacions amb dades</dt><dd>{len(filtered)}<small>{wet_count} amb pluja</small></dd></dl></div>',
        unsafe_allow_html=True,
    )
    with st.container(key="map_context_updates"):
        last_text = latest.strftime("%d/%m/%Y · %H:%M %Z") if latest is not None else "Sense lectures"
        st.caption(f"Última dada: {last_text}" + (" · Període en curs" if report["en_curs"] else ""))
    notices = []
    if report["acumulats_parcials"]:
        notices.append(f"{report['acumulats_parcials']} estacions tenen acumulats parcials per manca de lectures")
    if report["sense_coordenades"]:
        notices.append(f"{report['sense_coordenades']} estacions no tenen coordenades vàlides i només apareixen a la taula")
    if report["descartades"]:
        notices.append(f"{report['descartades']} registres s'han descartat per dades no vàlides")
    if report["conflictes"]:
        notices.append(f"{report['conflictes']} lectures duplicades tenien valors diferents; s'ha prioritzat l'estat V, després T")
    if report["altres_bases"]:
        notices.append(f"{report['altres_bases']} lectures d'una base alternativa s'han exclòs; es prioritza SH per estació i dia")
    if period_data.empty:
        st.warning("No hi ha lectures de precipitació disponibles per a aquest període i aquest criteri de validació.")
    elif filtered.empty:
        st.info("Cap estació compleix els filtres seleccionats.")
    partial_count = int(filtered["lectures"].lt(filtered["lectures_esperades"]).sum())
    status = [f"Consulta de la font: {report['consulta']:%d/%m/%Y %H:%M %Z}."]
    if include_provisional:
        status.append("Les dades més recents poden estar pendents de validació definitiva per Meteocat.")
    if report["en_curs"]:
        status.append("Període en curs: acumulat fins a les lectures publicades.")
    if partial_count:
        status.append("Una estació té un acumulat parcial per manca de lectures." if partial_count == 1 else
                      f"{partial_count} estacions de la selecció tenen acumulats parcials per manca de lectures.")
    render_map(filtered, end, include_provisional, label, " ".join(status))
    with st.container(key="ranking_controls"):
        heading_col, count_col = st.columns([3, 1], vertical_alignment="bottom")
        with heading_col:
            st.header("Top estacions per precipitació")
        with count_col:
            count = st.selectbox("Nombre d'estacions a la taula", [20, 50, 100, "Totes"], index=0, key="ranking")
    ranking = filtered if count == "Totes" else filtered.head(count)
    table = ranking[["nom", "municipi", "comarca", "precipitacio"]].rename(columns={
        "nom": "Estació", "municipi": "Municipi", "comarca": "Comarca", "precipitacio": "Precipitació",
    })
    st.dataframe(table.style.format({"Precipitació": format_mm}, na_rep="Sense dades"),
                 hide_index=True, width="stretch", column_order=["Estació", "Precipitació", "Municipi", "Comarca"],
                 column_config={"Estació": st.column_config.TextColumn(width="medium"),
                                "Precipitació": st.column_config.NumberColumn("Pluja", width="small",
                                    help="Precipitació acumulada durant el període seleccionat, en mm.")})
    st.caption("Pots ordenar la taula clicant les capçaleres. Les estacions sense lectures no es consideren estacions amb 0 mm.")
    with st.expander("Com s'interpreten les dades?"):
        st.write("El mapa mostra la pluja observada a cada estació; no interpola entre punts. "
                 "Tots els cercles tenen 12 píxels de diàmetre i el color indica l'acumulat. "
                 "Els llindars superiors de la llegenda són inclusius. 1 mm = 1 litre/m². "
                 "Mapa base: CARTO / OpenStreetMap.")
        st.write("El període es tria en hora local de Catalunya (Europe/Madrid) i es consulta en UTC. "
                 "L'inici està inclòs i el final queda exclòs. La darrera lectura "
                 "disponible indica l'inici de l'últim interval publicat, no l'hora de consulta.")
        st.write("Se sumen les lectures que tenen l'inici dins del període seleccionat. "
                 "Cada lectura representa 30 minuts (SH) o una hora (HO). "
                 "Si les hores no coincideixen amb aquests límits, no s'interpola ni es prorrateja la pluja.")
        st.write("El resum, el mapa i el rànquing segueixen els filtres. L'hora de l'última "
                 "lectura disponible correspon al conjunt d'estacions del període.")
        st.write("Les estacions amb buits de lectures tenen acumulats parcials. "
                 "Es prioritza una sola base temporal per estació i dia per evitar duplicacions.")
        st.write("Les consultes es conserven durant cinc minuts. «Actualitza dades» torna a consultar la font; "
                 "l'hora de consulta i l'hora de l'última lectura són diferents.")
        if notices:
            st.write("Control de qualitat del conjunt del període: " + ". ".join(notices) + ".")
    st.caption("Dades: [XEMA / Meteocat — Dades Obertes de Catalunya]"
                "(https://analisi.transparenciacatalunya.cat/d/nzvn-apee) · "
                "[Metadades d'estacions](https://analisi.transparenciacatalunya.cat/d/yqwd-vj5e)")


if __name__ == "__main__":
    main()
