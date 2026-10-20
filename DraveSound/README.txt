DraveSound v0.33  —  een Dravenlock product
==========================================

Een lichte, portable muziekmaker: zet loops op meerdere sporen, op maten/beats,
en exporteer je mix naar WAV of MP3. Huisstijl gelijk aan DraveMotion.

STARTEN (Windows)
-----------------
  Dubbelklik run.bat. De eerste keer zet hij zelf een .venv op en installeert
  PyQt5, numpy, soundfile en imageio-ffmpeg. Daarna start de app.

MAP-INHOUD
----------
  dravesound.py      <- het programma zelf
  run.bat            <- starten (zet de eerste keer alles op)
  herstel.bat        <- .venv weggooien en opnieuw laten opzetten
  requirements.txt   <- benodigde pakketten
  dravesound.spec    <- bouwconfig voor een zelfstandige .exe (onefile)
  bouw-exe.bat       <- maakt in een klik dist\DraveSound.exe
  logo.ico/.png      <- (optioneel) je eigen app-icoon/intrologo

ZO WERKT HET
------------
  1. 'Map met loops laden...' en kies een map met WAV/MP3/OGG/FLAC (soundpool).
  2. Klik een loop aan om 'm eerst te beluisteren (voorbeeld-balk verschijnt).
     Dubbelklik of SLEEP een loop -- of een hele map (soundpool) -- naar een spoor.
  3. Versleep clips om ze te schuiven; met 'Raster (magnetisch)' klikken ze op
     de tel. Zet het raster uit voor vrij plaatsen.
  4. Stel het tempo (BPM) in: de loops worden mee versneld/vertraagd
     (toonhoogte blijft gelijk), zodat alles op jouw tempo loopt.
  5. Sleep de rechterrand van een clip om 'm uit te rekken: de loop
     herhaalt zich dan over meer maten. (Of vul rechts 'Lengte' in.)
  6. Knippen/Kopieren/Plakken met de knoppen of Ctrl+X / Ctrl+C / Ctrl+V,
     Verwijderen met Delete. Plakken zet de clip op de afspeelkop.
  7. Je kunt ook loops/mappen vanuit Windows Verkenner op een spoor slepen.
  8. Per spoor (links in de spoorkolom): M = mute, S = solo, en een
     volumebalk. Of kies een spoor en regel rechts volume/mute/solo + effect
     (Echo, Galm, Dof, Helder).
  9. Bovenaan zie je de maten en eronder de tijd in seconden; onderaan loopt
     de tijd mee (positie / totale lengte).
 10. RECHTERKLIK op een clip: Kopieren / Knippen / Verwijderen / Effect,
     of RECHTERKLIK ergens (ook op een ander spoor) -> 'Plak hier'.
 11. Effecten: klik rechts op 'Effecten...' (of rechterklik op een clip ->
     Effect). In het venster kies je het effect en regel je de sterkte,
     met Beluister/Stop. Klik Toepassen om het op de clip te zetten, of
     Annuleren om het terug te draaien.
     Effecten: Echo, Galm, Dof, Helder, Overdrive, Tremolo, Bitcrusher,
     Chorus, Toon (donker<->helder), Flanger, Ping-pong echo,
     Pan (links<->rechts), Gater, Compressor, Phaser en
     Toonhoogte (lager<->hoger, lengte blijft gelijk).
 12. Rechterklik op een clip: ook 'Dupliceren' (of Ctrl+D) - kopie net
     erachter op hetzelfde spoor.
 13. Rechterklik op de mixer (links in de tijdlijn): spoor hernoemen of
     verwijderen.
 14. Master-volume: schuif links onder het raster regelt het totale niveau.
 15. Metronoom: vink 'Metronoom' aan voor een tik op elke tel (accent op
     tel 1). Hoor je alleen bij afspelen; komt niet in de export.
 16. Lus: zet de afspeelkop, klik 'Lus begin'; verzet de afspeelkop, klik
     'Lus eind'; vink 'Lus' aan -> dat stuk wordt herhaald afgespeeld.
     Of: met 'Lus' aan kun je het blauwe gebied direct op de liniaal
     slepen (nieuw gebied tekenen, of de randen verschuiven).
 17. Meerdere clips selecteren: trek een kader om ze heen op een lege plek,
     of houd Ctrl ingedrukt en klik clips aan/uit. Daarna Kopieren/Knippen/
     Plakken/Verwijderen (knoppen, rechterklik of Ctrl+C/X/V, Delete) werkt
     op de hele groep; bij plakken blijft de onderlinge plaatsing behouden.
 18. Blokjes (eigen combinaties): selecteer een groep clips en klik
     'Selectie -> blokje' om de combinatie te bewaren (met naam). Het
     blokje blijft bewaard tussen sessies. Dubbelklik een blokje om het
     op de afspeelkop te plaatsen; rechterklik voor plaatsen/hernoemen/
     verwijderen.
 19. Niveaumeter (links onder Master-volume): groen/geel/rood toont het
     uitgangsniveau tijdens afspelen; loopt het rood, zet dan het master-
     volume wat lager.
 20. Recent: knop 'Recent...' in Project toont je laatst geopende/opgeslagen
     projecten; klik er een om direct te openen.
 21. Exporteren: kies een bestandsnaam en formaat (WAV/MP3) en eventueel
     een map; tijdens het mixen/converteren zie je een voortgangsbalk.

TAAL
----
  DraveSound neemt automatisch de taal van je computer over (Nederlands als
  basis). In Instellingen kun je kiezen: Automatisch / Nederlands / English.

EEN ZELFSTANDIGE .EXE MAKEN (alles erin, geen losse bestanden)
--------------------------------------------------------------
  Zet (optioneel) je logo.ico in deze map en dubbelklik bouw-exe.bat.
  Resultaat: een enkel bestand dist\DraveSound.exe, met ffmpeg ingebouwd.
  De app maakt config/projecten/cache zelf aan naast de .exe.

Veel plezier ermee.  — gemaakt voor Dravenlock

EIGEN LOGO: zet een 'logo.png' (of 'logo.ico') in deze map naast
dravesound.py. De app toont dat logo dan in de kop, het introscherm
en als programma-/taakbalkpictogram. Zonder logo-bestand tekent de app
zelf een muzieknoot-symbool.
