# CHANGELOG - Gestione Abbonamenti

## Version 0.2.0 - 2025-01-13

### Nuove Funzionalità e Modifiche

## 🗄️ Database Changes

### Nuove Colonne
- Aggiunto `address_encrypted BLOB` alla tabella `subscriptions`
- Aggiunto `mobile_encrypted BLOB` alla tabella `subscriptions`
- Entrambi i campi sono crittografati con Fernet

### Nuovi Indici
- Aggiunto indice su `address_encrypted` per ricerche
- Aggiunto indice su `mobile_encrypted` per ricerche

## 📋 Data Model Changes

### Classe Subscription
- Aggiunto campo `address: str` - Indirizzo proprietario (opzionale)
- Aggiunto campo `mobile: str` - Numero cellulare (opzionale)
- Aggiunto campo `email: str` - Email (ora opzionale, non obbligatorio)

## 🔐 Security Changes

### Encryption
- Crittografia estesa ai nuovi campi:
  - `address_encrypted`: Indirizzo crittografato
  - `mobile_encrypted`: Cellulare crittografato

### Data Integrity
- Aggiornato calcolo HMAC per includere i nuovi campi
- Tutti i record hanno firme HMAC-SHA256 complete

## 💰 Payment Methods

### Cambi
- Rimossi vecchi metodi di pagamento:
  - ~~Carta di Credito~~
  - ~~Carta di Debito~~
  - ~~Contanti~~
  - ~~Bonifico~~
  - ~~Altro~~
- Nuovi metodi di pagamento:
  - **POS** - Pagamento elettronico
  - **Bollettino** - Pagamento tramite bollettino

## 🎨 GUI Changes

### Add/Edit Subscription Dialog
#### Nuovi Campi
- Campo **Indirizzo** (opzionale):
  - QLineEdit con placeholder "Via, numero, citt..."
  - Valido se vuoto
  - Crittografato nel database
- Campo **Cellulare** (opzionale):
  - QLineEdit con placeholder "123 456 7890"
  - Valido se vuoto
  - Crittografato nel database

#### Validazione Email Modificata
- **Prima**: Email era obbligatoria
- **Ora**: Email è opzionale
- Controllo formato (`@`) solo se campo non vuoto
- Messaggio di errore aggiornato: "Inserisci un'email valida"

#### Data Fine Predefinita
- **Prima**: Data fine = oggi + 365 giorni
- **Ora**: Data fine = 31 dicembre dell'anno corrente
- Implementato con: `datetime(datetime.now().year, 12, 31)`

#### Motivo Modifica (Aggiornamento)
- Campo "Motivo della modifica *":
  - **Nuovo abbonamento**: Testo predefinito "Inserimento nuovo abbonamento"
  - **Modifica abbonamento**: Placeholder "Inserisci il motivo della modifica (min. 10 caratteri)"
- Validazione: Minimo 10 caratteri richiesto
- Il valore viene salvato nel log audit

### Table Model
#### Nuove Colonne (10 totali)
1. **ID Protocollo** - Identificativo univoco
2. **Nome Proprietario** - Nome del possessore
3. **Targa** - Targa veicolo
4. **Email** - Email (opzionale)
5. **Indirizzo** - Indirizzo (opzionale)
6. **Cellulare** - Numero cellulare (opzionale)
7. **Data Inizio** - Data inizio abbonamento
8. **Data Fine** - Data fine abbonamento
9. **Metodo Pagamento** - POS o Bollettino
10. **Stato** - Attivo, In scadenza, Scaduto

#### Stati
- **Attivo**: Abbonamento valido (verde)
- **In scadenza**: Scade entro 30 giorni (giallo)
- **Scaduto**: Già scaduto (rosso)

#### Ricerca (FIX)
- **Problema 1**: `QLineEdit.textChanged.connect()` non passava argomento `text`
- **Soluzione 1**: Usato `lambda text: self.on_search(text)` per passare testo
- **Problema 2**: `search_subscriptions()` non decriptava `address_encrypted` e `mobile_encrypted`
- **Soluzione 2**: Aggiunta decrittografia di address e mobile in `search_subscriptions()`
- Funzionalità: Filtraggio istantaneo per protocollo, nome, targa, email, indirizzo, cellulare

