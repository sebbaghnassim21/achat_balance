frappe.ui.form.on("Pret Materiel", {
	setup(frm) {
		frm.set_query("compte_caution", () => ({
			filters: { company: frm.doc.societe, is_group: 0, account_type: ["in", ["Bank", "Cash"]] },
		}));
	},
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.statut !== "Clôturé") {
			frm.add_custom_button(__("Enregistrer un retour"), () => {
				frappe.new_doc("Retour Materiel", { pret_materiel: frm.doc.name, fournisseur: frm.doc.fournisseur, societe: frm.doc.societe });
			});
		}
	},
	fournisseur: charger_credit,
	societe: charger_credit,
	mode_paiement_caution: charger_compte_caution,
});

function charger_compte_caution(frm) {
	if (!frm.doc.mode_paiement_caution || !frm.doc.societe) return;
	frappe.call({
		method: "acaht_balance.achat_balance.doctype.reglement_fournisseur_huilerie.reglement_fournisseur_huilerie.get_compte_mode_paiement",
		args: { mode_paiement: frm.doc.mode_paiement_caution, societe: frm.doc.societe },
		callback(r) { frm.set_value("compte_caution", r.message); },
	});
}

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
