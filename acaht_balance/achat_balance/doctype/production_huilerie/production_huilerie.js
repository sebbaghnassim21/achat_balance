frappe.ui.form.on("Production Huilerie", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && !frm.doc.stock_entry) {
			frm.add_custom_button(__("Créer le mouvement de stock"), () => {
				frm.call("creer_mouvement_stock").then((r) => {
					if (r.message) frappe.set_route("Form", "Stock Entry", r.message);
				});
			}, __("Créer"));
		}
	},
});

frappe.ui.form.on("Produit Fini Huilerie", {
	quantite: calculer_ligne,
	cout_unitaire: calculer_ligne,
});

function calculer_ligne(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "montant", flt(row.quantite) * flt(row.cout_unitaire));
}
