import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class RetourMateriel(Document):
	def validate(self):
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

	def on_submit(self):
		frappe.get_doc("Pret Materiel", self.pret_materiel).refresh_totals()

	def on_cancel(self):
		frappe.get_doc("Pret Materiel", self.pret_materiel).refresh_totals()
