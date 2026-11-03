# Shakkilauta – analyysisovelluksen suunnitelma

> **Historiallinen asiakirja.** Tämä suunnitelma on toteutettu, eikä sitä enää päivitetä. Ohjelman nykyinen rakenne on kuvattu tiedostoissa [ARCHITECTURE.md](../ARCHITECTURE.md) ja [EXTENDING.md](../EXTENDING.md).

2.11.2026

> Tämä on alkuperäinen suunnitelma. Toteutuksen nykyinen rakenne, poikkeamat suunnitelmasta ja ohje pelikoneen lisäämiseen ovat tiedostossa [docs/ARCHITECTURE.md](../ARCHITECTURE.md), käyttöohje tiedostossa [README.md](../../README.md).

## Tavoite ja rajaus

Rakennetaan offline-toimiva, Pythonilla kirjoitettu shakkilauta pelien analysointiin: vain lailliset siirrot, vapaa liikkuminen siirtohistoriassa ja tallennus standardiformaatteihin. Ulkoasu ja tuntuma mukailevat Chess.comia, mutta grafiikka ja äänet ovat omia, koska Chess.comin materiaali on tekijänoikeuden suojaamaa.

**Mukana:**

- Laillisten siirtojen pakotus (myös linnoitus, ohestalyönti, korotus, matti, patti, toistot ja 50 siirron sääntö)
- Molempien osapuolten siirrot käyttäjä tekee itse
- Laudan kääntö: valkoinen tai musta alhaalla
- Siirtohistoria, peruutus ja eteneminen, sivumuunnelmat
- Pelien (PGN) ja asemien (FEN) tallennus ja avaus
- Oman aseman asettaminen FEN-merkinnällä
- Chess.com-tyyliset äänet

**Ei mukana:** shakkimoottori, siirtojen arviointi, verkkoyhteys, exe-paketti.

**Kieli:** Käyttöliittymä on kokonaan englanninkielinen: valikot, painikkeet, tilarivi, dialogit ja virheilmoitukset. Myös tallennettavien tiedostojen sanallinen teksti on englanniksi (PGN-otsikot, ohjelman lisäämät tekstit, settings.json-avaimet, error.log). Kaikki näkyvät tekstit kootaan yhteen moduuliin `app/strings.py`, jolloin niitä on helppo muokata.

## Teknologiavalinnat

Perusajatus: mahdollisimman vähän uusia riippuvuuksia. Lähes kaikki tulee Pythonin standardikirjastosta tai jo asennetuista paketeista; ainoa lisäys on puhdas Python-kirjasto python-chess.

| Osa-alue | Valinta | Peruste |
| --- | --- | --- |
| Käyttöliittymä | tkinter (standardikirjasto) | Tulee Pythonin mukana, ei asennusta eikä uusia binäärejä. Canvas riittää laudan piirtoon ja vetämiseen. |
| Shakkisäännöt | python-chess (`pip install chess`) | Testattu laillisten siirtojen generointi, PGN- ja FEN-tuki, muunnelmapuu. Puhdasta Pythonia, toimii 3.15:llä. |
| Kuvat | Pillow 12.3 (asennettu) | Nappulakuvien skaalaus ruudun kokoon ja läpinäkyvyys. |
| SVG-nappuloiden renderöinti | PyMuPDF 1.28 (asennettu) | Avaa SVG-tiedostot ja renderöi ne PNG:ksi ilman lisäkirjastoja. |
| Äänet | winsound (standardikirjasto) | Toistaa WAV-tiedostot asynkronisesti (`SND_ASYNC`), ei riippuvuuksia. |
| Asetukset | json (standardikirjasto) | Luettava asetustiedosto. |
| Testit | pytest 9.2 (asennettu) | Sääntö- ja tiedostologiikan yksikkötestit. |

Ennen aloitusta tarkistetaan, että Python-asennuksessa on Tcl/Tk mukana: `python -m tkinter` avaa pienen testi-ikkunan. Jos ei avaa, Python-asennus muokataan ja Tcl/Tk valitaan mukaan.

Vaihtoehdot, joita ei valita: PySide6/PyQt (iso binääripaketti, wheelit eivät välttämättä vielä ole 3.15:lle, F-Secure-riski) ja pygame (turha riippuvuus). Oma siirtogeneraattori olisi mahdollinen, mutta virhealtis ja hidas tehdä.

## F-Secure-yhteensopivuus

Sovellus ajetaan aina python.org:n allekirjoitetulla `pythonw.exe`:llä, eikä levylle synny yhtään uutta exe-tiedostoa. Silloin F-Securen DeepGuard näkee vain tutun, allekirjoitetun ohjelman, joka lukee tekstitiedostoja.

