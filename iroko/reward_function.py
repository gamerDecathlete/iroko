import numpy as np


class RewardFunction:
    def __init__(self, hosts, interfaces, function_name, max_queue, max_bw):
        self.interfaces = interfaces
        self.num_interfaces = len(interfaces)
        self.hosts = hosts
        self.func_name = function_name
        self.max_queue = max_queue
        self.max_bw = max_bw
        self.has_congestion = set()

    def get_reward(self, bw, queues):
        if self.func_name == 'q_bandwidth':
            return self._queue_bandwidth(bw, queues)
        elif self.func_name == 'q_precision':
            return self._queue_precision(queues)
        elif self.func_name == 'std_dev':
            return self._std_dev(bw, queues)
        else:
            return self._queue_bandwidth_filtered(bw, queues)

    def _queue_bandwidth(self, bws_rx, queues):
        bw_reward = 0.0
        queue_reward = 0.0
        for i, iface in enumerate(self.interfaces):
            bw_reward += float(bws_rx[iface]) / float(self.max_bw)
            # print('{} bw reward so far: {}'.format(i, bw_reward))
            queue_reward -= self.num_interfaces * \
                (float(queues[iface]) / float(self.max_queue))**2
        return bw_reward, queue_reward

    def _queue_bandwidth_filtered(self, bws_rx, queues):
        bw_reward = 0.0
        queue_reward = 0.0
        for iface in self.interfaces:
            if iface not in self.hosts:
                print("Interface: %s BW: %f Queues: %d" %
                      (iface, bws_rx[iface], queues[iface]))
                bw_reward += float(bws_rx[iface]) / float(self.max_bw)
                queue_reward -= (self.num_interfaces / 2) * \
                    (float(queues[iface]) / float(self.max_queue))**2
        return bw_reward, queue_reward

    def _queue_precision(self, queues):
        bw_reward = 0.0
        queue_reward = 0.0
        for iface in self.interfaces:
            if iface not in self.hosts:
                q = float(queues[iface])
                if q > 0.0 and iface not in self.has_congestion:
                    self.has_congestion.add(iface)
                    queue_reward = 0.0  # don't worry about it first time around
                elif iface in self.has_congestion:
                    if self.max_queue / 5. < q and q <= self.max_queue / 2.:
                        queue_reward += 0.0
                    elif q <= self.max_queue / 5.:
                        queue_reward += 0.5
                    else:
                        queue_reward -= 1.0
        return bw_reward, queue_reward

    def _std_dev(self, bws_rx, queues):
        bw_reward = 0.0
        queue_reward = 0.0
        std_reward = 0
        print self.interfaces
        for i, iface in enumerate(self.interfaces):
            bw_reward += float(bws_rx[iface]) / float(self.max_bw)
            pbws = [bws_rx[iface]
                    for i in self.interfaces if bws_rx[iface] > 0]
            if len(pbws) > 0:
                std_reward -= (np.std(pbws) / float(self.max_bw))
            queue_reward -= (self.num_interfaces / 2) * \
                (float(queues[iface]) / float(self.max_queue))**2
        bw_reward += std_reward
        return bw_reward, queue_reward
