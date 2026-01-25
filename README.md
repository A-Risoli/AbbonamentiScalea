# AbbonamentiScalea

**Sistema di Gestione Abbonamenti per la Città di Scalea**

Sistema sicuro e affidabile per la gestione degli abbonamenti parcheggio del Comune di Scalea, con crittografia end-to-end, audit trail completo e interfaccia moderna.

## 📋 Caratteristiche

- ✅ **Gestione completa abbonamenti** - Inserimento, modifica, eliminazione con validazione
- 🔐 **Sicurezza enterprise** - Crittografia AES-256, firma digitale RSA, HMAC per integrità dati
- 🤖 **Bot Telegram integrato** - Verifica validità targhe da remoto per agenti di polizia
- 📊 **Statistiche avanzate** - Grafici interattivi per analisi incassi e pagamenti
- 📝 **Audit trail completo** - Tracciamento di ogni operazione con timestamp e motivazione
- 🎨 **Interfaccia moderna** - Design Windows 11-aware con supporto tema chiaro/scuro
- 💾 **Export CSV** - Esportazione dati per backup e analisi esterne
- 🔍 **Ricerca rapida** - Filtro in tempo reale per proprietario, targa, protocollo

## 🚀 Installazione

### Requisiti

- **Windows 10/11** (o Linux/macOS per sviluppo)
- **Python 3.13+**
- **uv** (gestore pacchetti veloce) - [Installazione](https://docs.astral.sh/uv/)

### Installazione Dipendenze

```bash
# Clona il repository
git clone https://github.com/your-username/AbbonamentiScalea.git
cd AbbonamentiScalea

# Installa dipendenze con uv
uv sync
```

## 🏃 Esecuzione

### Modalità Sviluppo

```bash
# Avvia l'applicazione desktop
uv run abbonamenti

# Avvia il bot Telegram standalone (opzionale)
uv run abbonamenti-bot
```

### Primo Avvio

Al primo avvio, l'applicazione creerà automaticamente:
- Database SQLite in `%APPDATA%\AbbonamentiScalea\database.db`
- Chiavi di crittografia in `%APPDATA%\AbbonamentiScalea\keys\`
- Cartella backup in `%APPDATA%\AbbonamentiScalea\backups\`

## 🤖 Bot Telegram

Il bot Telegram consente agli agenti di polizia di verificare la validità delle targhe direttamente da smartphone mentre sono in servizio.

### Configurazione Bot

1. **Crea un bot Telegram**:
   - Apri Telegram e cerca [@BotFather](https://t.me/BotFather)
   - Invia `/newbot` e segui le istruzioni
   - Salva il **token** fornito (es: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

2. **Ottieni gli User ID degli agenti autorizzati**:
   - Ogni agente deve cercare [@userinfobot](https://t.me/userinfobot) su Telegram
   - Il bot risponderà con l'User ID (es: `123456789`)
   - In alternativa, usa il comando `/myid` del bot dopo la configurazione

3. **Configura il bot nell'applicazione**:
   - Apri l'applicazione desktop
   - Menu: **Strumenti > 🤖 Impostazioni Bot**
   - Abilita il bot e inserisci:
     - **Token Bot**: Il token da @BotFather
     - **Soglia scadenza**: Giorni prima della scadenza per l'avviso (default: 7)
     - **User ID autorizzati**: Uno per riga (es: `123456789`)
   - Clicca **Testa Connessione** per verificare
   - Salva le impostazioni

4. **Utilizzo del bot**:
   - Cerca il tuo bot su Telegram (es: `@ScaleaParkingBot`)
   - Comandi disponibili:
     - `/myid` - Mostra il tuo User ID (tutti gli utenti)
     - `/check AB123CD` - Verifica validità targa (solo utenti autorizzati)

### Risposte del Bot

- ✅ **VALIDO! Scade: 31/12/2026** - Abbonamento attivo
- ⏰ **IN SCADENZA (entro 7 giorni)! Scade: 27/01/2026** - In scadenza
- ❌ **NON VALIDO o SCADUTO** - Nessun abbonamento trovato o scaduto

### Sicurezza Bot

- **Whitelist utenti**: Solo gli User ID configurati possono usare il bot
- **Rate limiting**: Massimo 20 richieste/minuto per utente
- **Token crittografato**: Il token viene salvato crittografato (AES-256)
- **Log delle query**: Tutte le ricerche sono registrate in `bot_queries.log`
- **Accesso concorrente**: Database in modalità WAL per letture simultanee GUI+bot

### Modalità Standalone

Il bot può essere eseguito indipendentemente dalla GUI:

```bash
# Avvia solo il bot (senza GUI)
uv run abbonamenti-bot
```

Utile per:
- Esecuzione come servizio Windows/systemd
- Deploy su server remoto
- Debug e testing

### Popolamento Database (Opzionale)

Per test e sviluppo, puoi popolare il database con dati di esempio:

```bash
uv run python seed_database.py
```

## 📦 Creazione Installer Windows

### Build con PyInstaller

#### Opzione 1: Script Automatico (Consigliato)

```bash
# Build standard (cartella distribuibile)
python build_installer.py

# Build singolo .exe (più lento all'avvio)
python build_installer.py --onefile

# Build con console per debug
python build_installer.py --debug
```

#### Opzione 2: PyInstaller Manuale

```bash
# Usando il file .spec (maggior controllo)
pyinstaller AbbonamentiScalea.spec

# Oppure comando diretto
pyinstaller --name=AbbonamentiScalea ^
  --onedir ^
  --windowed ^
  --hidden-import=matplotlib.backends.backend_qtagg ^
  --hidden-import=PyQt6.sip ^
  --collect-data=matplotlib ^
  abbonamenti/main.py
```

### Output

Dopo il build, troverai l'eseguibile in:
- **Modalità onedir**: `dist/AbbonamentiScalea/AbbonamentiScalea.exe`
- **Modalità onefile**: `dist/AbbonamentiScalea.exe`

### Distribuzione

Per distribuire l'applicazione:

1. **Build onedir** (consigliato): Distribuisci l'intera cartella `dist/AbbonamentiScalea`
2. **Build onefile**: Distribuisci solo `AbbonamentiScalea.exe`

### Creazione Installer Professionale

Per creare un installer Windows con wizard di installazione:

#### Opzione A: Inno Setup (Consigliato)

1. Scarica [Inno Setup](https://jrsoftware.org/isinfo.php)
2. Crea file `installer.iss`:

```iss
[Setup]
AppName=AbbonamentiScalea
AppVersion=0.1.2
DefaultDirName={autopf}\AbbonamentiScalea
DefaultGroupName=Comune di Scalea
OutputDir=installer_output
OutputBaseFilename=AbbonamentiScalea-Setup
Compression=lzma2
SolidCompression=yes

[Files]
Source: "dist\AbbonamentiScalea\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\AbbonamentiScalea"; Filename: "{app}\AbbonamentiScalea.exe"
Name: "{autodesktop}\AbbonamentiScalea"; Filename: "{app}\AbbonamentiScalea.exe"
```

3. Compila: `iscc installer.iss`

#### Opzione B: NSIS

1. Scarica [NSIS](https://nsis.sourceforge.io/)
2. Usa NSIS Wizard o crea script `.nsi` personalizzato

## 🧪 Testing

### Linting

```bash
# Controlla stile codice
ruff check .

# Auto-fix problemi
ruff check . --fix

# Formatta codice
ruff format .
```

### Test

```bash
# Esegui tutti i test
pytest

# Test con coverage
pytest --cov=abbonamenti

# Test specifico
pytest tests/test_database.py -v
```

### Verifica Build

Dopo aver creato l'eseguibile, verifica:

1. ✅ App si avvia senza errori
2. ✅ Database viene creato in `%APPDATA%\AbbonamentiScalea`
3. ✅ Chiavi vengono generate automaticamente
4. ✅ Inserimento/modifica/eliminazione abbonamenti funziona
5. ✅ Dialog statistiche mostra grafici matplotlib
6. ✅ Export CSV funziona
7. ✅ Verifica integrità dati OK
8. ✅ Nessun errore DLL mancanti

## 📁 Struttura Progetto

```
AbbonamentiScalea/
├── abbonamenti/           # Package principale
│   ├── database/          # Gestione database e schema
│   ├── gui/               # Interfaccia PyQt6
│   │   ├── dialogs/       # Dialog di add/edit/statistiche/audit
│   │   └── widgets/       # Widget riutilizzabili
│   ├── security/          # Crittografia e sicurezza
│   ├── utils/             # Utilità (paths, helpers)
│   └── validators/        # Validazione dati
├── build_installer.py     # Script build PyInstaller
├── AbbonamentiScalea.spec # Configurazione PyInstaller
├── seed_database.py       # Popolamento dati test
├── pyproject.toml         # Configurazione progetto
└── README.md              # Questo file
```

## 🔒 Sicurezza

- **Crittografia AES-256-GCM** per dati sensibili
- **Firma digitale RSA-2048** per autenticità
- **HMAC-SHA256** per verifica integrità
- **Chiavi auto-generate** al primo avvio
- **Audit trail** completo di ogni modifica
- **Validazione input** rigorosa

## 🎨 Temi

L'applicazione rileva automaticamente il tema di Windows 11 (chiaro/scuro) e adatta l'interfaccia di conseguenza:

- **Tema chiaro**: Palette Scalea 2026 con azzurro istituzionale
- **Tema scuro**: Tonalità adattate per leggibilità notturna

## 📝 Licenza

Questo progetto è sviluppato per il Comune di Scalea.

## 👨‍💻 Autore

**Risoli Antonio**  
Sistema Abbonamenti Città di Scalea  
Versione 0.1.2

## 🆘 Supporto

Per problemi o domande:
1. Verifica che tutte le dipendenze siano installate: `uv sync`
2. Controlla i log in `%APPDATA%\AbbonamentiScalea\`
3. Per debug, esegui con: `python build_installer.py --debug`

## 🚧 Roadmap

- [ ] Notifiche scadenza abbonamenti
- [ ] Multi-utente con autenticazione

---

**Sistema sicuro, affidabile, facile da usare.** 🏛️
