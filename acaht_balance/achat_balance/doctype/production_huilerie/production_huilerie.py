import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from acaht_balance.achat_balance.calculations import calculate_yield


class ProductionHuilerie(Document):
	def validate(self):
		if flt(self.quantite_entree) <= 0:
			frappe.throw(_("La quantité d'olives consommée doit être supérieure à zéro."))
		if flt(self.pertes) < 0:
			frappe.throw(_("Les pertes ne peuvent pas être négatives."))
		if not self.produits_finis:
			frappe.throw(_("Ajoutez au moins un produit fini."))

		total = 0
		for row in self.produits_finis:
			if flt(row.quantite) <= 0:
				frappe.throw(_("La quantité doit être positive à la ligne {0}.").format(row.idx))
			if flt(row.taux_conversion) <= 0:
				frappe.throw(_("Le taux de conversion doit être positif à la ligne {0}.").format(row.idx))
			row.montant = flt(row.quantite) * flt(row.cout_unitaire)
			if row.type_produit != "Sous-produit":
				total += flt(row.quantite)

		self.quantite_produite = total
		self.rendement_pct = float(calculate_yield(self.quantite_entree, total))

	def before_submit(self):
		self.statut = "Terminée"

	@frappe.whitelist()
	def creer_mouvement_stock(self):
		if self.docstatus != 1:
			frappe.throw(_("Validez la production avant de créer le mouvement de stock."))
		if self.stock_entry:
			return self.stock_entry

		items = [{
			"item_code": self.article_olives,
			"s_warehouse": self.entrepot_source,
			"qty": self.quantite_entree,
			"uom": self.unite_entree,
			"stock_uom": self.unite_entree,
			"conversion_factor": 1,
		}]
		for row in self.produits_finis:
			items.append({
				"item_code": row.article,
				"t_warehouse": row.entrepot,
				"qty": row.quantite,
				"uom": row.unite,
				"conversion_factor": row.taux_conversion,
				"basic_rate": row.cout_unitaire,
				"allow_zero_valuation_rate": 1 if not row.cout_unitaire else 0,
			})

		doc = frappe.get_doc({
			"doctype": "Stock Entry",
			"stock_entry_type": "Repack",
			"company": self.societe,
			"posting_date": self.date_production,
			"remarks": _("Créé depuis la production huilerie {0}").format(self.name),
			"items": items,
		})
		doc.insert()
		self.db_set("stock_entry", doc.name)
		return doc.name
