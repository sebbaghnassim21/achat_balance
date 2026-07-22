import frappe
from frappe import _
from frappe.model.document import Document

from acaht_balance.achat_balance.calculations import calculate_reception


class ReceptionOlive(Document):
	def validate(self):
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
