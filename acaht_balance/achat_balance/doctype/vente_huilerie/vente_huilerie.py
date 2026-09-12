import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from acaht_balance.achat_balance.calculations import calculate_customer_payment, calculate_sale_total
from acaht_balance.achat_balance.doctype.reglement_fournisseur_huilerie.reglement_fournisseur_huilerie import get_compte_mode_paiement


class VenteHuilerie(Document):
	def validate(self):
		if not self.articles:
			frappe.throw(_("Ajoutez au moins un article."))
		for row in self.articles:
			row.montant = flt(row.quantite) * flt(row.prix_unitaire)
		try:
			self.total_ht = float(calculate_sale_total(
				[(row.quantite, row.prix_unitaire) for row in self.articles],
			))
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		if self.mode_paiement and not self.compte_paiement:
			self.compte_paiement = get_compte_mode_paiement(self.mode_paiement, self.societe)

	def before_submit(self):
		self.statut = "Confirmée"

	def on_cancel(self):
		if self.facture_vente:
			invoice = frappe.get_doc("Sales Invoice", self.facture_vente)
			if invoice.docstatus == 1 and flt(invoice.outstanding_amount) == flt(invoice.grand_total):
				invoice.cancel()
		if self.bon_livraison:
			delivery = frappe.get_doc("Delivery Note", self.bon_livraison)
			if delivery.docstatus == 1:
				delivery.cancel()
		self.statut = "Annulée"

	@frappe.whitelist()
	def creer_bon_livraison(self):
		if self.docstatus != 1:
			frappe.throw(_("Validez la vente avant de créer le bon de livraison."))
		if self.bon_livraison:
			return self.bon_livraison
		delivery = frappe.get_doc({
			"doctype": "Delivery Note", "customer": self.client, "company": self.societe,
			"posting_date": self.date_vente, "set_warehouse": self.entrepot,
			"remarks": _("Créé depuis la vente huilerie {0}").format(self.name),
			"items": [{
				"item_code": row.article, "item_name": row.designation, "qty": row.quantite,
				"uom": row.unite, "rate": row.prix_unitaire, "warehouse": self.entrepot,
			} for row in self.articles],
		})
		delivery.insert()
		delivery.submit()
		self.db_set("bon_livraison", delivery.name)
		self.db_set("statut", "Livrée")
		return delivery.name

	@frappe.whitelist()
	def creer_facture_vente(self):
		if not self.bon_livraison:
			frappe.throw(_("Créez d'abord le bon de livraison."))
		if self.facture_vente:
			return self.facture_vente
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
		invoice = make_sales_invoice(self.bon_livraison)
		invoice.posting_date = self.date_vente
		invoice.remarks = _("Créée depuis la vente huilerie {0}").format(self.name)
		invoice.insert()
		invoice.submit()
		self.db_set("facture_vente", invoice.name)
		self.db_set("montant_a_encaisser", invoice.outstanding_amount)
		self.db_set("statut", "Facturée")
		return invoice.name

	@frappe.whitelist()
	def encaisser_client(self):
		if not self.facture_vente:
			frappe.throw(_("Créez d'abord la facture de vente."))
		amount = flt(self.montant_a_encaisser)
		invoice = frappe.get_doc("Sales Invoice", self.facture_vente)
		try:
			calculate_customer_payment(invoice.outstanding_amount, amount)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		if not self.mode_paiement:
			frappe.throw(_("Choisissez le mode de paiement."))
		account = self.compte_paiement or get_compte_mode_paiement(self.mode_paiement, self.societe)
		from erpnext.accounts.party import get_party_account
		party_account = get_party_account("Customer", self.client, self.societe)
		payment = frappe.get_doc({
			"doctype": "Payment Entry", "payment_type": "Receive", "company": self.societe,
			"posting_date": frappe.utils.today(), "mode_of_payment": self.mode_paiement,
			"party_type": "Customer", "party": self.client,
			"paid_from": party_account, "paid_to": account,
			"paid_amount": amount, "received_amount": amount,
			"source_exchange_rate": 1, "target_exchange_rate": 1,
			"references": [{"reference_doctype": "Sales Invoice", "reference_name": invoice.name, "allocated_amount": amount}],
			"remarks": _("Paiement de la vente huilerie {0}").format(self.name),
		})
		payment.insert()
		payment.submit()
		invoice.reload()
		self.db_set("paiement_client", payment.name)
		self.db_set("montant_a_encaisser", invoice.outstanding_amount)
		self.db_set("statut", "Payée" if not flt(invoice.outstanding_amount) else "Partiellement payée")
		return payment.name
