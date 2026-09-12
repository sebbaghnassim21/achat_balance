import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

class VenteHuilerie(Document):
	def validate(self):
		if not self.articles:
			frappe.throw(_("Ajoutez au moins un article."))
		for row in self.articles:
			if flt(row.quantite) <= 0 or flt(row.prix_unitaire) < 0:
				frappe.throw(_("La quantité doit être positive et le prix ne peut pas être négatif."))
			row.montant = flt(row.quantite) * flt(row.prix_unitaire)
		self.total_ht = sum(flt(row.montant) for row in self.articles)
		if flt(self.montant_a_encaisser) > flt(self.total_ht):
			frappe.throw(_("Le montant à encaisser ne peut pas dépasser le total de la vente."))
		if flt(self.montant_a_encaisser) > 0 and not self.mode_paiement:
			frappe.throw(_("Choisissez le mode de paiement pour encaisser le client."))
		if self.mode_paiement and not self.compte_paiement:
			self.compte_paiement = _get_compte_mode_paiement(self.mode_paiement, self.societe)

	def before_submit(self):
		self.statut = "Confirmée"

	def on_submit(self):
		montant_demande = flt(self.montant_a_encaisser)
		self.creer_bon_livraison()
		self.creer_facture_vente()
		if montant_demande > 0:
			self.db_set("montant_a_encaisser", montant_demande)
			self.montant_a_encaisser = montant_demande
			self.encaisser_client()

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
		if amount <= 0 or amount > flt(invoice.outstanding_amount):
			frappe.throw(_("Le paiement doit être positif et ne pas dépasser le solde de la facture."))
		if not self.mode_paiement:
			frappe.throw(_("Choisissez le mode de paiement."))
		account = self.compte_paiement or _get_compte_mode_paiement(self.mode_paiement, self.societe)
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


def _get_compte_mode_paiement(mode_paiement, societe):
	account = frappe.db.get_value(
		"Mode of Payment Account",
		{"parent": mode_paiement, "parenttype": "Mode of Payment", "company": societe},
		"default_account",
	)
	if not account:
		frappe.throw(_("Aucun compte par défaut n'est configuré pour ce mode de paiement."))
	return account


@frappe.whitelist()
def get_compte_mode_paiement_vente(mode_paiement, societe):
	return _get_compte_mode_paiement(mode_paiement, societe)
