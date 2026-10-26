frappe.listview_settings['Reception Olive'] = {
	add_fields: [
		'date_reception',
		'fournisseur',
		'article_olives',
		'variete',
		'statut_pesee',
		'poids_payable'
	],
	get_indicator(doc) {
		const colors = {
			'Brouillon': 'orange',
			'Validée': 'green',
			'Annulée': 'red'
		};
		return [__(doc.statut_pesee || 'Brouillon'), colors[doc.statut_pesee] || 'gray', `statut_pesee,=,${doc.statut_pesee || 'Brouillon'}`];
	}
};
