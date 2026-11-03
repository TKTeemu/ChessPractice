# Shakkilauta – avausteorian opettelu (suunnitelma)

3.11.2026

> Jatkoa suunnitelmille [Shakkilauta_suunnitelma.md](Shakkilauta_suunnitelma.md) ja [Pelikone_suunnitelma.md](Pelikone_suunnitelma.md). Nykyinen rakenne on kuvattu tiedostoissa [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) ja [docs/EXTENDING.md](docs/EXTENDING.md).

## Tavoite ja rajaus

Game-valikkoon lisätään kolmas moodi, **Learn Openings…**. Lisäksi tehdään kaksi kaikkia moodeja koskevaa parannusta: aina näkyvä **New Game** -painike ja tiiviimpi oikea paneeli.

| Moodi | Kuvaus |
| --- | --- |
| Board | Ennallaan. |
| Play vs Computer… | Ennallaan. New Game -painike avaa saman dialogin kuin nyt. |
| **Learn Openings…** (uusi) | Käyttäjä valitsee avauksen ja vastustajan tason. Kone pelaa oman puolensa avausteorian mukaan niin kauan kuin teoriaa riittää, ja sen jälkeen pelikone jatkaa peliä valitulla tasolla. Valintaruutu *Suggest next move* näyttää teorian mukaisen seuraavan siirron nuolena. |

**Mukana:**

- avauskirja datatiedostoina (PGN), ei koodissa
- avauksen valinta pop-up-dialogissa (ryhmitelty lista, haku, puolen ja tason valinta)
- koneen siirrot teorian mukaan; käyttäjän poikkeaminen teoriasta tunnistetaan
- *Suggest next move* -nuolet, siirron peruutus (*Take Back*) opettelumoodissa
- yhteinen New Game -painike kaikissa moodeissa
- oikean paneelin tiivistäminen

**Kieli:** kaikki tekstit, myös avausten nimet, ovat englanniksi kuten muukin käyttöliittymä (`strings.py`).

**Ei mukana (myöhemmin, rakenne sallii):** pelikoneen ehdotukset teorian loputtua, kertausharjoitukset ja tilastot avauksittain, avauskirjan muokkaus ohjelmasta.

**Ehdoton vaatimus pysyy:** ohjelma toimii offline. Avauskirja on paikallinen tiedosto.

**Laajennettavuus:**

- uusi avaus = uusi PGN-tiedosto `assets/openings/`-kansioon, ei koodimuutoksia
- uusi moodi = yksi tiedosto `app/modes/`-kansioon ja rivi rekisteriin, kuten nyt; pelikonetta käyttävä moodi perii yhteisen `EngineGameMode`-luokan eikä kopioi säie- ja kyselykoodia

## Käyttöliittymä

### Oikea paneeli, uusi järjestys

Oikea paneeli on nyt 360 px leveä, ja siirtolista venyy täyttämään kaiken vapaan tilan. Kommentti- ja FEN-kenttä vievät tilaa myös moodeissa, joissa niitä ei voi muokata. Uusi järjestys:

```
┌────────────────────────────────┐
│ [ ⟲ New Game ]                 │  ← yhteinen työkalurivi, aina näkyvissä
│ Your move                      │  ← tilarivi
├── moodin paneeli ──────────────┤  (vain jos moodilla on sellainen)
│ Réti Opening · A04–A09         │
│ Line: King's Indian Attack     │
│ Theory: 5/5 moves              │
│ [x] Suggest next move          │
│ [Take Back] [Open in Board]    │
├────────────────────────────────┤
│ 1. Nf3   d5                    │  ← siirtolista, rajattu korkeus
│ 2. g3    Nf6                   │
│ 3. Bg2   …                     │
├────────────────────────────────┤
│ |◀   ◀   ▶   ▶|   Flip         │
├────────────────────────────────┤
│ ▸ Comment & FEN                │  ← kokoontaitettava, auki Board-moodissa
└────────────────────────────────┘
```

Muutokset `main_window.py`:hin:

