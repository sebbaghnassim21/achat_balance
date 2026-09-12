import frappe
from frappe.utils import flt, get_first_day, nowdate


@frappe.whitelist()
def get_kpis():
	start = get_first_day(nowdate())
	def total(doctype, field, filters):
		return sum(flt(value) for value in frappe.get_all(doctype, filters=filters, pluck=field))

	monthly = frappe.db.sql("""
		SELECT DATE_FORMAT(months.month_start, '%Y-%m') label,
			COALESCE(v.ventes, 0) ventes, COALESCE(r.achats, 0) achats,
			COALESCE(r.poids, 0) poids, COALESCE(p.production, 0) production
		FROM (
			SELECT DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL n MONTH), '%Y-%m-01') month_start
			FROM (SELECT 0 n UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) x
		) months
		LEFT JOIN (SELECT DATE_FORMAT(date_vente, '%Y-%m-01') m, SUM(total_ht) ventes FROM `tabVente Huilerie` WHERE docstatus=1 GROUP BY m) v ON v.m=months.month_start
		LEFT JOIN (SELECT DATE_FORMAT(date_reception, '%Y-%m-01') m, SUM(montant_achat) achats, SUM(poids_payable) poids FROM `tabReception Olive` WHERE docstatus=1 GROUP BY m) r ON r.m=months.month_start
		LEFT JOIN (SELECT DATE_FORMAT(date_production, '%Y-%m-01') m, SUM(quantite_produite) production FROM `tabProduction Huilerie` WHERE docstatus=1 GROUP BY m) p ON p.m=months.month_start
		ORDER BY months.month_start
	""", as_dict=True)
	return {
		"poids_recu_mois": total("Reception Olive", "poids_payable", {"docstatus": 1, "date_reception": [">=", start]}),
		"achats_mois": total("Reception Olive", "montant_achat", {"docstatus": 1, "date_reception": [">=", start]}),
		"production_mois": total("Production Huilerie", "quantite_produite", {"docstatus": 1, "date_production": [">=", start]}),
		"ventes_mois": total("Vente Huilerie", "total_ht", {"docstatus": 1, "date_vente": [">=", start]}),
		"creances_clients": total("Sales Invoice", "outstanding_amount", {"docstatus": 1, "outstanding_amount": [">", 0]}),
		"dettes_fournisseurs": total("Purchase Invoice", "outstanding_amount", {"docstatus": 1, "outstanding_amount": [">", 0]}),
		"materiel_non_rendu": total("Ligne Pret Materiel", "quantite_restante", {"docstatus": 1}),
		"monthly": monthly,
	}
