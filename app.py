from flask import Flask, render_template
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
    session.close()
    return render_template('index.html', records=records)

if __name__ == '__main__':
    app.run(debug=True)