1. **Paneelin leveys** 360 → noin 290 px (`_px(290)`). Siirtolistan sarkaimet (`tabs=("33p", "98p")`) mahtuvat edelleen; tarkistetaan pisimmällä SAN-siirrolla (`exd8=Q+`).
2. **Moodin paneeli** siirretään siirtolistan yläpuolelle, jotta opettelun säätimet ovat lähellä tilariviä.
3. **Comment & FEN** kootaan kokoontaitettavaan kehykseen. Oletustila tulee moodilta (`Mode.show_details`, oletus `True`; pelimoodeissa `False`). Käyttäjän valinta muistetaan moodikohtaisesti asetuksissa.
4. Siirtolista saa edelleen ylimääräisen tilan (`rowconfigure(weight=1)`), mutta muut osat eivät enää vie sitä turhaan.

### New Game -painike

Uuden pelin voi nytkin aloittaa näppäimillä Ctrl+N, valikosta File > New Game tai valitsemalla Game-valikosta jo aktiivisen moodin, mutta mikään näistä ei näy ruudulla. Siksi lisätään painike, jota kaikki moodit käyttävät.

- Painike on yhteisellä työkalurivillä ylimpänä oikeassa paneelissa, ja se rakennetaan `MainWindow`:ssa, ei moodeissa. Se kutsuu samaa `MainWindow.new_game()`-metodia kuin Ctrl+N.
- Moodi päättää, mitä uusi peli tarkoittaa (`Mode.new_game()`, kuten nyt):

| Moodi | New Game |
| --- | --- |
| Board | Tyhjä lauta alkuasemaan; kysyy tallennuksesta, jos peli on muuttunut. |
| Play vs Computer | Jos peli on kesken: "Resign the game?". Sitten avautuu sama dialogi kuin nyt (Engine, Level, Color, Start from), edelliset valinnat valmiiksi valittuina. Enter aloittaa pelin samoilla asetuksilla. |
| Learn Openings | Jos peli on kesken, kysytään vahvistus. Sitten avautuu avauksen valintadialogi (ks. alla), jossa edellinen avaus, puoli, pelikone ja taso ovat valmiiksi valittuina. |

Play vs Computer toimii siis kuten nyt; painike vain tuo toiminnon näkyviin. Erillistä *Change Opening…* -painiketta ei tarvita, koska New Game avaa saman dialogin.

### Avauksen valintadialogi (pop-up)

Dialogi aukeaa, kun käyttäjä valitsee Learn Openings… -moodin tai painaa New Game. Sitä ei pidetä koko ajan näkyvissä.

```
┌ Learn Openings ─────────────────────────────────────┐
│ Search: [ret______]                                 │
│ ┌──────────────────────────────┬──────────────────┐ │
│ │ ▾ Irregular openings (A00)   │ Réti Opening     │ │
│ │     Anderssen's Opening 1.a3 │ A04–A09          │ │
│ │     …                        │ 1.Nf3 d5 2.g3 …  │ │
│ │ ▾ Flank openings             │ (pääjatko, 8     │ │
│ │     Larsen's Opening   1.b3  │  siirtoa)        │ │
│ │   ► Réti Opening       1.Nf3 │                  │ │
│ │     …                        │                  │ │
│ └──────────────────────────────┴──────────────────┘ │
│ You play:   (•) the opening (White)  ( ) the reply  │
│ Engine:     [Stockfish ▾]   Level: [1500 ▾]         │
│ [x] Vary the computer's replies                     │
│                                    [Start] [Cancel] │
└─────────────────────────────────────────────────────┘
```

- Lista on `ttk.Treeview`, jossa ryhmät ovat avattavia solmuja. Ryhmät ja järjestys tulevat avauskirjasta, eivät koodista.
- Oikealla näkyy valitun avauksen pääjatko, jotta käyttäjä näkee, mitä on opettelemassa.
- *You play: the opening / the reply* tarkoittaa käyttäjän pyytämää valintaa "avauksen tekijä on käyttäjä / kone". Väri seuraa avauksesta: valkean avauksissa avauksen tekijä on valkea, *English Defence* -puolustuksessa musta. Väri näytetään sulkeissa.
- Pelikoneen ja tason valinta on sama kuin Play vs Computer -dialogissa. Valitsimet erotetaan yhteiseksi apufunktioksi `dialogs.py`:ssä (`_engine_level_pickers`), jota molemmat dialogit käyttävät.
- *Vary the computer's replies*: kun valittu, kone arpoo teoriasiirroista painotetusti (pääjatko useimmin); muuten se pelaa aina pääjatkon.
- Viimeisin valinta muistetaan asetuksissa.

