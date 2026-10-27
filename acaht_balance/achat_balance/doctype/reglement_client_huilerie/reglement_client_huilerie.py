import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

class ReglementClientHuilerie(Document):
	def validate(self):
		if not self.pieces:
			frappe.throw(_("Aucune facture non réglée n'a été trouvée."))
		outstandings = []
		for row in self.pieces:
			invoice = frappe.get_doc("Sales Invoice", row.facture_vente)
			if invoice.docstatus != 1 or invoice.customer != self.client or invoice.company != self.societe:
				frappe.throw(_("La facture {0} n'est pas valide pour ce règlement.").format(row.facture_vente))
			row.montant_facture = invoice.grand_total
			row.deja_regle = flt(invoice.grand_total) - flt(invoice.outstanding_amount)
			row.reste_avant = invoice.outstanding_amount
			outstandings.append(invoice.outstanding_amount)
		amount = flt(self.montant_regle)
		if amount <= 0 or amount > sum(flt(value) for value in outstandings):
			frappe.throw(_("Le montant réglé doit être positif et ne pas dépasser le montant global dû."))
		remaining = amount
		allocations = []
		for outstanding in outstandings:
			allocated = min(flt(outstanding), remaining)
			allocations.append(allocated)
			remaining -= allocated
		for row, allocated in zip(self.pieces, allocations):
			row.montant_affecte = float(allocated)
			row.reste_apres = flt(row.reste_avant) - flt(allocated)
		self.montant_global_du = sum(flt(value) for value in outstandings)
		self.montant_affecte = sum(flt(value) for value in allocations)
		self.reste_global = self.montant_global_du - self.montant_affecte
		if not self.compte_paiement:
			self.compte_paiement = get_compte_paiement_client(self.mode_paiement, self.societe)

	def before_submit(self):
		self.statut = "Validé"

	def on_submit(self):
		from erpnext.accounts.party import get_party_account
		party_account = get_party_account("Customer", self.client, self.societe)
		payment = frappe.get_doc({
			"doctype": "Payment Entry", "payment_type": "Receive", "company": self.societe,
			"posting_date": self.date_reglement, "mode_of_payment": self.mode_paiement,
			"party_type": "Customer", "party": self.client,
			"paid_from": party_account, "paid_to": self.compte_paiement,
			"paid_amount": self.montant_affecte, "received_amount": self.montant_affecte,
			"source_exchange_rate": 1, "target_exchange_rate": 1,
			"reference_no": self.reference_no, "reference_date": self.reference_date,
			"references": [{
				"reference_doctype": "Sales Invoice", "reference_name": row.facture_vente,
				"allocated_amount": row.montant_affecte,
			} for row in self.pieces if flt(row.montant_affecte) > 0],
			"remarks": _("Règlement client Huilerie et Oliveraie {0}").format(self.name),
		})
		payment.insert()
		payment.submit()
		self.db_set("payment_entry", payment.name)
		for row in self.pieces:
			if not flt(row.montant_affecte):
				continue
			invoice = frappe.get_doc("Sales Invoice", row.facture_vente)
			invoice.reload()
			status = "Payée" if not flt(invoice.outstanding_amount) else "Partiellement payée"
			frappe.db.set_value("Vente Huilerie", row.vente_huilerie, {
				"paiement_client": payment.name,
				"montant_a_encaisser": invoice.outstanding_amount,
				"statut": status,
			}, update_modified=False)

	def on_cancel(self):
		if self.payment_entry:
			payment = frappe.get_doc("Payment Entry", self.payment_entry)
			if payment.docstatus == 1:
				payment.cancel()
		for row in self.pieces:
			if not row.facture_vente or not row.vente_huilerie:
				continue
			invoice = frappe.get_doc("Sales Invoice", row.facture_vente)
			invoice.reload()
			status = "Payée" if not flt(invoice.outstanding_amount) else (
				"Partiellement payée" if flt(invoice.outstanding_amount) < flt(invoice.grand_total) else "Facturée"
			)
			frappe.db.set_value("Vente Huilerie", row.vente_huilerie, {
				"montant_a_encaisser": invoice.outstanding_amount,
				"statut": status,
			}, update_modified=False)
		self.statut = "Annulé"


@frappe.whitelist()
def get_pieces_non_reglees(client, societe, vente_source=None):
	filters = {"docstatus": 1, "client": client, "societe": societe}
	if vente_source:
		filters["name"] = vente_source
	rows = frappe.get_all(
		"Vente Huilerie", filters=filters,
		fields=["name", "date_vente", "facture_vente"], order_by="date_vente asc, creation asc",
	)
	result = []
	for row in rows:
		if not row.facture_vente:
			continue
		invoice = frappe.get_doc("Sales Invoice", row.facture_vente)
		if invoice.docstatus == 1 and flt(invoice.outstanding_amount) > 0:
			result.append({
				"vente_huilerie": row.name, "facture_vente": invoice.name,
				"date_vente": row.date_vente, "montant_facture": invoice.grand_total,
				"deja_regle": flt(invoice.grand_total) - flt(invoice.outstanding_amount),
				"reste_avant": invoice.outstanding_amount,
			})
	return result


@frappe.whitelist()
def get_compte_paiement_client(mode_paiement, societe):
	account = frappe.db.get_value(
		"Mode of Payment Account",
		{"parent": mode_paiement, "parenttype": "Mode of Payment", "company": societe},
		"default_account",
	)
	if not account:
		frappe.throw(_("Aucun compte par défaut n'est configuré pour ce mode de paiement."))
	return account
