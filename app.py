"""Interfície Streamlit del mapa de precipitació acumulada XEMA."""

from datetime import date, datetime, time, timedelta, timezone
from base64 import b64encode
from html import escape
from math import isfinite
from pathlib import Path

import pydeck as pdk
import streamlit as st

from data import (HISTORY_DAYS, LOCAL_TZ, MAX_INTERVAL_DAYS, DataError, clear_cache, day_bounds_utc,
                  interval_bounds_utc, load_interval_data, local_datetime_candidates,
                  load_station_history, resolve_local_datetime)

st.set_page_config(page_title="Pluja Cat · Precipitació a Catalunya",
                   page_icon=str(Path(__file__).parent / "static" / "gota.svg"),
                   layout="wide", initial_sidebar_state="collapsed")

# Un sistema visual petit; els controls continuen sent natius de Streamlit.
RESPONSIVE_CSS = """
<style>
:root {
    --rain-bg: #f4f7f8; --rain-surface: #ffffff; --rain-secondary: #eaf0f2;
    --rain-text: #18323d; --rain-muted: #536974; --rain-border: #d5dfe3;
    --rain-primary: #176572; --rain-focus: #176572;
    --rain-radius-sm: 8px; --rain-radius-md: 12px;
    --rain-shadow: 0 2px 12px rgba(24,50,61,.05);
    --rain-font: 'Inter', sans-serif; --rain-type-small: .8125rem;
    --rain-type-label: .875rem; --rain-control-height: 44px; --rain-max-width: 1440px;
    --rain-space-1: 4px; --rain-space-2: 8px; --rain-space-3: 12px;
    --rain-space-4: 16px; --rain-space-6: 24px; --rain-space-8: 32px;
}
[data-testid="stAppViewContainer"] {background: var(--rain-bg);}
.block-container {padding: 3rem 2rem 2rem; max-width: var(--rain-max-width);}
[data-testid="stVerticalBlock"] {gap: var(--rain-space-4);}
h1 {font-size: 1.625rem !important; font-weight: 650 !important; letter-spacing: -.045em !important; line-height: 1.2 !important; padding: 0 !important;}
h2 {font-size: 1.25rem !important; font-weight: 600 !important; letter-spacing: -.025em; line-height: 1.3 !important; padding: 0 !important;}
h3 {font-size: 1rem !important; font-weight: 600 !important; padding: 0 !important;}
.brand-header {display: flex; align-items: center; gap: var(--rain-space-3);
    padding: 0 0 var(--rain-space-4); border-bottom: 1px solid var(--rain-border);}
.brand-mark {width: 32px; height: 36px; flex: 0 0 32px;}
.brand-header h1 {margin: 0;}
.brand-header p {margin: var(--rain-space-1) 0 0; color: var(--rain-muted);
    font-size: var(--rain-type-small); line-height: 1.5;}
.st-key-map_context {gap: var(--rain-space-1) !important;}
[data-testid="stCaptionContainer"] {color: var(--rain-muted); opacity: 1 !important; font-size: var(--rain-type-small);}
[data-testid="stWidgetLabel"] p {font-size: var(--rain-type-label);}
button, input {min-height: var(--rain-control-height);}
button {border-radius: var(--rain-radius-sm) !important;
    transition: background-color 120ms ease, border-color 120ms ease, color 120ms ease;}
[data-testid="stBaseButton-secondary"] {background: var(--rain-surface); border-color: var(--rain-border);}
[data-testid="stBaseButton-secondary"]:hover {background: var(--rain-secondary); border-color: var(--rain-primary); color: var(--rain-text);}
[data-testid="stBaseButton-primary"]:hover {background: #124f5a; border-color: #124f5a;}
[data-baseweb="input"], [data-baseweb="select"] > div {background: var(--rain-surface); border-radius: var(--rain-radius-sm);}
button[data-variant="segmented_control"] {padding: .5rem .375rem !important; min-height: var(--rain-control-height) !important;}
button[data-variant="segmented_control"] p {font-size: var(--rain-type-label) !important;}
[data-testid="stDateInputField"], [data-testid="stTimeInputField"], [data-testid="stTimeInputTimeDisplay"],
[data-testid="stNumberInputContainer"], div:has(> input[role="combobox"]) {
    min-height: var(--rain-control-height); background: var(--rain-surface); border-radius: var(--rain-radius-sm);}
button:focus-visible, input:focus-visible, [role="combobox"]:focus-visible,
summary:focus-visible {outline: 3px solid var(--rain-focus) !important; outline-offset: 2px;}
[data-testid="stDateInputField"]:focus-within, [data-testid="stTimeInputTimeDisplay"]:focus-within {
    outline: 3px solid var(--rain-focus); outline-offset: 2px;}
[data-testid="stExpander"] {border-color: var(--rain-border); border-radius: var(--rain-radius-sm); background: var(--rain-surface);}
[data-testid="stExpander"] summary {min-height: var(--rain-control-height);}
[data-testid="stExpander"] summary:hover {background: var(--rain-secondary);}
.st-key-controls [data-testid="stHorizontalBlock"],
.st-key-interval_controls [data-testid="stHorizontalBlock"] {gap: var(--rain-space-3);}
.map-period {margin: 0 !important; color: var(--rain-text); font-size: 1rem; font-weight: 600 !important; line-height: 1.5; font-variant-numeric: tabular-nums;}
.map-scope {margin: var(--rain-space-1) 0 0 !important; color: var(--rain-muted); font-size: var(--rain-type-small) !important; line-height: 1.5;}
.weather-summary {display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
    gap: var(--rain-space-6); padding: var(--rain-space-3) 0;
    border-bottom: 1px solid var(--rain-border);}
.weather-summary dl {margin: 0; min-width: 0;}
.weather-summary dt {font-size: var(--rain-type-small); color: var(--rain-muted);}
.weather-summary dd {display: flex; align-items: baseline; gap: var(--rain-space-3);
    margin: var(--rain-space-1) 0 0; color: var(--rain-text);
    font-size: 1.75rem; font-weight: 600; letter-spacing: -.035em; line-height: 1.15; font-variant-numeric: tabular-nums;}
.weather-summary dl:first-child dd {font-size: 2.25rem;}
.rain-unit {font-size: .55em; font-weight: 500; letter-spacing: 0; color: var(--rain-muted);}
.weather-summary small {font-size: var(--rain-type-small); letter-spacing: 0;
    font-weight: 400; line-height: 1.4; color: var(--rain-muted);}
.st-key-map_context_updates {gap: var(--rain-space-1) !important;}
.st-key-map_surface {gap: 0 !important; background: var(--rain-surface); border: 1px solid var(--rain-border);
    border-radius: var(--rain-radius-md); box-shadow: var(--rain-shadow); overflow: hidden;}
.st-key-map_surface [data-testid="stVerticalBlock"] {gap: 0;}
.st-key-rain_map [data-testid="stDeckGlJsonChart"] {overflow: hidden;}
.st-key-rain_map .maplibregl-ctrl-group button {width: 44px; height: 44px;}
.map-legend {padding: var(--rain-space-3) var(--rain-space-4); border-top: 1px solid var(--rain-border);}
.legend-title {margin: 0 0 var(--rain-space-2) !important; font-size: var(--rain-type-small) !important; font-weight: 500 !important; color: var(--rain-muted);}
.rain-legend {display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 2px; max-width: 780px; font-size: var(--rain-type-small); color: var(--rain-text);}
.rain-legend span {display: flex; flex-direction: column; gap: var(--rain-space-1); white-space: nowrap; line-height: 1.4;}
.rain-legend i {height: 6px; display: block;}
.rain-legend span:first-child i {border-radius: 3px 0 0 3px;}
.rain-legend span:last-child i {border-radius: 0 3px 3px 0;}
.st-key-station_details {border-top: 1px solid var(--rain-border); padding-top: var(--rain-space-4);}
.station-rain {font-size: 2.25rem !important; font-weight: 600 !important; letter-spacing: -.035em; color: var(--rain-text); margin: 0 !important; line-height: 1.2; font-variant-numeric: tabular-nums;}
.st-key-history_controls [data-testid="stHorizontalBlock"] {gap: var(--rain-space-6);}
[data-testid="stDataFrame"] {border-radius: var(--rain-radius-sm);}
.st-key-ranking_controls [data-testid="stHorizontalBlock"] {align-items: end;}
@media (prefers-reduced-motion: reduce) {button {transition: none;}}
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
    .block-container {padding: 3rem 1rem 2rem;}
    [data-testid="stVerticalBlock"] {gap: var(--rain-space-3);}
    h1 {font-size: 1.5rem !important;}
    .brand-header {padding-bottom: var(--rain-space-3);}
    .brand-header p {max-width: 30ch;}
    .st-key-controls button {padding: .4rem .5rem;}
    .st-key-controls button p {white-space: normal !important;}
    .weather-summary {gap: var(--rain-space-3); grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr);}
    .weather-summary dd {display: block; font-size: 1.5rem;}
    .weather-summary dl:first-child dd {font-size: 2rem;}
    .weather-summary small {display: block; margin-top: var(--rain-space-1);}
    /* Streamlit reserva l'alçada amb flex-basis, a més del mapa interior. */
    .st-key-rain_map {flex: 0 0 auto !important;}
    .st-key-rain_map,
    .st-key-rain_map [data-testid="stFullScreenFrame"],
    .st-key-rain_map [data-testid="stDeckGlJsonChart"],
    .st-key-rain_map [data-testid="stDeckGlJsonChart"] > div:not([data-testid]) {
        height: clamp(360px, 52svh, 480px) !important; min-height: 0 !important;
    }
    .map-legend {padding: var(--rain-space-3);}
    .rain-legend {grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--rain-space-2) var(--rain-space-3); font-size: .75rem;}
    .rain-legend i {border-radius: 3px !important;}
    .st-key-history_controls [data-testid="stHorizontalBlock"] {flex-direction: column; gap: var(--rain-space-3);}
    .st-key-history_controls [data-testid="stColumn"] {width: 100% !important;}
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


def rain_value_html(value: float) -> str:
    """La unitat pesa menys visualment; el valor continua llegible com a text."""
    return format_mm(value).replace(" mm", ' <span class="rain-unit">mm</span>')


def keep_exclusive_selection(key: str) -> None:
    # Un segment actiu es pot desmarcar a Streamlit: conserva la darrera opció.
    previous_key = f"_{key}_selected"
    if st.session_state[key] is None:
        st.session_state[key] = st.session_state[previous_key]
    else:
        st.session_state[previous_key] = st.session_state[key]


def exclusive_control(label: str, options, key: str, format_func=str):
    previous = st.session_state.setdefault(f"_{key}_selected", options[0])
    st.session_state.setdefault(key, previous)
    return st.segmented_control(label, options, key=key,
                                format_func=format_func, on_change=keep_exclusive_selection, args=(key,))


def period_label(start: datetime, end: datetime, selected_day: date | None) -> str:
    if selected_day is not None:
        prefix = "Avui" if selected_day == datetime.now(LOCAL_TZ).date() else "Dia"
        return f"{prefix} · {selected_day:%d/%m/%Y}"
    return f"{start.astimezone(LOCAL_TZ):%d/%m/%Y %H:%M %Z} → {end.astimezone(LOCAL_TZ):%d/%m/%Y %H:%M %Z}"


def render_station_history(station_code: str, period_end: datetime, include_provisional: bool) -> None:
    st.markdown("### Histograma de precipitació")
    with st.container(key="history_controls"):
        horizon_col, grouping_col = st.columns([3, 2])
        with horizon_col:
            days = exclusive_control("Horitzó temporal", HISTORY_DAYS, "history_days",
                                     lambda value: "1 dia" if value == 1 else f"{value} dies")
        with grouping_col:
            grouping = exclusive_control("Agrupa la pluja per", ["Hores", "Dies"], "history_grouping")
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
        "background": "#ffffff",
        "config": {"font": "Inter", "view": {"stroke": None},
                   "axis": {"labelColor": "#536974", "titleColor": "#18323d",
                            "gridColor": "#eaf0f2", "domainColor": "#d5dfe3"},
                   "legend": {"labelColor": "#536974"}},
        "mark": {"type": "bar", "tooltip": True, "cornerRadiusTopLeft": 2, "cornerRadiusTopRight": 2},
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
        st.caption("L'històric inclou dades pendents de validació definitiva per Meteocat.")
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
        tooltip={"html": '<div style="font-weight:600">{nom}</div>'
                           '<div style="font-size:12px;color:#c8d8de">{municipi} · {comarca}</div>'
                           '<div style="font-size:24px;font-weight:600;margin:8px 0;font-variant-numeric:tabular-nums">{pluja_text}</div>'
                           '<div style="font-size:12px">{periode_text}</div>'
                           '<div style="font-size:12px;margin-top:8px">{lectures} lectures · {estat_dades}'
                           '<br/>Última lectura: {ultima_text}</div>',
                 "style": {"backgroundColor": "#18323d", "color": "white", "fontFamily": "Inter, sans-serif",
                           "fontSize": "14px", "lineHeight": "1.5", "padding": "16px",
                           "borderRadius": "8px", "maxWidth": "300px", "boxShadow": "0 2px 12px rgba(24,50,61,.15)"}},
    )
    with st.container(key="map_surface"):
        selection = st.pydeck_chart(deck, height=600, key="rain_map",
                                    on_select="rerun", selection_mode="single-object")
        items = []
        for _, label, color in SCALE:
            rgb = ",".join(map(str, color[:3]))
            items.append(f'<span><i aria-hidden="true" style="background:rgb({rgb});"></i>{label}</span>')
        st.markdown('<section class="map-legend" aria-label="Llegenda de precipitació">'
                    '<p class="legend-title">Precipitació acumulada · mm</p>'
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
        format_func=lambda code: f"{stations.loc[code, 'nom']} · {stations.loc[code, 'comarca']}",
    )
    if station_code is not None:
        station = stations.loc[station_code]
        with st.container(key="station_details"):
            st.caption("Estació seleccionada · " + period_text)
            st.header(station["nom"])
            st.caption(f"{station['municipi']} · {station['comarca']}")
            st.markdown(f'<p class="station-rain">{rain_value_html(station["precipitacio"])}</p>', unsafe_allow_html=True)
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
            mode = exclusive_control("Període", ["Un dia", "Entre dues dates i hores"], "period_mode",
                                     lambda value: "Dates i hores" if value != "Un dia" else value)
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
        mark = (Path(__file__).parent / "static" / "gota.svg").read_text(encoding="utf-8")
        mark_url = "data:image/svg+xml;base64," + b64encode(mark.encode()).decode()
        st.html(f'<header class="brand-header"><img class="brand-mark" src="{mark_url}" alt=""/>'
                '<div><h1>Pluja Cat</h1>'
                '<p>Pluja acumulada a Catalunya · XEMA — Meteocat</p></div></header>')
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
    maximum = rain_value_html(top["precipitacio"]) if top is not None else "Sense dades"
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
