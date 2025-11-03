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
	(
	select
		max(data_stampa)
	from
		dba.storico_report as storico_stampe
	where
		storico_stampe.id_entita = storico_modifiche.id_documento
		and storico_stampe.tipo_documento = cli.td_fatt) as data_stampa_fattura
FROM
	dba.hst_doc storico_modifiche
left outer join dba.tdo_cli cli on
	cli.id_documento = storico_modifiche.id_documento and storico_modifiche.gestione ='O'
	and cli.tipo_doc = storico_modifiche.tipo_doc
WHERE
	storico_modifiche.nome_tabella='tdo_cli' 
	AND note like '%ivato%'
	and cli.cond_pag ='205' --pagamento in contanti
	and cli.anno>=2024
order by
   cli.id_documento,
   storico_modifiche.data_operazione 
   
   


   