### Main Window

#### Modifica Edit Mode (CRASH FIX)
- **Problema**: `QAction.setText()` causava crash
- **Soluzione 1**: Sostituito `QAction` con `QPushButton`
- **Soluzione 2**: Usato `toggled.connect()` invece di `clicked.connect()`
- Funzionalità preservata:
  - Toggle tra "ON" e "OFF"
  - Solo cambio testo (nessun cambio stile come richiesto)
  - Abilitazione/disabilitazione pulsanti

#### CSV Export Aggiornato
- Aggiunte colonne "Indirizzo" e "Cellulare"
- Esporta valori vuoti come stringa vuota ""
- Ordine colonne aggiornato per corrispondere alla tabella

#### Status Bar
- Aggiornata lingua in italiano:
  - "✓ Attivi: {active} | ⚠ In scadenza: {expiring} | ✗ Scaduti: {expired} | Totale: {total}"

### Menu
- File → Esporta CSV (esporta tutti i campi)
- File → Esci
- Modifica → Nuovo Abbonamento
- Modifica → Modifica Abbonamento
- Modifica → Elimina Abbonamento
- Strumenti → Backup Database
- Strumenti → Visualizza Log Audit
- Aiuto → Informazioni

### Toolbar
- **Indicatore integrità**: ✓ verde o ✗ rosso
- **Ricerca**: Campo testo per filtrare abbonamenti
- **Edit Mode Toggle**: Pulsante per abilitare/disabilitare modifiche
- **Pulsanti Azione** (disabilitati in modalità sola lettura):
  - ➕ Aggiungi
  - ✏️ Modifica
  - 🗑️ Elimina

## 🔒 Audit Log

### Funzionalità
- Tutte le operazioni registrate con:
  - Tipo operazione (INSERT, UPDATE, DELETE)
  - ID protocollo
  - Data/ora timestamp
  - Utente (nome Windows)
  - Computer name
  - Indirizzo IP
  - Motivo (richiesto, min 10 caratteri)
  - Dati PRIMA (JSON completo)
  - Data DOPO (JSON completo)

### Visualizzatore Log Audit
- Tabella con colonne:
  - Timestamp
  - Operazione
  - ID Protocollo
  - Utente
  - Motivo
  - Dettagli
- Filtri:
  - Tipo operazione (Tutti, INSERT, UPDATE, DELETE)
  - Ricerca testo
  - Opzione esporta CSV
- Sola lettura (nessuna modifica permessa)

## 🔍 Funzionalità di Ricerca

### Campi Ricercabili
- ID Protocollo
- Nome Proprietario
- Targa
- Email (crittografato, decrittato per ricerca)
- Indirizzo (crittografato, decrittato per ricerca)
- Cellulare (crittografato, decrittato per ricerca)

## ✅ Validazione

### Campi Obbligatori
- Nome proprietario
- Targa
- Data inizio
- Data fine
- Metodo di pagamento
- Motivo modifica (min 10 caratteri)

### Campi Opzionali
- Email (validato solo se fornito)
- Indirizzo
- Cellulare

### Controlli
- La data fine deve essere successiva alla data inizio
- Il motivo deve contenere almeno 10 caratteri
- Email valida solo se non vuota (deve contenere "@")

## 🎯 UX Improvements

### Feedback Visivo
- Messaggi di errore chiari e in italiano
- Placeholder informativi nei campi opzionali
- Colori di stato intuitivi (verde/giallo/rosso)
- Indicatore visivo di integrità dati

### Accesso Facilitato
- Modalità sola lettura predefinita (sicuro per utenti non tecnici)
- Toggle per edit mode chiaro e visibile
- Pulsanti disabilitati quando in modalità sola lettura

## 🔧 Technical Changes

