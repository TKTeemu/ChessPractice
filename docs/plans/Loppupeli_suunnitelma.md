# Shakkilauta – loppupelien harjoittelu (suunnitelma)

> **Historiallinen asiakirja.** Tämä suunnitelma on toteutettu, eikä sitä enää päivitetä. Ohjelman nykyinen rakenne on kuvattu tiedostoissa [ARCHITECTURE.md](../ARCHITECTURE.md) ja [EXTENDING.md](../EXTENDING.md); poikkeamat suunnitelmasta on lueteltu EXTENDING.md:n lopussa.

3.11.2026

> Jatkoa suunnitelmille [Shakkilauta_suunnitelma.md](Shakkilauta_suunnitelma.md), [Pelikone_suunnitelma.md](Pelikone_suunnitelma.md) ja [Avausteoria_suunnitelma.md](Avausteoria_suunnitelma.md). Nykyinen rakenne on kuvattu tiedostoissa [docs/ARCHITECTURE.md](../ARCHITECTURE.md) ja [docs/EXTENDING.md](../EXTENDING.md). Kun suunnitelma on toteutettu, tiedosto siirretään kansioon `docs/plans/` ja merkitään historialliseksi kuten muutkin.

## Tavoite ja rajaus

Game-valikkoon lisätään neljäs moodi, **Endgame Samples…**. Ohjelmassa on noin 100 tallennettua loppupeliasemaa viidellä vaikeustasolla. Käyttäjä valitsee vaikeustason, ohjelma arpoo aseman, ja käyttäjä pelaa sen loppuun tietokonetta vastaan.

| Moodi | Kuvaus |
| --- | --- |
| Board, Play vs Computer…, Learn Openings… | Ennallaan. |
| **Endgame Samples…** (uusi) | Käyttäjä valitsee vain vaikeustason (1–5). Ohjelma arpoo tasolta aseman, jota ei ole vielä pelattu tämän suorituskerran aikana. Käyttäjä pelaa siirrossa olevaa puolta, kone toista. Kone puolustaa parhaansa mukaan: se noudattaa tallennettua puolustusta niin pitkään kuin ratkaisupuu riittää ja pelaa sen jälkeen täydellä teholla. Oikean paneelin **success-valo** kertoo, onko sekvenssi mennyt oikein (vihreä) tai pieleen (punainen). Peli jatkuu kummassakin tapauksessa. |

**Mukana:**

- loppupeliasemat datatiedostoina (PGN, `SetUp`/`FEN`), ei koodissa; ratkaisu siirtopuuna
- vaikeustason valinta pop-up-dialogissa, aseman arvonta ilman toistoa saman ajon aikana
- vastustajan **tasoa ei valita**: kone pelaa ratkaisupuun puolustuksen ja sen jälkeen aina täydellä teholla (Stockfish, *Maximum*). Ei ELO-valitsinta eikä pelikoneen valintaa
- 15 minuutin kello (asetus), peli päättyy mattiin, aikaan tai pattiin (ja muihin tasapeleihin, ks. *Päätökset*)
- success-valo (harmaa / vihreä / punainen) oikeassa paneelissa
- *Suggest next move* -valinta
- siirron peruutus (*Take Back*)
- aseman lähde, laatija ja vuosiluku laudan yläpuolella

**Kieli:** käyttöliittymän tekstit ja asemien nimet englanniksi kuten muuallakin (`strings.py`). Tämä suunnitelma on suomeksi.

**Ei mukana (myöhemmin, rakenne sallii):** tilastot ja kertaus, tietyn aseman valinta listasta, oma asemaeditori, Syzygy-taulukot pakollisina.

**Ehdoton vaatimus pysyy:** ohjelma toimii offline. Asemat ovat paikallisia tiedostoja, ja arviointi tehdään paikallisella Stockfishillä.

**Laajennettavuus:**

- uusi asema = uusi peli PGN-tiedostoon `assets/endgames/`-kansiossa, ei koodimuutoksia
- uusi moodi perii `EngineGameMode`:n (tai alla kuvatun kellollisen välitason) eikä kopioi säie-, kello- tai kyselykoodia

## Käyttöliittymä

### Laudan yläpuoli: aseman tiedot

