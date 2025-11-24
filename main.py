import configparser
import re
import pyodbc
import xml.etree.ElementTree as ET
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import StoricoModificheFatture, Base
from datetime import datetime, date
import json
import os

# Carica la configurazione
config = configparser.ConfigParser()
config.read('config.ini')

CHECKPOINT_FILE = 'checkpoint.json'

# Connessione SQL Server
sqlserver_conf = config['SQLSERVER']
sqlserver_conn_str = (
    f"mssql+pyodbc://{sqlserver_conf['username']}:{sqlserver_conf['password']}@"
    f"{sqlserver_conf['server']}/{sqlserver_conf['database']}?driver=ODBC+Driver+17+for+SQL+Server"
)
engine = create_engine(sqlserver_conn_str)
Session = sessionmaker(bind=engine)

def extract_importo(note):
    """
    Estrae l'ultimo importo numerico dal campo note.
    Accetta sia punto che virgola come separatore decimale, fino a 3 decimali.
    Restituisce il valore come float troncato a due decimali, oppure None se non trovato.
    """

    if not note:
        return None
    
    # Cerca numeri con separatore decimale punto o virgola, 1-3 decimali
    match = re.findall(r"\b\d{1,8}(?:[\.,]\d{1,3})?\b", note)

    if match:
        # Sostituisci la virgola con il punto per la conversione
        val = match[-1].replace(',', '.')
        try:
            # Tronca a due decimali. Es. 12.340 -> 12.34
            return float(f"{float(val):.2f}")
        except Exception:
            return None
    return None

def extract_importo_from_xml(xml_content):
    """
    Estrae l'importo effettivo della fattura elettronica dal file XML.
    Logica:
    - Prende il valore di <ImportoTotaleDocumento> (importo totale della fattura)
    - Sottrae la somma delle righe <DettaglioLinee> che hanno <Descrizione> contenente 'Spesa Materiale consumo'.
    - Sottrae anche l'IVA relativa a queste righe (se presente), per replicare il calcolo manuale dell'utente.
    - Restituisce il risultato arrotondato a due decimali.
    Parametri:
        xml_content: stringa XML (o bytes) della fattura elettronica
    Ritorna:
        float: importo effettivo (ImportoTotaleDocumento - somma Spesa Materiale consumo - IVA relativa), oppure None se errore
    """
    if not xml_content or not isinstance(xml_content, (str, bytes)):
        return None
    try:
        # Se il contenuto è bytes, decodifica in stringa
        if isinstance(xml_content, bytes):
            xml_content = xml_content.decode('utf-8', errors='ignore')
        root = ET.fromstring(xml_content)
        
        # Cerca il tag <ImportoTotaleDocumento> (importo totale della fattura)
        importo_totale = root.find('.//ImportoTotaleDocumento')
        importo_totale_val = float(importo_totale.text) if importo_totale is not None else 0.0
        
        # Cerca tutte le righe <DettaglioLinee> e somma i valori di <PrezzoTotale>
        # solo se la <Descrizione> contiene 'Spesa Materiale consumo'
        spesa_materiale = 0.0
        iva_materiale = 0.0
        for dettaglio in root.findall('.//DettaglioLinee'):
            descrizione = dettaglio.find('Descrizione')
            if descrizione is not None and 'Spesa Materiale consumo' in descrizione.text:
                prezzo_totale = dettaglio.find('PrezzoTotale')
                aliquota_iva = dettaglio.find('AliquotaIVA')
                if prezzo_totale is not None:
                    valore = float(prezzo_totale.text)
                    spesa_materiale += valore
                    # Calcola l'IVA di questa riga se presente
                    if aliquota_iva is not None:
                        try:
                            iva = valore * float(aliquota_iva.text) / 100.0
                            iva_materiale += iva
                        except Exception:
                            pass
        # Calcola l'importo effettivo: totale - spese materiale consumo - iva materiale consumo
        risultato = round(importo_totale_val - spesa_materiale - iva_materiale, 2)
        print(f"[DEBUG XML] ImportoTotale={importo_totale_val}, SpesaMateriale={spesa_materiale}, IVA_Materiale={iva_materiale}, Risultato={risultato}")
        return risultato
    except Exception as e:
        print(f"[WARNING] Errore nel parsing XML: {e}")
        return None

