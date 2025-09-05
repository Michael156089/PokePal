# Pokepal

Mimikyu Messenger est une petite appli de chat sympa écrite en **Python** avec une interface moderne grâce à `customtkinter`.  
Elle utilise **Google Gemini** pour répondre comme une IA et embarque plusieurs outils pratiques :

- 💬 Discuter avec l'IA en temps réel  
- 📋 Gérer une liste de tâches  
- 📅 Planifier des événements avec un agenda  
- 🔒 Stocker des fichiers dans un coffre-fort protégé par mot de passe  
- 🧠 Revoir l'historique des conversations  

---

## 🔧 Installation

1. **Cloner ce repo :**
```bash
git clone https://github.com/Michael156089/PokePal
```

2. **(Optionnel) Créer un environnement virtuel :**
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate   # Windows
```

3. **Installer les dépendances :**
```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuration

- Lance le programme (`python main.py`)  
- Rentre ta **clé API Gemini** dans les paramètres pour activer l’IA  
- Change les avatars si tu veux personnaliser ton app  

---


---

## 🛠️ bibliotheques utilisées

- Python 3.9+
- customtkinter pour l’UI
- sqlite3 pour stocker les données
- Pillow pour gérer les images
- google-generativeai pour discuter avec Gemini

---

## 📁 Organisation du projet

```
.
├── main.py                # Code principal
├── requirements.txt       # Liste des dépendances
├── assets/                # Images et avatars
└── vault_files/           # Coffre-fort des fichiers
```

---

## 📝 Licence
Projet open source

