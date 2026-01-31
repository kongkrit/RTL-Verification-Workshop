// Verilog-95 behavioral DFF with setup/hold checks + clk->Q delay.
// On violation at the sampling edge: drive X on Q.
//
// Added:
//  - parameter T_CLK2Q
//  - runtime sanity check: T_CLK2Q must be >= T_HOLD (else stop)

`timescale 1ns/1ps

module dff_shchk (
  input  d,
  input  clk,
  output reg q
);

  // ---- Parameters (edit as needed) ----
  parameter integer T_SETUP = 2;  // time units
  parameter integer T_HOLD  = 1;  // time units
  parameter integer T_CLK2Q = 1;  // time units

  // ---- Internal bookkeeping ----
  time last_d_change;
  time t_edge;
  reg  hold_window_open;
  reg  violation;

  initial begin
    // Sanity: enforce clk2q >= hold
    if (T_CLK2Q < T_HOLD) begin
      $display("%0t ERROR: T_CLK2Q(%0d) must be >= T_HOLD(%0d).",
               $time, T_CLK2Q, T_HOLD);
      $stop;
    end

    q                = 1'b0;
    last_d_change    = 0;
    t_edge           = 0;
    hold_window_open = 1'b0;
    violation        = 1'b0;
  end

  // Track D transitions time
  always @(d) begin
    last_d_change = $time;

    // Hold check: if D changes during [edge, edge+T_HOLD) window => violation
    if (hold_window_open) begin
      violation = 1'b1;
      // clk2q delay still applies to the point Q is observed changing
      q <= #(T_CLK2Q) 1'bx;
    end
  end

  // Sample on rising edge of clock
  always @(posedge clk) begin
    violation = 1'b0;
    t_edge = $time;

    // Setup check: D must be stable for T_SETUP before the edge
    if ((t_edge - last_d_change) < T_SETUP) begin
      violation = 1'b1;
      q <= #(T_CLK2Q) 1'bx;
    end else begin
      q <= #(T_CLK2Q) d;
    end

    // Open hold window after sampling edge
    hold_window_open = 1'b1;
    #(T_HOLD) hold_window_open = 1'b0;
  end

endmodule

// device under test with setup and hold violations

module dut(
  input clk,
  input in,
  output out_s,
  output out_h
);

  wire #9 in_s = in;   // setup violation
  wire #1.5 in_h = in; // hold violation

  // 2 FFs with delays
  dff_shchk ff_s(.clk(clk), .d(in_s), .q(out_s));
  dff_shchk ff_h(.clk(clk), .d(in_h), .q(out_h));

endmodule

// testbench for testing the dut with setup and hold violations

module testbench;
  reg clk;
  reg in;
  wire out_s;
  wire out_h;

// clock generator
    
  initial begin
    clk = 1;
    forever begin
      #5.5  // half clock cycle
        clk = ~clk;
    end
  end

  always @(posedge clk) begin
    in <= ~in;
  end

  initial begin
    in = 0;
    $dumpfile("setup_hold_violations.vcd");
    $dumpvars(0, testbench);
    #100;
    $finish;
  end

  dut dut0(.clk(clk), .in(in), .out_s(out_s), .out_h(out_h));

endmodule