### Suggest next move

- Valintaruutu on moodin paneelissa ja näkyy koko ajan opettelumoodissa. Tila tallennetaan asetuksiin (`learn_suggest`).
- Kun ruutu on valittu ja on käyttäjän vuoro, teorian siirrot näytetään nuolina: pääjatko vahvana nuolena, muut teoriasiirrot (enintään 3) ohuempina ja läpikuultavina.
- Nuolet ovat eri väriä kuin käyttäjän oikealla napilla piirtämät nuolet, eivätkä ne katoa käyttäjän nuolien mukana.
- Ehdotukset tulevat avauskirjasta, joten niitä on vain niin kauan kuin asema on kirjassa.
- **Avausvaihe päättyy**, ja ehdotukset loppuvat pysyvästi tämän pelin osalta, kun jompikumpi täyttyy:
  1. siirtonumero ylittää rajan `learn_suggest_moves` (oletus 12; asetus, jota voi muuttaa välillä 10–15), tai
  2. peli on selvästi teorian ulkopuolella: asema on pudonnut kirjasta, eikä se palaa kirjaan (siirtovaihdolla) kahden seuraavan käyttäjän siirron aikana.
- Kun avausvaihe on ohi, valintaruutu harmaantuu, ja sen vieressä lukee *(opening phase over)*. Valinta itse säilyy asetuksissa seuraavaa peliä varten.
- Myöhemmin tähän voidaan lisätä pelikoneen ehdotus (*Suggest best move*) teorian loputtua (ks. *Myöhemmin*).

### Pelin kulku opettelumoodissa

