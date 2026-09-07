# Huilerie & Oliveraie pour ERPNext 16

Application Frappe/ERPNext destinée aux huileries qui achètent des olives, produisent de l'huile d'olive ou des olives de table, puis vendent les produits finis.

## Fonctionnalités disponibles

Le bureau ERPNext contient un espace de travail **Huilerie & Oliveraie** avec des
raccourcis organisés vers les principales opérations du module.

### Réception et achat des olives

- double pesée manuelle (entrée et sortie) ;
- tare des emballages et pourcentage de déchet ;
- calcul serveur du poids net, du poids payable, du montant et du solde fournisseur ;
- validation des valeurs incohérentes ;
- création contrôlée d'une réception d'achat ERPNext en brouillon.

### Production

- production d'huile d'olive ou d'olives de table ;
- matière première, lot interne, pertes et produits obtenus ;
- plusieurs produits finis et sous-produits ;
- calcul du rendement ;
- création d'un mouvement de stock ERPNext de type Repack en brouillon.

### Conditionnement et préparation à la vente

- consommation d'un lot d'huile ou d'olives de table en vrac ;
- plusieurs formats de vente dans une même opération ;
- calcul automatique des quantités conditionnées et des pertes ;
- contrôle empêchant de conditionner plus que la quantité disponible ;
- création d'un mouvement de stock `Repack` en brouillon pour alimenter le stock vendable.

### Prêt d'échelles et de caisses (sandok)

- catalogue du matériel avec catégorie et caution unitaire ;
- prêt de plusieurs types de matériel à un fournisseur ;
- date prévue de restitution et responsable ;
- retours complets ou partiels ;
- suivi séparé du matériel rendu, perdu et endommagé ;
- calcul du matériel restant et du montant de caution ;
- calcul du solde net à payer au fournisseur après retenue du matériel non rendu ;
- clôture automatique lorsque tout le matériel est régularisé.

Exemple : pour une dette fournisseur de 50 000 DA et 10 caisses non rendues à
1 000 DA, la retenue est de 10 000 DA et le solde net à payer est de 40 000 DA.

Les ventes, livraisons, factures, paiements, stocks et lots utilisent les fonctions standards d'ERPNext 16.

## Installation de développement

Dans un environnement Bench contenant ERPNext 16 :

```bash
bench get-app <url-du-depot>
bench --site <site> install-app acaht_balance
bench --site <site> migrate
bench build --app acaht_balance
```

Configurer ensuite :

1. les sociétés, fournisseurs et entrepôts ;
2. les unités `Kg` et `Litre` ;
3. les articles olives, huile, olives de table et emballages ;
4. le suivi par lots sur les articles concernés dans ERPNext ;
5. les rôles Purchase User/Manager et Manufacturing User/Manager.

## Principes de sécurité

Tous les calculs importants sont répétés côté serveur. Les documents ERPNext générés restent en brouillon et doivent être vérifiés avant soumission. La future connexion à une balance pourra remplacer la saisie manuelle sans changer le modèle métier.

## Tests

```bash
bench --site <site> run-tests --app acaht_balance
```

## Licence

MIT
