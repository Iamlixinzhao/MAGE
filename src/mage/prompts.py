RTL_2_SHOT_EXAMPLES = """
Examples of RTL Verilog code:
Example 1:
<example>
    <input_spec>Implement a XOR gate.</input_spec>
    <module>
        module TopModule(input wire in0, input wire in1, output wire out);
            assign out = in0 ^ in1;
        endmodule
    </module>
</example>
Example 2:
<example>
    <input_spec>Implement an 8-bit registered incrementer. The input is registered and incremented by one on the next cycle. Reset is active high synchronous.</input_spec>
    <module>
        module TopModule(input wire clk, input wire reset, input wire [7:0] in_, output reg [7:0] out);
            reg [7:0] reg_out;
            
            always @(posedge clk) begin
                if (reset) 
                    reg_out <= 0;
                else 
                    reg_out <= in_;
            end
            
            always @(*) begin
                out = reg_out + 1;
            end
        endmodule
    </module>
</example>
"""

TB_2_SHOT_EXAMPLES = """
Examples of Verilog testbench code:
Example 1:
<example>
    <input_spec>Implement a XOR gate.</input_spec>
    <interface>
        module TopModule(input wire in0, input wire in1, output wire out);
    </interface>
    <testbench>
        module TopModule_tb();
            reg in0, in1;
            wire out, expected_out;
            integer mismatch_count = 0;
            
            TopModule dut (.in0(in0), .in1(in1), .out(out));
            assign expected_out = in0 ^ in1;
            
            initial begin
                for (integer i = 0; i < 4; i = i + 1) begin
                    {in0, in1} = i;
                    #10;
                    if (out !== expected_out) begin
                        $display("Mismatch: in0=%b, in1=%b, out=%b, expected=%b", in0, in1, out, expected_out);
                        mismatch_count = mismatch_count + 1;
                    end
                end
                if (mismatch_count == 0) $display("SIMULATION PASSED");
                else $display("SIMULATION FAILED");
                $finish;
            end
        endmodule
    </testbench>
</example>
Example 2:
<example>
    <input_spec>Implement an 8-bit registered incrementer. The input is registered and incremented by one on the next cycle. Reset is active high synchronous.</input_spec>
    <interface>
        module TopModule(input wire clk, input wire reset, input wire [7:0] in_, output reg [7:0] out);
    </interface>
    <testbench>
        module TopModule_tb();
            reg clk, reset;
            reg [7:0] in_;
            wire [7:0] out, expected_out;
            integer mismatch_count = 0;
            
            TopModule dut (.clk(clk), .reset(reset), .in_(in_), .out(out));
            
            always #5 clk = ~clk;
            
            initial begin
                clk = 0; reset = 1; in_ = 0;
                @(posedge clk); reset = 0;
                
                for (integer i = 0; i < 5; i = i + 1) begin
                    in_ = $random;
                    @(posedge clk);
                    expected_out = in_;
                    @(negedge clk);
                    if (out !== expected_out) mismatch_count = mismatch_count + 1;
                    
                    @(posedge clk);
                    expected_out = in_ + 1;
                    @(negedge clk);
                    if (out !== expected_out) mismatch_count = mismatch_count + 1;
                end
                
                if (mismatch_count == 0) $display("SIMULATION PASSED");
                else $display("SIMULATION FAILED");
                $finish;
            end
        endmodule
    </testbench>
</example>
"""

FAILED_TRIAL_PROMPT = r"""
There was a generation trial that failed simulation:
<failed_sim_log>
{failed_sim_log}
</failed_sim_log>
<previous_code>
{previous_code}
</previous_code>
<previous_tb>
{previous_tb}
</previous_tb>
"""

ORDER_PROMPT = r"""
Generate ONLY the required JSON object. Be concise and direct.
<output_format>
{output_format}
</output_format>
IMPORTANT: The "module" field must contain ONLY the complete Verilog code, starting with "module TopModule" and ending with "endmodule". Do NOT include descriptions, explanations, or comments about the code in the "module" field.
DO NOT include any other information in your response, like 'json', 'reasoning' or '<output_format>'.
"""