1. Käyttäjä valitsee avauksen. Peli alkaa alkuasemasta, ja lauta käännetään käyttäjän värin mukaan.
2. **Koneen vuorolla**, kun asema on kirjassa: kone pelaa teoriasiirron pienen viiveen jälkeen (noin 0,4 s, jotta siirto erottuu). Pelikonetta ei tarvita.
3. **Koneen vuorolla**, kun asema ei ole kirjassa: pelikone laskee siirron taustasäikeessä kuten Play vs Computer -moodissa. Tilarivi kertoo kerran: *"End of theory – the engine takes over."*
4. **Käyttäjän vuorolla**, kun asema on kirjassa:
   - teoriasiirto: laskuri *Theory: n/n moves* kasvaa ja kirjan muunnelman nimi päivittyy (esim. *Line: King's Indian Attack*)
   - muu siirto, kun *Suggest next move* **ei** ole päällä: kone pelaa normaalisti käyttäjää vastaan. Pelikone ottaa vuoron heti, eikä peliä keskeytetä. Tilarivillä näkyy vain lyhyt maininta *"Out of theory"*.
   - muu siirto, kun *Suggest next move* on päällä: pelikone jatkaa samalla tavalla, mutta tilarivi kertoo myös teorian siirrot (*"Out of theory. Book moves: Nf3, c4"*), ja ne näytetään nuolina edellisessä asemassa niin kauan, kunnes käyttäjä siirtää seuraavan kerran. Käyttäjä voi halutessaan perua siirron (*Take Back*) ja kokeilla teoriasiirtoa.
5. **Kirjan kommentit**: jos avauskirjan PGN:ssä on siirtoon liittyvä kommentti (esim. avauksen idea), se näytetään kommenttikentässä. Näin avauskirja voi myös opettaa, ei vain luetella siirtoja.
6. **Take Back** poistaa siirrot käyttäjän edelliseen vuoroon asti (yleensä kaksi puolisiirtoa) ja peruu mahdollisen kesken olevan pelikonepyynnön.
7. Kelloa ei ole. Selaus (← →) on sallittu, mutta siirtää saa vain viimeisestä asemasta, kuten Play vs Computer -moodissa.
8. *Open in Board Mode* toimii kuten Play vs Computer -moodissa. PGN:ään kirjataan otsikot `Event "Opening training"`, `Opening` ja `ECO`.

## Avauskirja

### Tiedostomuoto: PGN muunnelmineen

Avaukset tallennetaan tavallisina PGN-tiedostoina kansioon `assets/openings/`. Yksi peli on yksi avaus, ja siirtopuu muunnelmineen on avausteoria.

```pgn
[Event "Réti Opening"]
[Key "reti"]
[Group "Flank openings"]
[GroupOrder "2"]
[ECO "A04-A09"]
[Side "white"]

1. Nf3 {A flexible move: White does not yet commit to a pawn structure.}
1... d5 (1... Nf6 2. c4 g6 3. g3 Bg7 4. Bg2 O-O)
2. g3 (2. c4 d4 (2... e6 3. g3 Nf6 4. Bg2 Be7) 3. e3 Nc6)
2... Nf6 3. Bg2 c6 (3... e6 4. O-O Be7 5. d3 O-O) 4. O-O Bg4 5. d3 Nbd7 *
```

Miksi PGN eikä JSON:

- Ohjelma lukee PGN:ää jo ennestään (`fileio`, vendoroitu python-chess), ja muunnelmat, kommentit ja otsikot ovat valmiina.
- Avauskirjan voi avata ja muokata ohjelman omassa Board-moodissa ja tallentaa takaisin. Erillistä editoria ei tarvita.
- Siirrot tarkistetaan laillisiksi latauksessa.

Otsikot:

| Otsikko | Merkitys |
| --- | --- |
| `Event` | Näytettävä nimi. |
| `Key` | Pysyvä tunniste asetuksiin (`learn_opening`). |
| `Group`, `GroupOrder` | Ryhmä dialogissa ja ryhmien järjestys. Avaukset näytetään ryhmän sisällä tiedoston järjestyksessä. |
| `ECO` | Näytetään nimen vieressä. |
| `Side` | `white` tai `black`: kumpi puoli on avauksen tekijä. |

Muunnelmien järjestys on painotus: ensimmäinen jatko on pääjatko. Valinnainen NAG `!` tai `?!` voi myöhemmin säätää painoja.

**Merkintä:** käyttäjän listassa on suomalainen merkintätapa (R = ratsu, L = lähetti, T = torni, D = daami). Kirjaan tallennetaan standardi englanninkielinen SAN (N, B, R, Q), koska python-chess lukee vain sitä. Esim. *Rétin avaus 1.Rf3* = `1. Nf3`. Muunnos tehdään kerran kirjaa kirjoitettaessa.

### Aloituslista

Kolme tiedostoa: kaksi ryhmää käyttäjän alkuperäisen listan mukaan ja gambiitit omana ryhmänään.

`assets/openings/irregular.pgn` – ryhmä *Irregular openings* (ECO A00):

| Key | Nimi | Aloitus (SAN) | Tekijä |
| --- | --- | --- | --- |
| `anderssen` | Anderssen's Opening | 1. a3 | valkea |
| `ware` | Ware Opening | 1. a4 | valkea |
| `durkin` | Durkin Opening | 1. Na3 | valkea |
| `dunst` | Dunst Opening | 1. Nc3 | valkea |
| `sokolsky` | Sokolsky Opening | 1. b4 | valkea |
| `saragossa` | Saragossa Opening | 1. c3 | valkea |
| `mieses` | Mieses Opening | 1. d3 | valkea |
| `vant_kruijs` | Van't Kruijs Opening | 1. e3 | valkea |
| `barnes` | Barnes Opening | 1. f3 | valkea |
| `grob` | Grob's Attack | 1. g4 | valkea |
| `clemenz` | Clemenz Opening | 1. h3 | valkea |
| `desprez` | Desprez Opening | 1. h4 | valkea |
| `amar` | Amar Opening | 1. Nh3 | valkea |
| `benko` | Benko's Opening | 1. g3 | valkea |

`assets/openings/flank.pgn` – ryhmä *Flank openings*:

| Key | Nimi | ECO | Aloitus (SAN) | Tekijä |
| --- | --- | --- | --- | --- |
| `larsen` | Larsen's Opening | A01 | 1. b3 | valkea |
| `bird` | Bird's Opening | A02–A03 | 1. f4 | valkea |
| `reti` | Réti Opening | A04–A09 | 1. Nf3 | valkea |
| `english` | English Opening | A10–A39 | 1. c4 | valkea |
| `english_defence` | English Defence | A40 | 1. c4 e6 2. d4 b6 | **musta** |

`assets/openings/gambits.pgn` – ryhmä *Gambits* (lisätty alkuperäisen listan jälkeen):

| Key | Nimi | ECO | Aloitus (SAN) | Tekijä |
| --- | --- | --- | --- | --- |
| `queens_gambit` | Queen's Gambit | D06–D69 | 1. d4 d5 2. c4 | valkea |
| `kings_gambit` | King's Gambit | C30–C39 | 1. e4 e5 2. f4 | valkea |

Kummassakin musta ratkaisee toisella siirrollaan, otetaanko gambiitti vastaan. Kirjaan tulevat molemmat päähaarat nimettyinä linjoina, jotta *Line:*-rivi kertoo, kumpaa käyttäjä pelaa:

| Avaus | Nimetyt päähaarat (vähintään) |
| --- | --- |
| Queen's Gambit | *Accepted* (2…dxc4, D20–D29), *Declined* (2…e6, D30–D69; mm. *Orthodox*, *Exchange*, *Tarrasch* 3…c5), *Slav* (2…c6, D10–D19), *Albin Countergambit* (2…e5, D08–D09) |
| King's Gambit | *Accepted* (2…exf4, C33–C39; mm. *King's Knight's Gambit* 3.Nf3, *Bishop's Gambit* 3.Bc4), *Declined* (2…Bc5, C30), *Falkbeer Countergambit* (2…d5, C31–C32) |

