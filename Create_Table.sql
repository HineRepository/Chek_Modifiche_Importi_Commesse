-- Script per creare la tabella Storico_Modifiche_Fatture in SQL Server

CREATE TABLE Storico_Modifiche_Fatture (
    id INT PRIMARY KEY IDENTITY(1,1),
    id_documento INT NOT NULL,
    anno INT,
    id_cliente INT,
    tipo_doc VARCHAR(10),
    data_doc DATE,
    num_doc VARCHAR(20),
    tipo_fattura VARCHAR(10),
    data_fattura DATE,
    numero_fattura VARCHAR(20),
    tipo_pagamento VARCHAR(10),
    id_hst INT,
    nome_tabella VARCHAR(50),
    utente VARCHAR(50),
    tipo_operazione VARCHAR(50),
    note VARCHAR(255),
    data_modifica DATETIME,
    data_stampa_fattura DATETIME,
    azienda VARCHAR(10),
    importo_modifica DECIMAL(18, 2),
    importo_fattura DECIMAL(18, 2),
    id_reg_pd INT,
    data_trasmissione_fattura DATETIME,
    targa VARCHAR(20)
);
GO
