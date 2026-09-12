frappe.ui.form.on("Conditionnement Huilerie", {
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

frappe.ui.form.on("Ligne Conditionnement", {
	nombre_unites: calculer_ligne,
	contenance: calculer_ligne,
});

function calculer_ligne(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "quantite_conditionnee", flt(row.nombre_unites) * flt(row.contenance));
}
