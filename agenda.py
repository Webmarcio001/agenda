#!/usr/bin/env python3
"""
Agenda simples: contatos + compromissos
Salva os dados em SQLite (arquivo: agenda.db)
"""
import sqlite3
from datetime import datetime
import csv
import os

DB_FILE = "agenda.db"
DATE_FMT = "%Y-%m-%d"
DATETIME_FMT = "%Y-%m-%d %H:%M"

def get_conn():
    return sqlite3.connect(DB_FILE)

def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            notes TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER,
            title TEXT NOT NULL,
            start DATETIME NOT NULL,
            end DATETIME,
            location TEXT,
            notes TEXT,
            FOREIGN KEY(contact_id) REFERENCES contacts(id)
        )
        """)
        conn.commit()

# ---------- Helpers ----------
def input_nonempty(prompt):
    s = input(prompt).strip()
    while not s:
        print("Por favor, não deixe vazio.")
        s = input(prompt).strip()
    return s

def parse_datetime(s):
    try:
        return datetime.strptime(s, DATETIME_FMT)
    except ValueError:
        raise ValueError(f"Formato inválido. Use: {DATETIME_FMT}")

def parse_date(s):
    try:
        return datetime.strptime(s, DATE_FMT).date()
    except ValueError:
        raise ValueError(f"Formato inválido. Use: {DATE_FMT}")

def print_row(row):
    print(" | ".join(f"{k}: {v}" for k,v in row.items()))

# ---------- Contacts ----------
def add_contact():
    name = input_nonempty("Nome: ")
    phone = input("Telefone (opcional): ").strip()
    email = input("Email (opcional): ").strip()
    notes = input("Observações (opcional): ").strip()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO contacts(name,phone,email,notes) VALUES (?,?,?,?)",
                    (name, phone, email, notes))
        conn.commit()
    print("Contato salvo.")

def list_contacts():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id,name,phone,email,notes FROM contacts ORDER BY name")
        rows = cur.fetchall()
        if not rows:
            print("Nenhum contato.")
            return
        print(f"{'ID':<4} {'NOME':<30} {'TEL':<15} {'EMAIL':<25}")
        print("-"*80)
        for r in rows:
            print(f"{r[0]:<4} {r[1]:<30} {r[2] or '':<15} {r[3] or '':<25}")

def find_contacts_by_name():
    q = input_nonempty("Pesquisar nome (parte): ").lower()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id,name,phone,email,notes FROM contacts WHERE lower(name) LIKE ? ORDER BY name", (f"%{q}%",))
        rows = cur.fetchall()
        if not rows:
            print("Nenhum contato encontrado.")
            return
        for r in rows:
            print("-"*40)
            print(f"ID: {r[0]}\nNome: {r[1]}\nTelefone: {r[2]}\nEmail: {r[3]}\nNotas: {r[4]}")

def edit_contact():
    list_contacts()
    try:
        cid = int(input_nonempty("ID do contato para editar: "))
    except ValueError:
        print("ID inválido.")
        return
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id,name,phone,email,notes FROM contacts WHERE id=?", (cid,))
        row = cur.fetchone()
        if not row:
            print("Contato não encontrado.")
            return
        print("Deixe em branco para manter o valor atual.")
        name = input(f"Nome [{row[1]}]: ").strip() or row[1]
        phone = input(f"Telefone [{row[2] or ''}]: ").strip() or row[2]
        email = input(f"Email [{row[3] or ''}]: ").strip() or row[3]
        notes = input(f"Notas [{row[4] or ''}]: ").strip() or row[4]
        cur.execute("UPDATE contacts SET name=?,phone=?,email=?,notes=? WHERE id=?",
                    (name, phone, email, notes, cid))
        conn.commit()
        print("Contato atualizado.")

def delete_contact():
    list_contacts()
    try:
        cid = int(input_nonempty("ID do contato para apagar: "))
    except ValueError:
        print("ID inválido.")
        return
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM contacts WHERE id=?", (cid,))
        cur.execute("DELETE FROM appointments WHERE contact_id=?", (cid,))  # opcional: apagar compromissos vinculados
        conn.commit()
    print("Contato (e compromissos vinculados) apagados.")

# ---------- Appointments ----------
def add_appointment():
    title = input_nonempty("Título do compromisso: ")
    contact = None
    if input("Vincular a um contato? (s/n): ").strip().lower() == 's':
        list_contacts()
        try:
            cid = int(input_nonempty("ID do contato: "))
            contact = cid
        except ValueError:
            print("ID inválido. Será criado sem contato vinculado.")
            contact = None
    start_s = input_nonempty(f"Data e hora de início ({DATETIME_FMT}): ")
    try:
        start_dt = parse_datetime(start_s)
    except ValueError as e:
        print(e); return
    end_input = input(f"Data e hora de término ({DATETIME_FMT}) (opcional): ").strip()
    end_dt = None
    if end_input:
        try:
            end_dt = parse_datetime(end_input)
        except ValueError as e:
            print(e); return
    location = input("Local (opcional): ").strip()
    notes = input("Notas (opcional): ").strip()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO appointments(contact_id,title,start,end,location,notes)
            VALUES (?,?,?,?,?,?)
        """, (contact, title, start_dt.strftime(DATETIME_FMT), end_dt.strftime(DATETIME_FMT) if end_dt else None, location, notes))
        conn.commit()
    print("Compromisso salvo.")

