frappe.ui.form.on("Reglement Client Huilerie", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.payment_entry) {
			frm.add_custom_button(__("Voir le paiement"), () => {
				frappe.set_route("Form", "Payment Entry", frm.doc.payment_entry);
			});
		}
	},
	client: charger_pieces,
	societe: charger_pieces,
	montant_regle: repartir,
	mode_paiement(frm) {
		if (!frm.doc.mode_paiement || !frm.doc.societe) return;
		frappe.call({
			method: "acaht_balance.achat_balance.doctype.reglement_client_huilerie.reglement_client_huilerie.get_compte_paiement_client",
			args: {mode_paiement: frm.doc.mode_paiement, societe: frm.doc.societe},
			callback(r) { frm.set_value("compte_paiement", r.message); },
		});
	},
});

function charger_pieces(frm) {
	if (!frm.doc.client || !frm.doc.societe || frm.doc.docstatus !== 0) return;
	frappe.call({
		method: "acaht_balance.achat_balance.doctype.reglement_client_huilerie.reglement_client_huilerie.get_pieces_non_reglees",
		args: {client: frm.doc.client, societe: frm.doc.societe, vente_source: frm.doc.vente_source},
		callback(r) {
			frm.clear_table("pieces");
			(r.message || []).forEach(value => {
				const row = frm.add_child("pieces", value);
				row.montant_affecte = 0; row.reste_apres = row.reste_avant;
			});
			frm.refresh_field("pieces");
			frm.set_value("montant_global_du", (r.message || []).reduce((t, row) => t + flt(row.reste_avant), 0));
			repartir(frm);
		},
	});
}

function repartir(frm) {
	let disponible = flt(frm.doc.montant_regle);
	(frm.doc.pieces || []).forEach(row => {
		const affecte = Math.min(flt(row.reste_avant), Math.max(0, disponible));
		frappe.model.set_value(row.doctype, row.name, "montant_affecte", affecte);
		frappe.model.set_value(row.doctype, row.name, "reste_apres", flt(row.reste_avant) - affecte);
		disponible -= affecte;
	});
	const affecte = flt(frm.doc.montant_regle) - Math.max(0, disponible);
	frm.set_value("montant_affecte", affecte);
	frm.set_value("reste_global", flt(frm.doc.montant_global_du) - affecte);
}
