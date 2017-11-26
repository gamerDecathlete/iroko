INPUT_DIR=inputs
OUTPUT_DIR=results
INPUT_FILES='stag_prob_0_2_3_data stag_prob_1_2_3_data stag_prob_2_2_3_data stag_prob_0_5_3_data stag_prob_1_5_3_data stag_prob_2_5_3_data stride1_data stride2_data stride4_data stride8_data random0_data random1_data random2_data random0_bij_data random1_bij_data random2_bij_data random_2_flows_data random_3_flows_data random_4_flows_data hotspot_one_to_one_data'
# INPUT_FILES='stag_prob_0_2_3_data'
DURATION=60

sudo mn -c
for f in $INPUT_FILES;
do
        input_file=$INPUT_DIR/default/$f
        pref="nonblocking"
        out_dir=$OUTPUT_DIR/$pref/$f
        sudo python iroko.py -i $input_file -d $out_dir -p 0.03 -t $DURATION -n
done

for f in $INPUT_FILES;
do
        input_file=$INPUT_DIR/default/$f
        pref="fattree-ecmp"
        out_dir=$OUTPUT_DIR/$pref/$f
        sudo python iroko.py -i $input_file -d $out_dir -p 0.03 -t $DURATION --ecmp
done

for f in $INPUT_FILES;
do
        input_file=$INPUT_DIR/default/$f
        pref="fattree-dctcp"
        out_dir=$OUTPUT_DIR/$pref/$f
        sudo python iroko.py -i $input_file -d $out_dir -p 0.03 -t $DURATION --ecmp --dctcp
done

for f in $INPUT_FILES;
do
        input_file=$INPUT_DIR/iroko/$f
        pref="fattree-iroko"
        out_dir=$OUTPUT_DIR/$pref/$f
        sudo python iroko.py -i $input_file -d $out_dir -p 0.03 -t $DURATION --iroko
done

for f in $INPUT_FILES;
do
        input_file=$INPUT_DIR/hedera/$f
        pref="fattree-hedera"
        out_dir=$OUTPUT_DIR/$pref/$f
        sudo python iroko.py -i $input_file -d $out_dir -p 0.03 -t $DURATION --hedera
done
