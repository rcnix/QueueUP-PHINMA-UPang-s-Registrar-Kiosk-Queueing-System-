# DATA STRUCTURE - BATERBONIALISM
# FIFO (First In, Fitst Out) system implemented to generate and remove queue tickets

# class Node - One linked-list item used to preserve ticket order.
class Node:

# def __init__() - Stores one queue value and the link to the next value
    def __init__(self, value):
        self.value = value
        self.next = None

 # class Queue - FIFO (First In, First Out) queue for one registrar service window
class Queue:

# def__init__() - Keeping both ends makes adding a ticket an O(1) operation
    def __init__(self, prefix="REG"):
        self.prefix = prefix
        self._next_number = 1
        self.front = None
        self.end = None
        self.size = 0

# def__len__() - defReturns the number of tickets currently waiting
    def __len__(self):
        return self.size

# def enqueue() - Append a ticket behind every ticket already waiting
    def enqueue(self, value):
        new_node = Node(value)
        if self.end is None:
            self.front = self.end = new_node
        else:
            self.end.next = new_node
            self.end = new_node
        self.size += 1


# def generate_number() -  Create the next window-specific ticket and enqueue it
    def generate_number(self):
        ticket = f"{self.prefix}-{self._next_number:03d}"
        self._next_number += 1
        self.enqueue(ticket)
        return ticket

# def dequeue() - Serve the oldest ticket, or return None when no one is waiting.
    def dequeue(self):
        if self.is_empty():
            return None

# variables - An empty queue must not keep a stale tail node.
        ticket = self.front.value
        self.front = self.front.next
        self.size -= 1
        if self.front is None:
            self.end = None
        return ticket

# def peek() - Returns the oldest ticket without removing it
    def peek(self):
        return None if self.is_empty() else self.front.value

# def tickets() - Yield waiting tickets from first in line to last in line
    def tickets(self):
        current = self.front
        while current is not None:
            yield current.value
            current = current.next

#def clear() - Removes every ticket from the queue
    def clear(self):
        self.front = None
        self.end = None
        self.size = 0

#def is_empty() - Checks whether the queue has no tickets
    def is_empty(self):
        return self.front is None

if __name__ == "__main__":
    queue = Queue()
    queue.generate_number()
    print(queue.dequeue())
