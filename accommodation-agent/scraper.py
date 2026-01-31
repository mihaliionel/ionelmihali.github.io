"""
Modul pentru extragerea datelor de cazări de pe diverse platforme
"""

import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
import time
import random
import urllib.parse
from fake_useragent import UserAgent

@dataclass
class Accommodation:
    """Reprezentarea unei cazări găsite"""
    title: str
    price: float
    currency: str
    rating: float
    location: str
    url: str
    image_url: Optional[str] = None
    description: Optional[str] = None
    amenities: List[str] = None
    platform: str = "unknown"
    
    def __post_init__(self):
        if self.amenities is None:
            self.amenities = []

class BaseScraper:
    """Clasa de bază pentru toate scraperele"""
    
    def __init__(self):
        self.session = requests.Session()
        self.ua = UserAgent()
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept-Language': 'ro-RO,ro;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def random_delay(self, min_delay=1, max_delay=3):
        """Întârziere aleatoare pentru a evita detectarea"""
        time.sleep(random.uniform(min_delay, max_delay))
    
    def search_accommodations(self, criteria) -> List[Accommodation]:
        """Metodă abstractă pentru căutarea cazărilor"""
        raise NotImplementedError("Trebuie implementată în subclasă")

class BookingScraper(BaseScraper):
    """Scraper pentru Booking.com"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.booking.com"
        
    def build_search_url(self, criteria):
        """Construiește URL-ul de căutare pentru Booking.com"""
        params = {
            'ss': criteria.destination,
            'checkin': criteria.check_in.strftime('%Y-%m-%d'),
            'checkout': criteria.check_out.strftime('%Y-%m-%d'),
            'group_adults': str(criteria.guests),
            'group_children': '0',
            'no_rooms': '1',
            'sb_price_type': 'total',
            'lang': 'ro'
        }
        
        return f"{self.base_url}/searchresults.html?" + urllib.parse.urlencode(params)
    
    def parse_accommodation(self, element) -> Optional[Accommodation]:
        """Parsează un element HTML și returnează o cazare"""
        try:
            # Extrage titlul
            title_elem = element.find('h3', {'data-testid': 'title'})
            if not title_elem:
                title_elem = element.find('h3')
            title = title_elem.get_text(strip=True) if title_elem else "Titlu necunoscut"
            
            # Extrage prețul
            price_elem = element.find('span', {'data-testid': 'price-and-discounted-price'})
            if not price_elem:
                price_elem = element.find('span', class_='prco-valign-middle-helper')
            
            price = 0.0
            currency = "RON"
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # Extrage numerele din text (ex: "285 RON" -> 285.0)
                import re
                price_match = re.search(r'([0-9.,]+)', price_text.replace(',', '.'))
                if price_match:
                    price = float(price_match.group(1))
                
                if 'EUR' in price_text or '€' in price_text:
                    currency = "EUR"
                elif 'USD' in price_text or '$' in price_text:
                    currency = "USD"
            
            # Extrage ratingul
            rating_elem = element.find('div', {'data-testid': 'review-score'})
            rating = 0.0
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                rating_match = re.search(r'([0-9,]+)', rating_text.replace(',', '.'))
                if rating_match:
                    rating = float(rating_match.group(1))
            
            # Extrage locația
            location_elem = element.find('span', {'data-testid': 'address'})
            location = location_elem.get_text(strip=True) if location_elem else "Locație necunoscută"
            
            # Extrage URL-ul
            link_elem = element.find('a', {'data-testid': 'title-link'})
            if not link_elem:
                link_elem = element.find('a')
            url = ""
            if link_elem and link_elem.get('href'):
                url = self.base_url + link_elem.get('href')
            
            # Extrage imaginea
            img_elem = element.find('img')
            image_url = img_elem.get('src') if img_elem else None
            
            return Accommodation(
                title=title,
                price=price,
                currency=currency,
                rating=rating,
                location=location,
                url=url,
                image_url=image_url,
                platform="booking"
            )
            
        except Exception as e:
            print(f"Eroare la parsarea cazării: {e}")
            return None
    
    def search_accommodations(self, criteria) -> List[Accommodation]:
        """Caută cazări pe Booking.com"""
        accommodations = []
        
        try:
            url = self.build_search_url(criteria)
            print(f"Căutare pe: {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Caută elementele care conțin cazările
            property_elements = soup.find_all('div', {'data-testid': 'property-card'})
            
            # Fallback în cazul în care structura s-a schimbat
            if not property_elements:
                property_elements = soup.find_all('div', class_=['sr_property_block', 'listItem'])
            
            print(f"Găsite {len(property_elements)} elemente pe pagină")
            
            for element in property_elements[:criteria.max_price]:  # Limitează rezultatele
                accommodation = self.parse_accommodation(element)
                if accommodation and accommodation.price > 0:
                    accommodations.append(accommodation)
                
                self.random_delay(0.5, 1.5)
            
        except requests.exceptions.RequestException as e:
            print(f"Eroare la cererea HTTP: {e}")
        except Exception as e:
            print(f"Eroare generală la scraping: {e}")
        
        return accommodations

class ScraperFactory:
    """Factory pentru crearea scraperelor"""
    
    scrapers = {
        'booking': BookingScraper,
        # 'airbnb': AirbnbScraper,  # Se poate adăuga în viitor
        # 'hotels': HotelsScraper,
    }
    
    @classmethod
    def create_scraper(cls, platform: str) -> BaseScraper:
        """Creează un scraper pentru platforma specificată"""
        if platform not in cls.scrapers:
            raise ValueError(f"Platforma '{platform}' nu este suportată")
        
        return cls.scrapers[platform]()
    
    @classmethod
    def get_supported_platforms(cls) -> List[str]:
        """Returnează lista platformelor suportate"""
        return list(cls.scrapers.keys())

def search_all_platforms(criteria, platforms: List[str] = None) -> List[Accommodation]:
    """Caută pe toate platformele specificate"""
    if platforms is None:
        platforms = ScraperFactory.get_supported_platforms()
    
    all_accommodations = []
    
    for platform in platforms:
        try:
            print(f"Căutare pe platforma: {platform}")
            scraper = ScraperFactory.create_scraper(platform)
            accommodations = scraper.search_accommodations(criteria)
            all_accommodations.extend(accommodations)
            print(f"Găsite {len(accommodations)} cazări pe {platform}")
            
            # Pauză între platforme
            time.sleep(random.uniform(2, 4))
            
        except Exception as e:
            print(f"Eroare la căutarea pe {platform}: {e}")
    
    return all_accommodations