Nyt laudan yläpuolella on yksi rivi: moodin otsikko vasemmalla (`Mode.title()`) ja pistetilanne oikealla (`Mode.score_text()`). Lisätään toinen, ohuempi rivi aseman lähdetiedoille:

```
Endgame Samples · Level 5 · Saavedra Position                Material: you +1
Fernando Saavedra (after G. Barbier) · Glasgow Weekly Citizen · 1895
┌───────────────────────────────────────────────┐
│ Black (Stockfish 1500)                  14:52 │
│                  (lauta)                      │
```

- Uusi `Mode.subtitle() -> str | None`, oletus `None`. `MainWindow.refresh()` näyttää sen otsikkorivin alla pienellä, himmeällä fontilla (`FONT_SMALL`, `MUTED_FG`) ja piilottaa rivin, kun arvo on `None`. Muut moodit eivät muutu.
- Teksti kootaan PGN-otsakkeista `Composer`, `Source` ja `Year`; puuttuvat jätetään pois. Jos mitään ei tiedetä (esim. perusmatit), rivillä lukee *Classic endgame position*.

### Oikea paneeli

```
┌────────────────────────────────┐
│ [ ⟲ New Game ]                 │  ← yhteinen työkalurivi
│ Your move                      │  ← tilarivi
├── moodin paneeli ──────────────┤
│ ●  Success                     │  ← valo: harmaa / vihreä / punainen
│ Goal: White to play and win    │
│ Level 5 · 3 of 20 played       │
│ [x] Suggest next move          │
│ [Take Back] [Resign]           │
│ [Open in Board Mode]           │
├────────────────────────────────┤
│ 1. c7    Rd6+                  │  ← siirtolista
│ 2. Kb5   …                     │
├────────────────────────────────┤
│ |◀   ◀   ▶   ▶|   Flip         │
├────────────────────────────────┤
│ ▸ Comment & FEN                │  ← oletuksena kiinni
└────────────────────────────────┘
```

- **Success-valo** on pieni `tk.Canvas`, jossa ympyrä, ja sen vieressä lyhyt teksti. Uusi apufunktio `widgets.light(parent)` ja metodi `set_state(state)`; värit `theme.py`:hin (`LIGHT_PENDING`, `LIGHT_SUCCESS`, `LIGHT_FAIL`).

  | Tila | Väri | Teksti |
  | --- | --- | --- |
  | `pending` | harmaa | *In progress* |
  | `success` | vihreä | *Solved* |
  | `fail` | punainen | *Missed – keep playing* |

- *Goal* kertoo tehtävän: *White to play and win* / *Black to play and draw*.
- Laskuri *3 of 20 played* kertoo, montako tason asemista on jo pelattu tämän ajon aikana.
- Kellot näkyvät pelaajien nimien vieressä kuten Play vs Computer -moodissa (`ctx.set_clocks`).
- Comment & FEN on oletuksena kiinni (`show_details = False`); siihen tulee aseman kommentti, kun ratkaisupuussa on sellainen.

### Valintadialogi (pop-up)

Avautuu, kun moodi valitaan Game-valikosta tai painetaan New Game.

```
┌ Endgame Samples ───────────────────────────────────┐
│ Difficulty:                                        │
│   ( ) 1  Basic mates                (20, 0 played) │
│   ( ) 2  Elementary endings         (20, 4 played) │
│   (•) 3  Theoretical positions      (20, 1 played) │
│   ( ) 4  Practical endgames         (20, 0 played) │
│   ( ) 5  Studies                    (20, 0 played) │
│ Time:     [15] min                                 │
│                                   [Start] [Cancel] │
└────────────────────────────────────────────────────┘
```

- Dialogissa ei ole pelikoneen eikä tason valintaa; vastustaja on aina Stockfish täydellä teholla (ks. *Koneen vastustaja*). Jos Stockfishiä ei ole, dialogi kertoo, että kone pelaa vain tallennetun puolustuksen ja sen jälkeen satunnaisia siirtoja.
- Tasojen nimet ja asemamäärät luetaan kokoelmasta, eivät ole koodissa (tason nimi on PGN-tiedoston otsakkeessa, ks. alla).
- Viimeisin valinta muistetaan asetuksissa. Enter = Start.

### Pelin kulku

