import argparse
import os  # noqa
import sre_yield
from iroko_plt import IrokoPlotter

PARSER = argparse.ArgumentParser()
# parser.add_argument('--input', '-f', dest='files', required=True, help='Input rates')

PARSER.add_argument('--train', '-tr', dest='train', default=False,
                    action='store_true', help='Train Iroko in epoch mode and measure the improvement.')
PARSER.add_argument('--epoch', '-e', dest='epochs', type=int, default=0,
                    help='Specify the number of epochs Iroko should be trained.')
PARSER.add_argument('--offset', '-o', dest='offset', type=int, default=0,
                    help='Intended to start epochs from an offset.')
PARSER.add_argument('--test', '-t', dest='test', default=False,
                    action='store_true', help='Run the full tests of the algorithm.')
PARSER.add_argument('--agent', '-a', dest='agent', default='A', help='A, B, C, D')
PARSER.add_argument('--plot', '-pl', dest='plot', action='store_true',
                    default='False', help='Only plot the results for training.')
PARSER.add_argument('--dumbbell', '-db', dest='dumbbell', action='store_true',
                    default='False', help='Train on a simple dumbbell topology')

ARGS = PARSER.parse_args()


''' Output of bwm-ng has the following format:
    unix_timestamp;iface_name;bytes_out;bytes_in;bytes_total;packets_out;packets_in;packets_total;errors_out;errors_in
    '''

TRAFFIC_FILES = ['stag_prob_0_2_3_data', 'stag_prob_1_2_3_data', 'stag_prob_2_2_3_data',
                 'stag_prob_0_5_3_data', 'stag_prob_1_5_3_data', 'stag_prob_2_5_3_data', 'stride1_data',
                 'stride2_data', 'stride4_data', 'stride8_data', 'random0_data', 'random1_data', 'random2_data',
                 'random0_bij_data', 'random1_bij_data', 'random2_bij_data', 'random_2_flows_data',
                 'random_3_flows_data', 'random_4_flows_data', 'hotspot_one_to_one_data']
TRAFFIC_FILES = ['stag_prob_0_2_3_data']

LABELS = ['stag0(0.2,0.3)', 'stag1(0.2,0.3)', 'stag2(0.2,0.3)', 'stag0(0.5,0.3)',
          'stag1(0.5,0.3)', 'stag2(0.5,0.3)', 'stride1', 'stride2',
          'stride4', 'stride8', 'rand0', 'rand1', 'rand2', 'randbij0',
          'randbij1', 'randbij2', 'randx2', 'randx3', 'randx4', 'hotspot']
LABELS = ['stag0(0.2,0.3)']

QLEN_TRAFFICS = ['stag_prob_2_2_3_data',
                 'stag_prob_2_5_3_data', 'stride1_data',
                 'stride2_data', 'random0_data',
                 'random_2_flows_data',
                 'random_3_flows_data', 'random_4_flows_data']

QLEN_LABELS = ['stag2(0.2,0.3)',
               'stag2(0.5,0.3)', 'stride1', 'stride2',
               'rand0',
               'randx2', 'randx3', 'randx4']


INPUT_DIR = 'inputs'
OUTPUT_DIR = 'results'
DURATION = 60
NONBLOCK_SW = '1001'
HEDERA_SW = '[0-3]h[0-1]h1'
FATTREE_SW = '300[1-9]'
DUMBBELL_SW = '100[1]|1002-eth3'


def get_test_config():
    algos = {}
    # algos['nonblocking'] = {'sw': NONBLOCK_SW, 'tf': 'default', 'pre': 'nonblocking', 'color': 'royalblue'}
    algos['iroko'] = {'sw': FATTREE_SW, 'tf': 'iroko', 'pre': 'fattree-iroko', 'color': 'green'}
    # algos['ecmp'] = {'sw': FATTREE_SW, 'tf': 'default', 'pre': 'fattree-ecmp', 'color': 'magenta'}
    # algos['dctcp'] = {'sw': FATTREE_SW, 'tf': 'default', 'pre': 'fattree-dctcp', 'color': 'brown'}
    # algos['hedera'] = {'sw': HEDERA_SW, 'tf': 'hedera', 'pre': 'fattree-hedera', 'color': 'red'}
    return algos


def train(input_dir, output_dir, duration, traffic_files, offset, epochs, algorithm):
    os.system('sudo mn -c')
    f = open("reward.txt", "a+")
    algo = algorithm[0]
    conf = algorithm[1]
    for e in range(offset, epochs + offset):
        for tf in traffic_files:
            input_file = '%s/%s/%s' % (input_dir, conf['tf'], tf)
            pre_folder = "%s_%d" % (conf['pre'], e)
            out_dir = '%s/%s/%s' % (output_dir, pre_folder, tf)
            os.system('sudo python iroko.py -i %s -d %s -p 0.03 -t %d --%s --agent %s' %
                      (input_file, out_dir, duration, algo, ARGS.agent))
            os.system('sudo chown -R $USER:$USER %s' % out_dir)
            plotter.prune_bw(out_dir, tf, conf['sw'])
    f.close()


