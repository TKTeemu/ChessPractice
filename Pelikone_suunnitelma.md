# Shakkilauta – pelimoodit ja tietokonevastustaja (suunnitelma)

2.11.2026

> Jatkoa alkuperäiselle suunnitelmalle [Shakkilauta_suunnitelma.md](Shakkilauta_suunnitelma.md). Kehittäjän ohje moodien ja pelikoneiden lisäämiseen on tiedostossa [docs/EXTENDING.md](docs/EXTENDING.md).

## Tavoite ja rajaus

Ohjelmaan lisätään **moodit**. Laajennuksen jälkeen niitä on kaksi:

| Moodi | Kuvaus |
| --- | --- |
| **Pelilautamoodi** (valikossa *Board*) | Ohjelma sellaisena kuin se on nyt: käyttäjä siirtää molempien puolten nappuloita, voi kokeilla muunnelmia, ja kirjoittaa kommentteja. |
| **Peli konetta vastaan** (valikossa *Play vs Computer*) | Käyttäjä pelaa valitsemallaan värillä, ja pelikone vastaa. Käyttäjä valitsee tason ja värin. Shakkikello on käytössä, eikä siirtoja voi perua. |

**Mukana:** moodien valinta *Game*-valikossa, uuden pelin dialogi (taso, väri, aloitusasema), shakkikello (käyttäjällä 30 min), pelikoneen siirrot taustasäikeessä, luovutus, pelin tuloksen kirjaus PGN:ään ja päättyneen pelin avaaminen pelilautamoodissa.

**Ei mukana:** siirron peruutus, vinkit, arvio- tai parhaan linjan näyttö, avauskirjat, verkkopeli. Rakenne ei estä näitä myöhemmin.

**Ehdoton vaatimus:** ohjelma toimii offline Windows 11:ssä. Stockfish ladataan kerran ja se on tämän jälkeen paikallinen tiedosto; ohjelma ei käytä verkkoa.

**Laajennettavuus:** uusi moodi = yksi uusi tiedosto `app/modes/`-kansioon + rivi rekisteriin. Uusi pelikone = yksi tiedosto `app/engines/`-kansioon + rivi rekisteriin. Valikot ja dialogit rakentuvat rekistereistä automaattisesti.

## Pelikoneen valinta: Stockfish

| Vaihtoehto | Plussat | Miinukset |
| --- | --- | --- |
| **Stockfish (UCI)**, valittu | Avoin (GPL-3), vahva, säädettävä vahvuus `UCI_LimitStrength` + `UCI_Elo`, NNUE-verkko on exe-tiedoston sisällä (yksi tiedosto). | Exe-tiedosto ja aliprosessi: poikkeaa alkuperäisen suunnitelman F-Secure-periaatteista (ks. alla). |
| Oma Python-moottori | Ei exe-tiedostoja. | Heikko, hidas, tasojen kalibrointi vaikeaa. |

**Versio:** Stockfish 19 (tai uusin julkaistu). Ohjelma ei ole sidottu versioon: se lukee vahvuusasetusten rajat (`UCI_Elo`-optionin min/max) moottorilta käynnistyksessä. Viime versioiden alaraja on ollut 1320, joten pyydetty alin taso 1320 onnistuu.

**Tasot** (data-taulukko `app/engines/stockfish.py`:ssä, helppo muuttaa):

| Taso | Asetus | Miettimisaika |
| --- | --- | --- |
| 1320, 1500, 1650, 1800, 2000, 2200, 2400, 2600, 2800 | `UCI_LimitStrength=true`, `UCI_Elo=<taso>` | 1 s / siirto |
| Maximum | ei rajoitusta | 2 s / siirto |

Huom: Stockfishin Elo-asteikko on kalibroitu konepelien listaa vastaan, joten se ei vastaa suoraan Chess.comin tai FIDEn lukuja; 1320 voi tuntua ihmistä vastaan hieman vahvemmalta. Jos myöhemmin halutaan helpompia tasoja, taulukkoon voi lisätä rivejä `Skill Level` -optionilla (0–20).

