# Interface and behavior of `fpmul.v`

The port definition of module `fpmul` is as follows:

```Verilog
module fpmul(clk, a, b, c, over_mul_under);

    input clk;
    input [31:0] a, b;
    output [31:0] c;
    output over_mul_under;
```

So, it is a pipelined design without a `reset` signal.

**The design has `underflow`, `overflow`, and `NaN` support.**

It handles `NaN` output through a special 1-bit output `over_mul_under`.

## Definitions:

We will use the following definitions for `sa`, `ea`, `ma`:

  ```
  sa = a[31];    // sign bit of a
  ea = a[30:23]; // exponent part of a
  ma = a[22:0];  // mantissa part of a
  ```

  It is clear from the above that `sa`, `ea`, and `ma` follow the *IEEE-754 32-bit location definition*.

  Similarly:

  - `b` is `{sb, eb, mb}`
  - `c` is `{sc, ec, mc}`

    `sb`, `eb`, `mb`, `sc`, `ec`, and `mc` are defined similarly to `sa`, `ea`, and `ma`.
    
    This is so because `a`, `b`, and `c` all follow the same standard definitions.

## Assertions of underflow and overflow of inputs

We need to check `a` and `b` for *underflow* and *overflow* conditions to correctly define `c`'s result.

- `a_underflow` is *asserted* when `ea == 0`, and *deasserted* otherwise.
- `a_overflow` is *asserted* when `ea == 8'b1111_1111` and *deasserted* otherwise.

  `b_underflow` and `b_overflow` are defined similarly to `a_underflow` and `a_overflow`, except they are derived from `eb`.

## The operational `truth table`:

With *underflow* and *overflow* conditions clearly defined from the previous section, we have an operational truth table:

We use the symbols:

- `U` to designate *underflow*.
- `O` to designate *overflow*.
- `N` to designate *normal* (neither *underflow* or *overflow*)

### Here is the truth table of the multiplier operation:

  - Recall that `over_mul_under` signifies that `c` is *NaN*.

| `a` | `b` | Meaning | `c` | `over_mul_under` |
| :---: | :---: | :--- | :---: | :---: |
| `O` | `O` | Both `a` and `b` overflow | *overflow* | `0` |
| `O` | `N` | `a` overflow | `O` | `0` |
| `O` | `U` | *overflow* multiplies *underflow* | undefined output | `1` |
| `N` | `O` | `b` overflow |`O` | `0` |
| `N` | `N` |  normal operation | check multiplication result for *underflow* or *overflow* | `0` |
| `N` | `U` | `b` underflow | *underflow* | `0` |
| `U` | `O` | *overflow* multiplies *underflow* | undefined output | `1` |
| `U` | `N` | `a` underflow | *underflow* | `0` |
| `U` | `U` | both `a` and `b` underflow | *underflow* | `0` |

## `c` and `over_mul_under` outputs:

- `sc` is always calculated from `sa` and `sb`, so `+/-underflow` and `+/-overflow` outputs are possible.
- `ec` is as follows:

  - if `c` *underflows*, `ec` is set to `8'b0`.
  - if `c` *overflows*, `ec` is set to `8'b1111_1111`.
  - if `c` is *NaN*, assert `over_mul_under` and `ec` can be ignored.

- `sc` only has a meaningful interpretation if `over_mul_under` is deasserted.

**This completely specifies specifies the behavior of `c` and `over_mul_under` (*NaN*) output.**

## FAQs

the project requirement was 40MHz multiplication throughput on *Xilinx Spartan-3* platform in 2006.

All standard-deviations or limited implmentation was done to meet post-P&R 40MHz throughput with some safety margin built-in, hence the following design choices: 

1. `over_mul_under` signal was used for *NaN* instead of encoding it within `c`.

2. `c` is always round towards `0` because round-to-nearest adds more delay.
