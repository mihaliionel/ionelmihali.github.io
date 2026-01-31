# -*- coding: utf-8 -*-
"""
Script pentru configurarea corectă a Gmail App Password
"""

import json
import os
import sys

def print_gmail_instructions():
    """Afișează instrucțiunile pentru configurarea Gmail App Password"""
    print("📧 CONFIGURARE GMAIL APP PASSWORD")
    print("=" * 50)
    print()
    print("Pentru a folosi Gmail SMTP cu acest agent, ai nevoie de un App Password:")
    print()
    print("1️⃣  Activează 2-Factor Authentication pe contul Google:")
    print("   https://myaccount.google.com/security")
    print()
    print("2️⃣  Generează un App Password:")
    print("   https://myaccount.google.com/apppasswords")
    print("   - Selectează 'Mail' ca aplicație")
    print("   - Folosește-o pentru acest agent")
    print()
    print("3️⃣  Folosește App Password-ul în loc de parola ta normală")
    print()
    print("⚠️  IMPORTANT: Nu folosi parola normală Gmail!")
    print()

def update_config_with_app_password():
    """Actualizează config.json cu App Password-ul corect"""
    config_path = "config.json"
    
    if not os.path.exists(config_path):
        print("❌ Fișierul config.json nu există!")
        print("Rulează 'python start.py' mai întâi.")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Eroare la citirea config.json: {e}")
        return False
    
    print()
    print("Configurația curentă:")
    print(f"Email: {config.get('email', {}).get('email', 'N/A')}")
    print(f"Parola curentă: {'*' * len(config.get('email', {}).get('password', ''))}")
    print()
    
    # Cere App Password-ul
    print("Introdu App Password-ul Gmail (nu parola normală!):")
    app_password = input("App Password: ").strip()
    
    if not app_password:
        print("❌ App Password-ul nu poate fi gol!")
        return False
    
    # Verifică dacă pare a fi un App Password (16 caractere, fără spații)
    app_password_clean = app_password.replace(' ', '').replace('-', '')
    if len(app_password_clean) != 16:
        print("⚠️  ATENȚIE: App Password-ul Google are de obicei 16 caractere.")
        print("Asigură-te că ai introdus App Password-ul, nu parola normală!")
        
        confirm = input("Continuă oricum? (y/n): ").lower()
        if confirm not in ['y', 'yes', 'da']:
            return False
    
    # Actualizează configurația
    config['email']['password'] = app_password_clean
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        print("✅ Configurația a fost actualizată!")
        return True
    
    except Exception as e:
        print(f"❌ Eroare la salvarea config.json: {e}")
        return False

def test_email_config():
    """Testează configurația email"""
    print("\n🧪 Testare configurație email...")
    
    try:
        import subprocess
        result = subprocess.run([sys.executable, "main.py", "--test-email"], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Email-ul funcționează perfect!")
            return True
        else:
            print("❌ Email-ul încă nu funcționează:")
            if result.stderr:
                print(result.stderr)
            return False
    
    except subprocess.TimeoutExpired:
        print("⏰ Testul a expirat")
        return False
    except Exception as e:
        print(f"❌ Eroare la test: {e}")
        return False

def main():
    print_gmail_instructions()
    
    print("Ce vrei să faci?")
    print("1. Actualizez App Password-ul în config.json")
    print("2. Testez doar configurația curentă")
    print("3. Ieș")
    
    choice = input("\nAlege (1-3): ").strip()
    
    if choice == '1':
        if update_config_with_app_password():
            test_email_config()
    elif choice == '2':
        test_email_config()
    elif choice == '3':
        print("👋 La revedere!")
    else:
        print("❌ Opțiune invalidă!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Întrerupt de utilizator")
    except Exception as e:
        print(f"❌ Eroare: {e}")