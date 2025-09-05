import customtkinter as ctk
from tkinter import messagebox, filedialog, simpledialog
import sqlite3
import datetime
import json
import os
from PIL import Image, ImageTk
import google.generativeai as genai
import threading
import hashlib
import shutil
from dataclasses import dataclass
from typing import List, Optional


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class MimikyuDatabase:
    def __init__(self, db_path="mimikyu.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                message_type TEXT DEFAULT 'text'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'todo',
                priority INTEGER DEFAULT 2,
                created_date TEXT NOT NULL,
                due_date TEXT
            )
        """)

      
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_date TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_message(self, sender, content, message_type="text"):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = datetime.datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO messages (sender, content, timestamp, message_type)
            VALUES (?, ?, ?, ?)
        """, (sender, content, timestamp, message_type))
        
        conn.commit()
        conn.close()
    
    def get_recent_messages(self, limit=50):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT sender, content FROM messages 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        messages = cursor.fetchall()
        conn.close()
        return messages[::-1]
    
    def save_setting(self, key, value):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        """, (key, value))
        
        conn.commit()
        conn.close()
    
    def get_setting(self, key, default=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else default

class MimikyuAI:
    def __init__(self, db: MimikyuDatabase):
        self.db = db
        self.api_key = self.db.get_setting("gemini_api_key", "")
        self.model = None
        if self.api_key:
            self.configure_gemini()

    def configure_gemini(self):
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        except Exception as e:
            print(f"Erreur de configuration Gemini: {e}")
            self.model = None
    
    def set_api_key(self, api_key: str):
        self.api_key = api_key
        self.db.save_setting("gemini_api_key", api_key)
        self.configure_gemini()
    
    def get_conversation_context(self):
        recent_messages = self.db.get_recent_messages(15)
        context = []
        
        for sender, content in recent_messages:
            role = "model" if sender == "Mimikyu" else "user"
            context.append({"role": role, "parts": [content]})
        
        return context
    
    def call_gemini_api(self, messages):
        if not self.model:
            return "Désolé, l'IA n'est pas configurée. Va dans les paramètres pour entrer ta clé API Gemini ! >_<"

        try:
            system_prompt = """tu es un assistant virtuel qui s'appelle mimikyu
            
            Personnalité :
            - tu es un pokemon qui s'appelle mimikyu.
            - tu déteste pikachu 
            - tu m'aide dans la vie de tous les jours
            - Tu parles en français.
            
            Style de réponse :
            - Messages courts et directs.
            - Utilise des minuscules la plupart du temps.
            - tu aime parler, ça passe l'ennui.
            - quand je te demande de me donner une image  fait le.
            """
            
            full_history = [{"role": "user", "parts": [system_prompt]}]
            full_history.append({"role": "model", "parts": ["ok, compris! je suis prêt. à+ tard! ;)"]})
            full_history.extend(messages)
            
            response = self.model.generate_content(full_history)
            return response.text
            
        except Exception as e:
            print(f"Erreur API Gemini: {e}")
            return f"oops! l'api a eu un bug... ({e}) essaie encore! :s"
    
    def generate_response(self, user_message: str) -> str:
        if not self.api_key:
            return "yo! configure ta clé api gemini dans les paramètres pour qu'on puisse chatter! ;)"
        
        context = self.get_conversation_context()
        context.append({"role": "user", "parts": [user_message]})
        return self.call_gemini_api(context)

class MessageBubble(ctk.CTkFrame):
    def __init__(self, master, sender, message, is_mimikyu=False, avatar_image=None):
        color = "#2d5a87" if is_mimikyu else "#4a4e69"
        super().__init__(master, fg_color=color, corner_radius=15)
        
        self.grid_columnconfigure(1, weight=1)
        
        # Avatar
        if avatar_image:
            avatar_label = ctk.CTkLabel(self, image=avatar_image, text="")
            avatar_label.grid(row=0, column=0, padx=10, pady=10, sticky="n")
        
        # Contenu
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="ew")
        
        sender_label = ctk.CTkLabel(content_frame, text=sender, 
                                  font=ctk.CTkFont(size=12, weight="bold"),
                                  text_color="#00d4ff" if is_mimikyu else "#9476ff")
        sender_label.pack(anchor="w")
        
        message_label = ctk.CTkLabel(content_frame, text=message, 
                                   font=ctk.CTkFont(size=11),
                                   wraplength=350, justify="left")
        message_label.pack(anchor="w", pady=(5, 0))

class MimikyuApp:
    def __init__(self, root):
        self.root = root
        self.db = MimikyuDatabase()
        self.ai = MimikyuAI(self.db)
        self.avatar_image = None
        self.mimikyu_avatar = None
        self.user_avatar = None
        
        self.setup_window()
        self.load_avatars()
        self.create_widgets()
        self.load_chat_history()
        
        self.is_typing = False
        
    def setup_window(self):
        self.root.title("MiMiKyU Messenger")
        self.root.geometry("700x800")
        
        
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def load_avatars(self):
        try:

            avatar_path = self.db.get_setting("avatar_path", "assets/default_avatar.png")
            if not os.path.exists("assets"):
                os.makedirs("assets")
            if not os.path.exists(avatar_path):
               
                Image.new('RGB', (40, 40), color='#9476ff').save(avatar_path)
            
            user_img = Image.open(avatar_path).resize((40, 40), Image.Resampling.LANCZOS)
            self.user_avatar = ctk.CTkImage(light_image=user_img, dark_image=user_img, size=(40, 40))
            
            
            mimikyu_path = self.db.get_setting("bot_avatar_path", "assets/mimikyu_avatar.png")
            if not os.path.exists(mimikyu_path):
                Image.new('RGB', (40, 40), color='#00d4ff').save(mimikyu_path)
            
            mimikyu_img = Image.open(mimikyu_path).resize((40, 40), Image.Resampling.LANCZOS)
            self.mimikyu_avatar = ctk.CTkImage(light_image=mimikyu_img, dark_image=mimikyu_img, size=(40, 40))
            
            
            header_img = Image.open(avatar_path).resize((50, 50), Image.Resampling.LANCZOS)
            self.avatar_image = ctk.CTkImage(light_image=header_img, dark_image=header_img, size=(50, 50))
            
        except Exception as e:
            print(f"Erreur chargement avatars: {e}")
            self.user_avatar = None
            self.mimikyu_avatar = None
            self.avatar_image = None

    def create_widgets(self):
        
        header_frame = ctk.CTkFrame(self.root, height=80, fg_color="#1f538d")
        header_frame.pack(fill="x", padx=10, pady=10)
        header_frame.pack_propagate(False)
        
        self.avatar_button = ctk.CTkButton(header_frame, 
                                         image=self.avatar_image if self.avatar_image else None,
                                         text="" if self.avatar_image else "👤",
                                         width=60, height=60,
                                         command=self.change_user_avatar)
        self.avatar_button.pack(side="left", padx=15, pady=10)
        
        info_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, pady=10)
        
        name_label = ctk.CTkLabel(info_frame, text="MiMiKyU", 
                                font=ctk.CTkFont(size=20, weight="bold"),
                                text_color="white")
        name_label.pack(anchor="w")
        
        status_label = ctk.CTkLabel(info_frame, text="< en ligne >", 
                                  font=ctk.CTkFont(size=12),
                                  text_color="#00ff00")
        status_label.pack(anchor="w")
        
        settings_btn = ctk.CTkButton(header_frame, text="⚙️", width=40, height=40,
                                   command=self.show_ai_settings)
        settings_btn.pack(side="right", padx=15, pady=10)
        
        self.chat_frame = ctk.CTkScrollableFrame(self.root)
        self.chat_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        input_frame = ctk.CTkFrame(self.root, height=70)
        input_frame.pack(fill="x", padx=10, pady=10)
        input_frame.pack_propagate(False)
        
        self.message_entry = ctk.CTkEntry(input_frame, placeholder_text="Écris ton message...",
                                        font=ctk.CTkFont(size=12))
        self.message_entry.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=15)
        self.message_entry.bind('<Return>', self.send_message)
        
        send_button = ctk.CTkButton(input_frame, text="Envoyer", width=80,
                                  command=self.send_message)
        send_button.pack(side="right", padx=(5, 10), pady=15)
        
        menu_frame = ctk.CTkFrame(self.root, height=50)
        menu_frame.pack(fill="x", padx=10, pady=(0, 10))
        menu_frame.pack_propagate(False)
        
        buttons_data = [
            ("📋 Tâches", self.show_tasks),
            ("📅 Agenda", self.show_agenda),
            ("📁 Fichiers", self.show_file_vault),
            ("🧠 Mémoire", self.show_memory)
        ]
        
        for text, command in buttons_data:
            btn = ctk.CTkButton(menu_frame, text=text, width=120, height=30,
                              command=command)
            btn.pack(side="left", padx=5, pady=10)
    
    def add_message_to_chat(self, sender, message):
        is_mimikyu = (sender == "Mimikyu")
        avatar = self.mimikyu_avatar if is_mimikyu else self.user_avatar
        
        bubble = MessageBubble(self.chat_frame, sender, message, is_mimikyu, avatar)
        bubble.pack(fill="x", padx=10, pady=5)
        
        self.root.after(100, lambda: self.chat_frame._parent_canvas.yview_moveto(1.0))
    
    def send_message(self, event=None):
        user_message = self.message_entry.get().strip()
        if not user_message:
            return
        
        self.add_message_to_chat("Toi", user_message)
        self.db.save_message("User", user_message)
        self.message_entry.delete(0, 'end')
        
        self.is_typing = True
        self.show_typing_animation()
        threading.Thread(target=self.get_mimikyu_response, args=(user_message,), daemon=True).start()
    
    def show_typing_animation(self):
        if hasattr(self, 'typing_bubble'):
            self.typing_bubble.destroy()
        
        self.typing_bubble = MessageBubble(self.chat_frame, "Mimikyu", "écrit...", True, self.mimikyu_avatar)
        self.typing_bubble.pack(fill="x", padx=10, pady=5)
        self.root.after(100, lambda: self.chat_frame._parent_canvas.yview_moveto(1.0))
    
    def clear_typing_animation(self):
        if hasattr(self, 'typing_bubble'):
            self.typing_bubble.destroy()
    
    def get_mimikyu_response(self, user_message):
        try:
            response = self.ai.generate_response(user_message)
            self.is_typing = False
            self.root.after(10, lambda: self.display_mimikyu_response(response))
        except Exception as e:
            self.is_typing = False
            error_msg = f"omg, gros bug! T_T ({str(e)})"
            self.root.after(10, lambda: self.display_mimikyu_response(error_msg))
    
    def display_mimikyu_response(self, response):
        self.clear_typing_animation()
        self.add_message_to_chat("Mimikyu", response)
        self.db.save_message("Mimikyu", response)
    
    def load_chat_history(self):
        messages = self.db.get_recent_messages(30)
        if not messages:
            welcome = "salut! c'est mimikyu! prêt à chatter? B-)"
            self.add_message_to_chat("Mimikyu", welcome)
            self.db.save_message("Mimikyu", welcome)
        else:
            for sender, content in messages:
                self.add_message_to_chat(sender, content)
    
    def show_ai_settings(self):
        settings_window = ctk.CTkToplevel(self.root)
        settings_window.title("Configuration IA")
        settings_window.geometry("500x400")
        
        title_label = ctk.CTkLabel(settings_window, text="Configuration Gemini", 
                                 font=ctk.CTkFont(size=18, weight="bold"))
        title_label.pack(pady=20)
        
        api_frame = ctk.CTkFrame(settings_window)
        api_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(api_frame, text="Clé API Google Gemini:",
                   font=ctk.CTkFont(size=14)).pack(pady=10)
        
        self.api_entry = ctk.CTkEntry(api_frame, width=400, show="*")
        self.api_entry.pack(pady=10)
        self.api_entry.insert(0, self.ai.api_key)
        
        status_text = "Statut: OK! B-)" if self.ai.model else "Statut: pas de clé! >_>"
        self.status_label = ctk.CTkLabel(settings_window, text=status_text,
                                       font=ctk.CTkFont(size=12, weight="bold"))
        self.status_label.pack(pady=10)
        
        btn_frame = ctk.CTkFrame(settings_window, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        save_btn = ctk.CTkButton(btn_frame, text="Sauver", 
                               command=lambda: self.save_ai_settings(settings_window))
        save_btn.pack(side="left", padx=10)
        
        test_btn = ctk.CTkButton(btn_frame, text="Test!", 
                               command=self.test_ai_connection)
        test_btn.pack(side="left", padx=10)
        
        avatar_btn = ctk.CTkButton(settings_window, text="Changer avatar utilisateur",
                                 command=self.change_user_avatar)
        avatar_btn.pack(pady=10)
        
        bot_avatar_btn = ctk.CTkButton(settings_window, text="Changer avatar Mimikyu",
                                     command=self.change_bot_avatar)
        bot_avatar_btn.pack(pady=5)

    def save_ai_settings(self, window):
        api_key = self.api_entry.get().strip()
        self.ai.set_api_key(api_key)
        messagebox.showinfo("Succès", "Clé API sauvegardée!")
        status_text = "Statut: OK! B-)" if self.ai.model else "Statut: pas de clé! >_>"
        self.status_label.configure(text=status_text)
        window.destroy()
    
    def test_ai_connection(self):
        if not self.ai.model:
            messagebox.showerror("Erreur", "L'API n'est pas configurée. Entre une clé valide!")
            return
        threading.Thread(target=self._test_ai, daemon=True).start()

    def _test_ai(self):
        try:
            response = self.ai.generate_response("test")
            messagebox.showinfo("Test", f"Connexion OK! Réponse: {response[:60]}...")
        except Exception as e:
            messagebox.showerror("Erreur", f"Problème de connexion: {str(e)}")

    def change_user_avatar(self):
        file_path = filedialog.askopenfilename(
            title="Choisis ton nouvel avatar!",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if file_path:
            self.db.save_setting("avatar_path", file_path)
            self.load_avatars()
            self.avatar_button.configure(image=self.avatar_image)
            messagebox.showinfo("Succès", "Ton nouvel avatar est configuré!")

    def change_bot_avatar(self):
        file_path = filedialog.askopenfilename(
            title="Choisis un nouvel avatar pour Mimikyu!",
            filetypes=[("Images", "*.png *.jpg *.jpeg")]
        )
        if file_path:
            self.db.save_setting("bot_avatar_path", file_path)
            self.load_avatars()
            messagebox.showinfo("Succès", "L'avatar de Mimikyu a été changé!")

    def show_tasks(self):
        tasks_window = ctk.CTkToplevel(self.root)
        tasks_window.title("Gestionnaire de Tâches")
        tasks_window.geometry("600x500")
        
        title = ctk.CTkLabel(tasks_window, text="📋 Mes Tâches", 
                           font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=20)
        
        self.tasks_frame = ctk.CTkScrollableFrame(tasks_window)
        self.tasks_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        btn_frame = ctk.CTkFrame(tasks_window, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        add_btn = ctk.CTkButton(btn_frame, text="➕ Ajouter", command=self.add_task)
        add_btn.pack(side="left", padx=10)
        
        self.load_tasks()

    def load_tasks(self):
        for widget in self.tasks_frame.winfo_children():
            widget.destroy()
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, status FROM tasks ORDER BY created_date DESC")
        
        for task_id, title, status in cursor.fetchall():
            task_frame = ctk.CTkFrame(self.tasks_frame)
            task_frame.pack(fill="x", pady=5)
            
            status_icon = "✅" if status == "completed" else "🔲"
            task_text = f"{status_icon} {title}"
            
            task_label = ctk.CTkLabel(task_frame, text=task_text, 
                                    font=ctk.CTkFont(size=12))
            task_label.pack(side="left", padx=10, pady=10)
            
            if status != "completed":
                complete_btn = ctk.CTkButton(task_frame, text="✓", width=30,
                                           command=lambda tid=task_id: self.complete_task(tid))
                complete_btn.pack(side="right", padx=5, pady=5)
            
            delete_btn = ctk.CTkButton(task_frame, text="🗑️", width=30,
                                     command=lambda tid=task_id: self.delete_task(tid))
            delete_btn.pack(side="right", padx=5, pady=5)
        
        conn.close()

    def add_task(self):
        dialog = ctk.CTkInputDialog(text="Titre de la tâche:", title="Nouvelle Tâche")
        title = dialog.get_input()
        
        if title:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tasks (title, created_date) VALUES (?, ?)", 
                         (title, datetime.datetime.now().isoformat()))
            conn.commit()
            conn.close()
            self.load_tasks()

    def complete_task(self, task_id):
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        self.load_tasks()

    def delete_task(self, task_id):
        if messagebox.askyesno("Confirmation", "Sûr de vouloir supprimer?"):
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            conn.close()
            self.load_tasks()

    def show_agenda(self):
        agenda_window = ctk.CTkToplevel(self.root)
        agenda_window.title("Agenda")
        agenda_window.geometry("600x500")
        
        title = ctk.CTkLabel(agenda_window, text="📅 Mon Agenda", 
                           font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=20)
        
        self.events_frame = ctk.CTkScrollableFrame(agenda_window)
        self.events_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        btn_frame = ctk.CTkFrame(agenda_window, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        add_event_btn = ctk.CTkButton(btn_frame, text="➕ Ajouter Événement", 
                                    command=self.add_event)
        add_event_btn.pack()
        
        self.load_events()

    def load_events(self):
        for widget in self.events_frame.winfo_children():
            widget.destroy()
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, event_date, title, description FROM events ORDER BY event_date ASC")
        
        for event_id, date, title, desc in cursor.fetchall():
            event_frame = ctk.CTkFrame(self.events_frame)
            event_frame.pack(fill="x", pady=5)
            
            event_text = f"📅 {date} - {title}"
            if desc:
                event_text += f"\n   {desc}"
            
            event_label = ctk.CTkLabel(event_frame, text=event_text, 
                                     font=ctk.CTkFont(size=12), justify="left")
            event_label.pack(side="left", padx=10, pady=10)
            
            delete_btn = ctk.CTkButton(event_frame, text="🗑️", width=30,
                                     command=lambda eid=event_id: self.delete_event(eid))
            delete_btn.pack(side="right", padx=5, pady=5)
        
        conn.close()

    def add_event(self):
        event_window = ctk.CTkToplevel(self.root)
        event_window.title("Nouvel Événement")
        event_window.geometry("400x300")
        
        ctk.CTkLabel(event_window, text="Date (YYYY-MM-DD):", 
                   font=ctk.CTkFont(size=12)).pack(pady=10)
        date_entry = ctk.CTkEntry(event_window)
        date_entry.pack(pady=5)
        
        ctk.CTkLabel(event_window, text="Titre:", 
                   font=ctk.CTkFont(size=12)).pack(pady=10)
        title_entry = ctk.CTkEntry(event_window)
        title_entry.pack(pady=5)
        
        ctk.CTkLabel(event_window, text="Description:", 
                   font=ctk.CTkFont(size=12)).pack(pady=10)
        desc_entry = ctk.CTkEntry(event_window)
        desc_entry.pack(pady=5)
        
        def save_event():
            date = date_entry.get()
            title = title_entry.get()
            desc = desc_entry.get()
            
            if date and title:
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO events (event_date, title, description) VALUES (?, ?, ?)", 
                             (date, title, desc))
                conn.commit()
                conn.close()
                self.load_events()
                event_window.destroy()
        
        save_btn = ctk.CTkButton(event_window, text="Sauver", command=save_event)
        save_btn.pack(pady=20)

    def delete_event(self, event_id):
        if messagebox.askyesno("Confirmation", "Sûr de vouloir supprimer cet événement?"):
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
            conn.commit()
            conn.close()
            self.load_events()

    def show_file_vault(self):
        password_hash = self.db.get_setting("vault_password_hash")
        if not password_hash:
            dialog = ctk.CTkInputDialog(text="Créé un mot de passe pour le coffre-fort:", 
                                      title="Nouveau mot de passe")
            new_password = dialog.get_input()
            if new_password:
                hashed = hashlib.sha256(new_password.encode()).hexdigest()
                self.db.save_setting("vault_password_hash", hashed)
                self.open_vault_window()
        else:
            dialog = ctk.CTkInputDialog(text="Entre ton mot de passe:", 
                                      title="Mot de passe requis")
            password = dialog.get_input()
            if password and hashlib.sha256(password.encode()).hexdigest() == password_hash:
                self.open_vault_window()
            elif password:
                messagebox.showerror("Erreur", "Mot de passe incorrect!")

    def open_vault_window(self):
        vault_window = ctk.CTkToplevel(self.root)
        vault_window.title("Coffre-fort")
        vault_window.geometry("600x500")
        
        title = ctk.CTkLabel(vault_window, text="🔒 Coffre-fort de fichiers", 
                           font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=20)
        
        self.vault_path = "vault_files"
        if not os.path.exists(self.vault_path):
            os.makedirs(self.vault_path)

        self.files_frame = ctk.CTkScrollableFrame(vault_window)
        self.files_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        btn_frame = ctk.CTkFrame(vault_window, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        add_file_btn = ctk.CTkButton(btn_frame, text="📁 Ajouter Fichier", 
                                   command=self.add_file_to_vault)
        add_file_btn.pack(side="left", padx=10)
        
        self.load_vault_files()

    def load_vault_files(self):
        for widget in self.files_frame.winfo_children():
            widget.destroy()
        
        for filename in os.listdir(self.vault_path):
            file_frame = ctk.CTkFrame(self.files_frame)
            file_frame.pack(fill="x", pady=5)
            
            file_label = ctk.CTkLabel(file_frame, text=f"📄 {filename}", 
                                    font=ctk.CTkFont(size=12))
            file_label.pack(side="left", padx=10, pady=10)
            
            download_btn = ctk.CTkButton(file_frame, text="⬇️", width=30,
                                       command=lambda f=filename: self.download_file_from_vault(f))
            download_btn.pack(side="right", padx=5, pady=5)
            
            delete_btn = ctk.CTkButton(file_frame, text="🗑️", width=30,
                                     command=lambda f=filename: self.delete_file_from_vault(f))
            delete_btn.pack(side="right", padx=5, pady=5)

    def add_file_to_vault(self):
        filepath = filedialog.askopenfilename(title="Choisir un fichier à sécuriser")
        if filepath:
            try:
                shutil.copy(filepath, self.vault_path)
                self.load_vault_files()
                messagebox.showinfo("Succès", "Fichier ajouté au coffre-fort!")
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible d'ajouter le fichier: {e}")

    def download_file_from_vault(self, filename):
        src = os.path.join(self.vault_path, filename)
        dest = filedialog.asksaveasfilename(initialfile=filename)
        if dest:
            try:
                shutil.copy(src, dest)
                messagebox.showinfo("Succès", "Fichier téléchargé!")
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de télécharger: {e}")

    def delete_file_from_vault(self, filename):
        if messagebox.askyesno("Confirmation", f"Supprimer {filename}?"):
            try:
                os.remove(os.path.join(self.vault_path, filename))
                self.load_vault_files()
                messagebox.showinfo("Succès", "Fichier supprimé!")
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de supprimer: {e}")

    def show_memory(self):
        memory_window = ctk.CTkToplevel(self.root)
        memory_window.title("Mémoire")
        memory_window.geometry("600x500")
        
        title = ctk.CTkLabel(memory_window, text="🧠 Ce que j'ai en tête", 
                           font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=20)
        
        history_frame = ctk.CTkFrame(memory_window)
        history_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        subtitle = ctk.CTkLabel(history_frame, text="Nos derniers chats:", 
                              font=ctk.CTkFont(size=14, weight="bold"))
        subtitle.pack(pady=10)
        
        history_text = ctk.CTkTextbox(history_frame, width=500, height=300)
        history_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        messages = self.db.get_recent_messages(50)
        for sender, content in messages:
            history_text.insert("end", f"- {sender}: {content}\n\n")
        
        history_text.configure(state="disabled")

def main():
    root = ctk.CTk()
    app = MimikyuApp(root)
    
    root.mainloop()

if __name__ == "__main__":
    main()


