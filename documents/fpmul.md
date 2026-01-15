# Interface and Behavior of `fpmul.v`

## Module Interface
The `fpmul` module is a pipelined, single-precision floating-point multiplier. It does not utilize a `reset` signal.

```verilog
module fpmul(clk, a, b, c, over_mul_under);
    input clk;
    input [31:0] a, b;      // IEEE-754 Single Precision Inputs
    output [31:0] c;        // Result
    output over_mul_under;  // Exception Flag: Overflow * Underflow (NaN)
```

## 1. Data Definitions (IEEE-754)
Inputs `a`, `b` and output `c` follow the standard IEEE-754 32-bit format:

* **Sign (s):** Bit `[31]`
* **Exponent (e):** Bits `[30:23]`
* **Mantissa (m):** Bits `[22:0]`

## 2. Exception Logic
The module detects exceptions based strictly on the **Exponent (`e`)** field. It **does not** handle `NaN` on inputs.

### Input States
| State | Condition | Definition |
| :--- | :--- | :--- |
| **Underflow (U)** | `e == 0` | Treated as Zero |
| **Overflow (O)** | `e == 255` | Treated as Infinity |
| **Normal (N)** | `0 < e < 255` | Standard Value |

### Output Handling
* **Exceptions:** `+/- Underflow` and `+/- Overflow` are encoded in the output `c` using standard IEEE bit patterns.
* **NaN:** `NaN` is **not** encoded in `c`. It is flagged via the side-band signal `over_mul_under` (specifically for the invalid operation $0 \times \infty$).
* **Rounding:** The result is **Round towards Zero** (Truncation).

## 3. Operational Truth Table
The output `c` and flag `over_mul_under` are determined by the interaction of input states.

| Input `a` | Input `b` | Result | `over_mul_under` (NaN) | Note |
| :---: | :---: | :--- | :---: | :--- |
| **O** | **O** | **Overflow** | `0` | $\infty \times \infty = \infty$ |
| **O** | **N** | **Overflow** | `0` | $\infty \times \text{Normal} = \infty$ |
| **O** | **U** | **NaN** | **1** | $\infty \times 0 = \text{NaN}$ |
| **N** | **O** | **Overflow** | `0` | $\text{Normal} \times \infty = \infty$ |
| **N** | **N** | **Calculated** | `0` | Normal multiplication logic |
| **N** | **U** | **Underflow** | `0` | $\text{Normal} \times 0 = 0$ |
| **U** | **O** | **NaN** | **1** | $0 \times \infty = \text{NaN}$ |
| **U** | **N** | **Underflow** | `0` | $0 \times \text{Normal} = 0$ |
| **U** | **U** | **Underflow** | `0` | $0 \times 0 = 0$ |

## 4. Output Construction
The bits of `c` (`sc`, `ec`, `mc`) are driven as follows:

1.  **Sign (`sc`):** Always `sa ^ sb`.
2.  **Exponent (`ec`):**
    * **If Underflow:** Set to `0x00`.
    * **If Overflow:** Set to `0xFF`.
    * **If NaN:** `ec` is ignored (rely on `over_mul_under`).
3.  **Mantissa (`mc`):** Calculated logic or forced to 0 based on exception state.

## 5. Design History & Rationale
This module was originally designed in **2006** for the **Xilinx Spartan-3** platform.

To meet the strict **40MHz post-P&R timing constraint**, deviations from full IEEE-754 compliance were required:

1.  **NaN Encoding:** `NaN` is flagged via a dedicated bit (`over_mul_under`) rather than encoding specific bit patterns in `c`. This reduced logic depth in the critical path.
2.  **Rounding:** **Round-towards-zero** was selected over round-to-nearest to eliminate the additional adder delay required for rounding logic.