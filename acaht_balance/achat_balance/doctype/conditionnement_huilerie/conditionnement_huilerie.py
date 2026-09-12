import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from acaht_balance.achat_balance.calculations import calculate_packaging


class ConditionnementHuilerie(Document):
	def validate(self):
		if not self.lignes:
			frappe.throw(_("Ajoutez au moins une ligne de conditionnement."))
		if any(row.unite_contenu != self.unite_source for row in self.lignes):
			frappe.throw(_("L'unité du contenu de chaque ligne doit correspondre à l'unité du produit vrac."))

		try:
			result = calculate_packaging(
				self.quantite_source,
				[(row.nombre_unites, row.contenance) for row in self.lignes],
			)
		except ValueError as exc:
			frappe.throw(_(str(exc)))

		for row in self.lignes:
			row.quantite_conditionnee = flt(row.nombre_unites) * flt(row.contenance)
		self.quantite_conditionnee = float(result["packaged_quantity"])
		self.pertes = float(result["loss_quantity"])

	def before_submit(self):
		self.statut = "Terminé"

	@frappe.whitelist()
	def creer_mouvement_stock(self):
		if self.docstatus != 1:
			frappe.throw(_("Validez le conditionnement avant de créer le mouvement de stock."))
		if self.stock_entry:
			return self.stock_entry

		items = [{
			"item_code": self.article_source,
			"s_warehouse": self.entrepot_source,
			"qty": self.quantite_source,
			"uom": self.unite_source,
			"conversion_factor": 1,
		}]
		for row in self.lignes:
			items.append({
				"item_code": row.article_fini,
				"t_warehouse": row.entrepot_destination,
				"qty": row.nombre_unites,
				"uom": row.unite_vente,
				"conversion_factor": 1,
				"basic_rate": row.cout_unitaire,
				"allow_zero_valuation_rate": 1 if not row.cout_unitaire else 0,
			})

		doc = frappe.get_doc({
			"doctype": "Stock Entry",
			"stock_entry_type": "Repack",
			"company": self.societe,
			"posting_date": self.date_conditionnement,
			"remarks": _("Créé depuis le conditionnement {0}").format(self.name),
			"items": items,
		})
		doc.insert()
		self.db_set("stock_entry", doc.name)
		return doc.name
