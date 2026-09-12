frappe.ui.form.on("Pret Materiel", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.statut !== "Clôturé") {
			frm.add_custom_button(__("Enregistrer un retour"), () => {
				frappe.new_doc("Retour Materiel", { pret_materiel: frm.doc.name, fournisseur: frm.doc.fournisseur, societe: frm.doc.societe });
			});
		}
	},
	fournisseur: charger_credit,
	societe: charger_credit,
});

function charger_credit(frm) {
	if (!frm.doc.fournisseur || !frm.doc.societe) return;
	frappe.call({
		method: "acaht_balance.achat_balance.doctype.reception_olive.reception_olive.get_ancien_solde",
		args: {
			fournisseur: frm.doc.fournisseur,
			societe: frm.doc.societe,
			pret_materiel: frm.doc.name,
		},
		callback(r) {
			frm.set_value("dette_fournisseur", flt(r.message));
		},
	});
}
