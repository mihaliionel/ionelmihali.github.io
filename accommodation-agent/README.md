# 🏨 Agent de Căutare Cazări

Un agent automat inteligent care caută cazări pe platforme ca Booking.com la prețurile pe care le specifici și îți trimite notificări prin email.

## ✨ Funcționalități

- 🔍 **Căutare automată** pe multiple platforme (Booking.com, cu posibilitatea de extensie)
- 💰 **Filtrare după preț** și alte criterii (rating, tip cazare, locație)
- 📧 **Notificări email** cu HTML frumos formatat
- 🗄️ **Baza de date SQLite** pentru tracking duplicatelor și istoricul prețurilor
- ⏰ **Scheduler automat** pentru căutări periodice
- 📊 **Alerte de preț** când prețurile scad
- 🛡️ **Evită spam-ul** - nu trimite aceleași cazări de mai multe ori
- 💾 **Backup automat** al bazei de date

## 📋 Cerințe

- Python 3.7+ (pentru dataclasses)
- Conexiune la internet
- Email pentru trimiterea notificărilor (Gmail recomandat)

## 🚀 Instalare Rapidă

1. **Clonează sau descarcă proiectul**:
```bash
git clone <repo-url>
cd accommodation-agent
```

2. **Instalează dependențele**:
```bash
pip install -r requirements.txt
```

3. **Creează configurația**:
```bash
python main.py --create-config
```

4. **Editează `config.json`** cu criteriile tale de căutare și configurația email

5. **Testează email-ul**:
```bash
python main.py --test-email
```

6. **Rulează o căutare de test**:
```bash
python main.py --run-once
```

7. **Pornește agentul automat**:
```bash
python main.py --daemon
```

## ⚙️ Configurare

### 1. Configurația Email (Gmail)

Pentru Gmail, trebuie să:
1. Activezi autentificarea cu 2 factori
2. Generezi o "App Password" specifică
3. Folosești parola aplicației în configurare

```json
{
  "email": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "email": "your-email@gmail.com",
    "password": "your-16-char-app-password",
    "recipient": "recipient@gmail.com"
  }
}
```

### 2. Criteriile de Căutare

```json
{
  "search_criteria": {
    "destination": "București, România",
    "check_in": "2024-03-15",
    "check_out": "2024-03-17",
    "guests": 2,
    "max_price": 500.0,
    "currency": "RON",
    "property_types": ["hotel", "apartment"],
    "min_rating": 7.0
  }
}
```

### 3. Variabile de Mediu (Opțional)

Pentru securitate sporită, poți folosi variabile de mediu:

```bash
# Windows
set SENDER_EMAIL=your-email@gmail.com
set EMAIL_PASSWORD=your-app-password
set RECIPIENT_EMAIL=recipient@gmail.com

# Linux/Mac
export SENDER_EMAIL="your-email@gmail.com"
export EMAIL_PASSWORD="your-app-password"
export RECIPIENT_EMAIL="recipient@gmail.com"
```

## 🎯 Utilizare

### Comenzi de bază:

```bash
# Creează fișierul de configurare exemplu
python main.py --create-config

# Testează configurația email
python main.py --test-email

# Rulează o singură căutare
python main.py --run-once

# Rulează ca daemon (automat în fundal)
python main.py --daemon

# Mod interactiv (cu comenzi)
python main.py
```

### Mod interactiv:

Când rulezi `python main.py`, intri în modul interactiv cu comenzi:

- `search` - Caută cazări acum
- `status` - Afișează statusul agentului
- `start` - Pornește scheduler-ul automat
- `stop` - Oprește scheduler-ul
- `test-email` - Testează email-ul
- `exit` - Ieși din program

## 📁 Structura Proiectului

```
accommodation-agent/
├── main.py                 # Fișierul principal
├── config.py              # Configurațiile agentului
├── scraper.py             # Modulul de scraping
├── filter.py              # Sistemul de filtrare
├── database.py            # Gestionarea bazei de date
├── email_notifier.py      # Sistemul de notificări
├── scheduler.py           # Scheduler-ul automat
├── requirements.txt       # Dependențele
├── README.md             # Această documentație
├── config.json           # Configurația ta (creat automat)
├── accommodation_agent.db # Baza de date (creată automat)
└── accommodation_agent.log # Log-urile (creat automat)
```