**Tärkein yksityiskohta: ei venviä.** Windowsin venv kopioi `Scripts`-kansioon oman `python.exe`- ja `pythonw.exe`-käynnistimen. Ne ovat F-Securen silmissä uusia, harvinaisia exe-tiedostoja, eli juuri sitä mitä halutaan välttää. Siksi python-chess asennetaan sovelluskansion alikansioon:

```
python -m pip install --target vendor chess
```

Ohjelma lisää `vendor`-kansion `sys.path`-polkuun käynnistyessään. python-chessissä ei ole komentorivityökaluja, joten tämä ei luo exe-tiedostoja.

**Muut säännöt:**

- Ei PyInstalleria tai muuta exe-paketointia (koneella olevat altgraph ja pefile ovat PyInstallerin jäänteitä; niitä ei käytetä).
- Ei verkkoliikennettä, ei rekisterimuokkauksia, ei taustaprosesseja, ei `subprocess`-kutsuja. Ohjelma kirjoittaa vain omaan kansioonsa ja käyttäjän valitsemiin tallennustiedostoihin.
- Ääni- ja kuvatiedostot luodaan tai kopioidaan paikallisesti. Jos jokin tiedosto ladataan netistä (esim. zip), sen "Mark of the Web" -merkintä poistetaan: tiedoston ominaisuudet → Unblock, tai PowerShellissä `Unblock-File`.
- Käynnistys .bat-tiedostolla on pelkkää tekstiä ja kutsuu valmiiksi asennettua Pythonia.
- Jos F-Secure silti huomauttaa, sovelluskansio voidaan lisätä F-Securen poikkeuksiin, mutta tavoite on, ettei sitä tarvita.

## Toiminnot ja käyttöliittymä

Ikkuna jakautuu Chess.comin tapaan kahteen osaan: lauta vasemmalla, siirtolista ja ohjaimet oikealla. Lauta skaalautuu ikkunan koon mukaan.

**Lauta**

- Siirto vetämällä tai kahdella klikkauksella (lähtö- ja kohderuutu)
- Valitun nappulan lailliset kohteet: piste tyhjään ruutuun, rengas lyötävän nappulan ympärille
- Viimeisin siirto korostetaan kellertävällä, shakissa oleva kuningas punaisella
- Laiton siirto: nappula palaa paikalleen ja kuuluu "laiton"-ääni
- Korotus: pieni valikko (Q, R, B, N) kohderuudun päälle
- Koordinaatit (a–h, 1–8) ruutujen reunoilla, kääntyvät laudan mukana
- Analyysimerkinnät: oikealla napilla ruudun korostus, oikealla vedolla nuoli; vasen klikkaus tyhjentää
- Laudan yllä ja alla pelaajien nimet ja lyödyt nappulat sekä materiaaliero (+2 jne.)

**Oikea paneeli**

- Siirtolista pareittain (1. e4 e5 2. Nf3 …), nykyinen siirto korostettu, klikkaus hyppää siirtoon
- Sivumuunnelmat sisennettyinä suluissa; oikean napin valikko: Promote to Main Line, Delete Variation, Delete from Here
- Navigointi: |◀ ◀ ▶ ▶| sekä Flip Board -painike
- Kommenttikenttä valitulle siirrolle (tallentuu PGN:ään)
- Tilarivi: White to move / Black to move, Check, Checkmate, Stalemate, Draw (threefold repetition, 50-move rule, insufficient material)
- FEN-rivi kopioitavaksi

**Peruutus ja muunnelmat:** Kun käyttäjä palaa taaksepäin ja tekee eri siirron, syntyy oletuksena uusi sivumuunnelma, eikä mitään menetetä. Jos sama siirto on jo olemassa, siihen vain siirrytään. Ctrl+Z poistaa viimeisimmän siirron kokonaan.

**Valikot:** File (New Game, Open…, Save, Save As…, Copy PGN, Copy FEN, Paste PGN/FEN, Exit), View (Flip Board, Show Coordinates, Sound, Piece Set, Board Theme), Game (pelimuodot Board ja Play vs Computer… sekä aktiivisen moodin omat toiminnot), Help (Keyboard Shortcuts, About).

**Pikanäppäimet**

| Näppäin | Toiminto |
| --- | --- |
| ← / → | Siirto taakse / eteen |
| Home / End | Alkuun / loppuun |
| ↑ / ↓ | Muunnelmien välillä |
| F | Käännä lauta |
| Ctrl+Z | Poista viimeisin siirto |
| Ctrl+N / Ctrl+O / Ctrl+S | Uusi / Avaa / Tallenna |
| Ctrl+C / Ctrl+V | Kopioi / liitä PGN tai FEN |

## Tiedostoformaatit

Pelit tallennetaan PGN-muotoon ja yksittäiset asemat FEN-muotoon. Molemmat ovat kansainvälisiä tekstistandardeja, jotka avautuvat Notepadissa sekä Chess.comissa, Lichessissä ja ChessBasessa.

