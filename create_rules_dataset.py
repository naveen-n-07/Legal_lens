import json
import csv
import os

rules_data = [
    {
        "rule_id": "LMPCR_R6_1_a",
        "rule_category": "Mandatory Labeling",
        "statutory_reference": "Rule 6(1)(a)",
        "target_parameter": "manufacturer_packer_importer_details",
        "compliance_condition": "Every package must declare the name and complete address of the manufacturer, or packer, or importer, including street, city, state, and PIN code (or factory address). Food items fall under FSSAI Act, 2006.",
        "violation_condition": "Missing manufacturer/packer/importer name, missing complete postal address, or missing PIN code on retail package (unless package volume <= 10 cm3 under Rule 10(1))."
    },
    {
        "rule_id": "LMPCR_R6_1_aa",
        "rule_category": "Country of Origin",
        "statutory_reference": "Rule 6(1)(aa)",
        "target_parameter": "country_of_origin",
        "compliance_condition": "For imported products, the name of the country of origin or manufacture or assembly must be clearly mentioned on the package.",
        "violation_condition": "Imported pre-packaged commodity lacks explicit declaration of country of origin or country of manufacture/assembly."
    },
    {
        "rule_id": "LMPCR_R6_1_b",
        "rule_category": "Mandatory Labeling",
        "statutory_reference": "Rule 6(1)(b)",
        "target_parameter": "common_generic_name",
        "compliance_condition": "The common or generic name of the commodity contained in the package must be prominently declared on the principal display panel.",
        "violation_condition": "Pre-packaged commodity lacks a clear common or generic name, or name is misleading/ambiguous."
    },
    {
        "rule_id": "LMPCR_R6_1_c",
        "rule_category": "Net Quantity",
        "statutory_reference": "Rule 6(1)(c)",
        "target_parameter": "net_quantity",
        "compliance_condition": "Net quantity must be declared in terms of standard unit of weight, measure or number (e.g. g, kg, ml, L, N, u). Unit symbols must conform strictly to SI metric standards.",
        "violation_condition": "Missing net quantity, non-standard unit symbols (e.g., gms, ltrs, kgs), or short-measure beyond maximum permissible error (MPE)."
    },
    {
        "rule_id": "LMPCR_R6_1_d",
        "rule_category": "Date Declaration",
        "statutory_reference": "Rule 6(1)(d)",
        "target_parameter": "manufacturing_packing_date",
        "compliance_condition": "The month and year in which the commodity is manufactured or packed or imported must be declared on the package (Format: MM/YYYY or Month Year). Spare parts/accessories for servicing with warranty exempt from 01-04-2024.",
        "violation_condition": "Missing month and year of manufacture/packing/import, or invalid date format, unless explicitly exempted."
    },
    {
        "rule_id": "LMPCR_R6_1_da",
        "rule_category": "Date Declaration",
        "statutory_reference": "Rule 6(1)(da)",
        "target_parameter": "expiry_best_before_date",
        "compliance_condition": "If a commodity may become unfit for human consumption after a period of time, 'Best before' or 'Use by' date, month, and year must be declared on the label.",
        "violation_condition": "Perishable item lacking 'Best Before' or 'Use By' date/month/year declaration."
    },
    {
        "rule_id": "LMPCR_R6_1_e",
        "rule_category": "Pricing",
        "statutory_reference": "Rule 6(1)(e)",
        "target_parameter": "mrp",
        "compliance_condition": "Maximum Retail Price (MRP) must be declared clearly indicating 'Maximum retail price Rs. XX.XX (inclusive of all taxes)' or 'MRP Rs. XX.XX incl. of all taxes'. Price rounded to nearest rupee or 50 paise.",
        "violation_condition": "Missing MRP, missing 'inclusive of all taxes' clause, price listed with multiple taxes added separately, or price exceeding maximum retail price."
    },
    {
        "rule_id": "LMPCR_R6_1_ea",
        "rule_category": "Consumer Care",
        "statutory_reference": "Rule 6(1)(ea)",
        "target_parameter": "consumer_care_details",
        "compliance_condition": "Every package must declare the name, address, telephone number, and email address of the person or office that can be contacted in case of consumer complaints.",
        "violation_condition": "Missing consumer care contact name, postal address, telephone number, or email ID on package."
    },
    {
        "rule_id": "LMPCR_R6_1_n",
        "rule_category": "Pricing",
        "statutory_reference": "Rule 6(1)(n)",
        "target_parameter": "unit_sale_price",
        "compliance_condition": "Unit Sale Price (USP) must be declared in Rupees per g/ml (if net qty < 1kg/1L) or per kg/L (if net qty >= 1kg/1L) or per piece. Exempt for combination, group, or multi-piece packages.",
        "violation_condition": "Missing Unit Sale Price on eligible single retail package, or incorrect USP calculation."
    },
    {
        "rule_id": "LMPCR_R6_10",
        "rule_category": "E-Commerce Disclosures",
        "statutory_reference": "Rule 6(10)",
        "target_parameter": "e_commerce_declarations",
        "compliance_condition": "An e-commerce entity must display all mandatory declarations under Rule 6(1) on its digital platform (except month/year of manufacture/packing). Marketplaces must ensure sellers provide this metadata.",
        "violation_condition": "E-commerce product listing missing mandatory declarations (MRP, Net Qty, Manufacturer details, Country of Origin, USP)."
    },
    {
        "rule_id": "LMPCR_R6_10A",
        "rule_category": "E-Commerce Disclosures",
        "statutory_reference": "Rule 6(10A)",
        "target_parameter": "e_commerce_coo_filter",
        "compliance_condition": "Every e-commerce entity selling imported products shall provide product listings in a searchable and sortable filter specifying the country of origin.",
        "violation_condition": "E-commerce website lacking searchable/sortable Country of Origin filter for imported commodities."
    },
    {
        "rule_id": "LMPCR_R7_2_T1",
        "rule_category": "Typography",
        "statutory_reference": "Rule 7(2) & Table-I",
        "target_parameter": "font_size_height",
        "compliance_condition": "Minimum height of numerals and letters on PDP: Area A <= 50 cm2: 1.0mm (1.5mm if blown/molded); 50 < A <= 100 cm2: 1.5mm (3.0mm molded); 100 < A <= 500 cm2: 2.5mm (4.0mm molded); 500 < A <= 2500 cm2: 4.0mm (6.0mm molded); A > 2500 cm2: 6.0mm.",
        "violation_condition": "Numeral or letter height on Principal Display Panel falls below mandatory minimum height for the given PDP area range."
    },
    {
        "rule_id": "LMPCR_R7_3",
        "rule_category": "Typography",
        "statutory_reference": "Rule 7(3)",
        "target_parameter": "letter_width_ratio",
        "compliance_condition": "The width of any letter or numeral in mandatory declarations shall not be less than 1/3 of its height (except numeral '1' and letters 'i', 'I').",
        "violation_condition": "Letter or numeral width is compressed to less than 1/3 of its height, rendering text illegible or non-compliant."
    },
    {
        "rule_id": "LMPCR_R10_1",
        "rule_category": "Mandatory Labeling",
        "statutory_reference": "Rule 10(1)",
        "target_parameter": "small_package_address",
        "compliance_condition": "Small packages having capacity of 10 cm3 or less are exempt from declaring complete address, but must declare manufacturer/packer/importer name and city/state.",
        "violation_condition": "Package capacity > 10 cm3 failing to declare complete postal address with street, city, state, and PIN code."
    },
    {
        "rule_id": "LMPCR_R18_1",
        "rule_category": "Pricing",
        "statutory_reference": "Rule 18(1)",
        "target_parameter": "overcharging_above_mrp",
        "compliance_condition": "No retail dealer or person shall sell any commodity in packaged form at a price exceeding the retail sale price (MRP) declared on the package.",
        "violation_condition": "Retail sale price charged to consumer exceeds the printed MRP declared on package label."
    },
    {
        "rule_id": "LMPCR_R18_2A",
        "rule_category": "Pricing",
        "statutory_reference": "Rule 18(2A)",
        "target_parameter": "duplicate_mrp",
        "compliance_condition": "No manufacturer or packer or importer shall declare different Maximum Retail Prices (Dual MRP) on an identical pre-packaged commodity by adopting restrictive or unfair trade practices.",
        "violation_condition": "Identical pre-packaged commodity sold with dual MRP (different prices for different retail outlets or geographic regions)."
    },
    {
        "rule_id": "LMPCR_R26_a",
        "rule_category": "Exemptions",
        "statutory_reference": "Rule 26(a)",
        "target_parameter": "small_quantity_exemption",
        "compliance_condition": "Packages containing net quantity of 10g or 10ml or less are exempt from PCR declarations, EXCEPT for tobacco and pan masala products.",
        "violation_condition": "Non-tobacco package <= 10g/10ml being cited for non-declaration, or tobacco/pan masala <= 10g omitting mandatory declarations."
    },
    {
        "rule_id": "LMPCR_R26_f",
        "rule_category": "Exemptions",
        "statutory_reference": "Rule 26(f)",
        "target_parameter": "garment_dimensions",
        "compliance_condition": "Garments or hosiery items sold in loose form at retail are exempt from full PCR declarations provided package/tag declares size (chest/waist/length in cm/inches), manufacturer name/address, MRP, net qty (1 piece), and consumer care.",
        "violation_condition": "Loose garment packaging failing to specify explicit body measurement dimensions (e.g. Chest 102 cm) or mandatory size declarations."
    },
    {
        "rule_id": "LMA_S36_1",
        "rule_category": "Enforcement Penalties",
        "statutory_reference": "Section 36(1), Legal Metrology Act, 2009",
        "target_parameter": "non_declaration_penalty",
        "compliance_condition": "Manufacturing, packing, importing, or selling pre-packaged commodities without mandatory declarations is a punishable statutory offence.",
        "violation_condition": "First offence: Fine up to Rs. 25,000; Second offence: Fine up to Rs. 50,000; Subsequent offence: Fine up to Rs. 1,00,000 or imprisonment up to 1 year, or both."
    },
    {
        "rule_id": "LMA_S36_2",
        "rule_category": "Enforcement Penalties",
        "statutory_reference": "Section 36(2), Legal Metrology Act, 2009",
        "target_parameter": "short_quantity_penalty",
        "compliance_condition": "Manufacturing or packing pre-packaged commodities with non-conforming net quantity (short weight/volume) is a punishable offence.",
        "violation_condition": "Short measure net quantity violation: Fine up to Rs. 10,000 to Rs. 50,000 with potential forfeiture of non-conforming goods."
    }
]

def export_datasets():
    target_dir = r"c:\SIH"
    json_path = os.path.join(target_dir, "legal_metrology_rules.json")
    csv_path = os.path.join(target_dir, "legal_metrology_rules.csv")

    # Save JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(rules_data, f, indent=2, ensure_ascii=False)
    print(f"Generated {json_path} with {len(rules_data)} atomic rules.")

    # Save CSV
    fieldnames = ["rule_id", "rule_category", "statutory_reference", "target_parameter", "compliance_condition", "violation_condition"]
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rules_data:
            writer.writerow(row)
    print(f"Generated {csv_path} with {len(rules_data)} atomic rules.")

if __name__ == "__main__":
    export_datasets()
