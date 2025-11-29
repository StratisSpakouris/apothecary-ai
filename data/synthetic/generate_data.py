"""
Synthetic Data Generator for Apothecary AI

Generates realistic pharmacy data for demonstration:
- Patient prescription history (12 months)
- Current inventory with lot numbers and expiration dates
- Medication database

Usage:
    python data/synthetic/generate_data.py
    
    # Or with custom parameters:
    python data/synthetic/generate_data.py --patients 500 --months 18
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import random

# Seed for reproducibility
np.random.seed(42)
random.seed(42)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


# =============================================================================
# MEDICATION DATABASE
# =============================================================================

MEDICATIONS = {
    # Diabetes medications
    "Metformin 500mg": {
        "category": "diabetes",
        "unit_cost": 2.50,
        "shelf_life_months": 24,
        "case_size": 100,
        "daily_doses": 2,
        "is_chronic": True
    },
    "Metformin 1000mg": {
        "category": "diabetes",
        "unit_cost": 3.00,
        "shelf_life_months": 24,
        "case_size": 100,
        "daily_doses": 2,
        "is_chronic": True
    },
    "Insulin Glargine": {
        "category": "diabetes",
        "unit_cost": 45.00,
        "shelf_life_months": 18,
        "case_size": 10,
        "daily_doses": 1,
        "is_chronic": True
    },
    
    # Cardiovascular medications
    "Lisinopril 10mg": {
        "category": "cardiovascular",
        "unit_cost": 1.20,
        "shelf_life_months": 36,
        "case_size": 100,
        "daily_doses": 1,
        "is_chronic": True
    },
    "Lisinopril 20mg": {
        "category": "cardiovascular",
        "unit_cost": 1.50,
        "shelf_life_months": 36,
        "case_size": 100,
        "daily_doses": 1,
        "is_chronic": True
    },
    "Atorvastatin 20mg": {
        "category": "cardiovascular",
        "unit_cost": 2.00,
        "shelf_life_months": 36,
        "case_size": 100,
        "daily_doses": 1,
        "is_chronic": True
    },
    "Amlodipine 5mg": {
        "category": "cardiovascular",
        "unit_cost": 1.80,
        "shelf_life_months": 36,
        "case_size": 100,
        "daily_doses": 1,
        "is_chronic": True
    },
    
    # Antivirals (seasonal)
    "Tamiflu 75mg": {
        "category": "antiviral",
        "unit_cost": 18.00,
        "shelf_life_months": 18,
        "case_size": 50,
        "daily_doses": 2,
        "is_chronic": False
    },
    
    # Antibiotics (acute)
    "Amoxicillin 500mg": {
        "category": "antibiotic",
        "unit_cost": 0.80,
        "shelf_life_months": 24,
        "case_size": 50,
        "daily_doses": 3,
        "is_chronic": False
    },
    "Azithromycin 250mg": {
        "category": "antibiotic",
        "unit_cost": 2.50,
        "shelf_life_months": 24,
        "case_size": 30,
        "daily_doses": 1,
        "is_chronic": False
    },
    
    # Gastrointestinal
    "Omeprazole 20mg": {
        "category": "gastrointestinal",
        "unit_cost": 1.50,
        "shelf_life_months": 24,
        "case_size": 100,
        "daily_doses": 1,
        "is_chronic": True
    },
    "Pantoprazole 40mg": {
        "category": "gastrointestinal",
        "unit_cost": 2.00,
        "shelf_life_months": 24,
        "case_size": 100,
        "daily_doses": 1,
        "is_chronic": True
    },
    
    # Thyroid
    "Levothyroxine 50mcg": {
        "category": "thyroid",
        "unit_cost": 1.00,
        "shelf_life_months": 24,
        "case_size": 100,
        "daily_doses": 1,
        "is_chronic": True
    },
    "Levothyroxine 100mcg": {
        "category": "thyroid",
        "unit_cost": 1.20,
        "shelf_life_months": 24,
        "case_size": 100,
        "daily_doses": 1,
        "is_chronic": True
    },
    
    # Respiratory
    "Albuterol Inhaler": {
        "category": "respiratory",
        "unit_cost": 25.00,
        "shelf_life_months": 12,
        "case_size": 12,
        "daily_doses": 0.5,  # As needed
        "is_chronic": True
    },
    
    # Mental health
    "Sertraline 50mg": {
        "category": "mental_health",
        "unit_cost": 1.50,
        "shelf_life_months": 36,
        "case_size": 100,
        "daily_doses": 1,
        "is_chronic": True
    },
    
    # Pain management
    "Gabapentin 300mg": {
        "category": "pain",
        "unit_cost": 0.80,
        "shelf_life_months": 36,
        "case_size": 100,
        "daily_doses": 3,
        "is_chronic": True
    },
    
    # Allergy (seasonal)
    "Cetirizine 10mg": {
        "category": "allergy",
        "unit_cost": 0.30,
        "shelf_life_months": 36,
        "case_size": 100,
        "daily_doses": 1,
        "is_chronic": False
    },
    "Fluticasone Nasal Spray": {
        "category": "allergy",
        "unit_cost": 15.00,
        "shelf_life_months": 24,
        "case_size": 12,
        "daily_doses": 1,
        "is_chronic": False
    },
}

# Chronic medications list (for patient assignment)
CHRONIC_MEDICATIONS = [med for med, info in MEDICATIONS.items() if info["is_chronic"]]
ACUTE_MEDICATIONS = [med for med, info in MEDICATIONS.items() if not info["is_chronic"]]


# =============================================================================
# PATIENT BEHAVIOR TYPES
# =============================================================================

PATIENT_BEHAVIORS = {
    "highly_regular": {
        "probability": 0.30,          # 30% of patients
        "refill_interval_std": 2,     # Very consistent (±2 days)
        "skip_probability": 0.02,     # Rarely misses refills
        "early_refill_probability": 0.05
    },
    "regular": {
        "probability": 0.45,          # 45% of patients
        "refill_interval_std": 4,     # Somewhat consistent (±4 days)
        "skip_probability": 0.08,     # Occasionally misses
        "early_refill_probability": 0.10
    },
    "irregular": {
        "probability": 0.20,          # 20% of patients
        "refill_interval_std": 8,     # Variable (±8 days)
        "skip_probability": 0.15,     # Sometimes misses
        "early_refill_probability": 0.15
    },
    "new_patient": {
        "probability": 0.05,          # 5% of patients
        "refill_interval_std": 5,
        "skip_probability": 0.30,     # May not return
        "early_refill_probability": 0.05
    }
}


# =============================================================================
# DATA GENERATION FUNCTIONS
# =============================================================================

def generate_medication_database() -> pd.DataFrame:
    """
    Generate medication database with all drug information.
    
    Returns:
        DataFrame with medication details
    """
    records = []
    for med_name, med_info in MEDICATIONS.items():
        records.append({
            "medication": med_name,
            "category": med_info["category"],
            "unit_cost": med_info["unit_cost"],
            "shelf_life_months": med_info["shelf_life_months"],
            "case_size": med_info["case_size"],
            "daily_doses": med_info["daily_doses"],
            "is_chronic": med_info["is_chronic"]
        })
    
    return pd.DataFrame(records)


def assign_patient_behavior() -> str:
    """Randomly assign a behavior type to a patient."""
    rand = random.random()
    cumulative = 0
    for behavior, params in PATIENT_BEHAVIORS.items():
        cumulative += params["probability"]
        if rand < cumulative:
            return behavior
    return "regular"  # Fallback


def generate_patient_medications(patient_id: str, num_chronic: int = None) -> list:
    """
    Assign medications to a patient.
    
    Most patients on 1-3 chronic medications.
    """
    if num_chronic is None:
        # Realistic distribution: most patients on 1-2 meds
        num_chronic = np.random.choice([1, 2, 3, 4], p=[0.40, 0.35, 0.20, 0.05])
    
    medications = random.sample(CHRONIC_MEDICATIONS, min(num_chronic, len(CHRONIC_MEDICATIONS)))
    return medications


def generate_refill_history(
    patient_id: str,
    medication: str,
    behavior: str,
    start_date: datetime,
    end_date: datetime
) -> list:
    """
    Generate refill history for one patient-medication combination.
    
    Args:
        patient_id: Patient identifier
        medication: Medication name
        behavior: Patient behavior type
        start_date: Start of history period
        end_date: End of history period
        
    Returns:
        List of prescription fill records
    """
    behavior_params = PATIENT_BEHAVIORS[behavior]
    med_info = MEDICATIONS[medication]
    
    # Base refill interval (typically 30 days for chronic meds, 90 for some)
    base_interval = 30
    if med_info["is_chronic"]:
        # Some patients get 90-day supplies
        supply_days = random.choice([30, 30, 30, 90])  # 75% get 30-day, 25% get 90-day
    else:
        supply_days = 10  # Acute medications
    
    records = []
    current_date = start_date + timedelta(days=random.randint(0, 30))  # Stagger start dates
    
    while current_date < end_date:
        # Check if patient skips this refill
        if random.random() < behavior_params["skip_probability"]:
            current_date += timedelta(days=supply_days)
            continue
        
        # Calculate actual fill date (with variation)
        variation = np.random.normal(0, behavior_params["refill_interval_std"])
        
        # Early refill check
        if random.random() < behavior_params["early_refill_probability"]:
            variation -= random.randint(3, 7)  # 3-7 days early
        
        fill_date = current_date + timedelta(days=int(variation))
        
        # Ensure fill date is within bounds
        if fill_date < start_date:
            fill_date = start_date
        if fill_date >= end_date:
            break
        
        # Calculate quantity (based on supply days and daily doses)
        quantity = int(supply_days * med_info["daily_doses"])
        if quantity < 1:
            quantity = supply_days  # Minimum 1 per day
        
        records.append({
            "patient_id": patient_id,
            "medication": medication,
            "fill_date": fill_date.strftime("%Y-%m-%d"),
            "quantity": quantity,
            "days_supply": supply_days,
            "behavior_type": behavior
        })
        
        # Move to next expected refill
        current_date += timedelta(days=supply_days)
    
    return records


def generate_prescription_history(
    num_patients: int = 200,
    months: int = 12
) -> pd.DataFrame:
    """
    Generate complete prescription history for all patients.
    
    Args:
        num_patients: Number of patients to generate
        months: Number of months of history
        
    Returns:
        DataFrame with all prescription records
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    
    all_records = []
    
    for i in range(num_patients):
        patient_id = f"P{i+1:04d}"
        
        # Assign behavior type
        behavior = assign_patient_behavior()
        
        # Assign medications
        medications = generate_patient_medications(patient_id)
        
        # Generate refill history for each medication
        for medication in medications:
            records = generate_refill_history(
                patient_id=patient_id,
                medication=medication,
                behavior=behavior,
                start_date=start_date,
                end_date=end_date
            )
            all_records.extend(records)
    
    df = pd.DataFrame(all_records)
    
    # Sort by date
    df["fill_date"] = pd.to_datetime(df["fill_date"])
    df = df.sort_values(["fill_date", "patient_id"]).reset_index(drop=True)
    
    return df


