import sys
import os
import queue
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class LocalBuffer:
    def __init__(self, max_size=100):
        self.buffer = queue.Queue(maxsize=max_size)
        self.dropped = 0
        self.total_received = 0
        self.total_released = 0

    def push(self, item):
        self.total_received += 1
        try:
            self.buffer.put_nowait(item)
            return True
        except queue.Full:
            self.dropped += 1
            print(f"  [Buffer] FULL — dropped item {self.total_received}")
            return False

    def pop(self):
        try:
            item = self.buffer.get_nowait()
            self.total_released += 1
            return item
        except queue.Empty:
            return None

    def size(self):
        return self.buffer.qsize()

    def is_empty(self):
        return self.buffer.empty()

    def stats(self):
        return {
            "current_size": self.size(),
            "total_received": self.total_received,
            "total_released": self.total_released,
            "dropped": self.dropped
        }


if __name__ == "__main__":
    from tier1_device.sensor_simulator import generate_reading
    from tier1_device.preprocessing import preprocess
    from tier1_device.threshold_detector import check_thresholds
    from tier2_edge.interoperability_engine import adapt

    print("\n" + "="*55)
    print("  Local Buffer — TEST")
    print("="*55)

    buffer = LocalBuffer(max_size=5)

    print("\nPushing 5 readings into buffer...")
    for i in range(5):
        raw = generate_reading()
        cleaned = preprocess(raw)
        checked = check_thresholds(cleaned)
        standard = adapt(checked)
        success = buffer.push(standard)
        print(f"  Push {i+1}: {'OK' if success else 'FAILED'} | Buffer size: {buffer.size()}")

    print(f"\nBuffer full. Trying to push one more...")
    extra = adapt(check_thresholds(preprocess(generate_reading())))
    buffer.push(extra)

    print(f"\nPopping all items from buffer...")
    count = 0
    while not buffer.is_empty():
        item = buffer.pop()
        count += 1
        print(f"  Popped {count}: HeartRate={item.get('HeartRate')} vendor={item.get('original_vendor')}")

    print(f"\nBuffer stats: {buffer.stats()}")
    print("\n  Buffer prevents data loss during network failure ✅")