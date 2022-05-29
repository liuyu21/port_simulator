import random
import numpy as np
from collections import deque

import matplotlib.pyplot as plt


class MessageGenerator():
    def __init__(self, prob, min_len=64, max_len=1500):
        self.prob = prob
        self.min_len = min_len
        self.max_len = max_len
        return

    def generate(self):
        p = random.uniform(0, 1)
        if p < self.prob:
            message_len = random.randint(self.min_len, self.max_len)
        else:
            message_len = None
        return message_len


class MessageQueue():
    def __init__(self, band_width, prob):
        self.band_width = band_width
        self.credit_default = 64 * band_width
        self.credit = 0
        self.credit_used = 0
        self.queue = deque()
        self.message_generator = MessageGenerator(prob)
        return

    def update(self):
        self.credit += self.credit_default
        if len(self.queue) == 0:
            self.credit = min(self.credit, self.credit_default)
        return

    def receive(self):
        message_len = self.message_generator.generate()
        if message_len is not None:
            self.queue.append(message_len)
        return

    def read(self):
        message_len = None
        if self.credit > 0 and len(self.queue) > 0:
            message_len = self.queue[0]
        return message_len

    def send(self):
        message_len = self.queue.popleft()
        self.credit -= message_len
        return message_len

    def get_status(self):
        message_num = len(self.queue)
        total_size = sum(self.queue)
        return message_num, total_size


class Scheduler():
    def __init__(self, queue_num, total_band_width, min_band_width, increase_band_width,
                 receive_time=3, prob_loc=0.8, prob_scale=0.1):
        assert queue_num * min_band_width <= total_band_width, "too much queue_num!!!"
        self.queue_num = queue_num
        self.receive_time = receive_time
        self.max_buffer_size = total_band_width * 64
        all_band_width = []
        self.probs = []
        self.queue_records = []
        self.queues = []
        self.port_records = {'send': [], 'remain': []}
        self.idx = 0
        self.cycle_count = 0

        for i in range(queue_num):
            self.queue_records.append(
                {'total': 0, 'send': [], 'status_num': [], 'status_size': []})
            all_band_width.append(min_band_width)
            prob = max(min(np.random.normal(
                loc=prob_loc, scale=prob_scale, size=None), 1.0), 0.0)
            self.probs.append(prob)
            total_band_width -= min_band_width
        while total_band_width >= increase_band_width:
            idx = random.randint(0, queue_num-1)
            all_band_width[idx] += increase_band_width
            total_band_width -= increase_band_width

        for band_width, prob in zip(all_band_width, self.probs):
            self.queues.append(MessageQueue(band_width, prob))
        return

    def send_all(self):
        finish = False
        record = {}
        buffer_size = self.max_buffer_size

        for i in range(self.queue_num):
            mq = self.queues[self.idx]
            move_next = 0
            while True:
                send_len = mq.read()
                if send_len is None:  # is empty?
                    move_next = 1
                    break

                if buffer_size < send_len:  # have enough space?
                    finish = True
                    break

                # send, update and record
                send_len = mq.send()
                buffer_size -= send_len
                # move_next = 1

                if self.idx not in record:
                    record[self.idx] = 0
                record[self.idx] += send_len

            self.idx = (self.idx + move_next) % self.queue_num
            if finish:
                break
        return record, self.max_buffer_size - buffer_size

    def cycle(self):
        self.cycle_count += 1
        for mq in self.queues:
            for i in range(self.receive_time):
                mq.receive()
            mq.update()

        record, length = self.send_all()
        remain = 0
        for i in range(self.queue_num):
            in_queue_size, in_queue_size = self.queues[i].get_status()
            send_len = 0
            if i in record:
                send_len = record[i]
            self.queue_records[i]['send'].append(send_len)
            self.queue_records[i]['status_num'].append(in_queue_size)
            self.queue_records[i]['status_size'].append(in_queue_size)
            self.queue_records[i]['total'] += send_len
            remain += in_queue_size

        self.port_records['send'].append(length)
        self.port_records['remain'].append(remain)
        return

    def show_probs(self):
        plt.hist(self.probs, density=True, bins=50)
        plt.ylabel('count')
        plt.xlabel('Probability')
        return

    def show_port_usage(self):
        plt.figure(figsize=(14, 4))
        plt.ylabel('usage')
        plt.xlabel('cycle')
        plt.ylim(0.5, 1.1)
        x = list(range(len(self.port_records['send'])))
        plt.plot(x, np.array(
            self.port_records['send'])/self.max_buffer_size, 'b.')
        return

    def show_port_remain(self):
        plt.figure(figsize=(14, 4))
        plt.ylabel('remain')
        plt.xlabel('cycle')
        x = list(range(len(self.port_records['send'])))
        plt.plot(x, self.port_records['remain'], 'g.')
        return

    def show_queue_usage(self):
        ports_usage = []
        for i in range(self.queue_num):
            usage = self.queue_records[i]['total'] / \
                (self.queues[i].band_width*64*self.cycle_count)
            ports_usage.append(usage)

        plt.figure(figsize=(14, 4))
        plt.ylabel('usage')
        plt.xlabel('queue')
        plt.ylim(0.5, 1.1)
        x = list(range(self.queue_num))
        plt.plot(x, ports_usage, 'y.')
        return