## 📧 Tipuri de Email-uri

### 1. Notificări cu cazări noi
- Primești când agentul găsește cazări noi care îndeplinesc criteriile
- Include detalii complete: preț, rating, locație, link

### 2. Alerte de preț
- Quando prețurile scad cu mai mult de 10%
- Te anunță despre economiile posibile

### 3. Email de test
- Pentru verificarea configurației
- Se trimite manual cu `--test-email`

## 🔧 Personalizare Avansată

### Adăugarea de noi platforme:

În `scraper.py`, poți adăuga noi scrapers:

```python
class AirbnbScraper(BaseScraper):
    def search_accommodations(self, criteria):
        # Implementează logica pentru Airbnb
        pass

# Adaugă în ScraperFactory
scrapers = {
    'booking': BookingScraper,
    'airbnb': AirbnbScraper,  # Nou!
}
```

### Filtre personalizate:

În `filter.py`:

```python
def luxury_filter(accommodation):
    return accommodation.rating >= 9.0 and 'luxury' in accommodation.title.lower()

# Folosire
luxury_accommodations = create_custom_filter(luxury_filter)(accommodations)
```

## 🛠️ Troubleshooting

### Email nu funcționează
- Verifică că ai activat autentificarea cu 2 factori
- Folosești "App Password", nu parola normală
- Serverul SMTP și portul sunt corecte

### Nu găsește cazări
- Verifică criteriile (poate sunt prea restrictive)
- Testează cu preț maxim mai mare
- Verifică destinația (folosește numele exact de pe Booking.com)

### Baza de date se umple
- Agentul face curățare automată după 30 de zile
- Poți șterge manual `accommodation_agent.db`

### Scraping nu funcționează
- Booking.com poate schimba structura HTML-ului
- Ar fi nevoie de actualizări ale selectorilor CSS

## 🎛️ Configurări Avansate

### Intervalele de rulare:

```json
{
  "check_interval_hours": 6,    # Căutări la fiecare 6 ore
  "max_results_per_search": 20  # Maximum 20 de rezultate
}
```

### Platforme multiple:

```json
{
  "platforms": ["booking", "airbnb"]  # Când vor fi implementate
}
```

## 📊 Monitorizare și Statistici

Agentul urmărește:
- Numărul de căutări efectuate
- Timpul de execuție pentru fiecare căutare
- Istoricul prețurilor pentru fiecare cazare
- Rata de succes a notificărilor

Vezi statisticile cu comanda `status` în modul interactiv.

## 🔒 Securitate

- **Nu stoca parole în plain text** în configurații
- Folosește variabile de mediu pentru date sensibile
- Bazele de date sunt locale (SQLite)
- Nu se transmit date către servicii terțe

## 🆘 Support

Dacă întâmpini probleme:

1. Verifică log-urile în `accommodation_agent.log`
2. Rulează cu `--test-email` pentru a verifica email-ul
3. Testează cu `--run-once` pentru o căutare manuală
4. Verifică criteriile în `config.json`

## 🚧 Limitări Actuale

- Doar Booking.com este implementat
- Web scraping poate fi afectat de schimbările în site
- Rate limiting natural prin întârzieri aleatorii
- Nu suportă CAPTCHA automat

## 🔮 Planuri Viitoare

- [ ] Suport pentru Airbnb
- [ ] Suport pentru Hotels.com
- [ ] Interfață web pentru configurare
- [ ] Notificări Telegram/WhatsApp
- [ ] API pentru integrări
- [ ] Docker container
- [ ] Machine learning pentru predicții de preț

## 📝 Licență

Acest proiect este pentru uz personal și educațional. Respectă termenii de utilizare ai platformelor pe care le scrapiază.

---

**Happy searching! 🏨✈️**