Näissä mustalla on monta vahvaa vastausta jo toisella siirrolla, joten *Vary the computer's replies* on hyödyllisin juuri näissä: käyttäjä joutuu vastaamaan sekä vastaanotettuun että hylättyyn gambiittiin. Mustan näkökulmasta (*You play: the reply*) käyttäjä harjoittelee puolustusta gambiittia vastaan.

Ryhmä *Gambits* on käytännöllinen, kun avauksia on vähän. Jos myöhemmin lisätään muita 1.e4- ja 1.d4-avauksia, nämä kaksi siirretään ryhmiin *Open games (1.e4 e5)* ja *Closed games (1.d4 d5)*, mikä on vain `Group`-otsikon muutos.

Tehdyt valinnat (molemmat ovat yhden PGN-otsikon muutoksia, jos niitä halutaan myöhemmin muuttaa):

- **English Defence: ECO A40.** Alkuperäisessä listassa oli A14, mutta tavallisessa ECO-luokituksessa 1.c4 e6 2.d4 b6 luetaan koodiin A40, koska se johtaa siirtovaihdolla samaan asemaan kuin 1.d4 e6 2.c4 b6. Tunnetuimmat lähteet käyttävät A40:tä, joten ohjelma näyttää saman koodin kuin kirjat ja tietokannat.
- **Benko's Opening kuuluu ryhmään *Irregular openings*.** Alkuperäisessä listassa se oli viimeisenä laita-avausten jälkeen, mutta ECO-luokituksessa 1.g3 on A00, kuten muutkin ryhmän avaukset.

