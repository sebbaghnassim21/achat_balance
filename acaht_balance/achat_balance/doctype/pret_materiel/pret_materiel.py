import frappe
from frappe import _
from frappe.model.document import Document

from acaht_balance.achat_balance.calculations import calculate_loan_line


class PretMateriel(Document):
	def validate(self):
		if self.date_retour_prevue and self.date_retour_prevue < self.date_pret:
			frappe.throw(_("La date de retour prévue ne peut pas précéder la date du prêt."))
		if not self.materiels:
			frappe.throw(_("Ajoutez au moins un matériel à prêter."))
		seen = set()
		total_deposit = 0
		for row in self.materiels:
			if row.materiel in seen:
				frappe.throw(_("Le matériel {0} apparaît plusieurs fois.").format(row.materiel))
			seen.add(row.materiel)
			try:
				result = calculate_loan_line(
					row.quantite_pretee, row.quantite_rendue, row.quantite_perdue,
					row.quantite_endommagee, row.caution_unitaire,
				)
			except ValueError as exc:
				frappe.throw(_("Ligne {0}: {1}").format(row.idx, str(exc)))
			row.quantite_restante = float(result["remaining"])
			row.montant_caution = float(result["deposit_amount"])
			total_deposit += row.montant_caution
		self.montant_caution = total_deposit

	def before_submit(self):
		self.statut = "En cours"

	def on_cancel(self):
		self.statut = "Annulé"

	def refresh_totals(self):
		for row in self.materiels:
			values = frappe.db.sql(
				"""select coalesce(sum(l.quantite_rendue), 0),
				coalesce(sum(l.quantite_perdue), 0), coalesce(sum(l.quantite_endommagee), 0)
				from `tabLigne Retour Materiel` l
				inner join `tabRetour Materiel` r on r.name = l.parent
				where r.pret_materiel = %s and r.docstatus = 1 and l.materiel = %s""",
				(self.name, row.materiel),
			)[0]
			row.db_set("quantite_rendue", values[0], update_modified=False)
			row.db_set("quantite_perdue", values[1], update_modified=False)
			row.db_set("quantite_endommagee", values[2], update_modified=False)
			row.db_set("quantite_restante", row.quantite_pretee - sum(values), update_modified=False)
		remaining = sum(row.quantite_restante for row in self.materiels)
		status = "Clôturé" if remaining == 0 else "Partiellement rendu" if any(row.quantite_rendue or row.quantite_perdue or row.quantite_endommagee for row in self.materiels) else "En cours"
		self.db_set("statut", status, update_modified=False)
