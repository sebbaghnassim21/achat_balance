from decimal import Decimal, ROUND_HALF_UP


ZERO = Decimal("0")


def decimal_value(value) -> Decimal:
	if value in (None, ""):
		return ZERO
	return Decimal(str(value))


def round_quantity(value) -> Decimal:
	return decimal_value(value).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def round_money(value) -> Decimal:
	return decimal_value(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_reception(
	weight_in,
	weight_out,
	packaging_tare=0,
	waste_percent=0,
	rate=0,
	previous_balance=0,
	paid_amount=0,
):
	weight_in = decimal_value(weight_in)
	weight_out = decimal_value(weight_out)
	packaging_tare = decimal_value(packaging_tare)
	waste_percent = decimal_value(waste_percent)
	rate = decimal_value(rate)

	if min(weight_in, weight_out, packaging_tare, rate) < ZERO:
		raise ValueError("Les poids, la tare et le prix ne peuvent pas être négatifs.")
	if weight_out > weight_in:
		raise ValueError("Le poids de sortie ne peut pas dépasser le poids d'entrée.")
	if waste_percent < ZERO or waste_percent > Decimal("100"):
		raise ValueError("Le déchet doit être compris entre 0 et 100 %.")

	net_weight = weight_in - weight_out - packaging_tare
	if net_weight < ZERO:
		raise ValueError("La tare dépasse le poids net disponible.")

	payable_weight = net_weight * (Decimal("1") - waste_percent / Decimal("100"))
	amount = payable_weight * rate
	new_balance = decimal_value(previous_balance) + amount - decimal_value(paid_amount)

	return {
		"net_weight": round_quantity(net_weight),
		"payable_weight": round_quantity(payable_weight),
		"amount": round_money(amount),
		"new_balance": round_money(new_balance),
	}


def calculate_packaging_tare(lines):
	"""Return the total tare for ``(quantity, unit_weight)`` packaging lines."""
	total = ZERO
	for quantity, unit_weight in lines:
		quantity = decimal_value(quantity)
		unit_weight = decimal_value(unit_weight)
		if quantity <= ZERO:
			raise ValueError("La quantité d'emballages doit être supérieure à zéro.")
		if unit_weight <= ZERO:
			raise ValueError("Le poids unitaire de l'emballage doit être supérieur à zéro.")
		total += quantity * unit_weight
	return round_quantity(total)


def calculate_yield(input_quantity, output_quantity):
	input_quantity = decimal_value(input_quantity)
	output_quantity = decimal_value(output_quantity)
	if input_quantity <= ZERO:
		return ZERO
	return (output_quantity / input_quantity * Decimal("100")).quantize(
		Decimal("0.01"), rounding=ROUND_HALF_UP
	)


def calculate_packaging(source_quantity, lines):
	source_quantity = decimal_value(source_quantity)
	if source_quantity <= ZERO:
		raise ValueError("La quantité de vrac doit être supérieure à zéro.")

	total_packaged = ZERO
	for units, content_per_unit in lines:
		units = decimal_value(units)
		content_per_unit = decimal_value(content_per_unit)
		if units <= ZERO or content_per_unit <= ZERO:
			raise ValueError("Le nombre d'unités et la contenance doivent être positifs.")
		total_packaged += units * content_per_unit

	if total_packaged > source_quantity:
		raise ValueError("La quantité conditionnée dépasse la quantité de vrac disponible.")

	return {
		"packaged_quantity": round_quantity(total_packaged),
		"loss_quantity": round_quantity(source_quantity - total_packaged),
	}


def calculate_loan_line(loaned, returned=0, lost=0, damaged=0, deposit_rate=0):
	loaned = decimal_value(loaned)
	returned = decimal_value(returned)
	lost = decimal_value(lost)
	damaged = decimal_value(damaged)
	deposit_rate = decimal_value(deposit_rate)
	if loaned <= ZERO:
		raise ValueError("La quantité prêtée doit être supérieure à zéro.")
	if min(returned, lost, damaged, deposit_rate) < ZERO:
		raise ValueError("Les quantités et la caution ne peuvent pas être négatives.")
	processed = returned + lost + damaged
	if processed > loaned:
		raise ValueError("Le total rendu, perdu et endommagé dépasse la quantité prêtée.")
	return {
		"remaining": round_quantity(loaned - processed),
		"deposit_amount": round_money(loaned * deposit_rate),
	}


def calculate_supplier_settlement(supplier_debt, material_value, deposit_paid=0):
	supplier_debt = decimal_value(supplier_debt)
	material_value = decimal_value(material_value)
	deposit_paid = decimal_value(deposit_paid)
	if supplier_debt < ZERO or material_value < ZERO or deposit_paid < ZERO:
		raise ValueError("Le crédit fournisseur, le matériel et la caution ne peuvent pas être négatifs.")
	material_retention = max(ZERO, material_value - deposit_paid)
	return {
		"supplier_debt": round_money(supplier_debt),
		"material_value": round_money(material_value),
		"deposit_paid": round_money(deposit_paid),
		"material_retention": round_money(material_retention),
		"net_payable": round_money(supplier_debt - material_retention),
	}


def calculate_refundable_deposit(total_material_value, deposit_paid, returned_value, already_refunded=0):
	total_material_value = decimal_value(total_material_value)
	deposit_paid = decimal_value(deposit_paid)
	returned_value = decimal_value(returned_value)
	already_refunded = decimal_value(already_refunded)
	if min(total_material_value, deposit_paid, returned_value, already_refunded) < ZERO:
		raise ValueError("Les valeurs de caution ne peuvent pas être négatives.")
	if deposit_paid == ZERO or total_material_value == ZERO:
		return ZERO
	cumulative = min(deposit_paid, deposit_paid * returned_value / total_material_value)
	return round_money(max(ZERO, cumulative - already_refunded))


def calculate_sale_total(lines):
	total = ZERO
	for quantity, rate in lines:
		quantity = decimal_value(quantity)
		rate = decimal_value(rate)
		if quantity <= ZERO or rate < ZERO:
			raise ValueError("La quantité doit être positive et le prix ne peut pas être négatif.")
		total += quantity * rate
	return round_money(total)


def calculate_customer_payment(outstanding, amount):
	outstanding = decimal_value(outstanding)
	amount = decimal_value(amount)
	if amount <= ZERO or amount > outstanding:
		raise ValueError("Le paiement doit être positif et ne pas dépasser le solde de la facture.")
	return {"paid": round_money(amount), "remaining": round_money(outstanding - amount)}


def allocate_customer_payment(outstandings, amount):
	amount = decimal_value(amount)
	values = [decimal_value(value) for value in outstandings]
	if amount <= ZERO:
		raise ValueError("Le montant réglé doit être supérieur à zéro.")
	if amount > sum(values, ZERO):
		raise ValueError("Le montant réglé ne peut pas dépasser le montant global dû.")
	remaining = amount
	allocations = []
	for outstanding in values:
		allocated = min(outstanding, remaining)
		allocations.append(round_money(allocated))
		remaining -= allocated
	return allocations