def generate_current_inventory(prescription_history: pd.DataFrame) -> pd.DataFrame:
    """
    Generate current inventory based on prescription patterns.
    
    Creates realistic inventory levels with multiple lots and expiration dates.
    
    Args:
        prescription_history: Historical prescription data
        
    Returns:
        DataFrame with current inventory
    """
    today = datetime.now()
    
    # Calculate average monthly demand per medication
    recent_history = prescription_history[
        prescription_history["fill_date"] >= (today - timedelta(days=90))
    ]
    
    monthly_demand = (
        recent_history
        .groupby("medication")["quantity"]
        .sum()
        .div(3)  # 3 months
        .to_dict()
    )
    
    inventory_records = []
    
    for med_name, med_info in MEDICATIONS.items():
        demand = monthly_demand.get(med_name, 10)  # Default demand if not in history
        
        # Target: 2-4 weeks of inventory
        target_stock = int(demand * random.uniform(0.5, 1.0))
        
        # Create 1-3 lots per medication
        num_lots = random.randint(1, 3)
        remaining_stock = target_stock
        
        for lot_num in range(num_lots):
            if remaining_stock <= 0:
                break
            
            # Lot quantity
            if lot_num == num_lots - 1:
                lot_quantity = remaining_stock
            else:
                lot_quantity = int(remaining_stock * random.uniform(0.3, 0.6))
            
            remaining_stock -= lot_quantity
            
            if lot_quantity <= 0:
                continue
            
            # Expiration date (spread across shelf life)
            months_until_expiry = random.randint(
                2,  # At least 2 months
                med_info["shelf_life_months"]
            )
            expiration_date = today + timedelta(days=months_until_expiry * 30)
            
            # Lot number
            lot_number = f"LOT{med_name[:3].upper()}{random.randint(1000, 9999)}"
            
            inventory_records.append({
                "medication": med_name,
                "lot_number": lot_number,
                "quantity": lot_quantity,
                "unit_cost": med_info["unit_cost"],
                "expiration_date": expiration_date.strftime("%Y-%m-%d"),
                "days_until_expiry": months_until_expiry * 30,
                "received_date": (today - timedelta(days=random.randint(7, 60))).strftime("%Y-%m-%d")
            })
    
    df = pd.DataFrame(inventory_records)
    df = df.sort_values(["medication", "expiration_date"]).reset_index(drop=True)
    
    return df


