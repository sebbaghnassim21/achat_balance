frappe.ui.form.on("Vente Huilerie", {
	setup(frm) {
		frm.set_query("compte_paiement", () => ({filters: {company: frm.doc.societe, is_group: 0, account_type: ["in", ["Bank", "Cash"]]}}));
	},
	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;
		if (!frm.doc.bon_livraison) bouton(frm, "Créer le bon de livraison", "creer_bon_livraison");
		if (frm.doc.bon_livraison && !frm.doc.facture_vente) bouton(frm, "Créer la facture de vente", "creer_facture_vente");
		if (frm.doc.facture_vente && flt(frm.doc.montant_a_encaisser) > 0) bouton(frm, "Encaisser le client", "encaisser_client");
	},
	mode_paiement(frm) {
		if (!frm.doc.mode_paiement || !frm.doc.societe) return;
		frappe.call({
			method: "acaht_balance.achat_balance.doctype.reglement_fournisseur_huilerie.reglement_fournisseur_huilerie.get_compte_mode_paiement",
			args: {mode_paiement: frm.doc.mode_paiement, societe: frm.doc.societe},
			callback(r) { frm.set_value("compte_paiement", r.message); },
		});
	},
});
frappe.ui.form.on("Ligne Vente Huilerie", {
	quantite: calculer_ligne, prix_unitaire: calculer_ligne,
});
function calculer_ligne(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "montant", flt(row.quantite) * flt(row.prix_unitaire));
}
function bouton(frm, label, method) {
	frm.add_custom_button(__(label), () => frm.call(method).then((r) => {
		if (r.message) frm.reload_doc();
	}), __("Créer"));
}