**Kevyt ajo:** `Threads=1`, `Hash=64`. Moottoriprosessi käynnistetään vasta kun Play vs Computer -peli alkaa ja suljetaan, kun moodista poistutaan tai ohjelma suljetaan. Pelilautamoodissa ei ole yhtään aliprosessia, eli se toimii kuten ennenkin.

## Shakkikello

| Puoli | Aika | Toiminta |
| --- | --- | --- |
| Käyttäjä | 30 min koko peliin, ei lisäaikaa | Kello käy käyttäjän vuorolla. Jos aika loppuu, käyttäjä häviää ajalla. Poikkeus shakin säännöistä: jos koneella ei ole mattiin riittävää materiaalia, peli on tasapeli. |
| Kone | Myös 30 min | Kone käyttää tasosta riippuen 1–2 s siirtoa kohden, joten sen aika ei käytännössä lopu. Kello näytetään silti, jotta käyttäjä näkee koneen käyttämän ajan, ja tallennettu peli on tavallinen 30 minuutin peli. |

- Kellot näytetään pelaajien nimien vieressä laudan ylä- ja alapuolella. Vuorossa olevan pelaajan kello on korostettu. Alle minuutin aika näytetään punaisella ja kymmenyssekunnein (0:42.3).
- Kello käynnistyy valkoisen ensimmäisestä siirrosta. Jos kone pelaa valkeilla, se tekee ensimmäisen siirron heti, ja käyttäjän kello alkaa käydä.
- Kello perustuu `time.monotonic()`-aikaan, ei laskuriin. Näyttö päivittyy `root.after(100, …)`-ajastimella, mutta jäljellä oleva aika lasketaan aina kellonajasta, joten se pysyy oikeana, vaikka ikkunaa raahattaisiin tai se pienennettäisiin.
- Kelloa ei voi pysäyttää, eikä keskeneräistä peliä voi jatkaa ohjelman uudelleenkäynnistyksen jälkeen.
- Koneen miettimisaika ei riipu kellosta vaan tason asetuksesta. Jos halutaan, että kone jakaa aikansa itse, Stockfishille voidaan myöhemmin lähettää `go wtime … btime …` kiinteän `movetime`-ajan sijaan.
- Aika on asetus (`vs_minutes`, oletus 30). Jos myöhemmin halutaan valittavia aikoja tai lisäaikaa siirtoa kohden, ne lisätään aikataulukoksi samaan tapaan kuin tasot.

## F-Secure ja offline

Alkuperäinen periaate oli "ei uusia exe-tiedostoja, ei `subprocess`-kutsuja". Stockfish rikkoo tätä tietoisesti, mutta hallitusti:

1. **Yksi tunnettu exe, yhdessä paikassa:** `engines\stockfish\stockfish.exe`. Ei asennusohjelmaa, ei rekisterimuutoksia, ei taustapalvelua.
2. **Lataus kerran virallisesta lähteestä** (stockfishchess.org → GitHub-julkaisu). Zip puretaan omaan tyhjään kansioon, SHA-256 tarkistetaan julkaisusivun tarkisteeseen (`Get-FileHash`), ja Mark of the Web poistetaan: `Unblock-File engines\stockfish\stockfish.exe`.
3. **CPU-versio:** Windows 11 -koneelle `stockfish-windows-x86-64-avx2.exe`. Jos se kaatuu käynnistyksessä ("illegal instruction"), käytetään `x86-64-sse41-popcnt`-versiota, joka toimii kaikissa nykyaikaisissa prosessoreissa.
4. **Ei konsoli-ikkunaa:** Stockfish on konsoliohjelma, joten se käynnistetään `CREATE_NO_WINDOW`-lipulla. (python-chessin `popen_uci` ei aseta tätä itse.)
5. **Ei verkkoa:** Stockfish ei ota verkkoyhteyttä; ohjelma kommunikoi sen kanssa vain putkien (stdin/stdout) kautta.
6. **F-Secure-testi** tehdään vaiheessa 4: ensimmäinen käynnistys ja tapahtumaloki tarkistetaan. Jos DeepGuard huomauttaa, poikkeukseksi lisätään vain `stockfish.exe`, ei koko kansiota.
7. **Ilman Stockfishia** ohjelma toimii: Play vs Computer -dialogi kertoo, ettei moottoria löytynyt ja mihin se pitää kopioida. Testauksessa käytetään sisäistä *Random*-moottoria, joka ei tarvitse exeä.

