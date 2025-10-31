from flask import Flask, render_template, send_file, request
import io
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import StoricoModificheFatture
import configparser

app = Flask(__name__)

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

@app.route('/')
def index():
    session = Session()
    records = session.query(StoricoModificheFatture).order_by(StoricoModificheFatture.id.desc()).all()
    # Calcola il conteggio dei record per utente
    utenti_count = {}
    totale_soldi_spariti = 0.0
    for rec in records:
        utente = rec.utente or 'N/D'
        utenti_count[utente] = utenti_count.get(utente, 0) + 1
        try:
            if rec.importo_penultimo_log is not None and rec.importo_ultimo_log is not None:
                diff = float(rec.importo_penultimo_log) - float(rec.importo_ultimo_log)
                if diff > 0:
                    totale_soldi_spariti += diff
        except Exception:
            pass
    totale_record = sum(utenti_count.values())
    session.close()
    return render_template('index.html', records=records, utenti_count=utenti_count, totale_record=totale_record, totale_soldi_spariti=totale_soldi_spariti)


# Route per esportazione CSV
@app.route('/export')
def export():
    session = Session()
    records = session.query(StoricoModificheFatture).order_by(StoricoModificheFatture.id.desc()).all()
    session.close()
    # Colonne come nella tabella index
    columns = [
        'ID Fattura',
        'Azienda',
        'Importo stampato in fattura',
        'Importo modificato dopo la stampa della fattura',
        'Data stampa fattura',
        'Data modifica dopo la stampa della fattura',
        'Utente'
    ]
    data = []
    for rec in records:
        data.append({
            'ID Fattura': rec.id_documento,
            'Azienda': rec.azienda or '',
            'Importo stampato in fattura': f"{rec.importo_penultimo_log} €" if rec.importo_penultimo_log is not None else '',
            'Importo modificato dopo la stampa della fattura': f"{rec.importo_ultimo_log} €" if rec.importo_ultimo_log is not None else '',
            'Data stampa fattura': f"{rec.data_stampa_fattura.strftime('%d-%m-%Y')} - {rec.data_stampa_fattura.strftime('%H:%M')}" if rec.data_stampa_fattura else '',
            'Data modifica dopo la stampa della fattura': f"{rec.data_modifica.strftime('%d-%m-%Y')} - {rec.data_modifica.strftime('%H:%M')}" if rec.data_modifica else '',
            'Utente': rec.utente or ''
        })
    df = pd.DataFrame(data, columns=columns)
    output = io.StringIO()
    df.to_csv(output, index=False, sep=';')
    # Riga vuota
    output.write('\n')
    # Tabella utenti
    output.write('Utente;Numero record\n')
    utenti_count = {}
    totale_soldi_spariti = 0.0
    for rec in records:
        utente = rec.utente or 'N/D'
        utenti_count[utente] = utenti_count.get(utente, 0) + 1
        try:
            if rec.importo_penultimo_log is not None and rec.importo_ultimo_log is not None:
                diff = float(rec.importo_penultimo_log) - float(rec.importo_ultimo_log)
                if diff > 0:
                    totale_soldi_spariti += diff
        except Exception:
            pass
    totale_record = sum(utenti_count.values())
    for utente, count in utenti_count.items():
        output.write(f'{utente};{count}\n')
    output.write(f'TOTALE;{totale_record}\n')
    output.write(f'Totale soldi spariti;{totale_soldi_spariti:.2f} €\n')
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='storico_modifiche_fatture.csv'
    )

if __name__ == '__main__':
    app.run(debug=True)
