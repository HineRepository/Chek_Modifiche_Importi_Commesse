from sqlalchemy import DECIMAL, Column, Integer, String, Date, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class StoricoModificheFatture(Base):
    __tablename__ = 'Storico_Modifiche_Fatture'

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_documento = Column(Integer, nullable=False)
    anno = Column(Integer)
    id_cliente = Column(Integer)
    tipo_doc = Column(String(10))
    data_doc = Column(Date)
    num_doc = Column(String(20))
    tipo_fattura = Column(String(10))
    data_fattura = Column(Date)
    numero_fattura = Column(String(20))
    tipo_pagamento = Column(String(10))
    id_hst = Column(Integer)
    nome_tabella = Column(String(50))
    utente = Column(String(50))
    tipo_operazione = Column(String(50))
    note = Column(String(255))
    data_modifica = Column(DateTime)
    azienda = Column(String(10))
    importo_modifica = Column(DECIMAL(18, 2)) # Log 
    importo_fattura = Column(DECIMAL(18, 2)) # XML: importo totale documento - spesa materiale consumo
    id_reg_pd = Column(Integer) # ID registro PD
    data_trasmissione_fattura = Column(DateTime) # Query recupero fattura
    targa = Column(String(20)) # Targa veicolo