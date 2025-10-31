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
    data_stampa_fattura = Column(DateTime)
    azienda = Column(String(10))
    importo_ultimo_log = Column(DECIMAL(18, 2))
    importo_penultimo_log = Column(DECIMAL(18, 2))