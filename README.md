# Pluja Cat — Precipitació acumulada a Catalunya

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
- El segment «Dates i hores» permet triar data i hora d'inici i de final,
  en hora local de Catalunya, i aplicar-les amb «Mostra acumulat».
  El mateix període afecta el mapa, el resum i el rànquing.
  El formulari es pot plegar després d'aplicar-lo per donar més espai al mapa;
  els límits consultats continuen visibles.
- «Actualitza dades» buida les consultes de la cache; la cache caduca als 300 segons.
- «Filtres de territori i dades», al costat dels controls del període, agrupa
  comarca, precipitació mínima i criteri de validació. La selecció territorial
  i el criteri de dades queden visibles sobre el mapa, encara que es pleguin els filtres.
- «Comarca» i «Precipitació mínima» afecten el mapa, el rànquing i el resum
  d'estacions i màxims. La darrera lectura disponible correspon al conjunt del període.
- Els punts tenen una mida fixa de 12 píxels de diàmetre, independentment de la
  pluja acumulada i del zoom. Set trams de color representen l'acumulat. Passant-hi el
  cursor es veuen el nom, ubicació, acumulat, període i última lectura amb el seu
  fus horari. En tocar o clicar una estació, la fitxa sota el mapa afegeix el
  nombre de lectures i l'estat de les dades. També es pot cercar una estació pel
  nom amb el selector «Consulta una estació», accessible amb teclat i en mòbil.
- La fitxa inclou un histograma de l'estació, amb horitzons d'1, 3, 7, 15 o 30
  dies i agrupació per hores o per dies. Passa el cursor per una barra per veure
  la pluja, el nombre de lectures i l'estat de les dades.
- En mòbil, els controls es distribueixen en dues columnes, els indicadors són
  compactes, la llegenda ocupa tres columnes i l'alçada del mapa s'adapta a la
  pantalla. Els filtres es despleguen al mateix flux de la pàgina. La taula
  prioritza estació i pluja; es pot desplaçar dins del seu espai per veure municipi i comarca.
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

### Histograma d'una estació

Toca o clica un punt del mapa. Sota el mapa apareixen la fitxa i els selectors
«Horitzó temporal» i «Agrupa la pluja per». La taula «Lectures agrupades de
l'històric» permet revisar o descarregar els mateixos valors del gràfic.

Els horitzons són **finestres mòbils de 24, 72, 168, 360 o 720 hores** que acaben
al final del període seleccionat. Per a avui, el final es limita al tall de mitja
hora actual per no consultar hores futures. L'inici s'inclou i el final s'exclou.
El text sobre el gràfic indica els límits exactes, en hora de Catalunya.

Cada barra suma la precipitació d'una hora real o d'un dia local. Les dues hores
repetides de tardor són barres diferents, etiquetades CEST i CET; els dies locals
poden tenir 23, 24 o 25 hores. Una finestra que comença o acaba a mig dia pot
incloure dos dies extrems incomplets: només s'hi sumen les lectures dins la finestra.
La resolució original de 30/60 minuts i el criteri de lectura completa es mantenen.

**Sense lectures no significa 0 mm**: els valors sense dades queden nuls al
gràfic i a la taula. Les barres amb lectures absents es destaquen en taronja i
l'acumulat s'avisa com a parcial. El filtre lateral de dades validades també
afecta l'històric. Es reutilitzen els mateixos controls de qualitat, deduplicació
i base temporal per estació i dia que al mapa.

La consulta de l'històric es fa només quan se selecciona una estació, amb filtre
`codi_estacio`, variable 35 i límits UTC a Socrata. La cache de 300 segons es
comparteix entre les agrupacions horària i diària: canviar l'agrupació no torna
a descarregar les lectures. No s'ha afegit cap dependència per al gràfic.

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

El desplegament es va completar el **4 d'octubre de 2026**. La versió local
provada és Python 3.13; els logs del servei públic indiquen Python 3.14.7.
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
- Histogrames: 17 proves de càlcul en total, amb barres horàries i diàries,
  hores repetides, dies de 23/25 hores, valors nuls i buits de lectures, canvis
  de base i filtres de qualitat. Els cinc horitzons s'han consultat a l'API real
  per al Raval; els totals horaris i diaris coincideixen. Controls d'horitzó i
  agrupació comprovats amb `AppTest`, i clic a Granollers verificat al navegador.
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

## Revisió de la interfície — 7 d'octubre de 2026

