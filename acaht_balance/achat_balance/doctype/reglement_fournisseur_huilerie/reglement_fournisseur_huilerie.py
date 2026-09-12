import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from acaht_balance.achat_balance.doctype.reception_olive.reception_olive import get_ancien_solde


class ReglementFournisseurHuilerie(Document):
	def validate(self):
		if flt(self.montant_regle) <= 0:
			frappe.throw(_("Le montant réglé doit être supérieur à zéro."))
		self.solde_avant = get_ancien_solde(
			self.fournisseur, self.societe, date_reception=self.date_reglement,
		)
		self.solde_apres = flt(self.solde_avant) - flt(self.montant_regle)

	def before_submit(self):
		self.statut = "Validé"

	def on_submit(self):
		self._creer_ecriture_paiement()

	def on_cancel(self):
		if self.payment_entry:
			payment = frappe.get_doc("Payment Entry", self.payment_entry)
			if payment.docstatus == 1:
				payment.cancel()
		self.statut = "Annulé"

	@frappe.whitelist()
	def creer_ecriture_paiement(self):
		if self.docstatus != 1:
			frappe.throw(_("Validez le règlement avant de créer l'écriture de paiement."))
		return self._creer_ecriture_paiement()

	def _creer_ecriture_paiement(self):
		if self.payment_entry:
			return self.payment_entry
		from erpnext.accounts.party import get_party_account

		party_account = get_party_account("Supplier", self.fournisseur, self.societe)
		doc = frappe.get_doc({
			"doctype": "Payment Entry",
			"payment_type": "Pay",
			"company": self.societe,
			"posting_date": self.date_reglement,
			"mode_of_payment": self.mode_paiement,
			"party_type": "Supplier",
			"party": self.fournisseur,
			"paid_from": self.compte_paiement,
			"paid_to": party_account,
			"paid_amount": self.montant_regle,
			"received_amount": self.montant_regle,
			"source_exchange_rate": 1,
			"target_exchange_rate": 1,
			"reference_no": self.reference_no,
			"reference_date": self.reference_date,
			"remarks": _("Créé depuis le règlement huilerie {0}").format(self.name),
		})
		doc.insert()
		doc.submit()
		self.db_set("payment_entry", doc.name)
		return doc.name
