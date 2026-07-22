frappe.ui.form.on("Reception Olive", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && !frm.doc.purchase_receipt) {
			frm.add_custom_button(__("Créer la réception d'achat"), () => {
				frm.call("creer_reception_achat").then((r) => {
					if (r.message) frappe.set_route("Form", "Purchase Receipt", r.message);
				});
			}, __("Créer"));
		}
	},
	poids_entree: recalculer,
	poids_sortie: recalculer,
	tare_emballages: recalculer,
	dechet_pct: recalculer,
	prix_unitaire: recalculer,
	ancien_solde: recalculer,
	montant_verse: recalculer,
});

function recalculer(frm) {
	const entree = flt(frm.doc.poids_entree);
	const sortie = flt(frm.doc.poids_sortie);
	const tare = flt(frm.doc.tare_emballages);
	const dechet = flt(frm.doc.dechet_pct);
	const net = Math.max(0, entree - sortie - tare);
	const payable = net * (1 - dechet / 100);
	frm.set_value("poids_net", net);
	frm.set_value("poids_payable", payable);
	frm.set_value("montant_achat", payable * flt(frm.doc.prix_unitaire));
	frm.set_value("nouveau_solde", flt(frm.doc.ancien_solde) + payable * flt(frm.doc.prix_unitaire) - flt(frm.doc.montant_verse));
}
