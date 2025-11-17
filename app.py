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
    all_records = query.order_by(StoricoModificheFatture.data_modifica.desc()).all()
    
    # Raggruppa per id_documento e prendi solo l'ultimo (più recente)
    records_dict = {}
    for rec in all_records:
        id_doc = rec.id_documento
        if id_doc not in records_dict:
            records_dict[id_doc] = rec
    
    records = list(records_dict.values())
    
    # Calcola statistiche
    totale_record = len(records)
    totale_differenza = 0.0
    for rec in records:
        try:
            if rec.importo_fattura is not None and rec.importo_modifica is not None:
                diff = float(rec.importo_fattura) - float(rec.importo_modifica)
                if diff > 0.05:
                    totale_differenza += diff
        except Exception:
            pass
    
    # Totali per azienda (solo se nessun filtro attivo)
    totali_per_azienda = []
    if not azienda_filtro or azienda_filtro == 'TUTTE':
        for az in aziende:
            if not az:
                continue
            recs_az_all = [r for r in session.query(StoricoModificheFatture).filter(StoricoModificheFatture.azienda == az).order_by(StoricoModificheFatture.data_modifica.desc()).all()]
            # Raggruppa per id_documento
            recs_az_dict = {}
            for r in recs_az_all:
                if r.id_documento not in recs_az_dict:
                    recs_az_dict[r.id_documento] = r
            recs_az = list(recs_az_dict.values())
            count_az = len(recs_az)
            diff_az = 0.0
            for r in recs_az:
                try:
                    if r.importo_fattura is not None and r.importo_modifica is not None:
                        diff = float(r.importo_fattura) - float(r.importo_modifica)
                        if diff > 0.05:
                            diff_az += diff
                except Exception:
                    pass
            totali_per_azienda.append({'azienda': az, 'record': count_az, 'differenza': diff_az})
    
    session.close()
    return render_template(
        'index.html',
        records=records,
        totale_record=totale_record,
        totale_differenza=totale_differenza,
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
    
    # Colonne per la nuova visualizzazione
    columns = [
        'ID Documento',
        'ID Reg PD',
        'Azienda',
        'Data Trasmissione Fattura',
        'Targa',
        'Importo Fattura',
        'Importo Ultima Modifica',
        'Differenza',
        'Utente',
        'Data Modifica'
    ]
    
    data = []
    for rec in records:
        importo_fattura = rec.importo_fattura if rec.importo_fattura is not None else 0.0
        importo_modifica = rec.importo_modifica if rec.importo_modifica is not None else 0.0
        differenza = importo_fattura - importo_modifica
        
        data.append({
            'ID Documento': rec.id_documento,
            'ID Reg PD': rec.id_reg_pd or '',
            'Azienda': rec.azienda or '',
            'Data Trasmissione Fattura': rec.data_trasmissione_fattura.strftime('%d-%m-%Y %H:%M') if rec.data_trasmissione_fattura else '',
            'Targa': rec.targa or '',
            'Importo Fattura': f"{importo_fattura:.2f} €",
            'Importo Ultima Modifica': f"{importo_modifica:.2f} €",
            'Differenza': f"{differenza:.2f} €",
            'Utente': rec.utente or '',
            'Data Modifica': rec.data_modifica.strftime('%d-%m-%Y %H:%M') if rec.data_modifica else ''
        })
    
    df = pd.DataFrame(data, columns=columns)
    output = io.StringIO()
    df.to_csv(output, index=False, sep=';')
    
    # Riga vuota
    output.write('\n')
    
    # Statistiche per azienda
    output.write('Azienda;Numero Record;Differenza Totale\n')
    aziende_stats = {}
    for rec in records:
        azienda = rec.azienda or 'N/D'
        if azienda not in aziende_stats:
            aziende_stats[azienda] = {'count': 0, 'diff': 0.0}
        aziende_stats[azienda]['count'] += 1
        try:
            if rec.importo_fattura is not None and rec.importo_modifica is not None:
                diff = float(rec.importo_fattura) - float(rec.importo_modifica)
                if diff > 0:
                    aziende_stats[azienda]['diff'] += diff
        except Exception:
            pass
    
    for azienda in sorted(aziende_stats.keys()):
        stats = aziende_stats[azienda]
        output.write(f'{azienda};{stats["count"]};{stats["diff"]:.2f} €\n')
    
    # Totale generale
    totale_record = sum(s['count'] for s in aziende_stats.values())
    totale_diff = sum(s['diff'] for s in aziende_stats.values())
    output.write(f'TOTALE GENERALE;{totale_record};{totale_diff:.2f} €\n')
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='storico_modifiche_fatture.csv'
    )

if __name__ == '__main__':
    app.run(debug=True)
