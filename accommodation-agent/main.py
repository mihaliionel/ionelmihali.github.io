# -*- coding: utf-8 -*-
"""
Agentul principal de căutare cazări
Orchestrează toate componentele: scraping, filtrare, baza de date, notificări și scheduling
"""

import time
import logging
from datetime import datetime, timedelta
from typing import List, Optional
import argparse
import json
import os
import sys
from pathlib import Path

# Fix pentru encoding pe Windows
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Import-uri pentru componentele agentului
from config import get_default_config, AgentConfig, SearchCriteria, EmailConfig
from scraper import search_all_platforms, ScraperFactory
from filter import AccommodationFilter, PriceAlert, QualityFilter
from database import AccommodationDatabase, backup_database
from email_notifier import NotificationManager, setup_email_logging, test_email_configuration
from scheduler import AccommodationScheduler, create_default_scheduler, setup_scheduler_logging

class AccommodationAgent:
    """Clasa principală a agentului de căutare cazări"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.database = AccommodationDatabase()
        self.notification_manager = NotificationManager(config.email_config)
        self.accommodation_filter = AccommodationFilter(config.search_criteria)
        self.price_alert = PriceAlert(config.search_criteria.max_price * 0.8)  # 20% sub limită
        self.scheduler: Optional[AccommodationScheduler] = None
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        setup_email_logging()
        setup_scheduler_logging()
    
    def search_and_process(self) -> List:
        """Procesează o căutare completă: caută, filtrează, salvează și notifică"""
        start_time = time.time()
        
        try:
            self.logger.info("Începe căutarea cazărilor...")
            
            # 1. Caută cazări pe toate platformele
            raw_accommodations = search_all_platforms(
                self.config.search_criteria, 
                self.config.platforms
            )
            
            if not raw_accommodations:
                self.logger.warning("Nu s-au găsit cazări")
                return []
            
            self.logger.info(f"Găsite {len(raw_accommodations)} cazări brute")
            
            # 2. Aplică filtrele
            filtered_accommodations = self.accommodation_filter.apply_all_filters(raw_accommodations)
            
            if not filtered_accommodations:
                self.logger.info("Nu sunt cazări după aplicarea filtrelor")
                return []
            
            # 3. Salvează în baza de date
            accommodation_ids = []
            for accommodation in filtered_accommodations:
                acc_id = self.database.save_accommodation(accommodation)
                accommodation_ids.append(acc_id)
            
            # 4. Verifică alertele de preț
            price_alerts = self.price_alert.check_alerts(filtered_accommodations)
            
            # 5. Trimite notificări pentru cazări noi
            new_accommodations = self.database.get_new_accommodations(hours_back=24)
            
            if new_accommodations:
                success = self.notification_manager.send_if_needed(
                    new_accommodations, 
                    self.config.search_criteria
                )
                
                if success:
                    # Marchează ca notificate
                    notified_ids = [
                        self.database.save_accommodation(acc) 
                        for acc in new_accommodations
                    ]
                    self.database.mark_as_notified(notified_ids)
            
            # 6. Trimite alerte de preț dacă există
            if price_alerts:
                self.notification_manager.email_notifier.send_price_alert(
                    price_alerts, 
                    self.price_alert.target_price
                )
            
            # 7. Salvează statisticile căutării
            execution_time = int((time.time() - start_time) * 1000)
            self.database.save_search_record(
                self.config.search_criteria,
                len(filtered_accommodations),
                execution_time
            )
            
            self.logger.info(f"Căutare completă: {len(filtered_accommodations)} cazări, {execution_time}ms")
            
            return filtered_accommodations
            
        except Exception as e:
            self.logger.error(f"Eroare în procesarea căutării: {e}")
            return []
    
    def run_price_alerts(self):
        """Rulează doar verificarea alertelor de preț"""
        try:
            # Verifică scăderile de preț din baza de date
            price_drops = self.database.get_price_drops(percentage_threshold=10.0)
            
            if price_drops:
                self.logger.info(f"Găsite {len(price_drops)} scăderi de preț")
                
                # Convertește în obiecte Accommodation pentru notificare
                accommodations = []
                for drop in price_drops:
                    acc = self.database.get_accommodation_by_id(drop['id'])
                    if acc:
                        accommodations.append(acc)
                
                if accommodations:
                    self.notification_manager.email_notifier.send_price_alert(
                        accommodations,
                        self.price_alert.target_price
                    )
            
        except Exception as e:
            self.logger.error(f"Eroare la verificarea alertelor: {e}")
    
    def cleanup_database(self):
        """Curăță datele vechi din baza de date"""
        try:
            self.logger.info("Curățare bază de date...")
            
            # Creează backup înainte de curățare
            backup_path = backup_database(self.database.db_path)
            self.logger.info(f"Backup creat: {backup_path}")
            
            # Curăță datele vechi (păstrează 30 de zile)
            self.database.clean_old_data(days_to_keep=30)
            
            self.logger.info("Curățare completă")
            
        except Exception as e:
            self.logger.error(f"Eroare la curățarea bazei de date: {e}")
    
    def start_scheduler(self):
        """Pornește scheduler-ul pentru rularea automată"""
        if self.scheduler:
            self.logger.warning("Scheduler-ul rulează deja")
            return
        
        # Creează scheduler-ul cu funcțiile agentului
        self.scheduler = create_default_scheduler(
            search_function=self.search_and_process,
            alert_function=self.run_price_alerts,
            cleanup_function=self.cleanup_database
        )
        
        self.scheduler.start()
        self.logger.info("Scheduler pornit - agentul rulează automat")
    
    def stop_scheduler(self):
        """Oprește scheduler-ul"""
        if self.scheduler:
            self.scheduler.stop()
            self.scheduler = None
            self.logger.info("Scheduler oprit")
    
    def get_status(self) -> dict:
        """Returnează statusul agentului"""
        status = {
            'agent_running': True,
            'database_path': self.database.db_path,
            'platforms': self.config.platforms,
            'search_criteria': {
                'destination': self.config.search_criteria.destination,
                'check_in': self.config.search_criteria.check_in.isoformat(),
                'check_out': self.config.search_criteria.check_out.isoformat(),
                'max_price': self.config.search_criteria.max_price,
                'currency': self.config.search_criteria.currency,
            },
            'statistics': self.database.get_search_statistics(days_back=7)
        }
        
        if self.scheduler:
            status['scheduler'] = self.scheduler.get_status()
        
        return status
    
    def test_email(self) -> bool:
        """Testează configurația email"""
        return test_email_configuration(self.config.email_config)

def load_config_from_file(config_path: str) -> AgentConfig:
    """Încarcă configurația din fișier JSON"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # Parsează criteriile de căutare
        search_data = config_data.get('search_criteria', {})
        search_criteria = SearchCriteria(
            destination=search_data.get('destination', 'București, România'),
            check_in=datetime.fromisoformat(search_data.get('check_in')),
            check_out=datetime.fromisoformat(search_data.get('check_out')),
            guests=search_data.get('guests', 2),
            max_price=search_data.get('max_price', 500.0),
            currency=search_data.get('currency', 'RON'),
            property_types=search_data.get('property_types', ['hotel', 'apartment']),
            min_rating=search_data.get('min_rating', 7.0)
        )
        
        # Configurația email din environment sau fișier
        email_data = config_data.get('email', {})
        email_config = EmailConfig(
            smtp_server=email_data.get('smtp_server') or os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            smtp_port=email_data.get('smtp_port') or int(os.getenv('SMTP_PORT', '587')),
            email=email_data.get('email') or os.getenv('SENDER_EMAIL'),
            password=email_data.get('password') or os.getenv('EMAIL_PASSWORD'),
            recipient=email_data.get('recipient') or os.getenv('RECIPIENT_EMAIL')
        )
        
        return AgentConfig(
            search_criteria=search_criteria,
            email_config=email_config,
            check_interval_hours=config_data.get('check_interval_hours', 12),
            max_results_per_search=config_data.get('max_results_per_search', 15),
            platforms=config_data.get('platforms', ['booking'])
        )
        
    except Exception as e:
        logging.error(f"Eroare la încărcarea configurației: {e}")
        return get_default_config()

