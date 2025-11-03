from flask import Flask, render_template, send_file, request, redirect, url_for, flash
import io
import pandas as pd
import subprocess
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import StoricoModificheFatture
import configparser

app = Flask(__name__)
app.secret_key = 'your_secret_key' # Per flask o rompe le scatole

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
    # Lista aziende distinte
    aziende = [row[0] for row in session.query(StoricoModificheFatture.azienda).distinct().order_by(StoricoModificheFatture.azienda)]
    azienda_filtro = request.args.get('azienda', default=None, type=str)
    query = session.query(StoricoModificheFatture)
    if azienda_filtro and azienda_filtro != 'TUTTE':
        query = query.filter(StoricoModificheFatture.azienda == azienda_filtro)
    records = query.order_by(StoricoModificheFatture.id.desc()).all()
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
    # Totali per azienda (solo se nessun filtro attivo)
    totali_per_azienda = []
    if not azienda_filtro or azienda_filtro == 'TUTTE':
        for az in aziende:
            if not az:
                continue
            recs_az = [r for r in session.query(StoricoModificheFatture).filter(StoricoModificheFatture.azienda == az).all()]
            count_az = len(recs_az)
            soldi_az = 0.0
            for r in recs_az:
                try:
                    if r.importo_penultimo_log is not None and r.importo_ultimo_log is not None:
                        diff = float(r.importo_penultimo_log) - float(r.importo_ultimo_log)
                        if diff > 0:
                            soldi_az += diff
                except Exception:
                    pass
            totali_per_azienda.append({'azienda': az, 'record': count_az, 'soldi': soldi_az})
    session.close()
    return render_template(
        'index.html',
        records=records,
        utenti_count=utenti_count,
        totale_record=totale_record,
        totale_soldi_spariti=totale_soldi_spariti,
        aziende=aziende,
        azienda_filtro=azienda_filtro,
        totali_per_azienda=totali_per_azienda
    )


# Route per svuotare la tabella
@app.route('/clear-table', methods=['POST'])
def clear_table():
    session = Session()
    session.query(StoricoModificheFatture).delete()
    session.commit()
    session.close()
    flash('Tabella svuotata con successo!', 'success')
    return redirect(url_for('index'))

# Route per avviare lo script main.py
@app.route('/run-script', methods=['POST'])
def run_script():
    try:
        # Avvia main.py come sottoprocesso
        result = subprocess.run(['python', 'main.py'], capture_output=True, text=True, cwd='.')
        if result.returncode == 0:
            flash('Script eseguito con successo!', 'success')
        else:
            flash(f'Errore nell\'esecuzione dello script: {result.stderr}', 'danger')
    except Exception as e:
        flash(f'Errore: {e}', 'danger')
    return redirect(url_for('index'))


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