**Syvyys:** jokaiselle avaukselle pääjatko 8–12 puolisiirtoa ja 2–3 yleisintä vastausta tärkeimpiin kohtiin. Laajoille avauksille (English, Réti, Bird, Queen's Gambit, King's Gambit) lisätään keskeiset päämuunnelmat nimineen (esim. *Symmetrical*, *Reversed Sicilian*, *From's Gambit*). Nimetty muunnelma merkitään kommenttiin muodossa `{Line: Reversed Sicilian}`, ja ohjelma näyttää syvimmän saavutetun nimen.

**Sisällön lähde:** siirtolinjat kirjoitetaan käsin standardilähteiden mukaan. Vaihtoehtona tai täydennyksenä voidaan käyttää Lichessin avaustietokantaa (`lichess-org/chess-openings`, lisenssi CC0): pieni työkalu `tools/import_openings.py` muuntaa kerran ladatun TSV-tiedoston nimetyt linjat (ECO A00–A40, C30–C39, D06–D69) PGN-puuksi. Ohjelma itse ei käytä verkkoa.

### Kirjan logiikka (`app/openings.py`, logiikkakerros, ei tkinteriä)

```python
@dataclass(frozen=True)
class Opening:
    key: str
    name: str
    group: str
    eco: str
    side: chess.Color          # avauksen tekijä
    game: chess.pgn.Game       # siirtopuu

@dataclass(frozen=True)
class BookMove:
    move: chess.Move
    weight: int                # pääjatko suurin
    line: str | None           # muunnelman nimi, jos tiedossa
    comment: str               # opettava kommentti

class OpeningBook:
    @classmethod
    def load(cls, folder) -> "OpeningBook": ...          # kaikki *.pgn, virheelliset ohitetaan ja raportoidaan
    def groups(self) -> list[tuple[str, list[Opening]]]: ...
    def opening(self, key) -> Opening | None: ...

class OpeningLine:
    """Yhden avauksen teoria haettuna aseman mukaan."""
    def __init__(self, opening): ...                      # indeksoi: aseman avain -> [BookMove]
    def moves(self, board) -> list[BookMove]: ...         # tyhjä = ei kirjassa
    def pick(self, board, rng, vary) -> chess.Move | None: ...
    def main_line(self) -> list[chess.Move]: ...          # dialogin esikatselua varten
```

- Hakuavain on asema ilman siirtolaskureita (`board.epd()` tai `chess.polyglot.zobrist_hash`). Siksi **siirtovaihdot** (samaan asemaan eri siirtojärjestyksellä) löytyvät automaattisesti.
- Haku tehdään vain valitun avauksen puusta. Jos käyttäjä siirtää muuhun avaukseen, ollaan teorian ulkopuolella, vaikka asema olisi toisessa avauksessa.

## Arkkitehtuuri

### Uudet ja muuttuvat tiedostot

| Tiedosto | Kerros | Muutos |
| --- | --- | --- |
| `app/openings.py` | logiikka | **Uusi.** `OpeningBook`, `Opening`, `OpeningLine`, `BookMove`. |
| `app/learning_game.py` | logiikka | **Uusi.** `LearningGame`: opettelupelin säännöt (ks. alla). |
| `app/modes/engine_mode.py` | ohjain | **Uusi.** `EngineGameMode`: pelikoneen yhteinen käyttö moodeille. |
| `app/modes/learn_openings.py` | ohjain | **Uusi.** `LearnOpeningsMode`. |
| `app/modes/vs_computer.py` | ohjain | Perii `EngineGameMode`:n. Käytös ei muutu. |
| `app/modes/base.py` | ohjain | Uudet oletusmetodit `hint_arrows()`, `show_details`; `ModeContext.take_back`. |
| `app/modes/__init__.py` | ohjain | `MODES = [BoardMode, VsComputerMode, LearnOpeningsMode]` |
| `app/board_view.py` | näkymä | Erillinen vihjenuolikerros: `set_hints(arrows)`. |
| `app/dialogs.py` | näkymä | `choose_opening()`; yhteinen `_engine_level_pickers()`. |
| `app/main_window.py` | ohjain | New Game -painike, paneelin uusi järjestys, vihjeet `refresh()`:ssä, `take_back`. |
| `app/model.py` | logiikka | `GameModel.take_back(color)`: poistaa siirrot annetun värin edelliseen vuoroon asti. |
| `app/strings.py`, `app/settings.py` | logiikka | Tekstit ja `learn_*`-asetukset. |
| `assets/openings/*.pgn` | data | **Uusi.** Avauskirja. |
| `tests/test_openings.py`, `tests/test_learning_game.py` | testit | **Uusi.** |
| `docs/ARCHITECTURE.md`, `docs/EXTENDING.md` | dokumentit | Päivitetään. |

### Mode-rajapinnan lisäykset

Jokainen lisäys tehdään perusluokkaan neutraalilla oletuksella, joten Board-moodi ei muutu.

```python
class Mode:
    show_details = True     # Comment & FEN -osio auki oletuksena

    def hint_arrows(self):
        """Vihjenuolet laudalle: [(from_sq, to_sq, style)], style "main" tai "alt". Oletus []."""
        return []
```

```python
@dataclass
class ModeContext:
    ...
    take_back: Callable     # take_back(color): siirrot pois tämän värin edelliseen vuoroon asti, sitten refresh
```

- `MainWindow.refresh()` kysyy `mode.hint_arrows()` ja välittää ne `board.set_hints()`:lle, samaan tapaan kuin `title()` ja `status_text()` kysytään nyt. Moodi ei siis koske näkymään suoraan.
- Uusi komento `allows("take_back")`. Board-moodissa sitä vastaa nykyinen Ctrl+Z (`delete_last`).

### Yhteinen pelikonemoodi `EngineGameMode`

`VsComputerMode` sisältää nyt säikeen käytön, kyselyajastimen, pyyntötunnisteet ja virheenkäsittelyn. Opettelumoodi tarvitsee täsmälleen saman. Ne siirretään perusluokkaan:

```python
class EngineGameMode(Mode):
    """Moodi, jossa kone pelaa toista puolta. Aliluokka toteuttaa game-olion ja koneen siirron valinnan."""

    def start_engine(self, engine_cls, level): ...        # EngineWorker, _poll-ajastin
    def request_engine_move(self): ...                    # worker.request(board, level, game.new_request())
    def play_computer_move(self, move, delay_ms=0): ...   # kirjasiirto tai pelikoneen siirto
    def deactivate(self): ...                             # ajastimet ja worker kiinni
    def computer_turn(self):                              # aliluokka ylikirjoittaa
        self.request_engine_move()
```

- `VsComputerMode.computer_turn()` = aina pelikone (nykyinen käytös).
- `LearnOpeningsMode.computer_turn()` = kirjasiirto, jos asema on kirjassa, muuten pelikone.
- Pelikoneen prosessi käynnistyy vasta ensimmäisestä pyynnöstä (kuten `EngineWorker` jo tekee), joten pelkässä teoriaosuudessa Stockfishia ei käynnistetä lainkaan.

Uusi pelikonetta käyttävä moodi (esim. tulevaisuudessa *Solve Puzzle*, jossa kone vastaa ratkaisulinjaa pitkin) toteuttaa vain oman `computer_turn()`-metodinsa ja oman game-luokkansa.

### `LearningGame` (logiikkakerros)

`ComputerGame`-luokan vastine ilman kelloa, testattavissa ilman näyttöä:

```python
class LearningGame:
    def __init__(self, line: OpeningLine, user_color, engine_label, vary, rng): ...
    # Tila
    in_book: bool; book_moves_played: int; user_book_hits: int
    deviation: list[BookMove] | None     # teoriasiirrot, jos käyttäjä juuri poikkesi
    current_line_name: str | None
    opening_phase: bool                  # False, kun siirtoraja ylittyy tai peli on selvästi ohi teorian
    # Kyselyt
    def can_move(board, color, at_end) -> bool
    def allows(command) -> bool          # {"navigate", "edit_comment", "take_back"}
    def status_text(board) -> str
    def suggestions(board) -> list[BookMove]   # tyhjä, kun opening_phase on False
    def computer_reply(board) -> chess.Move | None   # kirjasiirto tai None = kysy pelikoneelta
    # Tapahtumat
    def move_played(board_before, move, board_after)  # päivittää osumat, poikkeaman, teorian lopun
    def took_back(board)
    # Pyynnöt (sama malli kuin ComputerGame)
    def new_request() -> int; def is_current(request_id) -> bool
    def write_headers(headers)
```

### Asetukset (`settings.DEFAULTS`)

| Avain | Oletus | Merkitys |
| --- | --- | --- |
| `learn_opening` | `"reti"` | Viimeksi valittu avaus (`Key`). |
| `learn_role` | `"opening"` | `"opening"` = käyttäjä pelaa avauksen, `"reply"` = kone pelaa avauksen. |
| `learn_engine` | `"stockfish"` | |
| `learn_level` | `"1320"` | |
| `learn_vary` | `True` | Koneen vastausten vaihtelu. |
| `learn_suggest` | `True` | *Suggest next move*. |
| `learn_suggest_moves` | `12` | Siirtonumero, jonka jälkeen avausvaihe on ohi ja ehdotukset loppuvat. |
| `details_open` | `"board"` | Moodit, joissa Comment & FEN on auki (pilkuilla eroteltu merkkijono, koska asetusten tyypin pitää vastata oletusta). |

### Testit

- `test_openings.py`: kaikki `assets/openings/*.pgn` latautuvat, jokaisella avauksella on yksilöllinen `Key` ja kelvollinen `Side`; siirtovaihto löytyy; `pick(vary=False)` palauttaa pääjatkon; avausten ensimmäiset siirrot vastaavat yllä olevaa taulukkoa.
- `test_learning_game.py`: poikkeama tunnistetaan, teorian loppu tunnistetaan, `computer_reply` palauttaa `None` kirjan ulkopuolella, Take Back palauttaa tilan, musta avauksen tekijänä (*English Defence*) toimii, avausvaihe päättyy siirtorajalla ja kun peli on kaksi käyttäjän siirtoa teorian ulkopuolella, ja siirtovaihdolla kirjaan palaava peli jatkaa avausvaihetta.
- `test_modes.py`: uusi moodi rekisterissä; `fake_context` saa `take_back`-kentän.
- Play vs Computer -moodin nykyiset testit ajetaan sellaisenaan `EngineGameMode`-refaktoroinnin jälkeen.

## Toteutusjärjestys

Jokainen vaihe on käyttökelpoinen yksinään, ja testit menevät läpi jokaisen vaiheen jälkeen.

1. **New Game -painike ja paneelin tiivistys.** Pelkkä `main_window.py` ja `Mode.show_details`. Hyöty heti kaikissa moodeissa.
2. **Refaktorointi:** `EngineGameMode` erotetaan `VsComputerMode`:sta; `hint_arrows()` + `BoardView.set_hints()`; `ModeContext.take_back` + `GameModel.take_back`. Käytös ei muutu.
3. **Avauskirja:** `app/openings.py`, kolme PGN-tiedostoa kaikille 21 avaukselle, `test_openings.py`.
4. **Opettelumoodi:** `LearningGame`, `LearnOpeningsMode`, `choose_opening()`-dialogi, tekstit ja asetukset, testit.
5. **Dokumentit:** ARCHITECTURE.md ja EXTENDING.md (uusi resepti: *Add an opening*, `EngineGameMode` moodireseptiin).

## Myöhemmin

- **Ehdotus teorian jälkeen (*Suggest best move*):** ehdotus jatkuu avausvaiheen loppuun pelikoneen parhaalla siirrolla (toinen `EngineWorker` korkealla tasolla, lyhyt miettimisaika). Rakenne valmis: `hint_arrows()` voi palauttaa myös pelikoneen siirron.
- **Kertausharjoitus:** avauksen muunnelmat käydään läpi järjestyksessä, ja virheelliset linjat toistetaan useammin (tilastot asetuksiin tai omaan JSON-tiedostoon).
- **Lisää avauksia:** muut avoimet ja suljetut avaukset (esim. Italian, Ruy Lopez, Sicilian, London System) ovat pelkkiä uusia PGN-tiedostoja.
- **Avauksen tunnistus Board-moodissa:** sama `OpeningBook` voi näyttää laudan yläpuolella, mikä avaus ja muunnelma on pelissä.

## Päätökset

Ensimmäisen version avoimet kysymykset, ratkaistu 3.11.2026:

1. **Kieli:** kaikki tekstit, myös avausten nimet, ovat englanniksi.
2. **New Game:** avaa moodin dialogin (Play vs Computer: Engine, Level, Color; Learn Openings: avauksen valinta). Edelliset valinnat ovat valmiiksi valittuina.
3. **Poikkeama teoriasta:** kone jatkaa peliä normaalisti. Jos *Suggest next move* on päällä, teoriasiirrot näytetään lisäksi tilarivillä ja nuolina. Ehdotukset loppuvat, kun avausvaihe on ohi: siirtoraja (oletus 12) ylittyy, tai peli on pysynyt kaksi käyttäjän siirtoa teorian ulkopuolella.
4. **ECO ja ryhmät:** käyttäjä ei ottanut kantaa, joten noudatetaan tavallista ECO-luokitusta: English Defence on A40, ja Benko's Opening kuuluu ryhmään *Irregular openings*.
