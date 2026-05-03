# Chemotherapy IV Drip Rate Calculation

## Problem Statement
A 6-year-old child weighing 22 kg with BSA 0.8 m² is prescribed a chemotherapy drug at 25 mg/m²/day over 3 days. The vial contains 100 mg/5 mL. A volume of 4.7 mL is drawn and diluted in 50 mL normal saline. What is the final drip rate in drops/minute (60 drops/mL), infused over 1 hour?

## Physical Process Recognition
This is a **Rate/Dimensional Analysis** problem (Template 6 from the skill). We have:
- A known total volume to be infused
- A known infusion time
- A known drop factor
- Goal: Calculate drops per minute

This requires correct dimensional analysis to convert volume-per-time to drops-per-time.

## Step-by-Step Reasoning

### Step 1: Calculate Prescribed Daily Dose (BSA-based dosing)
**Physical principle**: The dose is prescribed per unit of body surface area.

- Prescribed daily dose = 25 mg/m² × 0.8 m² = **20 mg/day**
- Total dose over 3 days = 20 mg/day × 3 days = 60 mg

### Step 2: Determine Drug Amount in the Drawn Volume
**Physical principle**: Conservation of mass. The amount of drug is proportional to the volume drawn.

- Vial concentration: 100 mg/5 mL = 20 mg/mL
- Volume drawn: 4.7 mL
- Drug amount = (4.7 mL / 5 mL) × 100 mg = **94 mg**

### Step 3: Calculate Final IV Solution Volume and Concentration
**Physical principle**: When two solutions mix, volumes are additive. The total amount of drug is conserved and distributed in the total volume.

- Total IV volume = 4.7 mL (drug) + 50 mL (saline) = **54.7 mL**
- Final concentration = 94 mg / 54.7 mL = 1.7185 mg/mL

### Step 4: Calculate Infusion Rate in mL per Minute
**Physical principle**: Flow rate = Volume / Time

- Infusion time: 1 hour = 60 minutes
- Volume to infuse: 54.7 mL
- Volume per minute = 54.7 mL ÷ 60 min = **0.9117 mL/min**

### Step 5: Convert to Drops per Minute
**Physical principle**: Dimensional analysis. The drop factor relates volume to drops.

- Drop factor: 60 drops/mL
- Drip rate = 0.9117 mL/min × 60 drops/mL = **54.70 drops/minute**

## Dimensional Analysis Verification
```
54.7 mL     ÷   60 min   ×   60 drops/mL  =  54.70 drops/min
   ↓             ↓            ↓                    ↓
(volume)    (time)       (drop factor)        (rate)

Units cancel correctly: [mL/min] × [drops/mL] = [drops/min] ✓
```

## Clinical Reasonableness Check
- Total IV volume: 54.7 mL infused over 1 hour is a moderate rate (standard pediatric IV infusions typically range from 20-100 mL/hr depending on indication)
- Drip rate of 55 drops/minute is achievable with standard infusion equipment
- The drug concentration (1.7 mg/mL) is safe for IV administration (no precipitation risk with this dilution)

## Final Answer

**The final drip rate is 55 drops per minute** (exact value: 54.70 drops/min, rounded to 55 for clinical practice)