L'auditoria ha revisat l'única pantalla, el formulari d'intervals, els filtres,
el mapa Pydeck, la fitxa i l'histograma d'estació, el rànquing i els estats de dades.
Els problemes prioritaris eren:

- **Dades i jerarquia:** l'última lectura destacava tant com la màxima, sense
  data completa en la vista diària. El període i el territori no quedaven junts.
- **Mapa i layout:** tres cards i diversos textos previs desplaçaven el mapa;
  els marges reduïen la superfície disponible. La llegenda ja era útil i es conserva.
- **Filtres i interacció:** els filtres quedaven en una barra lateral plegada;
  calia encertar un punt de 12 píxels per obrir l'histograma en mòbil.
- **Espaiat, consistència i tipografia:** les regles estaven disperses, amb
  cards més prominents del necessari i espaiats poc coherents entre grups.
- **Color i accessibilitat:** es conserva l'escala de pluja i l'accent blau;
  es reforcen el contrast dels textos auxiliars, els labels, el focus i els controls.
- **Responsive:** els controls temporals requerien més espai, la capçalera
  podia quedar sota la barra fixa i els valors del rànquing quedaven fora de la vista estreta.

Les millores segueixen el flux **context → controls → mapa → detall**: resum
compacte amb màxima i estació, període i filtres visibles, última lectura amb
data i fus, mapa de 600 píxels en desktop i alçada adaptable en mòbil, llegenda
vinculada al mapa i cercador d'estacions. Els avisos i la metodologia continuen
accessibles, amb menys competència visual. Els valors visibles utilitzen coma
decimal i unitats; les taules conserven dades numèriques per ordenar correctament.

El petit sistema visual centralitza colors, espaiats, radi i focus en variables
CSS i el tema Streamlit. Es mantenen els widgets natius, els set colors i els
cercles fixos. No s'han modificat `data.py`, les consultes, els càlculs ni les dependències.

La revisió s'ha comprovat amb l'aplicació real i dades Socrata: vista diària,
interval del 04/10/2026 de 00:00 a 02:00 CEST, cerca de Granollers i histogrames
horari i diari. S'han revisat amplades de 1366, 768, 390 i 320 píxels, sense
desbordament de la pàgina; el desplaçament de les taules queda dins del component.
El focus de teclat és visible i els textos auxiliars tenen contrast suficient
sobre el fons blanc. Les proves `AppTest` cobreixen filtres, resultats buits,
absència de lectures, error de la font, interval invàlid, horitzons d'històric
i sincronització entre mapa i cercador.

## Segona passada de disseny — 7 d'octubre de 2026

La identitat «Pluja Cat» utilitza una gota simple i la tipografia variable
[Inter](https://github.com/rsms/inter). La font es distribueix amb el projecte a
`static/InterVariable.woff2`, amb la seva llicència SIL Open Font License a
`static/Inter-LICENSE.txt`; Streamlit la serveix localment, sense Google Fonts.
La gota es conserva com a SVG a `static/gota.svg`.

El tema i els tokens CSS comparteixen fons gris blavós, superfície blanca,
text slate i accent teal. Els set colors de precipitació conserven el seu
significat i els cercles mantenen el diàmetre fix de 12 píxels. El resum té
números tabulars i unitats secundàries; el mapa i la llegenda formen una sola
superfície amb radi de 12 píxels, vora fina i ombra subtil. La llegenda segueix
els intervals reals, sense interpolar colors entre categories.

Els segments de període, horitzó i agrupació mantenen una opció seleccionada.
Els controls tenen almenys 44 píxels d'alçada, focus visible i transicions
curtes que es desactiven quan es demana reduir el moviment. La cerca d'estació
mostra nom i comarca; el seu acumulat es llegeix al detall i al rànquing.
No s'han afegit dependències de Python ni modificat els càlculs de `data.py`.

Verificació: aplicació real amb Socrata, episodi del 04/10/2026 (Granollers,
215,8 mm), histograma diari de set dies i formulari d'interval. S'han revisat
1366, 768, 390 i 320 píxels, sense desbordament de pàgina i amb els cinc
horitzons visibles a 320 píxels. `AppTest` comprova filtres, selecció sincronitzada,
intervals UTC, histogrames, selecció obligatòria dels segments i estats d'error
o sense dades. Contrast calculat: text secundari 5,36:1 sobre el fons,
botó principal 6,69:1. El focus s'ha comprovat amb teclat.
