# Emergency Room Data Generator

A Python program that generates 48 hours of stochastic FHIR and HL7 patient data to simulate a typical emergency room environment.

## Features

- **Stochastic Timing**: Uses Poisson process to generate realistic patient arrival patterns with higher rates during evening hours (6 PM - 2 AM)
- **Realistic Disease Types**: 20+ ER-specific conditions with ICD-10 codes, including:
  - Chest pain, abdominal pain, shortness of breath
  - Trauma cases (lacerations, fractures)
  - Chronic condition exacerbations (asthma, hypertension)
  - Infections (UTI, pneumonia, gastroenteritis)
  - And more...
- **FHIR Resources**: Generates standard FHIR resources:
  - Patient demographics
  - Encounter records
  - Condition diagnoses
  - Observation vital signs (temperature, heart rate, blood pressure, respiratory rate, oxygen saturation)
- **HL7 Messages**: Generates HL7 v2.5 messages:
  - ADT^A01 (Admit) messages
  - ORU^R01 (Observation Result) messages
- **Realistic Vital Signs**: Generates contextually appropriate vital signs based on condition severity

## Installation

1. Install Python 3.8 or higher
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the generator:

```bash
python generate_er_data.py
```

The script will:
1. Generate patient arrivals over a 48-hour period using stochastic timing
2. Assign random conditions based on patient demographics
3. Generate FHIR resources and HL7 messages
4. Save all data to the `output/` directory

## Output Files

The generator creates three output files in the `output/` directory:

1. **fhir_resources.json**: All FHIR resources in JSON format, including:
   - Patient resources
   - Encounter resources
   - Condition resources
   - Observation resources (vital signs)

2. **hl7_messages.txt**: HL7 messages in plain text format, one message per block with timestamps

3. **hl7_messages.json**: HL7 messages in JSON format for easier programmatic parsing

## Data Characteristics

- **Arrival Patterns**: 
  - Evening (6 PM - 2 AM): 4-8 patients/hour
  - Early morning (2 AM - 8 AM): 1-3 patients/hour
  - Daytime (8 AM - 6 PM): 2-5 patients/hour

- **Visit Duration**: Varies by condition severity:
  - Low severity: ~60 minutes
  - Medium severity: ~90-150 minutes
  - High severity: ~180-300 minutes

- **Patient Demographics**: Randomly generated using Faker library with realistic distributions

- **Condition Selection**: Weighted based on patient age (pediatric vs. geriatric conditions)

## Example Output

### FHIR Patient Resource
```json
{
  "resourceType": "Patient",
  "id": "PAT000001",
  "identifier": [{
    "system": "http://hospital.example.org/patients",
    "value": "MRN123456"
  }],
  "name": [{
    "family": "Smith",
    "given": ["John"]
  }],
  "gender": "male",
  "birthDate": "1985-03-15"
}
```

### HL7 ADT Message
```
MSH|^~\&|ER_SYS|HOSPITAL|ADT_SYS|HOSPITAL|20240101120000||ADT^A01^ADT_A01|...
PID|1||MRN123456||Smith^John||19850315|M|||...
PV1|1|E|ER^EMERGENCY ROOM|||||MRN123456^DOCTOR|||||||||||V
DG1|1|I10|R06.02|Chest Pain|||F
```

## Customization

You can modify the following in `generate_er_data.py`:

- **ER_CONDITIONS**: Add or modify condition types
- **VITAL_SIGNS**: Adjust normal/abnormal ranges
- **Arrival rates**: Modify lambda rates in `generate_arrival_times()`
- **Duration**: Adjust `duration_hours` parameter (default: 48)

## Requirements

- Python 3.8+
- fhir.resources >= 7.0.0
- hl7 >= 0.4.7
- faker >= 20.0.0
- python-dateutil >= 2.8.2
- numpy

## License

This is a data generation tool for simulation purposes.

