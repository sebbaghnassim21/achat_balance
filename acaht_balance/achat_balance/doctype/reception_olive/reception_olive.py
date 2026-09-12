import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from acaht_balance.achat_balance.calculations import calculate_packaging_tare, calculate_reception


class ReceptionOlive(Document):
	def validate(self):
		self.ancien_solde = get_ancien_solde(
			self.fournisseur, self.societe, self.name, self.date_reception,
		)
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


@frappe.whitelist()
def get_ancien_solde(fournisseur, societe, reception=None, date_reception=None):
	"""Return the last submitted operational balance for this supplier."""
	if not fournisseur or not societe:
		return 0
	filters = {
		"fournisseur": fournisseur,
		"societe": societe,
		"docstatus": 1,
	}
	if reception:
		filters["name"] = ["!=", reception]
	if date_reception:
		filters["date_reception"] = ["<=", date_reception]
	previous = frappe.get_all(
		"Reception Olive",
		filters=filters,
		fields=["nouveau_solde"],
		order_by="date_reception desc, creation desc",
		limit=1,
	)
	return flt(previous[0].nouveau_solde) if previous else 0


@frappe.whitelist()
def recalculer_historique_soldes():
	"""Rebuild the running supplier balance of all submitted receptions."""
	balances = {}
	updated = 0
	rows = frappe.get_all(
		"Reception Olive",
		filters={"docstatus": 1},
		fields=["name", "fournisseur", "societe", "montant_achat", "montant_verse"],
		order_by="date_reception asc, creation asc",
	)
	for row in rows:
		key = (row.fournisseur, row.societe)
		old_balance = balances.get(key, 0)
		new_balance = old_balance + flt(row.montant_achat) - flt(row.montant_verse)
		frappe.db.set_value(
			"Reception Olive", row.name,
			{"ancien_solde": old_balance, "nouveau_solde": new_balance},
			update_modified=False,
		)
		balances[key] = new_balance
		updated += 1
	return {"receptions_mises_a_jour": updated}
