
import pandas as pd
from sqlalchemy import create_engine
import configparser
import csv

# Carica la configurazione
def get_engine():
    config = configparser.ConfigParser()
    config.read('config.ini')
    sqlserver_conf = config['SQLSERVER']
    sqlserver_conn_str = (
        f"mssql+pyodbc://{sqlserver_conf['username']}:{sqlserver_conf['password']}@"
        f"{sqlserver_conf['server']}/{sqlserver_conf['database']}?driver=ODBC+Driver+17+for+SQL+Server"
    )
    return create_engine(sqlserver_conn_str)

def export_table_to_csv():
    engine = get_engine()
    query = "SELECT * FROM Storico_Modifiche_Fatture"
    df = pd.read_sql(query, engine)
    df.to_csv(
        "Storico_Modifiche_Fatture_export.csv",
        index=False,
        encoding="utf-8-sig",  # UTF-8 con BOM per Excel
        sep=";",  # Punto e virgola come separatore
        quoting=csv.QUOTE_ALL
    )
    print("Esportazione completata: Storico_Modifiche_Fatture_export.csv")

if __name__ == "__main__":
    export_table_to_csv()
