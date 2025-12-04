#!/usr/bin/env python3
"""
Emergency Room Data Generator
Generates 48 hours of stochastic FHIR and HL7 patient data for an ER setting.
"""

import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np
from faker import Faker
from fhir.resources.patient import Patient
from fhir.resources.humanname import HumanName
from fhir.resources.encounter import Encounter
from fhir.resources.condition import Condition
from fhir.resources.observation import Observation
from fhir.resources.coding import Coding
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.reference import Reference
from fhir.resources.period import Period
from fhir.resources.identifier import Identifier

fake = Faker()
Faker.seed(42)
random.seed(42)
np.random.seed(42)

# ER-specific disease/condition types with ICD-10 codes
ER_CONDITIONS = [
    {"name": "Chest Pain", "icd10": "R06.02", "severity": "high", "avg_duration_min": 180},
    {"name": "Abdominal Pain", "icd10": "R10.9", "severity": "medium", "avg_duration_min": 120},
    {"name": "Shortness of Breath", "icd10": "R06.02", "severity": "high", "avg_duration_min": 150},
    {"name": "Fever", "icd10": "R50.9", "severity": "medium", "avg_duration_min": 90},
    {"name": "Headache", "icd10": "R51", "severity": "low", "avg_duration_min": 60},
    {"name": "Trauma - Laceration", "icd10": "S01.9", "severity": "medium", "avg_duration_min": 90},
    {"name": "Fracture", "icd10": "S72.9", "severity": "high", "avg_duration_min": 240},
    {"name": "Asthma Exacerbation", "icd10": "J45.901", "severity": "high", "avg_duration_min": 180},
    {"name": "Hypertension", "icd10": "I10", "severity": "medium", "avg_duration_min": 120},
    {"name": "Urinary Tract Infection", "icd10": "N39.0", "severity": "medium", "avg_duration_min": 100},
    {"name": "Pneumonia", "icd10": "J18.9", "severity": "high", "avg_duration_min": 300},
    {"name": "Dehydration", "icd10": "E86.0", "severity": "medium", "avg_duration_min": 120},
    {"name": "Gastroenteritis", "icd10": "K52.9", "severity": "medium", "avg_duration_min": 150},
    {"name": "Back Pain", "icd10": "M54.5", "severity": "low", "avg_duration_min": 90},
    {"name": "Seizure", "icd10": "R56.9", "severity": "high", "avg_duration_min": 200},
    {"name": "Syncope", "icd10": "R55", "severity": "medium", "avg_duration_min": 120},
    {"name": "Alcohol Intoxication", "icd10": "F10.129", "severity": "medium", "avg_duration_min": 180},
    {"name": "Drug Overdose", "icd10": "T50.901A", "severity": "high", "avg_duration_min": 240},
    {"name": "Burn", "icd10": "T30.0", "severity": "high", "avg_duration_min": 200},
    {"name": "Anaphylaxis", "icd10": "T78.2XXA", "severity": "high", "avg_duration_min": 150},
]

# Common vital signs with normal ranges
VITAL_SIGNS = {
    "temperature": {"unit": "F", "normal_range": (97.0, 99.5), "abnormal_range": (95.0, 104.0)},
    "heart_rate": {"unit": "bpm", "normal_range": (60, 100), "abnormal_range": (40, 150)},
    "blood_pressure_systolic": {"unit": "mmHg", "normal_range": (90, 120), "abnormal_range": (70, 180)},
    "blood_pressure_diastolic": {"unit": "mmHg", "normal_range": (60, 80), "abnormal_range": (40, 120)},
    "respiratory_rate": {"unit": "/min", "normal_range": (12, 20), "abnormal_range": (8, 30)},
    "oxygen_saturation": {"unit": "%", "normal_range": (95, 100), "abnormal_range": (85, 100)},
}