## UCI-yhteys: oma ohut asiakas

python-chessissä on valmis `chess.engine`, mutta vendor-kansion versio 1.11.2 käyttää `asyncio.DefaultEventLoopPolicy`-luokkaa, joka on vanhentunut Python 3.15:ssä ja poistuu 3.16:ssa. Siksi tehdään oma pieni UCI-asiakas (`app/engines/uci.py`, n. 120 riviä) standardikirjaston `subprocess`-, `threading`- ja `queue`-moduuleilla. Tarvittavat komennot ovat vähäiset: `uci`, `setoption`, `isready`, `ucinewgame`, `position fen … moves …`, `go movetime …`, `stop`, `quit`. Siirrot muunnetaan `chess.Move.from_uci()`:lla, ja laillisuus tarkistetaan python-chessillä kuten ennenkin.

Jos python-chessistä tulee myöhemmin 3.16-yhteensopiva versio, `UciEngine` voidaan vaihtaa käyttämään sitä muuttamatta mitään muuta.

## Arkkitehtuuri

Nykyiset kerrokset säilyvät (ks. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)). Lisätään kaksi pakettia:

```
app\
├── engines\                  logiikkakerros, EI tkinteriä
│   ├── __init__.py           ENGINES-rekisteri
│   ├── base.py               Engine-rajapinta, Level-tietue
│   ├── uci.py                UCI-asiakas (subprocess, CREATE_NO_WINDOW)
│   ├── stockfish.py          StockfishEngine: tasotaulukko, exen etsintä
│   ├── random_engine.py      RandomEngine: testeihin ja varalle
│   └── worker.py             EngineWorker: haku taustasäikeessä, tulokset jonoon
├── modes\                    ohjainkerros (saa käyttää tkinteriä)
│   ├── __init__.py           MODES-rekisteri
│   ├── base.py               Mode-rajapinta ja ModeContext
│   ├── board.py              BoardMode: pelilautamoodi, nykyinen käytös
│   └── vs_computer.py        VsComputerMode: peli konetta vastaan
├── computer_game.py          ComputerGame: pelin säännöt ilman tkinteriä (testattava)
├── clock.py                  ChessClock: shakkikello ilman tkinteriä (testattava)
└── dialogs.py                + new_computer_game(): taso, väri, aloitusasema
engines\
└── stockfish\stockfish.exe   ladataan kerran, ei kuulu koodiin
```

**Moodi** päättää, mitä käyttäjä saa tehdä ja mitä siirron jälkeen tapahtuu. `MainWindow` pysyy ohjaimena, mutta kysyy moodilta:

| Kohta MainWindow:ssa | Kysymys moodille |
| --- | --- |
| `BoardView`-siirron alku | `mode.can_move(color)` – saako käyttäjä liikuttaa tätä väriä nyt? |
| `play_move()` onnistui | `mode.after_move()` – esim. käynnistä koneen haku |
| komennot (Ctrl+Z, muunnelmien muokkaus, liitä…) | `mode.allows(command)` – onko komento käytössä? |
| `refresh()` | `mode.status_text()` – oma tilarivi, esim. "Computer is thinking…" |
| `refresh()` | `mode.score_text()` – teksti laudan yläpuolelle oikealle, esim. materiaalitilanne |
| oikea paneeli | `mode.build_panel(parent)` – moodin omat painikkeet ja kellot (Resign, Open in Board Mode) |
| valikko | `mode.menu_items()` – moodin omat valikkorivit |
| moodin vaihto, Exit | `mode.deactivate()` – sulje moottori |