def get_fattura_data(odbc_conn_str, id_reg_pd):
    """
    Recupera i dati della fattura (data trasmissione e importo dal XML) dato l'id_reg_pd
    """
    if not id_reg_pd or id_reg_pd <= 0:
        return None, None
    
    # Carica la query dal file SQL
    query_fattura = open('Query Recupero Fattura.sql', encoding='utf-8').read()
    
    try:
        with pyodbc.connect(odbc_conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute(query_fattura, id_reg_pd)
            row = cursor.fetchone()
            if row:
                # La query restituisce: id_reg_pd, fine_trasmissione, nome_file, file_xml_vendita
                data_trasmissione = row[1]  # fine_trasmissione (datetime)
                xml_content = row[3]  # file_xml_vendita (XML string)
                print(f"[DEBUG] id_reg_pd {id_reg_pd}: data_trasmissione={data_trasmissione}")
                if xml_content is None:
                    print(f"[DEBUG] id_reg_pd {id_reg_pd}: xml_content è None!")
                elif isinstance(xml_content, bytes):
                    print(f"[DEBUG] id_reg_pd {id_reg_pd}: xml_content è bytes, len={len(xml_content)}")
                elif isinstance(xml_content, str):
                    print(f"[DEBUG] id_reg_pd {id_reg_pd}: xml_content è str, len={len(xml_content)}")
                else:
                    print(f"[DEBUG] id_reg_pd {id_reg_pd}: xml_content tipo sconosciuto: {type(xml_content)}")
                # Mostra un estratto dei primi 200 caratteri
                if xml_content:
                    anteprima = xml_content[:200] if isinstance(xml_content, (str, bytes)) else str(xml_content)[:200]
                    print(f"[DEBUG] id_reg_pd {id_reg_pd}: xml_content anteprima: {anteprima}")
                importo_fattura = extract_importo_from_xml(xml_content)
                print(f"[DEBUG] id_reg_pd {id_reg_pd}: importo_fattura={importo_fattura}")
                return data_trasmissione, importo_fattura
            else:
                print(f"[DEBUG] id_reg_pd {id_reg_pd}: Nessun risultato dalla query (fattura non trasmessa?)")
    except Exception as e:
        print(f"[WARNING] Errore nel recupero dati fattura per id_reg_pd {id_reg_pd}: {e}")
    
    return None, None

# Funzione per estrarre dati dal DNS e connettersi a Infinity
def estrai_dati_da_dsn(dsn_str):
    dsn_parts = dsn_str.split('^')
    azienda = dsn_parts[0] if len(dsn_parts) > 0 else ''
    dsn_name = dsn_parts[1] if len(dsn_parts) > 1 else ''
    username_source = dsn_parts[2] if len(dsn_parts) > 2 else ''
    password_source = dsn_parts[3] if len(dsn_parts) > 3 else ''
    odbc_conn_str = f"DSN={dsn_name};UID={username_source};PWD={password_source}"
    print(f"\n[INFO] Connessione a sorgente azienda: {azienda} (DSN: {dsn_name}) ...")
    query = open('Query Check Log Commesse.sql', encoding='utf-8').read()
    
    results = []
    with pyodbc.connect(odbc_conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        print(f"[INFO] Trovati {len(rows)} record per azienda {azienda}.")
        for row in rows:
            results.append((azienda, odbc_conn_str, dict(zip(columns, row))))
    
    return results



def main():

    """
    Script principale per il controllo delle modifiche importi commesse.

    Funzionalità:
    - Estrae i log delle modifiche da Infinity tramite query SQL.
    - Per ogni log, recupera la data di trasmissione e l'importo fattura dal file XML associato.
    - Salva nel database tutti i dati rilevanti, compresi importi log, importo fattura, targa, ecc.
    - Stampa dettagliate informazioni di debug per ogni step. 
    - Usa un checkpoint JSON per riprendere in caso di interruzione.

    Dipendenze: pyodbc, sqlalchemy, configparser
    Configurazione: vedi config.ini per parametri di connessione.
    """
    # Carica checkpoint se esiste
    checkpoint = {}
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f:
            checkpoint = json.load(f)
        print(f"[INFO] Checkpoint caricato: {checkpoint}")
    
    # Avvio script e creazione sessione DB
    print("[INFO] Avvio script di estrazione e salvataggio dati\n")
    session = Session()  # Crea una nuova sessione SQLAlchemy per il database
    source_conf = config['SOURCE_INFINITY']  # Legge la sezione di configurazione per le sorgenti Infinity
    dsn_list = [dsn.strip() for dsn in source_conf['dsn'].split(',') if dsn.strip()]  # Lista dei DSN configurati
    totale = 0  # Contatore dei record salvati

    # Ciclo su ogni DSN (azienda/sorgente)
    for dsn_str in dsn_list:
        azienda_name = dsn_str.split('^')[0]
        
        # Recupera l'ultimo id_documento processato per questa azienda
        last_id_documento = checkpoint.get(azienda_name, 0)
        
        print(f"[INFO] Inizio elaborazione per DSN: {dsn_str}")
        if last_id_documento > 0:
            print(f"[INFO] Ripresa da id_documento > {last_id_documento}")

        records = estrai_dati_da_dsn(dsn_str)  # Estrae tutti i log per questo DSN (azienda)
        print(f"[DEBUG] Numero record estratti da DSN {dsn_str}: {len(records)}")
        for idx, (azienda, odbc_conn_str, record) in enumerate(records):
            # Stampa info base su ogni record
            print(f"[DEBUG] [{idx+1}/{len(records)}] id_documento={record.get('id_documento')} id_reg_pd={record.get('id_reg_pd')}")
            
            # Salta record già processati (checkpoint)
            id_documento_current = record.get('id_documento')
            if id_documento_current <= last_id_documento:
                continue
            
            # Filtro anno in Python: CV dal 2024, altri dal 2025
            anno = record.get('anno')
            if azienda == 'CV':
                if anno is not None and int(anno) < 2024:
                    continue
            else:
                if anno is not None and int(anno) < 2025:
                    continue
            
            id_reg_pd = record.get('id_reg_pd')
            # Verifica che la commessa sia stata fatturata (id_reg_pd > 0)
            if not id_reg_pd or id_reg_pd <= 0:
                print(f"[DEBUG]   -> SKIP: id_reg_pd mancante o <= 0")
                continue
            # Recupera dati fattura (data trasmissione e importo fattura)
            data_trasmissione, importo_fattura = get_fattura_data(odbc_conn_str, id_reg_pd)
            if not data_trasmissione:
                print(f"[DEBUG]   -> SKIP: data_trasmissione non trovata per id_reg_pd={id_reg_pd}")
                continue
            data_modifica = record.get('data_modifica')
            # Funzione di utilità per convertire vari formati data in datetime
            def parse_data(val):
                if not val:
                    return None
                if isinstance(val, datetime):
                    return val
                s = str(val)
                try:
                    return datetime.fromisoformat(s)
                except Exception:
                    pass
                if s.isdigit() and len(s) == 8:
                    try:
                        return datetime.strptime(s, '%Y%m%d')
                    except Exception:
                        pass
                return None
            data_modifica = parse_data(data_modifica)
            data_trasmissione = parse_data(data_trasmissione)
            # Controlla validità delle date
            if not data_modifica:
                print(f"[DEBUG]   -> SKIP: data_modifica non valida: {record.get('data_modifica')}")
                continue
            if not data_trasmissione:
                print(f"[DEBUG]   -> SKIP: data_trasmissione non valida: {data_trasmissione}")
                continue
            if data_modifica >= data_trasmissione:
                print(f"[DEBUG]   -> SKIP: data_modifica >= data_trasmissione ({data_modifica} >= {data_trasmissione})")
                continue
            # Filtro anno in Python: CV dal 2024, altri dal 2025
            anno = record.get('anno')
            if azienda == 'CV':
                if anno is not None and int(anno) < 2024:
                    continue
            else:
                if anno is not None and int(anno) < 2025:
                    continue
            # Estrai importo log dalle note
            importo_log = extract_importo(record.get('note'))
            if importo_log is None:
                print(f"[DEBUG]   -> SKIP: importo_log non trovato nelle note")
                continue
            # Salva il record nel database
            print(f"[INFO] Salvo log per id_documento {record.get('id_documento')}, id_reg_pd {id_reg_pd}, azienda {azienda} | importo_log: {importo_log}")
            nuovo_record = StoricoModificheFatture(
                id_documento=record.get('id_documento'),
                anno=record.get('anno'),
                id_cliente=record.get('id_cliente'),
                tipo_doc=record.get('tipo_doc'),
                data_doc=record.get('data_doc'),
                num_doc=record.get('num_doc'),
                tipo_fattura=record.get('tipo_fattura'),
                data_fattura=record.get('data_fattura'),
                numero_fattura=record.get('numero_fattura'),
                tipo_pagamento=record.get('tipo_pagamento'),
                id_hst=record.get('id_hst'),
                nome_tabella=record.get('nome_tabella'),
                utente=record.get('utente'),
                tipo_operazione=record.get('tipo_operazione'),
                note=record.get('note'),
                data_modifica=data_modifica,
                azienda=azienda,
                importo_modifica=importo_log,
                importo_fattura=importo_fattura,
                id_reg_pd=id_reg_pd,
                data_trasmissione_fattura=data_trasmissione,
                targa=record.get('targa')
            )
            # Salta se il record è già presente (stesso id_documento, id_reg_pd, azienda, data_modifica)
            exists = session.query(StoricoModificheFatture).filter_by(
                id_documento=record.get('id_documento'),
                id_reg_pd=id_reg_pd,
                azienda=azienda,
                data_modifica=data_modifica
            ).first()
            if exists:
                print(f"[DEBUG]   -> SKIP: record già presente in DB (id_documento={record.get('id_documento')}, id_reg_pd={id_reg_pd}, azienda={azienda}, data_modifica={data_modifica})")
                continue
            session.add(nuovo_record)  # Aggiunge il record alla sessione
            session.commit()  # Commit immediato per ogni record
            totale += 1  # Incrementa il contatore dei record salvati
            
            # Aggiorna checkpoint dopo ogni record salvato
            checkpoint[azienda_name] = id_documento_current
            with open(CHECKPOINT_FILE, 'w') as f:
                json.dump(checkpoint, f, indent=2)
        
        # Azienda completata
        print(f"[INFO] Azienda {azienda_name} completata")

    session.close()  # Chiude la sessione del database
    
    # Rimuove il checkpoint alla fine (successo completo)
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        print(f"[INFO] Checkpoint rimosso: elaborazione completata")
    
    print(f"\n[INFO] Tutti i record ({totale}) sono stati inseriti con successo!")
    print("[INFO] Fine script\n")

if __name__ == '__main__':
    main()
