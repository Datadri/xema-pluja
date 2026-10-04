# 🌧️ Pluja acumulada a Catalunya

Aplicació local amb Python i Streamlit per visualitzar la precipitació acumulada
del dia civil de Catalunya, o d'un interval de dates i hores, a les estacions
automàtiques XEMA de Meteocat.
El mapa mostra observacions puntuals: no interpola la pluja entre estacions.
**1 mm de precipitació equival a 1 litre/m².**

**Aplicació pública:** [xema-pluja.streamlit.app](https://xema-pluja.streamlit.app/).
Funciona també en mòbil i es pot compartir sense iniciar sessió.

## Instal·lació i execució

Cal Python 3.10 o superior i connexió a Internet. Des d'aquesta carpeta:

```bash
python -m venv .venv
```

Activació a Windows (CMD):

```bash
.venv\Scripts\activate
```

A PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si PowerShell no permet activar scripts, pots executar directament
`.venv\Scripts\python.exe -m pip install -r requirements.txt` i
`.venv\Scripts\python.exe -m streamlit run app.py`.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Obre l'adreça local que indica Streamlit, normalment http://localhost:8501.
Per aturar el servidor, prem `Ctrl+C` al terminal.

`tzdata` és l'única dependència addicional: proporciona la base IANA de fusos
horaris per a `zoneinfo`, especialment necessària a Windows.

## Ús

- El selector de data comença amb el dia actual a `Europe/Madrid`.
- «Entre dues dates i hores» permet triar data i hora d'inici i de final,
  en hora local de Catalunya, i aplicar-les amb «Mostra acumulat».
  El mateix període afecta el mapa, el resum i el rànquing.
- «Actualitza dades» buida les consultes de la cache; la cache caduca als 300 segons.
- «Comarca» i «Precipitació mínima» afecten el mapa, el rànquing i el resum
  d'estacions i màxims. La darrera lectura disponible correspon al conjunt del període.
- Els punts representen l'acumulat amb set trams de color i mida. Passant-hi el
  cursor es veuen el nom, municipi, comarca, acumulat, lectures, última lectura
  amb el seu fus horari i estat de les dades. En tocar o clicar una estació,
  aquests detalls també apareixen en una fitxa sota el mapa.
- En mòbil, els indicadors són compactes, la llegenda ocupa diverses línies i
  l'alçada del mapa s'adapta a la pantalla. Els filtres s'obren amb la fletxa
  de la cantonada superior esquerra. La taula es pot desplaçar horitzontalment.
- La taula mostra les 20 estacions amb més precipitació i permet ampliar-la i
  ordenar-la clicant les capçaleres.
- Les estacions sense lectures no es dibuixen com si haguessin registrat 0 mm.
  Les estacions amb lectures però sense coordenades vàlides apareixen a la taula.

### Acumulat entre dos timestamps

L'inici queda **inclòs** i el final queda **exclòs**: se sumen les lectures amb
`inici <= data_lectura < final`, després de convertir els dos límits locals a UTC.
Per exemple, del 04/10/2026 a les 00:00 CEST al 04/10/2026 a les 02:00 CEST es
consulten lectures des del 03/10/2026 a les 22:00 UTC fins al 04/10/2026 a les
00:00 UTC, sense incloure aquesta última lectura.

Els selectors proposen salts de 30 minuts i també permeten introduir altres
minuts. **La resolució de les mesures és de 30 minuts (SH) o una hora (HO)**:
es compta el valor complet de les lectures que tenen l'inici dins del període.
No s'interpola ni es prorrateja la precipitació quan un límit talla un interval.

El final ha de ser posterior a l'inici. Es permeten fins a **31 dies civils per
consulta** per mantenir les consultes manejables a l'allotjament gratuït.
Les hores inexistents del canvi d'hora de primavera es rebutgen; per a una hora
repetida a la tardor es pot escollir la primera ocurrència (CEST) o la segona (CET).
El formulari aplica els quatre camps junts per evitar consultes durant l'edició.

## Publicació gratuïta

L'aplicació està publicada a [xema-pluja.streamlit.app](https://xema-pluja.streamlit.app/)
amb [Streamlit Community Cloud](https://share.streamlit.io/), sense servidor propi ni API key.
El servei es connecta a un repositori de GitHub i instal·la `requirements.txt`.

Configuració utilitzada per al desplegament:

1. Inicia sessió a Streamlit Community Cloud amb GitHub.
2. Crea una aplicació des del repositori `Datadri/xema-pluja`.
3. Selecciona la branca `main` i el fitxer principal `app.py`.
4. A «Advanced settings», selecciona Python **3.13**, la versió provada localment.
5. Tria un subdomini disponible, prem «Deploy» i comprova que l'accés sigui públic.

No cal configurar secrets. `.streamlit/config.toml` defineix el color principal
i desactiva les estadístiques d'ús de Streamlit. Els canvis pujats a GitHub
s'actualitzen al desplegament. El servei gratuït pot suspendre l'aplicació per
inactivitat; en tornar a obrir l'enllaç, es reactiva.

[Instruccions oficials de desplegament](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).

El desplegament es va completar el **4 d'octubre de 2026** amb Python 3.13.
Es van comprovar al navegador el mapa, el rànquing i les dades de 185 estacions,
a més de l'opció de compartir «Make this app public» activada.

## Dades i càlcul

Les dades meteorològiques provenen exclusivament de **XEMA / Meteocat mitjançant
Dades Obertes de Catalunya**, amb l'API pública Socrata/SODA i sense API key:

- Lectures: [nzvn-apee](https://analisi.transparenciacatalunya.cat/d/nzvn-apee),
  endpoint `https://analisi.transparenciacatalunya.cat/resource/nzvn-apee.json`.
- Estacions: [yqwd-vj5e](https://analisi.transparenciacatalunya.cat/d/yqwd-vj5e),
  endpoint `https://analisi.transparenciacatalunya.cat/resource/yqwd-vj5e.json`.
- Esquemes: `/api/views/nzvn-apee.json` i `/api/views/yqwd-vj5e.json` al mateix domini.

La variable `35` és precipitació (`PPT`, mm) **durant cada interval**.
Meteocat etiqueta `data_lectura` amb l'inici de l'interval en Temps Universal.
L'aplicació construeix separadament les dues mitjanits locals, les converteix
a UTC i consulta només aquesta variable i aquest interval `[inici, final)`.
Després interpreta les lectures com UTC, les converteix a `Europe/Madrid`
i torna a filtrar el període abans de sumar. La vista diària és el mateix càlcul
amb les dues mitjanits locals com a límits; la vista d'interval utilitza els
timestamps seleccionats.

Un dia d'estiu va de les 22:00 UTC del dia anterior a les 22:00 UTC del dia
seleccionat; a l'hivern, de les 23:00 a les 23:00. Els dies de canvi d'hora
poden tenir 23 o 25 hores. Les dues ocurrències d'una hora repetida continuen
sent lectures diferents perquè es dedupliquen amb la data UTC.

Només es demanen els camps necessaris, amb filtre de qualitat a l'API i
pàgines de fins a 50.000 registres amb ordre explícit, també en períodes de diversos
dies. Hi ha temps d'espera
HTTP, reintents limitats i tractament d'errors, respostes buides i valors corruptes.
No es descarrega tot l'històric ni es fa scraping del web de Meteocat.
El mapa base CARTO / OpenStreetMap també funciona sense clau.

## Qualitat i límits

Per defecte s'inclouen lectures `V` (validades), `T` (provisionals) i sense estat
definit. **Les dades més recents poden estar pendents de validació definitiva
per Meteocat.** Desactivant la casella lateral només s'inclouen lectures `V`.
Els estats no admesos, valors nuls, negatius o no finits, dates invàlides i bases
desconegudes es descarten.

Els duplicats es detecten amb `(codi_estacio, data_lectura UTC, codi_variable,
codi_base)`. Es conserva una lectura amb prioritat `V > T > sense estat`.
Si hi ha valors diferents amb la mateixa qualitat, es desempata de manera
determinista per identificador i valor; els conflictes s'avisen a la pantalla.

Cada estació utilitza **una sola base temporal per dia**: es prioritza `SH`
(30 minuts) i només s'utilitza `HO` (una hora) quan no hi ha lectures `SH`.
En períodes de diversos dies, una estació pot utilitzar HO un dia i SH un altre:
es conserven tots dos dies, sense duplicar bases dins d'un mateix dia.
Mai se sumen totes dues bases dins d'un mateix dia. Si la base prioritzada és incompleta, no es
barreja amb l'altra per omplir buits: l'acumulat s'indica com a parcial.

Per a dies acabats es compara el nombre de lectures amb les esperades durant
tot el dia (46, 48 o 50 per a `SH`). Per a avui es compara fins a l'inici de
l'últim interval publicat al conjunt d'estacions. Aquesta comprovació orientativa
detecta mancances i retard d'estacions; no substitueix la validació de Meteocat.
L'acumulat d'avui és sempre provisional mentre el dia continua.
En un interval acabat, es comproven les lectures esperades dins dels límits
seleccionats, inclosos els dies sense cap lectura. Si el final encara és futur,
la comprovació arriba només fins a l'últim inici d'interval publicat.

L'esquema de metadades es consulta abans de seleccionar camps. Es reconeixen
`latitud` i `longitud` WGS84 i, com a alternativa, el punt GeoJSON
`geocoded_column` amb ordre `[longitud, latitud]`. Es conserven altitud i estat
de l'estació si existeixen. També es conserven estacions desmantellades amb
lectures històriques. Les metadades descriuen la informació publicada actualment.

`app.py` conté la interfície i el mapa; `data.py` conté les consultes, dates,
normalització, qualitat, deduplicació, acumulats i unió amb les estacions.

Els totals diaris publicats en altres productes de Meteocat poden utilitzar un
dia UTC o un tall de publicació diferent. Per comparar-los amb aquest mapa cal
comprovar que el període i l'últim interval inclòs coincideixen.

## Validació realitzada

Comprovació del **4 d'octubre de 2026** amb Python 3.13, Streamlit 1.65.0,
pandas 3.0.6 i Pydeck 0.9.3:

- Aplicació executada realment amb Streamlit i revisada al navegador.
- Els dos esquemes Socrata consultats i les peticions SODA verificades.
- 4.585 lectures recuperades per al dia local, 185 estacions amb dades,
  cap lectura duplicada ni barreja de bases i coordenades vàlides per a totes.
  Set estacions tenien mancances de lectures i l'aplicació les indicava.
- Sis proves de càlcul: límits locals, dies de 23/25 hores, hora repetida,
  deduplicació i qualitat, bases SH/HO, valors corruptes, metadades GeoJSON,
  paginació, resposta buida i errors de xarxa.
- Proves d'interfície amb `Streamlit AppTest`: rànquing, comarca, mínim,
  resultats buits, només dades validades i refresc de la cache.
- Ampliació a intervals: límit final exclòs, precisió en minuts, conversió UTC,
  hores inexistents/repetides, canvi de base entre dies, dies sencers sense dades
  i límit de 31 dies en un canvi d'hora. Formulari i filtres d'interval provats
  amb `AppTest`, inclosa la validació d'un final anterior o igual a l'inici.
- Interval real del 04/10/2026 de 00:00 a 02:00 CEST: Barcelona - el Raval,
  47,4 mm en quatre lectures, amb el final exclòs i sense duplicats.
- Revisió responsive a amplades de 320 i 390 píxels, sense desbordament de la
  pantalla principal, amb mapa d'alçada adaptable i filtres plegats inicialment.
  Selecció d'una estació comprovada al navegador: la fitxa mostra Granollers,
  215,8 mm, el nombre de lectures i l'estat de validació.

Comparació manual amb **Barcelona - el Raval (X4)** a la
[taula de períodes de Meteocat del 3 d'octubre](https://www.meteo.cat/observacions/xema/dades?codi=X4&dia=2026-10-03T00%3A00Z)
i el resum del dia següent, consultats al navegador:

| Interval UTC | Precipitació |
|---|---:|
| 03/10/2026 22:00–22:30 | 24,8 mm |
| 03/10/2026 22:30–23:00 | 10,1 mm |
| 03/10/2026 23:00–23:30 | 8,2 mm |
| 03/10/2026 23:30–00:00 | 4,3 mm |
| 04/10/2026 des de 00:00 fins al tall consultat | 2,0 mm |
| **Total del dia local 04/10/2026** | **49,4 mm** |

El resultat de l'aplicació era **49,4 mm**, amb 25 lectures fins a l'interval
amb inici a les **10:00 UTC / 12:00 CEST**. El resum web arribava a les 10:30
UTC; l'interval addicional era de 0,0 mm. Aquest contrast confirma també que
començar a les 00:00 UTC hauria omès 47,4 mm d'aquest dia local.
La consulta manual del web només s'ha utilitzat per validar: l'aplicació
obté totes les observacions de Socrata.
