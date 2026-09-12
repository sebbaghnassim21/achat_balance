frappe.ui.form.on("Reglement Fournisseur Huilerie", {
	setup(frm) {
		frm.set_query("compte_paiement", () => ({
			filters: {
				company: frm.doc.societe,
				is_group: 0,
				account_type: ["in", ["Bank", "Cash"]],
			},
		}));
	},
	refresh(frm) {
		if (frm.doc.docstatus === 1 && !frm.doc.payment_entry) {
			frm.add_custom_button(__("Créer l'écriture de paiement"), () => {
				frm.call("creer_ecriture_paiement").then((r) => {
					if (r.message) frappe.set_route("Form", "Payment Entry", r.message);
				});
			}, __("Créer"));
		}
	},
	fournisseur: charger_solde,
	societe: charger_solde,
	date_reglement: charger_solde,
	montant_regle: calculer_solde_apres,
});

function charger_solde(frm) {
	if (!frm.doc.fournisseur || !frm.doc.societe) return;
	frappe.call({
		method: "acaht_balance.achat_balance.doctype.reception_olive.reception_olive.get_ancien_solde",
		args: {
			fournisseur: frm.doc.fournisseur,
			societe: frm.doc.societe,
			date_reception: frm.doc.date_reglement,
		},
		callback(r) {
			frm.set_value("solde_avant", flt(r.message)).then(() => calculer_solde_apres(frm));
		},
	});
}

function calculer_solde_apres(frm) {
	frm.set_value("solde_apres", flt(frm.doc.solde_avant) - flt(frm.doc.montant_regle));
}
