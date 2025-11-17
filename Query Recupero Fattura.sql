select comm_testata.id_reg_pd, trasmissione_testata.fine_trasmissione, trasmissione_dettaglio.nome_file, trasmissione_dettaglio.file_xml_vendita from dba.tdo_cli as comm_testata
inner join dba.reg_pd_fattura_xml as trasmissione_testata on trasmissione_testata.id_reg_pd=comm_testata.id_reg_pd
inner join dba.reg_pd_fattura_pa as trasmissione_dettaglio on trasmissione_dettaglio.id_reg_pd=comm_testata.id_reg_pd
where comm_testata.id_reg_pd = ?