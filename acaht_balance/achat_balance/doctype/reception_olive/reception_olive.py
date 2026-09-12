import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from acaht_balance.achat_balance.calculations import calculate_packaging_tare, calculate_reception


class ReceptionOlive(Document):
	def validate(self):
		for row in self.emballages:
			if not flt(row.poids_unitaire):
				row.poids_unitaire = flt(frappe.db.get_value("Item", row.article_emballage, "weight_per_unit"))
			if not row.unite_poids:
				row.unite_poids = frappe.db.get_value("Item", row.article_emballage, "weight_uom") or self.unite
			if row.unite_poids != self.unite:
				frappe.throw(_("L'unité de poids de l'emballage {0} doit être {1}.").format(
					row.article_emballage, self.unite,
				))
		try:
			self.tare_emballages = float(calculate_packaging_tare(
				[(row.quantite, row.poids_unitaire) for row in self.emballages]
			)) if self.emballages else 0
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		for row in self.emballages:
			row.poids_total = flt(row.quantite) * flt(row.poids_unitaire)

		try:
			result = calculate_reception(
				self.poids_entree,
				self.poids_sortie,
				self.tare_emballages,
				self.dechet_pct,
				self.prix_unitaire,
				self.ancien_solde,
				self.montant_verse,
			)
		except ValueError as exc:
			frappe.throw(_(str(exc)))

		self.poids_net = float(result["net_weight"])
		self.poids_payable = float(result["payable_weight"])
		self.montant_achat = float(result["amount"])
		self.nouveau_solde = float(result["new_balance"])

		if self.poids_payable <= 0:
			frappe.throw(_("Le poids payable doit être supérieur à zéro."))

	def before_submit(self):
		self.statut_pesee = "Validée"

	def on_cancel(self):
		self.statut_pesee = "Annulée"

	@frappe.whitelist()
	def creer_reception_achat(self):
		if self.docstatus != 1:
			frappe.throw(_("Validez la réception d'olives avant de créer la réception d'achat."))
		if self.purchase_receipt:
			return self.purchase_receipt

		doc = frappe.get_doc({
			"doctype": "Purchase Receipt",
			"supplier": self.fournisseur,
			"company": self.societe,
			"posting_date": self.date_reception,
			"set_warehouse": self.entrepot_olives,
			"remarks": _("Créé depuis la réception d'olives {0}").format(self.name),
			"items": [{
				"item_code": self.article_olives,
				"qty": self.poids_payable,
				"uom": self.unite,
				"rate": self.prix_unitaire,
				"warehouse": self.entrepot_olives,
			}],
		})
		doc.insert()
		self.db_set("purchase_receipt", doc.name)
		return doc.name
