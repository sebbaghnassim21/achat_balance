frappe.pages['achat-balance'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Tableau de bord Huilerie et Oliveraie',
		single_column: true
	});
	const body = $(wrapper).find('.layout-main-section');
	body.html('<div class="kpi-loading text-muted">Chargement des indicateurs...</div>');
	frappe.call({
		method: 'acaht_balance.achat_balance.page.achat_balance.achat_balance.get_kpis',
		callback: function(r) {
			const d = r.message || {};
			const cards = [
				['Olives reçues ce mois', d.poids_recu_mois, ' Kg'],
				['Achats ce mois', d.achats_mois, ' DA'],
				['Production ce mois', d.production_mois, ''],
				['Ventes ce mois', d.ventes_mois, ' DA'],
				['Créances clients', d.creances_clients, ' DA'],
				['Dettes fournisseurs', d.dettes_fournisseurs, ' DA'],
				['Matériel non rendu', d.materiel_non_rendu, ' unités']
			];
			body.html(`<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;padding:12px">${cards.map(c => `<div class="card" style="padding:20px;border-radius:12px"><div class="text-muted">${c[0]}</div><div style="font-size:26px;font-weight:700;margin-top:8px">${format_number(c[1] || 0)}${c[2]}</div></div>`).join('')}</div><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:16px;padding:12px"><div class="card" style="padding:16px"><h4>Ventes et achats — 6 mois</h4><div id="chart-money"></div></div><div class="card" style="padding:16px"><h4>Olives reçues et production — 6 mois</h4><div id="chart-quantity"></div></div></div>`);
			const monthly = d.monthly || [];
			new frappe.Chart('#chart-money', {data:{labels:monthly.map(x=>x.label),datasets:[{name:'Ventes',values:monthly.map(x=>x.ventes)},{name:'Achats',values:monthly.map(x=>x.achats)}]},type:'bar',height:280,colors:['#2e7d32','#ef6c00']});
			new frappe.Chart('#chart-quantity', {data:{labels:monthly.map(x=>x.label),datasets:[{name:'Olives reçues',values:monthly.map(x=>x.poids)},{name:'Production',values:monthly.map(x=>x.production)}]},type:'line',height:280,colors:['#558b2f','#1565c0']});
		}
	});
}