**Koneen siirto:** `VsComputerMode.after_move()` → jos koneen vuoro, `EngineWorker.request(board.copy(), level, request_id)` → taustasäie kysyy moottorilta → tulos jonoon → `root.after(50, …)`-kysely lukee jonon pääsäikeessä → jos `request_id` on yhä voimassa (peliä ei ole vaihdettu tai peruttu), `MainWindow.play_move(move)`. Koneen siirto kulkee siis samaa reittiä kuin käyttäjän siirto, joten äänet, siirtolista ja tallennus toimivat ilman lisäkoodia. tkinteriä ei kutsuta taustasäikeestä koskaan.

## Käyttöliittymä

**Siirtoanimaatio** (kaikissa moodeissa): kun asema etenee yhden siirron (koneen siirto, klikkaamalla tehty siirto tai → -selaus), nappula liukuu alkuruudusta loppuruutuun 0,16 sekunnissa. Linnoituksessa liikkuvat kuningas ja torni, lyötävä nappula näkyy, kunnes liikkuva nappula saapuu. Raahattua siirtoa ei animoida, koska nappula on jo perillä. Toteutus `BoardView`:ssä (`ANIM_SECONDS`).

**Valikko `Game`** (moodien valinta):

```
Game
 ◉ Board
 ○ Play vs Computer…
 ─────────────
   Resign              (vain pelin aikana)
   Open in Board Mode  (vain kun peli on päättynyt)
```

Moodien rivit tulevat `MODES`-rekisteristä, moodikohtaiset rivit `mode.menu_items()`:sta.

**Play vs Computer -dialogi:**

| Kenttä | Vaihtoehdot | Oletus (muistetaan settings.json:iin) |
| --- | --- | --- |
| Engine | rekisterin moottorit, joiden `available()` on tosi | Stockfish |
| Level | moottorin `levels()` | 1350 |
| Your colour | White / Black / Random | White |
| Start from | Initial position / Current position | Initial position |

**Pelin aikana:**

- Lauta käännetään käyttäjän värin mukaan. Pelaajien nimet: "You" ja "Stockfish 1500".
- Käyttäjä voi liikuttaa vain omia nappuloitaan ja vain silloin, kun on hänen vuoronsa ja ollaan päälinjan lopussa.
- Siirtohistoriassa ei voi selata (←/→, Home/End, siirtolistan klikkaus) Play vs Computer -moodissa, ei myöskään pelin päätyttyä. Selaus on vain pelilautamoodissa; päättynyt peli käydään läpi *Open in Board Mode* -toiminnolla. Muunnelmien muokkaus, liittäminen ja Ctrl+Z (viimeisen siirron poisto) ovat pois käytöstä, **eikä siirtoja voi perua**.
- Valittu moodi näkyy laudan yläpuolella (esim. "Board" tai "Play vs Computer · Stockfish 1500").
- **Materiaalitilanne** näkyy laudan yläpuolella oikealla käyttäjän näkökulmasta: "Material: you +3", "Material: you −2" tai "Material: even". Arvot: sotilas 1, ratsu ja lähetti 3, torni 5, kuningatar 9 (`material_balance()` `model.py`:ssä). Kyse on nappulalaskennasta, ei pelikoneen arviosta.
- **Resign** päättää pelin käyttäjän tappioon.
- Jos käyttäjä yrittää kesken pelin sulkea ohjelman, aloittaa uuden pelin tai vaihtaa moodia, ohjelma kysyy "Resign the game?". *Yes* kirjaa tappion, *No* jatkaa peliä.
- Pelin päättyessä (matti, patti, tasapeli, luovutus) PGN-otsikkoon kirjataan `Result`, ja tilarivi kertoo lopputuloksen.
- **Open in Board Mode** (vain päättyneelle pelille) avaa juuri pelatun pelin pelilautamoodissa. Siellä pelin voi käydä läpi, kokeilla "mitä jos olisin pelannut toisin" -siirtoja sivumuunnelmina ja kirjoittaa kommentteja, kuten mille tahansa avatulle PGN-pelille. Pelin aikana tätä ei voi tehdä, jottei siitä tule kiertotietä siirtojen peruuttamiseen. Tallennus (Ctrl+S) toimii molemmissa moodeissa.
- PGN-otsikot: `Event "vs Computer"`, `White`/`Black`, `Date`, `TimeControl "1800"`, `Termination` (esim. `time forfeit`), lisäksi `WhiteElo`/`BlackElo` koneen tasolle. Jokaisen siirron jälkeinen kelloaika tallennetaan siirron kommenttiin standardimuodossa `{[%clk 0:29:41]}`, jonka Lichess ja ChessBase ymmärtävät.