def create_example_config(config_path: str):
    """Creează un fișier de configurare exemplu"""
    example_config = {
        "search_criteria": {
            "destination": "București, România",
            "check_in": (datetime.now() + timedelta(days=30)).isoformat(),
            "check_out": (datetime.now() + timedelta(days=32)).isoformat(),
            "guests": 2,
            "max_price": 500.0,
            "currency": "RON",
            "property_types": ["hotel", "apartment"],
            "min_rating": 7.0
        },
        "email": {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "email": "your-email@gmail.com",
            "password": "your-app-password",
            "recipient": "recipient@gmail.com"
        },
        "check_interval_hours": 12,
        "max_results_per_search": 15,
        "platforms": ["booking"]
    }
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(example_config, f, indent=4, ensure_ascii=False)
    
    print(f"Configurație exemplu creată: {config_path}")

def main():
    """Funcția principală"""
    parser = argparse.ArgumentParser(description='Agent pentru căutarea automată de cazări')
    parser.add_argument('--config', '-c', default='config.json', 
                       help='Calea către fișierul de configurare')
    parser.add_argument('--create-config', action='store_true',
                       help='Creează un fișier de configurare exemplu')
    parser.add_argument('--test-email', action='store_true',
                       help='Testează configurația email')
    parser.add_argument('--run-once', action='store_true',
                       help='Rulează o singură căutare și iese')
    parser.add_argument('--daemon', action='store_true',
                       help='Rulează ca daemon cu scheduler automat')
    
    args = parser.parse_args()
    
    # Creează configurația exemplu dacă este solicitat
    if args.create_config:
        create_example_config(args.config)
        return
    
    # Încarcă configurația
    if os.path.exists(args.config):
        config = load_config_from_file(args.config)
    else:
        print(f"Fișierul de configurare {args.config} nu există. Folosind configurația implicită.")
        print(f"Rulează --create-config pentru a crea o configurație exemplu.")
        config = get_default_config()
    
    # Creează agentul
    agent = AccommodationAgent(config)
    
    # Testează email-ul dacă este solicitat
    if args.test_email:
        if agent.test_email():
            print("✅ Email configurat corect!")
        else:
            print("❌ Eroare la configurația email")
        return
    
    # Rulează o singură dată dacă este solicitat
    if args.run_once:
        print("Rulare unică...")
        results = agent.search_and_process()
        print(f"Găsite {len(results)} cazări")
        return
    
    # Rulează ca daemon
    if args.daemon:
        print("Pornire daemon...")
        agent.start_scheduler()
        
        try:
            # Ține programul în viață
            while True:
                time.sleep(60)
                # Afișează statusul periodic
                status = agent.get_status()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Agent activ - {status['statistics']['total_searches']} căutări în ultimele 7 zile")
                
        except KeyboardInterrupt:
            print("\nOprire daemon...")
            agent.stop_scheduler()
    else:
        # Mod interactiv
        print("Agent de căutare cazări pornit!")
        print("Comenzi disponibile:")
        print("  search - Caută cazări acum")
        print("  status - Afișează statusul")
        print("  start - Porniște scheduler-ul automat")
        print("  stop - Oprește scheduler-ul")
        print("  test-email - Testează email-ul")
        print("  exit - Ieși")
        
        while True:
            try:
                command = input("\n> ").strip().lower()
                
                if command == 'search':
                    results = agent.search_and_process()
                    print(f"Găsite {len(results)} cazări")
                
                elif command == 'status':
                    status = agent.get_status()
                    print(json.dumps(status, indent=2, ensure_ascii=False))
                
                elif command == 'start':
                    agent.start_scheduler()
                    print("Scheduler pornit")
                
                elif command == 'stop':
                    agent.stop_scheduler()
                    print("Scheduler oprit")
                
                elif command == 'test-email':
                    if agent.test_email():
                        print("✅ Email trimis cu succes!")
                    else:
                        print("❌ Eroare la trimiterea email-ului")
                
                elif command in ['exit', 'quit']:
                    break
                
                else:
                    print("Comandă necunoscută")
                    
            except KeyboardInterrupt:
                break
        
        # Oprește scheduler-ul la ieșire
        agent.stop_scheduler()
        print("Agent oprit")

if __name__ == "__main__":
    main()
