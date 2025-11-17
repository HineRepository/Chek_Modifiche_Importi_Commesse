SELECT 	 
	 storico_modifiche.id_documento,    		 
	 cli.anno,
	 cli.id_cliente,
	 cli.tipo_doc,
	 cli.data_doc,
	 cli.num_doc,
	 cli.td_fatt as tipo_fattura,
	 cli.data_fatt as data_fattura,
	 cli.num_fatt as numero_fattura,
	 cli.cond_pag as tipo_pagamento,
	 storico_modifiche.id_hst,
	storico_modifiche.nome_tabella,
	storico_modifiche.utente,
	storico_modifiche.tipo_operazione,
	storico_modifiche.note,
	storico_modifiche.data_operazione as data_modifica,
	cli.id_reg_pd,
	off_veicoli.targa
FROM
	dba.hst_doc storico_modifiche
left outer join dba.tdo_cli cli on
	cli.id_documento = storico_modifiche.id_documento and storico_modifiche.gestione ='O'
	and cli.tipo_doc = storico_modifiche.tipo_doc
left outer join dba.mdm_cli_veicoli mdm_veicoli on
	mdm_veicoli.anno = cli.anno
	and mdm_veicoli.id_cliente = cli.id_cliente
	and mdm_veicoli.data_doc = cli.data_doc
	and mdm_veicoli.tipo_doc = cli.tipo_doc
	and mdm_veicoli.numero_doc = cli.num_doc
left outer join dba.off_veicoli off_veicoli on
	off_veicoli.id_veicolo = mdm_veicoli.id_veicolo
WHERE
	storico_modifiche.nome_tabella='tdo_cli' 
	AND storico_modifiche.note like '%ivato%'
	and cli.cond_pag ='205' --pagamento in contanti
	and cli.anno>=2024
	and cli.id_reg_pd>0
order by
   cli.id_documento,
   storico_modifiche.data_operazione 
   
   


   
