"""
Sistem de filtrare pentru cazări
"""

from typing import List, Dict, Callable
from dataclasses import dataclass
from scraper import Accommodation
from config import SearchCriteria

class AccommodationFilter:
    """Clasa pentru filtrarea cazărilor pe baza criteriilor"""
    
    def __init__(self, criteria: SearchCriteria):
        self.criteria = criteria
    
    def filter_by_price(self, accommodations: List[Accommodation]) -> List[Accommodation]:
        """Filtrează cazările după preț"""
        filtered = []
        
        for accommodation in accommodations:
            # Convertește prețul în moneda criteriilor dacă este necesar
            price_in_target_currency = self._convert_currency(
                accommodation.price, 
                accommodation.currency, 
                self.criteria.currency
            )
            
            if price_in_target_currency <= self.criteria.max_price:
                # Actualizează prețul în moneda dorită pentru afișare
                accommodation.price = price_in_target_currency
                accommodation.currency = self.criteria.currency
                filtered.append(accommodation)
        
        return filtered
    
    def filter_by_rating(self, accommodations: List[Accommodation]) -> List[Accommodation]:
        """Filtrează cazările după rating"""
        return [acc for acc in accommodations if acc.rating >= self.criteria.min_rating]
    
    def filter_duplicates(self, accommodations: List[Accommodation]) -> List[Accommodation]:
        """Elimină duplicatele pe baza titlului și locației"""
        seen = set()
        unique_accommodations = []
        
        for accommodation in accommodations:
            # Creează o cheie unică bazată pe titlu și locație
            key = f"{accommodation.title.lower().strip()}_{accommodation.location.lower().strip()}"
            
            if key not in seen:
                seen.add(key)
                unique_accommodations.append(accommodation)
        
        return unique_accommodations
    
    def sort_accommodations(self, accommodations: List[Accommodation], 
                          sort_by: str = "price") -> List[Accommodation]:
        """Sortează cazările după criteriul specificat"""
        sort_functions = {
            "price": lambda x: x.price,
            "rating": lambda x: -x.rating,  # Descrescător pentru rating
            "title": lambda x: x.title.lower(),
        }
        
        if sort_by in sort_functions:
            return sorted(accommodations, key=sort_functions[sort_by])
        
        return accommodations
    
    def _convert_currency(self, amount: float, from_currency: str, to_currency: str) -> float:
        """Convertește prețul între monede (implementare simplificată)"""
        if from_currency == to_currency:
            return amount
        
        # Cursuri de schimb aproximative - în producție ar trebui să folosești un API real
        exchange_rates = {
            ("EUR", "RON"): 4.98,
            ("USD", "RON"): 4.52,
            ("RON", "EUR"): 0.20,
            ("RON", "USD"): 0.22,
            ("USD", "EUR"): 0.92,
            ("EUR", "USD"): 1.09,
        }
        
        rate_key = (from_currency, to_currency)
        if rate_key in exchange_rates:
            return amount * exchange_rates[rate_key]
        
        # Dacă nu avem cursul direct, încearcă prin RON
        if from_currency != "RON" and to_currency != "RON":
            ron_amount = self._convert_currency(amount, from_currency, "RON")
            return self._convert_currency(ron_amount, "RON", to_currency)
        
        return amount  # Fallback - returnează suma originală
    
    def apply_all_filters(self, accommodations: List[Accommodation]) -> List[Accommodation]:
        """Aplică toate filtrele în ordine"""
        # Filtrare după preț
        filtered = self.filter_by_price(accommodations)
        print(f"După filtrarea pe preț: {len(filtered)} cazări")
        
        # Filtrare după rating
        filtered = self.filter_by_rating(filtered)
        print(f"După filtrarea pe rating: {len(filtered)} cazări")
        
        # Eliminare duplicate
        filtered = self.filter_duplicates(filtered)
        print(f"După eliminarea duplicatelor: {len(filtered)} cazări")
        
        # Sortare după preț
        filtered = self.sort_accommodations(filtered, "price")
        
        return filtered

class PriceAlert:
    """Clasa pentru gestionarea alertelor de preț"""
    
    def __init__(self, target_price: float, currency: str = "RON"):
        self.target_price = target_price
        self.currency = currency
    
    def check_alerts(self, accommodations: List[Accommodation]) -> List[Accommodation]:
        """Verifică dacă există cazări sub prețul țintă"""
        alerts = []
        
        for accommodation in accommodations:
            if accommodation.currency == self.currency and accommodation.price <= self.target_price:
                alerts.append(accommodation)
        
        return alerts

class QualityFilter:
    """Filtru pentru calitatea cazărilor"""
    
    @staticmethod
    def is_high_quality(accommodation: Accommodation) -> bool:
        """Verifică dacă o cazare este de calitate înaltă"""
        # Criterii pentru calitate înaltă
        has_good_rating = accommodation.rating >= 8.0
        has_reasonable_price = accommodation.price > 0
        has_complete_info = bool(accommodation.title and accommodation.location)
        
        return has_good_rating and has_reasonable_price and has_complete_info
    
    @staticmethod
    def filter_high_quality(accommodations: List[Accommodation]) -> List[Accommodation]:
        """Returnează doar cazările de calitate înaltă"""
        return [acc for acc in accommodations if QualityFilter.is_high_quality(acc)]

def create_custom_filter(filter_func: Callable[[Accommodation], bool]):
    """Creează un filtru personalizat"""
    def custom_filter(accommodations: List[Accommodation]) -> List[Accommodation]:
        return [acc for acc in accommodations if filter_func(acc)]
    return custom_filter

# Exemple de filtre personalizate
def has_kitchen_filter(accommodation: Accommodation) -> bool:
    """Verifică dacă cazarea are bucătărie"""
    title_lower = accommodation.title.lower()
    return any(keyword in title_lower for keyword in ['kitchen', 'kitchenette', 'bucătărie', 'cooking'])

def is_apartment_filter(accommodation: Accommodation) -> bool:
    """Verifică dacă cazarea este apartament"""
    title_lower = accommodation.title.lower()
    return any(keyword in title_lower for keyword in ['apartment', 'apartament', 'studio', 'flat'])

def central_location_filter(accommodation: Accommodation) -> bool:
    """Verifică dacă cazarea este în centru"""
    location_lower = accommodation.location.lower()
    return any(keyword in location_lower for keyword in ['centru', 'center', 'central', 'downtown'])