1. **Arvonta.** Valitun tason asemista arvotaan yksi, jota ei ole pelattu tämän ajon aikana (ks. *Arvonta ilman toistoa*).
2. **Alku.** Peli alkaa aseman FEN:stä. Käyttäjä pelaa siirrossa olevaa puolta; lauta käännetään sen mukaan. Kello käynnistyy käyttäjän ensimmäisestä siirrosta kuten Play vs Computer -moodissa.
3. **Koneen vuoro.** Ks. *Koneen vastustaja*: ensin tallennettu puolustus, sen jälkeen Stockfish täydellä teholla.
4. **Käyttäjän siirto** arvioidaan (ks. *Onnistumisen arviointi*), ja valo päivittyy. Peli jatkuu valon väristä riippumatta.
5. **Pelin loppu:** matti, pattitilanne, ajan loppuminen tai muu sääntöjen mukainen tasapeli. *Resign* lopettaa pelin heti. Lopputulos näkyy tilarivillä, valo jää viimeiseen tilaansa.
6. **Take Back** poistaa siirrot käyttäjän edelliseen vuoroon asti (`ctx.take_back`), peruu kesken olevan konepyynnön ja laskee valon uudelleen (ks. alla). Toimii myös matin tai patin jälkeen, mutta ei ajan loputtua. Kello ei palaa ajassa taaksepäin.
7. **Open in Board Mode** kuten muissa pelimoodeissa. PGN:ään kirjataan `Event "Endgame practice"`, `SetUp "1"`, `FEN`, `EndgameKey`, `Difficulty`, sekä `Source`/`Composer`/`Year`, jos tiedossa.

### Suggest next move

- Valintaruutu moodin paneelissa, tila asetuksissa (`end_suggest`, oletus `False`).
- Käyttäjän vuorolla näytetään nuoli (`Mode.hint_arrows()`, sama vihjekerros kuin Learn Openingsissa):
  - **ratkaisupuun sisällä:** tallennettu ratkaisusiirto vahvana nuolena, vaihtoehtoiset oikeat siirrot ohuina
  - **ratkaisupuun ulkopuolella** (käyttäjä tai kone poikkesi): Stockfishin paras siirto (ks. alla)
- Vihjeen käyttö ei muuta valoa, mutta paneeliin kirjataan *Hints used: n* ja PGN:n otsakkeeseen `HintsUsed`. (Ks. *Avoimet kysymykset* 3.)

## Onnistumisen arviointi

Tämä on moodin vaikein osa: ratkaisupuu ei kata kaikkia käyttäjän järkeviä siirtoja eikä kaikkia koneen vastauksia, joten pelkkä "vastaako siirto tallennettua" ei riitä. Käytetään kahta kerrosta.

### 1. Ratkaisupuu (kirja)

Asemaan tallennettu siirtopuu on kuin avauskirja: siirrot haetaan aseman perusteella (kuten `OpeningLine`, joten siirtovaihdot löytyvät).

| Käyttäjän siirto ratkaisupuun asemassa | Tulos |
| --- | --- |
| pääjatkon tai merkitsemättömän muunnelman siirto | oikein, valo pysyy / muuttuu ok-tilaan |
| muunnelma, jonka siirrolla on NAG `?` tai `??` (tunnettu väärä yritys) | **punainen heti**; muunnelman kommentti näytetään selityksenä |
| muu siirto | ratkaistaan arvioijalla (kerros 2) |

### 2. Arvioija (Stockfish täydellä voimalla)

Sama `EngineWorker` (Stockfish, *Maximum*, miettimisaika ~1 s) arvioi aseman jokaisen käyttäjän siirron jälkeen, kun ollaan ratkaisupuun ulkopuolella. Yksi analyysipyyntö antaa kerralla sekä arvion että koneen parhaan vastasiirron, joten erillistä arvioijaa ei tarvita: arvio ratkaisee valon ja siirto on koneen vastaus. Tavoite (`Goal`) on käyttäjän näkökulmasta:

| Tavoite | Siirto on virhe (punainen), kun arvio siirron jälkeen on … |
| --- | --- |
| `win` | ei enää voittava: ei mattia käyttäjälle eikä vähintään `+WIN_CP` (oletus +300 cp) |
| `draw` | häviävä: matti käyttäjää vastaan tai alle `−LOSS_CP` (oletus −300 cp) |

