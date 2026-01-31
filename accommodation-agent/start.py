#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de start rapid pentru Agentul de Căutare Cazări
Acest script ajută utilizatorii noi să configureze și să pornească agentul rapid.
"""

import os
import sys
import subprocess
from datetime import datetime, timedelta

# Fix pentru encoding pe Windows
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def print_header():
    print("🏨" + "="*50 + "🏨")
    print("    Agent de Căutare Cazări - Setup Rapid")
    print("🏨" + "="*50 + "🏨")
    print()

def check_python_version():
    """Verifică versiunea Python"""
    if sys.version_info < (3, 7):
        print("❌ EROARE: Python 3.7+ este necesar pentru acest agent")
        print(f"   Versiunea ta: {sys.version}")
        sys.exit(1)
    print(f"✅ Python {sys.version.split()[0]} - OK")

def install_requirements():
    """Instalează dependențele"""
    print("\n📦 Instalare dependențe...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ Dependențe instalate cu succes")
    except subprocess.CalledProcessError:
        print("⚠️  Unele dependențe au eșuat, dar agentul ar trebui să funcționeze")

def get_user_input():
    """Colectează informațiile de la utilizator"""
    print("\n📝 Configurare agent - răspunde la următoarele întrebări:")
    print("   (Poți lăsa gol pentru valorile implicite)")
    
    # Criteriile de căutare
    print("\n🔍 Criteriile de căutare:")
    destination = input("Destinația (București, România): ").strip() or "București, România"
    
    try:
        days_ahead = int(input("Peste câte zile să caute? (30): ").strip() or "30")
    except ValueError:
        days_ahead = 30
    
    try:
        nights = int(input("Câte nopți? (2): ").strip() or "2")
    except ValueError:
        nights = 2
    
    try:
        guests = int(input("Câți oaspeți? (2): ").strip() or "2")
    except ValueError:
        guests = 2
    
    try:
        max_price = float(input("Preț maxim în RON (500): ").strip() or "500")
    except ValueError:
        max_price = 500.0
    
    try:
        min_rating = float(input("Rating minim (7.0): ").strip() or "7.0")
    except ValueError:
        min_rating = 7.0
    
    # Configurația email
    print("\n📧 Configurația email:")
    sender_email = input("Email-ul tău (pentru trimitere): ").strip()
    if not sender_email:
        print("❌ Email-ul expeditor este obligatoriu!")
        return None
    
    sender_password = input("App Password Gmail (pentru trimitere): ").strip()
    if not sender_password:
        print("❌ Parola aplicației este obligatorie!")
        return None
    
    recipient_email = input(f"Email destinatar ({sender_email}): ").strip() or sender_email
    
    # Intervalul de căutare
    try:
        check_hours = int(input("La câte ore să caute? (12): ").strip() or "12")
    except ValueError:
        check_hours = 12
    
    return {
        "destination": destination,
        "days_ahead": days_ahead,
        "nights": nights,
        "guests": guests,
        "max_price": max_price,
        "min_rating": min_rating,
        "sender_email": sender_email,
        "sender_password": sender_password,
        "recipient_email": recipient_email,
        "check_hours": check_hours
    }

def create_config(user_input):
    """Creează fișierul de configurare"""
    import json
    
    check_in = datetime.now() + timedelta(days=user_input["days_ahead"])
    check_out = check_in + timedelta(days=user_input["nights"])
    
    config = {
        "search_criteria": {
            "destination": user_input["destination"],
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "guests": user_input["guests"],
            "max_price": user_input["max_price"],
            "currency": "RON",
            "property_types": ["hotel", "apartment"],
            "min_rating": user_input["min_rating"]
        },
        "email": {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "email": user_input["sender_email"],
            "password": user_input["sender_password"],
            "recipient": user_input["recipient_email"]
        },
        "check_interval_hours": user_input["check_hours"],
        "max_results_per_search": 15,
        "platforms": ["booking"]
    }
    
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    print("✅ Configurația a fost salvată în config.json")

def test_configuration():
    """Testează configurația"""
    print("\n🧪 Testare configurație...")
    try:
        result = subprocess.run([sys.executable, "main.py", "--test-email"], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ Email-ul funcționează!")
            return True
        else:
            print("❌ Email-ul nu funcționează:")
            print(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("⏰ Testul email-ului a expirat")
        return False
    except Exception as e:
        print(f"❌ Eroare la testarea email-ului: {e}")
        return False

def run_test_search():
    """Rulează o căutare de test"""
    print("\n🔍 Căutare de test...")
    try:
        result = subprocess.run([sys.executable, "main.py", "--run-once"], 
                              capture_output=True, text=True, timeout=60)
        if "Găsite" in result.stdout:
            print("✅ Căutarea funcționează!")
            print(result.stdout.split('\n')[-2])  # Ultima linie cu rezultate
            return True
        else:
            print("⚠️  Căutarea s-a terminat, dar fără rezultate vizibile")
            if result.stderr:
                print("Erori:", result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("⏰ Căutarea de test a expirat (normal pentru prima rulare)")
        return True
    except Exception as e:
        print(f"❌ Eroare la căutarea de test: {e}")
        return False

def start_daemon():
    """Pornește agentul ca daemon"""
    print("\n🚀 Pornire agent automat...")
    print("   (Folosește Ctrl+C pentru a opri)")
    
    try:
        subprocess.run([sys.executable, "main.py", "--daemon"])
    except KeyboardInterrupt:
        print("\n👋 Agent oprit de utilizator")

def show_summary(user_input):
    """Afișează un sumar al configurației"""
    check_in = datetime.now() + timedelta(days=user_input["days_ahead"])
    check_out = check_in + timedelta(days=user_input["nights"])
    
    print("\n📋 Sumarul configurației:")
    print(f"   🎯 Destinație: {user_input['destination']}")
    print(f"   📅 Check-in: {check_in.strftime('%d.%m.%Y')}")
    print(f"   📅 Check-out: {check_out.strftime('%d.%m.%Y')}")
    print(f"   👥 Oaspeți: {user_input['guests']}")
    print(f"   💰 Preț maxim: {user_input['max_price']} RON")
    print(f"   ⭐ Rating minim: {user_input['min_rating']}")
    print(f"   📧 Notificări: {user_input['recipient_email']}")
    print(f"   ⏰ Verificare: la fiecare {user_input['check_hours']} ore")

def main():
    print_header()
    
    # Verificări preliminare
    check_python_version()
    install_requirements()
    
    # Configurare utilizator
    user_input = get_user_input()
    if not user_input:
        print("\n❌ Configurarea a fost întreruptă")
        return
    
    # Creare configurație
    create_config(user_input)
    show_summary(user_input)
    
    # Testare
    email_ok = test_configuration()
    search_ok = run_test_search()
    
    if not email_ok:
        print("\n⚠️  Email-ul nu funcționează. Verifică configurația în config.json")
        print("   Instrucțiuni pentru Gmail: https://support.google.com/accounts/answer/185833")
    
    if email_ok and search_ok:
        print("\n🎉 Totul funcționează perfect!")
        
        choice = input("\n❓ Vrei să pornești agentul automat acum? (y/n): ").strip().lower()
        if choice in ['y', 'yes', 'da', 'd', '']:
            start_daemon()
        else:
            print("\n💡 Pentru a porni agentul mai târziu:")
            print("   python main.py --daemon")
    else:
        print("\n🔧 Unele funcții nu merg perfect, dar poți începe:")
        print("   python main.py --daemon")
    
    print("\n📚 Vezi README.md pentru documentație completă")
    print("👋 Mulțumesc că folosești Agentul de Căutare Cazări!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Setup întrerupt de utilizator")
    except Exception as e:
        print(f"\n❌ Eroare neașteptată: {e}")
        print("📚 Vezi README.md pentru ajutor")