def run_tests(input_dir, output_dir, duration, traffic_files, algorithms):
    os.system('sudo mn -c')
    f = open("reward.txt", "a+")
    for algo, conf in algorithms.iteritems():
        pre_folder = conf['pre']
        for tf in traffic_files:
            input_file = '%s/%s/%s' % (input_dir, conf['tf'], tf)
            out_dir = '%s/%s/%s' % (output_dir, pre_folder, tf)
            os.system('sudo python iroko.py -i %s -d %s -p 0.03 -t %d --%s' % (input_file, out_dir, duration, algo))
            os.system('sudo chown -R $USER:$USER %s' % out_dir)
            plotter.prune_bw(out_dir, tf, conf['sw'])
    f.close()

# This is a stupid hack, but it works


def get_num_interfaces(pattern):
    n = []
    for each in sre_yield.AllStrings(r'%s' % pattern):
        n.append(each)
    return len(n)


def yn_choice(message, default='y'):
    shall = 'N'
    shall = raw_input("%s (y/N) " % message).lower() == 'y'
    return shall


if __name__ == '__main__':

    if yn_choice("Do you want to remove the reward file?"):
        print("Okay! Deleting...")
        try:
            os.remove("reward.txt")
        except OSError:
            pass

    algorithms = get_test_config()
    # Stupid hack, do not like.
    n = get_num_interfaces(DUMBBELL_SW)
    plotter = IrokoPlotter(n, ARGS.epochs + ARGS.offset)
    # Train on the dumbbell topology
    if ARGS.dumbbell is True:
        algorithms = {}
        algorithms['dumbbell'] = {'sw': DUMBBELL_SW, 'tf': 'dumbbell', 'pre': 'dumbbell-iroko', 'color': 'green'}
        TRAFFIC_FILES = ['incast_2']
        DURATION = 600
        # traffic_files = ['incast_4']
        # traffic_files = ['incast_8']
        LABELS = ['incast']
        ARGS.train = True
    # Train the agent
    # Compare against other algorithms, if necessary
    if ARGS.train is True:
        if ARGS.epochs is 0:
            print("Please specify the number of epochs you would like to train with (--epoch)!")
            exit(1)
        for algo, conf in algorithms.items():
            print("Training the %s agent for %d epoch(s)." % (algo, ARGS.epochs))
            if ARGS.plot is not True:
                train(INPUT_DIR, OUTPUT_DIR, DURATION, TRAFFIC_FILES, ARGS.offset, ARGS.epochs, (algo, conf))
            # plotter.plot_reward("reward.txt", "plots/reward_%s_%s" % (algo, ARGS.epoch + ARGS.offset))
            plotter.plot_avgreward("reward.txt", "plots/avgreward_%s_%s" % (algo, ARGS.epochs + ARGS.offset))
            plotter.plot_train_bw('results', 'plots/%s_train_bw' % algo, TRAFFIC_FILES, (algo, conf))
            plotter.plot_train_bw_iface('results', 'plots/%s_train_bw_alt' % algo, TRAFFIC_FILES, (algo, conf))
            plotter.plot_train_bw_avg('results', 'plots/%s_train_bw_avg' % algo, TRAFFIC_FILES, (algo, conf))
            plotter.plot_train_qlen('results', 'plots/%s_train_qlen' % algo, TRAFFIC_FILES, (algo, conf))
            plotter.plot_train_qlen_iface('results', 'plots/%s_train_qlen_alt' % algo, TRAFFIC_FILES, (algo, conf))
            plotter.plot_train_qlen_avg('results', 'plots/%s_train_qlen_avg' % algo, TRAFFIC_FILES, (algo, conf))

    # Compare the agents performance against other algorithms
    if ARGS.test is True:
        for e in range(ARGS.epochs):
            print("Running benchmarks for %d seconds each with input matrix at %s and output at %s"
                  % (DURATION, INPUT_DIR, OUTPUT_DIR))
            run_tests(INPUT_DIR, OUTPUT_DIR, DURATION, TRAFFIC_FILES, algorithms)
            plotter.plot_test_bw('results', 'plots/test_bw_sum_%d' % e, TRAFFIC_FILES, LABELS, algorithms)
            plotter.plot_test_qlen('results', 'plots/test_qlen_sum_%d' %
                                   e, QLEN_TRAFFICS, QLEN_LABELS, algorithms, FATTREE_SW)
    elif not ARGS.train:
        print("Doing nothing...\nRun the command with --train to train/ the Iroko agent and/or --test to run benchmarks.")