def list_appointments(show_all=True):
    with get_conn() as conn:
        cur = conn.cursor()
        if show_all:
            cur.execute("""
                SELECT a.id, a.title, a.start, a.end, a.location, c.name
                FROM appointments a
                LEFT JOIN contacts c ON a.contact_id = c.id
                ORDER BY a.start
            """)
        else:
            today = datetime.now().date().isoformat()
            cur.execute("""
                SELECT a.id, a.title, a.start, a.end, a.location, c.name
                FROM appointments a
                LEFT JOIN contacts c ON a.contact_id = c.id
                WHERE date(a.start) = ?
                ORDER BY a.start
            """, (today,))
        rows = cur.fetchall()
        if not rows:
            print("Nenhum compromisso encontrado.")
            return
        print(f"{'ID':<4} {'INÍCIO':<16} {'FIM':<16} {'TÍTULO':<30} {'CONTATO':<20}")
        print("-"*100)
        for r in rows:
            print(f"{r[0]:<4} {r[2] or '':<16} {r[3] or '':<16} {r[1]:<30} {r[5] or '':<20}")

def find_appointments_by_date():
    d = input_nonempty(f"Data ({DATE_FMT}): ")
    try:
        date_obj = parse_date(d)
    except ValueError as e:
        print(e); return
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT a.id,a.title,a.start,a.end,a.location,c.name
            FROM appointments a
            LEFT JOIN contacts c ON a.contact_id = c.id
            WHERE date(a.start)=?
            ORDER BY a.start
        """, (date_obj.isoformat(),))
        rows = cur.fetchall()
        if not rows:
            print("Nenhum compromisso nessa data.")
            return
        for r in rows:
            print("-"*40)
            print(f"ID: {r[0]}\nTítulo: {r[1]}\nInício: {r[2]}\nTérmino: {r[3]}\nLocal: {r[4]}\nContato: {r[5]}")

def edit_appointment():
    list_appointments()
    try:
        aid = int(input_nonempty("ID do compromisso para editar: "))
    except ValueError:
        print("ID inválido.")
        return
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id,contact_id,title,start,end,location,notes FROM appointments WHERE id=?", (aid,))
        row = cur.fetchone()
        if not row:
            print("Compromisso não encontrado.")
            return
        print("Deixe em branco para manter o valor atual.")
        title = input(f"Título [{row[2]}]: ").strip() or row[2]
        # trocar contato?
        if input("Mudar contato vinculado? (s/n): ").strip().lower() == 's':
            list_contacts()
            try:
                contact_id = int(input("Novo ID do contato (ou 0 para nenhum): "))
                contact_id = contact_id if contact_id != 0 else None
            except ValueError:
                contact_id = row[1]
        else:
            contact_id = row[1]
        start_in = input(f"Início [{row[3]}] ({DATETIME_FMT}): ").strip()
        if start_in:
            try:
                start = parse_datetime(start_in).strftime(DATETIME_FMT)
            except ValueError as e:
                print(e); return
        else:
            start = row[3]
        end_in = input(f"Término [{row[4] or ''}] ({DATETIME_FMT}): ").strip()
        if end_in:
            try:
                end = parse_datetime(end_in).strftime(DATETIME_FMT)
            except ValueError as e:
                print(e); return
        else:
            end = row[4]
        location = input(f"Local [{row[5] or ''}]: ").strip() or row[5]
        notes = input(f"Notas [{row[6] or ''}]: ").strip() or row[6]
        cur.execute("""
            UPDATE appointments SET contact_id=?,title=?,start=?,end=?,location=?,notes=? WHERE id=?
        """, (contact_id, title, start, end, location, notes, aid))
        conn.commit()
        print("Compromisso atualizado.")

def delete_appointment():
    list_appointments()
    try:
        aid = int(input_nonempty("ID do compromisso para apagar: "))
    except ValueError:
        print("ID inválido.")
        return
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM appointments WHERE id=?", (aid,))
        conn.commit()
    print("Compromisso apagado.")

# ---------- Export ----------
def export_contacts_csv(path="contacts_export.csv"):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id,name,phone,email,notes FROM contacts")
        rows = cur.fetchall()
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id","name","phone","email","notes"])
        writer.writerows(rows)
    print(f"Contatos exportados para {path}.")

def export_appointments_csv(path="appointments_export.csv"):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT a.id,a.title,a.start,a.end,a.location,c.name
            FROM appointments a
            LEFT JOIN contacts c ON a.contact_id=c.id
        """)
        rows = cur.fetchall()
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id","title","start","end","location","contact_name"])
        writer.writerows(rows)
    print(f"Compromissos exportados para {path}.")

# ---------- Main menu ----------
def main_menu():
    menu = """
=== AGENDA (contatos + compromissos) ===
1  - Adicionar contato
2  - Listar contatos
3  - Buscar contato por nome
4  - Editar contato
5  - Apagar contato
6  - Adicionar compromisso
7  - Listar todos compromissos
8  - Listar compromissos de hoje
9  - Buscar compromissos por data
10 - Editar compromisso
11 - Apagar compromisso
12 - Exportar contatos CSV
13 - Exportar compromissos CSV
0  - Sair
Escolha: """
    while True:
        try:
            choice = input(menu).strip()
            if choice == "1": add_contact()
            elif choice == "2": list_contacts()
            elif choice == "3": find_contacts_by_name()
            elif choice == "4": edit_contact()
            elif choice == "5": delete_contact()
            elif choice == "6": add_appointment()
            elif choice == "7": list_appointments(show_all=True)
            elif choice == "8": list_appointments(show_all=False)
            elif choice == "9": find_appointments_by_date()
            elif choice == "10": edit_appointment()
            elif choice == "11": delete_appointment()
            elif choice == "12": export_contacts_csv()
            elif choice == "13": export_appointments_csv()
            elif choice == "0":
                print("Tchau!")
                break
            else:
                print("Opção inválida.")
        except KeyboardInterrupt:
            print("\nInterrompido. Voltando ao menu.")
        except Exception as e:
            print("Erro:", e)

if __name__ == "__main__":
    init_db()
    main_menu()