class ERDataGenerator:
    """Generates stochastic ER patient data in FHIR and HL7 formats."""
    
    def __init__(self, start_time: datetime, duration_hours: int = 48):
        self.start_time = start_time
        self.end_time = start_time + timedelta(hours=duration_hours)
        self.current_time = start_time
        self.patients = []
        self.patient_counter = 1
        self.resource_counter = 1
    
    def _ensure_timezone_aware(self, dt: datetime) -> datetime:
        """Ensure a datetime is timezone-aware."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
        
    def generate_arrival_times(self) -> List[datetime]:
        """Generate stochastic arrival times using Poisson process (typical for ER)."""
        arrivals = []
        current = self.start_time
        
        # ER typically has 2-8 patients per hour, with peaks in evening
        while current < self.end_time:
            # Higher arrival rate in evening (6 PM - 2 AM)
            hour = current.hour
            if 18 <= hour or hour < 2:
                lambda_rate = random.uniform(4, 8)  # patients per hour
            elif 2 <= hour < 8:
                lambda_rate = random.uniform(1, 3)  # lower in early morning
            else:
                lambda_rate = random.uniform(2, 5)  # moderate during day
            
            # Exponential inter-arrival times
            inter_arrival_minutes = np.random.exponential(60 / lambda_rate)
            current += timedelta(minutes=inter_arrival_minutes)
            
            if current < self.end_time:
                arrivals.append(current)
        
        return arrivals
    
    def generate_patient(self, arrival_time: datetime) -> Dict:
        """Generate a single patient with demographics."""
        gender = random.choice(["male", "female", "other"])
        birth_date = fake.date_of_birth(minimum_age=0, maximum_age=100)
        
        patient_data = {
            "id": f"PAT{self.patient_counter:06d}",
            "mrn": f"MRN{random.randint(100000, 999999)}",
            "arrival_time": arrival_time,
            "name": fake.name(),
            "gender": gender,
            "birth_date": birth_date,
            "address": fake.address(),
            "phone": fake.phone_number(),
        }
        
        self.patient_counter += 1
        return patient_data
    
    def select_condition(self, patient_data: Dict) -> Dict:
        """Select a condition based on patient demographics and stochastic factors."""
        age = (datetime.now().date() - patient_data["birth_date"]).days // 365
        
        # Weight conditions based on age and other factors
        available_conditions = ER_CONDITIONS.copy()
        
        # Adjust probabilities based on age
        if age < 18:
            # Pediatric conditions more likely
            available_conditions.extend([
                {"name": "Pediatric Fever", "icd10": "R50.9", "severity": "medium", "avg_duration_min": 90},
                {"name": "Croup", "icd10": "J05.0", "severity": "medium", "avg_duration_min": 120},
            ])
        elif age > 65:
            # Geriatric conditions more likely
            available_conditions.extend([
                {"name": "Fall", "icd10": "W19.XXXA", "severity": "high", "avg_duration_min": 180},
                {"name": "Confusion", "icd10": "R41.82", "severity": "medium", "avg_duration_min": 150},
            ])
        
        condition = random.choice(available_conditions)
        
        # Add some variation to duration
        duration_minutes = int(
            condition["avg_duration_min"] * random.uniform(0.5, 2.0)
        )
        
        return {
            **condition,
            "duration_minutes": duration_minutes,
            "discharge_time": patient_data["arrival_time"] + timedelta(minutes=duration_minutes),
        }
    
    def generate_vitals(self, condition: Dict) -> Dict:
        """Generate realistic vital signs based on condition."""
        vitals = {}
        
        for vital_name, vital_info in VITAL_SIGNS.items():
            # Higher severity conditions more likely to have abnormal vitals
            if condition["severity"] == "high" and random.random() < 0.7:
                # Abnormal range
                min_val, max_val = vital_info["abnormal_range"]
            elif condition["severity"] == "medium" and random.random() < 0.4:
                min_val, max_val = vital_info["abnormal_range"]
            else:
                # Normal range
                min_val, max_val = vital_info["normal_range"]
            
            value = random.uniform(min_val, max_val)
            
            # Special adjustments for specific conditions
            if condition["name"] == "Fever" and vital_name == "temperature":
                value = random.uniform(100.0, 103.0)
            elif condition["name"] in ["Asthma Exacerbation", "Shortness of Breath"]:
                if vital_name == "respiratory_rate":
                    value = random.uniform(20, 30)
                elif vital_name == "oxygen_saturation":
                    value = random.uniform(88, 95)
            
            vitals[vital_name] = {
                "value": round(value, 1),
                "unit": vital_info["unit"]
            }
        
        return vitals
    
    def create_fhir_patient(self, patient_data: Dict) -> Patient:
        """Create a FHIR Patient resource."""
        name = HumanName()
        name.family = patient_data["name"].split()[-1]
        name.given = patient_data["name"].split()[:-1]
        
        identifier = Identifier()
        identifier.system = "http://hospital.example.org/patients"
        identifier.value = patient_data["mrn"]
        
        patient = Patient(
            id=patient_data["id"],
            identifier=[identifier],
            name=[name],
            gender=patient_data["gender"],
            birthDate=patient_data["birth_date"].isoformat(),
        )
        
        return patient
    
    def create_fhir_encounter(self, patient_data: Dict, condition: Dict) -> Encounter:
        """Create a FHIR Encounter resource."""
        # Ensure datetimes are timezone-aware
        arrival = self._ensure_timezone_aware(patient_data["arrival_time"])
        discharge = self._ensure_timezone_aware(condition["discharge_time"])
        
        period = Period()
        period.start = arrival.isoformat()
        period.end = discharge.isoformat()
        
        encounter_class_coding = Coding()
        encounter_class_coding.system = "http://terminology.hl7.org/CodeSystem/v3-ActCode"
        encounter_class_coding.code = "EMER"
        encounter_class_coding.display = "emergency"
        
        encounter_class = CodeableConcept()
        encounter_class.coding = [encounter_class_coding]
        
        enc_id = f"ENC{self.resource_counter}"
        self.resource_counter += 1
        encounter = Encounter(
            id=enc_id,
            status="completed",
            class_fhir=[encounter_class],
            actualPeriod=period,
            subject=Reference(reference=f"Patient/{patient_data['id']}"),
        )
        
        return encounter
    
    def create_fhir_condition(self, patient_data: Dict, condition: Dict) -> Condition:
        """Create a FHIR Condition resource."""
        coding = Coding()
        coding.system = "http://hl7.org/fhir/sid/icd-10-cm"
        coding.code = condition["icd10"]
        coding.display = condition["name"]
        
        codeable_concept = CodeableConcept()
        codeable_concept.coding = [coding]
        codeable_concept.text = condition["name"]
        
        cond_id = f"COND{self.resource_counter}"
        self.resource_counter += 1
        condition_resource = Condition(
            id=cond_id,
            clinicalStatus=CodeableConcept(
                coding=[Coding(
                    system="http://terminology.hl7.org/CodeSystem/condition-clinical",
                    code="active",
                    display="Active"
                )]
            ),
            verificationStatus=CodeableConcept(
                coding=[Coding(
                    system="http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    code="confirmed",
                    display="Confirmed"
                )]
            ),
            category=[CodeableConcept(
                coding=[Coding(
                    system="http://snomed.info/sct",
                    code="439740001",
                    display="Emergency"
                )]
            )],
            code=codeable_concept,
            subject=Reference(reference=f"Patient/{patient_data['id']}"),
            onsetDateTime=self._ensure_timezone_aware(patient_data["arrival_time"]).isoformat(),
        )
        
        return condition_resource
    
    def create_fhir_observation(self, patient_data: Dict, vital_name: str, vital_data: Dict, timestamp: datetime) -> Observation:
        """Create a FHIR Observation resource for a vital sign."""
        # Map vital names to LOINC codes
        loinc_codes = {
            "temperature": ("8310-5", "Body temperature"),
            "heart_rate": ("8867-4", "Heart rate"),
            "blood_pressure_systolic": ("8480-6", "Systolic blood pressure"),
            "blood_pressure_diastolic": ("8462-4", "Diastolic blood pressure"),
            "respiratory_rate": ("9279-1", "Respiratory rate"),
            "oxygen_saturation": ("2708-6", "Oxygen saturation in Arterial blood"),
        }
        
        loinc_code, display = loinc_codes.get(vital_name, ("", vital_name))
        
        coding = Coding()
        coding.system = "http://loinc.org"
        coding.code = loinc_code
        coding.display = display
        
        codeable_concept = CodeableConcept()
        codeable_concept.coding = [coding]
        codeable_concept.text = display
        
        obs_id = f"OBS{self.resource_counter}-{vital_name.replace('_', '-')}"
        self.resource_counter += 1
        observation = Observation(
            id=obs_id,
            status="final",
            code=codeable_concept,
            subject=Reference(reference=f"Patient/{patient_data['id']}"),
            effectiveDateTime=self._ensure_timezone_aware(timestamp).isoformat(),
            valueQuantity={
                "value": vital_data["value"],
                "unit": vital_data["unit"],
                "system": "http://unitsofmeasure.org",
            },
        )
        
        return observation
    
    def create_hl7_adt_message(self, patient_data: Dict, condition: Dict) -> str:
        """Create an HL7 ADT^A01 (Admit) message."""
        # HL7 message structure
        msh = f"MSH|^~\\&|ER_SYS|HOSPITAL|ADT_SYS|HOSPITAL|{patient_data['arrival_time'].strftime('%Y%m%d%H%M%S')}||ADT^A01^ADT_A01|{uuid.uuid4()}|P|2.5"
        
        # Patient Identification (PID)
        name_parts = patient_data["name"].split()
        last_name = name_parts[-1] if name_parts else ""
        first_name = name_parts[0] if name_parts else ""
        
        pid = f"PID|1||{patient_data['mrn']}||{last_name}^{first_name}||{patient_data['birth_date'].strftime('%Y%m%d')}|{patient_data['gender'][0].upper()}|||{patient_data['address'].replace(chr(10), '^').replace(',', '^')}||{patient_data['phone']}|||||||"
        
        # Patient Visit (PV1)
        pv1 = f"PV1|1|E|ER^EMERGENCY ROOM|||||{patient_data['mrn']}^DOCTOR|||||||||||V"
        
        # Diagnosis (DG1)
        dg1 = f"DG1|1|I10|{condition['icd10']}|{condition['name']}|||F"
        
        message = f"{msh}\r{pid}\r{pv1}\r{dg1}"
        return message
    
    def create_hl7_oru_message(self, patient_data: Dict, vital_name: str, vital_data: Dict, timestamp: datetime) -> str:
        """Create an HL7 ORU^R01 (Observation Result) message."""
        # Map vital names to LOINC codes
        loinc_codes = {
            "temperature": ("8310-5", "Body temperature", "F"),
            "heart_rate": ("8867-4", "Heart rate", "/min"),
            "blood_pressure_systolic": ("8480-6", "Systolic BP", "mmHg"),
            "blood_pressure_diastolic": ("8462-4", "Diastolic BP", "mmHg"),
            "respiratory_rate": ("9279-1", "Respiratory rate", "/min"),
            "oxygen_saturation": ("2708-6", "O2 Sat", "%"),
        }
        
        loinc_code, display, unit = loinc_codes.get(vital_name, ("", vital_name, ""))
        
        msh = f"MSH|^~\\&|ER_SYS|HOSPITAL|LAB_SYS|HOSPITAL|{timestamp.strftime('%Y%m%d%H%M%S')}||ORU^R01^ORU_R01|{uuid.uuid4()}|P|2.5"
        
        pid = f"PID|1||{patient_data['mrn']}||{patient_data['name'].split()[-1]}^{patient_data['name'].split()[0]}"
        
        obr = f"OBR|1|||{loinc_code}^{display}|||||||{timestamp.strftime('%Y%m%d%H%M%S')}"
        
        obx = f"OBX|1|NM|{loinc_code}^{display}||{vital_data['value']}|{unit}|||F"
        
        message = f"{msh}\r{pid}\r{obr}\r{obx}"
        return message
    
    def generate_all_data(self) -> Tuple[List[Dict], List[str]]:
        """Generate all patient data for the 48-hour period."""
        arrival_times = self.generate_arrival_times()
        fhir_resources = []
        hl7_messages = []
        
        print(f"Generating data for {len(arrival_times)} patients over 48 hours...")
        
        for i, arrival_time in enumerate(arrival_times):
            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1}/{len(arrival_times)} patients...")
            
            # Generate patient
            patient_data = self.generate_patient(arrival_time)
            condition = self.select_condition(patient_data)
            vitals = self.generate_vitals(condition)
            
            # Create FHIR resources
            fhir_patient = self.create_fhir_patient(patient_data)
            fhir_encounter = self.create_fhir_encounter(patient_data, condition)
            fhir_condition = self.create_fhir_condition(patient_data, condition)
            
            fhir_resources.append({
                "resourceType": "Patient",
                "data": fhir_patient.dict(),
                "timestamp": arrival_time.isoformat(),
            })
            fhir_resources.append({
                "resourceType": "Encounter",
                "data": fhir_encounter.dict(),
                "timestamp": arrival_time.isoformat(),
            })
            fhir_resources.append({
                "resourceType": "Condition",
                "data": fhir_condition.dict(),
                "timestamp": arrival_time.isoformat(),
            })
            
            # Create vital sign observations (taken at arrival and potentially during stay)
            observation_times = [arrival_time]
            if condition["duration_minutes"] > 120:
                # Add a mid-stay observation for longer visits
                mid_time = arrival_time + timedelta(minutes=condition["duration_minutes"] // 2)
                observation_times.append(mid_time)
            
            for obs_time in observation_times:
                for vital_name, vital_data in vitals.items():
                    fhir_obs = self.create_fhir_observation(patient_data, vital_name, vital_data, obs_time)
                    fhir_resources.append({
                        "resourceType": "Observation",
                        "data": fhir_obs.dict(),
                        "timestamp": obs_time.isoformat(),
                    })
            
            # Create HL7 messages
            hl7_adt = self.create_hl7_adt_message(patient_data, condition)
            hl7_messages.append({
                "type": "ADT^A01",
                "message": hl7_adt,
                "timestamp": arrival_time.isoformat(),
            })
            
            # Create ORU messages for vitals
            for obs_time in observation_times:
                for vital_name, vital_data in vitals.items():
                    hl7_oru = self.create_hl7_oru_message(patient_data, vital_name, vital_data, obs_time)
                    hl7_messages.append({
                        "type": "ORU^R01",
                        "message": hl7_oru,
                        "timestamp": obs_time.isoformat(),
                    })
        
        return fhir_resources, hl7_messages
    
    def save_data(self, fhir_resources: List[Dict], hl7_messages: List[Dict], output_dir: Path):
        """Save generated data to files."""
        output_dir.mkdir(exist_ok=True)
        
        # Save FHIR resources as JSON
        fhir_file = output_dir / "fhir_resources.json"
        with open(fhir_file, "w") as f:
            json.dump(fhir_resources, f, indent=2, default=str)
        print(f"Saved {len(fhir_resources)} FHIR resources to {fhir_file}")
        
        # Save HL7 messages
        hl7_file = output_dir / "hl7_messages.txt"
        with open(hl7_file, "w") as f:
            for msg in hl7_messages:
                f.write(f"# Timestamp: {msg['timestamp']}\n")
                f.write(f"# Message Type: {msg['type']}\n")
                f.write(msg["message"])
                f.write("\n\n")
        print(f"Saved {len(hl7_messages)} HL7 messages to {hl7_file}")
        
        # Also save HL7 as JSON for easier parsing
        hl7_json_file = output_dir / "hl7_messages.json"
        with open(hl7_json_file, "w") as f:
            json.dump(hl7_messages, f, indent=2, default=str)
        print(f"Saved HL7 messages (JSON format) to {hl7_json_file}")


def main():
    """Main function to generate ER data."""
    # Start from current time or a specific time (timezone-aware)
    start_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    generator = ERDataGenerator(start_time, duration_hours=48)
    fhir_resources, hl7_messages = generator.generate_all_data()
    
    output_dir = Path("output")
    generator.save_data(fhir_resources, hl7_messages, output_dir)
    
    print(f"\n✓ Generated {len(fhir_resources)} FHIR resources")
    print(f"✓ Generated {len(hl7_messages)} HL7 messages")
    print(f"✓ Data saved to {output_dir}/")


if __name__ == "__main__":
    main()

