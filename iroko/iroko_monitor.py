import subprocess
import re
import time
import threading

MAX_CAPACITY = 10e6   # Max capacity of link


class Collector(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.name = 'Collector'
        self.iface_list = []
        self.kill = False

    def set_interfaces(self):
        cmd = "sudo ovs-vsctl list-br | xargs -L1 sudo ovs-vsctl list-ports"
        output = subprocess.check_output(cmd, shell=True)
        iface_list_temp = []
        for row in output.split('\n'):
            if row != '':
                iface_list_temp.append(row)
        self.iface_list = iface_list_temp

    def run(self):
        while True:
            if self.kill:
                self.exit()

    def terminate(self):
        self.kill = True


class StatsCollector(Collector):

    def __init__(self):
        Collector.__init__(self)
        self.name = 'StatsCollector'
        self.iface_list = []
        self.bws_rx = {}
        self.bws_tx = {}
        self.free_bandwidths = {}
        self.drops = {}
        self.overlimits = {}
        self.queues = {}
        self.d_vector = {}

    def run(self):
        self.set_interfaces()
        self.init_stats()
        self.init_deltas()
        while True:
            if self.kill:
                self.exit()
            self._collect_stats()

    def init_deltas(self):
        for iface in self.iface_list:
            self.d_vector[iface] = {}
            self.d_vector[iface]["delta_rx"] = 0
            self.d_vector[iface]["delta_tx"] = 0
            self.d_vector[iface]["delta_d"] = 0
            self.d_vector[iface]["delta_ov"] = 0
            self.d_vector[iface]["delta_q"] = 0
            self.d_vector[iface]["delta_q_abs"] = 0
            self.d_vector[iface]["delta_rx_abs"] = 0
            self.d_vector[iface]["delta_tx_abs"] = 0
        return self.d_vector

    def init_stats(self):
        for iface in self.iface_list:
            self.bws_rx[iface] = 0
            self.bws_tx[iface] = 0
            self.free_bandwidths[iface] = 0
            self.drops[iface] = 0
            self.overlimits[iface] = 0
            self.queues[iface] = 0
        return self.bws_rx, self.bws_tx, self.drops, self.overlimits, self.queues

    def _get_bandwidths(self, iface_list):
        # cmd3 = "ifstat -i %s -q 0.1 1 | awk '{if (NR==3) print $2}'" % (iface)
        processes = []
        bws_rx = {}
        bws_tx = {}
        # iface_string = ",".join(iface_list )
        for iface in iface_list:
            cmd = (" ifstat -i %s -b -q 0.5 1 | awk \'{if (NR==3) print $0}\' | \
                   awk \'{$1=$1}1\' OFS=\", \"" % (iface))  # | sed \'s/\(\([^,]*,\)\{1\}[^,]*\),/\1;/g\'
            # output = subprocess.check_output(cmd, shell=True)
            proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True)
            processes.append((proc, iface))

        for proc, iface in processes:
            proc.wait()
            output, _ = proc.communicate()
            bw = output.split(',')
            try:
                bws_rx[iface] = float(bw[0]) * 1000
                bws_tx[iface] = float(bw[1]) * 1000
            except Exception as e:
                # print("Empty Request %s" % e)
                bws_rx[iface] = 0
                bws_tx[iface] = 0
        return bws_rx, bws_tx

    def _get_free_bw(self, capacity, speed):
        # freebw: Kbit/s
        return max(capacity - speed * 8 / 1000.0, 0)

    def _get_free_bandwidths(self, bandwidths):
        free_bandwidths = {}
        for iface, bandwidth in bandwidths.iteritems():
            free_bandwidths[iface] = self._get_free_bw(MAX_CAPACITY, bandwidth)
        return free_bandwidths

    def _get_qdisc_stats(self, iface_list):
        drops = {}
        overlimits = {}
        queues = {}

        re_dropped = re.compile(r'(?<=dropped )[ 0-9]*')
        re_overlimit = re.compile(r'(?<=overlimits )[ 0-9]*')
        re_queued = re.compile(r'backlog\s[^\s]+\s([\d]+)p')
        for iface in iface_list:
            cmd = "tc -s qdisc show dev %s" % (iface)
            # cmd1 = "tc -s qdisc show dev %s | grep -ohP -m1 '(?<=dropped )[ 0-9]*'" % (iface)
            # cmd2 = "tc -s qdisc show dev %s | grep -ohP -m1 '(?<=overlimits )[ 0-9]*'" % (iface)
            # cmd2 = "tc -s qdisc show dev %s | grep -ohP -m1 '(?<=backlog )[ 0-9]*'" % (iface)
            drop_return = {}
            over_return = {}
            queue_return = {}
            try:
                output = subprocess.check_output(cmd, shell=True)
                drop_return = re_dropped.findall(output)
                over_return = re_overlimit.findall(output)
                queue_return = re_queued.findall(output)
            except Exception as e:
                # print("Empty Request %s" % e)
                drop_return[0] = 0
                over_return[0] = 0
                queue_return[0] = 0
            drops[iface] = int(drop_return[0])
            overlimits[iface] = int(over_return[0])
            queues[iface] = int(queue_return[0])
        return drops, overlimits, queues

    def _collect_stats(self):
        self.bws_rx, self.bws_tx = self._get_bandwidths(self.iface_list)
        self.drops, self.overlimits, self.queues = self._get_qdisc_stats(
            self.iface_list)

    def _compute_delta(self, iface, bw_rx, bw_tx, drops, overlimits, queues):
        deltas = {}
        if bw_rx <= self.bws_rx[iface]:
            deltas["delta_rx"] = 1
        else:
            deltas["delta_rx"] = 0

        if bw_tx <= self.bws_tx[iface]:
            deltas["delta_tx"] = 1
        else:
            deltas["delta_tx"] = 0

        if drops < self.drops[iface]:
            deltas["delta_d"] = 0
        else:
            deltas["delta_d"] = 1

        if overlimits < self.overlimits[iface]:
            deltas["delta_ov"] = 0
        else:
            deltas["delta_ov"] = 1

        if queues < self.queues[iface]:
            deltas["delta_q"] = -1
        elif queues > self.queues[iface]:
            deltas["delta_q"] = 1
        else:
            deltas["delta_q"] = 0
        deltas["delta_q_abs"] = self.queues[iface] - queues
        deltas["delta_rx_abs"] = self.bws_rx[iface] - bw_rx
        deltas["delta_tx_abs"] = self.bws_tx[iface] - bw_tx
        return deltas


    def get_interface_deltas(self, bws_rx, bws_tx, drops, overlimits, queues):
        for iface in self.iface_list:
            self.d_vector[iface] = self._compute_delta(
                iface, bws_rx[iface], bws_tx[iface], drops[iface], overlimits[iface], queues[iface])
        return self.d_vector

    def get_interface_stats(self):
        # self._get_flow_stats(self.iface_list)
        # self.drops, self.overlimits, self.queues = self._get_qdisc_stats(  self.iface_list)
        return self.bws_rx, self.bws_tx, self.drops, self.overlimits, self.queues


