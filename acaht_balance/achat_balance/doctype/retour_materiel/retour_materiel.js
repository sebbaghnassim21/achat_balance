frappe.ui.form.on("Retour Materiel", {
	setup(frm) {
		frm.set_query("compte_caution", () => ({
			filters: { company: frm.doc.societe, is_group: 0, account_type: ["in", ["Bank", "Cash"]] },
		}));
	},
	refresh(frm) {
		if (frm.doc.docstatus === 0 && flt(frm.doc.montant_caution_restituee) > 0) {
			frm.add_custom_button(__("Valider et rembourser la caution"), async () => {
				await frm.set_value("traitement_caution", "Rembourser en espèces/banque");
				await frm.save("Submit");
			}, __("Caution"));
		}
		if (frm.doc.docstatus === 1 && frm.doc.payment_entry_caution) {
			frm.add_custom_button(__("Voir le remboursement"), () => {
				frappe.set_route("Form", "Payment Entry", frm.doc.payment_entry_caution);
			}, __("Caution"));
		}
	},
	mode_paiement_caution(frm) {
		if (!frm.doc.mode_paiement_caution || !frm.doc.societe) return;
		frappe.call({
			method: "acaht_balance.achat_balance.doctype.reglement_fournisseur_huilerie.reglement_fournisseur_huilerie.get_compte_mode_paiement",
			args: { mode_paiement: frm.doc.mode_paiement_caution, societe: frm.doc.societe },
			callback(r) { frm.set_value("compte_caution", r.message); },
		});
	},
});