### File Modificati
1. `abbonamenti/database/schema.py`:
   - Aggiunte colonne SQL
   - Aggiunti campi dataclass
   - Aggiornati indici

2. `abbonamenti/database/manager.py`:
   - Aggiornati metodi: `add_subscription()`, `update_subscription()`, `get_subscription()`, `get_all_subscriptions()`, `search_subscriptions()`
   - Aggiornato `_update_integrity_signature()` per nuovi campi
   - Aggiornato `verify_data_integrity()` per nuovi campi
   - Crittografia estesa a address e mobile

3. `abbonamenti/gui/dialogs/add_edit_dialog.py`:
   - Nuovi campi indirizzo e cellulare
   - Cambiato metodi pagamento a POS e Bollettino
   - Rimossa validazione obbligatoria email
   - Cambiato data fine predefinita a 31/12 anno corrente
   - Aggiornato metodo `get_data()` per includere nuovi campi

4. `abbonamenti/gui/models.py`:
   - Cambiati header in italiano
   - Aggiunte colonne indirizzo e cellulare (total 10 colonne)
   - Aggiornato metodo `data()` per nuovi campi
   - Cambiato metodo `_get_status()` con stati in italiano

5. `abbonamenti/gui/main_window.py`:
   - Sostituito `QAction` con `QPushButton` per edit mode (CRASH FIX)
   - Aggiornati metodi `add_subscription()`, `edit_subscription()` per includere address e mobile
   - Aggiornato metodo `export_data()` con nuove colonne
   - Aggiornato metodo `update_status_bar()` con testo in italiano

6. `abbonamenti/security/crypto.py`:
   - Gestione crittografia estesa a nuovi campi

7. `abbonamenti/security/hmac.py`:
   - Calcolo HMAC aggiornato per includere tutti i campi

### Database Migration
- Strategia: Drop and recreate
- Database vecchio cancellato automaticamente
- Schema nuovo con tutte le colonne
- Dati perduti: SI (come richiesto)
- Chiavi crittografia regenerate automaticamente

## 📊 Performance

### Ottimizzazioni
- Indici su campi crittografati per ricerche veloci
- Calcolo HMAC ottimizzato con codifica base64
- Decrittografia on-demand per campi opzionali

## 🧪 Testing

### Test Eseguiti
✅ Avvio applicazione senza crash
✅ Inizializzazione database
✅ Verifica integrità dati
✅ Aggiunta abbonamento con tutti i campi
✅ Recupero abbonamento con decrittografia
✅ Ricerca su tutti i campi
✅ Esportazione CSV con tutti i campi
✅ Toggle modalità modifica (senza crash)
✅ Log audit funzionante

### Fix Critici Risolti
1. ✅ CRASH FIX: Edit mode toggle - Sostituito QAction con QPushButton
2. ✅ CRASH FIX: Data fine predefinita - Uso diretto di QDate(year, month, day)
3. ✅ Validazione email - Ora opzionale come richiesto

## 🚀 Deploy Notes

### Windows
- Applicazione testata su Linux
- Pronta per deployment su Windows
- Nessuna dipendenza da Linux
- PyQt6 funziona cross-platform

### Database Location
- Path: `%APPDATA%/AbbonamentiScalea/`
  - Windows: `C:\Users\<username>\AppData\Roaming\AbbonamentiScalea\`
  - Linux: `~/.abbonamenti_scalea/`
- File:
  - `database.db` - Database SQLite
  - `keys/` - Directory chiavi crittografia
    - `fernet_key.bin` - Chiave crittografia dati
    - `hmac_key.bin` - Chiave HMAC
    - `private_key.pem` - Chiave privata RSA
    - `public_key.pem` - Chiave pubblica RSA

## 📝 Notes

- Tutti i campi crittografati vengono decrittati solo quando necessario (visualizzazione, ricerca)
- Le firme HMAC vengono generate dai dati codificati (base64) per consistenza
- Il log audit è immutabile (nessuna operazione di delete/update)
- I metodi di pagamento sono configurati nella GUI, non nel database (flessibilità)
