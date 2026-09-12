import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from acaht_balance.achat_balance.calculations import calculate_refundable_deposit
from acaht_balance.achat_balance.doctype.reglement_fournisseur_huilerie.reglement_fournisseur_huilerie import get_compte_mode_paiement


class RetourMateriel(Document):
	def validate(self):
		if (
			self.traitement_caution == "Rembourser en espèces/banque"
			and self.mode_paiement_caution and not self.compte_caution
		):
			self.compte_caution = get_compte_mode_paiement(self.mode_paiement_caution, self.societe)
		loan = frappe.get_doc("Pret Materiel", self.pret_materiel)
		if loan.docstatus != 1:
			frappe.throw(_("Le prêt doit être validé."))
		if getdate(self.date_retour) < getdate(loan.date_pret):
			frappe.throw(_("La date du retour ne peut pas précéder la date du prêt."))
		if self.fournisseur != loan.fournisseur or self.societe != loan.societe:
			frappe.throw(_("Le fournisseur et la société doivent correspondre au prêt."))
		loaned = {row.materiel: flt(row.quantite_pretee) for row in loan.materiels}
		seen = set()
		if not self.materiels:
			frappe.throw(_("Ajoutez au moins un matériel retourné, perdu ou endommagé."))
		for row in self.materiels:
			if row.materiel in seen or row.materiel not in loaned:
				frappe.throw(_("Matériel invalide ou dupliqué à la ligne {0}.").format(row.idx))
			seen.add(row.materiel)
			quantities = (flt(row.quantite_rendue), flt(row.quantite_perdue), flt(row.quantite_endommagee))
			if min(quantities) < 0:
				frappe.throw(_("Les quantités ne peuvent pas être négatives à la ligne {0}.").format(row.idx))
			current = sum(quantities)
			if current <= 0:
				frappe.throw(_("Saisissez une quantité à la ligne {0}.").format(row.idx))
			prior = frappe.db.sql(
				"""select coalesce(sum(l.quantite_rendue + l.quantite_perdue + l.quantite_endommagee), 0)
				from `tabLigne Retour Materiel` l inner join `tabRetour Materiel` r on r.name=l.parent
				where r.pret_materiel=%s and r.docstatus=1 and r.name!=%s and l.materiel=%s""",
				(self.pret_materiel, self.name or "", row.materiel),
			)[0][0]
			if prior + current > loaned[row.materiel]:
				frappe.throw(_("Le retour dépasse le solde prêté pour {0}.").format(row.materiel))
		deposit_rates = {row.materiel: flt(row.caution_unitaire) for row in loan.materiels}
		returned_value = sum(flt(row.quantite_rendue) * deposit_rates[row.materiel] for row in self.materiels)
		prior_returned_value = frappe.db.sql(
			"""select coalesce(sum(l.quantite_rendue * p.caution_unitaire), 0)
			from `tabLigne Retour Materiel` l
			inner join `tabRetour Materiel` r on r.name=l.parent
			inner join `tabLigne Pret Materiel` p on p.parent=r.pret_materiel and p.materiel=l.materiel
			where r.pret_materiel=%s and r.docstatus=1 and r.name!=%s""",
			(self.pret_materiel, self.name or ""),
		)[0][0]
		already_refunded = frappe.db.sql(
			"""select coalesce(sum(montant_caution_restituee), 0)
			from `tabRetour Materiel` where pret_materiel=%s and docstatus=1 and name!=%s""",
			(self.pret_materiel, self.name or ""),
		)[0][0]
		self.montant_caution_restituee = float(calculate_refundable_deposit(
			loan.montant_caution, loan.caution_versee,
			flt(prior_returned_value) + returned_value, already_refunded,
		))

	def on_submit(self):
		frappe.get_doc("Pret Materiel", self.pret_materiel).refresh_totals()
		self._creer_remboursement_caution()

	def on_cancel(self):
		if self.payment_entry_caution:
			payment = frappe.get_doc("Payment Entry", self.payment_entry_caution)
			if payment.docstatus == 1:
				payment.cancel()
		frappe.get_doc("Pret Materiel", self.pret_materiel).refresh_totals()

	def _creer_remboursement_caution(self):
		if self.traitement_caution != "Rembourser en espèces/banque" or not flt(self.montant_caution_restituee):
			return
		from erpnext.accounts.party import get_party_account
		party_account = get_party_account("Supplier", self.fournisseur, self.societe)
		payment = frappe.get_doc({
			"doctype": "Payment Entry", "payment_type": "Pay", "company": self.societe,
			"posting_date": self.date_retour, "mode_of_payment": self.mode_paiement_caution,
			"party_type": "Supplier", "party": self.fournisseur,
			"paid_from": self.compte_caution, "paid_to": party_account,
			"paid_amount": self.montant_caution_restituee,
			"received_amount": self.montant_caution_restituee,
			"source_exchange_rate": 1, "target_exchange_rate": 1,
			"remarks": _("Remboursement de caution du prêt {0}").format(self.pret_materiel),
		})
		payment.insert()
		payment.submit()
		self.db_set("payment_entry_caution", payment.name)
