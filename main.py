import configparser
import re
import pyodbc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import StoricoModificheFatture, Base
from datetime import datetime, date

# Carica la configurazione
config = configparser.ConfigParser()
config.read('config.ini')

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

# Funzione per estrarre dati dal DNS e connettersi a Infinity
def estrai_dati_da_dsn(dsn_str):
    dsn_parts = dsn_str.split('^')
    azienda = dsn_parts[0] if len(dsn_parts) > 0 else ''
    dsn_name = dsn_parts[1] if len(dsn_parts) > 1 else ''
    username_source = dsn_parts[2] if len(dsn_parts) > 2 else ''
    password_source = dsn_parts[3] if len(dsn_parts) > 3 else ''
    odbc_conn_str = f"DSN={dsn_name};UID={username_source};PWD={password_source}"
    print(f"\n[INFO] Connessione a sorgente azienda: {azienda} (DSN: {dsn_name}) ...")
    query = open('Query Check Ladroni.sql', encoding='utf-8').read()
    with pyodbc.connect(odbc_conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        print(f"[INFO] Trovati {len(rows)} record per azienda {azienda}.")
        for row in rows:
            yield azienda, dict(zip(columns, row))




def main():

    print("[INFO] Avvio script di estrazione e salvataggio dati\n")
    session = Session()
    source_conf = config['SOURCE_INFINITY']
    dsn_list = [dsn.strip() for dsn in source_conf['dsn'].split(',') if dsn.strip()]
    totale = 0

    for dsn_str in dsn_list:
        print(f"[INFO] Inizio elaborazione per DSN: {dsn_str}")

        # Raggruppa tutti i record per id_documento per calcolare importi log
        records_per_doc = {}
        for azienda, record in estrai_dati_da_dsn(dsn_str):
            id_doc = record.get('id_documento')
            if id_doc not in records_per_doc:
                records_per_doc[id_doc] = []
            records_per_doc[id_doc].append((azienda, record))

        print(f"[INFO] Trovati {len(records_per_doc)} gruppi di documenti per DSN {dsn_str}.")

        # Per ogni gruppo di log con stesso id_documento
        for id_doc, recs in records_per_doc.items():
            # Ordina i log per data_modifica decrescente (dal più recente al meno)
            recs_sorted = sorted(recs, key=lambda x: x[1].get('data_modifica') or '', reverse=True)

            # Estrai importo dell'ultimo e penultimo log dalle note
            importo_ultimo_log = extract_importo(recs_sorted[0][1].get('note')) if len(recs_sorted) > 0 else None
            importo_penultimo_log = extract_importo(recs_sorted[1][1].get('note')) if len(recs_sorted) > 1 else None

            # Cicla su tutti i log ordinati (in pratica salva solo il primo se rispetta i criteri)
            for idx, (azienda, record) in enumerate(recs_sorted):
                data_stampa = record.get('data_stampa_fattura')
                data_modifica = record.get('data_modifica')

                # Salva solo se rispettate tutte le condizioni:
                # Condizione 1: la data di stampa fattura deve essere precedente alla data dell'ultima modifica. (cioè la stampa è avvenuta prima dell'ultima modifica)
                # Condizione 2: importo_ultimo_log < importo_penultimo_log (cioè l'importo dopo la stampa è stato ridotto)
                # Condizione 3: la differenza tra data_modifica e data_stampa_fattura deve essere > 30 secondi (range di tempo accettabile)
                # Condizione 4: importo_ultimo_log > 0 (non salvare record con importo modificato a 0)
                if (
                    data_stampa and data_modifica and data_stampa < data_modifica
                    and importo_ultimo_log is not None and importo_penultimo_log is not None
                    and importo_ultimo_log < importo_penultimo_log
                    and importo_ultimo_log > 0
                ):
                    delta_sec = (data_modifica - data_stampa).total_seconds()
                    if delta_sec > 60:

                        print(f"[INFO] Salvo documento {record.get('id_documento')} azienda {azienda} (log: {idx+1}) | importo_ultimo_log: {importo_ultimo_log} | importo_penultimo_log: {importo_penultimo_log} | delta_sec: {delta_sec}")

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
                            data_stampa_fattura=data_stampa,
                            azienda=azienda,
                            importo_ultimo_log=importo_ultimo_log,
                            importo_penultimo_log=importo_penultimo_log
                        )

                        session.add(nuovo_record)
                        totale += 1

    session.commit()
    session.close()
    print(f"\n[INFO] Tutti i record ({totale}) sono stati inseriti con successo!")
    print("[INFO] Fine script\n")

if __name__ == '__main__':
    main()