def generate_all_data(num_patients: int = 200, months: int = 12):
    """
    Generate all synthetic data and save to CSV files.
    
    Args:
        num_patients: Number of patients
        months: Months of history
    """
    print("=" * 60)
    print("APOTHECARY AI - SYNTHETIC DATA GENERATOR")
    print("=" * 60)
    
    # Create directories
    (DATA_DIR / "raw" / "patients").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "raw" / "inventory").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "raw" / "medications").mkdir(parents=True, exist_ok=True)
    
    # Generate medication database
    print("\n[1/3] Generating medication database...")
    medications_df = generate_medication_database()
    medications_path = DATA_DIR / "raw" / "medications" / "medication_database.csv"
    medications_df.to_csv(medications_path, index=False)
    print(f"  ✓ Created {len(medications_df)} medications")
    print(f"  ✓ Saved to: {medications_path}")
    
    # Generate prescription history
    print(f"\n[2/3] Generating prescription history ({num_patients} patients, {months} months)...")
    prescriptions_df = generate_prescription_history(num_patients, months)
    prescriptions_path = DATA_DIR / "raw" / "patients" / "prescription_history.csv"
    prescriptions_df.to_csv(prescriptions_path, index=False)
    print(f"  ✓ Created {len(prescriptions_df)} prescription records")
    print(f"  ✓ Unique patients: {prescriptions_df['patient_id'].nunique()}")
    print(f"  ✓ Date range: {prescriptions_df['fill_date'].min()} to {prescriptions_df['fill_date'].max()}")
    print(f"  ✓ Saved to: {prescriptions_path}")
    
    # Generate current inventory
    print("\n[3/3] Generating current inventory...")
    inventory_df = generate_current_inventory(prescriptions_df)
    inventory_path = DATA_DIR / "raw" / "inventory" / "current_stock.csv"
    inventory_df.to_csv(inventory_path, index=False)
    print(f"  ✓ Created {len(inventory_df)} inventory lots")
    print(f"  ✓ Total units: {inventory_df['quantity'].sum():,}")
    print(f"  ✓ Total value: ${(inventory_df['quantity'] * inventory_df['unit_cost']).sum():,.2f}")
    print(f"  ✓ Saved to: {inventory_path}")
    
    # Summary statistics
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE - SUMMARY")
    print("=" * 60)
    
    print("\nPrescription History by Behavior Type:")
    behavior_counts = prescriptions_df.groupby("behavior_type")["patient_id"].nunique()
    for behavior, count in behavior_counts.items():
        print(f"  • {behavior}: {count} patients")
    
    print("\nTop 5 Medications by Volume:")
    top_meds = prescriptions_df.groupby("medication")["quantity"].sum().nlargest(5)
    for med, qty in top_meds.items():
        print(f"  • {med}: {qty:,} units")
    
    print("\nInventory Alerts:")
    low_stock = inventory_df.groupby("medication")["quantity"].sum()
    for med in low_stock[low_stock < 20].index:
        print(f"  ⚠ Low stock: {med} ({low_stock[med]} units)")
    
    expiring_soon = inventory_df[inventory_df["days_until_expiry"] < 90]
    for _, row in expiring_soon.iterrows():
        print(f"  ⚠ Expiring soon: {row['medication']} ({row['quantity']} units, {row['days_until_expiry']} days)")
    
    print("\n✓ All data files generated successfully!")
    print(f"\nData location: {DATA_DIR / 'raw'}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate synthetic pharmacy data for Apothecary AI"
    )
    parser.add_argument(
        "--patients",
        type=int,
        default=200,
        help="Number of patients to generate (default: 200)"
    )
    parser.add_argument(
        "--months",
        type=int,
        default=12,
        help="Months of prescription history (default: 12)"
    )
    
    args = parser.parse_args()
    
    generate_all_data(num_patients=args.patients, months=args.months)
