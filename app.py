"""Interfície Streamlit del mapa de precipitació acumulada XEMA."""

from datetime import date, datetime, time, timedelta, timezone

import pydeck as pdk
import streamlit as st

from data import (HISTORY_DAYS, LOCAL_TZ, MAX_INTERVAL_DAYS, DataError, clear_cache, day_bounds_utc,
                  interval_bounds_utc, load_interval_data, local_datetime_candidates,
                  load_station_history, resolve_local_datetime)

st.set_page_config(page_title="Pluja acumulada a Catalunya", page_icon="🌧️",
                   layout="wide", initial_sidebar_state="collapsed")

# Regles petites i locals: els widgets continuen sent natius de Streamlit.
RESPONSIVE_CSS = """
<style>
.block-container {padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1400px;}
h1 {font-size: clamp(1.7rem, 3vw, 2.4rem) !important; line-height: 1.2 !important;}
.st-key-context {gap: .35rem !important;}
.st-key-summary [data-testid="stHorizontalBlock"] {
    display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .75rem;
}
.st-key-summary [data-testid="stColumn"] {width: 100% !important; min-width: 0 !important;}
.st-key-summary [data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,.2); border-radius: 12px; padding: .6rem .75rem;
}
.rain-legend {display: flex; flex-wrap: wrap; gap: .5rem 1rem; font-size: .85rem;}
.rain-legend span {display: inline-flex; align-items: center; gap: 6px; white-space: nowrap;}
.rain-legend i {width: 12px; height: 12px; border-radius: 50%; display: inline-block;}
@media (max-width: 640px) {
    .block-container {padding: 1rem 1rem 2rem;}
    h1 {font-size: 1.7rem !important;}
    h3 {font-size: 1.15rem !important;}
    .st-key-controls [data-testid="stHorizontalBlock"] {
        display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .5rem;
    }
    .st-key-controls [data-testid="stColumn"] {width: 100% !important; min-width: 0 !important;}
    .st-key-controls button {min-height: 44px; padding: .4rem .5rem;}
    .st-key-controls button p {white-space: normal !important;}
    .st-key-summary [data-testid="stHorizontalBlock"] {gap: .4rem;}
    .st-key-summary [data-testid="stMetric"] {padding: .4rem;}
    .st-key-summary [data-testid="stMetricLabel"] p {font-size: .75rem;}
    .st-key-summary [data-testid="stMetricValue"] {font-size: clamp(.95rem, 4vw, 1.25rem);}
    .st-key-rain_map,
    .st-key-rain_map [data-testid="stDeckGlJsonChart"],
    .st-key-rain_map [data-testid="stDeckGlJsonChart"] > div:not([data-testid]) {
        height: clamp(320px, 52svh, 460px) !important; min-height: 0 !important;
    }
    .rain-legend {gap: .4rem .75rem; font-size: .75rem;}
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


def render_station_history(station_code: str, period_end: datetime, include_provisional: bool) -> None:
    st.markdown("#### Histograma de precipitació")
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
    st.write(f"Acumulat de l'històric: **{report['precipitacio']:.1f} mm** · "
             f"**{report['lectures']}** lectures")
    st.caption(f"Última lectura de l'històric: {report['ultima_lectura']:%d/%m/%Y %H:%M %Z}")
    # Etiquetes locals explícites: l'hora del gràfic no depèn del fus del navegador.
    spec = {
        "height": 280,
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
                {"field": "precipitacio", "type": "quantitative", "title": "Pluja (mm)", "format": ".1f"},
                {"field": "lectures", "type": "quantitative", "title": "Lectures"},
                {"field": "lectures_esperades", "type": "quantitative", "title": "Lectures esperades"},
                {"field": "estat", "type": "nominal", "title": "Estat"},
            ],
        },
    }
    st.vega_lite_chart(history, spec, width="stretch", key="station_histogram")
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
        st.dataframe(table, hide_index=True, width="stretch",
                     column_config={"Precipitació": st.column_config.NumberColumn(format="%.1f mm")})


def render_map(frame, period_end: datetime, include_provisional: bool) -> None:
    # Dibuixa els episodis més intensos al final perquè quedin per sobre dels altres punts.
    points = frame.dropna(subset=["latitud", "longitud"]).sort_values("precipitacio").copy()
    points["color"] = points["precipitacio"].map(rain_color)
    points["pluja_text"] = points["precipitacio"].map(lambda value: f"{value:.1f} mm")
    points["ultima_text"] = points["ultima_lectura"].map(lambda value: value.strftime("%d/%m/%Y %H:%M %Z"))
    fields = ["codi_estacio", "nom", "municipi", "comarca", "latitud", "longitud",
              "color", "pluja_text", "lectures", "ultima_text", "estat_dades"]
    layer = pdk.Layer(
        "ScatterplotLayer", data=points[fields].to_dict("records"),
        get_position="[longitud, latitud]", get_fill_color="color", get_radius=POINT_RADIUS_PX,
        # Pydeck exigeix cometes internes per a un literal, en lloc d'un accessor.
        radius_units="'pixels'", radius_min_pixels=POINT_RADIUS_PX, radius_max_pixels=POINT_RADIUS_PX,
        id="estacions-xema", pickable=True, stroked=True, filled=True,
        get_line_color=[255, 255, 255, 230], line_width_min_pixels=1,
    )
    deck = pdk.Deck(
        # El zoom inicial permet veure Catalunya sencera també en una pantalla estreta.
        layers=[layer], initial_view_state=pdk.ViewState(latitude=41.8, longitude=1.7, zoom=6),
        map_provider="carto", map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        tooltip={"text": "{nom}\nMunicipi: {municipi}\nComarca: {comarca}\n"
                           "Precipitació acumulada: {pluja_text}\nNombre de lectures: {lectures}\n"
                           "Última lectura: {ultima_text}\nEstat de les dades: {estat_dades}"},
    )
    selection = st.pydeck_chart(deck, height=570, key="rain_map",
                                on_select="rerun", selection_mode="single-object")
    items = []
    for _, label, color in SCALE:
        rgb = ",".join(map(str, color[:3]))
        items.append(f'<span><i style="background:rgb({rgb});"></i>{label}</span>')
    st.markdown('<div class="rain-legend">' + "".join(items) + "</div>", unsafe_allow_html=True)
    st.caption("Toca o clica una estació per veure'n les dades i l'histograma de pluja. "
               "Pots ampliar el mapa amb els botons + i −.")
    st.caption("Els llindars superiors són inclusius. 1 mm de precipitació = 1 litre/m². "
               "Mapa base: CARTO / OpenStreetMap.")
    selected_objects = selection.selection.objects.get("estacions-xema", [])
    if selected_objects:
        station_code = selected_objects[0].get("codi_estacio")
        selected_station = frame[frame["codi_estacio"] == station_code]
        # Una selecció anterior no ha de sobreviure als filtres si l'estació ja no hi és.
        if not selected_station.empty:
            station = selected_station.iloc[0]
            with st.container(border=True, key="station_details"):
                st.caption("Estació seleccionada")
                st.subheader(station["nom"])
                st.write(f"{station['municipi']} · {station['comarca']}")
                st.write(f"Precipitació acumulada: **{station['precipitacio']:.1f} mm** · "
                         f"Nombre de lectures: {station['lectures']}")
                st.caption(f"Última lectura: {station['ultima_lectura']:%d/%m/%Y %H:%M %Z}")
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
    mode = st.radio("Període", ["Un dia", "Entre dues dates i hores"],
                     horizontal=True, key="period_mode")
    now = datetime.now(LOCAL_TZ)
    with st.container(key="controls"):
        if mode == "Un dia":
            date_col, button_col = st.columns([3, 1], vertical_alignment="bottom")
            with date_col:
                selected_day = st.date_input("Data seleccionada", value=now.date(),
                                             min_value=date(2009, 1, 1),
                                             max_value=now.date(), format="DD/MM/YYYY", key="day")
            with button_col:
                if st.button("Actualitza dades", width="stretch"):
                    clear_cache()
            start, end = day_bounds_utc(selected_day)
            return start, end, selected_day
        # Un formulari consulta només en aplicar el període, no en editar cada camp.
        with st.form("interval_form", border=False):
            start_col, end_col = st.columns(2)
            with start_col:
                start_day = st.date_input("Data d'inici", value=now.date() - timedelta(days=1),
                                          min_value=date(2009, 1, 1), max_value=now.date(),
                                          format="DD/MM/YYYY", key="start_date")
                start_time = st.time_input("Hora d'inici", value=time(0), step=1800, key="start_time")
            with end_col:
                end_day = st.date_input("Data de final", value=now.date(),
                                        min_value=date(2009, 1, 1), max_value=now.date(),
                                        format="DD/MM/YYYY", key="end_date")
                end_time = st.time_input("Hora de final", value=time(now.hour, now.minute // 30 * 30),
                                         step=1800, key="end_time")
            apply_col, refresh_col = st.columns(2)
            with apply_col:
                st.form_submit_button("Mostra acumulat", type="primary", width="stretch")
            with refresh_col:
                refresh = st.form_submit_button("Actualitza dades", width="stretch")
        st.caption(f"Hores locals de Catalunya (Europe/Madrid). Inici inclòs, final exclòs. "
                   f"Màxim {MAX_INTERVAL_DAYS} dies per consulta.")
        if refresh:
            clear_cache()
        start = choose_local_timestamp(datetime.combine(start_day, start_time), "Inici", "start_occurrence")
        end = choose_local_timestamp(datetime.combine(end_day, end_time), "Final", "end_occurrence")
        start, end = interval_bounds_utc(start, end)
        return start, end, None


def main() -> None:
    st.markdown(RESPONSIVE_CSS, unsafe_allow_html=True)
    st.title("🌧️ Pluja acumulada a Catalunya")
    st.caption("Estacions automàtiques XEMA — Meteocat")
    try:
        start, end, selected_day = period_controls()
    except DataError as exc:
        st.error(str(exc))
        st.stop()
    with st.sidebar:
        st.subheader("Filtres")
        include_provisional = st.checkbox("Inclou dades pendents de validació", value=True, key="provisionals")
        st.caption("Si ho desactives, només s'utilitzen lectures amb estat V.")
    try:
        with st.spinner("Consultant les dades públiques de XEMA…"):
            period_data, report = load_interval_data(start, end, include_provisional)
    except DataError as exc:
        st.error(str(exc))
        st.caption("Prem «Actualitza dades» per tornar a consultar l'API.")
        st.stop()
    with st.sidebar:
        county = st.selectbox("Comarca", ["Totes", *report["comarques"]], key="comarca")
        minimum = st.number_input("Precipitació mínima (mm)", min_value=0.0, value=0.0, step=1.0, key="minim")
    filtered = period_data[period_data["precipitacio"] >= minimum]
    if county != "Totes":
        filtered = filtered[filtered["comarca"] == county]
    latest = report["ultima_lectura"]
    top = filtered.iloc[0] if not filtered.empty else None
    with st.container(key="summary"):
        cols = st.columns(3)
        cols[0].metric("Última lectura", latest.strftime("%H:%M %Z") if latest is not None else "—")
        cols[1].metric("Estacions", len(filtered))
        cols[2].metric("Màxima", f"{top['precipitacio']:.1f} mm" if top is not None else "—")
    with st.container(key="context"):
        st.caption("Estació amb màxima precipitació: " + (top["nom"] if top is not None else "—"))
        if selected_day is None:
            st.caption(f"Interval: {report['inici']:%d/%m/%Y %H:%M %Z} → "
                       f"{report['final']:%d/%m/%Y %H:%M %Z}")
            if latest is not None:
                st.caption(f"Última lectura del període: {latest:%d/%m/%Y %H:%M %Z}")
        st.caption(f"Hora local de Catalunya · Consulta: {report['consulta']:%H:%M %Z}")
        if include_provisional:
            st.caption("⚠️ Les dades més recents poden estar pendents de validació definitiva per Meteocat.")
        if report["en_curs"]:
            st.caption("El període és en curs: l'acumulat inclou només les lectures publicades fins ara.")
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
    render_map(filtered, end, include_provisional)
    if notices:
        st.warning(". ".join(notices) + ".")
    st.subheader("Top estacions per precipitació")
    count = st.selectbox("Nombre d'estacions a la taula", [20, 50, 100, "Totes"], index=0, key="ranking")
    ranking = filtered if count == "Totes" else filtered.head(count)
    table = ranking[["nom", "municipi", "comarca", "precipitacio"]].rename(columns={
        "nom": "Estació", "municipi": "Municipi", "comarca": "Comarca", "precipitacio": "Precipitació",
    })
    st.dataframe(table, hide_index=True, width="stretch",
                 column_config={"Precipitació": st.column_config.NumberColumn(format="%.1f mm")})
    st.caption("Pots ordenar la taula clicant les capçaleres. Les estacions sense lectures no es consideren estacions amb 0 mm.")
    with st.expander("Com s'interpreten les dades?"):
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
    st.markdown("Dades: [XEMA / Meteocat — Dades Obertes de Catalunya]"
                "(https://analisi.transparenciacatalunya.cat/d/nzvn-apee) · "
                "[Metadades d'estacions](https://analisi.transparenciacatalunya.cat/d/yqwd-vj5e)")


if __name__ == "__main__":
    main()