| Tallennettava | Formaatti | Pääte | Sisältö |
| --- | --- | --- | --- |
| Peli | PGN (Portable Game Notation) | .pgn | Otsikkotiedot, siirrot, muunnelmat, kommentit |
| Pelitilanne | FEN (Forsyth–Edwards Notation) | .fen | Yksi rivi: asema, vuoro, linnoitus, ohestalyönti, siirtolaskurit |
| Peli omasta asemasta | PGN + `[SetUp "1"]` ja `[FEN "…"]` | .pgn | Sama kuin peli, alkuasema mukana |

Esimerkki PGN-tiedostosta:

```
[Event "Analysis"]
[Site "?"]
[Date "2026.11.02"]
[Round "?"]
[White "White"]
[Black "Black"]
[Result "*"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 (3. Bc4 Bc5) 3... a6 {Morphy Defence} *
```

Tiedostot tallennetaan UTF-8-koodauksella. Avattaessa monipelisestä PGN:stä näytetään lista, josta peli valitaan. Siirrot näytetään ja tallennetaan standardin englanninkielisellä algebrallisella notaatiolla (K, Q, R, B, N). Ohjelman kirjoittamat tekstit ovat englanniksi: otsikkokenttien oletusarvot (Event "Analysis", White "White", Black "Black", tuntematon tieto "?") ja tallennusdialogien tiedostotyypit (PGN Game, FEN Position). Käyttäjän itse kirjoittamat kommentit ja nimet tallennetaan sellaisinaan.

## Äänet ja nappulagrafiikka

Chess.comin ääniä ja nappuloita ei voi kopioida, joten tehdään omat, samantyyliset. Äänet syntetisoidaan Pythonilla, jolloin ne eivät vaadi latauksia eikä lisenssejä.

**Äänet:** `tools/make_sounds.py` luo WAV-tiedostot standardikirjaston `wave`- ja `math`-moduuleilla: lyhyt, vaimeneva puinen "napsahdus" (kohinapurske + matala resonanssi), jota varioidaan tapahtuman mukaan.

| Tapahtuma | Ääni |
| --- | --- |
| Siirto | Lyhyt puinen napsahdus |
| Lyönti | Terävämpi, kovempi napsahdus |
| Linnoitus | Kaksi nopeaa napsahdusta |
| Shakki | Napsahdus + korkea äänimerkki |
| Korotus | Nouseva kaksisävel |
| Pelin loppu (matti, patti, tasapeli) | Pehmeä soinnillinen merkki |
| Laiton siirto | Matala, lyhyt "tömähdys" |

Ääni soitetaan `winsound.PlaySound(…, SND_FILENAME | SND_ASYNC)`, joten käyttöliittymä ei pysähdy. Siirtohistoriassa liikuttaessa soitetaan kyseisen siirron ääni, kuten Chess.comissa. Äänet voi kytkeä pois.

**Nappulat:** kaksi vaihtoehtoa, molemmat offline.

1. **Oletus: Cburnett-setti** (Wikimedia Commonsin SVG-nappulat, joita myös Lichess käyttää; lisenssi sallii käytön, tekijä mainitaan About-ikkunassa). 12 SVG-tiedostoa haetaan kerran ja tallennetaan `assets/pieces/`-kansioon. PyMuPDF renderöi ne PNG:ksi ruudun koon mukaan, Pillow hoitaa välimuistin.
2. **Varasetti: Unicode-merkit** (♔♕♖♗♘♙) piirrettynä Pillowlla Windowsin Segoe UI Symbol -fontista, ääriviivalla. Toimii ilman yhtään ladattua tiedostoa.