class FlowCollector(Collector):

    def __init__(self, host_ips):
        Collector.__init__(self)
        threading.Thread.__init__(self)
        self.name = 'FlowCollector'
        self.host_ips = host_ips
        self.kill = False
        self.src_flows = {}
        self.dst_flows = {}

    def run(self):
        self.set_interfaces()
        self.init_flows()
        while True:
            if self.kill:
                self.exit()
            self._collect_flows()

    def init_flows(self):
        for iface in self.iface_list:
            self.src_flows[iface] = [0] * len(self.host_ips)
            self.dst_flows[iface] = [0] * len(self.host_ips)

    def _get_flow_stats(self, iface_list):
        processes = []
        for iface in iface_list:
            cmd = ("sudo timeout 1 tcpdump -l -i " + iface + " -n -c 10 ip 2>/dev/null | " +
                   "grep -P -o \'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+).*? > ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\' | " + "grep -P -o \'[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\' | xargs -n 2 echo | awk \'!a[$0]++\'")
            # output = subprocess.check_output(cmd, shell=True)
            proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True)
            processes.append((proc, iface))

        for proc, iface in processes:
            proc.wait()
            output, _ = proc.communicate()
            self.src_flows[iface] = [0] * len(self.host_ips)
            self.dst_flows[iface] = [0] * len(self.host_ips)
            for row in output.split('\n'):
                if row != '':
                    src, dst = row.split(' ')
                    for i, ip in enumerate(self.host_ips):
                        if src == ip:
                            self.src_flows[iface][i] = 1
                        if dst == ip:
                            self.dst_flows[iface][i] = 1
            # print(self.src_flows)
            # print(self.dst_flows)

    def _collect_flows(self):
        # iface_list = self._get_interfaces()
        self._get_flow_stats(self.iface_list)

    def get_interface_flows(self):
        return self.src_flows, self.dst_flows
