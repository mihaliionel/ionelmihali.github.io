"""
Sistem de notificări email pentru agentul de căutare cazări
"""

import smtplib
from email.mime.text import MIMEText as MimeText
from email.mime.multipart import MIMEMultipart as MimeMultipart
from email.mime.image import MIMEImage as MimeImage
import requests
from typing import List, Optional
from datetime import datetime
from scraper import Accommodation
from config import EmailConfig
import logging

class EmailNotifier:
    """Clasa pentru trimiterea notificărilor prin email"""
    
    def __init__(self, email_config: EmailConfig):
        self.config = email_config
        self.logger = logging.getLogger(__name__)
    
    def send_accommodation_alert(self, accommodations: List[Accommodation], 
                               search_criteria=None) -> bool:
        """Trimite alertă cu cazările găsite"""
        if not accommodations:
            self.logger.info("Nu există cazări de trimis")
            return True
        
        try:
            subject = f"🏨 Găsite {len(accommodations)} cazări noi!"
            body = self._create_email_body(accommodations, search_criteria)
            
            return self._send_email(subject, body, is_html=True)
            
        except Exception as e:
            self.logger.error(f"Eroare la trimiterea email-ului: {e}")
            return False
    
    def send_price_alert(self, accommodations: List[Accommodation], 
                        target_price: float) -> bool:
        """Trimite alertă pentru cazările sub prețul țintă"""
        if not accommodations:
            return True
        
        try:
            subject = f"💰 ALERTĂ PREȚ: {len(accommodations)} cazări sub {target_price} RON!"
            body = self._create_price_alert_body(accommodations, target_price)
            
            return self._send_email(subject, body, is_html=True)
            
        except Exception as e:
            self.logger.error(f"Eroare la trimiterea alertei de preț: {e}")
            return False
    
    def send_test_email(self) -> bool:
        """Trimite un email de test pentru verificarea configurației"""
        try:
            subject = "🔧 Test - Agentul de căutare cazări"
            body = """
            <html>
            <body>
                <h2>Email de test</h2>
                <p>Dacă primești acest email, configurația este corectă!</p>
                <p>Agentul tău de căutare cazări este pregătit să îți trimită notificări.</p>
                <p><em>Trimis la: {}</em></p>
            </body>
            </html>
            """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            return self._send_email(subject, body, is_html=True)
            
        except Exception as e:
            self.logger.error(f"Eroare la trimiterea email-ului de test: {e}")
            return False
    
    def _create_email_body(self, accommodations: List[Accommodation], 
                          search_criteria=None) -> str:
        """Creează conținutul HTML al email-ului"""
        html = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { color: #2e86ab; margin-bottom: 20px; }
                .accommodation { 
                    border: 1px solid #ddd; 
                    margin-bottom: 15px; 
                    padding: 15px; 
                    border-radius: 8px;
                    background-color: #f9f9f9;
                }
                .title { color: #2e86ab; font-size: 18px; font-weight: bold; margin-bottom: 5px; }
                .price { color: #d73502; font-size: 20px; font-weight: bold; }
                .rating { color: #228b22; font-weight: bold; }
                .location { color: #666; font-style: italic; }
                .platform { 
                    background-color: #2e86ab; 
                    color: white; 
                    padding: 2px 8px; 
                    border-radius: 4px; 
                    font-size: 12px;
                }
                .summary { 
                    background-color: #e6f3ff; 
                    padding: 15px; 
                    border-radius: 8px; 
                    margin-bottom: 20px;
                }
            </style>
        </head>
        <body>
            <h1 class="header">🏨 Cazări găsite pentru tine</h1>
        """
        
        if search_criteria:
            html += f"""
            <div class="summary">
                <h3>Criteriile de căutare:</h3>
                <p><strong>Destinație:</strong> {search_criteria.destination}</p>
                <p><strong>Check-in:</strong> {search_criteria.check_in.strftime('%d.%m.%Y')}</p>
                <p><strong>Check-out:</strong> {search_criteria.check_out.strftime('%d.%m.%Y')}</p>
                <p><strong>Oaspeți:</strong> {search_criteria.guests}</p>
                <p><strong>Preț maxim:</strong> {search_criteria.max_price} {search_criteria.currency}</p>
            </div>
            """
        
        html += f"<p><strong>Găsite {len(accommodations)} cazări:</strong></p>"
        
        for acc in accommodations:
            html += f"""
            <div class="accommodation">
                <div class="title">{acc.title}</div>
                <div class="price">{acc.price:.2f} {acc.currency}</div>
                <div class="rating">⭐ {acc.rating}/10</div>
                <div class="location">📍 {acc.location}</div>
                <span class="platform">{acc.platform.upper()}</span>
                """
            
            if acc.url:
                html += f'<br><br><a href="{acc.url}" target="_blank" style="color: #2e86ab; text-decoration: none;">👁️ Vezi detalii</a>'
            
            html += "</div>"
        
        html += f"""
            <hr>
            <p style="color: #666; font-size: 12px;">
                Email trimis automat de agentul de căutare cazări la {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
            </p>
        </body>
        </html>
        """
        
        return html
    
    def _create_price_alert_body(self, accommodations: List[Accommodation], 
                               target_price: float) -> str:
        """Creează conținutul HTML pentru alertele de preț"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .alert {{ 
                    background-color: #ffe6e6; 
                    border: 2px solid #ff4444; 
                    padding: 15px; 
                    border-radius: 8px; 
                    margin-bottom: 20px;
                }}
                .accommodation {{ 
                    border: 1px solid #ddd; 
                    margin-bottom: 10px; 
                    padding: 10px; 
                    border-radius: 5px;
                    background-color: #f0fff0;
                }}
                .price {{ color: #d73502; font-size: 18px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="alert">
                <h1>💰 ALERTĂ PREȚ!</h1>
                <p>Găsite {len(accommodations)} cazări sub prețul de {target_price} RON!</p>
            </div>
        """
        
        for acc in accommodations:
            savings = target_price - acc.price
            html += f"""
            <div class="accommodation">
                <h3>{acc.title}</h3>
                <div class="price">{acc.price:.2f} {acc.currency}</div>
                <p><strong>Economisești: {savings:.2f} {acc.currency}</strong></p>
                <p>📍 {acc.location}</p>
                <p>⭐ {acc.rating}/10</p>
                """
            
            if acc.url:
                html += f'<a href="{acc.url}" target="_blank">Vezi acum!</a>'
                
            html += "</div>"
        
        html += """
            <p style="color: #666; font-size: 12px; margin-top: 20px;">
                Alertă trimisă automat - acționează rapid, ofertele se pot termina!
            </p>
        </body>
        </html>
        """
        
        return html
    
    def _send_email(self, subject: str, body: str, is_html: bool = False) -> bool:
        """Trimite email-ul efectiv"""
        try:
            # Validează configurația
            if not all([self.config.email, self.config.password, self.config.recipient]):
                self.logger.error("Configurația email incompletă")
                return False
            
            # Creează mesajul
            msg = MimeMultipart('alternative')
            msg['From'] = self.config.email
            msg['To'] = self.config.recipient
            msg['Subject'] = subject
            
            # Atașează conținutul
            if is_html:
                msg.attach(MimeText(body, 'html', 'utf-8'))
            else:
                msg.attach(MimeText(body, 'plain', 'utf-8'))
            
            # Trimite email-ul
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.email, self.config.password)
                server.send_message(msg)
            
            self.logger.info(f"Email trimis cu succes către {self.config.recipient}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            self.logger.error("Eroare de autentificare email - verifică parola")
            return False
        except smtplib.SMTPRecipientsRefused:
            self.logger.error("Adresa destinatarului refuzată")
            return False
        except Exception as e:
            self.logger.error(f"Eroare la trimiterea email-ului: {e}")
            return False

class NotificationManager:
    """Manager pentru toate tipurile de notificări"""
    
    def __init__(self, email_config: EmailConfig):
        self.email_notifier = EmailNotifier(email_config)
        self.last_sent = None
        self.sent_accommodations = set()  # Pentru a evita spam-ul
    
    def should_send_notification(self, accommodations: List[Accommodation]) -> bool:
        """Verifică dacă trebuie să trimită notificare"""
        if not accommodations:
            return False
        
        # Verifică dacă sunt cazări noi
        new_accommodations = []
        for acc in accommodations:
            acc_key = f"{acc.title}_{acc.location}_{acc.price}"
            if acc_key not in self.sent_accommodations:
                new_accommodations.append(acc)
                self.sent_accommodations.add(acc_key)
        
        return len(new_accommodations) > 0
    
    def send_if_needed(self, accommodations: List[Accommodation], 
                      search_criteria=None) -> bool:
        """Trimite notificare doar dacă este nevoie"""
        if self.should_send_notification(accommodations):
            return self.email_notifier.send_accommodation_alert(accommodations, search_criteria)
        return True
    
    def clear_sent_history(self):
        """Resetează istoricul cazărilor trimise"""
        self.sent_accommodations.clear()

# Funcții utilitare
def setup_email_logging():
    """Configurează logging-ul pentru email"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_email_configuration(email_config: EmailConfig) -> bool:
    """Testează configurația email"""
    notifier = EmailNotifier(email_config)
    return notifier.send_test_email()