- Raja-arvoissa on hystereesi, jotta yksi epävarma arvio ei käännä valoa: virhe vaatii selvän pudotuksen (esim. `win`-tavoitteessa arvio putoaa alle +150 cp).
- Arvio ja vastasiirto tulevat taustasäikeestä samalla kertaa; valo päivittyy, kun koneen siirto ilmestyy.
- Jos Stockfish ei ole käytettävissä, arvioijaa ei ole: ratkaisupuun ulkopuolinen siirto jättää valon harmaaksi, kone pelaa satunnaisen siirron, ja tilarivi kertoo *"No engine to judge moves off the solution"*.
- **Valinnainen tarkkuus:** jos kansiossa `engines/syzygy/` on Syzygy-taulukot (3–5 nappulaa), niiden polku annetaan Stockfishille (`SyzygyPath`), jolloin arvio on vähänappulaisissa asemissa täsmällinen. Ohjelma toimii ilman niitä.

### Koneen vastustaja

Kone valitsee siirtonsa tässä järjestyksessä:

1. **Ratkaisupuu.** Jos asema on ratkaisupuussa ja siinä on koneen puolen siirtoja, kone pelaa niistä yhden (pääjatko todennäköisimmin, muunnelmat joskus, jotta pelit vaihtelevat). Tallennettu puolustus on tutkielmissa ja teoreettisissa asemissa yleensä juuri se vaikein.
2. **Stockfish täydellä teholla**, kun asema on puun ulkopuolella (yllä oleva analyysipyyntö).
3. **Satunnainen laillinen siirto** vain, jos Stockfishiä ei ole.

Näin vastustaja on aina vahva eikä tasoa tarvitse valita. Pelikoneen valinta ja taso poistuvat dialogista ja asetuksista.

### Valon tilat

| Tapahtuma | Valo |
| --- | --- |
| peli alkaa | harmaa |
| käyttäjä tekee virheen (kerros 1 tai 2) | **punainen**, ja pysyy punaisena (paitsi Take Back) |
| käyttäjä pelaa ratkaisupuun loppuun asti ilman virhettä | **vihreä** |
| tavoite saavutetaan ilman virhettä: `win` → käyttäjä mattaa; `draw` → peli päättyy tasapeliin | **vihreä** |
| tavoite jää saavuttamatta: `win` → patti, tasapeli tai aika loppuu; `draw` → käyttäjä matataan tai aika loppuu | **punainen** |

- Punainen on pysyvä tälle yritykselle: myöhemmät hyvät siirrot eivät muuta sitä vihreäksi. Vihreä voi vielä muuttua punaiseksi, jos käyttäjä esimerkiksi pattittaa voitetun aseman.
- **Take Back** laskee valon uudelleen jäljelle jääneistä siirroista: jokainen arvio tallennetaan siirtokohtaisesti, joten perutun siirron arvio vain poistuu. Peruutukset lasketaan (*Take backs: n* paneelissa ja PGN:ssä).

## Asemakokoelma

### Tiedostomuoto

Yksi PGN-tiedosto per vaikeustaso: `assets/endgames/level1.pgn` … `level5.pgn`, noin 20 asemaa kussakin. Yksi peli on yksi asema.

```pgn
[Event "Saavedra Position"]
[Key "saavedra"]
[Difficulty "5"]
[DifficultyName "Studies"]
[Goal "win"]
[Composer "Fernando Saavedra (after Georges Barbier)"]
[Source "Glasgow Weekly Citizen"]
[Year "1895"]
[SetUp "1"]
[FEN "8/8/1KP5/3r4/8/8/8/k7 w - - 0 1"]

{White's pawn is one step from queening, but the rook keeps checking.}
1. c7 Rd6+ 2. Kb5 Rd5+ 3. Kb4 Rd4+ 4. Kb3 Rd3+ 5. Kc2 Rd4
6. c8=R! (6. c8=Q? {Rc4+ 7. Qxc4 is stalemate.} Rc4+ 7. Qxc4) 6... Ra4 7. Kb3 *
```