**Lautavärit:** oletuksena Chess.comin kaltainen vihreä–kerma (#769656 / #EEEED2), lisäksi ruskea ja sininen teema.

## Arkkitehtuuri ja kansiorakenne

Sovellus jaetaan malliin (pelin tila ja säännöt) ja näkymään (tkinter). Malli ei tiedä käyttöliittymästä mitään, joten sen voi testata pytestillä ilman ikkunoita.

```
C:\Users\Omistaja\Shakkilauta\
├── Shakkilauta.bat          käynnistys
├── shakkilauta.pyw          pääohjelma (pythonw, ei konsoli-ikkunaa)
├── settings.json            asetukset (luodaan ensimmäisellä ajolla)
├── app\
│   ├── model.py             GameModel: python-chess-pelipuu, nykyinen solmu, siirrot, muunnelmat
│   ├── fileio.py            PGN/FEN luku ja kirjoitus
│   ├── board_view.py        laudan Canvas: piirto, veto, korostukset, nuolet, korotusvalikko
│   ├── movelist_view.py     siirtolista ja muunnelmat (Text-widget tageilla)
│   ├── main_window.py       ikkuna, valikot, pikanäppäimet, tilarivi
│   ├── dialogs.py           pelin valinta ja pelin tiedot -dialogit
│   ├── pieces.py            nappulakuvien renderöinti ja välimuisti
│   ├── sounds.py            äänten toisto
│   ├── settings.py          asetusten luku/tallennus
│   ├── strings.py           kaikki käyttäjälle näkyvät tekstit
│   └── theme.py             yhteiset värit ja lautateemat
├── assets\
│   ├── pieces\cburnett\     12 SVG-tiedostoa
│   └── sounds\              move.wav, capture.wav, castle.wav, check.wav, promote.wav, end.wav, illegal.wav
├── tools\
│   └── make_sounds.py       äänten generointi
├── vendor\                  python-chess (pip --target)
├── tests\                   pytest-testit
└── Games\                   tallennusten oletuskansio
```

**Tiedonkulku:** näkymä lähettää käyttäjän toiminnon (esim. siirto e2→e4) mallille. Malli tarkistaa laillisuuden, päivittää pelipuun ja palauttaa tapahtuman (siirto, lyönti, shakki…). Pääikkuna päivittää laudan ja siirtolistan sekä soittaa tapahtumaa vastaavan äänen. Näin säännöt ovat yhdessä paikassa ja käyttöliittymä pysyy ohuena.

## Asennus ja käynnistys

Asennus on kertaluonteinen ja vie muutaman minuutin; nettiyhteyttä tarvitaan vain python-chessin ja nappulasettien hakuun.

1. Luo kansio `C:\Users\Omistaja\Shakkilauta` ja kopioi sovelluksen tiedostot sinne.
2. Tarkista Tk: `python -m tkinter` (pieni ikkuna aukeaa).
3. Asenna python-chess sovelluskansioon (ei venviä, ks. F-Secure-osio):

   ```
   cd C:\Users\Omistaja\Shakkilauta
   python -m pip install --target vendor chess
   ```
4. Luo äänet: `python tools\make_sounds.py`
5. Käynnistä tuplaklikkaamalla `Shakkilauta.bat` (tai suoraan `shakkilauta.pyw`).

`Shakkilauta.bat`:

```
@echo off
cd /d "%~dp0"
start "" pythonw shakkilauta.pyw
```

`pythonw` käynnistää ohjelman ilman mustaa konsoli-ikkunaa. Työpöydälle voi tehdä pikakuvakkeen .bat-tiedostoon. Vianetsinnässä ohjelman voi ajaa komennolla `python shakkilauta.pyw`, jolloin virheilmoitukset näkyvät konsolissa; lisäksi virheet kirjoitetaan `error.log`-tiedostoon.

## Toteutusvaiheet ja testaus

Toteutus etenee seitsemässä vaiheessa niin, että jokaisen jälkeen on käyttökelpoinen ohjelma. Vaiheet 1–4 riittävät jo laudan korvikkeeksi.

1. **Pohja:** kansiorakenne, python-chess vendor-kansioon, Tk-tarkistus, tyhjä ikkuna .bat-käynnistyksellä. Testataan, ettei F-Secure reagoi.
2. **Lauta ja siirrot:** laudan piirto, nappulat, klikkaus- ja vetosiirrot, lailliset kohteet, korotusvalikko, laudan kääntö.
3. **Historia:** siirtolista, navigointi painikkeilla ja nuolinäppäimillä, peruutus, muunnelmien luonti ja hallinta.
4. **Tallennus:** PGN- ja FEN-tallennus ja -avaus, leikepöytä, pelin tiedot.
5. **Äänet:** äänten generointi ja toisto tapahtumien mukaan.
6. **Analyysityökalut:** nuolet ja ruutukorostukset, kommentit, lyödyt nappulat ja materiaaliero.
7. **Viimeistely:** asetukset (teema, nappulasetti, äänet), ikkunan koon muistaminen, virheloki, About-ikkuna.

**Testaus**

- pytest mallille: laillisten siirtojen määrät tunnetuista asemista (perft-tyyppiset tarkistukset), linnoitus, ohestalyönti, korotus, matti ja patti
- PGN-kierros: avaa → tallenna → avaa uudelleen, muunnelmat ja kommentit säilyvät
- FEN-kierros
- Käsin: kuuluisa peli (esim. Morphy–herttua ja kreivi, 1858) syötetään laudalla ja verrataan siirtolistaa tunnettuun PGN:ään
- F-Secure: koko asennus ja ensimmäinen käynnistys ajetaan puhtaaseen kansioon ja tarkistetaan F-Securen tapahtumaloki

**Avoimet kysymykset**

- Riittääkö yksi peli kerrallaan, vai tarvitaanko välilehdet useammalle pelille? => Riittää yksi peli kerrallaan.
