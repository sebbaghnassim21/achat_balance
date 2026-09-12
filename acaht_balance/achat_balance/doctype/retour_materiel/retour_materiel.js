frappe.ui.form.on("Retour Materiel", {
	setup(frm) {
		frm.set_query("compte_caution", () => ({
			filters: { company: frm.doc.societe, is_group: 0, account_type: ["in", ["Bank", "Cash"]] },
		}));
	},
});