| Otsake | Pakollinen | Merkitys |
| --- | --- | --- |
| `Event` | kyllä | Aseman nimi (näkyy otsikossa). |
| `Key` | kyllä | Yksilöllinen, pysyvä tunniste. Ei koskaan muuteta. |
| `Difficulty` | kyllä | 1–5. |
| `DifficultyName` | ensimmäisessä pelissä | Tason nimi dialogiin (*Basic mates* …). |
| `Goal` | kyllä | `win` tai `draw`, siirrossa olevan puolen näkökulmasta. |
| `SetUp`, `FEN` | kyllä | Alkuasema. Siirrossa oleva puoli = käyttäjä. |
| `Composer`, `Source`, `Year` | ei | Näytetään laudan yläpuolella, jos annettu. |

**Siirtopuu:** pääjatko on ratkaisu. Käyttäjän puolen muunnelma ilman NAG-merkkiä on yhtä hyvä vaihtoehto; muunnelma, jonka ensimmäisellä siirrolla on `?`/`??`, on tunnettu väärä yritys (punainen valo, kommentti selittää). Koneen puolen muunnelmat ovat vaihtoehtoisia puolustuksia. Kommentit näytetään kommenttikentässä kuten Learn Openingsissa.

### Vaikeustasot ja aloituslista

Lista on luonnos; jokainen asema tarkistetaan työkalulla ennen lisäämistä (ks. *Datan tarkistus*). Lähde, laatija ja vuosi kirjataan vain, kun ne on varmistettu.

**Mistä asemat tulevat?** Sinun ei tarvitse tuntea niitä etukäteen. Kerään asemat itse tunnetuista, hyvin dokumentoiduista aiheista: oppikirjojen perusasemat (K+Q vs K, oppositio, sotilaan neliö), nimetyt teoreettiset asemat (Lucena, Philidor, Vančura, Saavedra, Réti) sekä klassiset tutkielmat. Nämä löytyvät mm. Wikipedian loppupeliartikkeleista ja shakkiseurojen oppimateriaaleista. Ohjelma ei lataa mitään verkosta ajon aikana. Stockfish tarkistaa jokaisen aseman (`tools/check_endgames.py`), ja sinä voit katsoa valmiin listan (nimi + taso + tavoite) ennen kuin asemat otetaan käyttöön. Lisäyksiä voi tehdä myöhemmin PGN-tiedostoon kuka tahansa.

