# Quick Start — tooluniverse-reaction-engineering

## 1. Install ToolUniverse

```bash
uv venv --python 3.12 && source .venv/bin/activate   # Linux/Mac
# or on Windows:
uv venv --python 3.12
.venv\Scripts\activate

uv pip install tooluniverse
```

## 2. Load Tools

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()
```

## 3. Example: Size a CSTR for 90% Conversion (First-Order)

**Problem:** A liquid-phase first-order reaction `A → B` has `k = 0.05 min⁻¹` at 25°C. Feed rate `F_A0 = 10 mol/min`, inlet concentration `C_A0 = 2 mol/L`. Target conversion `X = 0.90`. What CSTR volume is needed?

**Design equation (CSTR, first-order, constant density):**

```
V = F_A0 * X / (k * C_A0 * (1 - X))
```

**Calculation:**

```python
F_A0 = 10       # mol/min
k = 0.05        # min^-1
C_A0 = 2        # mol/L
X = 0.90        # target conversion

V = F_A0 * X / (k * C_A0 * (1 - X))
print(f"CSTR volume = {V:.1f} L")
# Output: CSTR volume = 900.0 L

# Space time
v0 = F_A0 / C_A0           # L/min
tau = V / v0               # min
print(f"Space time = {tau:.1f} min")
# Output: Space time = 180.0 min
```

## 4. Example: PFR vs CSTR Comparison

For the same first-order reaction, compare volumes for 90% conversion:

```python
import math

# CSTR
V_cstr = F_A0 * X / (k * C_A0 * (1 - X))

# PFR (first-order analytic)
V_pfr = (F_A0 / k) * math.log(1 / (1 - X))

print(f"CSTR: {V_cstr:.1f} L")
print(f"PFR:  {V_pfr:.1f} L")
print(f"CSTR/PFR ratio: {V_cstr/V_pfr:.2f}x")
```

**Expected output:** PFR is smaller than CSTR for the same conversion (typical for positive-order reactions).

## 5. Example: Arrhenius Temperature Correction

Given `k1 = 0.05 min⁻¹` at `T1 = 25°C`, `Ea = 50 kJ/mol`, find `k2` at `T2 = 50°C`:

```python
import math

R = 8.314          # J/mol·K
Ea = 50000         # J/mol
T1 = 25 + 273.15   # K
T2 = 50 + 273.15   # K
k1 = 0.05          # min^-1

k2 = k1 * math.exp((Ea/R) * (1/T1 - 1/T2))
print(f"k at 50°C = {k2:.4f} min^-1")
```

## 6. Using Existing ToolUniverse Chemistry Tools (Optional)

To identify reacting species before sizing:

```python
# Predict product from reactants (requires RXN4CHEMISTRY_API_KEY)
result = tu.run({
    "name": "RXNChemistry_predict_reaction",
    "arguments": {"reactants": "CC(=O)O.CCO", "reagents": ""}
})

# Resolve compound name to CID
result = tu.run({
    "name": "PubChem_get_CID_by_compound_name",
    "arguments": {"name": "Aspirin"}
})
```

## Next Steps

Read `SKILL.md` for full workflow, decision logic, and limitations. This skill is guidance-oriented — calculations are done by hand or in Python, not executed automatically by ToolUniverse.
