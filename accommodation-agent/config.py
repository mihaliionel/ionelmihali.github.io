"""
Configurația pentru agentul de căutare cazări
"""

import os
from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime, timedelta

@dataclass
class SearchCriteria:
    """Criterii de căutare pentru cazări"""
    destination: str
    check_in: datetime
    check_out: datetime
    guests: int
    max_price: float
    currency: str = "RON"
    property_types: List[str] = None  # ["hotel", "apartment", "house"]
    min_rating: float = 0.0
    
    def __post_init__(self):
        if self.property_types is None:
            self.property_types = ["hotel", "apartment"]

@dataclass
class EmailConfig:
    """Configurația pentru trimiterea email-urilor"""
    smtp_server: str
    smtp_port: int
    email: str
    password: str  # App password pentru Gmail/Outlook
    recipient: str
    
    @classmethod
    def from_env(cls):
        """Încarcă configurația din variabilele de mediu"""
        return cls(
            smtp_server=os.getenv("SMTP_SERVER", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            email=os.getenv("SENDER_EMAIL"),
            password=os.getenv("EMAIL_PASSWORD"),
            recipient=os.getenv("RECIPIENT_EMAIL")
        )

@dataclass
class AgentConfig:
    """Configurația principală a agentului"""
    search_criteria: SearchCriteria
    email_config: EmailConfig
    check_interval_hours: int = 6
    max_results_per_search: int = 10
    platforms: List[str] = None
    
    def __post_init__(self):
        if self.platforms is None:
            self.platforms = ["booking"]  # Se poate extinde cu "airbnb", "hotels"

# Exemplu de configurare
def get_default_config():
    """Returnează o configurație exemplu"""
    search_criteria = SearchCriteria(
        destination="București, România",
        check_in=datetime.now() + timedelta(days=30),
        check_out=datetime.now() + timedelta(days=32),
        guests=2,
        max_price=500.0,
        currency="RON",
        property_types=["hotel", "apartment"],
        min_rating=7.0
    )
    
    email_config = EmailConfig.from_env()
    
    return AgentConfig(
        search_criteria=search_criteria,
        email_config=email_config,
        check_interval_hours=12,
        max_results_per_search=15
    )