| Taso | Nimi | Sisältö (esimerkkejä) | Kpl |
| --- | --- | --- | --- |
| 1 | Basic mates | K+Q vs K, K+R vs K, kaksi tornia (tikapuumatti), K+Q vs K pattiansoin, kuningas + sotilas vs kuningas helpoimmat asemat | ~20 |
| 2 | Elementary endings | sotilaan neliö, oppositio ja avainruudut, K+2B vs K, Q vs sotilas 7. rivillä, torni vs sotilas, Philidorin asema (Philidor, *L'analyse des échecs*, 1777) | ~20 |
| 3 | Theoretical positions | Lucenan asema (Salvio 1634), Vančuran asema (1924), K+B+N vs K, Q vs R (Philidor 1777), kolmiointi, Centurinin asema (1856), läpimurto kolme sotilasta vastaan kolme | ~20 |
| 4 | Practical endgames | tunnettujen mestaripelien loppupelit (torni-, lähetti- ja ratsuloppupelit), vastaavat ruudut, Lasker–Reichhelmin asema (1901) | ~20 |
| 5 | Studies | Saavedran asema (1895), Rétin tutkielma (1921), muita klassisia tutkielmia (esim. Troitzki, Kubbel, Platovin veljekset, Rinck) | ~20 |

**Tekijänoikeus:** shakkiasemat ja siirrot ovat tosiasioita, mutta selitystekstit kirjoitetaan itse, eikä niitä kopioida kirjoista. Tutkielmat valitaan pääosin klassisista (ennen 1950-lukua julkaistuista) lähteistä.

### Kokoelman logiikka (`app/endgames.py`, logiikkakerros, ei tkinteriä)

```python
@dataclass(frozen=True)
class EndgameSample:
    key: str; name: str; difficulty: int; goal: str        # "win" | "draw"
    fen: str; composer: str; source: str; year: str
    game: chess.pgn.Game                                   # siirtopuu
    def side(self) -> chess.Color                          # siirrossa oleva puoli = käyttäjä
    def credit_text(self) -> str                           # "Composer · Source · Year" tai ""

class EndgameCollection:
    @classmethod
    def load(cls, folder) -> "EndgameCollection"           # errors: [(tiedosto, virhe)] kuten OpeningBook
    def levels(self) -> list[tuple[int, str, int]]         # (taso, nimi, asemien määrä)
    def samples(self, difficulty) -> list[EndgameSample]

class SolutionTree:                                        # aseman siirrot, haku asemasta (vrt. OpeningLine)
    def moves(self, board) -> list[SolutionMove]           # move, wrong (NAG ?/??), comment
    def at_end(self, board) -> bool                        # ratkaisu pelattu loppuun

class EndgameDeck:
    """Arvonta ilman toistoa saman ajon aikana."""
    def __init__(self, collection, rng): ...
    def draw(self, difficulty) -> EndgameSample
    def played(self, difficulty) -> int
```

Jos `OpeningLine`:n asemahaku sopii sellaisenaan, `SolutionTree` käyttää sitä (tai yhteinen apufunktio erotetaan `openings.py`:stä) sen sijaan, että hakulogiikka kirjoitettaisiin uudelleen.

### Arvonta ilman toistoa

- `EndgameDeck` pitää tasoittain sekoitetun pakan ("shuffle bag"). `draw()` ottaa pakasta seuraavan; kun pakka on tyhjä, se sekoitetaan uudelleen niin, ettei juuri pelattu asema tule heti ensimmäisenä.
- Pakka elää **moodiluokan tasolla** (ei moodi-instanssissa, koska `set_mode` luo moodista uuden olion jokaisella valinnalla), joten se säilyy moodin vaihdon yli mutta nollautuu, kun ohjelma käynnistetään uudelleen.
- Satunnaislähde annetaan parametrina, jotta testit ovat toistettavia.

## Arkkitehtuuri

### Uudet ja muuttuvat tiedostot

| Tiedosto | Kerros | Muutos |
| --- | --- | --- |
| `app/endgames.py` | logiikka | **Uusi.** `EndgameSample`, `EndgameCollection`, `SolutionTree`, `EndgameDeck`. |
| `app/endgame_game.py` | logiikka | **Uusi.** `EndgameGame(ComputerGame)`: säännöt, valo, arviot (ks. alla). |
| `app/modes/timed_mode.py` | ohjain | **Uusi.** `TimedGameMode(EngineGameMode)`: kellon tikitys, kellojen näyttö ja Resign siirretään tänne `VsComputerMode`:sta. |
| `app/modes/vs_computer.py` | ohjain | Perii `TimedGameMode`:n. Käytös ei muutu. |
| `app/modes/endgames.py` | ohjain | **Uusi.** `EndgameMode(TimedGameMode)`. |
| `app/modes/base.py` | ohjain | Uusi oletusmetodi `subtitle()` → `None`. |
| `app/modes/__init__.py` | ohjain | `MODES = [BoardMode, VsComputerMode, LearnOpeningsMode, EndgameMode]` |
| `app/engines/base.py`, `stockfish.py`, `uci.py` | logiikka | `Engine.analyse(board, think_time, stop) -> Analysis(move, cp, mate)`; UCI-asiakas lukee `info … score cp/mate` -rivit. `Engine.can_analyse` (Random: `False`). Valinnainen `SyzygyPath`. |
| `app/engines/worker.py` | logiikka | `request(…, analyse=False)`: palauttaa `Analysis`:n (arvio + paras siirto) pelkän siirron sijaan. |
| `app/main_window.py` | ohjain | Alaotsikkorivi laudan yläpuolelle, `refresh()` kysyy `mode.subtitle()`. |
| `app/widgets.py`, `app/theme.py` | näkymä / logiikka | `light()`-valo ja sen värit. |
| `app/dialogs.py` | näkymä | `choose_endgame()`. |
| `app/strings.py` | logiikka | Tekstit (`MODE_ENDGAMES = "Endgame Samples…"` jne.). |
| `assets/endgames/level1–5.pgn` | data | **Uusi.** Noin 100 asemaa. |
| `tools/check_endgames.py` | työkalu | **Uusi.** Datan tarkistus Stockfishillä (ks. alla). |
| `tests/test_endgames.py`, `tests/test_endgame_game.py` | testit | **Uusi.** |
| `docs/ARCHITECTURE.md`, `docs/EXTENDING.md` | dokumentit | Päivitetään; uusi resepti *Add an endgame*. |

### `EndgameGame` (logiikkakerros)

`ComputerGame` tuo jo kellon, ajan loppumisen, luovutuksen ja `move_played`-rungon, joten `EndgameGame` perii sen:

```python
class EndgameGame(ComputerGame):
    EVENT = S.END_EVENT
    ALLOWED_DURING_GAME = frozenset({TAKE_BACK})
    ALLOWED_AFTER_GAME = frozenset({TAKE_BACK, EDIT_COMMENT})   # ei TAKE_BACK ajan loputtua

    def __init__(self, sample, user_color, minutes=15, now=time.monotonic): ...   # ei pelikonetta/tasoa
    # Tila
    light: str                    # "pending" | "success" | "fail"
    judgements: list              # yksi arvio per käyttäjän siirto: "ok" | "fail" | "pending"
    take_backs: int; hints_used: int
    # Kyselyt
    def goal_text(self) -> str
    def hints(self, board, engine_move=None) -> list   # ratkaisupuusta, muuten Stockfishin siirto
    def needs_judging(self, board) -> bool              # ratkaisupuun ulkopuolella ja Stockfish käytössä
    def tree_reply(self, board, rng) -> chess.Move | None   # koneen tallennettu puolustus, jos on
    # Tapahtumat
    def move_played(self, board)                        # + ratkaisupuu, pelin loppu → valo
    def judged(self, ply, analysis)                     # arvioijan tulos → valo
    def took_back(self, board)                          # judgements lyhennetään, valo lasketaan uudelleen,
                                                        # kello käyntiin käyttäjälle
    def write_headers(self, headers)                    # SetUp, FEN, EndgameKey, Difficulty, Source…
```

Arvioijan tulos on aina sidottu siirron järjestysnumeroon (ply) ja pyyntötunnisteeseen, joten peruutuksen jälkeen saapuva vanha arvio hylätään samalla tavalla kuin vanhentunut konesiirto.

### `EndgameMode` (ohjain)

- `choose()` → `choose_endgame(…)`; `start(config)` arpoo aseman (`EndgameDeck`), luo `EndgameGame`:n, `ctx.new_game(chess.Board(sample.fen))`, kääntää laudan ja käynnistää Stockfishin täydellä teholla (ei käyttäjän valintaa).
- `after_move()` → `game.move_played`; sitten koneen vuoro: `tree_reply()` ensin, muuten analyysipyyntö (arvio → `judged`, paras siirto → koneen siirto).
- `title()`, `subtitle()`, `hint_arrows()`, `build_panel()` (valo, tavoite, laskurit, Suggest, Take Back, Resign, Open in Board Mode), `menu_items()`.
- `deactivate()` sulkee workerin kuten perusluokassa.

### Asetukset (moodin `SETTINGS`)

| Avain | Oletus | Merkitys |
| --- | --- | --- |
| `end_difficulty` | `1` | Viimeksi valittu vaikeustaso. |
| `end_minutes` | `15` | Kello minuutteina (molemmille). |
| `end_suggest` | `False` | *Suggest next move*. |

## Datan tarkistus

`tools/check_endgames.py` ajetaan aina, kun asemia lisätään tai muutetaan (ei osa tavallista testiajoa, koska se on hidas):

1. jokainen FEN on laillinen, ja `Goal` pitää paikkansa: Stockfish (pitkä miettimisaika, Syzygy jos saatavilla) arvioi alkuaseman voitoksi / tasapeliksi
2. jokainen pääjatkon käyttäjän siirto säilyttää tavoitteen, ja `?`-merkityt yritykset todella menettävät sen
3. tulostaa yhteenvedon: asemat tasoittain, puuttuvat lähdetiedot, epäilyttävät arviot

## Testit

- `test_endgames.py`: kaikki `assets/endgames/*.pgn` latautuvat; `Key` yksilöllinen; `Difficulty` 1–5; `Goal` kelvollinen; FEN laillinen ja peli ei ole jo päättynyt; ratkaisun siirrot laillisia; jokaisella tasolla vähintään 15 asemaa. `EndgameDeck`: sama asema ei toistu ennen kuin taso on käyty läpi, eikä juuri pelattu tule heti uudelleenkierron alussa.
- `test_endgame_game.py`: ratkaisupuun siirto → ok; `?`-yritys → punainen; ratkaisu loppuun → vihreä; matti (`win`) → vihreä; patti `win`-tavoitteessa → punainen; ajan loppuminen → punainen; arvioijan tulos kääntää valon; vanhentunut arvio hylätään; Take Back palauttaa valon; punainen pysyy punaisena; ei arvioijaa → harmaa ratkaisupuun ulkopuolella; `tree_reply` palauttaa tallennetun puolustuksen puun sisällä ja `None` puun ulkopuolella. Kello väärennetyllä aikalähteellä kuten `test_computer_game.py`.
- `test_engines.py`: `analyse()` palauttaa mattiarvion mattiasemassa (`fake_uci.py`:hin `info score` -rivit).
- `test_modes.py`: uusi moodi rekisterissä, asetukset eivät törmää; `EndgameMode.start` `fake_context()`:lla; `VsComputerMode`:n testit ajetaan sellaisenaan `TimedGameMode`-refaktoroinnin jälkeen.

## Toteutusjärjestys

Jokainen vaihe on käyttökelpoinen yksinään, ja testit menevät läpi jokaisen vaiheen jälkeen.

1. **Refaktorointi:** `TimedGameMode` erotetaan `VsComputerMode`:sta; `Mode.subtitle()` ja alaotsikkorivi. Käytös ei muutu.
2. **Arvioinnin pohja:** `Engine.analyse`, UCI:n `score`-jäsennys, `EngineWorker`:n analyysipyyntö, testit.
3. **Kokoelma:** `app/endgames.py`, ensimmäiset ~25 asemaa (5 per taso), `tools/check_endgames.py`, `test_endgames.py`.
4. **Moodi:** `EndgameGame`, `EndgameMode`, dialogi, valo, Suggest, Take Back, tekstit ja asetukset, testit.
5. **Loput asemat** (~100), tarkistettuina työkalulla, erissä taso kerrallaan.
6. **Dokumentit:** ARCHITECTURE.md ja EXTENDING.md; tämä tiedosto `docs/plans/`-kansioon historialliseksi.

## Myöhemmin

- Tilastot asemittain (ratkaistu / ei, peruutukset) ja epäonnistuneiden asemien kertaus; arvonnan muisti ajojen yli asetuksiin.
- Tietyn aseman valinta listasta (kuten avausdialogin puu).
- Valinta heikommalle vastustajalle (ELO-taso) aloittelijoille, jos täysi voima osoittautuu liian vaikeaksi alimmilla tasoilla.
- Syzygy-taulukoiden lataus ohjeineen README:hen.

## Avoimet kysymykset

Ratkaistaan ennen vaihetta 4. Suluissa suunnitelman oletus.

1. **Nimi:** *Endgame Samples…* vai esim. *Endgame Practice…*? Käyttäjä: Endgame Practice.
2. **Muut tasapelit:** päättyykö peli myös kolmesti toistuvaan asemaan, 50 siirron sääntöön ja riittämättömään materiaaliin, vai vain mattiin, aikaan ja pattiin? Tasapelitutkielmissa (esim. Réti) peli päättyy luontevasti juuri riittämättömään materiaaliin. (Kaikki sääntöjen mukaiset tasapelit päättävät pelin.)
3. **Vihjeet ja valo:** saako vihreän valon, jos on käyttänyt *Suggest next move* -vihjettä tai Take Backia? (Saa; käyttö näkyy vain laskureina.)
4. **Kello ja Take Back:** palautetaanko kellon aika peruutuksessa? Käyttäjä: Ei
5. **Success-kentän paikka:** oikean paneelin yläosa vai laudan yläpuolella oikealla, materiaalitilanteen paikalla? (Oikea paneeli.) Käyttäjä: Laudan yläpuolella oikealla.
6. **Koneen puolustus:** ELO-valinta on poistettu. Kone pelaa tallennetun puolustuksen ja sen jälkeen täydellä teholla. Onko täysi voima liian vaikea perusmateissa ja alimmilla tasoilla? (Ei: näissä asemissa täydellinen puolustus on se, mitä harjoitellaan; heikompi vastustaja *Myöhemmin*-listalla.)
