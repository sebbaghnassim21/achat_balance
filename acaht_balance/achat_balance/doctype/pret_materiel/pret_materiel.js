frappe.ui.form.on("Pret Materiel", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.statut !== "Clôturé") {
			frm.add_custom_button(__("Enregistrer un retour"), () => {
				frappe.new_doc("Retour Materiel", { pret_materiel: frm.doc.name, fournisseur: frm.doc.fournisseur, societe: frm.doc.societe });
			});
		}
	},
});
