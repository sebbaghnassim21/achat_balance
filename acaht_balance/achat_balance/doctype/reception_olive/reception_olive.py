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

	def on_submit(self):
		self._creer_documents_achat()

	def on_cancel(self):
		if self.purchase_invoice:
			invoice = frappe.get_doc("Purchase Invoice", self.purchase_invoice)
			if invoice.docstatus == 1:
				invoice.cancel()
		if self.purchase_receipt:
			receipt = frappe.get_doc("Purchase Receipt", self.purchase_receipt)
			if receipt.docstatus == 1:
				receipt.cancel()
		self.statut_pesee = "Annulée"

	@frappe.whitelist()
	def creer_reception_achat(self):
		if self.docstatus != 1:
			frappe.throw(_("Validez la réception d'olives avant de créer la réception d'achat."))
		self._creer_documents_achat()
		return self.purchase_receipt

	def _creer_documents_achat(self):
		if not self.purchase_receipt:
			doc = frappe.get_doc({
				"doctype": "Purchase Receipt",
				"supplier": self.fournisseur,
				"company": self.societe,
				"posting_date": self.date_reception,
				"set_warehouse": self.entrepot_olives,
				"remarks": _("Créé automatiquement depuis la réception d'olives {0}").format(self.name),
				"items": [{
					"item_code": self.article_olives,
					"qty": self.poids_payable,
					"uom": self.unite,
					"rate": self.prix_unitaire,
					"warehouse": self.entrepot_olives,
				}],
			})
			doc.insert()
			doc.submit()
			self.db_set("purchase_receipt", doc.name)
		else:
			doc = frappe.get_doc("Purchase Receipt", self.purchase_receipt)
			if doc.docstatus == 0:
				doc.submit()

		if not self.purchase_invoice:
			from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

			invoice = make_purchase_invoice(doc.name)
			invoice.posting_date = self.date_reception
			invoice.remarks = _("Créée automatiquement depuis la réception d'olives {0}").format(self.name)
			invoice.insert()
			invoice.submit()
			self.db_set("purchase_invoice", invoice.name)


@frappe.whitelist()
def get_ancien_solde(
	fournisseur, societe, reception=None, date_reception=None, pret_materiel=None,
):
	"""Return purchases minus all submitted supplier settlements."""
	if not fournisseur or not societe:
		return 0
	conditions = ["fournisseur=%s", "societe=%s", "docstatus=1"]
	values = [fournisseur, societe]
	if reception:
		conditions.append("name!=%s")
		values.append(reception)
	if date_reception:
		conditions.append("date_reception<=%s")
		values.append(date_reception)
	purchases = frappe.db.sql(
		f"""select coalesce(sum(montant_achat - montant_verse), 0)
		from `tabReception Olive` where {' and '.join(conditions)}""",
		values,
	)[0][0]
	settlements = 0
	if frappe.db.exists("DocType", "Reglement Fournisseur Huilerie"):
		settlement_conditions = ["fournisseur=%s", "societe=%s", "docstatus=1"]
		settlement_values = [fournisseur, societe]
		if date_reception:
			settlement_conditions.append("date_reglement<=%s")
			settlement_values.append(date_reception)
		settlements = frappe.db.sql(
			f"""select coalesce(sum(montant_regle), 0)
			from `tabReglement Fournisseur Huilerie`
			where {' and '.join(settlement_conditions)}""",
			settlement_values,
		)[0][0]
	material_retention = 0
	if frappe.db.exists("DocType", "Pret Materiel"):
		loan_conditions = ["fournisseur=%s", "societe=%s", "docstatus=1"]
		loan_values = [fournisseur, societe]
		if pret_materiel:
			loan_conditions.append("name!=%s")
			loan_values.append(pret_materiel)
		material_retention = frappe.db.sql(
			f"""select coalesce(sum(retenue_materiel), 0)
			from `tabPret Materiel` where {' and '.join(loan_conditions)}""",
			loan_values,
		)[0][0]
	return flt(purchases) - flt(settlements) - flt(material_retention)


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
