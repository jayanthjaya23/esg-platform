# SOURCES.md

# Source Research and Real-World Assumptions

## 1. SAP Procurement / Fuel Exports

### Research

Reviewed:

* SAP MM export examples
* fuel procurement datasets
* enterprise procurement CSV structures

### Key Learnings

SAP exports often contain:

* inconsistent headers
* procurement categories
* mixed units
* duplicated vendor fields

### Sample Data Design

The prototype includes:

* fuel combustion examples
* procurement quantities
* Scope 1 categorization

### Real-World Limitations

Production deployments would require:

* ERP authentication
* supplier mapping
* regional emissions factors
* schema versioning

Potential breakpoints:

* inconsistent SAP customizations
* multi-language exports
* malformed CSV encoding

---

# 2. Utility Consumption Data

### Research

Reviewed:

* utility billing exports
* electricity consumption reports
* smart-meter CSV examples

### Key Learnings

Utility exports commonly include:

* kWh usage
* billing periods
* inconsistent meter identifiers

### Sample Data Design

The prototype includes:

* electricity consumption rows
* Scope 2 mapping
* kWh normalization

### Real-World Limitations

Production deployments would require:

* interval usage handling
* OCR parsing
* smart-meter integrations
* regional grid emission factors

Potential breakpoints:

* timezone inconsistencies
* partial billing cycles
* utility-specific schemas

---

# 3. Corporate Travel Data

### Research

Reviewed:

* travel management exports
* Concur examples
* mileage reimbursement reports

### Key Learnings

Travel exports typically contain:

* employee travel records
* mileage
* travel class
* destinations

### Sample Data Design

The prototype includes:

* mileage-based examples
* Scope 3 categorization
* simplified emissions estimates

### Real-World Limitations

Production deployments would require:

* airline class calculations
* hotel emissions
* route-specific factors
* international travel handling

Potential breakpoints:

* missing trip metadata
* inconsistent units
* incomplete expense reports