**Uudet asetukset** (`settings.DEFAULTS`): `mode` ("board"), `vs_minutes` (30), `vs_engine` ("stockfish"), `vs_level` ("1350"), `vs_color` ("white"), `engine_path` ("" = etsi `engines\stockfish\`-kansiosta). Ohjelma käynnistyy aina pelilautamoodissa; keskeneräistä peliä konetta vastaan ei jatketa automaattisesti.

## Python-kirjastot: mihin mikin asennetaan

Lähtökohta on ennallaan: **ei venviä**, koska Windowsin venv kopioi `Scripts`-kansioon omat `python.exe`- ja `pythonw.exe`-käynnistimet, jotka F-Secure näkee uusina exe-tiedostoina. "Lokaali ympäristö" on tässä ohjelman oma `vendor\`-kansio (`pip install --target vendor`), joka toimii venvin tavoin, mutta ilman exe-tiedostoja.

Toinen sääntö: kirjastoissa, joissa on komentorivityökaluja (console scripts), pip luo `Scripts\`-kansioon `.exe`-käynnistimen. Siksi työkalut ajetaan aina muodossa `python -m <moduuli>`, ja uusia komentorivityökaluja vältetään.

**Pysyvästi koneen Pythoniin** (yleiskäyttöiset, käännetyt binäärit, joita päivitetään harvoin):

| Kirjasto | Miksi globaalisti |
| --- | --- |
| Pillow | Valmiiksi asennettu; käännetty paketti, jota muutkin ohjelmat voivat käyttää. |
| PyMuPDF | Valmiiksi asennettu; iso käännetty paketti. |
| pytest | Kehitystyökalu, ei kuulu ohjelmaan. Aja `python -m pytest`. |
| pip | Asennusten hallinta. |

**Ohjelman `vendor\`-kansioon** (sovelluskohtaiset, puhdasta Pythonia, versio lukitaan):

| Kirjasto | Miksi vendoriin |
| --- | --- |
| python-chess (`chess==1.11.2`) | Ohjelman ydin. Lukittu versio, joka kulkee ohjelmakansion mukana, eikä päivity vahingossa muiden ohjelmien takia. |

**Laajennus ei tarvitse uusia Python-kirjastoja.** UCI-asiakas, taustasäie ja jono ovat standardikirjastoa (`subprocess`, `threading`, `queue`).

**Ei asenneta:**

| Kirjasto | Syy |
| --- | --- |
| `stockfish` (PyPI) | Turha kääre, oma UCI-asiakas on pienempi ja hallittavampi. |
| PySide6/PyQt, pygame | Isoja binääripaketteja, ei tarvetta. |
| ruff, black ym. exe-pohjaiset työkalut | Luovat exe-tiedostoja; F-Secure-riski. |

**Voi poistaa:** `altgraph`, `pefile`, `pywin32-ctypes` ovat PyInstallerin jäänteitä, eikä ohjelma käytä niitä (`python -m pip uninstall altgraph pefile pywin32-ctypes`). Tämä on valinnaista.

**Toistettavuus:** lisätään kaksi tekstitiedostoa, joiden avulla asennuksen saa tehtyä uudelleen toisella koneella:

```
# requirements-global.txt   →  python -m pip install -r requirements-global.txt
pillow==12.3.0
pymupdf==1.28.2
pytest==9.2.0

# requirements-vendor.txt   →  python -m pip install --target vendor -r requirements-vendor.txt
chess==1.11.2
```

## Toteutusvaiheet

Jokaisen vaiheen jälkeen ohjelma toimii ja testit menevät läpi.

1. **Moodikehys, ei näkyviä muutoksia.** `app/modes/` (base, board, rekisteri). `MainWindow` kysyy moodilta `can_move`/`allows`/`after_move`; `BoardView` saa `can_move`-takaisinkutsun. Game-valikko, jossa vain Board. Kaikki nykyiset testit läpi.
2. **Moottorikerros.** `app/engines/`: Engine-rajapinta, RandomEngine, UCI-asiakas, StockfishEngine, EngineWorker. Testit: RandomEngine palauttaa laillisen siirron; UCI-asiakas testataan pienellä Pythonilla kirjoitetulla valemoottorilla (`tests/fake_uci.py`); Stockfish-testit ohitetaan (`pytest.skip`), jos exeä ei löydy.
3. **Play vs Computer.** `computer_game.py` (vuorot, tulos, vanhentuneen tuloksen hylkäys) ja `clock.py` (shakkikello), molemmat testattavia ilman ikkunoita; `VsComputerMode`, dialogi, kellonäytöt, paneelin painikkeet, asetukset, tekstit `strings.py`:hin.
4. **Stockfish ja F-Secure.** Lataus, tarkiste, Unblock-File, CPU-version valinta, F-Securen tapahtumaloki, tasojen käsitestaus (1350 ja Maximum).
5. **Viimeistely ja dokumentaatio.** About-ikkunaan Stockfishin GPL-3-maininta, README:n asennusohje, `docs/ARCHITECTURE.md` ja `docs/EXTENDING.md` ajan tasalle.

## Testaus

- **Automaattiset:** Engine-rajapinta (laillinen siirto, matti yhdellä tunnetussa asemassa, `close()` sulkee prosessin), UCI-protokolla valemoottorilla, `ComputerGame` (kenen vuoro, tulos, vanhentunut tulos hylätään, Ctrl+Z estetty), `ChessClock` (vuoron vaihto, aikahäviö, ja aikahäviö on tasapeli, jos vastustajalla ei ole mattiin riittävää materiaalia; testit syöttävät kellonajan itse eivätkä odota oikeaa aikaa), moodirekisteri (jokaisella moodilla on avain ja nimi, pelilautamoodi sallii kaiken).
- **Käsin:** peli valkoisilla ja mustilla, Random-väri, aloitus nykyisestä asemasta, aikahäviö (testissä kello lyhennetään asetuksella `vs_minutes`), kello pysyy oikeassa, vaikka ikkunaa siirretään tai se pienennetään, luovutus koneen miettiessä, moodin vaihto kesken haun, ohjelman sulkeminen kesken haun (ei jää `stockfish.exe`-prosessia Tehtävienhallintaan), ohjelma ilman Stockfishia, offline-testi verkkoyhteys katkaistuna.

## Avoimet kysymykset

Seuraavat on ratkaistu oletuksella; muutettavissa ennen toteutusta:

- Siirtoja ei voi perua. *(päätetty)*
- Shakkikello: käyttäjällä 30 min, ei lisäaikaa siirtoa kohden. *(päätetty; lisäaika voidaan lisätä myöhemmin)*
- Alin taso 1320; helpompia tasoja `Skill Level` -optionilla voidaan lisätä myöhemmin.
